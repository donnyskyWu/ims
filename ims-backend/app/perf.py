"""绩效考核 PERF-001 考核方案（W9-2 首片 · OPS M3 模板对齐）。"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import ExamQuestion, PerfRecord, PerfScheme, User

router = APIRouter(prefix="/perf", tags=["perf"])

BJ = timezone(timedelta(hours=8))
PERIOD_TYPES = frozenset({"WEEKLY", "MONTHLY", "QUARTERLY", "HALF_YEAR", "YEAR", "CUSTOM"})
SCHEME_STATUSES = frozenset({"ACTIVE", "INACTIVE"})
RECORD_STATUSES = frozenset(
    {"DRAFT", "CALCULATING", "CALCULATED", "REVIEWED", "CONFIRMED", "ISSUED", "REJECTED"}
)
RESULT_STATUSES = frozenset({"CALCULATED", "REVIEWED", "CONFIRMED", "ISSUED"})
EXPORT_STATUSES = frozenset({"CONFIRMED", "ISSUED"})
GRADE_THRESHOLDS = ((85, "S"), (70, "A"), (60, "B"), (0, "C"))
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


def result_vo(db: Session, row: PerfRecord, scheme: PerfScheme | None = None) -> dict:
    base = record_vo(db, row, scheme)
    base["grade"] = grade_of(row.total_score)
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


@router.get("/result/list")
def result_list(
    targetUserId: int | None = None,
    periodType: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(PerfRecord).where(
        PerfRecord.deleted == 0,
        PerfRecord.tenant_id == tenant_id,
        PerfRecord.status.in_(RESULT_STATUSES),
    )
    if targetUserId:
        stmt = stmt.where(PerfRecord.target_user_id == targetUserId)
    if periodType:
        stmt = stmt.where(PerfRecord.period_type == periodType)
    if status:
        if status not in RESULT_STATUSES:
            return fail(1001, "status 无效")
        stmt = stmt.where(PerfRecord.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(PerfRecord.total_score.desc(), PerfRecord.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    scheme_ids = {row.scheme_id for row in rows if row.scheme_id}
    schemes = {}
    if scheme_ids:
        for scheme in db.scalars(
            select(PerfScheme).where(PerfScheme.id.in_(scheme_ids), PerfScheme.deleted == 0)
        ).all():
            schemes[scheme.id] = scheme
    return paged([result_vo(db, row, schemes.get(row.scheme_id)) for row in rows], total, page_no, size)


@router.get("/result/export")
def result_export(
    targetUserId: int | None = None,
    periodType: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = select(PerfRecord).where(
        PerfRecord.deleted == 0,
        PerfRecord.tenant_id == tenant_id,
        PerfRecord.status.in_(EXPORT_STATUSES),
    )
    if targetUserId:
        stmt = stmt.where(PerfRecord.target_user_id == targetUserId)
    if periodType:
        stmt = stmt.where(PerfRecord.period_type == periodType)
    if status:
        if status not in EXPORT_STATUSES:
            return fail(1001, "status 无效")
        stmt = stmt.where(PerfRecord.status == status)
    rows = list(
        db.scalars(
            stmt.order_by(PerfRecord.total_score.desc(), PerfRecord.id.desc()).limit(5000)
        ).all()
    )
    scheme_ids = {row.scheme_id for row in rows if row.scheme_id}
    schemes: dict[int, PerfScheme] = {}
    if scheme_ids:
        for scheme in db.scalars(
            select(PerfScheme).where(PerfScheme.id.in_(scheme_ids), PerfScheme.deleted == 0)
        ).all():
            schemes[scheme.id] = scheme
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
        headers={"Content-Disposition": 'attachment; filename="perf_results.csv"'},
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
    count = db.scalar(
        select(func.count())
        .select_from(ExamQuestion)
        .where(ExamQuestion.deleted == 0, ExamQuestion.tenant_id == tenant_id)
    )
    if count:
        return
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
    for qno, stem, domain, qtype, score, refs in seeds:
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
