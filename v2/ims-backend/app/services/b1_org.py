"""组织架构同步页：指标、差异、事件、对账明细。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select

from app.core.clock import now_naive, parse_input_datetime
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result, parse_page
from app.db.session import get_session
from app.domains.auth.model import OrgSyncBatch, OrgSyncBatchItem, OrgSyncEvent, OrgSyncEventAttempt, UserMapping
from app.domains.system.model import ChangeLog, Dept, User, UserDept, UserRole
from app.services.exchange import remember_export
from app.services.org_sync import _ATTEMPT_TRIGGER, _execute


def sync_metrics() -> dict:
    session = get_session()
    current = now_naive()
    start_yesterday = datetime(current.year, current.month, current.day) - timedelta(days=1)
    end_yesterday = start_yesterday + timedelta(days=1)
    since = current - timedelta(hours=24)
    user_total = int(
        session.scalar(select(func.count()).select_from(User).where(User.status.in_(("ACTIVE", "FROZEN")))) or 0
    )
    yesterday = int(
        session.scalar(
            select(func.count()).select_from(OrgSyncEvent).where(OrgSyncEvent.event_time >= start_yesterday, OrgSyncEvent.event_time < end_yesterday)
        )
        or 0
    )
    pending = int(
        session.scalar(
            select(func.count()).select_from(OrgSyncEvent).where(OrgSyncEvent.status.in_(("PENDING", "RETRYING", "DEAD")))
        )
        or 0
    )
    dead = int(session.scalar(select(func.count()).select_from(OrgSyncEvent).where(OrgSyncEvent.status == "DEAD")) or 0)
    delays = [
        int(row.delay_seconds)
        for row in session.scalars(
            select(OrgSyncEvent).where(
                OrgSyncEvent.status == "SUCCESS",
                OrgSyncEvent.processed_time.is_not(None),
                OrgSyncEvent.processed_time >= since,
                OrgSyncEvent.delay_seconds.is_not(None),
            )
        )
    ]
    avg = round(sum(delays) / len(delays) / 60, 1) if delays else None
    ordered = sorted(delays)
    p95 = None
    if ordered:
        index = max(0, int(round(0.95 * (len(ordered) - 1))))
        p95 = round(ordered[index] / 60, 1)
    success = int(
        session.scalar(
            select(func.count()).select_from(OrgSyncEvent).where(OrgSyncEvent.status == "SUCCESS", OrgSyncEvent.processed_time >= since)
        )
        or 0
    )
    attempts = success + int(
        session.scalar(
            select(func.count()).select_from(OrgSyncEvent).where(
                OrgSyncEvent.status.in_(("RETRYING", "DEAD")),
                OrgSyncEvent.update_time >= since,
            )
        )
        or 0
    )
    rate = round(success / attempts, 4) if attempts else None
    recent_fail = session.scalar(
        select(OrgSyncBatch).where(OrgSyncBatch.error_code == 5003, OrgSyncBatch.finished_at >= current - timedelta(minutes=10))
    )
    last_two = list(session.scalars(select(OrgSyncBatch).order_by(OrgSyncBatch.id.desc()).limit(2)))
    twice = len(last_two) == 2 and all(row.status == "FAILED" for row in last_two)
    return {
        "userTotal": user_total,
        "yesterdayEventCount": yesterday,
        "pendingEventCount": pending,
        "deadEventCount": dead,
        "avgDelayMinutes": avg,
        "p95DelayMinutes": p95,
        "successRate24h": rate,
        "dingtalkUnavailable": recent_fail is not None,
        "reconcileFailedTwice": twice,
    }


def diff_summary() -> dict:
    return {item["category"]: item["count"] for item in _diff_counts()}


def diff_page(params: dict) -> dict:
    category = str(params.get("category") or "OVERRIDE")
    allowed = {"OVERRIDE", "PENDING_ASSIGN", "LOCAL_ORPHAN", "SAME_NAME", "UNBOUND"}
    if category not in allowed:
        raise BizError(1001, data={"fieldErrors": [{"field": "category", "message": "差异类别不正确"}]})
    page = parse_page(params)
    rows = _diff_rows(category, params)
    start = (page.page_no - 1) * page.page_size
    return page_result(rows[start : start + page.page_size], len(rows), page)


def event_page(params: dict) -> dict:
    page = parse_page(params, allowed_sort=["eventTime", "processedTime"])
    stmt = _event_stmt(params)
    session = get_session()
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    order_col = OrgSyncEvent.processed_time if page.sort_field == "processedTime" else OrgSyncEvent.event_time
    stmt = stmt.order_by(order_col.asc() if page.sort_order == "asc" else order_col.desc())
    rows = list(session.scalars(stmt.offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    return page_result([_event_row(row) for row in rows], total, page)


def event_detail(ident: int) -> dict:
    row = _visible_event(ident)
    payload = _mask_payload(row.payload or {})
    attempts = list(
        get_session().scalars(select(OrgSyncEventAttempt).where(OrgSyncEventAttempt.event_row_id == row.id).order_by(OrgSyncEventAttempt.id.asc()))
    )
    data = _event_row(row)
    data["payload"] = payload
    data["receivedTime"] = _fmt(row.received_time)
    data["attempts"] = [
        {
            "attemptNo": item.attempt_no,
            "trigger": item.trigger,
            "operatorId": item.operator_id,
            "startTime": _fmt(item.start_time),
            "endTime": _fmt(item.end_time),
            "result": item.result,
            "errorCode": item.error_code,
            "errorMsg": item.error_msg,
        }
        for item in attempts
    ]
    return data


def retry_event(ident: int) -> dict:
    row = _visible_event(ident)
    if row.status in {"SUCCESS", "PENDING"}:
        raise BizError(1286)
    if row.status == "DEAD":
        row.retry_count = 0
    row.status = "PENDING"
    row.next_retry_at = None
    token = _ATTEMPT_TRIGGER.set("RETRY")
    try:
        return _execute(row)
    finally:
        _ATTEMPT_TRIGGER.reset(token)


def replay_preview(params: dict) -> dict:
    rows = _replay_rows(params)
    return {"count": len(rows)}


def replay_events(body: dict) -> dict:
    rows = _replay_rows(body)
    if not rows:
        return {"count": 0}
    token = _ATTEMPT_TRIGGER.set("REPLAY")
    try:
        for row in rows:
            if row.status == "DEAD":
                row.retry_count = 0
            row.status = "PENDING"
            row.next_retry_at = None
            _execute(row)
    finally:
        _ATTEMPT_TRIGGER.reset(token)
    return {"count": len(rows)}


def batch_page(params: dict) -> dict:
    page = parse_page(params)
    stmt = select(OrgSyncBatch)
    start, end = _range(params, default_days=30, max_days=366, field="startTime")
    if start:
        stmt = stmt.where(OrgSyncBatch.started_at >= start)
    if end:
        stmt = stmt.where(OrgSyncBatch.started_at <= end)
    if params.get("triggerType"):
        stmt = stmt.where(OrgSyncBatch.trigger_type == params.get("triggerType"))
    if params.get("status"):
        stmt = stmt.where(OrgSyncBatch.status == params.get("status"))
    session = get_session()
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(session.scalars(stmt.order_by(OrgSyncBatch.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    return page_result([_batch_row(row) for row in rows], total, page)


def batch_detail(ident: int) -> dict:
    row = get_session().get(OrgSyncBatch, ident)
    if row is None:
        raise BizError(1504)
    data = _batch_row(row)
    data["summary"] = {
        "deptCreated": row.dept_created,
        "deptUpdated": row.dept_updated,
        "deptDisabled": row.dept_disabled,
        "userCreated": row.user_created,
        "userUpdated": row.user_updated,
        "userResigned": row.user_resigned,
        "unassigned": row.unassigned_count,
        "sameName": len(row.same_name_notes or []),
        "failCount": row.fail_count,
    }
    return data


def batch_items(ident: int, params: dict) -> dict:
    if get_session().get(OrgSyncBatch, ident) is None:
        raise BizError(1504)
    page = parse_page(params)
    stmt = select(OrgSyncBatchItem).where(OrgSyncBatchItem.batch_id == ident)
    stmt = _scope_dept(stmt, OrgSyncBatchItem.dept_id)
    if params.get("result"):
        stmt = stmt.where(OrgSyncBatchItem.result == params.get("result"))
    session = get_session()
    total = int(session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(session.scalars(stmt.order_by(OrgSyncBatchItem.id.asc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)))
    data = [
        {
            "id": row.id,
            "objectType": row.object_type,
            "objectId": row.object_id,
            "objectName": row.object_name,
            "action": row.action,
            "beforeValue": row.before_value,
            "afterValue": row.after_value,
            "result": row.result,
            "errorMsg": row.error_msg,
        }
        for row in rows
    ]
    return page_result(data, total, page)


def export_events(params: dict) -> dict:
    rows = list(get_session().scalars(_event_stmt(params).order_by(OrgSyncEvent.event_time.desc()).limit(50001)))
    if len(rows) > 50000:
        raise BizError(1001, "超过 5 万行，请缩小范围")
    header = ["事件类型", "事件编号", "人员", "工号", "变更前部门", "变更后部门", "同步状态", "重试次数", "事件时间", "同步完成时间"]
    body = [
        [
            row.biz_type or "",
            row.event_id,
            row.subject_name or "",
            "",
            row.before_dept_names or "",
            row.after_dept_names or "",
            row.status,
            row.retry_count,
            _fmt(row.event_time),
            _fmt(row.processed_time),
        ]
        for row in rows
    ]
    stamp = now_naive().strftime("%Y%m%d%H%M")
    return remember_export(f"同步事件_{stamp}.xlsx", header, body, "org_event")


def export_batch(ident: int) -> dict:
    batch = get_session().get(OrgSyncBatch, ident)
    if batch is None:
        raise BizError(1504)
    stmt = select(OrgSyncBatchItem).where(OrgSyncBatchItem.batch_id == ident)
    stmt = _scope_dept(stmt, OrgSyncBatchItem.dept_id)
    rows = list(get_session().scalars(stmt.limit(50001)))
    if len(rows) > 50000:
        raise BizError(1001, "超过 5 万行，请缩小范围")
    header = ["对象类型", "对象名称", "动作", "变更前", "变更后", "结果", "失败原因"]
    body = [[row.object_type, row.object_name or "", row.action, row.before_value or "", row.after_value or "", row.result, row.error_msg or ""] for row in rows]
    stamp = batch.started_at.strftime("%Y%m%d%H%M") if batch.started_at else "batch"
    return remember_export(f"对账明细_{stamp}.xlsx", header, body, "org_batch")


def user_detail(ident: int) -> dict:
    user = get_session().get(User, ident)
    if user is None or not _user_visible(user):
        raise BizError(1504)
    session = get_session()
    mapping = session.scalar(select(UserMapping).where(UserMapping.user_id == user.id))
    depts = []
    main_name = ""
    for link in session.scalars(select(UserDept).where(UserDept.user_id == user.id)):
        dept = session.get(Dept, link.dept_id)
        if dept is None:
            continue
        depts.append(dept.name)
        if link.is_main:
            main_name = dept.name
    roles = []
    for link in session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 0)):
        from app.domains.system.model import Role
        from app.domains.auth.model import PositionRoleRule

        role = session.get(Role, link.role_id)
        rule = session.get(PositionRoleRule, link.rule_id) if link.rule_id else None
        roles.append(
            {
                "roleId": link.role_id,
                "name": role.name if role else "",
                "source": link.source,
                "status": role.status if role else "",
                "ruleName": rule.rule_name if rule else None,
                "ruleVersion": link.rule_version,
                "revokeAt": _fmt(link.revoke_at),
            }
        )
    events = list(
        session.scalars(
            select(OrgSyncEvent).where(OrgSyncEvent.subject_user_id == user.id).order_by(OrgSyncEvent.id.desc()).limit(10)
        )
    )
    return {
        "id": user.id,
        "nickname": user.nickname,
        "username": user.username,
        "empNo": user.emp_no,
        "status": user.status,
        "mainDeptName": main_name,
        "deptNames": depts,
        "positionCode": user.position_code,
        "dingBound": mapping is not None,
        "lastSyncTime": _fmt(mapping.last_sync_time) if mapping else None,
        "source": user.source,
        "roles": roles,
        "dataScopeText": _scope_text(user),
        "menuCount": _menu_count(user.id),
        "events": [_event_row(row) for row in events],
    }


def _diff_counts() -> list[dict]:
    return [{"category": key, "count": len(_diff_rows(key, {}))} for key in ("OVERRIDE", "PENDING_ASSIGN", "LOCAL_ORPHAN", "SAME_NAME", "UNBOUND")]


def _diff_rows(category: str, params: dict) -> list[dict]:
    session = get_session()
    keyword = str(params.get("keyword") or "").strip()
    if category == "OVERRIDE":
        stmt = select(ChangeLog).where(ChangeLog.reason == "DINGTALK_OVERRIDE")
        start, end = _range(params, default_days=30, max_days=366)
        if start:
            stmt = stmt.where(ChangeLog.create_time >= start)
        if end:
            stmt = stmt.where(ChangeLog.create_time <= end)
        rows = []
        for item in session.scalars(stmt.order_by(ChangeLog.id.desc())):
            dept = session.get(Dept, item.biz_id)
            text = " ".join([dept.name if dept else "", item.field_label or "", item.before_value or "", item.after_value or ""])
            if keyword and keyword not in text:
                continue
            rows.append(
                {
                    "id": item.id,
                    "time": _fmt(item.create_time),
                    "deptName": dept.name if dept else "",
                    "field": item.field_label,
                    "beforeValue": item.before_value,
                    "afterValue": item.after_value,
                    "source": str(item.biz_id),
                }
            )
        return rows
    if category == "PENDING_ASSIGN":
        pending = session.scalar(select(Dept).where(Dept.source == "SYSTEM", Dept.name == "待分配"))
        if pending is None:
            return []
        users = list(session.scalars(select(User).where(User.main_dept_id == pending.id, User.status.in_(("ACTIVE", "FROZEN")))))
        return [_person(user) for user in users if _match_user(user, keyword)]
    if category == "LOCAL_ORPHAN":
        rows = []
        for dept in session.scalars(select(Dept).where(Dept.local_orphan == 1)):
            if keyword and keyword not in dept.name:
                continue
            parent = session.get(Dept, int(dept.parent_id or 0))
            members = int(session.scalar(select(func.count()).select_from(UserDept).where(UserDept.dept_id == dept.id)) or 0)
            rows.append(
                {
                    "id": dept.id,
                    "deptName": dept.name,
                    "parentName": parent.name if parent else "",
                    "memberCount": members,
                    "time": _fmt(dept.update_time),
                }
            )
        return rows
    if category == "SAME_NAME":
        stmt = select(OrgSyncBatchItem).where(OrgSyncBatchItem.action == "SAME_NAME")
        start, end = _range(params, default_days=30, max_days=366)
        if start:
            stmt = stmt.where(OrgSyncBatchItem.create_time >= start)
        if end:
            stmt = stmt.where(OrgSyncBatchItem.create_time <= end)
        rows = []
        for item in session.scalars(stmt.order_by(OrgSyncBatchItem.id.desc())):
            text = f"{item.object_name or ''} {item.before_value or ''} {item.after_value or ''}"
            if keyword and keyword not in text:
                continue
            rows.append(
                {
                    "id": item.id,
                    "dingDept": item.after_value,
                    "localDept": item.object_name,
                    "time": _fmt(item.create_time),
                }
            )
        return rows
    users = list(session.scalars(select(User).where(User.status == "ACTIVE")))
    mapped = set(session.scalars(select(UserMapping.user_id)))
    return [_person(user) for user in users if user.id not in mapped and _match_user(user, keyword)]


def _event_stmt(params: dict):
    start, end = _range(params, default_days=7, max_days=90)
    stmt = select(OrgSyncEvent)
    if start:
        stmt = stmt.where(OrgSyncEvent.event_time >= start)
    if end:
        stmt = stmt.where(OrgSyncEvent.event_time <= end)
    keyword = str(params.get("keyword") or "").strip()
    if len(keyword) > 50:
        raise BizError(1001, data={"fieldErrors": [{"field": "keyword", "message": "关键字不能超过 50 字"}]})
    if keyword:
        matched_users = select(User.id).where(or_(User.emp_no.contains(keyword), User.nickname.contains(keyword), User.username.contains(keyword)))
        stmt = stmt.where(
            or_(
                OrgSyncEvent.subject_name.contains(keyword),
                OrgSyncEvent.event_id.contains(keyword),
                OrgSyncEvent.subject_user_id.in_(matched_users),
            )
        )
    if params.get("deptId"):
        stmt = stmt.where(OrgSyncEvent.dept_id == int(params["deptId"]))
    types = _multi(params.get("bizTypes") or params.get("bizType"))
    if types:
        stmt = stmt.where(OrgSyncEvent.biz_type.in_(types))
    statuses = _multi(params.get("statuses") or params.get("status"))
    if statuses:
        stmt = stmt.where(OrgSyncEvent.status.in_(statuses))
    return _scope_dept(stmt, OrgSyncEvent.dept_id)


def _replay_rows(params: dict) -> list[OrgSyncEvent]:
    start_raw = params.get("startTime")
    end_raw = params.get("endTime")
    if not start_raw or not end_raw:
        raise BizError(1001, data={"fieldErrors": [{"field": "startTime", "message": "请选择时间范围"}]})
    start = parse_input_datetime(str(start_raw))
    end = parse_input_datetime(str(end_raw))
    if end > now_naive():
        raise BizError(1001, data={"fieldErrors": [{"field": "endTime", "message": "结束时间不能晚于当前"}]})
    if end - start > timedelta(days=7):
        raise BizError(1001, data={"fieldErrors": [{"field": "endTime", "message": "时间跨度不能超过 7 天"}]})
    statuses = _multi(params.get("statuses") or params.get("status"))
    if not statuses:
        raise BizError(1001, data={"fieldErrors": [{"field": "statuses", "message": "请选择事件状态"}]})
    bad = [item for item in statuses if item not in {"DEAD", "RETRYING"}]
    if bad:
        raise BizError(1001, data={"fieldErrors": [{"field": "statuses", "message": "只能重放失败重试或死信"}]})
    stmt = select(OrgSyncEvent).where(OrgSyncEvent.event_time >= start, OrgSyncEvent.event_time <= end, OrgSyncEvent.status.in_(statuses))
    rows = list(get_session().scalars(stmt.order_by(OrgSyncEvent.event_time.asc())))
    if len(rows) > 1000:
        raise BizError(1001, "符合条件超过 1000 条，请缩小时间范围")
    return rows


def _visible_event(ident: int) -> OrgSyncEvent:
    row = get_session().get(OrgSyncEvent, int(ident))
    if row is None:
        raise BizError(1504)
    allowed = _dept_ids()
    if allowed is not None and row.dept_id not in allowed and not (allowed == set() and False):
        if isinstance(allowed, set) and row.dept_id not in allowed:
            raise BizError(1504)
    return row


def _scope_dept(stmt, column):
    allowed = _dept_ids()
    if allowed is None:
        return stmt
    if not allowed:
        return stmt.where(column.in_([-1]))
    return stmt.where(column.in_(list(allowed)))


def _dept_ids():
    ctx = get_ctx()
    if ctx is None or ctx.system or "ALL" in (ctx.data_scopes or set()):
        return None
    if "DEPT" in (ctx.data_scopes or set()):
        return set(ctx.dept_ids or [])
    if "SELF" in (ctx.data_scopes or set()):
        return set(ctx.dept_ids or [])
    return set()


def _user_visible(user: User) -> bool:
    allowed = _dept_ids()
    if allowed is None:
        return True
    if "SELF" in ((get_ctx().data_scopes if get_ctx() else set()) or set()) and user.id == get_ctx().user_id:
        return True
    return user.main_dept_id in allowed


def _event_row(row: OrgSyncEvent) -> dict:
    return {
        "id": row.id,
        "eventId": row.event_id,
        "eventType": row.event_type,
        "bizType": row.biz_type,
        "status": row.status,
        "subjectName": row.subject_name,
        "subjectUserId": row.subject_user_id,
        "beforeDeptNames": row.before_dept_names,
        "afterDeptNames": row.after_dept_names,
        "retryCount": row.retry_count,
        "eventTime": _fmt(row.event_time),
        "processedTime": _fmt(row.processed_time or row.processed_at),
        "lastError": row.last_error,
        "deptId": row.dept_id,
    }


def _batch_row(row: OrgSyncBatch) -> dict:
    spent = None
    if row.started_at and row.finished_at:
        spent = int((row.finished_at - row.started_at).total_seconds())
    return {
        "id": row.id,
        "startedAt": _fmt(row.started_at),
        "finishedAt": _fmt(row.finished_at),
        "triggerType": row.trigger_type or "MANUAL",
        "operatorId": row.operator_id,
        "status": row.status,
        "durationSeconds": spent,
        "diffCount": row.diff_count,
        "fixedCount": row.fixed_count,
        "failCount": row.fail_count,
        "failReason": row.fail_reason,
        "deptCreated": row.dept_created,
        "deptUpdated": row.dept_updated,
        "deptDisabled": row.dept_disabled,
        "userCreated": row.user_created,
        "userUpdated": row.user_updated,
        "userResigned": row.user_resigned,
    }


def _person(user: User) -> dict:
    dept = get_session().get(Dept, user.main_dept_id) if user.main_dept_id else None
    return {
        "id": user.id,
        "nickname": user.nickname,
        "username": user.username,
        "empNo": user.emp_no,
        "status": user.status,
        "deptName": dept.name if dept else "",
        "source": user.source,
        "time": _fmt(user.create_time),
    }


def _match_user(user: User, keyword: str) -> bool:
    if not keyword:
        return True
    dept = get_session().get(Dept, user.main_dept_id) if user.main_dept_id else None
    text = " ".join([user.nickname or "", user.username or "", user.emp_no or "", dept.name if dept else ""])
    return keyword in text


def _range(params: dict, default_days: int, max_days: int, field: str = "startTime"):
    start_raw = params.get("startTime")
    end_raw = params.get("endTime")
    if not start_raw and not end_raw:
        end = now_naive()
        return end - timedelta(days=default_days), end
    start = parse_input_datetime(str(start_raw)) if start_raw else None
    end = parse_input_datetime(str(end_raw)) if end_raw else None
    if start and end and end - start > timedelta(days=max_days):
        raise BizError(1001, data={"fieldErrors": [{"field": field, "message": f"时间范围不能超过 {max_days} 天"}]})
    return start, end


def _multi(value) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [item for item in str(value).split(",") if item]


def _fmt(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _mask_payload(payload: dict) -> dict:
    hidden = {"mobile", "email", "phone", "mobileEnc"}

    def walk(value):
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if key in hidden and item:
                    out[key] = _mask_text(str(item), key)
                else:
                    out[key] = walk(item)
            return out
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    return walk(payload)


def _mask_text(value: str, key: str) -> str:
    if key == "email" and "@" in value:
        name, host = value.split("@", 1)
        return f"{name[:1]}***@{host}"
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 7:
        return f"{digits[:3]}****{digits[-4:]}"
    return "***"


def _scope_text(user: User) -> str:
    from app.services.b1_position import scope_text_for

    return scope_text_for(user)


def _menu_count(user_id: int) -> int:
    from app.services.b1_position import _menu_count as count_menus

    return count_menus(user_id)
