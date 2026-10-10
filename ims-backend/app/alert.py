"""预警 ALERT-001 规则 · ALERT-002 检查记录 · #141 命中统计/周报/升级轮询。

钉钉与短信外发保持本地桩：升级时间轴只写接收人角色，不调用外发。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.alert_escalate import router as escalate_router
from app.models import AlertDedupPolicy, AlertRecord, AlertRule, User

router = APIRouter(prefix="/alert", tags=["alert"])
router.include_router(escalate_router)

BJ = timezone(timedelta(hours=8))
# 契约 AlertEventStatus。1=CONFIRMED（旧称 ACK），2=RESOLVED（旧称 HANDLED）。
RESPONSE_LABELS = {0: "OPEN", 1: "CONFIRMED", 2: "RESOLVED", 3: "FALSE_ALARM"}
# 0 待推送（无回执）/ 1 工作台+钉钉本地记账 / 2 钉钉失败后短信兜底记账 / 3 补发后仍失败。
# 钉钉与短信 success 只表示本地桩已记账，outbound 恒为 false，不外发。
PUSH_LABELS = {0: "PENDING", 1: "DELIVERED", 2: "PARTIAL_FAILED", 3: "FAILED"}
PUSH_CODES = {label: code for code, label in PUSH_LABELS.items()}
SOURCE_JUMPS = {
    "SESSION": "/ims/live",
    "CERT": "/ims/corp/resource/certificate",
    "ACCOUNT": "/ims/corp/account/douyin",
    "COST": "/ims/cost",
    "MANUAL": "/ims/alert/rule",
}
PRIORITY_NOTE = "严重级 1 分钟内送达：工作台与钉钉优先，短信仅兜底。本地桩，不外发（ALR-P-R1）"
STATUS_ALIASES = {
    "ACK": "CONFIRMED",
    "HANDLED": "RESOLVED",
    "FALSE_POSITIVE": "FALSE_ALARM",
    "MISREPORT": "FALSE_ALARM",
}
# 已解决 / 误报为终态。已确认仍可处理或标误报。OPEN 仍可直接处理，保留试跑→处理闭环。
TERMINAL_STATUS = {2, 3}
ALLOWED_NEXT = {0: {1, 2, 3}, 1: {2, 3}}
DSL_OPS = {"GT", "GTE", "LT", "LTE", "EQ", "NEQ"}
DSL_KEYS = {"source", "condition", "conditions", "mergeWindowMinutes"}
COND_KEYS = {"field", "op", "value"}
IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
LEGACY_EXPR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\s*(>=|<=|==|!=|>|<)\s*-?\d+(\.\d+)?$")
# BR-114：默认同规则+同对象 30 分钟窗口。本环境只做统计归并，不改写入、不外发。
MERGE_WINDOW_MINUTES = 30
# 钉钉/短信只在统计页标明本地桩。outbound=False 表示没有外发。
CHANNEL_STUBS = [
    {"channel": "WORKBENCH", "label": "工作台", "mode": "LOCAL", "outbound": False, "countsTowardDelivery": True},
    {"channel": "DINGTALK", "label": "钉钉", "mode": "STUB", "outbound": False, "countsTowardDelivery": False},
    {"channel": "SMS", "label": "短信", "mode": "STUB", "outbound": False, "countsTowardDelivery": False},
]


class RuleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ruleCode: str
    ruleName: str
    metricType: str = "THRESHOLD"
    level: int = Field(default=2, ge=1, le=3)
    thresholdExpr: str = ""
    cronExpr: str = "0 */15 * * *"
    enabled: bool = False
    triggerConfig: Any = None


class RuleUpdateBody(BaseModel):
    """编辑阈值等参数。ruleCode 不可改（契约 Omit id | ruleCode）。"""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    ruleName: str | None = None
    metricType: str | None = None
    level: int | None = Field(default=None, ge=1, le=3)
    thresholdExpr: str | None = None
    cronExpr: str | None = None
    enabled: bool | None = None
    triggerConfig: Any = None


class RespondBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: str = ""
    response: str = ""
    handleRemark: str = ""
    falseAlarmReason: str = ""


def status_code(label: str) -> int | None:
    key = STATUS_ALIASES.get(label.upper(), label.upper())
    rev = {value: code for code, value in RESPONSE_LABELS.items()}
    return rev.get(key)


def parse_level(raw: str | None) -> tuple[int | None, str | None]:
    if raw is None or not str(raw).strip():
        return None, None
    text = str(raw).strip().upper()
    if text.startswith("L"):
        text = text[1:]
    if text in {"1", "2", "3"}:
        return int(text), None
    return None, "level 无效"


def parse_push(raw: str | None) -> tuple[int | None, str | None]:
    if raw is None or not str(raw).strip():
        return None, None
    key = str(raw).strip().upper()
    if key in PUSH_CODES:
        return PUSH_CODES[key], None
    if key.isdigit() and int(key) in PUSH_LABELS:
        return int(key), None
    return None, "pushStatus 无效"


def push_channels(row: AlertRecord) -> list[dict]:
    """本地回执。待推送返回空列表。短信未触发时 empty=true。不外发。"""
    at = iso(row.occurred_at) if row.occurred_at else None
    status = row.push_status

    def channel(
        code: str,
        label: str,
        success: bool,
        stub: bool,
        empty: bool = False,
        status_note: str = "",
    ) -> dict:
        item = {
            "channel": code,
            "label": label,
            "success": success,
            "outbound": False,
            "stub": stub,
            "empty": empty,
            "statusNote": status_note,
        }
        if success and at:
            item["receiptAt"] = at
        return item

    if status == 0:
        return []
    if status == 2:
        return [
            channel("WORKBENCH", "工作台", True, False, status_note="已落库"),
            channel("DINGTALK", "钉钉", False, True, status_note="失败，已改记短信兜底"),
            channel("SMS", "短信", True, True, status_note="兜底已记账，不外发"),
        ]
    if status == 3:
        return [
            channel("WORKBENCH", "工作台", False, False, status_note="补发后仍失败"),
            channel("DINGTALK", "钉钉", False, True, status_note="补发后仍失败"),
            channel("SMS", "短信", False, True, status_note="补发后仍失败"),
        ]
    return [
        channel("WORKBENCH", "工作台", True, False, status_note="已落库"),
        channel("DINGTALK", "钉钉", True, True, status_note="本地桩已记账，不外发"),
        channel("SMS", "短信", False, True, empty=True, status_note="未触发，不外发"),
    ]


def source_jump(row: AlertRecord) -> str:
    return SOURCE_JUMPS.get((row.source_ref_type or "").upper(), "")


def rate_pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(part * 100.0 / whole, 2)


def parse_day_range(raw: str | None) -> tuple[datetime | None, datetime | None, str | None]:
    """逗号分隔的 yyyy-MM-dd。空值不限；起大于止或格式不对返回错误文案。"""
    if raw is None or not str(raw).strip():
        return None, None, None
    parts = [part.strip() for part in str(raw).split(",") if part.strip()]
    if len(parts) != 2:
        return None, None, "日期范围无效"
    try:
        start = datetime.strptime(parts[0], "%Y-%m-%d")
        end_day = datetime.strptime(parts[1], "%Y-%m-%d")
    except ValueError:
        return None, None, "日期范围无效"
    if start > end_day:
        return None, None, "日期范围起大于止"
    end = end_day.replace(hour=23, minute=59, second=59)
    return start, end, None


def _ident(value: Any) -> bool:
    return isinstance(value, str) and bool(IDENT_RE.match(value))


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _condition_error(cond: Any, prefix: str) -> str | None:
    if not isinstance(cond, dict):
        return f"{prefix} 须为对象"
    extra = set(cond) - COND_KEYS
    if extra:
        return f"{prefix} 含未知字段 {sorted(extra)[0]}"
    if not _ident(cond.get("field")):
        return f"{prefix}.field 非法"
    op = cond.get("op")
    if not isinstance(op, str) or op not in DSL_OPS:
        return f"{prefix}.op 非法，允许 {', '.join(sorted(DSL_OPS))}"
    if "value" not in cond or not _number(cond.get("value")):
        return f"{prefix}.value 须为数字"
    return None


def dsl_error(cfg: Any) -> str | None:
    """triggerConfig 非法时返回原因；合法返回 None。错误码 1009。"""
    if not isinstance(cfg, dict):
        return "triggerConfig 须为对象"
    extra = set(cfg) - DSL_KEYS
    if extra:
        return f"triggerConfig 含未知字段 {sorted(extra)[0]}"
    if not _ident(cfg.get("source")):
        return "source 非法"
    has_one = "condition" in cfg
    has_many = "conditions" in cfg
    if not has_one and not has_many:
        return "condition 缺失"
    if has_one:
        reason = _condition_error(cfg.get("condition"), "condition")
        if reason:
            return reason
    if has_many:
        rows = cfg.get("conditions")
        if not isinstance(rows, list) or not rows:
            return "conditions 须为非空数组"
        for index, row in enumerate(rows):
            reason = _condition_error(row, f"conditions[{index}]")
            if reason:
                return reason
    if "mergeWindowMinutes" in cfg:
        window = cfg.get("mergeWindowMinutes")
        if isinstance(window, bool) or not isinstance(window, int) or window < 5 or window > 60:
            return "mergeWindowMinutes 须为 5~60 的整数"
    return None


def dsl_summary(cfg: dict) -> str:
    cond = cfg.get("condition")
    if not isinstance(cond, dict):
        rows = cfg.get("conditions") or []
        cond = rows[0] if rows else {}
    return f"{cfg.get('source')}.{cond.get('field')} {cond.get('op')} {cond.get('value')}"


def legacy_expr_error(expr: str) -> str | None:
    text = expr.strip()
    if not text:
        return None
    if LEGACY_EXPR_RE.match(text):
        return None
    return "thresholdExpr 不是合法比较式（字段><=数字）"


def fail_dsl(reason: str):
    return fail(1009, f"预警规则 DSL 非法（1009）：{reason}")


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_rule_code(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"AR{day}"
    count = db.scalar(
        select(func.count())
        .select_from(AlertRule)
        .where(
            AlertRule.deleted == 0,
            AlertRule.tenant_id == tenant_id,
            AlertRule.rule_code.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def next_alert_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"AL{day}"
    count = db.scalar(
        select(func.count())
        .select_from(AlertRecord)
        .where(
            AlertRecord.deleted == 0,
            AlertRecord.tenant_id == tenant_id,
            AlertRecord.alert_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def rule_vo(row: AlertRule) -> dict:
    return {
        "id": row.id,
        "ruleCode": row.rule_code,
        "ruleName": row.rule_name,
        "metricType": row.metric_type,
        "level": row.level,
        "thresholdExpr": row.threshold_expr,
        "cronExpr": row.cron_expr,
        "enabled": bool(row.enabled),
        "hitCount": row.hit_count,
        "createdAt": iso(row.created_at),
    }


def record_vo(row: AlertRecord, rule: AlertRule | None = None) -> dict:
    rule_code = rule.rule_code if rule else ""
    ref = f"{row.source_ref_type or ''}:{row.source_ref_id or 0}"
    return {
        "id": row.id,
        "alertNo": row.alert_no,
        "ruleId": row.rule_id,
        "ruleCode": rule_code,
        "ruleName": rule.rule_name if rule else "",
        "level": row.level,
        "content": row.content,
        "sourceRefType": row.source_ref_type or None,
        "sourceRefId": row.source_ref_id or None,
        "dedupKey": f"{rule_code}+{ref}" if rule_code else ref,
        "mergedCount": 1,
        "notifyTargetUserIds": [],
        "pushStatus": PUSH_LABELS.get(row.push_status, "PENDING"),
        "pushChannels": push_channels(row),
        "responseStatus": RESPONSE_LABELS.get(row.response_status, "OPEN"),
        "occurredAt": iso(row.occurred_at),
    }


def _rules_for(db: Session, rows: list[AlertRecord]) -> dict[int, AlertRule]:
    rule_ids = {row.rule_id for row in rows if row.rule_id}
    if not rule_ids:
        return {}
    return {rule.id: rule for rule in db.scalars(select(AlertRule).where(AlertRule.id.in_(rule_ids))).all()}


def channel_receipts(rows: list[AlertRecord]) -> list[dict]:
    """范围内回执计数。短信仅在兜底记账后有数，否则为空态。"""
    counts = {"WORKBENCH": 0, "DINGTALK": 0, "SMS": 0}
    for row in rows:
        if row.push_status == 1:
            counts["WORKBENCH"] += 1
            counts["DINGTALK"] += 1
        elif row.push_status == 2:
            counts["WORKBENCH"] += 1
            counts["SMS"] += 1
    specs = (
        ("WORKBENCH", "工作台", "LOCAL", False, "工作台已落库才计入回执"),
        ("DINGTALK", "钉钉", "STUB", True, "本地桩，不外发"),
        ("SMS", "短信", "STUB", True, "短信仅兜底，未触发则无回执"),
    )
    result = []
    for code, label, mode, stub, note in specs:
        count = counts[code]
        result.append(
            {
                "channel": code,
                "label": label,
                "mode": mode,
                "outbound": False,
                "stub": stub,
                "receiptCount": count,
                "empty": count == 0,
                "note": note,
            }
        )
    return result


@router.get("/rule/list")
def rule_list(
    ruleName: str | None = None,
    enabled: bool | None = None,
    level: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    level_code, level_error = parse_level(level)
    if level_error:
        return fail(1001, level_error)
    stmt = select(AlertRule).where(AlertRule.deleted == 0, AlertRule.tenant_id == tenant_id)
    if ruleName:
        stmt = stmt.where(AlertRule.rule_name.contains(ruleName.strip()))
    if enabled is not None:
        stmt = stmt.where(AlertRule.enabled == (1 if enabled else 0))
    if level_code is not None:
        stmt = stmt.where(AlertRule.level == level_code)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(AlertRule.enabled.desc(), AlertRule.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([rule_vo(row) for row in rows], total, page_no, size)


@router.post("/rule")
def create_rule(
    body: RuleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    code = body.ruleCode.strip()
    name = body.ruleName.strip()
    if not code and not name:
        return fail(1001, "ruleCode 或 ruleName 必填")
    tenant_id = tenant_of(actor)
    if code:
        dup = db.scalar(
            select(AlertRule.id).where(
                AlertRule.deleted == 0,
                AlertRule.tenant_id == tenant_id,
                AlertRule.rule_code == code,
            )
        )
        if dup:
            return fail(1165, "规则编码已存在（1165）")
    if not code:
        code = next_rule_code(db, tenant_id)
    stored_expr = body.thresholdExpr.strip()
    if body.triggerConfig is not None:
        reason = dsl_error(body.triggerConfig)
        if reason:
            return fail_dsl(reason)
        stored_expr = dsl_summary(body.triggerConfig)
    elif stored_expr:
        reason = legacy_expr_error(stored_expr)
        if reason:
            return fail_dsl(reason)
    row = AlertRule(
        rule_code=code,
        rule_name=name or code,
        metric_type=body.metricType.strip() or "THRESHOLD",
        level=body.level,
        threshold_expr=stored_expr,
        cron_expr=body.cronExpr.strip() or "0 */15 * * *",
        enabled=1 if body.enabled else 0,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(rule_vo(row))


@router.put("/rule/{rule_id}")
def update_rule(
    rule_id: int,
    body: RuleUpdateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """阈值热更新（ALR-C-R2）。ruleCode 忽略，不因请求体改编码。"""
    tenant_id = tenant_of(actor)
    row = db.get(AlertRule, rule_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "规则不存在")
    if body.ruleName is not None:
        name = body.ruleName.strip()
        if not name:
            return fail(1001, "ruleName 不能为空")
        row.rule_name = name
    if body.metricType is not None and body.metricType.strip():
        row.metric_type = body.metricType.strip()
    if body.level is not None:
        row.level = body.level
    if body.cronExpr is not None and body.cronExpr.strip():
        row.cron_expr = body.cronExpr.strip()
    if body.enabled is not None:
        row.enabled = 1 if body.enabled else 0
    if body.triggerConfig is not None:
        reason = dsl_error(body.triggerConfig)
        if reason:
            return fail_dsl(reason)
        row.threshold_expr = dsl_summary(body.triggerConfig)
    elif body.thresholdExpr is not None:
        expr = body.thresholdExpr.strip()
        if expr != (row.threshold_expr or ""):
            if expr:
                reason = legacy_expr_error(expr)
                if reason:
                    return fail_dsl(reason)
            row.threshold_expr = expr
    row.updated_at = utcnow()
    db.flush()
    return ok(rule_vo(row))


@router.put("/rule/{rule_id}/enable")
def toggle_rule(
    rule_id: int,
    enabled: bool = True,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(AlertRule, rule_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "规则不存在")
    row.enabled = 1 if enabled else 0
    row.updated_at = utcnow()
    db.flush()
    return ok(rule_vo(row))


@router.get("/check/records")
def check_records(
    responseStatus: str | None = None,
    ruleId: int | None = None,
    ruleCode: str | None = None,
    level: str | None = None,
    pushStatus: str | None = None,
    dateRange: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AlertRecord).where(AlertRecord.deleted == 0, AlertRecord.tenant_id == tenant_id)
    if ruleId:
        stmt = stmt.where(AlertRecord.rule_id == ruleId)
    code = (ruleCode or "").strip()
    if code:
        matched = list(
            db.scalars(
                select(AlertRule.id).where(
                    AlertRule.deleted == 0,
                    AlertRule.tenant_id == tenant_id,
                    AlertRule.rule_code == code,
                )
            ).all()
        )
        if not matched:
            return paged([], 0, page_no, size)
        stmt = stmt.where(AlertRecord.rule_id.in_(matched))
    level_code, level_error = parse_level(level)
    if level_error:
        return fail(1001, level_error)
    if level_code is not None:
        stmt = stmt.where(AlertRecord.level == level_code)
    push_code, push_error = parse_push(pushStatus)
    if push_error:
        return fail(1001, push_error)
    if push_code is not None:
        stmt = stmt.where(AlertRecord.push_status == push_code)
    if responseStatus:
        status = status_code(responseStatus)
        if status is None:
            return fail(1001, "responseStatus 无效")
        stmt = stmt.where(AlertRecord.response_status == status)
    start, end, range_error = parse_day_range(dateRange)
    if range_error:
        return fail(1001, range_error)
    if start is not None:
        stmt = stmt.where(AlertRecord.occurred_at >= start)
    if end is not None:
        stmt = stmt.where(AlertRecord.occurred_at <= end)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(AlertRecord.occurred_at.desc(), AlertRecord.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    rules = _rules_for(db, rows)
    return paged([record_vo(r, rules.get(r.rule_id)) for r in rows], total, page_no, size)


def _find_record(db: Session, tenant_id: int, alert_no: str) -> AlertRecord | None:
    return db.scalar(
        select(AlertRecord).where(
            AlertRecord.deleted == 0,
            AlertRecord.tenant_id == tenant_id,
            AlertRecord.alert_no == alert_no,
        )
    )


@router.get("/check/my-alerts")
def my_alerts(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    """工作台「我的预警」。本库没有通知目标人列，未响应记录即当前租户待办。"""
    tenant_id = tenant_of(actor)
    rows = list(
        db.scalars(
            select(AlertRecord)
            .where(
                AlertRecord.deleted == 0,
                AlertRecord.tenant_id == tenant_id,
                AlertRecord.response_status == 0,
            )
            .order_by(AlertRecord.occurred_at.desc(), AlertRecord.id.desc())
            .limit(20)
        ).all()
    )
    rules = _rules_for(db, rows)
    data = []
    for row in rows:
        item = record_vo(row, rules.get(row.rule_id))
        item["isUnread"] = True
        data.append(item)
    return ok(data)


@router.get("/check/delivery-stats")
def delivery_stats(
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """送达率。分母为记录数，分子为 push_status=1。失败明细含本地补发 1 次，不外发钉钉/短信。"""
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    rows = _overview_rows(db, tenant_of(actor), start, end)
    delivered = 0
    failed: list[dict] = []
    for row in rows:
        if row.push_status == 1:
            delivered += 1
        elif row.push_status == 2:
            failed.append({"alertNo": row.alert_no, "failedChannel": "DINGTALK", "retryCount": 1})
        elif row.push_status == 3:
            failed.append({"alertNo": row.alert_no, "failedChannel": "SMS", "retryCount": 1})
    total = len(rows)
    return ok(
        {
            "totalDelivered": delivered,
            "totalShould": total,
            "deliveryRate": rate_pct(delivered, total),
            "failedAlerts": failed[:20],
            "target": 99,
        }
    )


@router.get("/check/{alert_no}")
def check_detail(
    alert_no: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = _find_record(db, tenant_id, alert_no)
    if row is None:
        return fail(1500, "预警不存在")
    rule = db.get(AlertRule, row.rule_id) if row.rule_id else None
    channels = push_channels(row)
    data = record_vo(row, rule)
    data["ruleCode"] = rule.rule_code if rule else data.get("ruleCode") or ""
    data["pushChannels"] = channels
    data["receiptEmpty"] = not channels
    data["priorityNote"] = PRIORITY_NOTE if row.level == 3 else ""
    if row.push_status == 2:
        data["retryNote"] = "钉钉未送达，已改记短信兜底 1 次（不外发）"
    elif row.push_status == 3:
        data["retryNote"] = "已自动补发 1 次（ALR-P-R2）"
    else:
        data["retryNote"] = ""
    data["sourceJumpUrl"] = source_jump(row)
    data["escalationTimeline"] = []
    data["retryCount"] = 1 if row.push_status in (2, 3) else 0
    return ok(data)


@router.put("/check/{alert_no}/respond")
def respond_alert(
    alert_no: str,
    body: RespondBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    action = (body.action or body.response or "").upper()
    mapping = {
        "ACK": 1,
        "CONFIRM": 1,
        "HANDLE": 2,
        "HANDLED": 2,
        "RESOLVE": 2,
        "FALSE_POSITIVE": 3,
        "MISREPORT": 3,
        "FALSE_ALARM": 3,
    }
    if action not in mapping:
        return fail(1001, "action 无效")
    tenant_id = tenant_of(actor)
    row = _find_record(db, tenant_id, alert_no)
    if row is None:
        return fail(1500, "预警不存在")
    from app.alert_escalate import actor_may_respond

    rule = db.get(AlertRule, row.rule_id) if row.rule_id else None
    if not actor_may_respond(db, actor, rule):
        return fail(1166, "仅预警目标人或运营总监可响应（1166）")
    if row.response_status in TERMINAL_STATUS:
        return fail(1167, "预警已终态不可重复响应（1167）")
    target = mapping[action]
    if target not in ALLOWED_NEXT.get(row.response_status, set()):
        return fail(1001, "当前状态不可执行该响应")
    row.response_status = target
    notes: list[str] = []
    if action == "FALSE_ALARM" and (body.falseAlarmReason or "").strip():
        notes.append(f"误报原因：{body.falseAlarmReason.strip()}")
    if (body.handleRemark or "").strip():
        notes.append(f"处理说明：{body.handleRemark.strip()}")
    if notes:
        row.content = f"{row.content}；{'；'.join(notes)}"[:512]
    row.updated_at = utcnow()
    db.flush()
    data = record_vo(row, rule)
    data["escalationStopped"] = True
    return ok(data)


def seed_dedup_policies(db: Session, tenant_id: int) -> None:
    has = db.scalar(
        select(func.count()).select_from(AlertDedupPolicy).where(
            AlertDedupPolicy.deleted == 0, AlertDedupPolicy.tenant_id == tenant_id
        )
    )
    if has:
        return
    now = utcnow()
    for code, name, window, expr in (
        ("DEDUP-LIVE", "直播指标窗口去重", 15, "ruleId+sourceRefId"),
        ("DEDUP-COLLECT", "采集异常合并", 30, "ruleId+metricType"),
    ):
        db.add(
            AlertDedupPolicy(
                policy_code=code,
                policy_name=name,
                window_minutes=window,
                merge_key_expr=expr,
                enabled=1,
                merged_count=0,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    db.flush()


def dedup_vo(row: AlertDedupPolicy) -> dict:
    return {
        "id": row.id,
        "policyCode": row.policy_code,
        "policyName": row.policy_name,
        "windowMinutes": row.window_minutes,
        "mergeKeyExpr": row.merge_key_expr,
        "enabled": bool(row.enabled),
        "mergedCount": row.merged_count,
        "updatedAt": iso(row.updated_at),
    }


@router.get("/dedup/list")
def dedup_list(
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_dedup_policies(db, tenant_id)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AlertDedupPolicy).where(AlertDedupPolicy.deleted == 0, AlertDedupPolicy.tenant_id == tenant_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(stmt.order_by(AlertDedupPolicy.enabled.desc(), AlertDedupPolicy.id).offset((page_no - 1) * size).limit(size)).all()
    )
    return paged([dedup_vo(r) for r in rows], total, page_no, size)


@router.get("/history/summary")
def history_summary(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    base = select(AlertRecord).where(AlertRecord.deleted == 0, AlertRecord.tenant_id == tenant_id)
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    handled = int(
        db.scalar(
            select(func.count()).select_from(AlertRecord).where(
                AlertRecord.deleted == 0,
                AlertRecord.tenant_id == tenant_id,
                AlertRecord.response_status.in_([1, 2, 3]),
            )
        )
        or 0
    )
    false_pos = int(
        db.scalar(
            select(func.count()).select_from(AlertRecord).where(
                AlertRecord.deleted == 0,
                AlertRecord.tenant_id == tenant_id,
                AlertRecord.response_status == 3,
            )
        )
        or 0
    )
    return ok(
        {
            "totalAlerts": total,
            "handledCount": handled,
            "falsePositiveCount": false_pos,
            "openCount": max(total - handled, 0),
        }
    )


def _overview_rows(db: Session, tenant_id: int, start: datetime | None, end: datetime | None) -> list[AlertRecord]:
    stmt = select(AlertRecord).where(AlertRecord.deleted == 0, AlertRecord.tenant_id == tenant_id)
    if start is not None:
        stmt = stmt.where(AlertRecord.occurred_at >= start)
    if end is not None:
        stmt = stmt.where(AlertRecord.occurred_at <= end)
    return list(db.scalars(stmt).all())


@router.get("/stats/overview")
def stats_overview(
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """全局统计总览。resolutionRate 为 E2E-S11-06 解决率，契约总览未单列，同响应追加。

    响应时长取已响应记录（非 OPEN）的 updated_at − occurred_at 均值（分钟）。
    送达率按 push_status=1（工作台已落库）计，不含钉钉/短信外发。
    通道回执只做本地计数：钉钉为桩，短信未兜底时为空。
    升级率：越过起始级（默认一级 30 分钟，L3 从二级起）仍未在时限内响应的占比。
    """
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    rows = _overview_rows(db, tenant_id, start, end)
    total = len(rows)
    by_level = {"L1": 0, "L2": 0, "L3": 0}
    responded = 0
    resolved = 0
    false_alarm = 0
    delivered = 0
    minutes: list[float] = []
    level_key = {1: "L1", 2: "L2", 3: "L3"}
    for row in rows:
        key = level_key.get(row.level)
        if key:
            by_level[key] += 1
        if row.push_status == 1:
            delivered += 1
        if row.response_status in (1, 2, 3):
            responded += 1
            if row.occurred_at is not None and row.updated_at is not None:
                delta = (row.updated_at - row.occurred_at).total_seconds() / 60.0
                minutes.append(delta if delta > 0 else 0.0)
        if row.response_status == 2:
            resolved += 1
        elif row.response_status == 3:
            false_alarm += 1
    avg = round(sum(minutes) / len(minutes), 2) if minutes else 0.0
    from app.alert_escalate import count_escalated

    escalated = count_escalated(db, tenant_id, rows)
    return ok(
        {
            "totalAlertCount": total,
            "byLevel": by_level,
            "responseRate": rate_pct(responded, total),
            "resolutionRate": rate_pct(resolved, total),
            "deliveryRate": rate_pct(delivered, total),
            "falseAlarmRate": rate_pct(false_alarm, total),
            "escalateRate": rate_pct(escalated, total),
            "avgResponseMinutes": avg,
            "respondedCount": responded,
            "resolvedCount": resolved,
            "falseAlarmCount": false_alarm,
            "channelStubs": CHANNEL_STUBS,
            "channelReceipts": channel_receipts(rows),
        }
    )


# BR-113：一级 30 分钟、二级再 60 分钟。L3 从二级起跳（ALR-E-R2）。
LEVEL1_TIMEOUT_MINUTES = 30
LEVEL2_TIMEOUT_MINUTES = 60
RESPONSE_TARGET = 90.0
# 本地桩接收人，仅用于时间轴展示，不触发钉钉/短信。
STUB_RECEIVERS = {
    1: [{"userId": 0, "userName": "责任人", "roleLabel": "责任人"}],
    2: [{"userId": 0, "userName": "部门负责人", "roleLabel": "部门负责人"}],
    3: [
        {"userId": 0, "userName": "运营总监", "roleLabel": "R4"},
        {"userId": 0, "userName": "系统管理员", "roleLabel": "R1"},
    ],
}


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def iso_utc(dt: datetime | None) -> str:
    """库内 naive UTC 转成带 +08:00 的东八区时刻，供前端倒计时解析。"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def level_label(level: int) -> str:
    return {1: "L1", 2: "L2", 3: "L3"}.get(level, "L2")


def escalation_state(row: AlertRecord, now: datetime) -> tuple[int, datetime | None]:
    """返回 (currentLevel, nextEscalateAt)。next 为 naive UTC，终级为 None。"""
    now_naive = _naive_utc(now)
    occurred = _naive_utc(row.occurred_at or now_naive)
    elapsed = (now_naive - occurred).total_seconds() / 60.0
    if elapsed < 0:
        elapsed = 0.0
    if (row.level or 0) >= 3:
        if elapsed < LEVEL2_TIMEOUT_MINUTES:
            return 2, occurred + timedelta(minutes=LEVEL2_TIMEOUT_MINUTES)
        return 3, None
    if elapsed < LEVEL1_TIMEOUT_MINUTES:
        return 1, occurred + timedelta(minutes=LEVEL1_TIMEOUT_MINUTES)
    gate = LEVEL1_TIMEOUT_MINUTES + LEVEL2_TIMEOUT_MINUTES
    if elapsed < gate:
        return 2, occurred + timedelta(minutes=gate)
    return 3, None


def escalation_at(row: AlertRecord, now: datetime) -> tuple[int, datetime | None]:
    """未响应按当前时刻；已响应按处置时刻，避免事后把已关闭预警算成仍在升级。"""
    if row.response_status == 0:
        return escalation_state(row, now)
    anchor = row.updated_at or row.occurred_at or now
    return escalation_state(row, anchor)


def week_window(week_start: str | None) -> tuple[datetime | None, datetime | None, list[str], str | None]:
    """自然周（东八区周一至周日）。返回的起止是 naive UTC，便于和 occurred_at 比较。"""
    raw = (week_start or "").strip()
    if raw:
        try:
            civil = datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None, None, [], "weekStart 无效"
    else:
        civil = datetime.now(BJ).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    start_civil = (civil - timedelta(days=civil.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_civil = start_civil + timedelta(days=6)
    start_utc = start_civil.replace(tzinfo=BJ).astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_civil.replace(hour=23, minute=59, second=59, tzinfo=BJ).astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc, [start_civil.strftime("%Y-%m-%d"), end_civil.strftime("%Y-%m-%d")], None


def _rules_map(db: Session, ids: set[int]) -> dict[int, AlertRule]:
    if not ids:
        return {}
    return {row.id: row for row in db.scalars(select(AlertRule).where(AlertRule.id.in_(ids))).all()}


def _hit_bucket() -> dict[str, Any]:
    return {
        "alertCount": 0,
        "responded": 0,
        "falseAlarmCount": 0,
        "delivered": 0,
        "lastHitAt": None,
    }


def _accumulate(bucket: dict[str, Any], row: AlertRecord) -> None:
    bucket["alertCount"] += 1
    if row.response_status in (1, 2, 3):
        bucket["responded"] += 1
    if row.response_status == 3:
        bucket["falseAlarmCount"] += 1
    if row.push_status == 1:
        bucket["delivered"] += 1
    if row.occurred_at is not None and (bucket["lastHitAt"] is None or row.occurred_at > bucket["lastHitAt"]):
        bucket["lastHitAt"] = row.occurred_at


@router.get("/rule/hit-stats")
def rule_hit_stats(
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """规则命中统计。误报 ≥5 的复核标记由前端按 falseAlarmCount 展示。"""
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    rows = _overview_rows(db, tenant_id, start, end)
    rules = _rules_map(db, {row.rule_id for row in rows if row.rule_id})
    buckets: dict[int, dict[str, Any]] = {}
    for row in rows:
        buckets.setdefault(row.rule_id, _hit_bucket())
        _accumulate(buckets[row.rule_id], row)
    data = []
    for rule_id, bucket in buckets.items():
        rule = rules.get(rule_id)
        data.append(
            {
                "ruleCode": rule.rule_code if rule else "",
                "ruleName": rule.rule_name if rule else "",
                "alertCount": bucket["alertCount"],
                "responseRate": rate_pct(bucket["responded"], bucket["alertCount"]),
                "falseAlarmCount": bucket["falseAlarmCount"],
                "lastHitAt": iso(bucket["lastHitAt"]) if bucket["lastHitAt"] else "",
            }
        )
    data.sort(key=lambda item: (-item["alertCount"], item["ruleCode"]))
    return ok(data)


def _suggestion_lines(total: int, response_rate: float, false_by_rule: list[tuple[str, int]]) -> list[str]:
    if total <= 0:
        return []
    notes: list[str] = []
    if response_rate < RESPONSE_TARGET:
        notes.append(f"本周响应率 {response_rate}% 低于 90%（BR-112），建议优先处理未响应预警")
    for code, count in false_by_rule:
        if count >= 5 and code:
            notes.append(f"规则 {code} 误报 {count} 次，建议复核阈值（ALR-S-R3）")
    notes.append("钉钉/短信外发保持本地桩，周报仅在线查看，不实际推送")
    return notes


@router.get("/stats/weekly-report")
def weekly_report(
    weekStart: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """在线周报。外发推送不在本接口执行。"""
    start, end, week_range, error = week_window(weekStart)
    if error or start is None or end is None:
        return fail(1001, error or "weekStart 无效")
    tenant_id = tenant_of(actor)
    rows = _overview_rows(db, tenant_id, start, end)
    rules = _rules_map(db, {row.rule_id for row in rows if row.rule_id})
    buckets: dict[int, dict[str, Any]] = {}
    responded = 0
    delivered = 0
    now = utcnow()
    escalated = []
    for row in rows:
        buckets.setdefault(row.rule_id, _hit_bucket())
        _accumulate(buckets[row.rule_id], row)
        if row.response_status in (1, 2, 3):
            responded += 1
        if row.push_status == 1:
            delivered += 1
        current, _next = escalation_at(row, now)
        if current >= 2:
            escalated.append(
                {
                    "alertNo": row.alert_no,
                    "level": level_label(row.level),
                    "currentLevel": current,
                }
            )
    total = len(rows)
    top = []
    false_by_rule: list[tuple[str, int]] = []
    for rule_id, bucket in buckets.items():
        rule = rules.get(rule_id)
        code = rule.rule_code if rule else ""
        top.append({"ruleCode": code, "alertCount": bucket["alertCount"]})
        false_by_rule.append((code, bucket["falseAlarmCount"]))
    top.sort(key=lambda item: (-item["alertCount"], item["ruleCode"]))
    false_by_rule.sort(key=lambda item: (-item[1], item[0]))
    escalated.sort(key=lambda item: item["alertNo"])
    response_rate = rate_pct(responded, total)
    return ok(
        {
            "weekRange": week_range,
            "totalAlerts": total,
            "topRules": top[:5],
            "responseRate": response_rate,
            "deliveryRate": rate_pct(delivered, total),
            "escalatedAlerts": escalated,
            "suggestions": _suggestion_lines(total, response_rate, false_by_rule),
        }
    )


def _response_minutes(row: AlertRecord) -> float | None:
    if row.response_status not in (1, 2, 3):
        return None
    if row.occurred_at is None or row.updated_at is None:
        return None
    delta = (row.updated_at - row.occurred_at).total_seconds() / 60.0
    return delta if delta > 0 else 0.0


@router.get("/escalate/response-stats")
def escalate_response_stats(
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    rows = _overview_rows(db, tenant_of(actor), start, end)
    total = len(rows)
    responded = 0
    in_time = 0
    minutes: list[float] = []
    by_level = {1: {"total": 0, "responded": 0}, 2: {"total": 0, "responded": 0}, 3: {"total": 0, "responded": 0}}
    for row in rows:
        bucket = by_level.get(row.level)
        if bucket is not None:
            bucket["total"] += 1
        taken = _response_minutes(row)
        if taken is None and row.response_status not in (1, 2, 3):
            continue
        if row.response_status in (1, 2, 3):
            responded += 1
            if bucket is not None:
                bucket["responded"] += 1
            if taken is not None:
                minutes.append(taken)
                if taken <= LEVEL1_TIMEOUT_MINUTES:
                    in_time += 1
    avg = round(sum(minutes) / len(minutes), 2) if minutes else 0.0
    return ok(
        {
            "totalAlerts": total,
            "respondedInTime": in_time,
            "responseRate": rate_pct(responded, total),
            "avgResponseMinutes": avg,
            "target": RESPONSE_TARGET,
            "byLevel": [
                {
                    "level": level_label(level),
                    "responseRate": rate_pct(bucket["responded"], bucket["total"]),
                    "alertCount": bucket["total"],
                }
                for level, bucket in by_level.items()
            ],
        }
    )


@router.get("/stats/response-rate")
def stats_response_rate(
    dateRange: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    rows = _overview_rows(db, tenant_of(actor), start, end)
    grouped: dict[str, list[AlertRecord]] = {}
    for row in rows:
        if row.occurred_at is None:
            continue
        grouped.setdefault(row.occurred_at.strftime("%Y-%m-%d"), []).append(row)
    trend = []
    for day in sorted(grouped):
        day_rows = grouped[day]
        responded = sum(1 for row in day_rows if row.response_status in (1, 2, 3))
        trend.append(
            {
                "statDate": day,
                "responseRate": rate_pct(responded, len(day_rows)),
                "alertCount": len(day_rows),
            }
        )
    return ok(trend)

def _record_time(row: AlertRecord) -> datetime:
    return row.occurred_at or row.created_at or datetime.min


def _cluster_records(rows: list[AlertRecord]) -> list[list[AlertRecord]]:
    """同规则+同对象，自第一条起 30 分钟内归成一组。单条不构成合并。"""
    groups: dict[tuple, list[AlertRecord]] = {}
    for row in rows:
        key = (row.rule_id, row.source_ref_type or "", int(row.source_ref_id or 0))
        groups.setdefault(key, []).append(row)
    window = timedelta(minutes=MERGE_WINDOW_MINUTES)
    clusters: list[list[AlertRecord]] = []
    for bucket in groups.values():
        bucket.sort(key=lambda item: (_record_time(item), item.id))
        current: list[AlertRecord] = []
        master_at: datetime | None = None
        for row in bucket:
            at = _record_time(row)
            if not current or master_at is None or at > master_at + window:
                if current:
                    clusters.append(current)
                current = [row]
                master_at = at
            else:
                current.append(row)
        if current:
            clusters.append(current)
    return clusters


@router.get("/stats/rule-rank")
def stats_rule_rank(
    dateRange: str | None = None,
    topN: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """规则命中排行。合并节省数是窗口内被归并掉的重复条数，不触发推送。"""
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    if topN < 1 or topN > 50:
        return fail(1001, "topN 无效")
    tenant_id = tenant_of(actor)
    rows = _overview_rows(db, tenant_id, start, end)
    rules = _rules_for(db, rows)
    savings: dict[int, int] = {}
    for cluster in _cluster_records(rows):
        rule_id = cluster[0].rule_id
        savings[rule_id] = savings.get(rule_id, 0) + max(0, len(cluster) - 1)
    grouped: dict[int, list[AlertRecord]] = {}
    for row in rows:
        grouped.setdefault(row.rule_id, []).append(row)
    items = []
    for rule_id, group in grouped.items():
        rule = rules.get(rule_id)
        responded = sum(1 for row in group if row.response_status in (1, 2, 3))
        items.append(
            {
                "ruleCode": rule.rule_code if rule else "",
                "ruleName": rule.rule_name if rule else "",
                "alertCount": len(group),
                "mergedSavingsCount": savings.get(rule_id, 0),
                "responseRate": rate_pct(responded, len(group)),
            }
        )
    items.sort(key=lambda item: (-item["alertCount"], item["ruleCode"]))
    ranked = [{"rank": index, **item} for index, item in enumerate(items[:topN], start=1)]
    return ok(ranked)


@router.get("/stats/merge-logs")
def stats_merge_logs(
    ruleCode: str | None = None,
    dateRange: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """合并记录。只读归并，窗口固定 30 分钟。钉钉/短信不外发。"""
    start, end, error = parse_day_range(dateRange)
    if error:
        return fail(1001, error)
    tenant_id = tenant_of(actor)
    rows = _overview_rows(db, tenant_id, start, end)
    rules = _rules_for(db, rows)
    code = (ruleCode or "").strip()
    logs = []
    for cluster in _cluster_records(rows):
        if len(cluster) < 2:
            continue
        master = cluster[0]
        rule = rules.get(master.rule_id)
        if code and (rule is None or rule.rule_code != code):
            continue
        last = max(cluster, key=lambda item: (_record_time(item), item.id))
        logs.append(
            {
                "id": master.id,
                "ruleCode": rule.rule_code if rule else "",
                "masterAlertNo": master.alert_no,
                "mergedAlertNos": [item.alert_no for item in cluster[1:]],
                "mergedCount": len(cluster),
                "mergeWindowMinutes": MERGE_WINDOW_MINUTES,
                "masterOccurredAt": iso(master.occurred_at),
                "lastMergedAt": iso(last.occurred_at or last.updated_at),
            }
        )
    logs.sort(key=lambda item: (item["masterOccurredAt"], item["masterAlertNo"]), reverse=True)
    page_no, size = page_args(pageNo, pageSize)
    offset = (page_no - 1) * size
    return paged(logs[offset : offset + size], len(logs), page_no, size)


def run_check_impl(rule_id: int, db: Session, actor: User):
    tenant_id = tenant_of(actor)
    rule = db.get(AlertRule, rule_id)
    if rule is None or rule.deleted or rule.tenant_id != tenant_id:
        return fail(1500, "规则不存在")
    if not rule.enabled:
        return fail(1001, "规则未启用")
    now = utcnow()
    row = AlertRecord(
        alert_no=next_alert_no(db, tenant_id),
        rule_id=rule.id,
        source_ref_type="MANUAL",
        source_ref_id=0,
        level=rule.level,
        content=f"手动触发：{rule.rule_name}（{rule.threshold_expr or '条件扫描'}）",
        push_status=1,
        response_status=0,
        occurred_at=now,
        tenant_id=tenant_id,
    )
    db.add(row)
    rule.hit_count = (rule.hit_count or 0) + 1
    rule.updated_at = now
    db.flush()
    return ok(record_vo(row, rule))


@router.post("/check/run/{rule_id}")
def run_check(
    rule_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """规则试跑（手动触发一次检查，写入预警记录）。"""
    return run_check_impl(rule_id, db, actor)


@router.post("/rule/{rule_id}/trial")
def trial_rule(
    rule_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """试跑别名，与 POST /alert/check/run/{id} 等价。"""
    return run_check_impl(rule_id, db, actor)
