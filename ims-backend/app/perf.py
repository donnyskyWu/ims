"""绩效考核 PERF-001 考核方案（W9-2 首片 · OPS M3 模板对齐）。"""

from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import ExamQuestion, PerfMetric, PerfPositionBind, PerfRecord, PerfScheme, User

router = APIRouter(prefix="/perf", tags=["perf"])

BJ = timezone(timedelta(hours=8))
PERIOD_TYPES = frozenset({"WEEKLY", "MONTHLY", "QUARTERLY", "HALF_YEAR", "YEAR", "CUSTOM"})
SCHEME_STATUSES = frozenset({"ACTIVE", "INACTIVE"})
RECORD_STATUSES = frozenset(
    {"DRAFT", "CALCULATING", "CALCULATED", "REVIEWED", "CONFIRMED", "ISSUED", "REJECTED"}
)
RESULT_STATUSES = frozenset({"CALCULATED", "REVIEWED", "CONFIRMED", "ISSUED"})
EXPORT_STATUSES = frozenset({"CONFIRMED", "ISSUED"})
# PRD-M3 绩效等级 PerfGrade。与 PerfGradeLevel（≥85 / ≥60）分开，不在这里混用。
GRADE_THRESHOLDS = ((90, "S"), (80, "A"), (70, "B"), (60, "C"))
GRADE_LETTERS = frozenset({"S", "A", "B", "C", "D"})
GRADE_EDGES = {
    "S": "S ≥90",
    "A": "A 80-89",
    "B": "B 70-79",
    "C": "C 60-69",
    "D": "D <60",
}
CALC_RULES = frozenset({"AUTO", "MANUAL", "MIXED"})
QUESTION_TYPES = frozenset({"SINGLE", "MULTIPLE", "JUDGE", "ESSAY"})
KNOWLEDGE_DOMAINS = frozenset(
    {"LIVE_RULE", "CONTENT_SKILL", "LIVE_SKILL", "DATA_SKILL", "COMPLIANCE"}
)

POSITION_LABELS = {
    "R5": "直播运营",
    "R6": "内容运营",
    "R2": "行政管理",
    "R4": "运营总监",
    "OPS_LEADER": "运营组长",
}


class SchemeItemBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricName: str
    weight: float = Field(ge=0, le=100)
    calcRule: str = "AUTO"


class ExecutionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    targetUserId: int
    schemeId: int | None = None
    templateId: int | None = None
    ipGroupId: int | None = None
    periodType: str = "QUARTERLY"
    periodStart: str
    periodEnd: str


class AdjustBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    manualAdjustment: float
    remark: str = ""


class SchemeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateName: str
    positionCode: str
    periodType: str = "QUARTERLY"
    items: list[SchemeItemBody] = Field(default_factory=list)
    metricSummary: str = ""
    evaluateeCount: int = Field(ge=0, default=0)
    activate: bool = False


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def position_label(code: str) -> str:
    return POSITION_LABELS.get(code or "", code or "—")


def weight_total(items: list) -> float:
    return round(sum(float(item.get("weight") or 0) for item in items), 2)


def build_metric_summary(body: SchemeBody) -> str:
    if body.metricSummary.strip():
        return body.metricSummary.strip()
    names = [item.metricName.strip() for item in body.items if item.metricName.strip()]
    return " · ".join(names[:4])


def validate_items(items: list[SchemeItemBody]) -> str | None:
    if not items:
        return "至少配置一项指标"
    total = round(sum(item.weight for item in items), 2)
    if abs(total - 100) > 0.01:
        return "指标权重合计须为 100%"
    for item in items:
        if not item.metricName.strip():
            return "指标名称必填"
        if item.calcRule not in CALC_RULES:
            return "算分方式无效"
    return None


def cycle_display(period_type: str, period_start: str, period_end: str) -> str:
    start = (period_start or "")[:10]
    end = (period_end or "")[:10]
    if period_type == "QUARTERLY" and start:
        try:
            year = int(start[:4])
            month = int(start[5:7])
            quarter = (month - 1) // 3 + 1
            return f"{year} Q{quarter}"
        except ValueError:
            pass
    if period_type == "MONTHLY" and start:
        return start[:7]
    if start and end and start != end:
        return f"{start} ~ {end}"
    return start or end or "—"


def user_label(db: Session, user_id: int) -> str:
    if not user_id:
        return "—"
    user = db.get(User, user_id)
    if user is None or user.deleted:
        return f"用户#{user_id}"
    return user.nickname or user.username or f"用户#{user_id}"


def next_record_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m")
    prefix = f"PR{day}"
    count = db.scalar(
        select(func.count())
        .select_from(PerfRecord)
        .where(
            PerfRecord.deleted == 0,
            PerfRecord.tenant_id == tenant_id,
            PerfRecord.record_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def next_scheme_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"PS{day}"
    count = db.scalar(
        select(func.count())
        .select_from(PerfScheme)
        .where(
            PerfScheme.deleted == 0,
            PerfScheme.tenant_id == tenant_id,
            PerfScheme.scheme_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def grade_of(score: float | None) -> str:
    if score is None:
        return "—"
    for threshold, label in GRADE_THRESHOLDS:
        if score >= threshold:
            return label
    return "D"


def grade_edge(letter: str) -> str:
    return GRADE_EDGES.get(letter, letter)


def grade_counts(rows: list[PerfRecord]) -> dict[str, int]:
    counts = {letter: 0 for letter in ("S", "A", "B", "C", "D")}
    for row in rows:
        letter = grade_of(row.total_score)
        if letter in counts:
            counts[letter] += 1
    return counts


def matching_user_ids(db: Session, tenant_id: int, keyword: str) -> list[int] | None:
    text = keyword.strip()
    if not text:
        return None
    like = f"%{text}%"
    return list(
        db.scalars(
            select(User.id).where(
                User.deleted == 0,
                User.tenant_id == tenant_id,
                or_(User.nickname.like(like), User.username.like(like)),
            )
        ).all()
    )


def result_records(
    db: Session,
    tenant_id: int,
    *,
    statuses: frozenset[str],
    target_user_id: int | None,
    period_type: str | None,
    status: str | None,
    evaluatee_name: str | None,
    grade: str | None,
    record_no: str | None = None,
) -> tuple[list[PerfRecord], dict[str, int], str | None]:
    if grade and grade not in GRADE_LETTERS:
        return [], {}, "grade 无效"
    if status and status not in statuses:
        return [], {}, "status 无效"
    if period_type and period_type not in PERIOD_TYPES:
        return [], {}, "periodType 无效"
    user_ids = matching_user_ids(db, tenant_id, evaluatee_name or "")
    empty_counts = {letter: 0 for letter in ("S", "A", "B", "C", "D")}
    if user_ids is not None and not user_ids:
        return [], empty_counts, None
    stmt = select(PerfRecord).where(
        PerfRecord.deleted == 0,
        PerfRecord.tenant_id == tenant_id,
        PerfRecord.status.in_(statuses),
    )
    if target_user_id:
        stmt = stmt.where(PerfRecord.target_user_id == target_user_id)
    if user_ids is not None:
        stmt = stmt.where(PerfRecord.target_user_id.in_(user_ids))
    if period_type:
        stmt = stmt.where(PerfRecord.period_type == period_type)
    if status:
        stmt = stmt.where(PerfRecord.status == status)
    if record_no and record_no.strip():
        stmt = stmt.where(PerfRecord.record_no.like(f"%{record_no.strip()}%"))
    rows = list(
        db.scalars(
            stmt.order_by(PerfRecord.total_score.desc(), PerfRecord.id.desc())
        ).all()
    )
    counts = grade_counts(rows)
    if grade:
        rows = [row for row in rows if grade_of(row.total_score) == grade]
    return rows, counts, None


def result_vo(db: Session, row: PerfRecord, scheme: PerfScheme | None = None) -> dict:
    base = record_vo(db, row, scheme)
    letter = grade_of(row.total_score)
    base["grade"] = letter
    base["gradeEdge"] = grade_edge(letter)
    base["published"] = row.status in ("CONFIRMED", "ISSUED")
    return base


def record_vo(db: Session, row: PerfRecord, scheme: PerfScheme | None = None) -> dict:
    if scheme is None and row.scheme_id:
        scheme = db.get(PerfScheme, row.scheme_id)
    position = position_label(scheme.position_code) if scheme else "—"
    return {
        "id": row.id,
        "recordNo": row.record_no,
        "targetUserId": row.target_user_id,
        "evaluateeName": user_label(db, row.target_user_id),
        "position": position,
        "positionCode": scheme.position_code if scheme else "",
        "cycleDisplay": cycle_display(row.period_type, row.period_start, row.period_end),
        "periodType": row.period_type,
        "periodStart": row.period_start,
        "periodEnd": row.period_end,
        "schemeId": row.scheme_id,
        "schemeName": scheme.template_name if scheme else "",
        "totalScore": row.total_score,
        "calcBaseScore": row.calc_base_score,
        "manualAdjustment": float(row.manual_adjustment or 0),
        "adjustRemark": row.adjust_remark or "",
        "status": row.status,
        "evaluatorUserId": row.evaluator_user_id,
        "evaluatorName": user_label(db, row.evaluator_user_id),
        "ipGroupId": row.ip_group_id or None,
        "createdAt": iso(row.created_at),
    }


def scheme_vo(row: PerfScheme) -> dict:
    items = row.items if isinstance(row.items, list) else []
    return {
        "id": row.id,
        "schemeNo": row.scheme_no,
        "templateName": row.template_name,
        "positionCode": row.position_code,
        "positionLabel": position_label(row.position_code),
        "periodType": row.period_type,
        "status": row.status,
        "itemCount": len(items),
        "items": items,
        "metricSummary": row.metric_summary or "",
        "evaluateeCount": int(row.evaluatee_count or 0),
        "weightTotal": weight_total(items),
        "createdBy": row.created_by,
        "createdAt": iso(row.created_at),
    }


def mock_total_score(scheme: PerfScheme) -> float:
    items = scheme.items if isinstance(scheme.items, list) else []
    total = 0.0
    for item in items:
        weight = float(item.get("weight") or 0)
        name = str(item.get("metricName") or "")
        raw = 70.0 + (hash(name) % 26)
        total += raw * weight / 100.0
    return round(total, 1) if items else 75.0


def deactivate_position_schemes(db: Session, tenant_id: int, position_code: str, except_id: int | None = None) -> None:
    stmt = (
        update(PerfScheme)
        .where(
            PerfScheme.deleted == 0,
            PerfScheme.tenant_id == tenant_id,
            PerfScheme.position_code == position_code,
            PerfScheme.status == "ACTIVE",
        )
        .values(status="INACTIVE", updated_at=utcnow())
    )
    if except_id is not None:
        stmt = stmt.where(PerfScheme.id != except_id)
    db.execute(stmt)


@router.get("/scheme/list")
def scheme_list(
    templateName: str | None = None,
    positionCode: str | None = None,
    periodType: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(PerfScheme).where(PerfScheme.deleted == 0, PerfScheme.tenant_id == tenant_id)
    if templateName:
        stmt = stmt.where(PerfScheme.template_name.contains(templateName.strip()))
    if positionCode:
        stmt = stmt.where(PerfScheme.position_code == positionCode.strip())
    if periodType:
        stmt = stmt.where(PerfScheme.period_type == periodType)
    if status:
        if status not in SCHEME_STATUSES:
            return fail(1001, "status 无效")
        stmt = stmt.where(PerfScheme.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(PerfScheme.status.desc(), PerfScheme.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([scheme_vo(row) for row in rows], total, page_no, size)


@router.post("/scheme")
def create_scheme(
    body: SchemeBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.templateName.strip():
        return fail(1001, "templateName 必填")
    if not body.positionCode.strip():
        return fail(1001, "positionCode 必填")
    if body.periodType not in PERIOD_TYPES:
        return fail(1001, "periodType 无效")
    err = validate_items(body.items)
    if err:
        return fail(1001, err)
    tenant_id = tenant_of(actor)
    status = "ACTIVE" if body.activate else "INACTIVE"
    row = PerfScheme(
        scheme_no=next_scheme_no(db, tenant_id),
        template_name=body.templateName.strip(),
        position_code=body.positionCode.strip(),
        period_type=body.periodType,
        status=status,
        items=[item.model_dump() for item in body.items],
        metric_summary=build_metric_summary(body),
        evaluatee_count=body.evaluateeCount,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    if status == "ACTIVE":
        deactivate_position_schemes(db, tenant_id, row.position_code, except_id=row.id)
    db.flush()
    return ok(scheme_vo(row))


@router.get("/execution/list")
def execution_list(
    targetUserId: int | None = None,
    ipGroupId: int | None = None,
    periodType: str | None = None,
    status: str | None = None,
    schemeId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(PerfRecord).where(PerfRecord.deleted == 0, PerfRecord.tenant_id == tenant_id)
    if targetUserId:
        stmt = stmt.where(PerfRecord.target_user_id == targetUserId)
    if ipGroupId:
        stmt = stmt.where(PerfRecord.ip_group_id == ipGroupId)
    if periodType:
        stmt = stmt.where(PerfRecord.period_type == periodType)
    if schemeId:
        stmt = stmt.where(PerfRecord.scheme_id == schemeId)
    if status:
        if status not in RECORD_STATUSES:
            return fail(1001, "status 无效")
        stmt = stmt.where(PerfRecord.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(PerfRecord.id.desc()).offset((page_no - 1) * size).limit(size)
        ).all()
    )
    scheme_ids = {row.scheme_id for row in rows if row.scheme_id}
    schemes = {}
    if scheme_ids:
        for scheme in db.scalars(
            select(PerfScheme).where(PerfScheme.id.in_(scheme_ids), PerfScheme.deleted == 0)
        ).all():
            schemes[scheme.id] = scheme
    return paged([record_vo(db, row, schemes.get(row.scheme_id)) for row in rows], total, page_no, size)


@router.post("/execution")
def create_execution(
    body: ExecutionBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    scheme_id = body.schemeId or body.templateId
    if not scheme_id:
        return fail(1001, "schemeId 必填")
    if body.periodType not in PERIOD_TYPES:
        return fail(1001, "periodType 无效")
    if not body.periodStart.strip() or not body.periodEnd.strip():
        return fail(1001, "考核周期起止必填")
    tenant_id = tenant_of(actor)
    scheme = db.get(PerfScheme, scheme_id)
    if scheme is None or scheme.deleted or scheme.tenant_id != tenant_id:
        return fail(1500, "方案不存在")
    if scheme.status != "ACTIVE":
        return fail(1001, "仅可对生效中的方案发起考核")
    target = db.get(User, body.targetUserId)
    if target is None or target.deleted or target.status != "ENABLED":
        return fail(1001, "被考核人无效")
    row = PerfRecord(
        record_no=next_record_no(db, tenant_id),
        scheme_id=scheme.id,
        target_user_id=body.targetUserId,
        ip_group_id=int(body.ipGroupId or 0),
        period_type=body.periodType,
        period_start=body.periodStart.strip(),
        period_end=body.periodEnd.strip(),
        status="DRAFT",
        evaluator_user_id=actor.id,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(record_vo(db, row, scheme))


def scheme_map(db: Session, rows: list[PerfRecord]) -> dict[int, PerfScheme]:
    scheme_ids = {row.scheme_id for row in rows if row.scheme_id}
    schemes: dict[int, PerfScheme] = {}
    if scheme_ids:
        for scheme in db.scalars(
            select(PerfScheme).where(PerfScheme.id.in_(scheme_ids), PerfScheme.deleted == 0)
        ).all():
            schemes[scheme.id] = scheme
    return schemes


@router.get("/result/list")
def result_list(
    targetUserId: int | None = None,
    periodType: str | None = None,
    status: str | None = None,
    evaluateeName: str | None = None,
    grade: str | None = None,
    recordNo: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    rows, counts, err = result_records(
        db,
        tenant_id,
        statuses=RESULT_STATUSES,
        target_user_id=targetUserId,
        period_type=periodType,
        status=status,
        evaluatee_name=evaluateeName,
        grade=grade,
        record_no=recordNo,
    )
    if err:
        return fail(1001, err)
    total = len(rows)
    page_rows = rows[(page_no - 1) * size : page_no * size]
    schemes = scheme_map(db, page_rows)
    payload = paged(
        [result_vo(db, row, schemes.get(row.scheme_id)) for row in page_rows],
        total,
        page_no,
        size,
    )
    payload["data"]["gradeCounts"] = counts
    return payload


@router.get("/result/export")
def result_export(
    targetUserId: int | None = None,
    periodType: str | None = None,
    status: str | None = None,
    evaluateeName: str | None = None,
    grade: str | None = None,
    recordNo: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    rows, _, err = result_records(
        db,
        tenant_id,
        statuses=EXPORT_STATUSES,
        target_user_id=targetUserId,
        period_type=periodType,
        status=status,
        evaluatee_name=evaluateeName,
        grade=grade,
        record_no=recordNo,
    )
    if err:
        return fail(1001, err)
    rows = rows[:5000]
    schemes = scheme_map(db, rows)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["recordNo", "evaluateeName", "position", "cycleDisplay", "totalScore", "grade", "status"]
    )
    for row in rows:
        vo = result_vo(db, row, schemes.get(row.scheme_id))
        writer.writerow(
            [
                vo["recordNo"],
                vo["evaluateeName"],
                vo["position"],
                vo["cycleDisplay"],
                vo["totalScore"] if vo["totalScore"] is not None else "",
                vo["grade"],
                vo["status"],
            ]
        )
    payload = "\ufeff" + buf.getvalue()
    return Response(
        content=payload.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="perf_results.csv"',
            "X-Export-Rows": str(len(rows)),
        },
    )


@router.get("/result/{record_id}")
def result_detail(
    record_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(PerfRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "考核记录不存在")
    if row.status not in RESULT_STATUSES:
        return fail(1157, "考核结果尚未发布")
    scheme = db.get(PerfScheme, row.scheme_id) if row.scheme_id else None
    return ok(result_vo(db, row, scheme))


@router.post("/execution/{record_id}/calculate")
def calculate_execution(
    record_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(PerfRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "考核记录不存在")
    if row.status not in ("DRAFT", "CALCULATING", "REJECTED"):
        return fail(1001, "当前状态不可算分")
    scheme = db.get(PerfScheme, row.scheme_id) if row.scheme_id else None
    if scheme is None or scheme.deleted:
        return fail(1500, "方案不存在")
    row.status = "CALCULATING"
    row.updated_at = utcnow()
    db.flush()
    row.total_score = mock_total_score(scheme)
    row.calc_base_score = row.total_score
    row.manual_adjustment = 0.0
    row.adjust_remark = ""
    row.status = "CALCULATED"
    row.updated_at = utcnow()
    db.flush()
    return ok(record_vo(db, row, scheme))


@router.put("/execution/{record_id}/adjust")
def adjust_execution(
    record_id: int,
    body: AdjustBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(PerfRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "考核记录不存在")
    if row.status in ("CONFIRMED", "ISSUED"):
        return fail(1155, "周期数据已锁定，更正须运营总监审批并留痕")
    if row.status not in ("CALCULATED", "REVIEWED"):
        return fail(1001, "须先完成算分后再调整")
    base = row.calc_base_score
    if base is None:
        base = row.total_score
    if base is None:
        return fail(1001, "总分缺失，请先算分")
    delta = float(body.manualAdjustment)
    if abs(delta) > round(float(base) * 0.2, 4) + 1e-6:
        return fail(1001, "人工调整幅度不得超过基础分的 ±20%")
    row.manual_adjustment = delta
    row.adjust_remark = (body.remark or "").strip()[:256]
    row.total_score = round(float(base) + delta, 1)
    row.status = "REVIEWED"
    row.updated_at = utcnow()
    db.flush()
    scheme = db.get(PerfScheme, row.scheme_id) if row.scheme_id else None
    return ok(record_vo(db, row, scheme))


@router.post("/execution/{record_id}/confirm")
def confirm_execution(
    record_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(PerfRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "考核记录不存在")
    if row.status not in ("CALCULATED", "REVIEWED"):
        return fail(1001, "须先完成算分后再确认")
    if row.total_score is None:
        return fail(1001, "总分缺失，请先算分")
    row.status = "CONFIRMED"
    row.updated_at = utcnow()
    db.flush()
    scheme = db.get(PerfScheme, row.scheme_id) if row.scheme_id else None
    return ok(record_vo(db, row, scheme))


@router.put("/execution/{record_id}/issue")
def issue_execution(
    record_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(PerfRecord, record_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "考核记录不存在")
    if row.status == "ISSUED":
        return fail(1155, "周期数据已锁定，更正须运营总监审批并留痕")
    if row.status not in ("REVIEWED", "CONFIRMED"):
        return fail(1001, "须先确认考核结果后再下发")
    if row.total_score is None:
        return fail(1001, "总分缺失，请先算分")
    row.status = "ISSUED"
    row.updated_at = utcnow()
    db.flush()
    scheme = db.get(PerfScheme, row.scheme_id) if row.scheme_id else None
    return ok(record_vo(db, row, scheme))


def ensure_exam_questions(db: Session, tenant_id: int, actor_id: int) -> None:
    rows = db.scalars(
        select(ExamQuestion)
        .where(ExamQuestion.deleted == 0, ExamQuestion.tenant_id == tenant_id)
        .order_by(ExamQuestion.id.asc())
    ).all()
    seen: set[str] = set()
    for row in rows:
        key = (row.question_no or "").strip()
        if not key or key in seen:
            row.deleted = 1
            continue
        seen.add(key)
    _insert_exam_question_seeds(db, tenant_id, actor_id, seen)
    from app.exam_paper import backfill_question_answers

    backfill_question_answers(db, tenant_id)


def _insert_exam_question_seeds(db: Session, tenant_id: int, actor_id: int, seen: set[str] | None = None) -> None:
    seeds = [
        ("EQ-001", "直播开场 15 分钟的留存红线是？", "LIVE_RULE", "SINGLE", 10, 6),
        ("EQ-002", "以下哪些行为属于平台高危违规（多选）？", "LIVE_RULE", "MULTIPLE", 10, 5),
        ("EQ-003", "直播间挂「福利品」时可以直接改价上链接。（判断）", "LIVE_RULE", "JUDGE", 5, 8),
        ("EQ-004", "短视频完播率显著衰减的时间点是？", "CONTENT_SKILL", "SINGLE", 10, 4),
        ("EQ-005", "口播脚本「痛点前置」的正确做法是？", "CONTENT_SKILL", "SINGLE", 10, 7),
        ("EQ-006", "请简述一个你操盘过的直播间起号思路。（简答）", "LIVE_SKILL", "ESSAY", 20, 2),
        ("EQ-007", "投流 ROI 的计算公式是？", "DATA_SKILL", "SINGLE", 10, 6),
        ("EQ-008", "口径「GMV」与「净 GMV」的区别是什么？（简答）", "DATA_SKILL", "ESSAY", 15, 1),
        ("EQ-009", "数据上报的截止时间是每日几点前？", "COMPLIANCE", "SINGLE", 10, 9),
        ("EQ-010", "外协人员可以访问公司数据看板。（判断）", "COMPLIANCE", "JUDGE", 5, 3),
    ]
    present = seen or set()
    for qno, stem, domain, qtype, score, refs in seeds:
        if qno in present:
            continue
        db.add(
            ExamQuestion(
                question_no=qno,
                stem=stem,
                knowledge_domain=domain,
                question_type=qtype,
                score=score,
                ref_count=refs,
                created_by=actor_id,
                tenant_id=tenant_id,
            )
        )
    db.flush()


def question_vo(row: ExamQuestion) -> dict:
    labels = {
        "LIVE_RULE": "直播规范",
        "CONTENT_SKILL": "内容技能",
        "LIVE_SKILL": "直播技能",
        "DATA_SKILL": "数据技能",
        "COMPLIANCE": "制度合规",
    }
    type_labels = {
        "SINGLE": "单选",
        "MULTIPLE": "多选",
        "JUDGE": "判断",
        "ESSAY": "简答",
    }
    return {
        "id": str(row.id),
        "questionNo": row.question_no,
        "stem": row.stem,
        "knowledgeDomain": row.knowledge_domain,
        "knowledgeDomainLabel": labels.get(row.knowledge_domain, row.knowledge_domain),
        "questionType": row.question_type,
        "questionTypeLabel": type_labels.get(row.question_type, row.question_type),
        "score": row.score,
        "refCount": row.ref_count,
    }


@router.get("/exam/questions")
def exam_questions(
    pageNo: int = 1,
    pageSize: int = 10,
    questionNo: str = "",
    stemKeyword: str = "",
    knowledgeDomain: str = "",
    questionType: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_exam_questions(db, tenant_id, actor.id)

    stmt = select(ExamQuestion).where(ExamQuestion.deleted == 0, ExamQuestion.tenant_id == tenant_id)
    if questionNo.strip():
        stmt = stmt.where(ExamQuestion.question_no.like(f"%{questionNo.strip()}%"))
    if stemKeyword.strip():
        stmt = stmt.where(ExamQuestion.stem.like(f"%{stemKeyword.strip()}%"))
    if knowledgeDomain.strip():
        dom = knowledgeDomain.strip().upper()
        if dom not in KNOWLEDGE_DOMAINS:
            return fail(1001, "知识域无效")
        stmt = stmt.where(ExamQuestion.knowledge_domain == dom)
    if questionType.strip():
        qt = questionType.strip().upper()
        if qt not in QUESTION_TYPES:
            return fail(1001, "题型无效")
        stmt = stmt.where(ExamQuestion.question_type == qt)

    page_no, size = page_args(pageNo, pageSize)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(ExamQuestion.question_no.asc()).offset((page_no - 1) * size).limit(size)
    ).all()
    return paged([question_vo(row) for row in rows], int(total or 0), page_no, size)


@router.post("/scheme/{scheme_id}/activate")
def activate_scheme(
    scheme_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(PerfScheme, scheme_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "方案不存在")
    deactivate_position_schemes(db, tenant_id, row.position_code, except_id=row.id)
    row.status = "ACTIVE"
    row.updated_at = utcnow()
    db.flush()
    return ok(scheme_vo(row))


COMPETE_CODE = "COMPETE_SUBMIT_RATE"
COMPETE_NOTE = "待 V3 竞品管理（04）上线后启用（BR-110/BR-206）"
COMPETE_LOCK_MSG = "竞品分析提交率指标 V2 锁定禁用（BR-110）"
METRIC_SOURCES = frozenset({"AUTO", "MANUAL", "EXAM"})
METRIC_MODULES = frozenset({"TRAIN", "MEET", "REPORT", "LIVE", "FIN", "FLOW"})
METRIC_STATUSES = frozenset({"ENABLED", "DISABLED"})
SCORE_RULE_TYPES = frozenset({"SEGMENT", "LINEAR"})
HUNDRED = Decimal("100.00")
ZERO = Decimal("0.00")


class ScoreSegmentBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    minValue: float
    maxValue: float | None = None
    score: float


class ScoreLinearBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    minMetric: float
    maxMetric: float
    minScore: float
    maxScore: float


class ScoreRuleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ruleType: str
    segments: list[ScoreSegmentBody] | None = None
    linear: ScoreLinearBody | None = None


class SourceConfigBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    module: str
    metricExpression: str
    periodType: str = "MONTHLY"


class MetricBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricCode: str
    metricName: str
    dataSource: str
    sourceConfig: SourceConfigBody | None = None
    weight: float = Field(ge=0, le=100)
    scoreRule: ScoreRuleBody
    status: str | None = None


class MetricBindItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricId: int
    weightOverride: float | None = Field(default=None, ge=0, le=100)


class TestFetchBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricId: int
    testPeriod: str


class PositionBindBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    positionCode: str
    metricBindings: list[MetricBindItem] = Field(default_factory=list)


def q2(value: float | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def score_in_range(value: float) -> bool:
    score = q2(value)
    return ZERO <= score <= HUNDRED


def segments_overlap(ranges: list[tuple[Decimal, Decimal | None]]) -> bool:
    """半开区间 [min, max)；max 为空表示无上界。相邻端点不算重叠。"""
    ordered = sorted(ranges, key=lambda item: (item[0], item[1] is None))
    prev_hi: Decimal | None = None
    started = False
    for lo, hi in ordered:
        if started and (prev_hi is None or lo < prev_hi):
            return True
        started = True
        prev_hi = hi
    return False


def check_score_rule(rule: ScoreRuleBody):
    kind = (rule.ruleType or "").strip().upper()
    if kind not in SCORE_RULE_TYPES:
        return fail(1001, "得分规则类型无效")
    if kind == "LINEAR":
        if rule.linear is None:
            return fail(1001, "线性得分规则缺少参数")
        if not score_in_range(rule.linear.minScore) or not score_in_range(rule.linear.maxScore):
            return fail(1152, "得分规则非法：分数越界 [0,100]")
        return None
    segments = rule.segments or []
    if not segments:
        return fail(1152, "得分规则非法：分段区间缺失")
    ranges: list[tuple[Decimal, Decimal | None]] = []
    for seg in segments:
        if not score_in_range(seg.score):
            return fail(1152, "得分规则非法：分数越界 [0,100]")
        lo = q2(seg.minValue)
        hi = None if seg.maxValue is None else q2(seg.maxValue)
        if hi is not None and hi <= lo:
            return fail(1152, "得分规则非法：分段区间非法")
        ranges.append((lo, hi))
    if segments_overlap(ranges):
        return fail(1152, "得分规则非法：分段区间重叠")
    return None


def dump_score_rule(rule: ScoreRuleBody) -> dict:
    kind = rule.ruleType.strip().upper()
    if kind == "LINEAR" and rule.linear is not None:
        linear = rule.linear
        return {
            "ruleType": "LINEAR",
            "linear": {
                "minMetric": float(q2(linear.minMetric)),
                "maxMetric": float(q2(linear.maxMetric)),
                "minScore": float(q2(linear.minScore)),
                "maxScore": float(q2(linear.maxScore)),
            },
        }
    segments = []
    for seg in rule.segments or []:
        segments.append(
            {
                "minValue": float(q2(seg.minValue)),
                "maxValue": None if seg.maxValue is None else float(q2(seg.maxValue)),
                "score": float(q2(seg.score)),
            }
        )
    return {"ruleType": "SEGMENT", "segments": segments}


def check_metric_body(body: MetricBody):
    code = body.metricCode.strip()
    name = body.metricName.strip()
    if not code:
        return fail(1001, "指标编码必填"), None
    if not name:
        return fail(1001, "指标名称必填"), None
    source = body.dataSource.strip().upper()
    if source not in METRIC_SOURCES:
        return fail(1001, "取数来源无效"), None
    status = (body.status or "ENABLED").strip().upper()
    if status not in METRIC_STATUSES:
        return fail(1001, "指标状态无效"), None
    if code == COMPETE_CODE and status == "ENABLED":
        return fail(1153, COMPETE_LOCK_MSG), None
    if code == COMPETE_CODE:
        status = "DISABLED"
    source_config = None
    if source == "AUTO":
        if body.sourceConfig is None:
            return fail(1001, "自动取数指标须填写取数映射"), None
        module = body.sourceConfig.module.strip().upper()
        expr = body.sourceConfig.metricExpression.strip()
        period = (body.sourceConfig.periodType or "").strip().upper()
        if module not in METRIC_MODULES:
            return fail(1001, "取数模块无效"), None
        if not expr:
            return fail(1001, "指标表达式必填"), None
        if period != "MONTHLY":
            return fail(1001, "取数周期仅支持 MONTHLY"), None
        source_config = {"module": module, "metricExpression": expr, "periodType": "MONTHLY"}
    ruled = check_score_rule(body.scoreRule)
    if ruled is not None:
        return ruled, None
    payload = {
        "metricCode": code,
        "metricName": name,
        "dataSource": source,
        "sourceConfig": source_config,
        "weight": float(q2(body.weight)),
        "scoreRule": dump_score_rule(body.scoreRule),
        "status": status,
    }
    return None, payload


def metric_vo(row: PerfMetric) -> dict:
    data = {
        "id": row.id,
        "metricCode": row.metric_code,
        "metricName": row.metric_name,
        "dataSource": row.data_source,
        "weight": float(q2(row.weight or 0)),
        "scoreRule": row.score_rule or {},
        "status": row.status,
        "version": row.version,
    }
    if row.source_config:
        data["sourceConfig"] = row.source_config
    if row.metric_code == COMPETE_CODE or row.enable_note:
        data["enableNote"] = row.enable_note or COMPETE_NOTE
    return data


def ensure_compete_metric(db: Session, tenant_id: int, actor_id: int) -> PerfMetric:
    rows = list(
        db.scalars(
            select(PerfMetric)
            .where(
                PerfMetric.deleted == 0,
                PerfMetric.tenant_id == tenant_id,
                PerfMetric.metric_code == COMPETE_CODE,
            )
            .order_by(PerfMetric.id.asc())
        ).all()
    )
    if rows:
        row = rows[0]
        for extra in rows[1:]:
            extra.deleted = 1
            extra.updated_at = utcnow()
        if len(rows) > 1:
            db.flush()
        if row.status != "DISABLED":
            row.status = "DISABLED"
        if not row.enable_note:
            row.enable_note = COMPETE_NOTE
        return row
    row = PerfMetric(
        metric_code=COMPETE_CODE,
        metric_name="竞品分析提交率",
        data_source="MANUAL",
        source_config=None,
        weight=0,
        score_rule={
            "ruleType": "LINEAR",
            "linear": {"minMetric": 0, "maxMetric": 100, "minScore": 0, "maxScore": 100},
        },
        status="DISABLED",
        enable_note=COMPETE_NOTE,
        version=1,
        created_by=actor_id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return row


def find_metric(db: Session, tenant_id: int, metric_id: int) -> PerfMetric | None:
    row = db.get(PerfMetric, metric_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    return row


def code_taken(db: Session, tenant_id: int, code: str, except_id: int | None = None) -> bool:
    stmt = select(PerfMetric.id).where(
        PerfMetric.deleted == 0,
        PerfMetric.tenant_id == tenant_id,
        PerfMetric.metric_code == code,
    )
    if except_id is not None:
        stmt = stmt.where(PerfMetric.id != except_id)
    return db.scalar(stmt) is not None


@router.get("/metric/list")
def metric_list(
    pageNo: int = 1,
    pageSize: int = 10,
    metricName: str = "",
    dataSource: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_compete_metric(db, tenant_id, actor.id)
    stmt = select(PerfMetric).where(PerfMetric.deleted == 0, PerfMetric.tenant_id == tenant_id)
    if metricName.strip():
        stmt = stmt.where(PerfMetric.metric_name.like(f"%{metricName.strip()}%"))
    if dataSource.strip():
        source = dataSource.strip().upper()
        if source not in METRIC_SOURCES:
            return fail(1001, "取数来源无效")
        stmt = stmt.where(PerfMetric.data_source == source)
    if status.strip():
        stat = status.strip().upper()
        if stat not in METRIC_STATUSES:
            return fail(1001, "指标状态无效")
        stmt = stmt.where(PerfMetric.status == stat)
    page_no, size = page_args(pageNo, pageSize)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(PerfMetric.id.asc()).offset((page_no - 1) * size).limit(size)).all()
    return paged([metric_vo(row) for row in rows], int(total or 0), page_no, size)


AUTO_FETCH_PAIRS = frozenset(
    {
        ("TRAIN", "finish_rate"),
        ("MEET", "on_time_rate"),
        ("REPORT", "on_time_rate"),
        ("LIVE", "gmv"),
        ("LIVE", "session_count"),
    }
)


def coverage_payload(rows: list[PerfMetric]) -> dict:
    enabled = [row for row in rows if row.status == "ENABLED"]
    auto_rows = [row for row in enabled if (row.data_source or "").upper() in {"AUTO", "EXAM"}]
    manual = [
        {"metricCode": row.metric_code, "metricName": row.metric_name}
        for row in enabled
        if (row.data_source or "").upper() not in {"AUTO", "EXAM"}
    ]
    manual.sort(key=lambda item: item["metricCode"])
    enabled_count = len(enabled)
    auto_count = len(auto_rows)
    if enabled_count == 0:
        rate = 0.0
    else:
        rate = float(q2(Decimal(auto_count) * Decimal(100) / Decimal(enabled_count)))
    return {
        "enabledMetricCount": enabled_count,
        "autoMetricCount": auto_count,
        "autoCoverageRate": rate,
        "manualMetrics": manual,
    }


def probe_fetch(db: Session, actor: User, metric: PerfMetric, period: str) -> tuple[bool, float | None, str]:
    if metric.status != "ENABLED":
        return False, None, "指标已禁用，不能试取数"
    source = (metric.data_source or "").upper()
    if source == "MANUAL":
        return False, None, "手工指标不支持自动取数"
    if source == "EXAM":
        return True, 0.0, ""
    if source != "AUTO":
        return False, None, "取数来源无效"
    config = metric.source_config or {}
    module = str(config.get("module") or "").upper()
    expression = str(config.get("metricExpression") or "")
    if module == "FIN":
        return False, None, "财务取数本期未接入本地试取"
    if (module, expression) not in AUTO_FETCH_PAIRS:
        return False, None, "指标表达式无法取数"
    from app.perf_calc import fetch_auto

    value = fetch_auto(db, metric.tenant_id, actor.id, period, module, expression)
    if value is None:
        return True, None, "本期无样本数据，取数通道可用"
    return True, float(value), ""


@router.get("/metric/auto-coverage")
def metric_auto_coverage(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    from app.perf_calc import can_view_coverage, role_tags

    if not can_view_coverage(role_tags(db, actor)):
        return fail(403, "仅超管或运营总监可查看自动取数覆盖率")
    tenant_id = tenant_of(actor)
    ensure_compete_metric(db, tenant_id, actor.id)
    rows = db.scalars(
        select(PerfMetric).where(PerfMetric.deleted == 0, PerfMetric.tenant_id == tenant_id)
    ).all()
    return ok(coverage_payload(list(rows)))


@router.post("/metric/test-fetch")
def metric_test_fetch(
    body: TestFetchBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    from app.perf_calc import can_test_fetch, role_tags

    if not can_test_fetch(role_tags(db, actor)):
        return fail(403, "仅超管、运营总监或财务可试取数")
    period = body.testPeriod.strip()
    from app.perf_calc import period_ok

    if not period_ok(period):
        return fail(1001, "绩效月格式须为 yyyy-MM")
    tenant_id = tenant_of(actor)
    metric = find_metric(db, tenant_id, body.metricId)
    if metric is None:
        return fail(1500, "指标不存在")
    started = time.perf_counter()
    fetchable, sample, reason = probe_fetch(db, actor, metric, period)
    elapsed = int((time.perf_counter() - started) * 1000)
    data: dict = {"fetchable": fetchable, "elapsedMs": elapsed}
    if sample is not None:
        data["sampleValue"] = sample
    if reason:
        data["errorReason"] = reason
    return ok(data)


@router.post("/metric")
def create_metric(
    body: MetricBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_compete_metric(db, tenant_id, actor.id)
    rejected, payload = check_metric_body(body)
    if rejected is not None:
        return rejected
    assert payload is not None
    if code_taken(db, tenant_id, payload["metricCode"]):
        return fail(1151, "指标编码已存在")
    row = PerfMetric(
        metric_code=payload["metricCode"],
        metric_name=payload["metricName"],
        data_source=payload["dataSource"],
        source_config=payload["sourceConfig"],
        weight=payload["weight"],
        score_rule=payload["scoreRule"],
        status=payload["status"],
        enable_note=COMPETE_NOTE if payload["metricCode"] == COMPETE_CODE else "",
        version=1,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(metric_vo(row))


@router.put("/metric/{metric_id}")
def update_metric(
    metric_id: int,
    body: MetricBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_compete_metric(db, tenant_id, actor.id)
    row = find_metric(db, tenant_id, metric_id)
    if row is None:
        return fail(1500, "指标不存在")
    if row.metric_code == COMPETE_CODE and (body.status or "").strip().upper() == "ENABLED":
        return fail(1153, COMPETE_LOCK_MSG)
    if body.metricCode.strip() != row.metric_code:
        return fail(1001, "指标编码不可修改")
    rejected, payload = check_metric_body(body)
    if rejected is not None:
        return rejected
    assert payload is not None
    if row.metric_code == COMPETE_CODE:
        payload["status"] = "DISABLED"
    row.metric_name = payload["metricName"]
    row.data_source = payload["dataSource"]
    row.source_config = payload["sourceConfig"]
    row.weight = payload["weight"]
    row.score_rule = payload["scoreRule"]
    row.status = payload["status"]
    if row.metric_code == COMPETE_CODE:
        row.enable_note = COMPETE_NOTE
    row.version = int(row.version or 1) + 1
    row.updated_at = utcnow()
    db.flush()
    return ok(metric_vo(row))


@router.delete("/metric/{metric_id}")
def disable_metric(
    metric_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_compete_metric(db, tenant_id, actor.id)
    row = find_metric(db, tenant_id, metric_id)
    if row is None:
        return fail(1500, "指标不存在")
    if row.metric_code == COMPETE_CODE:
        return fail(1153, COMPETE_LOCK_MSG)
    row.status = "DISABLED"
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.post("/metric/bind-position")
def bind_position_metrics(
    body: PositionBindBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    ensure_compete_metric(db, tenant_id, actor.id)
    position = body.positionCode.strip()
    if not position:
        return fail(1001, "岗位编码必填")
    seen: set[int] = set()
    chosen: list[tuple[PerfMetric, float | None, Decimal]] = []
    total = ZERO
    for item in body.metricBindings:
        if item.metricId in seen:
            return fail(1001, "指标重复绑定")
        seen.add(item.metricId)
        metric = find_metric(db, tenant_id, item.metricId)
        if metric is None:
            return fail(1001, "指标不存在")
        effective = q2(metric.weight if item.weightOverride is None else item.weightOverride)
        total += effective
        chosen.append((metric, item.weightOverride, effective))
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if total != HUNDRED:
        shown = f"{total:.2f}"
        return fail(
            1154,
            f"该岗位指标集权重合计 {shown}%，须 = 100%",
            {"positionCode": position, "totalWeight": float(total)},
        )
    existing = db.scalars(
        select(PerfPositionBind).where(
            PerfPositionBind.deleted == 0,
            PerfPositionBind.tenant_id == tenant_id,
            PerfPositionBind.position_code == position,
        )
    ).all()
    now = utcnow()
    for old in existing:
        old.deleted = 1
        old.updated_at = now
    for metric, override, _effective in chosen:
        db.add(
            PerfPositionBind(
                position_code=position,
                metric_id=metric.id,
                weight_override=None if override is None else float(q2(override)),
                created_by=actor.id,
                tenant_id=tenant_id,
            )
        )
    db.flush()
    return ok({"positionCode": position, "boundCount": len(chosen), "totalWeight": float(total)})


from app.exam_paper import router as exam_paper_router

router.include_router(exam_paper_router)
