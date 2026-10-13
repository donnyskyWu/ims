"""直播告警：规则、去重、处置、升级。预警中心留到 B23。"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.clock import now_naive, today
from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.session import get_session
from app.domains.live.common import in_scope, limit_text, require_scope, save, user_name, viewer_id, when_text
from app.domains.live.model import LiveAlarmRecord, LiveAlarmRule
from app.domains.master.model import LiveSession
from app.domains.message.service import send
from app.domains.resource.common import has_perm, one, text_of, user_ids_with_perm
from app.domains.system.model import Timeline
from app.domains.todo.service import todo_create
from app.integrations.dingtalk.client import send_work_notice

log = logging.getLogger("ims.live.sms")

THRESHOLD_METRICS = {"GMV_DROP", "VIEWER_DROP", "BALANCE_LOW"}
EVENT_METRICS = {"ACCOUNT_ABNORMAL", "BANNED_WORD"}
THRESHOLD_OPS = {"PCT_DROP", "LT", "GT"}
LEVELS = {"1", "2", "3"}
HANDLE_ACTIONS = {"CONFIRMED": "已确认", "HANDLED": "已处理", "FALSE_ALARM": "误报"}
LEVEL_LABEL = {"1": "L1 提示", "2": "L2 警告", "3": "L3 严重"}
STATUS_LABEL = {"UNHANDLED": "未处理", "CONFIRMED": "已确认", "HANDLED": "已处理", "FALSE_ALARM": "误报"}
SEED_RULES = (
    ("GMV 异常波动", "THRESHOLD", "GMV_DROP", "PCT_DROP", "30", 10),
    ("场观骤降", "THRESHOLD", "VIEWER_DROP", "PCT_DROP", "30", 10),
    ("话费余额低", "THRESHOLD", "BALANCE_LOW", "LT", "50", 10),
    ("账号异常状态", "EVENT", "ACCOUNT_ABNORMAL", "HIT", "0", None),
    ("违禁词命中", "EVENT", "BANNED_WORD", "HIT", "0", None),
)


def ensure_rules() -> int:
    session = get_session()
    made = 0
    for name, kind, metric, operator, threshold, window in SEED_RULES:
        existed = session.scalar(select(LiveAlarmRule).where(LiveAlarmRule.rule_name == name))
        if existed is not None:
            continue
        save(
            LiveAlarmRule(
                rule_name=name,
                rule_type=kind,
                metric=metric,
                operator=operator,
                threshold=Decimal(threshold),
                window_minutes=window,
                level="2",
                notify_role_ids=[104],
                notify_user_ids=[],
                status="DISABLED",
                version=1,
            )
        )
        made += 1
    return made


def rule_list() -> dict:
    rows = list(get_session().scalars(select(LiveAlarmRule).order_by(LiveAlarmRule.id.asc())))
    return {"list": [_rule_view(row) for row in rows], "total": len(rows), "message": "已即时生效"}


def create_rule(body: dict) -> dict:
    row = LiveAlarmRule(status="DISABLED", version=1)
    _fill_rule(row, body, creating=True)
    save(row)
    return {**_rule_view(row), "message": "已即时生效"}


def update_rule(ident: int, body: dict) -> dict:
    row = _rule(ident)
    version = body.get("version")
    if version not in (None, "") and int(version) != int(row.version or 1):
        one("version", "规则已被他人修改，请刷新后重试")
    _fill_rule(row, body, creating=False)
    row.version = int(row.version or 1) + 1
    save(row)
    return {**_rule_view(row), "message": "已即时生效"}


def set_status(ident: int, body: dict) -> dict:
    row = _rule(ident)
    status = text_of(body, "status")
    if status not in {"ENABLED", "DISABLED"}:
        raise BizError(1503, data={"fieldErrors": [{"field": "status", "message": "状态不合法"}]})
    row.status = status
    row.version = int(row.version or 1) + 1
    save(row)
    return {**_rule_view(row), "message": "已即时生效"}


def remove_rule(ident: int, body: dict) -> dict:
    row = _rule(ident)
    typed = text_of(body, "confirmName") or text_of(body, "ruleName")
    if typed != row.rule_name:
        one("confirmName", "请输入规则名称确认删除")
    from app.db.repository import Repository

    Repository(LiveAlarmRule).soft_delete(row.id)
    return {"message": "已即时生效"}


def record_page(page, params: dict) -> dict:
    rows = _records(params)
    start = (page.page_no - 1) * page.page_size
    chunk = rows[start : start + page.page_size]
    return page_result([_record_view(row) for row in chunk], len(rows), page)


def record_detail(ident: int) -> dict:
    row = _record(ident)
    data = _record_view(row)
    data["history"] = _history(row.id)
    return data


def handle(ident: int, body: dict) -> dict:
    row = _record(ident)
    action = text_of(body, "action") or text_of(body, "handleStatus")
    if action not in HANDLE_ACTIONS:
        raise BizError(1503, data={"fieldErrors": [{"field": "action", "message": "处置动作不合法"}]})
    if row.handle_status in {"HANDLED", "FALSE_ALARM"}:
        raise BizError(1042, "当前场次状态不允许该操作")
    if row.handle_status == "CONFIRMED" and action == "CONFIRMED":
        raise BizError(1042, "当前场次状态不允许该操作")
    remark = limit_text(body.get("remark") or body.get("handleRemark"), "remark", "说明", 512)
    if action in {"HANDLED", "FALSE_ALARM"} and not remark:
        one("remark", "请填写说明")
    row.handle_status = action
    row.handle_remark = remark
    row.handler_user_id = viewer_id() or None
    row.handled_at = now_naive()
    save(row)
    _trace(row.id, HANDLE_ACTIONS[action], remark)
    if action in {"HANDLED", "FALSE_ALARM"}:
        from app.domains.live.common import close_todos

        close_todos("LIVE_ALARM", row.id)
    data = _record_view(row)
    data["history"] = _history(row.id)
    return data


def stats() -> dict:
    rows = _records({})
    by_level = []
    for level in ("1", "2", "3"):
        by_level.append({"name": LEVEL_LABEL[level], "value": sum(1 for row in rows if row.alarm_level == level)})
    by_status = []
    for status, label in STATUS_LABEL.items():
        by_status.append({"name": label, "value": sum(1 for row in rows if row.handle_status == status)})
    hits: dict[int, int] = {}
    for row in rows:
        if row.rule_id:
            hits[int(row.rule_id)] = hits.get(int(row.rule_id), 0) + int(row.merge_count or 1)
    ranked = sorted(hits.items(), key=lambda item: item[1], reverse=True)[:10]
    top = []
    for rule_id, count in ranked:
        rule = get_session().get(LiveAlarmRule, rule_id)
        top.append({"name": rule.rule_name if rule and not rule.deleted else "规则已删除", "value": count})
    days = []
    for offset in range(6, -1, -1):
        day = today() - timedelta(days=offset)
        key = day.isoformat()
        matched = [row for row in rows if row.occur_at and row.occur_at.date() == day]
        days.append({"name": key, "value": len(matched), "l3": sum(1 for row in matched if row.alarm_level == "3")})
    banner = any(row.alarm_level == "3" and row.handle_status == "UNHANDLED" and _owns_session(row.session_id) for row in rows)
    return {"byLevel": by_level, "byStatus": by_status, "topRules": top, "daily": days, "l3Banner": banner, "unhandled": sum(1 for row in rows if row.handle_status == "UNHANDLED")}


def accept(session_id: int, metric: str, value=None, text: str = "") -> dict | None:
    row = get_session().get(LiveSession, int(session_id))
    if row is None or row.session_status != "LIVE":
        return None
    if metric not in THRESHOLD_METRICS | EVENT_METRICS:
        return None
    rules = list(
        get_session().scalars(select(LiveAlarmRule).where(LiveAlarmRule.metric == metric, LiveAlarmRule.status == "ENABLED"))
    )
    last = None
    for rule in rules:
        if not _hit(rule, value, text):
            continue
        last = _merge(rule, row, text or _content(rule, value))
    return last


def on_account(account_id: int, status: str) -> int:
    if status not in {"FROZEN", "CANCELLED"}:
        return 0
    rows = list(
        get_session().scalars(select(LiveSession).where(LiveSession.account_id == int(account_id), LiveSession.session_status == "LIVE"))
    )
    done = 0
    for row in rows:
        if accept(row.id, "ACCOUNT_ABNORMAL", text=f"账号变为{status}"):
            done += 1
    return done


def escalate_due() -> int:
    now = now_naive()
    rows = list(
        get_session().scalars(
            select(LiveAlarmRecord).where(LiveAlarmRecord.handle_status == "UNHANDLED", LiveAlarmRecord.escalated == 0)
        )
    )
    done = 0
    directors = user_ids_with_perm("ims:live:session:approve")
    for row in rows:
        if row.occur_at is None or now < row.occur_at + timedelta(minutes=30):
            continue
        row.escalated = 1
        row.escalated_at = now
        save(row)
        session = get_session().get(LiveSession, row.session_id)
        title = f"直播告警已升级 {session.session_code if session else ''}"
        for user_id in directors:
            send(user_id, title, row.alarm_content or title, "LIVE_ALARM_UP", f"live-alarm-up:{row.id}:{user_id}", route=f"/ims/live/alarm?id={row.id}", source_module="live")
            _ding(user_id, title, row.alarm_content or title)
        done += 1
    return done


def _fill_rule(row: LiveAlarmRule, body: dict, creating: bool) -> None:
    name = limit_text(body.get("ruleName") or body.get("name") or row.rule_name, "ruleName", "规则名", 64, required=True)
    kind = text_of(body, "ruleType") or row.rule_type or ""
    metric = text_of(body, "metric") or row.metric or ""
    operator = text_of(body, "operator") or row.operator or ""
    if kind not in {"THRESHOLD", "EVENT"}:
        raise BizError(1050, "告警规则表达式不合法：类型须为阈值或事件")
    if kind == "THRESHOLD" and metric not in THRESHOLD_METRICS:
        raise BizError(1050, "告警规则表达式不合法：阈值型指标不正确")
    if kind == "EVENT" and metric not in EVENT_METRICS:
        raise BizError(1050, "告警规则表达式不合法：事件型指标不正确")
    if kind == "THRESHOLD" and operator not in THRESHOLD_OPS:
        raise BizError(1050, "告警规则表达式不合法：操作符不正确")
    if kind == "EVENT" and operator != "HIT":
        raise BizError(1050, "告警规则表达式不合法：事件型操作符须为命中")
    raw_threshold = body.get("threshold") if "threshold" in body else row.threshold
    try:
        threshold = Decimal(str(raw_threshold if raw_threshold not in (None, "") else "0"))
    except Exception:
        raise BizError(1050, "告警规则表达式不合法：阈值不是数字")
    if threshold < 0:
        raise BizError(1050, "告警规则表达式不合法：阈值不能为负")
    window = body.get("windowMinutes") if "windowMinutes" in body else row.window_minutes
    if kind == "THRESHOLD":
        if window in (None, ""):
            raise BizError(1050, "告警规则表达式不合法：窗口须为 1～60 分钟")
        window = int(window)
        if window < 1 or window > 60:
            raise BizError(1050, "告警规则表达式不合法：窗口须为 1～60 分钟")
    else:
        window = None
    if operator == "PCT_DROP" and (threshold < 1 or threshold > 100):
        raise BizError(1050, "告警规则表达式不合法：降幅须为 1～100")
    level = str(body.get("level") or row.level or "")
    if level not in LEVELS:
        raise BizError(1503, data={"fieldErrors": [{"field": "level", "message": "告警级别不合法"}]})
    roles = body.get("notifyRoleIds") if "notifyRoleIds" in body else (row.notify_role_ids or [])
    users = body.get("notifyUserIds") if "notifyUserIds" in body else (row.notify_user_ids or [])
    roles = [int(item) for item in (roles or []) if str(item).strip()]
    users = [int(item) for item in (users or []) if str(item).strip()]
    if not roles and not users:
        raise BizError(1050, "告警规则表达式不合法：请指定通知人")
    taken = get_session().scalar(select(LiveAlarmRule).where(LiveAlarmRule.rule_name == name, LiveAlarmRule.id != (row.id or 0)))
    if taken is not None:
        one("ruleName", "规则名称已存在")
    row.rule_name = name
    row.rule_type = kind
    row.metric = metric
    row.operator = operator
    row.threshold = threshold
    row.window_minutes = window
    row.level = level
    row.notify_role_ids = roles
    row.notify_user_ids = users
    if creating and text_of(body, "status") in {"ENABLED", "DISABLED"}:
        row.status = text_of(body, "status")


def _hit(rule: LiveAlarmRule, value, text: str) -> bool:
    if rule.operator == "HIT":
        return True
    if value in (None, ""):
        return False
    number = Decimal(str(value))
    threshold = Decimal(rule.threshold or 0)
    if rule.operator == "LT":
        return number < threshold
    if rule.operator == "GT":
        return number > threshold
    if rule.operator == "PCT_DROP":
        return number >= threshold
    return False


def _merge(rule: LiveAlarmRule, session_row: LiveSession, content: str) -> dict:
    now = now_naive()
    recent = get_session().scalar(
        select(LiveAlarmRecord)
        .where(LiveAlarmRecord.rule_id == rule.id, LiveAlarmRecord.session_id == session_row.id)
        .order_by(LiveAlarmRecord.id.desc())
    )
    if recent is not None and recent.last_occur_at and now - recent.last_occur_at < timedelta(minutes=10):
        recent.merge_count = int(recent.merge_count or 1) + 1
        recent.last_occur_at = now
        save(recent)
        return _record_view(recent)
    record = LiveAlarmRecord(
        rule_id=rule.id,
        session_id=session_row.id,
        alarm_level=rule.level,
        alarm_content=content[:512],
        occur_at=now,
        last_occur_at=now,
        merge_count=1,
        handle_status="UNHANDLED",
    )
    save(record)
    users = list(rule.notify_user_ids or [])
    if session_row.responsible_user_id:
        users.append(int(session_row.responsible_user_id))
    users = sorted(set(users))
    if users:
        todo_create("LIVE_ALARM", int(record.id), "ALERT", f"直播告警 {session_row.session_code}", user_ids=users, route=f"/ims/live/alarm?id={record.id}", source_module="live")
    if rule.level == "3":
        for user_id in users:
            _ding(user_id, "直播严重告警", content)
            log.info("模拟短信 user=%s content=%s", user_id, content)
    return _record_view(record)


def _content(rule: LiveAlarmRule, value) -> str:
    return f"{rule.rule_name} 命中 {value if value is not None else ''}".strip()


def _ding(user_id: int, title: str, content: str) -> None:
    try:
        send_work_notice(str(user_id), title, content or title)
    except Exception:
        log.info("钉钉通知未发出 user=%s", user_id)


def _records(params: dict) -> list[LiveAlarmRecord]:
    stmt = select(LiveAlarmRecord)
    code = text_of(params, "sessionCode")
    if code:
        session_row = get_session().scalar(select(LiveSession).where(LiveSession.session_code == code))
        if session_row is None or not in_scope(session_row):
            return []
        stmt = stmt.where(LiveAlarmRecord.session_id == session_row.id)
    level = text_of(params, "level") or text_of(params, "alarmLevel")
    if level:
        stmt = stmt.where(LiveAlarmRecord.alarm_level == level)
    status = text_of(params, "handleStatus")
    if status:
        stmt = stmt.where(LiveAlarmRecord.handle_status == status)
    rows = list(get_session().scalars(stmt.order_by(LiveAlarmRecord.occur_at.desc(), LiveAlarmRecord.id.desc())))
    kept = []
    for row in rows:
        session_row = get_session().get(LiveSession, row.session_id)
        if session_row is None or not in_scope(session_row):
            continue
        if _narrow() and not has_perm("ims:live:alarm:rule") and not _owns_session(row.session_id):
            continue
        kept.append(row)
    start = text_of(params, "occurFrom")
    end = text_of(params, "occurTo")
    if start:
        kept = [row for row in kept if row.occur_at and str(row.occur_at)[:10] >= start[:10]]
    if end:
        kept = [row for row in kept if row.occur_at and str(row.occur_at)[:10] <= end[:10]]
    return kept


def _narrow() -> bool:
    from app.domains.live.common import scope_mode

    kind, _, _ = scope_mode()
    return kind != "all"


def _owns_session(session_id: int) -> bool:
    from app.domains.live.common import owns

    row = get_session().get(LiveSession, int(session_id))
    return bool(row and owns(row))


def _record(ident: int) -> LiveAlarmRecord:
    row = get_session().get(LiveAlarmRecord, int(ident))
    if row is None or row.deleted:
        raise BizError(1008, "您无权查看该场次")
    session_row = get_session().get(LiveSession, row.session_id)
    if session_row is None:
        raise BizError(1008, "您无权查看该场次")
    require_scope(session_row)
    return row


def _rule(ident: int) -> LiveAlarmRule:
    row = get_session().get(LiveAlarmRule, int(ident))
    if row is None or row.deleted:
        raise BizError(1500, "关联的规则不存在")
    return row


def _rule_view(row: LiveAlarmRule) -> dict:
    return {
        "id": row.id,
        "ruleName": row.rule_name,
        "ruleType": row.rule_type,
        "metric": row.metric,
        "operator": row.operator,
        "threshold": f"{Decimal(row.threshold or 0):.2f}",
        "windowMinutes": row.window_minutes,
        "level": row.level,
        "levelLabel": LEVEL_LABEL.get(row.level, row.level),
        "notifyRoleIds": row.notify_role_ids or [],
        "notifyUserIds": row.notify_user_ids or [],
        "status": row.status,
        "version": row.version,
    }


def _record_view(row: LiveAlarmRecord) -> dict:
    rule = get_session().get(LiveAlarmRule, row.rule_id) if row.rule_id else None
    session_row = get_session().get(LiveSession, row.session_id)
    name = "规则已删除"
    if rule is not None and not rule.deleted:
        name = rule.rule_name
    count = int(row.merge_count or 1)
    content = row.alarm_content or ""
    if count > 1:
        content = f"{content} ×{count}"
    return {
        "id": row.id,
        "sessionId": row.session_id,
        "sessionCode": session_row.session_code if session_row else "",
        "ruleName": name,
        "level": row.alarm_level,
        "levelLabel": LEVEL_LABEL.get(row.alarm_level, row.alarm_level),
        "content": content,
        "occurAt": when_text(row.occur_at),
        "mergeCount": count,
        "handleStatus": row.handle_status,
        "handleStatusLabel": STATUS_LABEL.get(row.handle_status, row.handle_status),
        "handlerName": user_name(row.handler_user_id),
        "handleRemark": row.handle_remark or "",
        "escalated": int(row.escalated or 0) == 1,
        "escalatedLabel": "已升级" if int(row.escalated or 0) == 1 else "",
    }


def _history(record_id: int) -> list[dict]:
    rows = list(
        get_session().scalars(
            select(Timeline).where(Timeline.biz_type == "LIVE_ALARM", Timeline.biz_id == int(record_id)).order_by(Timeline.id.asc())
        )
    )
    return [
        {
            "title": item.title,
            "detail": (item.detail or {}).get("text") if isinstance(item.detail, dict) else "",
            "time": when_text(item.event_time),
        }
        for item in rows
    ]


def _trace(record_id: int, title: str, detail: str) -> None:
    get_session().add(
        Timeline(
            biz_type="LIVE_ALARM",
            biz_id=int(record_id),
            event_type="HANDLE",
            title=title[:100],
            detail={"text": detail} if detail else {},
            operator_id=viewer_id() or None,
            event_time=now_naive(),
        )
    )
    get_session().flush()


def open_count() -> int:
    return int(get_session().scalar(select(func.count()).select_from(LiveAlarmRecord).where(LiveAlarmRecord.handle_status == "UNHANDLED")) or 0)
