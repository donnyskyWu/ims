"""离职归还。闭环后账号保持冻结，由管理员解冻回池。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive, today
from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.session import get_session
from app.domains.account.model import AccountTransfer, ReturnItem, ReturnOrder
from app.domains.account.support import (
    account_row,
    dept_name,
    limit,
    log_event,
    page_slice,
    parse_day,
    remember,
    replay,
    require_active_user,
    require_resigned,
    save,
    stamp_no,
    text_of,
    token_of,
    user_brief,
    viewer_id,
    when,
)
from app.domains.device.flow import give_back, transfer as asset_transfer
from app.domains.device.model import AssetLedger
from app.domains.master.model import Cert, PlatformAccount, Realname
from app.domains.message.service import send_notify
from app.domains.todo.service import todo_create

_ORDER = {"IN_PROGRESS": "进行中", "CLOSED": "已闭环", "EXCEPTION_SUSPENDED": "异常挂起"}
_ITEM = {"PENDING": "待归还", "RETURNED": "已归还", "TRANSFERRED": "转交", "DISPUTED": "争议"}
_DONE = {"RETURNED", "TRANSFERRED"}


def page(page_query, params: dict) -> dict:
    rows = list(get_session().scalars(select(ReturnOrder).order_by(ReturnOrder.id.desc())))
    status = text_of(params, "status")
    if status:
        from app.domains.account.support import require_dict

        require_dict("dict_return_order_status", status, "status", "状态")
        rows = [row for row in rows if row.status == status]
    keyword = text_of(params, "keyword")
    if keyword:
        rows = [row for row in rows if keyword in row.return_no or keyword in user_brief(row.user_id)["name"]]
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def detail(ident: int) -> dict:
    return _view(_order(ident), full=True)


def generate(body: dict, *, manual: bool = True, event_user: int | None = None) -> dict:
    if manual:
        cached = replay(token_of(body))
        if cached:
            return cached
    user = require_resigned(event_user if event_user is not None else body.get("userId"))
    day = parse_day(body.get("resignDate"), "resignDate", required=manual, label="离职日") or today()
    existing = get_session().scalar(select(ReturnOrder).where(ReturnOrder.user_id == user.id, ReturnOrder.status == "IN_PROGRESS"))
    if existing is not None:
        if not manual:
            return _view(existing, full=True)
        raise BizError(1001, f"已有归还单 {existing.return_no}")
    order = ReturnOrder(
        return_no=stamp_no("RT", ReturnOrder.return_no),
        user_id=user.id,
        resign_date=day,
        status="IN_PROGRESS",
        manual=1 if manual else 0,
    )
    save(order)
    _collect(order, user.id)
    payload = _view(order, full=True)
    if manual:
        remember(token_of(body), payload)
    return payload


def on_resigned(payload: dict) -> None:
    user_id = payload.get("userId")
    if not user_id:
        return
    try:
        get_session()
    except RuntimeError:
        from app.core.context import system_context, use_context
        from app.db.session import session_scope

        with session_scope(commit=True):
            with use_context(system_context(1)):
                _resign(int(user_id))
        return
    _resign(int(user_id))


def _resign(user_id: int) -> None:
    if not _has_holdings(user_id):
        return
    try:
        generate({"userId": user_id, "resignDate": today().isoformat()}, manual=False, event_user=user_id)
    except BizError:
        return


def handle_item(item_id: int, body: dict) -> dict:
    item = get_session().get(ReturnItem, int(item_id))
    if item is None or int(item.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    order = _order(item.order_id)
    if order.status != "IN_PROGRESS":
        raise BizError(1023, "归还单状态非法")
    action = (text_of(body, "action") or "RETURN").upper()
    item.handler_user_id = viewer_id()
    if action == "DISPUTE":
        item.remark = limit(text_of(body, "remark"), "remark", "说明", 256, required=True)
        item.item_status = "DISPUTED"
    elif action == "TRANSFER":
        target = require_active_user(body.get("toUserId"), "toUserId", "接收人")
        item.transfer_to_user_id = target.id
        item.remark = limit(text_of(body, "remark"), "remark", "说明", 256)
        _transfer_item(item, target.id)
        if item.item_type != "ACCOUNT":
            item.item_status = "TRANSFERRED"
    elif action == "RETURN":
        _return_item(item)
        item.item_status = "RETURNED"
    else:
        from app.domains.account.support import one

        one("action", "请选择处理方式")
    save(item)
    return _view(order, full=True)


def close(ident: int) -> dict:
    order = _order(ident)
    if order.status != "IN_PROGRESS":
        raise BizError(1023, "归还单状态非法")
    items = _items(order.id)
    if any(item.item_status == "DISPUTED" or item.item_status not in _DONE for item in items):
        raise BizError(1024, "归还单未闭环，禁止关闭")
    order.status = "CLOSED"
    order.closed_at = now_naive()
    save(order)
    return _view(order, full=True)


def suspend(ident: int, body: dict) -> dict:
    order = _order(ident)
    action = (text_of(body, "action") or "SUSPEND").upper()
    if action == "RESUME":
        if order.status != "EXCEPTION_SUSPENDED":
            raise BizError(1023, "归还单状态非法")
        order.status = "IN_PROGRESS"
        save(order)
        return _view(order, full=True)
    if order.status != "IN_PROGRESS":
        raise BizError(1023, "归还单状态非法")
    order.suspend_reason = limit(text_of(body, "reason"), "reason", "挂起原因", 256, required=True)
    order.status = "EXCEPTION_SUSPENDED"
    save(order)
    return _view(order, full=True)


def overdue_scan() -> int:
    from datetime import timedelta

    session = get_session()
    rows = list(session.scalars(select(ReturnOrder).where(ReturnOrder.status == "IN_PROGRESS", ReturnOrder.escalated_at.is_(None))))
    sent = 0
    for order in rows:
        if order.resign_date + timedelta(days=7) > today():
            continue
        order.escalated_at = now_naive()
        from app.domains.todo.service import users_with_perm

        for receiver in users_with_perm("ims:account:return:handle"):
            send_notify(
                receiver,
                "归还逾期",
                f"归还单 {order.return_no} 已超过 7 天未闭环",
                "ACCT_RETURN_OVERDUE",
                f"return:{order.id}:{receiver}",
                route=f"/ims/account/return?id={order.id}",
                source_module="account",
            )
        todo_create(
            "ACCT_RETURN_OVERDUE",
            int(order.id),
            "RETURN",
            f"归还单 {order.return_no} 逾期未闭环",
            perm_code="ims:account:return:handle",
            route=f"/ims/account/return?id={order.id}",
            source_module="account",
        )
        sent += 1
    session.flush()
    return sent


def _has_holdings(user_id: int) -> bool:
    session = get_session()
    if session.scalar(select(PlatformAccount.id).where(PlatformAccount.owner_user_id == user_id, PlatformAccount.status != "CANCELLED")):
        return True
    if session.scalar(select(AssetLedger.id).where(AssetLedger.owner_user_id == user_id, AssetLedger.status != "SCRAPPED")):
        return True
    people = list(session.scalars(select(Realname.id).where(Realname.user_id == user_id)))
    if not people:
        return False
    return session.scalar(select(Cert.id).where(Cert.realname_id.in_(people), Cert.status != "RECYCLED")) is not None


def _collect(order: ReturnOrder, user_id: int) -> None:
    session = get_session()
    accounts = list(session.scalars(select(PlatformAccount).where(PlatformAccount.owner_user_id == user_id, PlatformAccount.status != "CANCELLED")))
    for account in accounts:
        if account.status == "IN_USE":
            account.status = "FROZEN"
            log_event(account.id, "FREEZE", "离职冻结", order.return_no)
            from app.domains.live.guards import on_account_status

            on_account_status(account.id, "FROZEN")
        _add_item(order, "ACCOUNT", account.id, {"accountNo": account.account_no, "nickname": account.nickname or account.name})
    assets = list(session.scalars(select(AssetLedger).where(AssetLedger.owner_user_id == user_id, AssetLedger.status != "SCRAPPED")))
    for asset in assets:
        _add_item(order, "ASSET", asset.id, {"assetCode": asset.asset_code, "assetName": asset.asset_name})
    people = list(session.scalars(select(Realname).where(Realname.user_id == user_id)))
    for person in people:
        certs = list(session.scalars(select(Cert).where(Cert.realname_id == person.id, Cert.status != "RECYCLED")))
        for cert in certs:
            _add_item(order, "CERT", cert.id, {"name": cert.name, "certType": cert.cert_type or ""})
    session.flush()


def _add_item(order: ReturnOrder, kind: str, item_id: int, snapshot: dict) -> None:
    row = ReturnItem(order_id=order.id, item_type=kind, item_id=int(item_id), item_snapshot=snapshot, item_status="PENDING")
    save(row)


def _return_item(item: ReturnItem) -> None:
    if item.item_type == "ACCOUNT":
        account = account_row(item.item_id)
        if account.status != "FROZEN":
            account.status = "FROZEN"
            from app.domains.live.guards import on_account_status

            on_account_status(account.id, "FROZEN")
        save(account)
        log_event(account.id, "RETURN", "归还", "", ref=f"/ims/account/return?id={item.order_id}")
        return
    if item.item_type == "ASSET":
        asset = get_session().get(AssetLedger, item.item_id)
        if asset is not None and asset.status == "IN_USE":
            give_back(asset.id, {"condition": "GOOD", "returnDate": today().isoformat(), "remark": "离职归还"})
        return
    if item.item_type == "CERT":
        cert = get_session().get(Cert, item.item_id)
        if cert is not None:
            cert.status = "RECYCLED"
            get_session().flush()


def _transfer_item(item: ReturnItem, user_id: int) -> None:
    if item.item_type == "ACCOUNT":
        account = account_row(item.item_id)
        if account.status == "FROZEN":
            account.status = "IN_USE"
            account.owner_user_id = account.owner_user_id or user_id
        row = AccountTransfer(
            transfer_no=stamp_no("TR", AccountTransfer.transfer_no),
            account_id=account.id,
            transfer_type="TRANSFER",
            from_user_id=account.owner_user_id,
            to_user_id=user_id,
            reason_type="PRE_RESIGN",
            remark="离职归还转交",
            status="PENDING_CONFIRM",
        )
        if account.owner_user_id is None:
            account.owner_user_id = user_id
            account.status = "IN_USE"
            row.status = "EFFECTIVE"
            row.effective_at = now_naive()
            item.item_status = "TRANSFERRED"
        save(account)
        save(row)
        item.transfer_id = row.id
        if row.status == "PENDING_CONFIRM":
            todo_create(
                "ACCT_TRANSFER",
                int(row.id),
                "CONFIRM",
                f"离职转交待确认 {row.transfer_no}",
                user_ids=[user_id],
                route=f"/ims/account/transfer?id={row.id}",
                source_module="account",
            )
        return
    if item.item_type == "ASSET":
        asset = get_session().get(AssetLedger, item.item_id)
        if asset is not None and asset.status == "IN_USE":
            asset_transfer(asset.id, {"userId": user_id, "reason": "RESIGN", "remark": "离职归还转交"})


def _order(ident: int) -> ReturnOrder:
    row = get_session().get(ReturnOrder, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    return row


def _items(order_id: int) -> list[ReturnItem]:
    return list(get_session().scalars(select(ReturnItem).where(ReturnItem.order_id == int(order_id)).order_by(ReturnItem.id.asc())))


def _view(row: ReturnOrder, full: bool = False) -> dict:
    items = _items(row.id)
    done = sum(1 for item in items if item.item_status in _DONE)
    person = user_brief(row.user_id)
    overdue = row.status == "IN_PROGRESS" and row.resign_date is not None and (today() - row.resign_date).days >= 7
    data = {
        "id": row.id,
        "returnNo": row.return_no,
        "userId": row.user_id,
        "userName": person["name"],
        "userResigned": person["resigned"],
        "deptName": dept_name(row.user_id),
        "resignDate": row.resign_date.isoformat() if row.resign_date else "",
        "status": row.status,
        "statusLabel": _ORDER.get(row.status, row.status),
        "progress": f"{done}/{len(items)}",
        "overdue": overdue or row.escalated_at is not None,
        "closedAt": when(row.closed_at),
        "manual": bool(row.manual),
        "suspendReason": row.suspend_reason or "",
    }
    if full:
        data["items"] = [
            {
                "id": item.id,
                "itemType": item.item_type,
                "itemId": item.item_id,
                "snapshot": item.item_snapshot or {},
                "itemStatus": item.item_status,
                "statusLabel": _ITEM.get(item.item_status, item.item_status),
                "remark": item.remark or "",
                "transferToUserId": item.transfer_to_user_id,
            }
            for item in items
        ]
    return data
