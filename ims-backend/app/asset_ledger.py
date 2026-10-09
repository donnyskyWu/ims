"""ASSET 台账生命周期（#63 · E2E-S5-02）：登记 → 领用 → 使用 → 归还 → 报废。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import check_date, check_enum, count_of, page_args, tenant_of, user_names
from app.models import AssetBind, AssetLedger, AssetLifecycleEvent, User

router = APIRouter()

class LedgerBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    assetCode: str = ""
    assetName: str = ""
    assetType: str = "OFFICE"
    spec: str = ""
    purchaseDate: str = ""
    realnameId: int | None = None
    parentAssetCode: str = ""
    accountId: int | None = None
    accountNo: str = ""
    sessionCode: str = ""
    bindType: str = "HOLD"


class CheckoutBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ownerUserId: int | None = None
    purpose: str = ""


class RemarkBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remark: str = ""


def _missing(db: Session, actor: User, asset_id: int):
    row = db.get(AssetLedger, asset_id)
    if row is None or row.deleted:
        return None, fail(1011, "资产不存在")
    if (row.tenant_id or 0) != tenant_of(actor):
        return None, fail(1504, "资源不可用")
    return row, None


_BLOCKED = {
    ("SCRAPPED", "checkout"): "已报废，不能再领用",
    ("SCRAPPED", "use"): "已报废，不能再使用",
    ("SCRAPPED", "return"): "已报废，不能归还",
    ("SCRAPPED", "scrap"): "已报废，不能再次报废",
    ("RETURNED", "checkout"): "已归还，不能再领用",
    ("RETURNED", "use"): "已归还，不能再使用",
    ("RETURNED", "return"): "已归还，不能再次归还",
    ("PENDING_REVIEW", "use"): "尚未领用，不能使用",
    ("PENDING_REVIEW", "return"): "尚未领用，不能归还",
    ("PENDING_REVIEW", "scrap"): "须先归还再报废",
    ("IN_USE", "scrap"): "须先归还再报废",
}


def _blocked(status: str, action: str):
    return fail(1015, _BLOCKED.get((status, action), "资产状态流转非法"))


def _check_owner(db: Session, actor: User, owner_id: int | None):
    if not owner_id:
        return fail(1001, "责任人必填")
    user = db.get(User, owner_id)
    if user is None or user.deleted:
        return fail(1500, "责任人不存在")
    if (user.tenant_id or 0) != tenant_of(actor):
        return fail(1504, "资源不可用")
    if user.status != "ENABLED":
        return fail(1501, "责任人已停用")
    return None


def _events(db: Session, asset_id: int) -> list[AssetLifecycleEvent]:
    stmt = (
        select(AssetLifecycleEvent)
        .where(AssetLifecycleEvent.asset_id == asset_id, AssetLifecycleEvent.deleted == 0)
        .order_by(AssetLifecycleEvent.id)
    )
    return list(db.scalars(stmt).all())


def _event_vo(row: AssetLifecycleEvent, names: dict[int, str]) -> dict:
    created = row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else ""
    return {
        "id": row.id,
        "eventType": row.event_type,
        "fromStatus": row.from_status,
        "toStatus": row.to_status,
        "actorUserId": row.actor_user_id,
        "actorName": names.get(row.actor_user_id or 0, ""),
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id or 0, "") if row.owner_user_id else "",
        "remark": row.remark,
        "createdAt": created,
    }


def ledger_vo(
    row: AssetLedger,
    names: dict[int, str],
    timeline: list[dict] | None = None,
    bind_count: int = 0,
) -> dict:
    count = int(bind_count or 0)
    owner_id = int(row.owner_user_id or 0)
    data = {
        "id": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "spec": row.spec,
        "status": row.status,
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(owner_id, "") if owner_id else "",
        "purchaseDate": row.purchase_date,
        "purchaseBatchNo": row.purchase_batch_no or "",
        "bindCount": count,
        "linkGap": count <= 0 or owner_id <= 0,
        "used": bool(row.used_at),
    }
    if timeline is not None:
        data["timeline"] = timeline
    return data


def _detail(db: Session, row: AssetLedger) -> dict:
    events = _events(db, row.id)
    ids = {row.owner_user_id} if row.owner_user_id else set()
    for event in events:
        if event.actor_user_id:
            ids.add(event.actor_user_id)
        if event.owner_user_id:
            ids.add(event.owner_user_id)
    names = user_names(db, ids)
    timeline = [_event_vo(event, names) for event in events]
    data = ledger_vo(row, names, timeline, _bind_counts(db, [row.id]).get(row.id, 0))
    from app.asset_penetrate import holders_of

    data["holders"] = holders_of(db, row)
    return data


def _add_event(
    db: Session,
    row: AssetLedger,
    actor: User,
    event_type: str,
    from_status: str,
    to_status: str,
    remark: str,
    owner_id: int | None,
) -> None:
    db.add(
        AssetLifecycleEvent(
            asset_id=row.id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor.id,
            owner_user_id=owner_id,
            remark=(remark or "")[:256],
            deleted=0,
            tenant_id=tenant_of(actor),
            created_at=utcnow(),
        )
    )


LEDGER_EXPORT_LIMIT = 2000
LEDGER_STATUS_LABEL = {
    "PENDING_REVIEW": "待审核",
    "IN_USE": "在用",
    "RETURNED": "已归还",
    "SCRAPPED": "已报废",
}
LEDGER_TYPE_LABEL = {
    "OFFICE": "办公设备",
    "LIVE": "直播设备",
    "SHOOT": "拍摄设备",
    "DIGITAL": "数码设备",
}


def _bind_counts(db: Session, asset_ids: list[int]) -> dict[int, int]:
    if not asset_ids:
        return {}
    stmt = (
        select(AssetBind.asset_id, func.count(AssetBind.id))
        .where(
            AssetBind.asset_id.in_(asset_ids),
            AssetBind.deleted == 0,
            AssetBind.bind_status == "ACTIVE",
            AssetBind.account_id > 0,
        )
        .group_by(AssetBind.asset_id)
    )
    return {int(asset_id): int(count) for asset_id, count in db.execute(stmt).all()}


def _missing_active_bind():
    active = (
        select(AssetBind.id)
        .where(
            AssetBind.asset_id == AssetLedger.id,
            AssetBind.deleted == 0,
            AssetBind.bind_status == "ACTIVE",
            AssetBind.account_id > 0,
        )
        .correlate(AssetLedger)
        .exists()
    )
    return ~active


def _link_gap_clause():
    return or_(
        AssetLedger.owner_user_id.is_(None),
        AssetLedger.owner_user_id == 0,
        _missing_active_bind(),
    )


def _filtered_ledger(
    actor: User,
    asset_type: str = "",
    asset_types: list[str] | None = None,
    asset_code: str = "",
    keyword: str = "",
    status: str = "",
    owner_user_id: int = 0,
    unassigned: bool = False,
):
    stmt = select(AssetLedger).where(AssetLedger.deleted == 0, AssetLedger.tenant_id == tenant_of(actor))
    if asset_types:
        stmt = stmt.where(AssetLedger.asset_type.in_(asset_types))
    elif asset_type:
        stmt = stmt.where(AssetLedger.asset_type == asset_type)
    code = asset_code.strip()
    if code:
        stmt = stmt.where(AssetLedger.asset_code.like(f"%{code}%"))
    text = keyword.strip()
    if text:
        like = f"%{text}%"
        stmt = stmt.where(or_(AssetLedger.asset_code.like(like), AssetLedger.asset_name.like(like)))
    if status:
        stmt = stmt.where(AssetLedger.status == status)
    if owner_user_id > 0:
        stmt = stmt.where(AssetLedger.owner_user_id == owner_user_id)
    elif unassigned:
        stmt = stmt.where(or_(AssetLedger.owner_user_id.is_(None), AssetLedger.owner_user_id == 0))
    return stmt


def _ledger_rows(
    db: Session,
    actor: User,
    page_no: int,
    page_size: int,
    asset_type: str = "",
    asset_types: list[str] | None = None,
    asset_code: str = "",
    keyword: str = "",
    status: str = "",
    owner_user_id: int = 0,
    unassigned: bool = False,
    link_gap: bool = False,
    hard_limit: int | None = None,
):
    if owner_user_id < 0:
        return None, fail(1001, "责任人无效")
    stmt = _filtered_ledger(
        actor,
        asset_type=asset_type,
        asset_types=asset_types,
        asset_code=asset_code,
        keyword=keyword,
        status=status,
        owner_user_id=owner_user_id,
        unassigned=unassigned,
    )
    gap_total = count_of(db, stmt.where(_link_gap_clause()))
    if link_gap:
        stmt = stmt.where(_link_gap_clause())
    total = count_of(db, stmt)
    if hard_limit:
        number, size = 1, hard_limit
    else:
        number, size = page_args(page_no, page_size)
    rows = db.scalars(stmt.order_by(AssetLedger.id.desc()).offset((number - 1) * size).limit(size)).all()
    return (rows, total, gap_total, number, size), None


def _vo_list(db: Session, rows: list[AssetLedger]) -> list[dict]:
    names = user_names(db, {row.owner_user_id for row in rows if row.owner_user_id})
    counts = _bind_counts(db, [row.id for row in rows])
    return [ledger_vo(row, names, bind_count=counts.get(row.id, 0)) for row in rows]


def list_ledger(
    db: Session,
    actor: User,
    page_no: int,
    page_size: int,
    asset_type: str = "",
    asset_types: list[str] | None = None,
    asset_code: str = "",
    keyword: str = "",
    status: str = "",
    owner_user_id: int = 0,
    unassigned: bool = False,
    link_gap: bool = False,
):
    found, error = _ledger_rows(
        db,
        actor,
        page_no,
        page_size,
        asset_type=asset_type,
        asset_types=asset_types,
        asset_code=asset_code,
        keyword=keyword,
        status=status,
        owner_user_id=owner_user_id,
        unassigned=unassigned,
        link_gap=link_gap,
    )
    if error:
        return error
    rows, total, gap_total, number, size = found
    return ok(
        {
            "list": _vo_list(db, rows),
            "total": total,
            "linkGapTotal": gap_total,
            "pageNo": number,
            "pageSize": size,
        }
    )


def _code_taken(db: Session, actor: User, code: str) -> bool:
    stmt = select(AssetLedger.id).where(
        AssetLedger.deleted == 0,
        AssetLedger.tenant_id == tenant_of(actor),
        AssetLedger.asset_code == code,
    )
    return db.scalar(stmt) is not None


def _type_args(asset_type: str) -> tuple[str, list[str] | None]:
    if asset_type == "LIVE,SHOOT":
        return "", ["LIVE", "SHOOT"]
    return asset_type, None


def _owner_flags(owner_user_id: int, unassigned: int) -> tuple[int, bool]:
    return owner_user_id, bool(unassigned) and owner_user_id <= 0


@router.get("/asset/ledger/page")
def ledger_page(
    pageNo: int = 1,
    pageSize: int = 10,
    assetCode: str = "",
    assetType: str = "",
    status: str = "",
    keyword: str = "",
    ownerUserId: int = 0,
    unassigned: int = 0,
    linkGap: int = 0,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    one, types = _type_args(assetType)
    owner_id, only_unassigned = _owner_flags(ownerUserId, unassigned)
    return list_ledger(
        db,
        actor,
        pageNo,
        pageSize,
        asset_type=one,
        asset_types=types,
        asset_code=assetCode,
        keyword=keyword,
        status=status,
        owner_user_id=owner_id,
        unassigned=only_unassigned,
        link_gap=bool(linkGap),
    )


def ledger_matrix(items: list[dict]) -> list[list[str]]:
    rows = [["资产编号", "名称", "类型", "规格", "状态", "责任人", "绑定账号数", "待补关联", "采购日期"]]
    for item in items:
        rows.append(
            [
                item.get("assetCode") or "",
                item.get("assetName") or "",
                LEDGER_TYPE_LABEL.get(item.get("assetType") or "", item.get("assetType") or ""),
                item.get("spec") or "",
                LEDGER_STATUS_LABEL.get(item.get("status") or "", item.get("status") or ""),
                item.get("ownerName") or "未分配",
                str(item.get("bindCount") or 0),
                "待补关联" if item.get("linkGap") else "",
                item.get("purchaseDate") or "",
            ]
        )
    return rows


def _csv_bytes(rows: list[list[str]]) -> bytes:
    import csv
    from io import StringIO

    buf = StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


@router.get("/asset/ledger/export/file")
def ledger_export_file(token: str, actor: User = Depends(current_user)):
    from app.asset_export import _file_response

    return _file_response(token, actor)


@router.get("/asset/ledger/export")
def ledger_export(
    assetCode: str = "",
    assetType: str = "",
    status: str = "",
    keyword: str = "",
    ownerUserId: int = 0,
    unassigned: int = 0,
    linkGap: int = 0,
    format: str = "XLSX",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    kind = (format or "XLSX").strip().upper()
    if kind not in {"XLSX", "CSV"}:
        return fail(1001, "导出格式仅支持 XLSX 或 CSV")
    one, types = _type_args(assetType)
    owner_id, only_unassigned = _owner_flags(ownerUserId, unassigned)
    found, error = _ledger_rows(
        db,
        actor,
        1,
        10,
        asset_type=one,
        asset_types=types,
        asset_code=assetCode,
        keyword=keyword,
        status=status,
        owner_user_id=owner_id,
        unassigned=only_unassigned,
        link_gap=bool(linkGap),
        hard_limit=LEDGER_EXPORT_LIMIT,
    )
    if error:
        return error
    rows, total, _gap_total, _number, _size = found
    items = _vo_list(db, rows)
    matrix = ledger_matrix(items)
    from app.asset_export import XLSX_MEDIA, build_xlsx, issue_export

    try:
        if kind == "CSV":
            body = _csv_bytes(matrix)
            media = "text/csv; charset=utf-8"
            filename = "asset_ledger.csv"
            file_kind = "csv"
        else:
            body = build_xlsx(matrix)
            media = XLSX_MEDIA
            filename = "asset_ledger.xlsx"
            file_kind = "xlsx"
    except Exception:
        return fail(5005, "报告生成失败，请稍后重试或联系管理员")
    message = "台账已按当前筛选导出"
    if total > len(items):
        message = f"台账已按当前筛选导出前 {len(items)} 条，共 {total} 条"
    payload = issue_export(actor.id, body, media, filename, file_kind, route="ledger", message=message)
    if payload is None:
        return fail(5005, "报告生成失败，请稍后重试或联系管理员")
    payload["total"] = total
    payload["exported"] = len(items)
    return ok(payload)


@router.get("/asset/ledger/{asset_id}")
def ledger_detail(
    asset_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row, error = _missing(db, actor, asset_id)
    if error:
        return error
    return ok(_detail(db, row))


@router.post("/asset/ledger")
def ledger_create(
    body: LedgerBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = (body.assetName or "").strip()
    if not name:
        return fail(1001, "资产名称必填")
    if len(name) > 128:
        return fail(1001, "资产名称过长")
    enum_error = check_enum(db, "dict_asset_type", body.assetType, True)
    if enum_error:
        return enum_error
    date_error = check_date(body.purchaseDate or None, False)
    if date_error:
        return date_error
    code = (body.assetCode or "").strip()
    if not code:
        code = "AS" + utcnow().strftime("%Y%m%d%H%M%S%f")
    if len(code) > 64:
        return fail(1001, "资产编号过长")
    if _code_taken(db, actor, code):
        return fail(1012, "资产编号已存在")
    from app.asset_penetrate import bind_person_id, resolve_bind

    person_id = bind_person_id(db, actor, body.realnameId, body.parentAssetCode)
    resolved, bind_error = resolve_bind(
        db,
        actor,
        body.accountId,
        body.accountNo,
        body.sessionCode,
        body.bindType,
        person_id,
    )
    if bind_error:
        return bind_error
    now = utcnow()
    row = AssetLedger(
        asset_code=code,
        asset_name=name,
        asset_type=body.assetType,
        spec=(body.spec or "")[:128],
        status="PENDING_REVIEW",
        owner_user_id=None,
        purchase_date=body.purchaseDate or "",
        subject_id=0,
        creator=actor.id,
        updater=actor.id,
        deleted=0,
        tenant_id=tenant_of(actor),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    remark = "登记入台账"
    if resolved:
        parts = []
        if resolved["accountNo"]:
            parts.append(f"绑定账号 {resolved['accountNo']}")
        if resolved["sessionCode"]:
            parts.append(f"绑定场次 {resolved['sessionCode']}")
        if parts:
            remark = "登记入台账 · " + " · ".join(parts)
    _add_event(db, row, actor, "REGISTER", "", "PENDING_REVIEW", remark, None)
    from app.asset_penetrate import link_hierarchy, write_bind

    link_error = link_hierarchy(db, actor, row, body.realnameId, body.parentAssetCode)
    if link_error:
        db.rollback()
        return link_error
    if resolved:
        write_bind(db, actor, row, resolved)
    db.flush()
    return ok(_detail(db, row))


@router.post("/asset/ledger/{asset_id}/checkout")
def ledger_checkout(
    asset_id: int,
    body: CheckoutBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row, error = _missing(db, actor, asset_id)
    if error:
        return error
    if row.status == "IN_USE":
        return fail(1012, "资产已在用")
    if row.status != "PENDING_REVIEW":
        return _blocked(row.status, "checkout")
    owner_error = _check_owner(db, actor, body.ownerUserId)
    if owner_error:
        return owner_error
    previous = row.status
    row.status = "IN_USE"
    row.owner_user_id = body.ownerUserId
    row.updater = actor.id
    row.updated_at = utcnow()
    _add_event(db, row, actor, "CHECKOUT", previous, "IN_USE", body.purpose or "领用", body.ownerUserId)
    db.flush()
    return ok(_detail(db, row))


@router.post("/asset/ledger/{asset_id}/use")
def ledger_use(
    asset_id: int,
    body: RemarkBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row, error = _missing(db, actor, asset_id)
    if error:
        return error
    if row.status != "IN_USE":
        return _blocked(row.status, "use")
    now = utcnow()
    if row.used_at is None:
        row.used_at = now
    row.updater = actor.id
    row.updated_at = now
    _add_event(db, row, actor, "USE", "IN_USE", "IN_USE", body.remark or "使用", row.owner_user_id)
    db.flush()
    return ok(_detail(db, row))


@router.post("/asset/ledger/{asset_id}/return")
def ledger_return(
    asset_id: int,
    body: RemarkBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row, error = _missing(db, actor, asset_id)
    if error:
        return error
    if row.status != "IN_USE":
        return _blocked(row.status, "return")
    if row.used_at is None:
        return fail(1015, "尚未登记使用，不能归还")
    previous_owner = row.owner_user_id
    row.status = "RETURNED"
    row.owner_user_id = None
    row.updater = actor.id
    row.updated_at = utcnow()
    _add_event(db, row, actor, "RETURN", "IN_USE", "RETURNED", body.remark or "归还", previous_owner)
    db.flush()
    return ok(_detail(db, row))


@router.post("/asset/ledger/{asset_id}/scrap")
def ledger_scrap(
    asset_id: int,
    body: RemarkBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row, error = _missing(db, actor, asset_id)
    if error:
        return error
    reason = (body.remark or "").strip()
    if not reason:
        return fail(1001, "报废原因必填")
    if row.status != "RETURNED":
        return _blocked(row.status, "scrap")
    row.status = "SCRAPPED"
    row.owner_user_id = None
    row.updater = actor.id
    row.updated_at = utcnow()
    _add_event(db, row, actor, "SCRAP", "RETURNED", "SCRAPPED", reason, None)
    db.flush()
    return ok(_detail(db, row))
