"""领用单。审批只走预置模板 ACCT_BORROW。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.session import get_session
from app.domains.account.model import AccountApply
from app.domains.account.platform import _view as account_view
from app.domains.account.support import (
    account_row,
    limit,
    log_event,
    owner_limit,
    page_slice,
    parse_day,
    remember,
    replay,
    save,
    stamp_no,
    text_of,
    token_of,
    user_brief,
    viewer_id,
    visible,
    when,
)
from app.domains.message.service import send_notify
from app.domains.todo.service import todo_create

_STATUS = {
    "PENDING_APPROVAL": "待审批",
    "PENDING_HANDOVER": "待交接",
    "APPROVED": "已领用",
    "REJECTED": "拒绝",
    "RETURNED": "已归还",
}


def page(page_query, params: dict) -> dict:
    rows = _filtered(params)
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def detail(ident: int) -> dict:
    return _view(_row(ident), full=True)


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    from app.core.serialize import parse_api_id

    raw = body.get("accountId")
    if raw in (None, ""):
        from app.domains.account.support import one

        one("accountId", "请选择账号")
    account = account_row(int(parse_api_id(raw)))
    if account.status == "FROZEN":
        raise BizError(1022, "账号处于冻结态，不可领用")
    if account.status == "IN_USE" or account.owner_user_id:
        raise BizError(1021, "账号已被领用")
    if account.status != "IN_POOL":
        raise BizError(1001, "状态已变化，请刷新")
    open_row = get_session().scalar(
        select(AccountApply).where(AccountApply.account_id == account.id, AccountApply.apply_status.in_(("PENDING_APPROVAL", "PENDING_HANDOVER")))
    )
    if open_row is not None:
        raise BizError(1021, "账号已被领用")
    purpose = limit(text_of(body, "purpose"), "purpose", "用途", 256, required=True)
    start = parse_day(body.get("planStart"), "planStart", required=True, label="计划开始")
    end = parse_day(body.get("planEnd"), "planEnd", required=True, label="计划结束")
    if end < start:
        from app.domains.account.support import one

        one("planEnd", "计划结束不能早于开始")
    row = AccountApply(
        apply_no=stamp_no("AP", AccountApply.apply_no),
        account_id=account.id,
        applicant_user_id=viewer_id(),
        purpose=purpose,
        plan_start=start,
        plan_end=end,
        apply_status="PENDING_APPROVAL",
        current_step="待审批",
        idle_reminded=0,
    )
    save(row)
    instance = _start_flow(row, account)
    row.flow_instance_id = int(instance.id)
    row.current_step = instance.current_node or "待审批"
    get_session().flush()
    payload = _view(row, full=True)
    remember(token_of(body), payload)
    return payload


def confirm(ident: int, body: dict) -> dict:
    row = _row(ident)
    if row.apply_status != "PENDING_HANDOVER":
        raise BizError(1023, "领用单状态非法")
    actor = viewer_id()
    from app.domains.resource.common import has_perm

    if actor != int(row.applicant_user_id) and not has_perm("ims:account:apply:confirm"):
        raise BizError(1008, "您无权查看该账号")
    handover = body.get("handover") if isinstance(body.get("handover"), dict) else body
    if not handover.get("passwordReset"):
        from app.domains.account.support import one

        one("passwordReset", "请确认密码已重置")
    detail = {
        "passwordReset": True,
        "note": limit(text_of(handover, "note") or text_of(body, "note"), "note", "交接说明", 512),
    }
    account = account_row(row.account_id)
    if account.status != "IN_POOL" or account.owner_user_id:
        raise BizError(1021, "账号已被领用")
    account.status = "IN_USE"
    account.owner_user_id = row.applicant_user_id
    row.apply_status = "APPROVED"
    row.handover_detail = detail
    row.current_step = "已领用"
    save(account)
    save(row)
    log_event(account.id, "APPLY", "领用", row.apply_no, ref=f"/ims/account/apply?id={row.id}")
    return _view(row, full=True)


def on_finished(biz_id: int, result: str) -> None:
    row = get_session().get(AccountApply, int(biz_id))
    if row is None or int(row.deleted or 0) != 0:
        return
    if result == "APPROVED":
        if row.apply_status != "PENDING_APPROVAL":
            return
        row.apply_status = "PENDING_HANDOVER"
        row.current_step = "待交接"
        get_session().flush()
        send_notify(
            int(row.applicant_user_id),
            "领用待交接",
            f"领用单 {row.apply_no} 已通过，请完成交接确认",
            "ACCT_HANDOVER",
            f"apply:{row.id}",
            route=f"/ims/account/apply?id={row.id}",
            source_module="account",
        )
        todo_create(
            "ACCT_HANDOVER",
            int(row.id),
            "CONFIRM",
            f"账号领用待交接 {row.apply_no}",
            user_ids=[int(row.applicant_user_id)],
            route=f"/ims/account/apply?id={row.id}",
            source_module="account",
        )
        return
    if result in {"REJECTED", "CANCELLED"}:
        if row.apply_status != "PENDING_APPROVAL":
            return
        row.apply_status = "REJECTED"
        row.current_step = "已拒绝"
        get_session().flush()
        send_notify(
            int(row.applicant_user_id),
            "领用已拒绝",
            f"领用单 {row.apply_no} 未通过",
            "ACCT_REJECT",
            f"apply-reject:{row.id}",
            route=f"/ims/account/apply?id={row.id}",
            source_module="account",
        )


def _start_flow(row: AccountApply, account):
    from app.domains.flow.graph import normalize_nodes, open_entry
    from app.domains.flow.model import FlowInstance, FlowTemplate, FlowTemplateVersion

    session = get_session()
    template = session.scalar(select(FlowTemplate).where(FlowTemplate.code == "ACCT_BORROW", FlowTemplate.deleted == 0))
    if template is None or template.status not in {"PUBLISHED", "ENABLED"}:
        raise BizError(1134, "账号领用审批模板未发布")
    version = session.scalar(
        select(FlowTemplateVersion).where(
            FlowTemplateVersion.template_id == template.id,
            FlowTemplateVersion.version == template.current_version,
            FlowTemplateVersion.status == "PUBLISHED",
        )
    )
    if version is None:
        raise BizError(1134, "账号领用审批模板未发布")
    instance = FlowInstance(
        template_version_id=version.id,
        template_id=template.id,
        biz_type="ACCT_BORROW",
        biz_id=int(row.id),
        initiator=int(row.applicant_user_id),
        status="RUNNING",
        current_node="",
        instance_no=f"FI{row.apply_no}",
        form_data={"accountName": account.nickname or account.name, "purpose": row.purpose},
        business_key=f"ACCT_BORROW:{row.id}",
        version_no=version.version,
    )
    save(instance)
    open_entry(instance, normalize_nodes(version.nodes or [], strict=False))
    session.flush()
    return instance


def _row(ident: int) -> AccountApply:
    row = get_session().get(AccountApply, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    account = account_row(row.account_id)
    owner = owner_limit()
    if owner is not None and owner not in {int(row.applicant_user_id), int(account.owner_user_id or 0)}:
        raise BizError(1008, "您无权查看该账号")
    return row


def _filtered(params: dict) -> list[AccountApply]:
    stmt = select(AccountApply).order_by(AccountApply.id.desc())
    status = text_of(params, "applyStatus") or text_of(params, "status")
    if status:
        from app.domains.account.support import require_dict

        require_dict("dict_apply_status", status, "status", "状态")
        stmt = stmt.where(AccountApply.apply_status == status)
    rows = list(get_session().scalars(stmt))
    owner = owner_limit()
    if owner is not None:
        rows = [row for row in rows if int(row.applicant_user_id) == owner or int(account_row(row.account_id).owner_user_id or 0) == owner]
    keyword = text_of(params, "keyword")
    if keyword:
        rows = [row for row in rows if keyword in row.apply_no or keyword in (account_row(row.account_id).nickname or "")]
    return rows


def _view(row: AccountApply, full: bool = False) -> dict:
    account = account_row(row.account_id)
    person = user_brief(row.applicant_user_id)
    data = {
        "id": row.id,
        "applyNo": row.apply_no,
        "accountId": row.account_id,
        "accountNo": account.account_no or "",
        "nickname": account.nickname or account.name,
        "platform": account.platform,
        "applicantUserId": row.applicant_user_id,
        "applicantName": person["name"],
        "purpose": row.purpose,
        "planStart": row.plan_start.isoformat() if row.plan_start else "",
        "planEnd": row.plan_end.isoformat() if row.plan_end else "",
        "applyStatus": row.apply_status,
        "statusLabel": _STATUS.get(row.apply_status, row.apply_status),
        "currentStep": row.current_step or "",
        "flowInstanceId": row.flow_instance_id,
        "createTime": when(row.create_time),
        "passwordReset": bool((row.handover_detail or {}).get("passwordReset")),
    }
    if full:
        data["account"] = account_view(account)
        data["handoverNote"] = (row.handover_detail or {}).get("note") or ""
        visible(account)
    return data


def idle_scan() -> int:
    from datetime import timedelta

    session = get_session()
    rows = list(session.scalars(select(AccountApply).where(AccountApply.apply_status == "APPROVED", AccountApply.idle_reminded == 0)))
    from app.domains.master.model import PlatformAccount

    sent = 0
    for row in rows:
        account = session.get(PlatformAccount, row.account_id)
        if account is None or account.status != "IN_USE":
            continue
        if row.update_time is None or row.update_time > now_naive() - timedelta(days=15):
            continue
        from app.domains.account.platform import _idle

        if not _idle(account):
            continue
        row.idle_reminded = 1
        send_notify(
            int(account.owner_user_id or row.applicant_user_id),
            "账号长期未使用",
            f"账号 {account.account_no} 领用后长期未使用",
            "ACCT_IDLE",
            f"idle:{account.id}",
            route=f"/ims/corp/account/douyin?id={account.id}",
            source_module="account",
        )
        todo_create(
            "ACCT_IDLE",
            int(account.id),
            "WARNING",
            f"账号 {account.account_no} 领用后长期未使用",
            user_ids=[int(account.owner_user_id or row.applicant_user_id)],
            route=f"/ims/corp/account/douyin?id={account.id}",
            source_module="account",
        )
        sent += 1
    session.flush()
    return sent
