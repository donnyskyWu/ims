"""场次、风控、下播、台账与 Football 只读绑定。"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select

from app.core.clock import now_naive, today
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import page_result
from app.core.sequence import session_code
from app.db.session import get_session
from app.domains.account.model import Recharge
from app.domains.device.model import AssetBind, AssetLedger
from app.domains.live import risk
from app.domains.live.common import (
    ENTRY_LABEL,
    LIVE_PLATFORMS,
    OPEN_STATUS,
    PLATFORM_LABEL,
    STATUS_LABEL,
    SYNC_LABEL,
    apply_scope,
    body_text,
    broad_editor,
    close_todos,
    divide,
    duration_text,
    hours_between,
    show_money,
    in_scope,
    int_of,
    limit_text,
    money_of,
    money_text,
    owns,
    parse_dt,
    require_scope,
    save,
    trace,
    user_name,
    view_mode,
    viewer_id,
    when_text,
)
from app.domains.live.model import (
    LiveCost,
    LiveDataSnapshot,
    LiveReport,
    LiveReportCorrection,
    LiveRiskCheck,
    LiveSessionDevice,
    LiveSupplement,
)
from app.domains.master.model import Author, IpGroup, LiveSession, PlatformAccount, Realname
from app.domains.message.service import send
from app.domains.resource.common import has_perm, one, text_of, user_ids_with_perm
from app.domains.system.model import DictData, Outbox, User
from app.domains.todo.service import todo_create
from app.integrations.football_live.reader import UNAVAILABLE, football_row_or_unavailable, get_room
from app.services.exchange import remember_export

REPORT_FIELDS = (
    ("gmv", "GMV"),
    ("orderCount", "订单数"),
    ("viewerCount", "观看人数"),
    ("peakOnline", "峰值在线"),
    ("newFans", "涨粉数"),
    ("refundAmount", "退款额"),
    ("adCost", "投放成本"),
)


def stats() -> dict:
    rows = list(get_session().scalars(apply_scope(select(LiveSession))))
    day = today()
    month = day.strftime("%Y-%m")
    pending = 0
    live = 0
    overdue = 0
    gmv = Decimal("0")
    for row in rows:
        if row.session_status in {"PENDING_RISK_CHECK", "APPROVED"} and row.plan_start_time and row.plan_start_time.date() == day:
            pending += 1
        if row.session_status == "LIVE":
            live += 1
        report = _report(row.id)
        if row.session_status == "ENDED" and (report is None or report.entry_status != "SUBMITTED" and report.entry_status != "CONFIRMED"):
            overdue += 1
        if show_money(row) and report and report.entry_status == "CONFIRMED" and row.actual_end_time and row.actual_end_time.strftime("%Y-%m") == month:
            gmv += Decimal(report.gmv or 0)
    data = {
        "pendingToday": pending,
        "living": live,
        "overdueEntry": overdue,
    }
    if has_perm("ims:live:report:finance"):
        data["monthGmv"] = money_text(gmv)
    return data


def session_list(page, params: dict) -> dict:
    rows = _filtered(params)
    start = (page.page_no - 1) * page.page_size
    chunk = rows[start : start + page.page_size]
    return page_result([_list_item(row) for row in chunk], len(rows), page)


def ledger_list(page, params: dict) -> dict:
    return session_list(page, params)


def detail(code: str) -> dict:
    row = _by_code(code)
    require_scope(row)
    data = _full(row)
    if not in_scope(row):
        raise BizError(1008, "您无权查看该场次")
    return data


def realname_precheck(params: dict) -> dict:
    raw = text_of(params, "realnameId")
    if not raw:
        one("realnameId", "请选择实名人")
    from app.core.serialize import parse_api_id

    person = get_session().get(Realname, int(parse_api_id(raw)))
    if person is None or person.deleted:
        raise BizError(1500, data={"fieldErrors": [{"field": "realnameId", "message": "实名人不存在"}]})
    if person.status != "ENABLED":
        raise BizError(1501, data={"fieldErrors": [{"field": "realnameId", "message": "实名人已停用"}]})
    fact = risk.cert_fact(person.id)
    return {"realnameId": person.id, "realnameName": person.name, "tone": fact["tone"], "message": fact["message"], "expireDate": fact["expireDate"]}


def register(body: dict) -> dict:
    if not has_perm("ims:live:session:register"):
        raise BizError(1008, "您无权查看该场次")
    token = _token(body)
    existed = get_session().scalar(select(LiveSession).where(LiveSession.client_token == token))
    if existed is not None:
        return _full(existed)
    account = _live_account(body.get("accountId"), allow_idle=False)
    person = _live_person(body.get("realnameId"))
    owner = _owner(body.get("responsibleUserId") or viewer_id())
    assets = _assets(body.get("assetIds") or body.get("deviceIds"), require_in_use=True)
    topic = limit_text(body_text(body, "topic"), "topic", "主题", 256, required=True)
    start = parse_dt(body.get("planStartTime"), "planStartTime", "计划开播")
    end = parse_dt(body.get("planEndTime"), "planEndTime", "计划下播")
    _plan_future(start, end)
    row = LiveSession(
        name=topic[:100],
        status="ENABLED",
        session_code=session_code(account.platform, now_naive()),
        platform=account.platform,
        account_id=account.id,
        realname_id=person.id,
        responsible_user_id=owner.id,
        ip_group_id=account.ip_group_id,
        author_id=account.author_user_id,
        topic=topic,
        plan_start_time=start,
        plan_end_time=end,
        session_status="PENDING_RISK_CHECK",
        football_sync_status="UNLINKED",
        client_token=token,
        is_supplement=0,
    )
    save(row)
    _bind_devices(row, assets)
    trace(row.id, "REGISTER", "登记场次", topic)
    _run_risk(row, manual=False)
    return _full(row)


def update_register(code: str, body: dict) -> dict:
    row = _editable(code)
    if "platform" in body and body_text(body, "platform") not in {"", row.platform or ""}:
        one("platform", "平台不一致，请取消后重新登记")
    if body.get("accountId"):
        account = _live_account(body.get("accountId"), allow_idle=False)
        if account.platform != row.platform:
            one("accountId", "平台不一致，请取消后重新登记")
        row.account_id = account.id
        row.ip_group_id = account.ip_group_id
        row.author_id = account.author_user_id
    if body.get("realnameId"):
        row.realname_id = _live_person(body.get("realnameId")).id
    if body.get("responsibleUserId"):
        row.responsible_user_id = _owner(body.get("responsibleUserId")).id
    if "topic" in body:
        row.topic = limit_text(body_text(body, "topic"), "topic", "主题", 256, required=True)
        row.name = row.topic[:100]
    if body.get("planStartTime") or body.get("planEndTime"):
        start = parse_dt(body.get("planStartTime") or row.plan_start_time, "planStartTime", "计划开播")
        end = parse_dt(body.get("planEndTime") or row.plan_end_time, "planEndTime", "计划下播")
        _plan_future(start, end)
        row.plan_start_time = start
        row.plan_end_time = end
    assets = None
    if "assetIds" in body or "deviceIds" in body:
        assets = _assets(body.get("assetIds") or body.get("deviceIds"), require_in_use=True)
    save(row)
    if assets is not None:
        _bind_devices(row, assets)
    trace(row.id, "EDIT", "编辑登记", row.topic or "")
    _run_risk(row, manual=False)
    return _full(row)


def rerun(code: str) -> dict:
    row = _by_code(code)
    require_scope(row)
    _ensure_editor(row)
    if row.session_status not in {"PENDING_RISK_CHECK", "APPROVED"}:
        raise BizError(1042, "当前场次状态不允许该操作")
    _run_risk(row, manual=True)
    return _full(row)


def approve(code: str, body: dict) -> dict:
    row = _by_code(code)
    require_scope(row)
    if not has_perm("ims:live:session:approve"):
        raise BizError(1008, "您无权查看该场次")
    if row.session_status != "PENDING_RISK_CHECK" or row.risk_level != "YELLOW":
        if row.risk_level == "RED":
            raise BizError(1043)
        raise BizError(1042, "当前场次状态不允许该操作")
    if owns(row):
        raise BizError(1049, "补录 / 更正的审批人不能是发起人")
    opinion = limit_text(body_text(body, "opinion"), "opinion", "审批意见", 512, required=True)
    passed = body.get("approve")
    if passed is None:
        passed = body_text(body, "action") != "REJECT"
    close_todos("LIVE_APPROVAL", row.id)
    if passed:
        row.session_status = "APPROVED"
        row.approver_user_id = viewer_id()
        row.approve_opinion = opinion
        row.approved_at = now_naive()
        save(row)
        trace(row.id, "APPROVE", "审批放行", opinion)
    else:
        save(row)
        trace(row.id, "REJECT", "审批退回", opinion)
        if row.responsible_user_id:
            send(row.responsible_user_id, "开播申请被退回", opinion or "开播申请被退回", "LIVE_REJECT", f"live-reject:{row.id}", route=f"/ims/live/sessions/{row.session_code}?tab=risk", source_module="live")
    return _full(row)


def start(code: str, body: dict) -> dict:
    row = _by_code(code)
    require_scope(row)
    if not owns(row):
        raise BizError(1042, "当前场次状态不允许该操作")
    if row.session_status != "APPROVED":
        if row.risk_level == "RED" or row.session_status == "PENDING_RISK_CHECK" and row.risk_level == "RED":
            raise BizError(1043)
        if row.risk_level == "YELLOW" or row.session_status == "PENDING_RISK_CHECK":
            raise BizError(1044, "风险级别为黄色，需运营总监审批放行后才能开播")
        raise BizError(1042, "当前场次状态不允许该操作")
    if row.realname_id and risk.cert_fact(row.realname_id)["score"] >= 100:
        _run_risk(row, manual=True)
        raise BizError(1043)
    row.session_status = "LIVE"
    row.actual_start_time = now_naive()
    save(row)
    trace(row.id, "START", "确认开播", "")
    early = bool(row.plan_start_time and hours_between(now_naive(), row.plan_start_time) > 2)
    data = _full(row)
    data["earlyWarning"] = early
    return data


def end(code: str, body: dict | None = None) -> dict:
    row = _by_code(code)
    require_scope(row)
    if row.session_status != "LIVE":
        raise BizError(1042, "当前场次状态不允许该操作")
    if not owns(row) and not has_perm("ims:live:session:approve"):
        raise BizError(1008, "您无权查看该场次")
    return _finish(row, now_naive(), "确认下播", system=False)


def cancel(code: str, body: dict) -> dict:
    row = _by_code(code)
    require_scope(row)
    if not has_perm("ims:live:session:cancel"):
        raise BizError(1008, "您无权查看该场次")
    if not broad_editor() and not owns(row):
        raise BizError(1008, "您无权查看该场次")
    if row.session_status not in {"PENDING_RISK_CHECK", "APPROVED"}:
        raise BizError(1042, "当前场次状态不允许该操作")
    reason = limit_text(body_text(body, "cancelReason") or body_text(body, "reason"), "cancelReason", "取消原因", 256, required=True)
    row.session_status = "CANCELLED"
    row.cancel_reason = reason
    save(row)
    _release(row.id)
    close_todos("LIVE_APPROVAL", row.id)
    trace(row.id, "CANCEL", "取消场次", reason)
    return _full(row)


def bind_room(code: str, body: dict) -> dict:
    row = _by_code(code)
    require_scope(row)
    _ensure_bind(row)
    if row.session_status == "CANCELLED":
        raise BizError(1042, "当前场次状态不允许该操作")
    raw = body.get("roomId")
    if raw in (None, ""):
        row.football_room_id = None
        row.football_sync_status = "UNLINKED"
        row.last_football_sync_at = None
        save(row)
        trace(row.id, "UNBIND", "解绑直播间", "")
        return _full(row)
    room_id = _room_id(raw)
    taken = get_session().scalar(
        select(LiveSession).where(
            LiveSession.football_room_id == room_id,
            LiveSession.session_status != "CANCELLED",
            LiveSession.id != row.id,
        )
    )
    if taken is not None:
        one("roomId", f"该直播间已关联场次 {taken.session_code}")
    ctx = get_ctx()
    found = get_room(ctx.tenant_id if ctx else 1, room_id)
    if found is None:
        raise BizError(1041, "Football 直播间不存在或不属于本租户")
    row.football_room_id = room_id
    row.football_sync_status = "PENDING"
    save(row)
    _sync_row(row, force=True)
    trace(row.id, "BIND", "绑定直播间", str(room_id))
    return _full(row)


def sync_room(code: str, body: dict | None = None) -> dict:
    row = _by_code(code)
    require_scope(row)
    _ensure_bind(row)
    if not row.football_room_id:
        one("roomId", "请先绑定直播间")
    _sync_row(row, force=bool((body or {}).get("force")))
    return _full(row)


def metrics(code: str) -> dict:
    row = _by_code(code)
    require_scope(row)
    data = {
        "sessionCode": row.session_code,
        "footballSyncStatus": row.football_sync_status,
        "footballSyncLabel": SYNC_LABEL.get(row.football_sync_status, row.football_sync_status),
        "lastFootballSyncAt": when_text(row.last_football_sync_at),
        "hint": "GMV 等经营数据见『下播与 GMV』Tab",
        "linked": bool(row.football_room_id),
    }
    if not row.football_room_id:
        data["empty"] = "未关联 Football 直播间"
        return data
    ctx = get_ctx()
    loaded = football_row_or_unavailable(lambda: _display_room(ctx.tenant_id if ctx else 1, int(row.football_room_id)))
    if loaded is UNAVAILABLE or loaded is None:
        if loaded is None:
            row.football_sync_status = "FAILED"
            save(row)
            data["deleted"] = True
            data["message"] = "直播间已在 Football 删除"
        else:
            data["unavailable"] = True
            data["message"] = "Football 直播数据暂不可用，稍后重试"
        return data
    deleted = int(loaded.get("deleted") or 0)
    if deleted == 1:
        row.football_sync_status = "FAILED"
        save(row)
        data["deleted"] = True
        data["message"] = "直播间已在 Football 删除"
        return data
    shown = dict(loaded)
    if not has_perm("ims:live:football:bind"):
        if shown.get("server_url"):
            shown["server_url"] = "已隐藏"
    data["room"] = _room_view(shown)
    report = _report(row.id)
    data["compare"] = {
        "enteredViewer": None if report is None else report.viewer_count,
        "footballViewer": shown.get("viewer_count"),
    }
    return data


def save_draft(code: str, body: dict) -> dict:
    row, report = _entry_target(code)
    _fill_report(report, row, body, strict=False)
    report.entry_status = "DRAFT"
    report.entry_user_id = report.entry_user_id or viewer_id()
    save(report)
    _save_costs(row, body, report)
    return _report_view(row, report)


def submit_report(code: str, body: dict) -> dict:
    row, report = _entry_target(code)
    if report.entry_status in {"SUBMITTED", "CONFIRMED"}:
        raise BizError(1047, "下播数据已提交，修改请走更正单")
    _fill_report(report, row, body, strict=True)
    report.entry_status = "SUBMITTED"
    report.entry_user_id = viewer_id()
    report.submitted_at = now_naive()
    save(report)
    _save_costs(row, body, report)
    close_todos("LIVE_ENTRY", row.id)
    trace(row.id, "REPORT", "提交下播数据", "")
    return _report_view(row, report)


def report_detail(code: str) -> dict:
    row = _by_code(code)
    require_scope(row)
    report = _report(row.id)
    if report is None:
        return {"sessionCode": row.session_code, "entryStatus": "", "entryStatusLabel": "未录", "canEntry": row.session_status == "ENDED" and owns(row)}
    return _report_view(row, report)


def confirm_report(code: str, body: dict | None = None) -> dict:
    row = _by_code(code)
    require_scope(row)
    if not has_perm("ims:live:report:confirm"):
        raise BizError(1008, "您无权查看该场次")
    report = _report(row.id)
    if report is None or report.entry_status != "SUBMITTED":
        raise BizError(1042, "当前场次状态不允许该操作")
    if int(report.entry_user_id or 0) == viewer_id():
        raise BizError(1049, "补录 / 更正的审批人不能是发起人")
    report.entry_status = "CONFIRMED"
    report.confirm_user_id = viewer_id()
    report.confirmed_at = now_naive()
    save(report)
    trace(row.id, "CONFIRM", "核准下播数据", "核准后数据进入场次财务，修改需走更正单")
    return _report_view(row, report)


def correct(code: str, body: dict) -> dict:
    row = _by_code(code)
    require_scope(row)
    if not has_perm("ims:live:report:correct"):
        raise BizError(1008, "您无权查看该场次")
    report = _report(row.id)
    if report is None or report.entry_status not in {"SUBMITTED", "CONFIRMED"}:
        raise BizError(1042, "当前场次状态不允许该操作")
    reason = limit_text(body_text(body, "reason"), "reason", "更正原因", 512, required=True)
    before = _report_numbers(report)
    changed = _apply_correction(report, body)
    if not changed:
        one("gmv", "请至少修改一项")
    report.version = int(report.version or 1) + 1
    kept = report.entry_status
    save(report)
    if "costs" in body:
        _save_costs(row, body, report, replace=True)
    after = _report_numbers(report)
    corr = LiveReportCorrection(session_id=row.id, before_json=before, after_json=after, reason=reason, operator_id=viewer_id())
    save(corr)
    trace(row.id, "CORRECT", "更正下播数据", reason)
    if kept == "CONFIRMED":
        for user_id in user_ids_with_perm("ims:live:report:confirm"):
            send(user_id, "已核准场次被更正", f"{row.session_code} {reason}", "LIVE_CORRECT", f"live-correct:{corr.id}:{user_id}", route=f"/ims/live/sessions/{row.session_code}?tab=report", source_module="live")
    return _report_view(row, report)


def corrections(code: str) -> dict:
    row = _by_code(code)
    require_scope(row)
    rows = list(get_session().scalars(select(LiveReportCorrection).where(LiveReportCorrection.session_id == row.id).order_by(LiveReportCorrection.id.asc())))
    return {
        "list": [
            {
                "id": item.id,
                "before": item.before_json or {},
                "after": item.after_json or {},
                "reason": item.reason,
                "operatorName": user_name(item.operator_id),
                "createdAt": when_text(item.create_time),
            }
            for item in rows
        ]
    }


def pending(page, params: dict) -> dict:
    rows = []
    for row in _filtered({"tab": "overdue"}):
        if row.session_status != "ENDED":
            continue
        report = _report(row.id)
        if report and report.entry_status in {"SUBMITTED", "CONFIRMED"}:
            continue
        end_at = row.actual_end_time
        hours = 0
        if end_at:
            hours = int(hours_between(end_at, now_naive()))
        overdue = hours >= 24
        if text_of(params, "onlyOverdue") in {"1", "true"} and not overdue:
            continue
        owner = text_of(params, "responsibleUserId")
        if owner and str(row.responsible_user_id) != str(owner):
            continue
        rows.append((overdue, hours, row, report))
    rows.sort(key=lambda item: (not item[0], -(item[1])))
    start = (page.page_no - 1) * page.page_size
    chunk = rows[start : start + page.page_size]
    data = []
    for overdue, hours, row, report in chunk:
        item = _list_item(row)
        item["overdue"] = overdue
        item["overdueHours"] = hours
        item["overdueLabel"] = "超 24h" if overdue else ""
        item["entryStatusLabel"] = "未录" if report is None else ENTRY_LABEL.get(report.entry_status, report.entry_status)
        data.append(item)
    return page_result(data, len(rows), page)


def remind(code: str) -> dict:
    row = _by_code(code)
    require_scope(row)
    if not has_perm("ims:live:session:approve"):
        raise BizError(1008, "您无权查看该场次")
    if row.last_remind_at and hours_between(row.last_remind_at, now_naive()) < 1:
        one("sessionCode", "1 小时内已提醒")
    row.last_remind_at = now_naive()
    save(row)
    if row.responsible_user_id:
        send(row.responsible_user_id, "请尽快提交下播数据", row.session_code or "", "LIVE_REMIND", f"live-remind:{row.id}:{int(now_naive().timestamp())}", route=f"/ims/live/sessions/{row.session_code}?tab=report", source_module="live")
    return {"reminded": True}


def submit_supplement(body: dict) -> dict:
    if not has_perm("ims:live:ledger:supplement"):
        raise BizError(1008, "您无权查看该场次")
    register_body = body.get("register") or body
    report_body = body.get("report") or body
    reason = limit_text(body_text(body, "supplementReason") or body_text(body, "reason"), "supplementReason", "补录说明", 256, required=True)
    _supplement_times(register_body)
    _require_report(report_body)
    row = LiveSupplement(
        register_json=register_body,
        report_json=report_body,
        cost_json=body.get("costs") or report_body.get("costs") or [],
        supplement_reason=reason,
        status="PENDING",
        applicant_id=viewer_id(),
        reject_editable=0,
    )
    save(row)
    approvers = [item for item in user_ids_with_perm("ims:live:ledger:supplement-approve") if item != viewer_id()]
    if approvers:
        todo_create("LIVE_SUPPLEMENT", int(row.id), "APPROVAL", "历史补录待审批", user_ids=approvers, route=f"/ims/live/ledger?supplementId={row.id}", source_module="live")
    return _supplement_view(row)


def supplement_detail(ident: int) -> dict:
    return _supplement_view(_supplement(ident))


def supplement_update(ident: int, body: dict) -> dict:
    row = _supplement(ident)
    if int(row.applicant_id or 0) != viewer_id() or row.status != "REJECTED":
        raise BizError(1042, "当前场次状态不允许该操作")
    if body.get("register"):
        row.register_json = body.get("register")
    if body.get("report"):
        row.report_json = body.get("report")
    if "costs" in body:
        row.cost_json = body.get("costs")
    reason = body_text(body, "supplementReason") or body_text(body, "reason")
    if reason:
        row.supplement_reason = limit_text(reason, "supplementReason", "补录说明", 256, required=True)
    _supplement_times(row.register_json or {})
    _require_report(row.report_json or {})
    row.status = "PENDING"
    row.opinion = ""
    save(row)
    approvers = [item for item in user_ids_with_perm("ims:live:ledger:supplement-approve") if item != viewer_id()]
    if approvers:
        todo_create("LIVE_SUPPLEMENT", int(row.id), "APPROVAL", "历史补录待审批", user_ids=approvers, route=f"/ims/live/ledger?supplementId={row.id}", source_module="live")
    return _supplement_view(row)


def supplement_approve(ident: int, body: dict) -> dict:
    row = _supplement(ident)
    if not has_perm("ims:live:ledger:supplement-approve"):
        raise BizError(1008, "您无权查看该场次")
    if int(row.applicant_id or 0) == viewer_id():
        raise BizError(1049, "补录 / 更正的审批人不能是发起人")
    if row.status != "PENDING":
        raise BizError(1042, "当前场次状态不允许该操作")
    opinion = limit_text(body_text(body, "opinion"), "opinion", "审批意见", 512, required=False)
    passed = body.get("approve")
    if passed is None:
        passed = body_text(body, "action") != "REJECT"
    close_todos("LIVE_SUPPLEMENT", row.id)
    row.approver_id = viewer_id()
    row.opinion = opinion
    if not passed:
        row.status = "REJECTED"
        row.reject_editable = 1
        save(row)
        if row.applicant_id:
            send(row.applicant_id, "历史补录已退回", opinion or "请修改后重新提交", "LIVE_SUPPLEMENT_REJECT", f"live-sup-rej:{row.id}", route="/ims/live/ledger", source_module="live")
        return _supplement_view(row)
    created = _materialize_supplement(row)
    row.status = "APPROVED"
    row.session_id = created.id
    save(row)
    return _supplement_view(row)


def export_ledger(params: dict) -> dict:
    if not has_perm("ims:live:ledger:export"):
        raise BizError(1008, "您无权查看该场次")
    rows = _filtered(params)
    mode = view_mode()
    header = ["场次ID", "日期", "平台", "账号", "责任人", "主题", "状态", "风险级别", "时长", "观看数"]
    if mode == "finance":
        header = ["场次ID", "日期", "账号", "GMV", "退款", "投放成本", "成本汇总", "ROAS"]
    elif mode == "full":
        header = header + ["GMV", "退款", "投放成本", "ROAS"]
    body = []
    for row in rows:
        item = _list_item(row)
        if mode == "finance":
            body.append([item.get("sessionCode"), item.get("date"), item.get("accountName"), item.get("gmv"), item.get("refundAmount"), item.get("adCost"), item.get("costTotal"), item.get("roas")])
        elif mode == "full":
            body.append([item.get("sessionCode"), item.get("date"), item.get("platformLabel"), item.get("accountName"), item.get("responsibleName"), item.get("topic"), item.get("sessionStatusLabel"), item.get("riskLevelLabel"), item.get("durationText"), item.get("viewerCount"), item.get("gmv"), item.get("refundAmount"), item.get("adCost"), item.get("roas")])
        else:
            body.append([item.get("sessionCode"), item.get("date"), item.get("platformLabel"), item.get("accountName"), item.get("responsibleName"), item.get("topic"), item.get("sessionStatusLabel"), item.get("riskLevelLabel"), item.get("durationText"), item.get("viewerCount")])
    task = remember_export("直播台账.xlsx", header, body, "live_ledger")
    send(viewer_id(), "直播台账导出完成", "导出任务已提交，可在消息中下载", "LIVE_EXPORT", f"live-export:{task['id']}", route="/ims/live/ledger", source_module="live")
    return {"id": task["id"], "status": task["status"], "message": "导出任务已提交"}


def group_live_stats(group_ids: list[int]) -> dict:
    if not group_ids:
        return {"count": 0, "gmv": "0.00"}
    month = today().strftime("%Y-%m")
    rows = list(get_session().scalars(select(LiveSession).where(LiveSession.ip_group_id.in_(group_ids), LiveSession.session_status != "CANCELLED")))
    count = 0
    gmv = Decimal("0")
    for row in rows:
        anchor = row.actual_start_time or row.plan_start_time
        if anchor and anchor.strftime("%Y-%m") == month:
            count += 1
        report = _report(row.id)
        if report and report.entry_status == "CONFIRMED" and row.actual_end_time and row.actual_end_time.strftime("%Y-%m") == month:
            gmv += Decimal(report.gmv or 0)
    return {"count": count, "gmv": money_text(gmv)}


def open_session_codes(account_id: int) -> list[str]:
    rows = list(
        get_session().scalars(
            select(LiveSession).where(LiveSession.account_id == int(account_id), LiveSession.session_status.in_(OPEN_STATUS))
        )
    )
    return [row.session_code or "" for row in rows if row.session_code]


def _finish(row: LiveSession, end_at, title: str, system: bool) -> dict:
    row.session_status = "ENDED"
    end_at = end_at.replace(microsecond=0)
    if row.actual_start_time:
        row.actual_start_time = row.actual_start_time.replace(microsecond=0)
        if end_at <= row.actual_start_time:
            end_at = row.actual_start_time + timedelta(seconds=1)
    row.actual_end_time = end_at
    save(row)
    _release(row.id)
    close_todos("LIVE_APPROVAL", row.id)
    trace(row.id, "END", "系统自动下播" if system else title, "系统自动下播" if system else "")
    if row.responsible_user_id:
        todo_create(
            "LIVE_ENTRY",
            int(row.id),
            "CONFIRM",
            f"下播录入 {row.session_code}",
            user_ids=[int(row.responsible_user_id)],
            route=f"/ims/live/sessions/{row.session_code}?tab=report",
            source_module="live",
        )
    return _full(row)


def auto_end_due() -> int:
    now = now_naive()
    rows = list(get_session().scalars(select(LiveSession).where(LiveSession.session_status == "LIVE")))
    done = 0
    for row in rows:
        if row.plan_end_time and now >= row.plan_end_time + timedelta(hours=6):
            _finish(row, row.plan_end_time, "系统自动下播", system=True)
            done += 1
    return done


def mark_overdue() -> int:
    now = now_naive()
    rows = list(get_session().scalars(select(LiveSession).where(LiveSession.session_status == "ENDED", LiveSession.overdue_notified == 0)))
    done = 0
    for row in rows:
        if not row.actual_end_time or now < row.actual_end_time + timedelta(hours=24):
            continue
        report = _report(row.id)
        if report and report.entry_status in {"SUBMITTED", "CONFIRMED"}:
            continue
        row.overdue_notified = 1
        save(row)
        users = []
        if row.responsible_user_id:
            users.append(int(row.responsible_user_id))
        if row.ip_group_id:
            group = get_session().get(IpGroup, row.ip_group_id)
            if group and group.leader_user_id and int(group.leader_user_id) not in users:
                users.append(int(group.leader_user_id))
        if users:
            todo_create("LIVE_OVERDUE", int(row.id), "WARNING", f"下播录入超时 {row.session_code}", user_ids=users, route=f"/ims/live/report/pending", source_module="live")
        done += 1
    return done


def _open_todo(source: str, source_id: int, kind: str, title: str, users: list[int], route: str) -> None:
    from app.domains.todo.model import Todo

    existing = get_session().scalar(select(Todo).where(Todo.source_type == source, Todo.source_id == int(source_id), Todo.type == kind))
    if existing is not None:
        if existing.status != "PENDING":
            existing.status = "PENDING"
            existing.title = title
            existing.route = route
            get_session().flush()
        return
    if users:
        todo_create(source, int(source_id), kind, title, user_ids=users, route=route, source_module="live")


def _run_risk(row: LiveSession, manual: bool) -> None:
    account = get_session().get(PlatformAccount, row.account_id) if row.account_id else None
    devices = list(get_session().scalars(select(LiveSessionDevice).where(LiveSessionDevice.session_id == row.id)))
    assets = [get_session().get(AssetLedger, item.asset_id) for item in devices]
    checks = []
    fact = risk.cert_fact(row.realname_id) if row.realname_id else {"score": 100, "message": "该实名人未建证件档案", "code": 1045}
    checks.append(("CERT_VALID", fact["score"], fact["message"] or "证件正常"))
    if account is None or account.status != "IN_USE":
        checks.append(("ACCOUNT_STATUS", 100, "账号非在用"))
    elif int(account.realname_id or 0) != int(row.realname_id or 0):
        checks.append(("ACCOUNT_STATUS", 20, "账号绑定实名人与本场不一致"))
    else:
        checks.append(("ACCOUNT_STATUS", 0, "账号在用"))
    balance = _balance(account)
    if balance is None:
        checks.append(("BALANCE", 0, "余额数据暂不可用"))
    elif balance < 0:
        checks.append(("BALANCE", 40, "话费余额小于 0"))
    elif balance < Decimal("50"):
        checks.append(("BALANCE", 20, "话费余额低于 50 元"))
    else:
        checks.append(("BALANCE", 0, "话费余额充足"))
    words = _hit_words(row.topic or "")
    if words:
        checks.append(("BLACKLIST", 40, "命中" + "、".join(words)))
    else:
        checks.append(("BLACKLIST", 0, "未命中"))
    device_score, device_text = _device_score(assets, row.responsible_user_id)
    checks.append(("DEVICE_OWNER", device_score, device_text))
    score = sum(item[1] for item in checks)
    level = risk.level_of(score)
    previous = int(get_session().scalar(select(func.max(LiveRiskCheck.check_round)).where(LiveRiskCheck.session_id == row.id)) or 0)
    now = now_naive()
    for item, weight, detail in checks:
        save(
            LiveRiskCheck(
                session_id=row.id,
                check_round=previous + 1,
                check_item=item,
                check_result=risk.judge(weight),
                score_weight=weight,
                detail=detail[:512],
                checked_at=now,
            )
        )
    row.risk_score = score
    row.risk_level = level
    close_todos("LIVE_APPROVAL", row.id)
    if level == "GREEN":
        row.session_status = "APPROVED"
        row.approver_user_id = None
        row.approve_opinion = "系统自动放行"
        row.approved_at = now
    else:
        row.session_status = "PENDING_RISK_CHECK"
        row.approve_opinion = ""
        row.approved_at = None
        if level == "YELLOW":
            approvers = [item for item in user_ids_with_perm("ims:live:session:approve") if item != int(row.responsible_user_id or 0)]
            _open_todo("LIVE_APPROVAL", int(row.id), "APPROVAL", f"开播审批 {row.session_code}", approvers, f"/ims/live/sessions/{row.session_code}?tab=risk")
    save(row)
    trace(row.id, "RISK", "重新风控" if manual else "自动风控", risk.level_label(level))


def _device_score(assets, owner_id) -> tuple[int, str]:
    if any(item is None or item.status != "IN_USE" for item in assets):
        return 40, "设备非使用中"
    if any(int(item.owner_user_id or 0) != int(owner_id or 0) for item in assets if item is not None):
        return 10, "设备责任人与本场责任人不一致"
    return 0, "设备归属一致"


def _hit_words(topic: str) -> list[str]:
    rows = list(get_session().scalars(select(DictData).where(DictData.dict_type == "dict_live_blacklist_word", DictData.status == "ENABLED")))
    found = []
    for row in rows:
        word = row.dict_label or row.dict_value
        if word and word in topic:
            found.append(word)
    return found


def _balance(account: PlatformAccount | None):
    if account is None:
        return None
    from app.domains.live.collect import consume_of

    consumed = consume_of(account.id)
    if consumed is None:
        return None
    return (Decimal(int(account.recharge_total_fen or 0)) / Decimal(100)) - consumed


def _filtered(params: dict) -> list[LiveSession]:
    stmt = apply_scope(select(LiveSession))
    code = text_of(params, "sessionCode")
    if code:
        stmt = stmt.where(LiveSession.session_code == code)
    account = text_of(params, "accountId")
    if account:
        stmt = stmt.where(LiveSession.account_id == int(account))
    owner = text_of(params, "responsibleUserId")
    if owner:
        stmt = stmt.where(LiveSession.responsible_user_id == int(owner))
    platform = text_of(params, "platform")
    if platform:
        stmt = stmt.where(LiveSession.platform == platform)
    status = text_of(params, "sessionStatus") or text_of(params, "status")
    if status:
        stmt = stmt.where(LiveSession.session_status == status)
    level = text_of(params, "riskLevel")
    if level:
        stmt = stmt.where(LiveSession.risk_level == level)
    group = text_of(params, "ipGroupId")
    if group:
        stmt = stmt.where(LiveSession.ip_group_id == int(group))
    tab = text_of(params, "tab")
    if tab in {"risk", "pendingRisk"}:
        stmt = stmt.where(LiveSession.session_status.in_(("PENDING_RISK_CHECK", "APPROVED")))
    kind = text_of(params, "supplement")
    if kind == "yes":
        stmt = stmt.where(LiveSession.is_supplement == 1)
    elif kind == "normal":
        stmt = stmt.where(LiveSession.is_supplement == 0)
    rows = list(get_session().scalars(stmt.order_by(LiveSession.plan_start_time.desc(), LiveSession.id.desc())))
    start = text_of(params, "planFrom") or text_of(params, "dateFrom")
    end = text_of(params, "planTo") or text_of(params, "dateTo")
    if start:
        rows = [row for row in rows if (row.plan_start_time and str(row.plan_start_time)[:10] >= start[:10])]
    if end:
        rows = [row for row in rows if (row.plan_start_time and str(row.plan_start_time)[:10] <= end[:10])]
    return rows


def _list_item(row: LiveSession) -> dict:
    report = _report(row.id)
    account = get_session().get(PlatformAccount, row.account_id) if row.account_id else None
    person = get_session().get(Realname, row.realname_id) if row.realname_id else None
    fact = risk.cert_fact(row.realname_id) if row.realname_id else {"tone": "", "message": ""}
    mode = view_mode()
    item = {
        "id": row.id,
        "sessionCode": row.session_code,
        "date": (row.actual_start_time or row.plan_start_time).strftime("%Y-%m-%d") if (row.actual_start_time or row.plan_start_time) else "",
        "platform": row.platform,
        "platformLabel": PLATFORM_LABEL.get(row.platform or "", row.platform or ""),
        "accountId": row.account_id,
        "accountName": (account.nickname or account.account_no) if account else "",
        "topic": row.topic,
        "sessionStatus": row.session_status,
        "sessionStatusLabel": STATUS_LABEL.get(row.session_status, row.session_status),
        "isSupplement": int(row.is_supplement or 0) == 1,
    }
    if mode == "finance":
        item.update(_money_bits(report))
        return item
    item.update(
        {
            "realnameName": person.name if person else "",
            "certWarning": fact["message"] if fact["tone"] == "danger" else "",
            "responsibleUserId": row.responsible_user_id,
            "responsibleName": user_name(row.responsible_user_id),
            "planStartTime": when_text(row.plan_start_time),
            "riskScore": row.risk_score,
            "riskLevel": row.risk_level or "",
            "riskLevelLabel": "补录" if row.is_supplement and not row.risk_level else risk.level_label(row.risk_level),
            "entryStatus": "" if report is None else report.entry_status,
            "entryStatusLabel": "未录" if report is None else ENTRY_LABEL.get(report.entry_status, report.entry_status),
            "footballSyncStatus": row.football_sync_status,
            "footballSyncLabel": SYNC_LABEL.get(row.football_sync_status, ""),
            "durationText": duration_text(report.duration_minutes if report else None),
            "viewerCount": None if report is None else report.viewer_count,
        }
    )
    if mode == "full" and show_money(row):
        item.update(_money_bits(report))
    return item


def _money_bits(report: LiveReport | None) -> dict:
    if report is None:
        return {"gmv": None, "refundAmount": None, "adCost": None, "costTotal": None, "roas": None}
    total = _cost_total(report.session_id)
    return {
        "gmv": money_text(report.gmv),
        "refundAmount": money_text(report.refund_amount),
        "adCost": money_text(report.ad_cost),
        "costTotal": money_text(total),
        "roas": divide(report.gmv, total),
    }


def _full(row: LiveSession) -> dict:
    data = _list_item(row)
    if view_mode() == "finance":
        data["checks"] = []
        return data
    report = _report(row.id)
    data.update(
        {
            "planEndTime": when_text(row.plan_end_time),
            "actualStartTime": when_text(row.actual_start_time),
            "actualEndTime": when_text(row.actual_end_time),
            "approverName": "系统" if row.approve_opinion == "系统自动放行" else user_name(row.approver_user_id),
            "approveOpinion": row.approve_opinion or "",
            "approvedAt": when_text(row.approved_at),
            "cancelReason": row.cancel_reason or "",
            "ipGroupId": row.ip_group_id,
            "authorId": row.author_id,
            "authorName": _author_name(row.author_id),
            "ipGroupName": _group_name(row.ip_group_id),
            "devices": _device_views(row.id),
            "conclusion": _conclusion(row),
            "checks": _checks(row.id),
            "rounds": _rounds(row.id),
            "timeline": timeline_of(row.id) if False else [],
            "report": None if report is None else _report_view(row, report),
            "actions": _actions(row, report),
        }
    )
    from app.domains.live.common import timeline_of as lines

    data["timeline"] = lines(row.id)
    return data


def timeline_of(session_id: int):
    from app.domains.live.common import timeline_of as lines

    return lines(session_id)


def _conclusion(row: LiveSession) -> str:
    if row.is_supplement and not row.risk_level:
        return "补录"
    if row.risk_level == "RED":
        return "禁止开播，请整改后重新风控"
    if row.risk_level == "YELLOW" and row.session_status == "PENDING_RISK_CHECK":
        return "已提交运营总监审批"
    if row.risk_level == "GREEN":
        return "风控通过，可以开播"
    return ""


def _checks(session_id: int) -> list[dict]:
    latest = get_session().scalar(select(func.max(LiveRiskCheck.check_round)).where(LiveRiskCheck.session_id == session_id))
    if not latest:
        return []
    rows = list(get_session().scalars(select(LiveRiskCheck).where(LiveRiskCheck.session_id == session_id, LiveRiskCheck.check_round == latest)))
    return [
        {
            "item": row.check_item,
            "itemLabel": risk.LABELS.get(row.check_item, row.check_item),
            "result": row.check_result,
            "resultLabel": {"PASS": "通过", "WARN": "警告", "FAIL": "未通过"}.get(row.check_result, row.check_result),
            "score": row.score_weight,
            "detail": row.detail or "",
        }
        for row in rows
    ]


def _rounds(session_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(LiveRiskCheck).where(LiveRiskCheck.session_id == session_id).order_by(LiveRiskCheck.check_round.asc())))
    grouped: dict[int, list] = {}
    for row in rows:
        grouped.setdefault(int(row.check_round), []).append(row)
    data = []
    for number, items in grouped.items():
        score = sum(int(item.score_weight or 0) for item in items)
        data.append({"round": number, "score": score, "level": risk.level_of(score), "levelLabel": risk.level_label(risk.level_of(score))})
    return data


def _actions(row: LiveSession, report: LiveReport | None) -> dict:
    editor = has_perm("ims:live:session:register") and (broad_editor() or owns(row))
    before = row.session_status in {"PENDING_RISK_CHECK", "APPROVED"}
    return {
        "edit": editor and before,
        "cancel": has_perm("ims:live:session:cancel") and before and (broad_editor() or owns(row)),
        "approve": has_perm("ims:live:session:approve") and row.session_status == "PENDING_RISK_CHECK" and row.risk_level == "YELLOW" and not owns(row),
        "start": owns(row) and row.session_status == "APPROVED",
        "end": row.session_status == "LIVE" and (owns(row) or has_perm("ims:live:session:approve")),
        "entry": owns(row) and has_perm("ims:live:report:entry") and row.session_status == "ENDED" and (report is None or report.entry_status == "DRAFT"),
        "confirm": has_perm("ims:live:report:confirm") and report is not None and report.entry_status == "SUBMITTED" and int(report.entry_user_id or 0) != viewer_id(),
        "correct": has_perm("ims:live:report:correct") and report is not None and report.entry_status in {"SUBMITTED", "CONFIRMED"},
        "bind": has_perm("ims:live:football:bind") and row.session_status != "CANCELLED" and (broad_editor() or owns(row)),
        "rerun": editor and before,
    }


def _by_code(code: str) -> LiveSession:
    row = get_session().scalar(select(LiveSession).where(LiveSession.session_code == code))
    if row is None:
        raise BizError(1008, "您无权查看该场次")
    return row


def _editable(code: str) -> LiveSession:
    row = _by_code(code)
    require_scope(row)
    _ensure_editor(row)
    if row.session_status not in {"PENDING_RISK_CHECK", "APPROVED"}:
        raise BizError(1042, "当前场次状态不允许该操作")
    return row


def _ensure_editor(row: LiveSession) -> None:
    if not has_perm("ims:live:session:register"):
        raise BizError(1008, "您无权查看该场次")
    if not broad_editor() and not owns(row):
        raise BizError(1008, "您无权查看该场次")


def _ensure_bind(row: LiveSession) -> None:
    if not has_perm("ims:live:football:bind"):
        raise BizError(1008, "您无权查看该场次")
    if not broad_editor() and not owns(row):
        raise BizError(1008, "您无权查看该场次")


def _token(body: dict) -> str:
    from app.api.runtime import current_request

    request = current_request()
    token = ""
    if request is not None:
        token = request.headers.get("X-Client-Token") or request.headers.get("x-client-token") or ""
    if not token:
        token = body_text(body, "clientToken")
    if not token:
        one("xClientToken", "缺少幂等令牌")
    return token


def _live_account(raw, allow_idle: bool) -> PlatformAccount:
    from app.core.serialize import parse_api_id

    if raw in (None, ""):
        one("accountId", "请选择直播账号")
    row = get_session().get(PlatformAccount, int(parse_api_id(raw)))
    if row is None or row.deleted:
        raise BizError(1500, data={"fieldErrors": [{"field": "accountId", "message": "账号不存在"}]})
    if row.platform not in LIVE_PLATFORMS:
        one("accountId", "公众号不能开播")
    if not allow_idle and row.status != "IN_USE":
        raise BizError(1501, data={"fieldErrors": [{"field": "accountId", "message": "账号不在用"}]})
    if not broad_editor() and int(row.owner_user_id or 0) != viewer_id():
        raise BizError(1008, "您无权查看该场次")
    return row


def _live_person(raw) -> Realname:
    from app.core.serialize import parse_api_id

    if raw in (None, ""):
        one("realnameId", "请选择实名人")
    row = get_session().get(Realname, int(parse_api_id(raw)))
    if row is None or row.deleted:
        raise BizError(1500, data={"fieldErrors": [{"field": "realnameId", "message": "实名人不存在"}]})
    if row.status != "ENABLED":
        raise BizError(1501, data={"fieldErrors": [{"field": "realnameId", "message": "实名人已停用"}]})
    return row


def _owner(raw) -> User:
    from app.core.serialize import parse_api_id

    row = get_session().get(User, int(parse_api_id(raw)))
    if row is None or row.deleted:
        raise BizError(1500, data={"fieldErrors": [{"field": "responsibleUserId", "message": "责任人不存在"}]})
    if row.status != "ACTIVE":
        raise BizError(1501, data={"fieldErrors": [{"field": "responsibleUserId", "message": "责任人已离职"}]})
    if not broad_editor() and int(row.id) != viewer_id():
        one("responsibleUserId", "只能选择本人")
    return row


def _assets(raw, require_in_use: bool) -> list[AssetLedger]:
    if not raw:
        one("assetIds", "请选择设备")
    if isinstance(raw, str):
        raw = [item for item in raw.split(",") if item]
    from app.core.serialize import parse_api_id

    found = []
    for item in raw:
        row = get_session().get(AssetLedger, int(parse_api_id(item)))
        if row is None or row.deleted:
            raise BizError(1500, data={"fieldErrors": [{"field": "assetIds", "message": "设备不存在"}]})
        if require_in_use and row.status != "IN_USE":
            raise BizError(1501, data={"fieldErrors": [{"field": "assetIds", "message": "设备非使用中"}]})
        if row.asset_type not in {"LIVE", "SHOOT"}:
            one("assetIds", "请选择直播或拍摄设备")
        found.append(row)
    return found


def _plan_future(start: datetime, end: datetime) -> None:
    if start <= now_naive():
        one("planStartTime", "计划开播须晚于当前时间")
    if end <= start:
        one("planEndTime", "计划下播须晚于计划开播")
    if hours_between(start, end) > 24:
        one("planEndTime", "计划开播与下播跨度不能超过 24 小时")


def _bind_devices(row: LiveSession, assets: list[AssetLedger]) -> None:
    session = get_session()
    old = list(session.scalars(select(LiveSessionDevice).where(LiveSessionDevice.session_id == row.id)))
    for item in old:
        session.delete(item)
    binds = list(session.scalars(select(AssetBind).where(AssetBind.session_id == row.id, AssetBind.bind_status == "ACTIVE")))
    for item in binds:
        item.bind_status = "RELEASED"
    for asset in assets:
        save(LiveSessionDevice(session_id=row.id, asset_id=asset.id))
        save(
            AssetBind(
                asset_id=asset.id,
                session_id=row.id,
                bind_type="LIVE_USE",
                bind_status="ACTIVE",
                effective_time=now_naive(),
            )
        )


def _release(session_id: int) -> None:
    rows = list(get_session().scalars(select(AssetBind).where(AssetBind.session_id == int(session_id), AssetBind.bind_status == "ACTIVE")))
    for row in rows:
        row.bind_status = "RELEASED"
    get_session().flush()


def _report(session_id: int) -> LiveReport | None:
    return get_session().scalar(select(LiveReport).where(LiveReport.session_id == int(session_id)))


def _entry_target(code: str) -> tuple[LiveSession, LiveReport]:
    row = _by_code(code)
    require_scope(row)
    if not owns(row) or not has_perm("ims:live:report:entry"):
        raise BizError(1008, "您无权查看该场次")
    if row.session_status != "ENDED":
        raise BizError(1042, "下播后才能录入")
    report = _report(row.id)
    if report and report.entry_status in {"SUBMITTED", "CONFIRMED"}:
        raise BizError(1047, "下播数据已提交，修改请走更正单")
    if report is None:
        report = LiveReport(session_id=row.id, entry_status="DRAFT", version=1, actual_start=row.actual_start_time, actual_end=row.actual_end_time)
        if row.actual_start_time and row.actual_end_time:
            report.duration_minutes = int(hours_between(row.actual_start_time, row.actual_end_time) * 60)
    return row, report


def _fill_report(report: LiveReport, row: LiveSession, body: dict, strict: bool) -> None:
    start = parse_dt(body.get("actualStart") or body.get("actualStartTime") or report.actual_start or row.actual_start_time, "actualStart", "实际开始", required=strict)
    end = parse_dt(body.get("actualEnd") or body.get("actualEndTime") or report.actual_end or row.actual_end_time, "actualEnd", "实际结束", required=strict)
    if start and end and end <= start:
        one("actualEnd", "实际结束须晚于实际开始")
    report.actual_start = start or report.actual_start
    report.actual_end = end or report.actual_end
    if report.actual_start and report.actual_end:
        report.duration_minutes = int((report.actual_end - report.actual_start).total_seconds() // 60)
    mapping = {
        "gmv": ("gmv", "GMV", money_of),
        "orderCount": ("order_count", "订单数", int_of),
        "viewerCount": ("viewer_count", "观看人数", int_of),
        "peakOnline": ("peak_online", "峰值在线", int_of),
        "newFans": ("new_fans", "涨粉数", int_of),
        "refundAmount": ("refund_amount", "退款额", money_of),
        "adCost": ("ad_cost", "投放成本", money_of),
    }
    missing = []
    for key, (attr, label, parser) in mapping.items():
        if key in body and body.get(key) not in (None, ""):
            setattr(report, attr, parser(body.get(key), key, label, required=True))
        elif strict and getattr(report, attr) in (None, ""):
            missing.append(label)
    if missing:
        raise BizError(1046, "下播数据必填项缺失：" + "、".join(missing))


def _require_report(body: dict) -> None:
    missing = []
    for key, label in REPORT_FIELDS:
        if body.get(key) in (None, ""):
            missing.append(label)
    if body.get("actualStart") in (None, "") and body.get("actualStartTime") in (None, ""):
        missing.append("实际开始")
    if body.get("actualEnd") in (None, "") and body.get("actualEndTime") in (None, ""):
        missing.append("实际结束")
    if missing:
        raise BizError(1046, "下播数据必填项缺失：" + "、".join(missing))


def _save_costs(row: LiveSession, body: dict, report: LiveReport, replace: bool = False) -> None:
    session = get_session()
    if replace or "costs" in body:
        old = list(session.scalars(select(LiveCost).where(LiveCost.session_id == row.id)))
        for item in old:
            session.delete(item)
        session.flush()
    lines = body.get("costs") or []
    for line in lines:
        kind = body_text(line, "costType") or "GIFT"
        if kind not in {"AD", "RECHARGE", "GIFT", "SAMPLE"}:
            raise BizError(1503, data={"field": "costType"})
        amount = money_of(line.get("amount"), "amount", "金额", required=True)
        ref = line.get("refRechargeId") or line.get("rechargeId")
        ref_id = int(ref) if ref not in (None, "") else None
        if ref_id:
            recharge = session.get(Recharge, ref_id)
            if recharge is None:
                raise BizError(1500, data={"fieldErrors": [{"field": "refRechargeId", "message": "冲话费记录不存在"}]})
        save(LiveCost(session_id=row.id, cost_type=kind, amount=amount, ref_recharge_id=ref_id, remark=limit_text(line.get("remark"), "remark", "备注", 256)))
    if report.ad_cost is not None:
        existing = session.scalar(select(LiveCost).where(LiveCost.session_id == row.id, LiveCost.cost_type == "AD"))
        if existing is None:
            save(LiveCost(session_id=row.id, cost_type="AD", amount=report.ad_cost, remark="投放成本"))
        else:
            existing.amount = report.ad_cost
            session.flush()


def _cost_total(session_id: int) -> Decimal:
    rows = list(get_session().scalars(select(LiveCost).where(LiveCost.session_id == int(session_id))))
    return sum((Decimal(row.amount or 0) for row in rows), Decimal("0"))


def _report_view(row: LiveSession, report: LiveReport) -> dict:
    total = _cost_total(row.id)
    mode = view_mode()
    data = {
        "sessionCode": row.session_code,
        "entryStatus": report.entry_status,
        "entryStatusLabel": ENTRY_LABEL.get(report.entry_status, report.entry_status),
        "actualStart": when_text(report.actual_start),
        "actualEnd": when_text(report.actual_end),
        "durationMinutes": report.duration_minutes,
        "durationText": duration_text(report.duration_minutes),
        "orderCount": report.order_count,
        "viewerCount": report.viewer_count,
        "peakOnline": report.peak_online,
        "newFans": report.new_fans,
        "version": report.version,
        "entryUserName": user_name(report.entry_user_id),
        "confirmUserName": user_name(report.confirm_user_id),
        "unitPrice": divide(report.gmv, report.order_count) if show_money(row) else None,
        "uvValue": divide(report.gmv, report.viewer_count) if show_money(row) else None,
        "canEntry": False,
        "locked": report.entry_status in {"SUBMITTED", "CONFIRMED"},
    }
    if show_money(row):
        data.update(_money_bits(report))
        data["unitPrice"] = divide(report.gmv, report.order_count)
        data["uvValue"] = divide(report.gmv, report.viewer_count)
        data["roas"] = divide(report.gmv, total)
        data["costTotal"] = money_text(total)
        data["costs"] = _cost_views(row.id)
        data["rechargeHint"] = _recharge_hint(row.id)
    if mode == "finance":
        for key in ("orderCount", "viewerCount", "peakOnline", "newFans", "durationText", "actualStart", "actualEnd"):
            data.pop(key, None)
    return data


def _cost_views(session_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(LiveCost).where(LiveCost.session_id == int(session_id))))
    labels = {"AD": "投放", "RECHARGE": "充值", "GIFT": "礼物", "SAMPLE": "样品"}
    return [
        {"id": row.id, "costType": row.cost_type, "costTypeLabel": labels.get(row.cost_type, row.cost_type), "amount": money_text(row.amount), "refRechargeId": row.ref_recharge_id, "remark": row.remark or ""}
        for row in rows
    ]


def _recharge_hint(session_id: int) -> str:
    rows = list(get_session().scalars(select(LiveCost).where(LiveCost.session_id == int(session_id), LiveCost.cost_type == "RECHARGE")))
    for row in rows:
        if not row.ref_recharge_id:
            continue
        recharge = get_session().get(Recharge, row.ref_recharge_id)
        if recharge is None:
            continue
        linked = Decimal(int(recharge.amount_fen or 0)) / Decimal(100)
        diff = abs(Decimal(row.amount or 0) - linked)
        if diff != 0:
            return f"与冲话费记录差 ¥{diff.quantize(Decimal('0.01')):.2f}"
    return ""


def _report_numbers(report: LiveReport) -> dict:
    return {
        "gmv": money_text(report.gmv),
        "orderCount": report.order_count,
        "viewerCount": report.viewer_count,
        "peakOnline": report.peak_online,
        "newFans": report.new_fans,
        "refundAmount": money_text(report.refund_amount),
        "adCost": money_text(report.ad_cost),
        "actualStart": when_text(report.actual_start),
        "actualEnd": when_text(report.actual_end),
    }


def _apply_correction(report: LiveReport, body: dict) -> bool:
    changed = False
    pairs = {
        "gmv": ("gmv", money_of, "GMV"),
        "orderCount": ("order_count", int_of, "订单数"),
        "viewerCount": ("viewer_count", int_of, "观看人数"),
        "peakOnline": ("peak_online", int_of, "峰值在线"),
        "newFans": ("new_fans", int_of, "涨粉数"),
        "refundAmount": ("refund_amount", money_of, "退款额"),
        "adCost": ("ad_cost", money_of, "投放成本"),
    }
    for key, (attr, parser, label) in pairs.items():
        if key in body and body.get(key) not in (None, ""):
            value = parser(body.get(key), key, label, required=True)
            if getattr(report, attr) != value:
                setattr(report, attr, value)
                changed = True
    return changed or "costs" in body


def _room_id(raw) -> int:
    text = str(raw).strip()
    if not text.isdigit() or len(text) > 20:
        one("roomId", "直播间编号须为不超过 20 位的数字")
    return int(text)


def _display_room(tenant_id: int, room_id: int):
    from app.integrations.football_live.reader import get_room_display

    return get_room_display(tenant_id, room_id)


def _sync_row(row: LiveSession, force: bool) -> None:
    from app.core.redis_client import get_redis

    key = f"ims:live:sync:{row.id}"
    if not force:
        try:
            if not get_redis().set(key, "1", nx=True, ex=10):
                return
        except Exception:
            pass
    ctx = get_ctx()
    loaded = football_row_or_unavailable(lambda: _display_room(ctx.tenant_id if ctx else 1, int(row.football_room_id)))
    if loaded in (None, UNAVAILABLE) or int((loaded or {}).get("deleted") or 0) == 1:
        row.football_sync_status = "FAILED"
        save(row)
        get_session().add(Outbox(topic="live.football.sync", payload={"sessionId": row.id, "roomId": row.football_room_id}, status="PENDING", retry_count=0))
        get_session().flush()
        if loaded is None or (isinstance(loaded, dict) and int(loaded.get("deleted") or 0) == 1):
            raise BizError(1041, "Football 直播间不存在或不属于本租户")
        return
    row.football_sync_status = "SYNCED"
    row.last_football_sync_at = now_naive()
    save(row)
    save(
        LiveDataSnapshot(
            session_id=row.id,
            source="FOOTBALL",
            viewer_count=_count(loaded.get("viewer_count")),
            like_count=_count(loaded.get("like_count")),
            reserve_count=_count(loaded.get("reserve_count")),
            room_status=str(loaded.get("status") or ""),
            room_start_time=_as_dt(loaded.get("start_time")),
            room_end_time=_as_dt(loaded.get("end_time")),
            captured_at=now_naive(),
        )
    )


def _count(value):
    if value in (None, ""):
        return None
    return int(value)


def _as_dt(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return parse_dt(value, "startTime", "时间", required=False)


def _room_view(row: dict) -> dict:
    status = {1: "未开始", 2: "直播中", 3: "已结束", 4: "过期", 5: "暂停"}.get(int(row.get("status") or 0), "")
    screen = {1: "横屏", 2: "竖屏"}.get(int(row.get("screen_type") or 0), "")
    watch = {1: "公开", 2: "付费", 3: "加密"}.get(int(row.get("watch_type") or 0), "")
    start = row.get("start_time")
    end = row.get("end_time")
    minutes = None
    if start and end:
        try:
            minutes = int(((_as_dt(end) - _as_dt(start)).total_seconds()) // 60)
        except Exception:
            minutes = None
    return {
        "liveName": row.get("live_name") or "",
        "nickname": row.get("nickname") or "",
        "avatarUrl": row.get("avatar_url") or "",
        "liveId": row.get("live_id") or "",
        "cover": row.get("cover") or "",
        "statusLabel": status,
        "screenLabel": screen,
        "watchLabel": watch,
        "startTime": when_text(_as_dt(start)) if start else "",
        "endTime": when_text(_as_dt(end)) if end else "",
        "durationText": duration_text(minutes) if minutes is not None else "",
        "viewUrl": row.get("view_url") or "",
        "playbackUrl": row.get("playback_url") or "",
        "serverUrl": row.get("server_url") or "",
        "viewerCount": row.get("viewer_count") if row.get("viewer_count") is not None else 0,
        "likeCount": row.get("like_count") if row.get("like_count") is not None else 0,
        "reserveCount": row.get("reserve_count") if row.get("reserve_count") is not None else 0,
    }


def _device_views(session_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(LiveSessionDevice).where(LiveSessionDevice.session_id == int(session_id))))
    data = []
    for row in rows:
        asset = get_session().get(AssetLedger, row.asset_id)
        if asset:
            data.append({"id": asset.id, "assetCode": asset.asset_code, "assetName": asset.asset_name, "status": asset.status})
    return data


def _author_name(author_id) -> str:
    if not author_id:
        return ""
    row = get_session().get(Author, int(author_id))
    return (row.author_name or row.name) if row else ""


def _group_name(group_id) -> str:
    if not group_id:
        return ""
    row = get_session().get(IpGroup, int(group_id))
    return (row.group_name or row.name) if row else ""


def _supplement(ident: int) -> LiveSupplement:
    row = get_session().get(LiveSupplement, int(ident))
    if row is None or row.deleted:
        raise BizError(1008, "您无权查看该场次")
    return row


def _supplement_view(row: LiveSupplement) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "statusLabel": {"PENDING": "待审批", "APPROVED": "已通过", "REJECTED": "已退回"}.get(row.status, row.status),
        "reason": row.supplement_reason or "",
        "opinion": row.opinion or "",
        "applicantName": user_name(row.applicant_id),
        "sessionId": row.session_id,
        "sessionCode": get_session().get(LiveSession, row.session_id).session_code if row.session_id else "",
        "register": row.register_json or {},
        "report": row.report_json or {},
    }


def _supplement_times(body: dict) -> None:
    start = parse_dt(body.get("planStartTime"), "planStartTime", "计划开播")
    end = parse_dt(body.get("planEndTime"), "planEndTime", "计划下播")
    now = now_naive()
    if start >= now:
        one("planStartTime", "补录时间须早于当前时间")
    if (now.date() - start.date()).days > 365:
        one("planStartTime", "最早可补录 365 天内")
    if end <= start:
        one("planEndTime", "计划下播须晚于计划开播")
    if end > now:
        one("planEndTime", "补录时间须早于当前时间")


def _materialize_supplement(sheet: LiveSupplement) -> LiveSession:
    body = dict(sheet.register_json or {})
    account = _live_account(body.get("accountId"), allow_idle=True)
    person = _live_person(body.get("realnameId"))
    owner = _owner(body.get("responsibleUserId") or sheet.applicant_id)
    assets = _assets(body.get("assetIds") or body.get("deviceIds"), require_in_use=False)
    start = parse_dt(body.get("planStartTime"), "planStartTime", "计划开播")
    end = parse_dt(body.get("planEndTime"), "planEndTime", "计划下播")
    topic = limit_text(body.get("topic"), "topic", "主题", 256, required=True)
    row = LiveSession(
        name=topic[:100],
        status="ENABLED",
        session_code=session_code(account.platform, start),
        platform=account.platform,
        account_id=account.id,
        realname_id=person.id,
        responsible_user_id=owner.id,
        ip_group_id=account.ip_group_id,
        author_id=account.author_user_id,
        topic=topic,
        plan_start_time=start,
        plan_end_time=end,
        actual_start_time=start,
        actual_end_time=end,
        session_status="ENDED",
        football_sync_status="UNLINKED",
        is_supplement=1,
        supplement_id=sheet.id,
        client_token=f"supplement-{sheet.id}",
    )
    save(row)
    _bind_devices(row, assets)
    _release(row.id)
    report_body = dict(sheet.report_json or {})
    report = LiveReport(session_id=row.id, entry_status="SUBMITTED", version=1, entry_user_id=sheet.applicant_id, submitted_at=now_naive())
    _fill_report(report, row, report_body, strict=True)
    save(report)
    _save_costs(row, {"costs": sheet.cost_json or []}, report)
    trace(row.id, "SUPPLEMENT", "历史补录", sheet.supplement_reason or "")
    return row
