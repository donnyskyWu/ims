"""BI0 指标管理（W9-6 · FR-M6-001 首片）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiMetric, User

router = APIRouter(prefix="/bi/metric", tags=["bi-metric"])

BJ = timezone(timedelta(hours=8))


class MetricBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricName: str
    metricType: str = "BASIC"
    category: str = "内容表现"
    calcFreq: str = "DAY"
    formula: str = ""


class MetricUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricName: str | None = None
    metricType: str | None = None
    category: str | None = None
    calcFreq: str | None = None
    status: str | None = None
    formula: str | None = None


class MetricPreviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sampleDate: str = "2026-09-30"


class AnalysisRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricIds: list[int] = Field(default_factory=list)
    ipGroupId: int | None = None
    dateStart: str = ""
    dateEnd: str = ""
    view: str = "DETAIL"


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_metric_code(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(BiMetric).where(BiMetric.deleted == 0, BiMetric.tenant_id == tenant_id)
    )
    seq = int(count or 0) + 1
    return f"M{seq:05d}"


def metric_vo(row: BiMetric, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "metricCode": row.metric_code,
        "metricName": row.metric_name,
        "metricType": row.metric_type,
        "category": row.category,
        "calcFreq": row.calc_freq,
        "status": row.status,
        "formula": row.formula or "",
        "refCount": int(row.ref_count or 0),
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }


@router.get("/list")
def metric_list(
    keyword: str | None = None,
    metricType: str | None = None,
    category: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    q = select(BiMetric).where(BiMetric.deleted == 0, BiMetric.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((BiMetric.metric_name.like(kw)) | (BiMetric.metric_code.like(kw)))
    if metricType:
        q = q.where(BiMetric.metric_type == metricType.strip().upper())
    if category:
        q = q.where(BiMetric.category == category.strip())
    if status:
        q = q.where(BiMetric.status == status.strip().upper())
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(BiMetric.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([metric_vo(r, names) for r in rows], total, page_no, size)


@router.post("")
def metric_create(body: MetricBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    name = body.metricName.strip()
    if not name:
        return fail(1001, "指标名称必填")
    mtype = body.metricType.strip().upper() or "BASIC"
    if mtype not in {"BASIC", "COMPOSITE"}:
        return fail(1001, "指标类型无效")
    now = utcnow()
    row = BiMetric(
        metric_code=next_metric_code(db, tenant_id),
        metric_name=name,
        metric_type=mtype,
        category=body.category.strip() or "内容表现",
        calc_freq=body.calcFreq.strip().upper() or "DAY",
        status="ENABLED",
        formula=body.formula.strip(),
        ref_count=0,
        creator_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.creator_id])
    return ok(metric_vo(row, names))


@router.put("/{metric_id}")
def metric_update(
    metric_id: int,
    body: MetricUpdateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiMetric, metric_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    if body.metricName is not None:
        name = body.metricName.strip()
        if not name:
            return fail(1001, "指标名称必填")
        row.metric_name = name
    if body.metricType is not None:
        mtype = body.metricType.strip().upper()
        if mtype not in {"BASIC", "COMPOSITE"}:
            return fail(1001, "指标类型无效")
        row.metric_type = mtype
    if body.category is not None:
        row.category = body.category.strip() or row.category
    if body.calcFreq is not None:
        row.calc_freq = body.calcFreq.strip().upper() or row.calc_freq
    if body.status is not None:
        st = body.status.strip().upper()
        if st not in {"ENABLED", "DISABLED"}:
            return fail(1001, "状态无效")
        row.status = st
    if body.formula is not None:
        row.formula = body.formula.strip()
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    return ok(metric_vo(row, names))


@router.delete("/{metric_id}")
def metric_delete(metric_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = db.get(BiMetric, metric_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    if int(row.ref_count or 0) > 0:
        return fail(1262, "指标已被引用，不可删除")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok({"id": metric_id})


def mock_series(metric: BiMetric, date_start: str, date_end: str) -> list[dict]:
    base = 80.0 + (hash(metric.metric_code) % 40)
    return [
        {"date": date_start[:10] if date_start else "2026-09-01", "value": round(base, 1)},
        {"date": date_end[:10] if date_end else "2026-09-30", "value": round(base * 1.12, 1)},
    ]


def analyze_metric_row(metric: BiMetric, date_start: str, date_end: str, ip_group_id: int | None) -> dict:
    value = 128.6 if metric.metric_type == "BASIC" else 256.3
    value += (ip_group_id or 0) % 17
    return {
        "metricId": metric.id,
        "metricCode": metric.metric_code,
        "metricName": metric.metric_name,
        "value": round(value, 1),
        "unit": "次" if "互动" in metric.metric_name else "个",
        "dateStart": date_start,
        "dateEnd": date_end,
    }


@router.get("/{metric_id}/analyze")
def metric_analyze(
    metric_id: int,
    dateStart: str = "",
    dateEnd: str = "",
    ipGroupId: int | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiMetric, metric_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    if row.status != "ENABLED":
        return fail(1001, "指标未启用")
    detail = analyze_metric_row(row, dateStart, dateEnd, ipGroupId)
    return ok({"view": "DETAIL", "rows": [detail], "series": mock_series(row, dateStart, dateEnd)})


@router.post("/analysis/run")
def metric_analysis_run(
    body: AnalysisRunBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not body.metricIds:
        return fail(1001, "请至少选择一个指标")
    tenant_id = tenant_of(actor)
    rows_out: list[dict] = []
    series: list[dict] = []
    for mid in body.metricIds:
        row = db.get(BiMetric, mid)
        if row is None or row.deleted or row.tenant_id != tenant_id:
            return fail(1504, "资源不可用")
        if row.status != "ENABLED":
            return fail(1001, f"指标 {row.metric_name} 未启用")
        rows_out.append(analyze_metric_row(row, body.dateStart, body.dateEnd, body.ipGroupId))
        series.append({"metricCode": row.metric_code, "points": mock_series(row, body.dateStart, body.dateEnd)})
    view = body.view.strip().upper() or "DETAIL"
    if view not in {"DETAIL", "TREND"}:
        return fail(1001, "view 无效")
    return ok(
        {
            "view": view,
            "rows": rows_out,
            "series": series if view == "TREND" else [],
            "note": "分析占位 · 未接 DW",
        }
    )


@router.post("/{metric_id}/preview")
def metric_preview(
    metric_id: int,
    body: MetricPreviewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiMetric, metric_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    value = 128.6 if row.metric_type == "BASIC" else 256.3
    return ok(
        {
            "metricCode": row.metric_code,
            "metricName": row.metric_name,
            "sampleDate": body.sampleDate,
            "value": value,
            "unit": "次" if "互动" in row.metric_name else "个",
            "note": "试算占位 · 未接 DW",
        }
    )
