"""冲话费。平台消费本批按充值额模拟。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.core.clock import today
from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.session import get_session
from app.domains.account.model import Recharge, RechargeVerify
from app.domains.account.support import (
    account_row,
    amount_fen,
    dept_name,
    limit,
    log_event,
    mask_amount,
    money_text,
    page_slice,
    parse_day,
    remember,
    replay,
    require_dict,
    save,
    text_of,
    token_of,
    user_brief,
    viewer_id,
    visible,
    when,
)
from app.domains.master.model import PlatformAccount
from app.domains.message.service import send_notify
from app.domains.resource.common import has_perm
from app.domains.todo.service import todo_create
from app.services.exchange import remember_export

_CHANNEL = {"ALIPAY": "支付宝", "WECHAT_PAY": "微信支付", "PLATFORM": "平台内充", "OTHER": "其他"}
_VERIFY = {"UNVERIFIED": "未核对", "MATCHED": "一致", "DIFF": "差异"}
_LIMIT = 500000


def page(page_query, params: dict) -> dict:
    rows = _filtered(params)
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def overview() -> dict:
    session = get_session()
    month = today().strftime("%Y-%m")
    previous = _previous_month(today())
    pending = list(session.scalars(select(Recharge).where(Recharge.verify_status == "UNVERIFIED")))
    pending = [row for row in pending if row.recharge_date.strftime("%Y-%m") == month]
    last = session.scalar(select(RechargeVerify).where(RechargeVerify.month == previous).order_by(RechargeVerify.id.desc()))
    day = today().day
    return {
        "pendingCount": len(pending),
        "lastDiffRate": _rate(last.diff_rate_bp) if last else "—",
        "lastDiffAmount": money_text(abs(int(last.total_recharge_fen) - int(last.platform_consumed_fen))) if last else "—",
        "banner": "请于 5 日前完成上月核对" if 1 <= day <= 5 else "",
    }


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    row = Recharge(verify_status="UNVERIFIED", operator_user_id=viewer_id(), amount_fen=0, channel="ALIPAY", recharge_date=today())
    _fill(row, body, creating=True)
    account = account_row(row.account_id)
    account.recharge_total_fen = int(account.recharge_total_fen or 0) + int(row.amount_fen)
    save(account)
    save(row)
    log_event(account.id, "RECHARGE", "充值", money_text(row.amount_fen), ref=f"/ims/account/recharge?id={row.id}")
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = _row(ident)
    if row.verify_status == "MATCHED":
        raise BizError(1001, "状态已变化，请刷新")
    before = int(row.amount_fen)
    _fill(row, body, creating=False)
    account = account_row(row.account_id)
    account.recharge_total_fen = int(account.recharge_total_fen or 0) - before + int(row.amount_fen)
    save(account)
    save(row)
    return _view(row)


def verify(body: dict) -> dict:
    month = text_of(body, "month") or _previous_month(today())
    if len(month) != 7 or month[4] != "-":
        from app.domains.account.support import one

        one("month", "请选择月份")
    session = get_session()
    rows = [row for row in session.scalars(select(Recharge)) if row.recharge_date.strftime("%Y-%m") == month]
    total = sum(int(row.amount_fen) for row in rows)
    consumed = _consumed(total, body)
    diff = consumed - total
    rate_bp = 0 if total == 0 else int(round(abs(diff) * 10000 / total))
    detail = []
    for row in rows:
        account = account_row(row.account_id)
        share = 0 if total == 0 else int(round(consumed * row.amount_fen / total))
        row.verify_diff_fen = share - int(row.amount_fen)
        row.verify_status = "MATCHED" if abs(row.verify_diff_fen) == 0 else "DIFF"
        detail.append(
            {
                "accountId": account.id,
                "accountNo": account.account_no,
                "rechargeFen": int(row.amount_fen),
                "consumedFen": share,
                "diffFen": int(row.verify_diff_fen),
            }
        )
    batch = RechargeVerify(
        month=month,
        total_recharge_fen=total,
        platform_consumed_fen=consumed,
        diff_rate_bp=rate_bp,
        diff_detail=detail,
        ticket_created=1 if rate_bp >= 200 else 0,
    )
    save(batch)
    session.flush()
    hint = None
    if rate_bp >= 200:
        hint = "月度核对差异率 ≥ 2%，已生成核查工单"
        todo_create(
            "ACCT_RECHARGE_DIFF",
            int(batch.id),
            "WARNING",
            f"{month} 冲话费差异率 {_rate(rate_bp)}",
            perm_code="ims:account:recharge:verify",
            route=f"/ims/account/recharge?month={month}",
            source_module="account",
        )
        from app.domains.todo.service import users_with_perm

        for receiver in users_with_perm("ims:account:recharge:verify"):
            send_notify(
                receiver,
                "冲话费差异核查",
                hint,
                "ACCT_RECHARGE_DIFF",
                f"recharge:{batch.id}:{receiver}",
                route=f"/ims/account/recharge?month={month}",
                source_module="account",
            )
    return {
        "id": batch.id,
        "month": month,
        "totalRecharge": money_text(total),
        "platformConsumed": money_text(consumed),
        "diffRate": _rate(rate_bp),
        "diffDetail": detail if not mask_amount() else [],
        "ticketCreated": bool(batch.ticket_created),
        "hintCode": 1026 if hint else None,
        "hintMessage": hint or "",
        "simulated": True,
    }


def summary(params: dict) -> dict:
    dimension = (text_of(params, "dimension") or "account").lower()
    month = text_of(params, "month")
    rows = list(get_session().scalars(select(Recharge)))
    if month:
        rows = [row for row in rows if row.recharge_date.strftime("%Y-%m") == month]
    grouped: dict[str, int] = {}
    for row in rows:
        account = account_row(row.account_id)
        if dimension == "dept":
            key = dept_name(account.owner_user_id) or "未分配"
        elif dimension == "month":
            key = row.recharge_date.strftime("%Y-%m")
        elif dimension in {"platform", "PLATFORM"}:
            key = account.platform or ""
        else:
            key = account.account_no or str(account.id)
        grouped[key] = grouped.get(key, 0) + int(row.amount_fen)
    return {
        "dimension": "platform" if dimension == "PLATFORM" else dimension,
        "list": [{"name": key, "amount": money_text(value)} for key, value in grouped.items()],
    }


def export(params: dict) -> dict:
    rows = [_view(row) for row in _filtered(params)]
    header = ["账号", "金额", "渠道", "充值日期", "核对状态", "操作人"]
    body = [[item["accountNo"], item["amount"], item["channelLabel"], item["rechargeDate"], item["verifyLabel"], item["operatorName"]] for item in rows]
    return remember_export("冲话费.xlsx", header, body, "account_recharge")


def _consumed(total: int, body: dict) -> int:
    raw = body.get("platformConsumedFen")
    if raw not in (None, "") and str(body.get("simulate") or "") == "test":
        return int(raw)
    bias = text_of(body, "simulate")
    if bias == "diff":
        return int(total * 103 / 100)
    return total


def _fill(row: Recharge, body: dict, creating: bool) -> None:
    from app.core.serialize import parse_api_id

    if creating or "accountId" in body:
        raw = body.get("accountId")
        if raw in (None, ""):
            from app.domains.account.support import one

            one("accountId", "请选择账号")
        account = account_row(int(parse_api_id(raw)))
        if account.status == "CANCELLED":
            raise BizError(1001, "状态已变化，请刷新")
        visible(account)
        row.account_id = account.id
    if creating or "amount" in body:
        row.amount_fen = amount_fen(body.get("amount"), "amount")
    if creating or "channel" in body:
        row.channel = require_dict("dict_recharge_channel", text_of(body, "channel"), "channel", "渠道")
    if creating or "rechargeDate" in body:
        found = parse_day(body.get("rechargeDate"), "rechargeDate", required=True, label="充值日期")
        if found > today():
            from app.domains.account.support import one

            one("rechargeDate", "充值日期不能晚于今天")
        row.recharge_date = found
    if "voucherFileKey" in body or creating:
        row.voucher_file_key = text_of(body, "voucherFileKey") or None
    if "remark" in body or creating:
        row.remark = limit(text_of(body, "remark"), "remark", "备注", 256)
    if int(row.amount_fen) > _LIMIT and not row.voucher_file_key:
        raise BizError(1025, "金额超过 5000 元须上传凭证")
    row.operator_user_id = viewer_id()


def _row(ident: int) -> Recharge:
    row = get_session().get(Recharge, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    visible(account_row(row.account_id))
    return row


def _filtered(params: dict) -> list[Recharge]:
    rows = list(get_session().scalars(select(Recharge).order_by(Recharge.id.desc())))
    month = text_of(params, "month")
    if month:
        rows = [row for row in rows if row.recharge_date.strftime("%Y-%m") == month]
    status = text_of(params, "verifyStatus")
    if status:
        require_dict("dict_recharge_verify_status", status, "verifyStatus", "核对状态")
        rows = [row for row in rows if row.verify_status == status]
    account_id = text_of(params, "accountId")
    if account_id:
        from app.core.serialize import parse_api_id

        wanted = int(parse_api_id(account_id))
        rows = [row for row in rows if int(row.account_id) == wanted]
    kept = []
    for row in rows:
        try:
            visible(account_row(row.account_id))
        except BizError:
            continue
        kept.append(row)
    return kept


def _view(row: Recharge) -> dict:
    account = account_row(row.account_id)
    show_voucher = has_perm("ims:account:recharge:voucher")
    return {
        "id": row.id,
        "accountId": row.account_id,
        "accountNo": account.account_no or "",
        "nickname": account.nickname or account.name,
        "platform": account.platform,
        "amount": money_text(row.amount_fen),
        "amountFen": 0 if mask_amount() else int(row.amount_fen),
        "channel": row.channel,
        "channelLabel": _CHANNEL.get(row.channel, row.channel),
        "rechargeDate": row.recharge_date.isoformat() if row.recharge_date else "",
        "voucherFileKey": row.voucher_file_key if show_voucher else "",
        "voucherVisible": show_voucher and bool(row.voucher_file_key),
        "verifyStatus": row.verify_status,
        "verifyLabel": _VERIFY.get(row.verify_status, row.verify_status),
        "diffAmount": money_text(row.verify_diff_fen) if row.verify_diff_fen is not None else "",
        "operatorName": user_brief(row.operator_user_id)["name"],
        "remark": row.remark or "",
        "createTime": when(row.create_time),
    }


def _previous_month(day) -> str:
    first = day.replace(day=1)
    last = first - timedelta(days=1)
    return last.strftime("%Y-%m")


def _rate(bp: int) -> str:
    return f"{bp / 100:.2f}%"
