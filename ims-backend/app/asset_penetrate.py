"""ASSET 穿透（#65 · E2E-S5-03/04）。

正向：实名人 → 资产，层级 ≤ 5；更深或 layers 超出 L1–L5 返回 1013。
反向：资产 → 使用人，按领用/归还/报废区分在用、已归还、已报废。
"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_id_card, mask_mobile, mask_name, utcnow
from app.corp import count_of, page_args, tenant_of, user_names
from app.crypto import decrypt_text
from app.models import AssetHierarchy, AssetLedger, AssetLifecycleEvent, AssetTraceLog, User
from app.ops_db import ops_session
from app.ops_models import Realname

router = APIRouter()

MAX_LAYER = 5
LAYER_TOKENS = {"L1", "L2", "L3", "L4", "L5"}
HOLDER_LABEL = {"IN_USE": "在用", "RETURNED": "已归还", "SCRAPPED": "已报废"}


def _missing(db: Session, actor: User, asset_id: int):
    row = db.get(AssetLedger, asset_id)
    if row is None or row.deleted:
        return None, fail(1011, "资产不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return None, fail(1504, "资源不可用")
    return row, None


def _hierarchy(db: Session, actor: User, asset_id: int) -> AssetHierarchy | None:
    stmt = select(AssetHierarchy).where(
        AssetHierarchy.asset_id == asset_id,
        AssetHierarchy.deleted == 0,
        AssetHierarchy.tenant_id == tenant_of(actor),
    )
    return db.scalar(stmt)


def _layers_blocked(layers: str):
    text = (layers or "").strip()
    if not text:
        return None
    parts = [item.strip().upper() for item in text.split(",") if item.strip()]
    if len(parts) > MAX_LAYER or any(item not in LAYER_TOKENS for item in parts):
        return fail(1013, "穿透层级超限")
    return None


def _audit(db: Session, actor: User, trace_type: str, asset_id: int, realname_id: int, nodes: list) -> None:
    db.add(
        AssetTraceLog(
            trace_type=trace_type,
            asset_id=asset_id or 0,
            realname_id=realname_id or 0,
            node_chain=json.dumps(nodes, ensure_ascii=False)[:65000],
            query_user_id=actor.id,
            tenant_id=tenant_of(actor),
            created_at=utcnow(),
        )
    )


def _realname(actor: User, realname_id: int) -> dict | None:
    ops = ops_session()
    try:
        row = ops.get(Realname, realname_id)
        if row is None or row.deleted:
            return None
        if (row.tenant_id or 0) != tenant_of(actor):
            return None
        return {
            "id": row.id,
            "real_name": row.real_name,
            "status": row.status,
            "phone_enc": row.phone_enc,
            "id_card_enc": row.id_card_enc,
        }
    finally:
        ops.close()


def _check_realname(actor: User, realname_id: int):
    row = _realname(actor, realname_id)
    if row is None:
        return fail(1500, "实名人不存在")
    if row["status"] != "ENABLED":
        return fail(1501, "实名人已停用")
    return None


def _person_brief(row: dict | None, realname_id: int) -> dict:
    if row is None:
        return {
            "userId": realname_id,
            "nickname": "实名人",
            "mobileMasked": "",
            "idCardMasked": "",
            "deptNames": [],
        }
    phone = ""
    card = ""
    try:
        phone = mask_mobile(decrypt_text(row["phone_enc"]))
    except Exception:
        phone = ""
    try:
        card = mask_id_card(decrypt_text(row["id_card_enc"]))
    except Exception:
        card = ""
    return {
        "userId": row["id"],
        "nickname": mask_name(row["real_name"]) or "实名人",
        "mobileMasked": phone,
        "idCardMasked": card,
        "deptNames": [],
    }


def _person_node(brief: dict) -> dict:
    return {
        "id": f"person:{brief['userId']}",
        "label": brief["nickname"],
        "layer": "PERSON",
        "level": 0,
        "assetCode": "",
        "status": "",
    }


def _asset_node(row: AssetLedger, level: int) -> dict:
    return {
        "id": f"asset:{row.id}",
        "label": f"{row.asset_code} {row.asset_name}".strip(),
        "layer": "ASSET",
        "level": level,
        "assetCode": row.asset_code,
        "status": row.status,
    }


def _edges(nodes: list[dict]) -> list[dict]:
    edges = []
    for index in range(1, len(nodes)):
        relation = "实名" if nodes[index - 1]["layer"] == "PERSON" else "下级"
        edges.append({"from": nodes[index - 1]["id"], "to": nodes[index]["id"], "relation": relation})
    return edges


def _walk(db: Session, actor: User, asset_id: int):
    seen: set[int] = set()
    assets: list[AssetLedger] = []
    levels: list[int] = []
    realname_id = 0
    current = asset_id
    while current:
        if current in seen:
            return None, fail(1001, "资产层级成环")
        seen.add(current)
        row, error = _missing(db, actor, current)
        if error:
            return None, error
        hier = _hierarchy(db, actor, current)
        assets.append(row)
        levels.append(hier.level if hier else 0)
        if hier is None:
            break
        realname_id = hier.realname_id or realname_id
        current = hier.parent_asset_id or 0
    assets.reverse()
    levels.reverse()
    return (assets, levels, realname_id), None


def holders_of(db: Session, row: AssetLedger) -> list[dict]:
    stmt = (
        select(AssetLifecycleEvent)
        .where(AssetLifecycleEvent.asset_id == row.id, AssetLifecycleEvent.deleted == 0)
        .order_by(AssetLifecycleEvent.id)
    )
    events = list(db.scalars(stmt).all())
    ids = {event.owner_user_id for event in events if event.owner_user_id}
    names = user_names(db, ids)
    last_id = 0
    last_name = ""
    rows: list[dict] = []
    for event in events:
        owner_id = event.owner_user_id or 0
        owner_name = names.get(owner_id, "") if owner_id else ""
        if event.event_type == "CHECKOUT" and owner_id:
            last_id = owner_id
            last_name = owner_name
            rows.append(_holder(owner_id, owner_name, "IN_USE", event.remark))
        elif event.event_type == "RETURN" and owner_id:
            last_id = owner_id
            last_name = owner_name
            rows.append(_holder(owner_id, owner_name, "RETURNED", event.remark))
        elif event.event_type == "SCRAP":
            rows.append(_holder(last_id, last_name or "—", "SCRAPPED", event.remark))
    return rows


def _holder(user_id: int, user_name: str, status: str, remark: str) -> dict:
    return {
        "userId": user_id,
        "userName": user_name or "—",
        "status": status,
        "statusLabel": HOLDER_LABEL[status],
        "remark": remark or "",
    }


def link_hierarchy(db: Session, actor: User, row: AssetLedger, realname_id: int | None, parent_code: str):
    code = (parent_code or "").strip()
    person_id = int(realname_id or 0)
    if not code and not person_id:
        return None
    parent = None
    parent_hier = None
    if code:
        parent = db.scalar(
            select(AssetLedger).where(
                AssetLedger.deleted == 0,
                AssetLedger.tenant_id == tenant_of(actor),
                AssetLedger.asset_code == code,
            )
        )
        if parent is None:
            return fail(1011, "上级资产不存在")
        parent_hier = _hierarchy(db, actor, parent.id)
        if parent_hier is None:
            return fail(1001, "上级资产未挂实名人")
        seen: set[int] = set()
        cursor = parent_hier
        while cursor is not None:
            if cursor.asset_id in seen:
                return fail(1001, "资产层级成环")
            seen.add(cursor.asset_id)
            if not cursor.parent_asset_id:
                break
            cursor = _hierarchy(db, actor, cursor.parent_asset_id)
        level = int(parent_hier.level or 0) + 1
        person_id = int(parent_hier.realname_id or 0)
        path = f"{parent_hier.path}/{row.id}"
    else:
        person_error = _check_realname(actor, person_id)
        if person_error:
            return person_error
        level = 1
        path = f"/{person_id}/{row.id}"
    db.add(
        AssetHierarchy(
            asset_id=row.id,
            parent_asset_id=parent.id if parent else None,
            realname_id=person_id,
            level=level,
            path=path[:512],
            deleted=0,
            tenant_id=tenant_of(actor),
            created_at=utcnow(),
        )
    )
    return None


def _graph(db: Session, actor: User, assets: list[AssetLedger], levels: list[int], realname_id: int) -> dict:
    brief = _person_brief(_realname(actor, realname_id) if realname_id else None, realname_id)
    nodes = []
    if realname_id:
        nodes.append(_person_node(brief))
    for asset, level in zip(assets, levels):
        nodes.append(_asset_node(asset, level))
    depth = max(levels) if levels else 0
    return {"nodes": nodes, "edges": _edges(nodes), "depth": depth, "realnameId": realname_id, "verifiedPersons": [brief] if realname_id else []}


def _trace_asset(db: Session, actor: User, asset_id: int, layers: str):
    graph, error = _prepare_graph(db, actor, asset_id, layers)
    if error:
        return error
    return ok(graph)


def _trace_realname(db: Session, actor: User, realname_id: int, layers: str):
    blocked = _layers_blocked(layers)
    if blocked:
        _audit(db, actor, "forward", 0, realname_id, [])
        return blocked
    person_error = _check_realname(actor, realname_id)
    if person_error:
        return person_error
    stmt = select(AssetHierarchy).where(
        AssetHierarchy.deleted == 0,
        AssetHierarchy.tenant_id == tenant_of(actor),
        AssetHierarchy.realname_id == realname_id,
    )
    rows = list(db.scalars(stmt).all())
    if any(int(row.level or 0) > MAX_LAYER for row in rows):
        _audit(db, actor, "forward", 0, realname_id, [])
        return fail(1013, "穿透层级超限")
    if not rows:
        graph = _graph(db, actor, [], [], realname_id)
        _audit(db, actor, "forward", 0, realname_id, graph["nodes"])
        return ok(graph)
    leaf = max(rows, key=lambda item: (int(item.level or 0), int(item.asset_id or 0)))
    return _trace_asset(db, actor, leaf.asset_id, "")


def _asset_brief(row: AssetLedger) -> dict:
    return {
        "id": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "spec": row.spec,
        "status": row.status,
        "purchaseDate": row.purchase_date,
        "subjectId": 0,
        "ownerUserId": row.owner_user_id,
    }


def _prepare_graph(db: Session, actor: User, asset_id: int, layers: str):
    blocked = _layers_blocked(layers)
    if blocked:
        _audit(db, actor, "forward", asset_id, 0, [])
        return None, blocked
    walked, error = _walk(db, actor, asset_id)
    if error:
        return None, error
    assets, levels, realname_id = walked
    if any(level > MAX_LAYER for level in levels):
        _audit(db, actor, "forward", asset_id, realname_id, [])
        return None, fail(1013, "穿透层级超限")
    graph = _graph(db, actor, assets, levels, realname_id)
    _audit(db, actor, "forward", asset_id, realname_id, graph["nodes"])
    return graph, None


@router.get("/asset/forward/trace/{asset_id}")
def forward_trace(
    asset_id: int,
    realnameId: int = 0,
    layers: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if asset_id <= 0:
        if not realnameId:
            return fail(1001, "实名人必填")
        return _trace_realname(db, actor, realnameId, layers)
    graph, error = _prepare_graph(db, actor, asset_id, layers)
    if error:
        return error
    return ok(graph)


@router.get("/asset/forward/detail/{asset_id}")
def forward_detail(
    asset_id: int,
    layers: str = "",
    withSessionLayer: bool = False,
    withFinanceLayer: bool = False,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    del withSessionLayer, withFinanceLayer
    graph, error = _prepare_graph(db, actor, asset_id, layers)
    if error:
        return error
    row, missing = _missing(db, actor, asset_id)
    if missing:
        return missing
    return ok(
        {
            "asset": _asset_brief(row),
            "bindAccounts": [],
            "verifiedPersons": graph.get("verifiedPersons") or [],
            "liveSessions": [],
            "financeSummary": {"totalCost": 0, "totalRevenue": 0, "costMasked": False},
            "nodes": graph.get("nodes") or [],
            "edges": graph.get("edges") or [],
            "depth": graph.get("depth") or 0,
            "holders": holders_of(db, row),
        }
    )


def _effective_time(db: Session, asset_id: int) -> str:
    stmt = (
        select(AssetLifecycleEvent)
        .where(
            AssetLifecycleEvent.asset_id == asset_id,
            AssetLifecycleEvent.deleted == 0,
            AssetLifecycleEvent.event_type == "CHECKOUT",
        )
        .order_by(AssetLifecycleEvent.id.desc())
    )
    event = db.scalars(stmt).first()
    if event is None or event.created_at is None:
        return ""
    return event.created_at.strftime("%Y-%m-%d %H:%M:%S")


@router.get("/asset/reverse/by-person/{user_id}")
def reverse_by_person(
    user_id: int,
    pageNo: int = 1,
    pageSize: int = 10,
    statusFilter: str = "",
    includeHistory: bool = True,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    user = db.get(User, user_id)
    if user is None or user.deleted or (user.tenant_id or 0) != tenant_of(actor):
        return fail(1500, "使用人不存在")
    owned = select(AssetLedger.id).where(
        AssetLedger.deleted == 0,
        AssetLedger.tenant_id == tenant_of(actor),
        AssetLedger.owner_user_id == user_id,
    )
    asset_ids = set(db.scalars(owned).all())
    if includeHistory:
        hist = select(AssetLifecycleEvent.asset_id).where(
            AssetLifecycleEvent.deleted == 0,
            AssetLifecycleEvent.tenant_id == tenant_of(actor),
            AssetLifecycleEvent.owner_user_id == user_id,
        )
        asset_ids.update(db.scalars(hist).all())
    number, size = page_args(pageNo, pageSize)
    if not asset_ids:
        _audit(db, actor, "reverse", 0, 0, [])
        return ok({"list": [], "total": 0, "pageNo": number, "pageSize": size, "summary": _summary([])})
    stmt = select(AssetLedger).where(
        AssetLedger.deleted == 0,
        AssetLedger.tenant_id == tenant_of(actor),
        AssetLedger.id.in_(asset_ids),
    )
    if statusFilter:
        stmt = stmt.where(AssetLedger.status == statusFilter)
    total = count_of(db, stmt)
    rows = list(db.scalars(stmt.order_by(AssetLedger.id.desc()).offset((number - 1) * size).limit(size)).all())
    count_stmt = select(AssetLedger).where(
        AssetLedger.deleted == 0,
        AssetLedger.tenant_id == tenant_of(actor),
        AssetLedger.id.in_(asset_ids),
    )
    if statusFilter:
        count_stmt = count_stmt.where(AssetLedger.status == statusFilter)
    counted = list(db.scalars(count_stmt).all())
    items = [_reverse_item(db, row) for row in rows]
    _audit(db, actor, "reverse", 0, 0, [{"assetId": item["assetId"], "status": item["status"]} for item in items])
    return ok(
        {
            "list": items,
            "total": total,
            "pageNo": number,
            "pageSize": size,
            "summary": _summary(counted),
        }
    )


def _summary(rows: list[AssetLedger]) -> dict:
    counts = {"IN_USE": 0, "RETURNED": 0, "SCRAPPED": 0}
    for row in rows:
        if row.status in counts:
            counts[row.status] += 1
    return {
        "total": len(rows),
        "inUse": counts["IN_USE"],
        "returned": counts["RETURNED"],
        "scrapped": counts["SCRAPPED"],
    }


def _reverse_item(db: Session, row: AssetLedger) -> dict:
    return {
        "assetId": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "status": row.status,
        "bindType": "HOLD",
        "effectiveTime": _effective_time(db, row.id),
        "frozen": False,
        "relatedAccountNo": "",
    }
