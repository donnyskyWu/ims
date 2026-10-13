"""流转、收回与解冻回池。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.session import get_session
from app.domains.account.model import AccountTransfer
from app.domains.account.support import (
    account_row,
    limit,
    log_event,
    owner_limit,
    page_slice,
    remember,
    replay,
    require_active_user,
    require_dict,
    save,
    stamp_no,
    text_of,
    token_of,
    user_brief,
    viewer_id,
    when,
)
from app.domains.device.ledger import add_event
from app.domains.device.model import AssetBind, AssetLedger
from app.domains.message.service import send_notify
from app.domains.resource.common import has_perm
from app.domains.todo.service import todo_create

_TYPE = {"TRANSFER": "流转", "RECALL": "收回"}
_STATUS = {"PENDING_CONFIRM": "待确认", "EFFECTIVE": "已生效", "REVOKED": "已撤销"}
_REASON = {
    "TRANSFER_POSITION": "岗位调动",
    "PRE_RESIGN": "离职前置",
    "VIOLATION": "违规",
    "BUSINESS_ADJUST": "业务调整",
}


def page(page_query, params: dict) -> dict:
    rows = _filtered(params)
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    kind = require_dict("dict_transfer_type", text_of(body, "transferType") or "TRANSFER", "transferType", "类型")
    from app.core.serialize import parse_api_id

    raw = body.get("accountId")
    if raw in (None, ""):
        from app.domains.account.support import one

        one("accountId", "请选择账号")
    account = account_row(int(parse_api_id(raw)))
    if account.status == "FROZEN":
        raise BizError(1022, "账号处于冻结态，不可领用")
    if account.status != "IN_USE":
        raise BizError(1023, "流转单状态非法")
    actor = viewer_id()
    if owner_limit() is not None and int(account.owner_user_id or 0) != actor:
        raise BizError(1008, "您无权查看该账号")
    if kind == "RECALL":
        return _recall(account, body)
    target = require_active_user(body.get("toUserId"), "toUserId", "新责任人")
    if int(target.id) == int(account.owner_user_id or 0):
        from app.domains.account.support import one

        one("toUserId", "新责任人不能与原责任人相同")
    reason = require_dict("dict_transfer_reason", text_of(body, "reasonType"), "reasonType", "原因")
    note = limit(text_of(body, "remark"), "remark", "交接说明", 512, required=True)
    row = AccountTransfer(
        transfer_no=stamp_no("TR", AccountTransfer.transfer_no),
        account_id=account.id,
        transfer_type="TRANSFER",
        from_user_id=account.owner_user_id,
        to_user_id=target.id,
        reason_type=reason,
        remark=note,
        status="PENDING_CONFIRM",
        sync_assets=1 if body.get("syncAssets") else 0,
    )
    save(row)
    send_notify(
        target.id,
        "账号流转待确认",
        f"账号 {account.account_no} 待您确认接收",
        "ACCT_TRANSFER",
        f"transfer:{row.id}",
        route=f"/ims/account/transfer?id={row.id}",
        source_module="account",
    )
    todo_create(
        "ACCT_TRANSFER",
        int(row.id),
        "CONFIRM",
        f"账号流转待确认 {row.transfer_no}",
        user_ids=[target.id],
        route=f"/ims/account/transfer?id={row.id}",
        source_module="account",
    )
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def confirm(ident: int, body: dict) -> dict:
    row = _row(ident)
    if row.status != "PENDING_CONFIRM" or row.transfer_type != "TRANSFER":
        raise BizError(1023, "流转单状态非法")
    if viewer_id() != int(row.to_user_id or 0):
        raise BizError(1008, "您无权查看该账号")
    accept = body.get("accept")
    if accept is None:
        accept = text_of(body, "action") != "REJECT"
    account = account_row(row.account_id)
    if accept:
        if account.status != "IN_USE":
            raise BizError(1023, "流转单状态非法")
        previous = account.owner_user_id
        account.owner_user_id = row.to_user_id
        row.status = "EFFECTIVE"
        row.effective_at = now_naive()
        save(account)
        save(row)
        if row.sync_assets:
            _sync_assets(account.id, previous, row.to_user_id)
        log_event(account.id, "TRANSFER", "流转", row.transfer_no, ref=f"/ims/account/transfer?id={row.id}")
        _mark_return_item(row)
        return _view(row)
    row.status = "REVOKED"
    save(row)
    send_notify(
        int(row.from_user_id or 0),
        "流转已拒绝",
        f"流转单 {row.transfer_no} 被新责任人拒绝",
        "ACCT_TRANSFER_REJECT",
        f"transfer-reject:{row.id}",
        route=f"/ims/account/transfer?id={row.id}",
        source_module="account",
    )
    return _view(row)


def revoke(ident: int, body: dict) -> dict:
    row = _row(ident)
    if row.status != "PENDING_CONFIRM":
        raise BizError(1023, "流转单状态非法")
    if not has_perm("ims:account:transfer:revoke"):
        raise BizError(1008, "您无权查看该账号")
    limit(text_of(body, "reason"), "reason", "撤销原因", 256, required=True)
    row.status = "REVOKED"
    row.remark = text_of(body, "reason")
    save(row)
    return _view(row)


def unfreeze(ident: int, body: dict) -> dict:
    account = account_row(ident)
    if account.status != "FROZEN":
        raise BizError(1023, "流转单状态非法")
    limit(text_of(body, "remark") or text_of(body, "reason"), "remark", "说明", 512, required=True)
    account.status = "IN_POOL"
    account.owner_user_id = None
    save(account)
    log_event(account.id, "UNFREEZE", "解冻回池", text_of(body, "remark") or text_of(body, "reason"))
    from app.domains.account.platform import _view

    return _view(account, detail=True)


def _recall(account, body: dict) -> dict:
    reason = text_of(body, "reasonType")
    if reason:
        require_dict("dict_transfer_reason", reason, "reasonType", "原因")
    note = limit(text_of(body, "remark"), "remark", "说明", 512)
    row = AccountTransfer(
        transfer_no=stamp_no("TR", AccountTransfer.transfer_no),
        account_id=account.id,
        transfer_type="RECALL",
        from_user_id=account.owner_user_id,
        to_user_id=None,
        reason_type=reason or None,
        remark=note,
        status="EFFECTIVE",
        effective_at=now_naive(),
    )
    account.status = "FROZEN"
    account.owner_user_id = None
    save(row)
    save(account)
    log_event(account.id, "TRANSFER", "收回", row.transfer_no, ref=f"/ims/account/transfer?id={row.id}")
    log_event(account.id, "FREEZE", "冻结", row.transfer_no)
    from app.domains.live.guards import on_account_status, open_hint

    hint = open_hint(account.id)
    on_account_status(account.id, "FROZEN")
    payload = _view(row)
    if hint:
        payload["liveHint"] = hint
    remember(token_of(body), payload)
    return payload


def _sync_assets(account_id: int, previous, target) -> None:
    session = get_session()
    binds = list(session.scalars(select(AssetBind).where(AssetBind.account_id == int(account_id), AssetBind.bind_status == "ACTIVE")))
    for bind in binds:
        asset = session.get(AssetLedger, bind.asset_id)
        if asset is None or asset.status == "SCRAPPED":
            continue
        if int(asset.owner_user_id or 0) != int(previous or 0):
            continue
        before = asset.owner_user_id
        asset.owner_user_id = target
        asset.version = int(asset.version or 1) + 1
        add_event(asset, "TRANSFER", "随账号流转", detail="账号流转同步责任人", from_owner=before, to_owner=target)
    session.flush()


def _mark_return_item(row: AccountTransfer) -> None:
    from app.domains.account.model import ReturnItem

    item = get_session().scalar(select(ReturnItem).where(ReturnItem.transfer_id == row.id, ReturnItem.item_status == "PENDING"))
    if item is None:
        return
    item.item_status = "TRANSFERRED"
    item.transfer_to_user_id = row.to_user_id
    get_session().flush()


def _row(ident: int) -> AccountTransfer:
    row = get_session().get(AccountTransfer, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    owner = owner_limit()
    if owner is not None and owner not in {int(row.from_user_id or 0), int(row.to_user_id or 0)}:
        raise BizError(1008, "您无权查看该账号")
    return row


def _filtered(params: dict) -> list[AccountTransfer]:
    stmt = select(AccountTransfer).order_by(AccountTransfer.id.desc())
    kind = text_of(params, "transferType")
    if kind:
        require_dict("dict_transfer_type", kind, "transferType", "类型")
        stmt = stmt.where(AccountTransfer.transfer_type == kind)
    status = text_of(params, "status")
    if status:
        require_dict("dict_transfer_status", status, "status", "状态")
        stmt = stmt.where(AccountTransfer.status == status)
    rows = list(get_session().scalars(stmt))
    owner = owner_limit()
    if owner is not None:
        rows = [row for row in rows if owner in {int(row.from_user_id or 0), int(row.to_user_id or 0)}]
    return rows


def _view(row: AccountTransfer) -> dict:
    account = account_row(row.account_id)
    return {
        "id": row.id,
        "transferNo": row.transfer_no,
        "transferType": row.transfer_type,
        "typeLabel": _TYPE.get(row.transfer_type, row.transfer_type),
        "accountId": row.account_id,
        "accountNo": account.account_no or "",
        "nickname": account.nickname or account.name,
        "fromUserId": row.from_user_id,
        "fromName": user_brief(row.from_user_id)["name"],
        "toUserId": row.to_user_id,
        "toName": user_brief(row.to_user_id)["name"],
        "reasonType": row.reason_type or "",
        "reasonLabel": _REASON.get(row.reason_type or "", row.reason_type or ""),
        "remark": row.remark or "",
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "effectiveAt": when(row.effective_at),
        "syncAssets": bool(row.sync_assets),
        "createTime": when(row.create_time),
    }
