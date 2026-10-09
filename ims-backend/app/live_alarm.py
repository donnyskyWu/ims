"""LIVE-003 事中告警：规则热更新、站内命中、10 分钟去重、处置与只读统计。

ALM-R1：L3 记钉钉/短信桩，不外呼。
ALM-R3：未处理满 30 分钟升级运营总监，站内信桩。
ALM-R4：规则保存后下一次读取即新表达式。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, tenant_of, user_names
from app.models import (
    LiveAlarmRecord,
    LiveAlarmRule,
    LiveDataSnapshot,
    LiveReport,
    LiveSession,
    Role,
    User,
    UserRole,
    WorkMessage,
)

router = APIRouter(prefix="/alarm", tags=["live-alarm"])

BJ = timezone(timedelta(hours=8))
DEDUP_MINUTES = 10
ESCALATE_MINUTES = 30
DIRECTOR_USERNAME = "live_director"
AGED_SESSION = "IMS20261009ALM0030"
FRESH_L3_SESSION = "IMS20261009ALM0003"
FRESH_L2_SESSION = "IMS20261009ALM0005"
STUB_NOTE = "站内桩，未调用钉钉，未调用短信"
METRIC_LABELS = {
    "viewer_count": "场观",
    "viewer_drop": "场观",
    "gmv": "GMV",
    "peak_online": "峰值在线",
    "blacklist": "违禁词",
}
THRESHOLD_METRICS = {"viewer_count", "viewer_drop", "gmv", "peak_online"}
THRESHOLD_OPS = {"GT", "LT", "PCT_DROP"}
EVENT_METRICS = {"blacklist"}
HANDLE_NEXT = {
    "UNHANDLED": {"CONFIRMED", "HANDLED", "FALSE_ALARM"},
    "CONFIRMED": {"HANDLED", "FALSE_ALARM"},
}
TERMINAL_HANDLE = {"HANDLED", "FALSE_ALARM"}


class RuleExprBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    metric: str = ""
    operator: str = ""
    threshold: float | None = None
    window: int | None = None


class RuleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    ruleName: str = ""
    ruleType: str = "THRESHOLD"
    ruleExpr: RuleExprBody = Field(default_factory=RuleExprBody)
    level: int = 2
    notifyUsers: list[int] = Field(default_factory=list)
    status: str = "ENABLED"


class HandleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    handleStatus: str = ""
    handleRemark: str = ""


def iso_now() -> str:
    return datetime.now(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_occur(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BJ)
    return parsed.astimezone(BJ)


def within_dedup(occur_at: str, now: datetime) -> bool:
    parsed = parse_occur(occur_at)
    if parsed is None:
        return False
    return abs((now - parsed).total_seconds()) <= DEDUP_MINUTES * 60


def expr_error(rule_type: str, expr: RuleExprBody) -> str | None:
    metric = (expr.metric or "").strip()
    operator = (expr.operator or "").strip().upper()
    if rule_type == "EVENT":
        if metric not in EVENT_METRICS:
            return "事件规则指标仅支持 blacklist"
        if operator != "HIT":
            return "事件规则操作符须为 HIT"
    elif rule_type == "THRESHOLD":
        if metric not in THRESHOLD_METRICS:
            return "阈值规则指标仅支持 viewer_count / gmv / peak_online"
        if operator not in THRESHOLD_OPS:
            return "阈值规则操作符须为 GT / LT / PCT_DROP"
    else:
        return "ruleType 须为 THRESHOLD 或 EVENT"
    if expr.threshold is None or isinstance(expr.threshold, bool) or expr.threshold < 0:
        return "threshold 须为不小于 0 的数字"
    if expr.window is not None and (isinstance(expr.window, bool) or not isinstance(expr.window, int) or expr.window < 1 or expr.window > 60):
        return "window 须为 1~60 的整数"
    return None


def fail_expr(reason: str):
    return fail(1009, f"告警规则表达式非法（1009）：{reason}")


def expr_dict(expr: RuleExprBody) -> dict:
    data = {
        "metric": expr.metric.strip(),
        "operator": expr.operator.strip().upper(),
        "threshold": expr.threshold,
    }
    if expr.window is not None:
        data["window"] = expr.window
    return data


def expr_summary(rule_type: str, expr: dict) -> str:
    metric = METRIC_LABELS.get(str(expr.get("metric")), str(expr.get("metric") or ""))
    operator = str(expr.get("operator") or "")
    threshold = expr.get("threshold")
    window = expr.get("window")
    if operator == "HIT":
        text = f"{metric}命中"
    elif operator == "PCT_DROP":
        pct = round(float(threshold or 0) * 100, 2)
        text = f"{metric}降幅 ≥ {pct}%"
    elif operator == "LT":
        text = f"{metric}低于 {threshold}"
    else:
        text = f"{metric}高于 {threshold}"
    if window:
        text = f"{text}（窗口 {window} 分钟）"
    if rule_type == "EVENT":
        return f"事件 · {text}"
    return text


def validate_rule(body: RuleBody):
    name = body.ruleName.strip()
    if not name:
        return None, fail(1001, "ruleName 必填")
    if len(name) > 64:
        return None, fail(1001, "ruleName 过长")
    rule_type = body.ruleType.strip().upper()
    if rule_type not in {"THRESHOLD", "EVENT"}:
        return None, fail_expr("ruleType 须为 THRESHOLD 或 EVENT")
    if body.level not in (1, 2, 3):
        return None, fail(1001, "level 须为 1/2/3")
    status = body.status.strip().upper() or "ENABLED"
    if status not in {"ENABLED", "DISABLED"}:
        return None, fail(1001, "status 无效")
    if not body.notifyUsers:
        return None, fail(1001, "notifyUsers 至少一人")
    reason = expr_error(rule_type, body.ruleExpr)
    if reason:
        return None, fail_expr(reason)
    return {
        "rule_name": name,
        "rule_type": rule_type,
        "rule_expr": expr_dict(body.ruleExpr),
        "level": body.level,
        "notify_users": [int(item) for item in body.notifyUsers],
        "status": status,
    }, None


def rule_vo(row: LiveAlarmRule, names: dict[int, str]) -> dict:
    expr = row.rule_expr if isinstance(row.rule_expr, dict) else {}
    users = [int(item) for item in (row.notify_users or [])]
    summary = "、".join(names.get(item) or str(item) for item in users) or "—"
    return {
        "id": row.id,
        "ruleName": row.rule_name,
        "ruleType": row.rule_type,
        "ruleExpr": expr,
        "ruleExprSummary": expr_summary(row.rule_type, expr),
        "level": row.level,
        "notifyUsers": users,
        "notifySummary": summary,
        "status": row.status,
    }


def clock(moment: datetime | None = None) -> datetime:
    now = moment or datetime.now(BJ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=BJ)
    return now.astimezone(BJ).replace(microsecond=0)


def stamp(moment: datetime | None = None) -> str:
    return clock(moment).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def channel_set(raw: str | None) -> set[str]:
    return {part for part in (raw or "").split(",") if part}


def join_channels(parts: set[str]) -> str:
    order = ["IN_APP", "DINGTALK_STUB", "SMS_STUB", "ESCALATE_STUB"]
    ranked = [name for name in order if name in parts]
    extra = sorted(parts - set(order))
    return ",".join(ranked + extra)


def director_ids(db: Session, tenant_id: int) -> list[int]:
    roles = db.scalars(select(Role).where(Role.deleted == 0, Role.tenant_id == tenant_id)).all()
    role_ids = []
    for role in roles:
        key = (role.role_key or "").strip().lower()
        name = role.role_name or ""
        if key == "r4" or key.endswith(":r4") or "运营总监" in name:
            role_ids.append(role.id)
    if not role_ids:
        return []
    found: list[int] = []
    rows = db.scalars(
        select(UserRole.user_id).where(UserRole.role_id.in_(role_ids), UserRole.tenant_id == tenant_id)
    ).all()
    for user_id in rows:
        if user_id not in found:
            found.append(int(user_id))
    return found


def ensure_message(
    db: Session,
    *,
    user_id: int,
    title: str,
    content: str,
    ref_type: str,
    ref_id: int,
    tenant_id: int,
) -> None:
    existing = db.scalar(
        select(WorkMessage).where(
            WorkMessage.user_id == user_id,
            WorkMessage.source_module == "LIVE",
            WorkMessage.ref_type == ref_type,
            WorkMessage.ref_id == ref_id,
        )
    )
    if existing is not None:
        return
    db.add(
        WorkMessage(
            user_id=user_id,
            title=title[:128],
            content=content[:512],
            channel="IN_APP",
            read_flag=0,
            source_module="LIVE",
            ref_type=ref_type,
            ref_id=ref_id,
            tenant_id=tenant_id,
        )
    )


def apply_l3_stub(row: LiveAlarmRecord) -> None:
    """L3 只写渠道名，不请求钉钉或短信。"""
    channels = channel_set(row.notify_channels)
    channels.add("IN_APP")
    if row.alarm_level == 3:
        channels.update({"DINGTALK_STUB", "SMS_STUB"})
    row.notify_channels = join_channels(channels)


def ingest_alarm(
    db: Session,
    *,
    tenant_id: int,
    rule_id: int,
    rule_name: str,
    session_code: str,
    alarm_level: int,
    alarm_content: str,
    occur_at: str,
) -> LiveAlarmRecord:
    moment = parse_occur(occur_at) or clock()
    cutoff = stamp(moment - timedelta(minutes=DEDUP_MINUTES))
    existing = db.scalar(
        select(LiveAlarmRecord).where(
            LiveAlarmRecord.deleted == 0,
            LiveAlarmRecord.tenant_id == tenant_id,
            LiveAlarmRecord.session_code == session_code,
            LiveAlarmRecord.rule_name == rule_name,
            LiveAlarmRecord.handle_status == "UNHANDLED",
            LiveAlarmRecord.occur_at >= cutoff,
        )
    )
    if existing is not None:
        existing.merge_count = (existing.merge_count or 1) + 1
        apply_l3_stub(existing)
        return existing
    row = LiveAlarmRecord(
        rule_id=rule_id,
        rule_name=rule_name[:64],
        session_code=session_code,
        alarm_level=alarm_level,
        alarm_content=alarm_content[:512],
        occur_at=stamp(moment),
        handle_status="UNHANDLED",
        escalated=0,
        escalated_at="",
        merge_count=1,
        notify_channels="",
        tenant_id=tenant_id,
    )
    apply_l3_stub(row)
    db.add(row)
    db.flush()
    return row


def sweep_alarms(db: Session, tenant_id: int, now: datetime | None = None) -> int:
    """补 L3 触达桩，并把未处理满 30 分钟的告警升级给运营总监。"""
    moment = clock(now)
    rows = db.scalars(
        select(LiveAlarmRecord).where(
            LiveAlarmRecord.deleted == 0,
            LiveAlarmRecord.tenant_id == tenant_id,
            LiveAlarmRecord.handle_status == "UNHANDLED",
        )
    ).all()
    escalated = 0
    directors = director_ids(db, tenant_id)
    for row in rows:
        apply_l3_stub(row)
        if row.escalated:
            continue
        occurred = parse_occur(row.occur_at)
        if occurred is None:
            continue
        if moment - occurred < timedelta(minutes=ESCALATE_MINUTES):
            continue
        row.escalated = 1
        row.escalated_at = stamp(moment)
        channels = channel_set(row.notify_channels)
        channels.add("ESCALATE_STUB")
        row.notify_channels = join_channels(channels)
        title = f"直播告警已升级：{row.session_code}"
        content = f"ALM-R3 未处理满 30 分钟，已升级运营总监。{STUB_NOTE}。{row.alarm_content}"
        for user_id in directors:
            ensure_message(
                db,
                user_id=user_id,
                title=title,
                content=content,
                ref_type="live_alarm_escalate",
                ref_id=row.id,
                tenant_id=tenant_id,
            )
        escalated += 1
    return escalated


def record_vo(row: LiveAlarmRecord, names: dict[int, str]) -> dict:
    handler = row.handler_user_id
    count = row.merge_count or 1
    content = row.alarm_content or ""
    if count > 1 and "×" not in content:
        content = f"{content} ×{count}"
    channels = [part for part in (row.notify_channels or "").split(",") if part]
    return {
        "id": row.id,
        "ruleId": row.rule_id,
        "ruleName": row.rule_name,
        "sessionCode": row.session_code,
        "alarmLevel": row.alarm_level,
        "alarmContent": content,
        "occurAt": row.occur_at,
        "handleStatus": row.handle_status,
        "handlerUserId": handler,
        "handlerName": names.get(handler) if handler else None,
        "handleRemark": row.handle_remark or "",
        "mergeCount": count,
        "notifyChannel": "IN_APP",
        "escalated": bool(row.escalated),
        "escalatedAt": row.escalated_at or None,
        "notifyChannels": channels or ["IN_APP"],
    }


def latest_snapshot(db: Session, session_code: str) -> LiveDataSnapshot | None:
    return db.scalar(
        select(LiveDataSnapshot)
        .where(LiveDataSnapshot.deleted == 0, LiveDataSnapshot.session_code == session_code)
        .order_by(LiveDataSnapshot.id.desc())
        .limit(1)
    )


def metric_number(metric: str, report: LiveReport | None, snap: LiveDataSnapshot | None) -> float | None:
    if metric in {"viewer_count", "viewer_drop"}:
        if report is not None:
            return float(report.viewer_count or 0)
        if snap is not None and snap.viewer_count is not None:
            return float(snap.viewer_count)
        return None
    if metric == "gmv":
        if report is not None:
            return float(report.gmv or 0)
        if snap is not None and snap.gmv_from_platform is not None:
            return float(snap.gmv_from_platform)
        return None
    if metric == "peak_online":
        if report is not None:
            return float(report.peak_online or 0)
        if snap is not None and snap.peak_online is not None:
            return float(snap.peak_online)
        return None
    return None


def drop_ratio(metric: str, report: LiveReport | None, snap: LiveDataSnapshot | None) -> float | None:
    if report is None or snap is None:
        return None
    if metric in {"viewer_count", "viewer_drop"}:
        base = snap.viewer_count
        current = report.viewer_count
    elif metric == "gmv":
        base = snap.gmv_from_platform
        current = report.gmv
    elif metric == "peak_online":
        base = snap.peak_online
        current = report.peak_online
    else:
        return None
    if base is None or current is None or float(base) <= 0:
        return None
    return (float(base) - float(current)) / float(base)


def hit_text(rule: LiveAlarmRule, session: LiveSession, report: LiveReport | None, snap: LiveDataSnapshot | None) -> str | None:
    expr = rule.rule_expr if isinstance(rule.rule_expr, dict) else {}
    metric = str(expr.get("metric") or "")
    operator = str(expr.get("operator") or "")
    try:
        threshold = float(expr.get("threshold"))
    except (TypeError, ValueError):
        return None
    label = METRIC_LABELS.get(metric, metric)
    if operator == "HIT" and metric == "blacklist":
        from app.live import topic_hits_blacklist

        if topic_hits_blacklist(session.topic or ""):
            return f"{label}命中：{session.topic}"[:512]
        return None
    if operator == "PCT_DROP":
        ratio = drop_ratio(metric, report, snap)
        if ratio is None or ratio < threshold:
            return None
        return f"{label}降幅 {round(ratio * 100, 1)}% ≥ {round(threshold * 100, 1)}%"[:512]
    value = metric_number(metric, report, snap)
    if value is None:
        return None
    if operator == "LT" and value < threshold:
        return f"{label} {value:g} 低于阈值 {threshold:g}"[:512]
    if operator == "GT" and value > threshold:
        return f"{label} {value:g} 高于阈值 {threshold:g}"[:512]
    return None


def upsert_hit(db: Session, tenant_id: int, rule: LiveAlarmRule, session: LiveSession, content: str, now: datetime) -> None:
    latest = db.scalar(
        select(LiveAlarmRecord)
        .where(
            LiveAlarmRecord.deleted == 0,
            LiveAlarmRecord.tenant_id == tenant_id,
            LiveAlarmRecord.rule_id == rule.id,
            LiveAlarmRecord.session_code == session.session_code,
        )
        .order_by(LiveAlarmRecord.id.desc())
        .limit(1)
    )
    stamped = iso_now()
    if latest is not None and within_dedup(latest.occur_at, now):
        latest.merge_count = (latest.merge_count or 1) + 1
        latest.alarm_content = content
        latest.alarm_level = rule.level
        latest.occur_at = stamped
        latest.rule_name = rule.rule_name
        apply_l3_stub(latest)
        return
    created = LiveAlarmRecord(
        rule_id=rule.id,
        rule_name=rule.rule_name,
        session_code=session.session_code,
        alarm_level=rule.level,
        alarm_content=content,
        occur_at=stamped,
        handle_status="UNHANDLED",
        merge_count=1,
        escalated=0,
        escalated_at="",
        notify_channels="",
        tenant_id=tenant_id,
    )
    apply_l3_stub(created)
    db.add(created)


def scan_rules(db: Session, actor: User, session_code: str = "") -> None:
    """对已有下播数据或直播中的场次套用已启用规则。同一请求内按当前规则热更新结果计算。"""
    tenant_id = tenant_of(actor)
    rules = list(
        db.scalars(
            select(LiveAlarmRule).where(
                LiveAlarmRule.deleted == 0,
                LiveAlarmRule.tenant_id == tenant_id,
                LiveAlarmRule.status == "ENABLED",
            )
        ).all()
    )
    if not rules:
        return
    stmt = select(LiveSession).where(LiveSession.deleted == 0, LiveSession.tenant_id == tenant_id)
    if session_code:
        stmt = stmt.where(LiveSession.session_code == session_code)
    else:
        stmt = stmt.where(LiveSession.session_status.in_(("LIVE", "ENDED", "APPROVED")))
    sessions = list(db.scalars(stmt.order_by(LiveSession.id.desc()).limit(200)).all())
    if not sessions:
        return
    codes = [row.session_code for row in sessions]
    reports = {
        row.session_code: row
        for row in db.scalars(select(LiveReport).where(LiveReport.deleted == 0, LiveReport.session_code.in_(codes))).all()
    }
    now = datetime.now(BJ)
    for session in sessions:
        report = reports.get(session.session_code)
        if report is None and session.session_status != "LIVE":
            continue
        snap = latest_snapshot(db, session.session_code)
        for rule in rules:
            content = hit_text(rule, session, report, snap)
            if content:
                upsert_hit(db, tenant_id, rule, session, content, now)
    db.flush()


def load_rule(db: Session, actor: User, rule_id: int) -> LiveAlarmRule | None:
    row = db.get(LiveAlarmRule, rule_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return None
    return row


@router.get("/rules")
def alarm_rules(
    pageNo: int = 1,
    pageSize: int = 20,
    ruleType: str = "",
    status: str = "",
    keyword: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(LiveAlarmRule).where(LiveAlarmRule.deleted == 0, LiveAlarmRule.tenant_id == tenant_of(actor))
    if ruleType:
        stmt = stmt.where(LiveAlarmRule.rule_type == ruleType.strip().upper())
    if status:
        stmt = stmt.where(LiveAlarmRule.status == status.strip().upper())
    if keyword.strip():
        stmt = stmt.where(LiveAlarmRule.rule_name.contains(keyword.strip()))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.order_by(LiveAlarmRule.id.desc()).offset((page_no - 1) * size).limit(size)).all())
    ids: set[int] = set()
    for row in rows:
        ids.update(int(item) for item in (row.notify_users or []))
    names = user_names(db, ids)
    return ok({"list": [rule_vo(row, names) for row in rows], "total": total, "pageNo": page_no, "pageSize": size})


@router.post("/rule")
def create_rule(body: RuleBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    parsed, error = validate_rule(body)
    if error is not None:
        return error
    row = LiveAlarmRule(tenant_id=tenant_of(actor), **parsed)
    db.add(row)
    db.flush()
    names = user_names(db, set(parsed["notify_users"]))
    return ok(rule_vo(row, names))


@router.put("/rule/{rule_id}")
def update_rule(rule_id: int, body: RuleBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = load_rule(db, actor, rule_id)
    if row is None:
        return fail(1500, "规则不存在")
    parsed, error = validate_rule(body)
    if error is not None:
        return error
    for key, value in parsed.items():
        setattr(row, key, value)
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.delete("/rule/{rule_id}")
def delete_rule(
    rule_id: int,
    confirmText: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if confirmText != "DELETE":
        return fail(1001, "confirmText 须为 DELETE")
    row = load_rule(db, actor, rule_id)
    if row is None:
        return fail(1500, "规则不存在")
    row.deleted = 1
    row.status = "DISABLED"
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.get("/records")
def alarm_records(
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    alarmLevel: int | None = None,
    handleStatus: str = "",
    timeRange: list[str] = Query(default=[]),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    scan_rules(db, actor, sessionCode.strip())
    sweep_alarms(db, tenant_of(actor))
    db.flush()
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(LiveAlarmRecord).where(LiveAlarmRecord.deleted == 0, LiveAlarmRecord.tenant_id == tenant_of(actor))
    if sessionCode.strip():
        stmt = stmt.where(LiveAlarmRecord.session_code == sessionCode.strip())
    if alarmLevel in (1, 2, 3):
        stmt = stmt.where(LiveAlarmRecord.alarm_level == alarmLevel)
    if handleStatus.strip():
        stmt = stmt.where(LiveAlarmRecord.handle_status == handleStatus.strip().upper())
    if len(timeRange) >= 2 and timeRange[0] and timeRange[1]:
        stmt = stmt.where(LiveAlarmRecord.occur_at >= timeRange[0], LiveAlarmRecord.occur_at <= timeRange[1] + "T23:59:59")
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.order_by(LiveAlarmRecord.id.desc()).offset((page_no - 1) * size).limit(size)).all())
    ids = {row.handler_user_id for row in rows if row.handler_user_id}
    names = user_names(db, ids)
    severe_stmt = select(LiveAlarmRecord).where(
        LiveAlarmRecord.deleted == 0,
        LiveAlarmRecord.tenant_id == tenant_of(actor),
        LiveAlarmRecord.alarm_level == 3,
        LiveAlarmRecord.handle_status == "UNHANDLED",
    )
    severe_unhandled = int(db.scalar(select(func.count()).select_from(severe_stmt.subquery())) or 0)
    return ok(
        {
            "list": [record_vo(row, names) for row in rows],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
            "severeUnhandled": severe_unhandled,
        }
    )


@router.put("/record/{record_id}/handle")
def handle_record(
    record_id: int,
    body: HandleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    status = body.handleStatus.strip().upper()
    if status not in {"CONFIRMED", "HANDLED", "FALSE_ALARM"}:
        return fail(1001, "handleStatus 无效")
    remark = (body.handleRemark or "").strip()
    if len(remark) > 512:
        return fail(1001, "handleRemark 过长")
    row = db.get(LiveAlarmRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1500, "告警不存在")
    if row.handle_status in TERMINAL_HANDLE:
        return fail(1001, "告警已处置，请刷新")
    allowed = HANDLE_NEXT.get(row.handle_status, set())
    if status not in allowed:
        return fail(1001, "当前状态不可执行该处置")
    row.handle_status = status
    row.handler_user_id = actor.id
    row.handle_remark = remark
    db.flush()
    return ok(None)


@router.get("/stats")
def alarm_stats(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    rows = list(
        db.scalars(
            select(LiveAlarmRecord).where(LiveAlarmRecord.deleted == 0, LiveAlarmRecord.tenant_id == tenant_id)
        ).all()
    )
    by_level = {"1": 0, "2": 0, "3": 0}
    by_status = {"UNHANDLED": 0, "CONFIRMED": 0, "HANDLED": 0, "FALSE_ALARM": 0}
    by_rule: dict[str, int] = {}
    day_total: dict[str, int] = {}
    day_severe: dict[str, int] = {}
    for row in rows:
        key = str(row.alarm_level)
        if key in by_level:
            by_level[key] += 1
        if row.handle_status in by_status:
            by_status[row.handle_status] += 1
        name = row.rule_name or "未命名"
        by_rule[name] = by_rule.get(name, 0) + (row.merge_count or 1)
        day = (row.occur_at or "")[:10]
        if len(day) == 10:
            day_total[day] = day_total.get(day, 0) + 1
            if row.alarm_level == 3:
                day_severe[day] = day_severe.get(day, 0) + 1
    today = datetime.now(BJ).date()
    trend = []
    for offset in range(6, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        trend.append({"date": day, "total": day_total.get(day, 0), "severe": day_severe.get(day, 0)})
    ranked = sorted(by_rule.items(), key=lambda item: item[1], reverse=True)[:10]
    return ok(
        {
            "byLevel": by_level,
            "byHandleStatus": by_status,
            "trend": trend,
            "byRule": [{"ruleName": name, "hitCount": count} for name, count in ranked],
        }
    )


def _upsert_alarm(
    db: Session,
    *,
    tenant_id: int,
    session_code: str,
    level: int,
    content: str,
    minutes_ago: int,
) -> None:
    row = db.scalar(
        select(LiveAlarmRecord).where(
            LiveAlarmRecord.deleted == 0,
            LiveAlarmRecord.tenant_id == tenant_id,
            LiveAlarmRecord.session_code == session_code,
            LiveAlarmRecord.rule_name == "场观骤降",
        )
    )
    occur = stamp(clock() - timedelta(minutes=minutes_ago))
    if row is None:
        db.add(
            LiveAlarmRecord(
                rule_id=0,
                rule_name="场观骤降",
                session_code=session_code,
                alarm_level=level,
                alarm_content=content,
                occur_at=occur,
                handle_status="UNHANDLED",
                escalated=0,
                escalated_at="",
                merge_count=1,
                notify_channels="",
                tenant_id=tenant_id,
            )
        )
        return
    row.alarm_level = level
    row.alarm_content = content
    row.occur_at = occur
    row.handle_status = "UNHANDLED"
    row.handler_user_id = None
    row.handle_remark = ""
    row.escalated = 0
    row.escalated_at = ""
    row.merge_count = 1
    row.notify_channels = ""
    db.query(WorkMessage).filter(
        WorkMessage.source_module == "LIVE",
        WorkMessage.ref_type == "live_alarm_escalate",
        WorkMessage.ref_id == row.id,
    ).delete(synchronize_session=False)


def refresh_live_alarm_e2e(db: Session) -> None:
    """本地运营总监与三场告警。打开告警列表时才升级，不外呼钉钉/短信。"""
    from app.scope import refresh_user_scope
    from app.security import hash_password

    role = db.scalar(select(Role).where(Role.role_key == "live:r4", Role.deleted == 0))
    if role is None:
        role = Role(
            role_name="运营总监",
            role_key="live:r4",
            data_scope="ALL",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
    director = db.scalar(select(User).where(User.username == DIRECTOR_USERNAME, User.deleted == 0))
    if director is None:
        director = User(
            username=DIRECTOR_USERNAME,
            nickname="运营总监",
            mobile="13900001420",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(director)
        db.flush()
    if not db.scalar(select(UserRole).where(UserRole.user_id == director.id, UserRole.role_id == role.id)):
        db.add(UserRole(user_id=director.id, role_id=role.id, tenant_id=0))
    refresh_user_scope(db, director.id)
    _upsert_alarm(db, tenant_id=0, session_code=AGED_SESSION, level=3, content="场观 5 分钟内骤降 42%", minutes_ago=31)
    _upsert_alarm(db, tenant_id=0, session_code=FRESH_L3_SESSION, level=3, content="场观 5 分钟内骤降 18%", minutes_ago=2)
    _upsert_alarm(db, tenant_id=0, session_code=FRESH_L2_SESSION, level=2, content="话费余额低于阈值", minutes_ago=5)
