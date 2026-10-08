"""预警 ALERT-001 规则 · ALERT-002 检查记录（W9-4 首片）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import AlertDedupPolicy, AlertRecord, AlertRule, User

router = APIRouter(prefix="/alert", tags=["alert"])

BJ = timezone(timedelta(hours=8))
RESPONSE_LABELS = {0: "OPEN", 1: "ACK", 2: "HANDLED", 3: "FALSE_POSITIVE"}


class RuleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ruleCode: str
    ruleName: str
    metricType: str = "THRESHOLD"
    level: int = Field(default=2, ge=1, le=3)
    thresholdExpr: str = ""
    cronExpr: str = "0 */15 * * *"
    enabled: bool = False


class RespondBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: str


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
    return {
        "id": row.id,
        "alertNo": row.alert_no,
        "ruleId": row.rule_id,
        "ruleName": rule.rule_name if rule else "",
        "level": row.level,
        "content": row.content,
        "sourceRefType": row.source_ref_type or None,
        "sourceRefId": row.source_ref_id or None,
        "pushStatus": row.push_status,
        "responseStatus": RESPONSE_LABELS.get(row.response_status, "OPEN"),
        "occurredAt": iso(row.occurred_at),
    }


@router.get("/rule/list")
def rule_list(
    ruleName: str | None = None,
    enabled: bool | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AlertRule).where(AlertRule.deleted == 0, AlertRule.tenant_id == tenant_id)
    if ruleName:
        stmt = stmt.where(AlertRule.rule_name.contains(ruleName.strip()))
    if enabled is not None:
        stmt = stmt.where(AlertRule.enabled == (1 if enabled else 0))
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
            return fail(1165, "规则编码重复")
    if not code:
        code = next_rule_code(db, tenant_id)
    row = AlertRule(
        rule_code=code,
        rule_name=name or code,
        metric_type=body.metricType.strip() or "THRESHOLD",
        level=body.level,
        threshold_expr=body.thresholdExpr.strip(),
        cron_expr=body.cronExpr.strip() or "0 */15 * * *",
        enabled=1 if body.enabled else 0,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
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
    if responseStatus:
        rev = {v: k for k, v in RESPONSE_LABELS.items()}
        code = rev.get(responseStatus.upper())
        if code is None:
            return fail(1001, "responseStatus 无效")
        stmt = stmt.where(AlertRecord.response_status == code)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(AlertRecord.occurred_at.desc(), AlertRecord.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    rule_ids = {r.rule_id for r in rows if r.rule_id}
    rules = {}
    if rule_ids:
        for rule in db.scalars(select(AlertRule).where(AlertRule.id.in_(rule_ids))).all():
            rules[rule.id] = rule
    return paged([record_vo(r, rules.get(r.rule_id)) for r in rows], total, page_no, size)


@router.put("/check/{alert_no}/respond")
def respond_alert(
    alert_no: str,
    body: RespondBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    action = (body.action or "").upper()
    mapping = {"ACK": 1, "CONFIRM": 1, "HANDLE": 2, "HANDLED": 2, "FALSE_POSITIVE": 3, "MISREPORT": 3}
    if action not in mapping:
        return fail(1001, "action 无效")
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(AlertRecord).where(
            AlertRecord.deleted == 0,
            AlertRecord.tenant_id == tenant_id,
            AlertRecord.alert_no == alert_no,
        )
    )
    if row is None:
        return fail(1500, "预警不存在")
    row.response_status = mapping[action]
    row.updated_at = utcnow()
    db.flush()
    rule = db.get(AlertRule, row.rule_id) if row.rule_id else None
    return ok(record_vo(row, rule))


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
