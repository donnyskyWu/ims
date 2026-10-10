"""PERF-002 月度计算、核准发布、锁定更正与员工本人查看。

分档用 PerfGradeLevel（≥85 优秀 / 60~84 合格 / <60 待改进）。
单条考核的 PerfGrade（S~D）不写入本域。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import (
    FlowInstance,
    LiveReport,
    LiveSession,
    MeetDailyReport,
    PerfCalcDetail,
    PerfCalcResult,
    PerfMetric,
    PerfPeriod,
    PerfPositionBind,
    PerfRank,
    PerfRankAlert,
    ReportSubmission,
    TrainTask,
    TrainTaskRecord,
    User,
    WorkMessage,
)
from app.perf import iso, q2
from app.scope import dept_ids_of, enabled_roles

router = APIRouter(prefix="/perf", tags=["perf-calc"])

ENGINE_VERSION = "perf-calc-1"
# PRD M4：第 23 周后方可计算。2026 ISO 周 23 自 2026-06-01 起，故 2026-06 之前返回 1156。
OBSERVATION_OPEN = "2026-06"
LOCK_MSG = "绩效月数据已锁定，更正须运营总监审批并留痕（PER-C-R4）"
OBS_MSG = "观察期不足：第 23 周前无基线数据"
UNPUBLISHED_MSG = "结果未发布，员工不可见"
REASON_MSG = "补充原因必填"
RESULT_STATUSES = frozenset({"CALCULATING", "PENDING_MANUAL", "PENDING_APPROVE", "PUBLISHED"})
GRADE_EXCELLENT = Decimal("85")
GRADE_QUALIFIED = Decimal("60")
ZERO = Decimal("0")
HUNDRED = Decimal("100")


def role_tags(db: Session, actor: User) -> set[str]:
    tags: set[str] = set()
    for role in enabled_roles(db, actor):
        key = (role.role_key or "").strip().lower()
        name = role.role_name or ""
        if key:
            tags.add(key)
        if key == "sys:admin" or "系统管理员" in name:
            tags.update({"r1", "sys:admin"})
        if key == "r2" or key.endswith(":r2") or "人事" in name or "行政管理" in name:
            tags.add("r2")
        if key == "r3" or key.endswith(":r3") or "财务" in name:
            tags.add("r3")
        if key == "r4" or key.endswith(":r4") or "运营总监" in name:
            tags.add("r4")
        if key == "r9" or key.endswith(":r9") or "数据分析" in name:
            tags.add("r9")
        if key in {"dept_leader", "dept:leader"} or "部门负责人" in name:
            tags.add("dept_leader")
    return tags


class CalcScopeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userIds: list[int] | None = None
    deptIds: list[int] | None = None


class CalcRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    periodMonth: str
    scope: CalcScopeBody | None = None


class ManualBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricId: int
    manualValue: float
    supplementReason: str = ""


class ApproveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    approve: bool
    remark: str = ""
    excludeUserIds: list[int] = Field(default_factory=list)


class AlertHandleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    handleRemark: str = ""
    followUpPlan: str = ""


def period_ok(value: str) -> bool:
    text = (value or "").strip()
    if len(text) != 7 or text[4] != "-":
        return False
    year, month = text[:4], text[5:]
    return year.isdigit() and month.isdigit() and 1 <= int(month) <= 12


def month_bounds(period: str) -> tuple[datetime, datetime]:
    year = int(period[:4])
    month = int(period[5:7])
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def previous_period(period: str) -> str:
    year = int(period[:4])
    month = int(period[5:7])
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def grade_level_of(score: Decimal | float | None) -> str:
    value = Decimal(str(score or 0))
    if value >= GRADE_EXCELLENT:
        return "EXCELLENT"
    if value >= GRADE_QUALIFIED:
        return "QUALIFIED"
    return "IMPROVE"


def is_manager(tags: set[str]) -> bool:
    return bool(tags & {"r1", "r4", "sys:admin"})


def can_view_rank_board(tags: set[str]) -> bool:
    """全量排名：R1/R2/R4/R9。不含预警处置。"""
    return bool(tags & {"r1", "r2", "r4", "r9", "sys:admin"})


def can_approve(tags: set[str]) -> bool:
    """本地 sys:admin 代 R4 核准（与财务锁后审批同一口径）。"""
    return bool(tags & {"r4", "sys:admin"})


def can_calc(tags: set[str]) -> bool:
    return bool(tags & {"r1", "r4", "sys:admin"})


def can_view_coverage(tags: set[str]) -> bool:
    return bool(tags & {"r1", "r4", "sys:admin"})


def can_test_fetch(tags: set[str]) -> bool:
    return bool(tags & {"r1", "r3", "r4", "sys:admin"})


def can_view_alerts(tags: set[str]) -> bool:
    return bool(tags & {"r1", "r2", "r4", "sys:admin"})


def can_handle_alert(tags: set[str]) -> bool:
    """本地 sys:admin / R1 代 R4 登记（与核准同一口径）。"""
    return bool(tags & {"r1", "r2", "r4", "sys:admin"})


def can_view_coaching(tags: set[str]) -> bool:
    return bool(tags & {"r1", "r4", "sys:admin", "dept_leader"})


def lock_key(period: str) -> str:
    return f"PERF-LOCK-{period}"


def load_period(db: Session, tenant_id: int, period: str) -> PerfPeriod | None:
    return db.scalar(
        select(PerfPeriod).where(
            PerfPeriod.deleted == 0,
            PerfPeriod.tenant_id == tenant_id,
            PerfPeriod.period_month == period,
        )
    )


def period_locked(db: Session, tenant_id: int, period: str) -> bool:
    row = load_period(db, tenant_id, period)
    return row is not None and row.finance_status == "LOCKED"


def lock_approved(db: Session, tenant_id: int, period: str) -> bool:
    row = db.scalar(
        select(FlowInstance.id).where(
            FlowInstance.deleted == 0,
            FlowInstance.tenant_id == tenant_id,
            FlowInstance.business_key == lock_key(period),
            FlowInstance.instance_status == "APPROVED",
        )
    )
    return row is not None


def position_codes_of(db: Session, user: User) -> list[str]:
    codes: list[str] = []
    for role in enabled_roles(db, user):
        position = (role.dingtalk_position or "").strip()
        if position:
            codes.append(position)
        key = (role.role_key or "").strip()
        if key in {"R2", "R4", "R5", "R6"}:
            codes.append(key)
    seen: list[str] = []
    for code in codes:
        if code not in seen:
            seen.append(code)
    return seen


def dept_of(db: Session, user: User) -> tuple[int, str]:
    ids = dept_ids_of(db, user)
    dept_id = ids[0] if ids else 0
    name = db.scalar(
        select(MeetDailyReport.dept_name)
        .where(
            MeetDailyReport.deleted == 0,
            MeetDailyReport.user_id == user.id,
            MeetDailyReport.dept_name != "",
        )
        .order_by(MeetDailyReport.id.desc())
        .limit(1)
    )
    if name:
        return dept_id, str(name)
    if dept_id:
        return dept_id, f"部门#{dept_id}"
    return 0, "未分配"


def tenure_ratio(user: User, period: str) -> Decimal:
    """入职当月按在职天数折算。无离职日期字段时不折离职。"""
    start, end = month_bounds(period)
    hired = user.created_at
    if hired is None:
        return Decimal(1)
    hired_date = hired.date()
    start_date = start.date()
    end_date = end.date()
    days = (end_date - start_date).days
    if days <= 0 or hired_date <= start_date:
        return Decimal(1)
    if hired_date >= end_date:
        return ZERO
    worked = (end_date - hired_date).days
    return (Decimal(worked) / Decimal(days)).quantize(Decimal("0.0001"))


def linear_score(value: float, linear: dict) -> Decimal:
    lo_m = Decimal(str(linear.get("minMetric", 0)))
    hi_m = Decimal(str(linear.get("maxMetric", 100)))
    lo_s = Decimal(str(linear.get("minScore", 0)))
    hi_s = Decimal(str(linear.get("maxScore", 100)))
    raw = Decimal(str(value))
    if hi_m == lo_m:
        return q2(hi_s)
    ratio = (raw - lo_m) / (hi_m - lo_m)
    if ratio < 0:
        ratio = ZERO
    if ratio > 1:
        ratio = Decimal(1)
    return q2(lo_s + ratio * (hi_s - lo_s))


def segment_score(value: float, segments: list) -> Decimal:
    raw = Decimal(str(value))
    for seg in segments or []:
        lo = Decimal(str(seg.get("minValue", 0)))
        hi_raw = seg.get("maxValue")
        hi = None if hi_raw is None else Decimal(str(hi_raw))
        if raw < lo:
            continue
        if hi is not None and raw >= hi:
            continue
        return q2(Decimal(str(seg.get("score", 0))))
    return ZERO


def score_of(rule: dict, value: float | None) -> Decimal:
    if value is None:
        return ZERO
    kind = str((rule or {}).get("ruleType") or "").upper()
    if kind == "LINEAR":
        return linear_score(value, (rule or {}).get("linear") or {})
    return segment_score(value, (rule or {}).get("segments") or [])


def fetch_train_finish(db: Session, tenant_id: int, user_id: int, period: str) -> float | None:
    start, end = month_bounds(period)
    rows = db.execute(
        select(TrainTaskRecord, TrainTask)
        .join(TrainTask, TrainTask.id == TrainTaskRecord.task_id)
        .where(
            TrainTaskRecord.deleted == 0,
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTaskRecord.user_id == user_id,
            TrainTask.deleted == 0,
            TrainTask.created_at >= start,
            TrainTask.created_at < end,
        )
    ).all()
    if not rows:
        return None
    finished = sum(1 for record, _task in rows if int(record.confirm_status or 0) == 1)
    return round(finished * 100.0 / len(rows), 2)


def fetch_meet_on_time(db: Session, tenant_id: int, user_id: int, period: str) -> float | None:
    rows = db.scalars(
        select(MeetDailyReport).where(
            MeetDailyReport.deleted == 0,
            MeetDailyReport.tenant_id == tenant_id,
            MeetDailyReport.user_id == user_id,
            MeetDailyReport.report_date.like(f"{period}%"),
            MeetDailyReport.submit_status.in_(("SUBMITTED", "READ")),
        )
    ).all()
    if not rows:
        return None
    on_time = sum(1 for row in rows if int(row.is_on_time or 0) == 1)
    return round(on_time * 100.0 / len(rows), 2)


def fetch_report_on_time(db: Session, tenant_id: int, user_id: int, period: str) -> float | None:
    start, end = month_bounds(period)
    rows = db.scalars(
        select(ReportSubmission).where(
            ReportSubmission.deleted == 0,
            ReportSubmission.tenant_id == tenant_id,
            ReportSubmission.submitter_user_id == user_id,
            ReportSubmission.submit_status != "DRAFT",
        )
    ).all()
    matched = []
    for row in rows:
        period_text = row.period or ""
        submitted = row.submitted_at
        in_period = period_text == period or period_text.startswith(period)
        in_time = submitted is not None and start <= submitted.replace(tzinfo=None) < end
        if in_period or in_time:
            matched.append(row)
    if not matched:
        return None
    on_time = sum(1 for row in matched if int(row.is_on_time or 0) == 1)
    return round(on_time * 100.0 / len(matched), 2)


def fetch_live(db: Session, tenant_id: int, user_id: int, period: str, expression: str) -> float | None:
    sessions = db.scalars(
        select(LiveSession).where(
            LiveSession.deleted == 0,
            LiveSession.tenant_id == tenant_id,
            LiveSession.responsible_user_id == user_id,
        )
    ).all()
    codes = []
    for session in sessions:
        stamp = session.actual_start or session.plan_start_time or ""
        if stamp.startswith(period):
            codes.append(session.session_code)
    if not codes:
        return None
    reports = db.scalars(
        select(LiveReport).where(
            LiveReport.deleted == 0,
            LiveReport.tenant_id == tenant_id,
            LiveReport.session_code.in_(codes),
            LiveReport.entry_status == "CONFIRMED",
        )
    ).all()
    if expression == "session_count":
        return float(len(reports))
    if expression == "gmv":
        if not reports:
            return None
        return round(sum(float(row.gmv or 0) for row in reports), 2)
    return None


def fetch_auto(db: Session, tenant_id: int, user_id: int, period: str, module: str, expression: str) -> float | None:
    if module == "TRAIN" and expression == "finish_rate":
        return fetch_train_finish(db, tenant_id, user_id, period)
    if module == "MEET" and expression == "on_time_rate":
        return fetch_meet_on_time(db, tenant_id, user_id, period)
    if module == "REPORT" and expression == "on_time_rate":
        return fetch_report_on_time(db, tenant_id, user_id, period)
    if module == "LIVE" and expression in {"gmv", "session_count"}:
        return fetch_live(db, tenant_id, user_id, period, expression)
    if module == "FIN":
        return None
    return None


def bound_metrics(db: Session, tenant_id: int, position: str) -> list[tuple[PerfMetric, Decimal]]:
    binds = db.scalars(
        select(PerfPositionBind).where(
            PerfPositionBind.deleted == 0,
            PerfPositionBind.tenant_id == tenant_id,
            PerfPositionBind.position_code == position,
        )
    ).all()
    chosen: list[tuple[PerfMetric, Decimal]] = []
    for bind in binds:
        metric = db.get(PerfMetric, bind.metric_id)
        if metric is None or metric.deleted or metric.tenant_id != tenant_id:
            continue
        if metric.status != "ENABLED":
            continue
        if metric.metric_code == "COMPETE_SUBMIT_RATE":
            continue
        weight = metric.weight if bind.weight_override is None else bind.weight_override
        chosen.append((metric, q2(weight or 0)))
    return chosen


def positions_with_binds(db: Session, tenant_id: int) -> set[str]:
    rows = db.scalars(
        select(PerfPositionBind.position_code).where(
            PerfPositionBind.deleted == 0,
            PerfPositionBind.tenant_id == tenant_id,
        )
    ).all()
    return {str(row) for row in rows if row}


def people_for_period(
    db: Session,
    tenant_id: int,
    period: str,
    scope: CalcScopeBody | None,
) -> list[tuple[User, str, int, str, Decimal]]:
    positions = positions_with_binds(db, tenant_id)
    users = db.scalars(
        select(User).where(User.deleted == 0, User.tenant_id == tenant_id, User.status == "ENABLED")
    ).all()
    user_ids = set(scope.userIds) if scope and scope.userIds else None
    dept_ids = set(scope.deptIds) if scope and scope.deptIds else None
    found: list[tuple[User, str, int, str, Decimal]] = []
    for user in users:
        if user_ids is not None and user.id not in user_ids:
            continue
        codes = position_codes_of(db, user)
        position = next((code for code in codes if code in positions), None)
        if position is None:
            continue
        dept_id, dept_name = dept_of(db, user)
        if dept_ids is not None and dept_id not in dept_ids:
            continue
        ratio = tenure_ratio(user, period)
        if ratio <= 0:
            continue
        found.append((user, position, dept_id, dept_name, ratio))
    return found


def next_version(db: Session, tenant_id: int, period: str, user_id: int) -> int:
    current = db.scalar(
        select(func.max(PerfCalcResult.version)).where(
            PerfCalcResult.deleted == 0,
            PerfCalcResult.tenant_id == tenant_id,
            PerfCalcResult.period_month == period,
            PerfCalcResult.user_id == user_id,
        )
    )
    return int(current or 0) + 1


def retire_current(db: Session, tenant_id: int, period: str, user_id: int) -> None:
    rows = db.scalars(
        select(PerfCalcResult).where(
            PerfCalcResult.deleted == 0,
            PerfCalcResult.tenant_id == tenant_id,
            PerfCalcResult.period_month == period,
            PerfCalcResult.user_id == user_id,
            PerfCalcResult.is_current == 1,
        )
    ).all()
    now = utcnow()
    for row in rows:
        row.is_current = 0
        row.updated_at = now


def current_results(db: Session, tenant_id: int, period: str) -> list[PerfCalcResult]:
    return list(
        db.scalars(
            select(PerfCalcResult).where(
                PerfCalcResult.deleted == 0,
                PerfCalcResult.tenant_id == tenant_id,
                PerfCalcResult.period_month == period,
                PerfCalcResult.is_current == 1,
            )
        ).all()
    )


def score_cents(value: Decimal | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def assign_ranks(rows: list[PerfCalcResult]) -> None:
    """部门内按得分降序。同分并列，下一名跳号。"""
    grouped: dict[int, list[PerfCalcResult]] = {}
    for row in rows:
        grouped.setdefault(int(row.dept_id or 0), []).append(row)
    for group in grouped.values():
        group.sort(key=lambda item: (-score_cents(item.total_score), int(item.user_id or 0)))
        last_score: Decimal | None = None
        last_rank = 0
        for index, row in enumerate(group, start=1):
            score = score_cents(row.total_score)
            if last_score is not None and score == last_score:
                row.rank_in_dept = last_rank
            else:
                row.rank_in_dept = index
                last_rank = index
            last_score = score


def build_details(
    db: Session,
    tenant_id: int,
    user_id: int,
    period: str,
    metrics: list[tuple[PerfMetric, Decimal]],
) -> tuple[list[dict], Decimal, bool]:
    total = ZERO
    missing = False
    details: list[dict] = []
    for metric, weight in metrics:
        source = (metric.data_source or "MANUAL").upper()
        module = ""
        value: float | None = None
        status = "MISSING"
        if source == "MANUAL":
            status = "MISSING"
        elif source == "EXAM":
            module = "EXAM"
            from app.exam_paper import exam_metric_value

            fetched = exam_metric_value(db, tenant_id, user_id, period)
            if fetched is None:
                status = "MISSING"
            else:
                value = fetched
                status = "EXAM"
        elif source == "AUTO":
            config = metric.source_config or {}
            module = str(config.get("module") or "")
            expression = str(config.get("metricExpression") or "")
            fetched = fetch_auto(db, tenant_id, user_id, period, module, expression)
            if fetched is None:
                status = "MISSING"
            else:
                value = fetched
                status = "AUTO"
        else:
            status = "MISSING"
        if status == "MISSING":
            missing = True
        metric_score = score_of(metric.score_rule or {}, value)
        total += q2(metric_score * weight / HUNDRED)
        details.append(
            {
                "metric_id": metric.id,
                "metric_code": metric.metric_code,
                "metric_name": metric.metric_name,
                "source_module": module,
                "metric_value": None if value is None else q2(value),
                "metric_score": metric_score,
                "weight": weight,
                "data_status": status,
                "version": int(metric.version or 1),
            }
        )
    return details, q2(total), missing


def next_task_id(db: Session, tenant_id: int, period: str) -> str:
    prefix = f"PC{period.replace('-', '')}"
    count = db.scalar(
        select(func.count())
        .select_from(PerfCalcResult)
        .where(
            PerfCalcResult.tenant_id == tenant_id,
            PerfCalcResult.calc_task_id.like(f"{prefix}%"),
        )
    )
    return f"{prefix}{int(count or 0) + 1:03d}"


def mask_value(value, module: str, masked: bool):
    if masked and module == "FIN" and value is not None:
        return "***"
    if value is None:
        return None
    return float(q2(value))


def detail_rows(db: Session, result_id: int) -> list[PerfCalcDetail]:
    return list(
        db.scalars(
            select(PerfCalcDetail).where(
                PerfCalcDetail.deleted == 0,
                PerfCalcDetail.result_id == result_id,
            )
        ).all()
    )


def history_of(db: Session, row: PerfCalcResult) -> list[dict]:
    rows = db.scalars(
        select(PerfCalcResult)
        .where(
            PerfCalcResult.deleted == 0,
            PerfCalcResult.tenant_id == row.tenant_id,
            PerfCalcResult.period_month == row.period_month,
            PerfCalcResult.user_id == row.user_id,
        )
        .order_by(PerfCalcResult.version.asc())
    ).all()
    items = []
    for item in rows:
        snap = item.calc_snapshot or {}
        items.append(
            {
                "version": int(item.version or 1),
                "resultStatus": item.result_status,
                "totalScore": None if item.total_score is None else float(item.total_score),
                "fetchTime": snap.get("fetchTime") or "",
                "isCurrent": bool(item.is_current),
            }
        )
    return items


def result_vo(db: Session, row: PerfCalcResult, masked: bool, with_details: bool = True) -> dict:
    details = detail_rows(db, row.id) if with_details else []
    missing = sum(1 for item in details if item.data_status == "MISSING")
    score = None if row.total_score is None else float(row.total_score)
    data = {
        "id": row.id,
        "periodMonth": row.period_month,
        "userId": row.user_id,
        "userName": row.user_name,
        "positionCode": row.position_code,
        "deptId": row.dept_id,
        "deptName": row.dept_name,
        "totalScore": score,
        "rankInDept": row.rank_in_dept,
        "gradeLevel": grade_level_of(row.total_score),
        "resultStatus": row.result_status,
        "missingCount": missing,
        "calcSnapshot": row.calc_snapshot or {},
        "version": int(row.version or 1),
        "versionHistory": history_of(db, row),
        "approveRemark": row.approve_remark or "",
    }
    if row.approved_by:
        data["approvedBy"] = row.approved_by
        data["approvedAt"] = iso(row.approved_at)
    if with_details:
        data["details"] = [
            {
                "metricId": item.metric_id,
                "metricCode": item.metric_code,
                "metricName": item.metric_name,
                "metricValue": mask_value(item.metric_value, item.source_module, masked),
                "metricScore": float(item.metric_score or 0),
                "weight": float(item.weight or 0),
                "dataStatus": item.data_status,
                "contribution": float(q2(Decimal(str(item.metric_score or 0)) * Decimal(str(item.weight or 0)) / HUNDRED)),
            }
            for item in details
        ]
    return data


def find_current(db: Session, tenant_id: int, result_id: int) -> PerfCalcResult | None:
    row = db.get(PerfCalcResult, result_id)
    if row is None or row.deleted or row.tenant_id != tenant_id or not row.is_current:
        return None
    return row


def recompute_total(db: Session, row: PerfCalcResult) -> None:
    details = detail_rows(db, row.id)
    total = ZERO
    for item in details:
        total += q2(Decimal(str(item.metric_score or 0)) * Decimal(str(item.weight or 0)) / HUNDRED)
    ratio = Decimal(str((row.calc_snapshot or {}).get("tenureRatio") or 1))
    row.total_score = q2(total * ratio)
    missing = any(item.data_status == "MISSING" for item in details)
    if row.result_status != "PUBLISHED":
        row.result_status = "PENDING_MANUAL" if missing else "PENDING_APPROVE"
    row.updated_at = utcnow()


def notify_published(db: Session, tenant_id: int, row: PerfCalcResult) -> None:
    score = float(row.total_score or 0)
    content = f"{row.period_month} 绩效已发布，综合得分 {score:.2f}"
    if grade_level_of(row.total_score) == "IMPROVE":
        content += "，低于 60 分，分档为待改进"
    db.add(
        WorkMessage(
            user_id=row.user_id,
            title="绩效已发布",
            content=content,
            channel="IN_APP",
            source_module="PERF",
            ref_type="perf_result",
            ref_id=row.id,
            tenant_id=tenant_id,
        )
    )


def consecutive_improve(db: Session, tenant_id: int, user_id: int, period: str, grade: str) -> int:
    if grade != "IMPROVE":
        return 0
    count = 1
    cursor = previous_period(period)
    for _ in range(24):
        row = db.scalar(
            select(PerfRank).where(
                PerfRank.deleted == 0,
                PerfRank.tenant_id == tenant_id,
                PerfRank.period_month == cursor,
                PerfRank.user_id == user_id,
                PerfRank.is_current == 1,
            )
        )
        if row is None or row.grade_level != "IMPROVE":
            break
        count += 1
        cursor = previous_period(cursor)
    return count


PUSH_TARGETS = ["SELF", "SUPERIOR", "HR"]


def sync_rank_alerts(db: Session, tenant_id: int, period: str | None = None) -> None:
    """把当前待改进排名落成预警。已处置的记录只更新分数，不改回待处置。"""
    stmt = select(PerfRank).where(
        PerfRank.deleted == 0,
        PerfRank.tenant_id == tenant_id,
        PerfRank.is_current == 1,
        PerfRank.alert_status == "ALERTED",
    )
    if period:
        stmt = stmt.where(PerfRank.period_month == period)
    now = utcnow()
    for rank in db.scalars(stmt).all():
        alert = db.scalar(
            select(PerfRankAlert).where(
                PerfRankAlert.deleted == 0,
                PerfRankAlert.tenant_id == tenant_id,
                PerfRankAlert.period_month == rank.period_month,
                PerfRankAlert.user_id == rank.user_id,
            )
        )
        if alert is None:
            alert = PerfRankAlert(
                period_month=rank.period_month,
                user_id=rank.user_id,
                user_name=rank.user_name,
                dept_id=rank.dept_id,
                dept_name=rank.dept_name,
                total_score=rank.total_score or ZERO,
                alerted_at=now,
                push_targets=list(PUSH_TARGETS),
                handle_status="PENDING",
                tenant_id=tenant_id,
            )
            db.add(alert)
            db.flush()
            score = float(rank.total_score or 0)
            db.add(
                WorkMessage(
                    user_id=rank.user_id,
                    title="绩效预警",
                    content=(
                        f"{rank.period_month} 综合得分 {score:.2f}，低于 60，"
                        "已通知本人、直属上级与 HR"
                    ),
                    channel="IN_APP",
                    source_module="PERF",
                    ref_type="perf_rank_alert",
                    ref_id=alert.id,
                    tenant_id=tenant_id,
                )
            )
            continue
        alert.user_name = rank.user_name
        alert.dept_id = rank.dept_id
        alert.dept_name = rank.dept_name
        alert.total_score = rank.total_score or ZERO
        alert.updated_at = now


def write_ranks(db: Session, tenant_id: int, period: str) -> None:
    published = [
        row
        for row in current_results(db, tenant_id, period)
        if row.result_status == "PUBLISHED"
    ]
    now = utcnow()
    previous = db.scalars(
        select(PerfRank).where(
            PerfRank.deleted == 0,
            PerfRank.tenant_id == tenant_id,
            PerfRank.period_month == period,
            PerfRank.is_current == 1,
        )
    ).all()
    for row in previous:
        row.is_current = 0
        row.updated_at = now
    for row in published:
        grade = grade_level_of(row.total_score)
        db.add(
            PerfRank(
                period_month=period,
                dept_id=row.dept_id,
                dept_name=row.dept_name,
                user_id=row.user_id,
                user_name=row.user_name,
                total_score=row.total_score or ZERO,
                rank_no=int(row.rank_in_dept or 0),
                grade_level=grade,
                alert_status="ALERTED" if grade == "IMPROVE" else "NONE",
                consecutive_months=consecutive_improve(db, tenant_id, row.user_id, period, grade),
                version=int(row.version or 1),
                is_current=1,
                tenant_id=tenant_id,
            )
        )
    db.flush()
    sync_rank_alerts(db, tenant_id, period)


def rank_vo(row: PerfRank) -> dict:
    return {
        "id": row.id,
        "periodMonth": row.period_month,
        "deptId": row.dept_id,
        "deptName": row.dept_name,
        "userId": row.user_id,
        "userName": row.user_name,
        "totalScore": float(row.total_score or 0),
        "rankNo": int(row.rank_no or 0),
        "gradeLevel": row.grade_level,
        "alertStatus": row.alert_status,
        "consecutiveMonths": int(row.consecutive_months or 0),
    }


def distribution(rows: list[PerfRank]) -> dict:
    return {
        "excellent": sum(1 for row in rows if row.grade_level == "EXCELLENT"),
        "qualified": sum(1 for row in rows if row.grade_level == "QUALIFIED"),
        "improve": sum(1 for row in rows if row.grade_level == "IMPROVE"),
    }


PIP_STUB = "低于 60 分列入末位预警，将触发绩效改进计划（PIP），并通知本人、直属上级与 HR。本地只记说明，不外发钉钉。"
GRADE_LINE = "优秀 ≥85 · 合格 60~84 · 待改进 <60"
MEDALS = {1: "GOLD", 2: "SILVER", 3: "BRONZE"}


def average_score(rows: list[PerfRank]) -> float | None:
    if not rows:
        return None
    total = sum((score_cents(row.total_score) for row in rows), Decimal("0"))
    return float((total / Decimal(len(rows))).quantize(Decimal("0.01")))


def board_item(row: PerfRank, board_rank: int) -> dict:
    data = rank_vo(row)
    data["boardRank"] = board_rank
    data["medal"] = MEDALS.get(board_rank, "")
    data["belowLine"] = score_cents(row.total_score) < GRADE_QUALIFIED
    return data


def competition_board(rows: list[PerfRank]) -> list[tuple[int, PerfRank]]:
    ordered = sorted(rows, key=lambda item: (-score_cents(item.total_score), int(item.user_id or 0)))
    last_score: Decimal | None = None
    last_rank = 0
    ranked: list[tuple[int, PerfRank]] = []
    for index, row in enumerate(ordered, start=1):
        score = score_cents(row.total_score)
        if last_score is not None and score == last_score:
            rank = last_rank
        else:
            rank = index
            last_rank = index
        last_score = score
        ranked.append((rank, row))
    return ranked


def dept_options(rows: list[PerfRank]) -> list[dict]:
    seen: set[int] = set()
    options: list[dict] = []
    for row in rows:
        dept_id = int(row.dept_id or 0)
        if dept_id in seen:
            continue
        seen.add(dept_id)
        options.append({"deptId": dept_id, "deptName": row.dept_name or "未分配"})
    return options


def dept_averages(rows: list[PerfRank]) -> list[dict]:
    grouped: dict[int, list[PerfRank]] = {}
    for row in rows:
        grouped.setdefault(int(row.dept_id or 0), []).append(row)
    items = []
    for dept_id, group in grouped.items():
        items.append(
            {
                "deptId": dept_id,
                "deptName": group[0].dept_name or "未分配",
                "average": average_score(group),
                "headcount": len(group),
            }
        )
    items.sort(key=lambda item: int(item["deptId"]))
    return items


def build_rank_board(visible: list[PerfRank], period_rows: list[PerfRank]) -> dict:
    """考核结果页排名区：红榜前三、末位预警桩、部门均分。不创建预警单、不外发。"""
    depts = dept_options(period_rows)
    empty = {
        "top3": [],
        "tail": [],
        "deptAverage": None,
        "deptAverages": [],
        "depts": depts,
        "pipStub": PIP_STUB,
        "gradeLine": GRADE_LINE,
    }
    if not period_rows:
        return {**empty, "emptyReason": "UNPUBLISHED", "depts": []}
    if not visible:
        return {**empty, "emptyReason": "DEPT_EMPTY"}
    ranked = competition_board(visible)
    top3 = [board_item(row, rank) for rank, row in ranked if rank <= 3]
    tail_rows = sorted(
        [row for row in visible if row.grade_level == "IMPROVE" or row.alert_status == "ALERTED"],
        key=lambda row: (score_cents(row.total_score), int(row.user_id or 0)),
    )
    tail = [board_item(row, 0) for row in tail_rows[:3]]
    return {
        "emptyReason": "",
        "top3": top3,
        "tail": tail,
        "deptAverage": average_score(visible),
        "deptAverages": dept_averages(visible),
        "depts": depts,
        "pipStub": PIP_STUB,
        "gradeLine": GRADE_LINE,
    }


@router.post("/calc/run")
def calc_run(
    body: CalcRunBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tags = role_tags(db, actor)
    if not can_calc(tags):
        return fail(1008, "无数据权限")
    period = body.periodMonth.strip()
    if not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    if period < OBSERVATION_OPEN:
        return fail(1156, OBS_MSG)
    tenant_id = tenant_of(actor)
    if period_locked(db, tenant_id, period) and not lock_approved(db, tenant_id, period):
        return fail(1155, LOCK_MSG)
    if not positions_with_binds(db, tenant_id):
        return ok({"calcTaskId": "", "targetUserCount": 0, "message": "没有可计算的岗位指标集"})
    people = people_for_period(db, tenant_id, period, body.scope)
    task_id = next_task_id(db, tenant_id, period)
    now = utcnow()
    for user, position, dept_id, dept_name, ratio in people:
        metrics = bound_metrics(db, tenant_id, position)
        details, raw_total, missing = build_details(db, tenant_id, user.id, period, metrics)
        total = q2(raw_total * ratio)
        versions = {item["metric_code"]: item["version"] for item in details}
        retire_current(db, tenant_id, period, user.id)
        result = PerfCalcResult(
            period_month=period,
            user_id=user.id,
            user_name=user.nickname or user.username,
            position_code=position,
            dept_id=dept_id,
            dept_name=dept_name,
            total_score=total,
            result_status="PENDING_MANUAL" if missing else "PENDING_APPROVE",
            calc_snapshot={
                "metricVersions": versions,
                "fetchTime": iso(now),
                "engineVersion": ENGINE_VERSION,
                "tenureRatio": float(ratio),
            },
            calc_task_id=task_id,
            version=next_version(db, tenant_id, period, user.id),
            is_current=1,
            created_by=actor.id,
            tenant_id=tenant_id,
        )
        db.add(result)
        db.flush()
        for item in details:
            db.add(
                PerfCalcDetail(
                    result_id=result.id,
                    metric_id=item["metric_id"],
                    metric_code=item["metric_code"],
                    metric_name=item["metric_name"],
                    source_module=item["source_module"],
                    metric_value=item["metric_value"],
                    metric_score=item["metric_score"],
                    weight=item["weight"],
                    data_status=item["data_status"],
                    tenant_id=tenant_id,
                )
            )
    assign_ranks(current_results(db, tenant_id, period))
    db.flush()
    count = len(people)
    return ok({"calcTaskId": task_id, "targetUserCount": count, "message": f"已创建计算任务（{count} 人）"})


@router.get("/calc/{period}/mine")
def calc_mine(
    period: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(PerfCalcResult).where(
            PerfCalcResult.deleted == 0,
            PerfCalcResult.tenant_id == tenant_id,
            PerfCalcResult.period_month == period,
            PerfCalcResult.user_id == actor.id,
            PerfCalcResult.is_current == 1,
        )
    )
    if row is None:
        return ok(None)
    if row.result_status != "PUBLISHED":
        return fail(1157, UNPUBLISHED_MSG)
    return ok(result_vo(db, row, masked=False))


@router.get("/calc/{period}")
def calc_list(
    period: str,
    pageNo: int = 1,
    pageSize: int = 10,
    deptId: int | None = None,
    resultStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    tags = role_tags(db, actor)
    tenant_id = tenant_of(actor)
    stmt = select(PerfCalcResult).where(
        PerfCalcResult.deleted == 0,
        PerfCalcResult.tenant_id == tenant_id,
        PerfCalcResult.period_month == period,
        PerfCalcResult.is_current == 1,
    )
    manager = is_manager(tags)
    masked = (not manager) and ("r9" in tags)
    if not manager and "r9" not in tags:
        stmt = stmt.where(PerfCalcResult.user_id == actor.id, PerfCalcResult.result_status == "PUBLISHED")
    if deptId:
        stmt = stmt.where(PerfCalcResult.dept_id == deptId)
    if resultStatus.strip():
        status = resultStatus.strip().upper()
        if status not in RESULT_STATUSES:
            return fail(1001, "结果状态无效")
        stmt = stmt.where(PerfCalcResult.result_status == status)
    page_no, size = page_args(pageNo, pageSize)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(stmt.order_by(PerfCalcResult.id.asc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([result_vo(db, row, masked) for row in rows], total, page_no, size)


@router.put("/calc/detail/{result_id}/manual")
def calc_manual(
    result_id: int,
    body: ManualBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tags = role_tags(db, actor)
    if not can_calc(tags):
        return fail(1008, "无数据权限")
    if not (body.supplementReason or "").strip():
        return fail(1158, REASON_MSG)
    tenant_id = tenant_of(actor)
    row = find_current(db, tenant_id, result_id)
    if row is None:
        return fail(1500, "绩效结果不存在")
    if row.result_status == "PUBLISHED" or period_locked(db, tenant_id, row.period_month):
        return fail(1155, LOCK_MSG)
    detail = db.scalar(
        select(PerfCalcDetail).where(
            PerfCalcDetail.deleted == 0,
            PerfCalcDetail.result_id == row.id,
            PerfCalcDetail.metric_id == body.metricId,
        )
    )
    if detail is None:
        return fail(1001, "指标明细不存在")
    if detail.data_status != "MISSING":
        return fail(1001, "该指标不是待人工缺项")
    metric = db.get(PerfMetric, body.metricId)
    rule = metric.score_rule if metric is not None else {}
    detail.metric_value = q2(body.manualValue)
    detail.metric_score = score_of(rule or {}, body.manualValue)
    detail.data_status = "MANUAL"
    detail.supplement_reason = body.supplementReason.strip()
    detail.updated_at = utcnow()
    recompute_total(db, row)
    assign_ranks(current_results(db, tenant_id, row.period_month))
    db.flush()
    return ok(None)


@router.put("/calc/{period}/approve")
def calc_approve(
    period: str,
    body: ApproveBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    tags = role_tags(db, actor)
    if not can_approve(tags):
        return fail(1008, "无数据权限")
    tenant_id = tenant_of(actor)
    rows = current_results(db, tenant_id, period)
    if not rows:
        return fail(1001, "该周期没有可核准的计算结果")
    now = utcnow()
    if not body.approve:
        if not (body.remark or "").strip():
            return fail(1001, "驳回须填写审批意见")
        for row in rows:
            if row.result_status != "PUBLISHED":
                row.result_status = "CALCULATING"
                row.approve_remark = body.remark.strip()
                row.updated_at = now
        db.flush()
        return ok({"publishedCount": 0, "pendingManualCount": 0, "publishedAt": iso(now)})
    excluded = set(body.excludeUserIds or [])
    published = 0
    for row in rows:
        if row.user_id in excluded or row.result_status == "PUBLISHED":
            continue
        if row.result_status not in {"PENDING_APPROVE", "PENDING_MANUAL"}:
            continue
        row.result_status = "PUBLISHED"
        row.approved_by = actor.id
        row.approved_at = now
        row.approve_remark = (body.remark or "").strip()
        row.updated_at = now
        published += 1
        notify_published(db, tenant_id, row)
    assign_ranks(current_results(db, tenant_id, period))
    if published:
        period_row = load_period(db, tenant_id, period)
        if period_row is None:
            period_row = PerfPeriod(period_month=period, tenant_id=tenant_id)
            db.add(period_row)
        period_row.finance_status = "LOCKED"
        period_row.locked_by = actor.id
        period_row.locked_at = now
        period_row.updated_at = now
        write_ranks(db, tenant_id, period)
    db.flush()
    pending = sum(1 for row in current_results(db, tenant_id, period) if row.result_status == "PENDING_MANUAL")
    return ok({"publishedCount": published, "pendingManualCount": pending, "publishedAt": iso(now)})


@router.get("/rank/period/{period}")
def rank_period(
    period: str,
    deptId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    if not can_view_rank_board(role_tags(db, actor)):
        return fail(403, "仅管理者可查看全量排名")
    tenant_id = tenant_of(actor)
    period_rows = list(
        db.scalars(
            select(PerfRank)
            .where(
                PerfRank.deleted == 0,
                PerfRank.tenant_id == tenant_id,
                PerfRank.period_month == period,
                PerfRank.is_current == 1,
            )
            .order_by(PerfRank.dept_id.asc(), PerfRank.rank_no.asc(), PerfRank.user_id.asc())
        ).all()
    )
    visible = period_rows
    if deptId:
        visible = [row for row in period_rows if int(row.dept_id or 0) == int(deptId)]
    page_no, size = page_args(pageNo, pageSize)
    start = (page_no - 1) * size
    page = visible[start : start + size]
    return ok(
        {
            "list": [rank_vo(row) for row in page],
            "total": len(visible),
            "pageNo": page_no,
            "pageSize": size,
            "rankBoard": build_rank_board(visible, period_rows),
        }
    )


@router.get("/rank/mine")
def rank_mine(
    periodMonth: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = select(PerfRank).where(
        PerfRank.deleted == 0,
        PerfRank.tenant_id == tenant_id,
        PerfRank.user_id == actor.id,
        PerfRank.is_current == 1,
    )
    period = periodMonth.strip()
    if period:
        if not period_ok(period):
            return fail(1001, "绩效月格式须为 yyyy-MM")
        stmt = stmt.where(PerfRank.period_month == period)
    row = db.scalar(stmt.order_by(PerfRank.period_month.desc()))
    if row is None:
        return fail(1157, UNPUBLISHED_MSG)
    peers = db.scalars(
        select(PerfRank).where(
            PerfRank.deleted == 0,
            PerfRank.tenant_id == tenant_id,
            PerfRank.period_month == row.period_month,
            PerfRank.dept_id == row.dept_id,
            PerfRank.is_current == 1,
        )
    ).all()
    data = rank_vo(row)
    data["deptTotalCount"] = len(peers)
    data["scoreDistribution"] = distribution(list(peers))
    return ok(data)


def alert_vo(row: PerfRankAlert) -> dict:
    data = {
        "id": row.id,
        "periodMonth": row.period_month,
        "userId": row.user_id,
        "userName": row.user_name,
        "deptName": row.dept_name,
        "totalScore": float(row.total_score or 0),
        "alertedAt": iso(row.alerted_at),
        "pushTargets": list(row.push_targets or PUSH_TARGETS),
        "handleStatus": row.handle_status,
    }
    if row.handle_remark:
        data["handleRemark"] = row.handle_remark
    if row.follow_up_plan:
        data["followUpPlan"] = row.follow_up_plan
    return data


def period_score(row: PerfRank) -> dict:
    return {
        "periodMonth": row.period_month,
        "totalScore": float(row.total_score or 0),
        "gradeLevel": row.grade_level,
    }


@router.get("/rank/alerts")
def rank_alerts(
    periodMonth: str = "",
    handleStatus: str = "",
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_view_alerts(role_tags(db, actor)):
        return fail(403, "仅管理者可查看绩效预警")
    period = periodMonth.strip()
    if period and not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    status = handleStatus.strip().upper()
    if status and status not in {"PENDING", "DONE"}:
        return fail(1001, "处置状态无效")
    tenant_id = tenant_of(actor)
    sync_rank_alerts(db, tenant_id, period or None)
    stmt = select(PerfRankAlert).where(
        PerfRankAlert.deleted == 0,
        PerfRankAlert.tenant_id == tenant_id,
    )
    if period:
        stmt = stmt.where(PerfRankAlert.period_month == period)
    if status:
        stmt = stmt.where(PerfRankAlert.handle_status == status)
    page_no, size = page_args(pageNo, pageSize)
    ordered = stmt.order_by(PerfRankAlert.alerted_at.desc(), PerfRankAlert.id.desc())
    total = int(db.scalar(select(func.count()).select_from(ordered.subquery())) or 0)
    rows = db.scalars(ordered.offset((page_no - 1) * size).limit(size)).all()
    return paged([alert_vo(row) for row in rows], total, page_no, size)


@router.put("/rank/alert/{alert_id}/handle")
def handle_rank_alert(
    alert_id: int,
    body: AlertHandleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_handle_alert(role_tags(db, actor)):
        return fail(403, "仅运营总监或人事可登记预警处置")
    remark = body.handleRemark.strip()
    if not remark:
        return fail(1001, "处置说明必填")
    tenant_id = tenant_of(actor)
    row = db.get(PerfRankAlert, alert_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "预警不存在")
    if row.handle_status == "DONE":
        return fail(1001, "预警已处置")
    row.handle_status = "DONE"
    row.handle_remark = remark
    row.follow_up_plan = body.followUpPlan.strip()
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.get("/rank/coaching-list")
def coaching_list(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_view_coaching(role_tags(db, actor)):
        return fail(403, "仅管理者或部门负责人可查看重点辅导名单")
    tenant_id = tenant_of(actor)
    rows = db.scalars(
        select(PerfRank).where(
            PerfRank.deleted == 0,
            PerfRank.tenant_id == tenant_id,
            PerfRank.is_current == 1,
            PerfRank.grade_level == "IMPROVE",
            PerfRank.consecutive_months >= 2,
        )
    ).all()
    latest: dict[int, PerfRank] = {}
    for row in rows:
        held = latest.get(row.user_id)
        if held is None or row.period_month > held.period_month:
            latest[row.user_id] = row
    ordered = sorted(latest.values(), key=lambda item: (-int(item.consecutive_months or 0), float(item.total_score or 0)))
    data = []
    for row in ordered:
        prev = db.scalar(
            select(PerfRank).where(
                PerfRank.deleted == 0,
                PerfRank.tenant_id == tenant_id,
                PerfRank.period_month == previous_period(row.period_month),
                PerfRank.user_id == row.user_id,
                PerfRank.is_current == 1,
            )
        )
        item = rank_vo(row)
        periods = []
        if prev is not None:
            periods.append(period_score(prev))
        periods.append(period_score(row))
        item["lastTwoPeriods"] = periods
        data.append(item)
    return ok(data)
