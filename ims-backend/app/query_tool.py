"""QT-001 查询工具（W9-9 首片 · 模板列表 + run 占位）。"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import ops_db, page_args, paged, tenant_of, user_names
from app.models import QueryTemplate, User

router = APIRouter(prefix="/analysis/query-tool", tags=["query-tool"])

BJ = timezone(timedelta(hours=8))
MODES = frozenset({"DRILL", "TRACE", "FLAT"})
STATUSES = frozenset({"DRAFT", "PUBLISHED"})


class TemplateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    mode: str = "DRILL"
    desc: str = ""
    payloadJson: dict = Field(default_factory=dict)


class TemplateUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    desc: str | None = None
    payloadJson: dict | None = None


class RunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mode: str
    templateCode: str | None = None
    runtime: dict | None = None
    inlineTemplate: dict | None = None


# 执行只读开发/测试种子表。列名来自白名单，条件值只走绑定参数。
_SEED_SOURCES: dict[str, dict] = {
    "IP_GROUP": {
        "table": "oa_ip_group",
        "kind": "ops",
        "columns": [("group_name", "组名称"), ("level", "级别"), ("status", "状态")],
    },
    "PLATFORM_ACCOUNT": {
        "table": "oa_platform_account",
        "kind": "ops",
        "columns": [("account_no", "账号"), ("account_name", "账号名称"), ("platform_type", "平台")],
    },
    "LIVE_SESSION": {
        "table": "ims_live_session",
        "kind": "ims",
        "columns": [("session_code", "场次编号"), ("topic", "主题"), ("platform", "平台"), ("account_no", "账号")],
    },
    "REALNAME": {
        "table": "oa_realname",
        "kind": "ops",
        "columns": [("real_name", "姓名"), ("status", "状态")],
    },
    "CONTENT_METRIC": {
        "table": "oa_internal_content",
        "kind": "ops",
        "columns": [("title", "标题"), ("play_count", "播放量")],
    },
}
_SEED_ALIAS = {
    "ip_group": "IP_GROUP",
    "IP_GROUP": "IP_GROUP",
    "platform_account": "PLATFORM_ACCOUNT",
    "PLATFORM_ACCOUNT": "PLATFORM_ACCOUNT",
    "ACCOUNT": "PLATFORM_ACCOUNT",
    "account": "PLATFORM_ACCOUNT",
    "live_session": "LIVE_SESSION",
    "LIVE_SESSION": "LIVE_SESSION",
    "SESSION": "LIVE_SESSION",
    "session": "LIVE_SESSION",
    "realname": "REALNAME",
    "REALNAME": "REALNAME",
    "PERSON": "REALNAME",
    "person": "REALNAME",
    "COST": "CONTENT_METRIC",
    "cost": "CONTENT_METRIC",
    "CONTENT_METRIC": "CONTENT_METRIC",
}


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_template_code(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(QueryTemplate).where(
            QueryTemplate.deleted == 0, QueryTemplate.tenant_id == tenant_id
        )
    )
    return f"QT-TPL-{int(count or 0) + 1:04d}"


def template_vo(row: QueryTemplate, names: dict[int, str]) -> dict:
    payload = row.payload_json if isinstance(row.payload_json, dict) else {}
    menu_title = str(payload.get("menuTitle") or "")
    if row.menu_seed:
        menu_label = "已挂 L3 数据分析"
    else:
        menu_label = ""
    return {
        "templateCode": row.template_code,
        "name": row.name,
        "mode": row.mode,
        "status": row.status,
        "menuSeed": bool(row.menu_seed),
        "menuRoute": row.menu_route or "",
        "menuTitle": menu_title or (row.name if row.menu_seed else ""),
        "menuPathLabel": menu_label or ("未挂菜单" if row.status == "PUBLISHED" else "—"),
        "permCode": row.perm_code or "",
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id, ""),
        "desc": row.desc or "",
        "updatedAt": iso(row.updated_at),
    }


def seed_templates(db: Session, tenant_id: int, owner_id: int) -> None:
    exists = db.scalar(
        select(func.count()).select_from(QueryTemplate).where(
            QueryTemplate.deleted == 0, QueryTemplate.tenant_id == tenant_id
        )
    )
    if exists:
        return
    now = utcnow()
    samples = [
        {
            "template_code": "QT-TPL-0001",
            "name": "IP 组周产出（标准）",
            "mode": "DRILL",
            "status": "PUBLISHED",
            "desc": "下钻 L0→L1 占位",
            "payload_json": {"levels": [{"levelIndex": 0, "label": "IP 组", "entityCode": "ip_group"}]},
        },
        {
            "template_code": "QT-TPL-0002",
            "name": "IP 组→场次下钻",
            "mode": "DRILL",
            "status": "DRAFT",
            "payload_json": {"levels": []},
        },
        {
            "template_code": "QT-TPL-0003",
            "name": "实名人成本 TRACE",
            "mode": "TRACE",
            "status": "DRAFT",
            "payload_json": {"pathSteps": [{"entity": "PERSON"}, {"entity": "SESSION"}]},
        },
        {
            "template_code": "QT-TPL-0004",
            "name": "财务穿透 · 场次成本",
            "mode": "TRACE",
            "status": "PUBLISHED",
            "menu_seed": 1,
            "menu_route": "/ims/analysis/query-tool/run/QT-TPL-0004",
            "desc": "挂数据分析 L3",
            "payload_json": {"pathSteps": [{"entity": "SESSION"}, {"entity": "COST"}]},
        },
    ]
    for item in samples:
        row = QueryTemplate(
            template_code=item["template_code"],
            name=item["name"],
            mode=item["mode"],
            status=item["status"],
            menu_seed=int(item.get("menu_seed") or 0),
            menu_route=item.get("menu_route") or "",
            desc=item.get("desc") or "",
            payload_json=item.get("payload_json") or {},
            owner_user_id=owner_id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.flush()


def get_template(db: Session, tenant_id: int, template_code: str) -> QueryTemplate | None:
    return db.scalar(
        select(QueryTemplate).where(
            QueryTemplate.deleted == 0,
            QueryTemplate.tenant_id == tenant_id,
            QueryTemplate.template_code == template_code.strip(),
        )
    )


@router.get("/template/page")
def template_page(
    keyword: str | None = None,
    status: str | None = None,
    mode: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_templates(db, tenant_id, actor.id)
    q = select(QueryTemplate).where(QueryTemplate.deleted == 0, QueryTemplate.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((QueryTemplate.name.like(kw)) | (QueryTemplate.template_code.like(kw)))
    if status:
        st = status.strip().upper()
        if st in STATUSES:
            q = q.where(QueryTemplate.status == st)
    if mode:
        md = mode.strip().upper()
        if md in MODES:
            q = q.where(QueryTemplate.mode == md)
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(QueryTemplate.updated_at.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.owner_user_id for r in rows])
    return paged([template_vo(r, names) for r in rows], total, page_no, size)


@router.get("/template/{template_code}")
def template_detail(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    names = user_names(db, [row.owner_user_id])
    data = template_vo(row, names)
    data["payloadJson"] = row.payload_json if isinstance(row.payload_json, dict) else {}
    return ok(data)


def payload_error(mode: str, payload: dict) -> str:
    if mode == "DRILL":
        levels = payload.get("levels") or []
        if not isinstance(levels, list):
            return "下钻层级无效"
        if len(levels) > 5:
            return "分级下钻最多 5 层"
    if mode == "TRACE":
        steps = payload.get("pathSteps") or []
        if not isinstance(steps, list):
            return "穿透步骤无效"
        if len(steps) > 6:
            return "逐级穿透最多 6 步"
    return ""


@router.post("/template")
def template_create(
    body: TemplateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = body.name.strip()
    if not name:
        return fail(1001, "模板名称必填")
    mode = body.mode.strip().upper()
    if mode not in MODES:
        return fail(1001, "模式无效")
    if mode == "FLAT":
        return fail(1001, "平铺查询请使用自定义查询")
    err = payload_error(mode, body.payloadJson or {})
    if err:
        return fail(1001, err)
    tenant_id = tenant_of(actor)
    now = utcnow()
    row = QueryTemplate(
        template_code=next_template_code(db, tenant_id),
        name=name,
        mode=mode,
        status="DRAFT",
        desc=body.desc.strip(),
        payload_json=body.payloadJson or {},
        owner_user_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.put("/template/{template_code}")
def template_update(
    template_code: str,
    body: TemplateUpdateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    if body.name is not None:
        name = body.name.strip()
        if not name:
            return fail(1001, "模板名称必填")
        row.name = name
    if body.desc is not None:
        row.desc = body.desc.strip()
    if body.payloadJson is not None:
        err = payload_error(row.mode, body.payloadJson)
        if err:
            return fail(1001, err)
        row.payload_json = body.payloadJson
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.post("/template/{template_code}/publish")
def template_publish(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.post("/template/{template_code}/unpublish")
def template_unpublish(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    row.status = "DRAFT"
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.delete("/template/{template_code}")
def template_delete(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    if row.menu_seed:
        return fail(1265, "模板已挂菜单，请先撤销侧栏")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok({"templateCode": template_code})


def fetch_seed_level(
    ims: Session,
    ops: Session,
    entity_code: str,
    tenant_id: int,
    *,
    entry_id: int | None = None,
    keyword: str = "",
) -> dict:
    spec = _SEED_SOURCES.get(_SEED_ALIAS.get(entity_code.strip(), ""))
    if spec is None:
        return {"entityCode": entity_code, "columns": [], "rows": []}
    columns = [{"key": col, "label": label} for col, label in spec["columns"]]
    select_sql = ", ".join(f"`{col}` AS `{col}`" for col, _label in spec["columns"])
    sql = f"SELECT {select_sql} FROM `{spec['table']}` WHERE deleted = 0 AND tenant_id = :tenant_id"
    params: dict = {"tenant_id": tenant_id}
    if entry_id is not None:
        sql += " AND id = :entry_id"
        params["entry_id"] = entry_id
    if keyword:
        probe = spec["columns"][0][0]
        sql += f" AND `{probe}` LIKE :kw"
        params["kw"] = f"%{keyword}%"
    sql += " ORDER BY id DESC LIMIT 100"
    db = ops if spec["kind"] == "ops" else ims
    fetched = db.execute(text(sql), params).mappings().all()
    rows = [{col: item.get(col) for col, _label in spec["columns"]} for item in fetched]
    return {"entityCode": entity_code, "columns": columns, "rows": rows}


def _entry_id(runtime: dict) -> int | None:
    raw = runtime.get("entryId")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class MenuSeedBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateCode: str
    menuTitle: str = ""
    parentMenuCode: str = "ims:analysis:query-tool-group"
    sortOrder: int = 0
    permCode: str = ""


@router.post("/menu-seed")
def menu_seed_create(
    body: MenuSeedBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if body.parentMenuCode.strip() != "ims:analysis:query-tool-group":
        return fail(1001, "只能挂到数据分析")
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, body.templateCode)
    if row is None:
        return fail(1263, "查询模板不存在")
    if row.status != "PUBLISHED":
        return fail(1001, "仅已发布模板可挂到侧栏")
    title = (body.menuTitle or row.name).strip()
    if not title:
        return fail(1001, "请填写菜单标题")
    if len(title) > 16:
        return fail(1001, "菜单标题不超过 16 字")
    payload = dict(row.payload_json) if isinstance(row.payload_json, dict) else {}
    payload["menuTitle"] = title
    row.payload_json = payload
    flag_modified(row, "payload_json")
    row.menu_seed = 1
    row.menu_route = f"/ims/analysis/query-tool/run/{row.template_code}"
    row.perm_code = (body.permCode or f"ims:analysis:qt:run:{row.template_code}").strip()
    row.updated_at = utcnow()
    return ok({"menuId": row.id, "routePath": row.menu_route})


@router.delete("/menu-seed/{template_code}")
def menu_seed_delete(
    template_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = get_template(db, tenant_id, template_code)
    if row is None:
        return fail(1263, "查询模板不存在")
    payload = dict(row.payload_json) if isinstance(row.payload_json, dict) else {}
    payload.pop("menuTitle", None)
    row.payload_json = payload
    flag_modified(row, "payload_json")
    row.menu_seed = 0
    row.menu_route = ""
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(template_vo(row, names))


@router.post("/run")
def query_run(
    body: RunBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    mode = body.mode.strip().upper()
    if mode not in {"DRILL", "TRACE"}:
        return fail(1001, "mode 无效")
    tenant_id = tenant_of(actor)
    template = None
    payload: dict = {}
    if body.templateCode:
        template = get_template(db, tenant_id, body.templateCode)
        if template is None or template.status != "PUBLISHED":
            return fail(1263, "查询模板不存在或未发布")
        mode = template.mode if template.mode in {"DRILL", "TRACE"} else mode
        payload = template.payload_json if isinstance(template.payload_json, dict) else {}
    elif isinstance(body.inlineTemplate, dict):
        inline_mode = str(body.inlineTemplate.get("mode") or mode).strip().upper()
        if inline_mode not in {"DRILL", "TRACE"}:
            return fail(1001, "mode 无效")
        mode = inline_mode
        raw_payload = body.inlineTemplate.get("payloadJson")
        payload = raw_payload if isinstance(raw_payload, dict) else {}
    runtime = body.runtime if isinstance(body.runtime, dict) else {}
    entry_id = _entry_id(runtime)
    keyword = str(runtime.get("keyword") or "").strip()[:64]
    t0 = time.perf_counter()
    levels: list[dict] = []
    if mode == "TRACE":
        steps = payload.get("pathSteps") if isinstance(payload.get("pathSteps"), list) else []
        if len(steps) < 1:
            steps = [{"entity": "PERSON"}, {"entity": "SESSION"}]
        root = str(payload.get("rootEntity") or (steps[0].get("entity") if steps else "PERSON"))
        for index, step in enumerate(steps[:6]):
            entity = str((step or {}).get("entity") or "PERSON")
            level = fetch_seed_level(
                db, ops, entity, tenant_id, entry_id=entry_id if index == 0 else None, keyword=keyword if index == 0 else ""
            )
            level["levelIndex"] = index
            level["label"] = entity
            levels.append(level)
        breadcrumbs = [root]
        root_entity = root
    else:
        raw_levels = payload.get("levels") if isinstance(payload.get("levels"), list) else []
        if not raw_levels:
            raw_levels = [{"levelIndex": 0, "label": "IP组", "entityCode": "IP_GROUP"}]
        root_entity = str(payload.get("rootEntity") or raw_levels[0].get("entityCode") or "IP_GROUP")
        for index, item in enumerate(raw_levels[:5]):
            entity = str((item or {}).get("entityCode") or "IP_GROUP")
            level = fetch_seed_level(
                db, ops, entity, tenant_id, entry_id=entry_id if index == 0 else None, keyword=keyword if index == 0 else ""
            )
            level["levelIndex"] = index
            level["label"] = str((item or {}).get("label") or entity)
            level["entityCode"] = entity
            levels.append(level)
        breadcrumbs = [levels[0]["label"]] if levels else ["IP组"]
    active = levels[0] if levels else {"columns": [], "rows": [], "label": ""}
    return ok(
        {
            "columns": active.get("columns") or [],
            "rows": active.get("rows") or [],
            "levels": levels,
            "levelState": {
                "activeLevel": 0,
                "breadcrumbs": breadcrumbs,
                "currentLevel": active.get("label") or "",
                "rootEntity": root_entity,
            },
            "queryCostMs": int((time.perf_counter() - t0) * 1000),
            "queryMode": "SYNC",
            "mode": mode,
            "templateCode": template.template_code if template else None,
        }
    )
