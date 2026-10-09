"""ACCT-003 离职归还单。未全部归还或转交时，关闭权限返回 1024（RET-R3 / BR-015）。"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import count_of, page_args, tenant_of
from app.models import (
    AccountReturnItem,
    AccountReturnOrder,
    AccountTimelineEvent,
    AssetLedger,
    CertArchive,
    Todo,
    User,
    WorkMessage,
)
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

router = APIRouter()

OPEN_STATUS = ("IN_PROGRESS", "EXCEPTION_SUSPENDED")
DONE_STATUS = {"RETURNED", "TRANSFERRED"}
ITEM_STATUS = {"RETURNED", "TRANSFERRED", "DISPUTED"}


class ReturnReject(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg


class GenerateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: int = 0
    dingtalkResignDate: str = ""
    resignDate: str = ""
    manual: bool = True


class ItemBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    itemStatus: str = ""
    transferToUserId: int | None = None
    remark: str = ""


def _clock(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def _parse_day(text: str) -> date:
    raw = (text or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ReturnReject(1001, "离职日期格式应为 yyyy-MM-dd") from None


def _order_stmt(actor: User):
    return select(AccountReturnOrder).where(
        AccountReturnOrder.deleted == 0,
        AccountReturnOrder.tenant_id == tenant_of(actor),
    )


def _items(db: Session, order_id: int) -> list[AccountReturnItem]:
    return list(
        db.scalars(
            select(AccountReturnItem)
            .where(AccountReturnItem.deleted == 0, AccountReturnItem.return_order_id == order_id)
            .order_by(AccountReturnItem.id)
        ).all()
    )


def _name(db: Session, user_id: int | None) -> str:
    if not user_id:
        return ""
    user = db.get(User, user_id)
    if user is None:
        return ""
    return user.nickname or user.username


def _progress(items: list[AccountReturnItem]) -> dict:
    done = sum(1 for item in items if item.item_status in DONE_STATUS)
    disputed = sum(1 for item in items if item.item_status == "DISPUTED")
    return {"total": len(items), "done": done, "disputed": disputed}


def _overdue(order: AccountReturnOrder, today: date) -> tuple[bool, int]:
    if order.status == "CLOSED" or not order.resign_date:
        return False, 0
    try:
        start = date.fromisoformat(order.resign_date)
    except ValueError:
        return False, 0
    due = start + timedelta(days=7)
    if today < due:
        return False, 0
    return True, max((today - due).days, 0)


def _item_vo(db: Session, item: AccountReturnItem) -> dict:
    return {
        "id": item.id,
        "returnOrderId": item.return_order_id,
        "itemType": item.item_type,
        "itemId": item.item_ref_id,
        "itemSnapshot": item.item_snapshot,
        "itemLabel": item.item_snapshot,
        "itemStatus": item.item_status,
        "handlerUserId": item.handler_user_id,
        "handlerName": _name(db, item.handler_user_id),
        "transferToUserId": item.transfer_to_user_id,
        "remark": item.remark or "",
    }


def _order_vo(db: Session, order: AccountReturnOrder, with_items: bool, today: date | None = None) -> dict:
    current = today or utcnow().date()
    items = _items(db, order.id)
    late, late_days = _overdue(order, current)
    payload = {
        "id": order.id,
        "returnNo": order.return_no,
        "userId": order.user_id,
        "userNickname": _name(db, order.user_id),
        "userName": _name(db, order.user_id),
        "dingtalkResignDate": order.resign_date,
        "resignDate": order.resign_date,
        "status": order.status,
        "manual": bool(order.manual),
        "itemCount": len(items),
        "progress": _progress(items),
        "overdue": late,
        "overdueDays": late_days,
        "closedAt": _clock(order.closed_at) or None,
        "createdAt": _clock(order.created_at),
    }
    if with_items:
        payload["items"] = [_item_vo(db, item) for item in items]
    return payload


def permission_close_blocked(db: Session, user_id: int) -> bool:
    row = db.scalar(
        select(AccountReturnOrder.id).where(
            AccountReturnOrder.deleted == 0,
            AccountReturnOrder.user_id == user_id,
            AccountReturnOrder.status.in_(OPEN_STATUS),
        )
    )
    return row is not None


def _open_order(db: Session, actor: User, user_id: int) -> AccountReturnOrder | None:
    return db.scalar(
        _order_stmt(actor)
        .where(AccountReturnOrder.user_id == user_id, AccountReturnOrder.status.in_(OPEN_STATUS))
        .order_by(AccountReturnOrder.id.desc())
    )


def _next_no(db: Session, day: date) -> str:
    prefix = "RT" + day.strftime("%Y%m%d")
    count = db.scalar(
        select(func.count()).select_from(AccountReturnOrder).where(AccountReturnOrder.return_no.like(prefix + "%"))
    ) or 0
    return f"{prefix}{int(count) + 1:04d}"


def _leaver(db: Session, actor: User, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted or (user.tenant_id or 0) != tenant_of(actor):
        raise ReturnReject(1500, "离职人不存在")
    return user


def _collect(db: Session, actor: User, user: User, order: AccountReturnOrder, stamped: datetime) -> None:
    tenant = tenant_of(actor)
    ops = ops_session()
    try:
        accounts = ops.scalars(
            select(PlatformAccount).where(
                PlatformAccount.deleted == 0,
                PlatformAccount.tenant_id == tenant,
                PlatformAccount.holder_user_id == user.id,
                PlatformAccount.status.in_(("IN_USE", "FROZEN")),
            )
        ).all()
        for account in accounts:
            if account.status == "IN_USE":
                account.status = "FROZEN"
                account.updated_at = stamped
            db.add(
                AccountReturnItem(
                    return_order_id=order.id,
                    item_type="ACCOUNT",
                    item_ref_id=account.id,
                    item_snapshot=(account.account_no or account.account_name or str(account.id))[:128],
                    item_status="PENDING",
                    tenant_id=tenant,
                    created_at=stamped,
                )
            )
            db.add(
                AccountTimelineEvent(
                    account_id=account.id,
                    event_type="FREEZE",
                    ref_no=order.return_no,
                    ref_id=order.id,
                    operator_user_id=actor.id,
                    snapshot_summary=f"离职归还冻结 · {order.return_no}",
                    tenant_id=tenant,
                    event_time=stamped,
                )
            )
        ops.commit()
    finally:
        ops.close()
    assets = db.scalars(
        select(AssetLedger).where(
            AssetLedger.deleted == 0,
            AssetLedger.tenant_id == tenant,
            AssetLedger.owner_user_id == user.id,
            AssetLedger.status == "IN_USE",
        )
    ).all()
    for asset in assets:
        db.add(
            AccountReturnItem(
                return_order_id=order.id,
                item_type="ASSET",
                item_ref_id=asset.id,
                item_snapshot=(asset.asset_code or asset.asset_name or str(asset.id))[:128],
                item_status="PENDING",
                tenant_id=tenant,
                created_at=stamped,
            )
        )
    nickname = (user.nickname or "").strip()
    cert_stmt = select(CertArchive).where(CertArchive.deleted == 0, CertArchive.tenant_id == tenant, CertArchive.status != "RECYCLED")
    if nickname:
        cert_stmt = cert_stmt.where(or_(CertArchive.holder_user_id == user.id, CertArchive.holder_name == nickname))
    else:
        cert_stmt = cert_stmt.where(CertArchive.holder_user_id == user.id)
    for cert in db.scalars(cert_stmt).all():
        label = f"{cert.cert_type or '证件'} {cert.holder_name or nickname}".strip()
        db.add(
            AccountReturnItem(
                return_order_id=order.id,
                item_type="CERT",
                item_ref_id=cert.id,
                item_snapshot=label[:128],
                item_status="PENDING",
                tenant_id=tenant,
                created_at=stamped,
            )
        )


def _notify_overdue(db: Session, order: AccountReturnOrder) -> None:
    exists = db.scalar(
        select(Todo).where(
            Todo.ref_type == "acct_return",
            Todo.ref_id == order.id,
            Todo.task_type == "return_overdue",
            Todo.status == "PENDING",
        )
    )
    if exists is not None:
        return
    admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0, User.status == "ENABLED"))
    if admin is None:
        return
    title = f"离职归还逾期：{order.return_no}"
    content = f"{_name(db, order.user_id)} 的归还单超过 7 天未闭环，已挂起并冻结"
    db.add(
        Todo(
            assignee_user_id=admin.id,
            task_type="return_overdue",
            ref_type="acct_return",
            ref_id=order.id,
            title=title[:128],
            content=content[:512],
            status="PENDING",
            tenant_id=order.tenant_id or 0,
            created_at=utcnow(),
        )
    )
    db.add(
        WorkMessage(
            user_id=admin.id,
            title=title[:128],
            content=content[:512],
            channel="IN_APP",
            read_flag=0,
            source_module="acct",
            ref_type="acct_return",
            ref_id=order.id,
            tenant_id=order.tenant_id or 0,
            created_at=utcnow(),
        )
    )


def _freeze_open_accounts(user_id: int, tenant: int, stamped: datetime) -> None:
    ops = ops_session()
    try:
        rows = ops.scalars(
            select(PlatformAccount).where(
                PlatformAccount.deleted == 0,
                PlatformAccount.tenant_id == tenant,
                PlatformAccount.holder_user_id == user_id,
                PlatformAccount.status == "IN_USE",
            )
        ).all()
        for row in rows:
            row.status = "FROZEN"
            row.updated_at = stamped
        ops.commit()
    finally:
        ops.close()


def sweep_overdue(db: Session, today: date | None = None) -> None:
    current = today or utcnow().date()
    rows = list(
        db.scalars(
            select(AccountReturnOrder).where(
                AccountReturnOrder.deleted == 0,
                AccountReturnOrder.status == "IN_PROGRESS",
            )
        ).all()
    )
    stamped = utcnow()
    for order in rows:
        late, _days = _overdue(order, current)
        if not late:
            continue
        order.status = "EXCEPTION_SUSPENDED"
        _freeze_open_accounts(order.user_id, order.tenant_id or 0, stamped)
        _notify_overdue(db, order)


def generate_return_order(db: Session, actor: User, user_id: int, resign_text: str, manual: bool) -> dict:
    user = _leaver(db, actor, user_id)
    day = _parse_day(resign_text)
    existing = _open_order(db, actor, user.id)
    if existing is not None:
        if manual:
            raise ReturnReject(1001, f"该离职人已有归还单 {existing.return_no}")
        return _order_vo(db, existing, True)
    stamped = utcnow()
    order = AccountReturnOrder(
        return_no=_next_no(db, day),
        user_id=user.id,
        resign_date=day.isoformat(),
        status="IN_PROGRESS",
        manual=1 if manual else 0,
        tenant_id=tenant_of(actor),
        created_at=stamped,
    )
    db.add(order)
    db.flush()
    if user.status == "ENABLED":
        user.status = "FROZEN"
    _collect(db, actor, user, order, stamped)
    db.flush()
    return _order_vo(db, order, True)


def _load_order(db: Session, actor: User, order_id: int) -> AccountReturnOrder:
    row = db.get(AccountReturnOrder, order_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant_of(actor):
        raise ReturnReject(1504, "归还单不存在")
    return row


def _target_user(db: Session, actor: User, user_id: int, leaver_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted or (user.tenant_id or 0) != tenant_of(actor):
        raise ReturnReject(1500, "接收人不存在")
    if user.id == leaver_id:
        raise ReturnReject(1001, "不能转交给离职人本人")
    if user.status != "ENABLED":
        raise ReturnReject(1501, "接收人已停用")
    return user


def _apply_account(item: AccountReturnItem, status: str, holder_id: int | None) -> None:
    ops = ops_session()
    try:
        account = ops.get(PlatformAccount, item.item_ref_id)
        if account is None or account.deleted:
            raise ReturnReject(1504, "账号不存在")
        account.status = status
        if holder_id is not None:
            account.holder_user_id = holder_id
        elif status == "IN_POOL":
            account.holder_user_id = None
        account.updated_at = utcnow()
        ops.commit()
    finally:
        ops.close()


def _apply_effect(db: Session, actor: User, item: AccountReturnItem, status: str, target: User | None) -> None:
    if item.item_type == "ACCOUNT":
        if status == "RETURNED":
            _apply_account(item, "FROZEN", None)
        elif status == "TRANSFERRED" and target is not None:
            _apply_account(item, "IN_USE", target.id)
        return
    if item.item_type == "ASSET":
        asset = db.get(AssetLedger, item.item_ref_id)
        if asset is None or asset.deleted:
            raise ReturnReject(1504, "资产不存在")
        if status == "RETURNED":
            asset.status = "RETURNED"
            asset.owner_user_id = None
        elif status == "TRANSFERRED" and target is not None:
            asset.owner_user_id = target.id
            asset.status = "IN_USE"
        asset.updated_at = utcnow()
        return
    if item.item_type == "CERT":
        cert = db.get(CertArchive, item.item_ref_id)
        if cert is None or cert.deleted:
            raise ReturnReject(1504, "证件不存在")
        if status == "RETURNED":
            cert.status = "RECYCLED"
        elif status == "TRANSFERRED" and target is not None:
            cert.holder_user_id = target.id
            cert.holder_name = (target.nickname or target.username or "")[:64]
        cert.updated_at = utcnow()


def handle_item(db: Session, actor: User, item_id: int, status: str, transfer_to: int | None, remark: str) -> None:
    item = db.get(AccountReturnItem, item_id)
    if item is None or item.deleted or (item.tenant_id or 0) != tenant_of(actor):
        raise ReturnReject(1504, "归还项不存在")
    order = _load_order(db, actor, item.return_order_id)
    if order.status == "CLOSED":
        raise ReturnReject(1014, "归还单已闭环")
    target_status = (status or "").strip().upper()
    if target_status not in ITEM_STATUS:
        raise ReturnReject(1001, "归还项状态不正确")
    target = None
    text = (remark or "").strip()
    if target_status == "TRANSFERRED":
        if not transfer_to:
            raise ReturnReject(1001, "转交接收人必填")
        target = _target_user(db, actor, int(transfer_to), order.user_id)
    if target_status == "DISPUTED" and not text:
        raise ReturnReject(1001, "争议说明必填")
    if target_status != "DISPUTED":
        _apply_effect(db, actor, item, target_status, target)
    item.item_status = target_status
    item.handler_user_id = actor.id
    item.transfer_to_user_id = target.id if target is not None else None
    if text:
        item.remark = text[:512]
    db.flush()


def _release_accounts(db: Session, order: AccountReturnOrder) -> None:
    items = [item for item in _items(db, order.id) if item.item_type == "ACCOUNT" and item.item_status == "RETURNED"]
    if not items:
        return
    ops = ops_session()
    try:
        for item in items:
            account = ops.get(PlatformAccount, item.item_ref_id)
            if account is None or account.deleted:
                continue
            account.status = "IN_POOL"
            account.holder_user_id = None
            account.updated_at = utcnow()
        ops.commit()
    finally:
        ops.close()


def _finish_todos(db: Session, order: AccountReturnOrder) -> None:
    rows = db.scalars(
        select(Todo).where(
            Todo.status == "PENDING",
            or_(
                and_(Todo.ref_type == "org_resign", Todo.ref_id == order.user_id),
                and_(Todo.ref_type == "acct_return", Todo.ref_id == order.id),
            ),
        )
    ).all()
    for todo in rows:
        todo.status = "DONE"


def close_return_order(db: Session, actor: User, order_id: int) -> None:
    sweep_overdue(db)
    order = _load_order(db, actor, order_id)
    if order.status == "CLOSED":
        raise ReturnReject(1014, "归还单已闭环")
    items = _items(db, order.id)
    if any(item.item_status not in DONE_STATUS for item in items):
        raise ReturnReject(1024, "归还单未闭环，禁止关闭权限")
    user = db.get(User, order.user_id)
    _release_accounts(db, order)
    order.status = "CLOSED"
    order.closed_at = utcnow()
    if user is not None and not user.deleted:
        user.status = "DISABLED"
    _finish_todos(db, order)
    db.flush()


def _guard(action):
    try:
        return action()
    except ReturnReject as exc:
        return fail(exc.code, exc.msg)


@router.post("/account/return/generate")
def return_generate(body: GenerateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    text = (body.dingtalkResignDate or body.resignDate or "").strip()

    def run():
        if not body.userId:
            raise ReturnReject(1001, "离职人必填")
        data = generate_return_order(db, actor, int(body.userId), text, bool(body.manual))
        return ok(data)

    return _guard(run)


@router.get("/account/return/list")
def return_list(
    pageNo: int = 1,
    pageSize: int = 10,
    status: str = "",
    userId: int = 0,
    returnNo: str = "",
    timeFrom: str = "",
    timeTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    sweep_overdue(db)
    number, size = page_args(pageNo, pageSize)
    stmt = _order_stmt(actor)
    if status.strip():
        stmt = stmt.where(AccountReturnOrder.status == status.strip())
    if userId:
        stmt = stmt.where(AccountReturnOrder.user_id == userId)
    if returnNo.strip():
        stmt = stmt.where(AccountReturnOrder.return_no == returnNo.strip())
    if timeFrom.strip():
        stmt = stmt.where(AccountReturnOrder.resign_date >= timeFrom.strip())
    if timeTo.strip():
        stmt = stmt.where(AccountReturnOrder.resign_date <= timeTo.strip())
    total = count_of(db, stmt)
    rows = list(db.scalars(stmt.order_by(AccountReturnOrder.id.desc()).offset((number - 1) * size).limit(size)).all())
    today = utcnow().date()
    return ok({"list": [_order_vo(db, row, False, today) for row in rows], "total": total, "pageNo": number, "pageSize": size})


@router.get("/account/return/{order_id}")
def return_detail(order_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    sweep_overdue(db)

    def run():
        order = _load_order(db, actor, order_id)
        return ok(_order_vo(db, order, True))

    return _guard(run)


@router.put("/account/return/item/{item_id}")
def return_item(
    item_id: int,
    body: ItemBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    def run():
        handle_item(db, actor, item_id, body.itemStatus, body.transferToUserId, body.remark)
        return ok(None)

    return _guard(run)


@router.put("/account/return/{order_id}/close")
def return_close(order_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    def run():
        close_return_order(db, actor, order_id)
        return ok(None)

    return _guard(run)
