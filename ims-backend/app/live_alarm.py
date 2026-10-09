"""直播风险告警（LIVE-003）。

ALM-R1：L3 记钉钉/短信桩，不外呼。
ALM-R2：同规则同场次 10 分钟内合并。
ALM-R3：未处理满 30 分钟升级运营总监，站内信桩。
ALM-R4：规则保存后下一次读取即新表达式。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.corp import page_args, tenant_of, user_names
from app.models import LiveAlarmRecord, LiveAlarmRule, Role, User, UserRole, WorkMessage

router = APIRouter()

BJ = timezone(timedelta(hours=8))
ESCALATE_MINUTES = 30
DEDUP_MINUTES = 10
DIRECTOR_USERNAME = "live_director"
AGED_SESSION = "IMS20261009ALM0030"
FRESH_L3_SESSION = "IMS20261009ALM0003"
FRESH_L2_SESSION = "IMS20261009ALM0005"
STUB_NOTE = "站内桩，未调用钉钉，未调用短信"

METRICS = {
    "gmv_drop": "GMV 异常波动",
    "viewer_drop": "场观骤降",
    "balance_low": "话费余额",
    "account_status": "账号异常状态",
    "banned_word": "违禁词命中",
}
OPERATORS = {
    "GT": ">",
    "LT": "<",
    "PCT_DROP": "降幅超过",
    "HIT": "命中",
}
HANDLE_STATUS = {"CONFIRMED", "HANDLED", "FALSE_ALARM"}


def clock(moment: datetime | None = None) -> datetime:
    now = moment or datetime.now(BJ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=BJ)
    return now.astimezone(BJ).replace(microsecond=0)


def stamp(moment: datetime | None = None) -> str:
    return clock(moment).strftime("%Y-%m-%dT%H:%M:%S+08:00")


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


def channel_set(raw: str | None) -> set[str]:
    return {part for part in (raw or "").split(",") if part}


def join_channels(parts: set[str]) -> str:
    order = ["IN_APP", "DINGTALK_STUB", "SMS_STUB", "ESCALATE_STUB"]
    ranked = [name for name in order if name in parts]
    extra = sorted(parts - set(order))
    return ",".join(ranked + extra)


def can_manage_rules(db: Session, actor: User) -> bool:
    from app.live import role_tags

    return bool(role_tags(db, actor) & {"r1", "r4", "sys:admin"})


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
    rows = db.scalars(
        select(UserRole.user_id).where(UserRole.role_id.in_(role_ids), UserRole.tenant_id == tenant_id)
    ).all()
    found = []
    for user_id in rows:
        if user_id not in found:
            found.append(user_id)
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
    """L3 在列表扫描时补上触达桩。只写渠道名，不请求钉钉或短信。"""
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


def content_of(row: LiveAlarmRecord) -> str:
    text = row.alarm_content or ""
    count = row.merge_count or 1
    if count > 1:
        return f"{text} ×{count}"
    return text


def record_vo(row: LiveAlarmRecord, names: dict[int, str]) -> dict:
    channels = [part for part in (row.notify_channels or "").split(",") if part]
    return {
        "id": row.id,
        "ruleId": row.rule_id,
        "ruleName": row.rule_name,
        "sessionCode": row.session_code,
        "alarmLevel": row.alarm_level,
        "alarmContent": content_of(row),
        "occurAt": row.occur_at,
        "handleStatus": row.handle_status,
        "handlerUserId": row.handler_user_id,
        "handlerName": names.get(row.handler_user_id or 0),
        "handleRemark": row.handle_remark,
        "escalated": bool(row.escalated),
        "escalatedAt": row.escalated_at or None,
        "mergeCount": row.merge_count or 1,
        "notifyChannels": channels,
    }


class ExprBody(BaseModel):
    metric: str = ""
    operator: str = ""
    threshold: float | None = None
    window: int | None = None


class RuleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ruleName: str = ""
    ruleType: str = ""
    ruleExpr: ExprBody = ExprBody()
    level: int = 0
    notifyUsers: list[int] = []
    status: str = "ENABLED"


class HandleBody(BaseModel):
    handleStatus: str = ""
    handleRemark: str = ""


def loads(raw: str, fallback):
    try:
        return json.loads(raw or "")
    except json.JSONDecodeError:
        return fallback


def expr_summary(expr: dict) -> str:
    metric = METRICS.get(str(expr.get("metric")), str(expr.get("metric") or ""))
    operator = OPERATORS.get(str(expr.get("operator")), str(expr.get("operator") or ""))
    text = f"{metric} {operator} {expr.get('threshold')}"
    window = expr.get("window")
    if window:
        text += f"（窗口 {window} 分钟）"
    return text.strip()


def notify_summary(db: Session, user_ids: list[int]) -> str:
    names = user_names(db, set(user_ids))
    labels = [names[item] for item in user_ids if item in names]
    if not labels:
        return "未指定"
    return "、".join(labels)


def rule_vo(db: Session, row: LiveAlarmRule) -> dict:
    expr = loads(row.rule_expr, {})
    users = loads(row.notify_users, [])
    if not isinstance(users, list):
        users = []
    return {
        "id": row.id,
        "ruleName": row.rule_name,
        "ruleType": row.rule_type,
        "ruleExpr": expr,
        "ruleExprSummary": expr_summary(expr if isinstance(expr, dict) else {}),
        "level": row.level,
        "notifyUsers": users,
        "notifySummary": notify_summary(db, [int(item) for item in users if str(item).isdigit() or isinstance(item, int)]),
        "status": row.status,
    }


def reject_rule(body: RuleBody):
    name = body.ruleName.strip()
    if not name or len(name) > 64:
        return fail(1009, "规则名必填且不超过 64 字")
    if body.ruleType not in ("THRESHOLD", "EVENT"):
        return fail(1009, "规则类型须为阈值或事件")
    expr = body.ruleExpr
    if expr.metric not in METRICS or expr.operator not in OPERATORS:
        return fail(1009, "规则表达式不合法")
    if expr.threshold is None or expr.threshold < 0:
        return fail(1009, "阈值须大于等于 0")
    if body.ruleType == "THRESHOLD" and (expr.window is None or expr.window < 1 or expr.window > 60):
        return fail(1009, "阈值窗口须在 1 到 60 分钟")
    if expr.window is not None and (expr.window < 1 or expr.window > 60):
        return fail(1009, "窗口须在 1 到 60 分钟")
    if body.level not in (1, 2, 3):
        return fail(1009, "告警级别不合法")
    if not body.notifyUsers:
        return fail(1009, "请选择通知人")
    if body.status not in ("ENABLED", "DISABLED"):
        return fail(1009, "规则状态不合法")
    return None


def dump_expr(expr: ExprBody) -> str:
    payload = {
        "metric": expr.metric,
        "operator": expr.operator,
        "threshold": expr.threshold,
    }
    if expr.window is not None:
        payload["window"] = expr.window
    return json.dumps(payload, ensure_ascii=False)


@router.get("/alarm/records")
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
    tenant_id = tenant_of(actor)
    sweep_alarms(db, tenant_id)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(LiveAlarmRecord).where(
        LiveAlarmRecord.deleted == 0,
        LiveAlarmRecord.tenant_id == tenant_id,
    )
    if sessionCode:
        stmt = stmt.where(LiveAlarmRecord.session_code == sessionCode)
    if alarmLevel in (1, 2, 3):
        stmt = stmt.where(LiveAlarmRecord.alarm_level == alarmLevel)
    if handleStatus:
        stmt = stmt.where(LiveAlarmRecord.handle_status == handleStatus)
    if len(timeRange) >= 2 and timeRange[0] and timeRange[1]:
        stmt = stmt.where(LiveAlarmRecord.occur_at >= timeRange[0], LiveAlarmRecord.occur_at <= timeRange[1])
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(LiveAlarmRecord.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    names = user_names(db, {row.handler_user_id for row in rows if row.handler_user_id})
    items = [record_vo(row, names) for row in rows]
    return ok({"list": items, "total": total, "pageNo": page_no, "pageSize": size})


@router.put("/alarm/record/{record_id}/handle")
def alarm_handle(
    record_id: int,
    body: HandleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if body.handleStatus not in HANDLE_STATUS:
        return fail(1001, "处置动作不合法")
    if len(body.handleRemark or "") > 512:
        return fail(1001, "处置说明不超过 512 字")
    row = db.get(LiveAlarmRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1504, "资源不可用")
    if row.handle_status != "UNHANDLED":
        return fail(1001, "告警已处置，请刷新")
    row.handle_status = body.handleStatus
    row.handler_user_id = actor.id
    row.handle_remark = (body.handleRemark or "")[:512]
    return ok(None)


@router.get("/alarm/rules")
def alarm_rules(
    pageNo: int = 1,
    pageSize: int = 20,
    ruleType: str = "",
    status: str = "",
    keyword: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_manage_rules(db, actor):
        return fail(1008, "无数据权限")
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(LiveAlarmRule).where(
        LiveAlarmRule.deleted == 0,
        LiveAlarmRule.tenant_id == tenant_of(actor),
    )
    if ruleType:
        stmt = stmt.where(LiveAlarmRule.rule_type == ruleType)
    if status:
        stmt = stmt.where(LiveAlarmRule.status == status)
    if keyword.strip():
        stmt = stmt.where(LiveAlarmRule.rule_name.contains(keyword.strip()))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(LiveAlarmRule.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    return ok({"list": [rule_vo(db, row) for row in rows], "total": total, "pageNo": page_no, "pageSize": size})


@router.post("/alarm/rule")
def alarm_rule_create(
    body: RuleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_manage_rules(db, actor):
        return fail(1008, "无数据权限")
    rejected = reject_rule(body)
    if rejected is not None:
        return rejected
    row = LiveAlarmRule(
        rule_name=body.ruleName.strip(),
        rule_type=body.ruleType,
        rule_expr=dump_expr(body.ruleExpr),
        level=body.level,
        notify_users=json.dumps(body.notifyUsers),
        status=body.status,
        tenant_id=tenant_of(actor),
    )
    db.add(row)
    db.flush()
    return ok(rule_vo(db, row))


@router.put("/alarm/rule/{rule_id}")
def alarm_rule_update(
    rule_id: int,
    body: RuleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_manage_rules(db, actor):
        return fail(1008, "无数据权限")
    rejected = reject_rule(body)
    if rejected is not None:
        return rejected
    row = db.get(LiveAlarmRule, rule_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1504, "资源不可用")
    row.rule_name = body.ruleName.strip()
    row.rule_type = body.ruleType
    row.rule_expr = dump_expr(body.ruleExpr)
    row.level = body.level
    row.notify_users = json.dumps(body.notifyUsers)
    row.status = body.status
    from app.core import utcnow

    row.updated_at = utcnow()
    return ok(None)


@router.delete("/alarm/rule/{rule_id}")
def alarm_rule_delete(
    rule_id: int,
    confirmText: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_manage_rules(db, actor):
        return fail(1008, "无数据权限")
    if confirmText != "DELETE":
        return fail(1001, "请输入 DELETE 确认删除")
    row = db.get(LiveAlarmRule, rule_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1504, "资源不可用")
    row.deleted = 1
    return ok(None)


@router.get("/alarm/stats")
def alarm_stats(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    sweep_alarms(db, tenant_id)
    rows = db.scalars(
        select(LiveAlarmRecord).where(
            LiveAlarmRecord.deleted == 0,
            LiveAlarmRecord.tenant_id == tenant_id,
        )
    ).all()
    by_level = {"1": 0, "2": 0, "3": 0}
    by_status: dict[str, int] = {}
    by_day: dict[str, dict[str, int]] = {}
    today = clock().date()
    for offset in range(6, -1, -1):
        by_day[(today - timedelta(days=offset)).isoformat()] = {"total": 0, "severe": 0}
    for row in rows:
        key = str(row.alarm_level)
        if key in by_level:
            by_level[key] += 1
        by_status[row.handle_status] = by_status.get(row.handle_status, 0) + 1
        day = (row.occur_at or "")[:10]
        if day in by_day:
            by_day[day]["total"] += 1
            if row.alarm_level == 3:
                by_day[day]["severe"] += 1
    trend = [{"date": day, "total": bucket["total"], "severe": bucket["severe"]} for day, bucket in by_day.items()]
    return ok({"byLevel": by_level, "byHandleStatus": by_status, "trend": trend})


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
    _upsert_alarm(
        db,
        tenant_id=0,
        session_code=AGED_SESSION,
        level=3,
        content="场观 5 分钟内骤降 42%",
        minutes_ago=31,
    )
    _upsert_alarm(
        db,
        tenant_id=0,
        session_code=FRESH_L3_SESSION,
        level=3,
        content="场观 5 分钟内骤降 18%",
        minutes_ago=2,
    )
    _upsert_alarm(
        db,
        tenant_id=0,
        session_code=FRESH_L2_SESSION,
        level=2,
        content="话费余额低于阈值",
        minutes_ago=5,
    )
