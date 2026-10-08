"""ASSET 台账生命周期（#63 · E2E-S5-02）：登记 → 领用 → 使用 → 归还 → 报废。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import check_date, check_enum, count_of, page_args, tenant_of, user_names
from app.models import AssetLedger, AssetLifecycleEvent, User

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


def ledger_vo(row: AssetLedger, names: dict[int, str], timeline: list[dict] | None = None) -> dict:
    data = {
        "id": row.id,
        "assetCode": row.asset_code,
        "assetName": row.asset_name,
        "assetType": row.asset_type,
        "spec": row.spec,
        "status": row.status,
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id or 0, "") if row.owner_user_id else "",
        "purchaseDate": row.purchase_date,
        "purchaseBatchNo": row.purchase_batch_no or "",
        "bindCount": 0,
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
    data = ledger_vo(row, names, timeline)
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
):
    number, size = page_args(page_no, page_size)
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
    total = count_of(db, stmt)
    rows = db.scalars(stmt.order_by(AssetLedger.id.desc()).offset((number - 1) * size).limit(size)).all()
    names = user_names(db, {row.owner_user_id for row in rows if row.owner_user_id})
    return ok(
        {
            "list": [ledger_vo(row, names) for row in rows],
            "total": total,
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


@router.get("/asset/ledger/page")
def ledger_page(
    pageNo: int = 1,
    pageSize: int = 10,
    assetCode: str = "",
    assetType: str = "",
    status: str = "",
    keyword: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    types = None
    one = assetType
    if assetType == "LIVE,SHOOT":
        types = ["LIVE", "SHOOT"]
        one = ""
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
    )


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
    _add_event(db, row, actor, "REGISTER", "", "PENDING_REVIEW", "登记入台账", None)
    from app.asset_penetrate import link_hierarchy

    link_error = link_hierarchy(db, actor, row, body.realnameId, body.parentAssetCode)
    if link_error:
        db.rollback()
        return link_error
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
        return fail(1015, "资产状态流转非法")
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
        return fail(1015, "资产状态流转非法")
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
        return fail(1015, "资产状态流转非法")
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
        return fail(1015, "须先归还再报废")
    row.status = "SCRAPPED"
    row.owner_user_id = None
    row.updater = actor.id
    row.updated_at = utcnow()
    _add_event(db, row, actor, "SCRAP", "RETURNED", "SCRAPPED", reason, None)
    db.flush()
    return ok(_detail(db, row))
