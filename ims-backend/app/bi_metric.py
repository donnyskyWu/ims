"""BI0 指标管理（W9-6 · FR-M6-001 首片）。"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_metric_formula import formula_error
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiMetric, User

router = APIRouter(prefix="/bi/metric", tags=["bi-metric"])

BJ = timezone(timedelta(hours=8))


class ConditionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    field: str = "stat_date"
    op: str = "介于"
    value: str = ""
    param: bool = False


class MetricBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricName: str
    metricCode: str = ""
    metricType: str = "BASIC"
    category: str = "内容表现"
    calcFreq: str = "DAY"
    formula: str = ""
    unit: str = ""
    dataSource: str = ""
    calcMethod: str = ""
    calcField: str = ""
    summaryField: str = ""
    conditions: list[ConditionItem] = Field(default_factory=list)


class MetricUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricName: str | None = None
    metricCode: str | None = None
    metricType: str | None = None
    category: str | None = None
    calcFreq: str | None = None
    status: str | None = None
    formula: str | None = None
    unit: str | None = None
    dataSource: str | None = None
    calcMethod: str | None = None
    calcField: str | None = None
    summaryField: str | None = None
    conditions: list[ConditionItem] | None = None


class MetricPreviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sampleDate: str = "2026-09-30"


class DraftPreviewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    formula: str = ""
    dataSource: str = ""
    calcMethod: str = "SUM"
    calcField: str = "play_count"
    summaryField: str = "ip_group_name"
    conditions: list[ConditionItem] = Field(default_factory=list)


class AnalysisRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    metricIds: list[int] = Field(default_factory=list)
    ipGroupId: int | None = None
    ipGroupName: str = ""
    dateStart: str = ""
    dateEnd: str = ""
    view: str = "DETAIL"
    pageNo: int = 1
    pageSize: int = 20


FREQS = {"DAY", "REALTIME", "DAILY", "WEEKLY", "MONTHLY"}
SOURCES = {"oa_content_metric", "oa_content", "oa_ip_group", "oa_platform_account", "oa_live_session"}
METHODS = {"COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT_COUNT"}
FIELDS = {"ip_group_name", "play_count", "interaction_count", "stat_date", "platform_code"}
CODE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
SAFE_VALUE = re.compile(r"^[0-9A-Za-z_ \-:~.,]{0,64}$")


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


def load_conditions(raw: str | None) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "field": str(item.get("field") or ""),
                "op": str(item.get("op") or ""),
                "value": str(item.get("value") or ""),
                "param": bool(item.get("param")),
            }
        )
    return out


def dump_conditions(items: list[ConditionItem]) -> str:
    return json.dumps(
        [{"field": i.field, "op": i.op, "value": i.value, "param": bool(i.param)} for i in items],
        ensure_ascii=False,
    )


def name_error(name: str) -> str | None:
    if not name:
        return "指标名称必填"
    if len(name) > 50:
        return "指标名称不超过 50 字"
    return None


def code_error(db: Session, tenant_id: int, code: str, ignore_id: int | None = None) -> str | None:
    if not code:
        return None
    if not CODE_RE.match(code):
        return "指标编码需以字母开头，仅含字母数字下划线"
    taken = db.scalar(
        select(BiMetric).where(
            BiMetric.deleted == 0,
            BiMetric.tenant_id == tenant_id,
            BiMetric.metric_code == code,
        )
    )
    if taken is not None and taken.id != ignore_id:
        return "编码已存在"
    return None


def freq_error(freq: str) -> str | None:
    if freq and freq not in FREQS:
        return "计算频率无效"
    return None


def build_select_sql(
    data_source: str,
    calc_method: str,
    calc_field: str,
    summary_field: str,
    conditions: list[ConditionItem],
) -> tuple[str | None, str | None]:
    source = (data_source or "oa_content_metric").strip()
    method = (calc_method or "SUM").strip().upper()
    field = (calc_field or "play_count").strip()
    summary = (summary_field or "ip_group_name").strip()
    if source not in SOURCES:
        return None, "数据源不在白名单"
    if method not in METHODS:
        return None, "计算方式无效"
    if field not in FIELDS or summary not in FIELDS:
        return None, "计算字段不在白名单"
    if method == "COUNT":
        agg = "COUNT(*)"
    elif method == "DISTINCT_COUNT":
        agg = f"COUNT(DISTINCT {field})"
    else:
        agg = f"{method}({field})"
    wheres = ["tenant_id = :tenantId"]
    for cond in conditions:
        col = (cond.field or "").strip()
        if col not in FIELDS:
            return None, "条件字段不在白名单"
        if cond.param:
            wheres.append(f"{col} = :p_{col}")
            continue
        value = (cond.value or "").strip()
        if not value:
            continue
        if not SAFE_VALUE.match(value):
            return None, "条件值含非法字符"
        wheres.append(f"{col} = '{value}'")
    sql = (
        f"SELECT {summary}, {agg} AS metric_value\n"
        f"FROM {source}\n"
        f"WHERE {' AND '.join(wheres)}\n"
        f"GROUP BY {summary}"
    )
    blocked = formula_error(sql)
    if blocked:
        return None, blocked
    return sql, None


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
        "unit": row.unit or "",
        "dataSource": row.data_source or "",
        "calcMethod": row.calc_method or "",
        "calcField": row.calc_field or "",
        "summaryField": row.summary_field or "",
        "conditions": load_conditions(row.conditions_json),
        "refCount": int(row.ref_count or 0),
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }


def apply_builder(row: BiMetric, body: MetricBody | MetricUpdateBody, *, partial: bool) -> None:
    if not partial or body.unit is not None:
        row.unit = (body.unit or "").strip()
    if not partial or body.dataSource is not None:
        row.data_source = (body.dataSource or "").strip()
    if not partial or body.calcMethod is not None:
        row.calc_method = (body.calcMethod or "").strip().upper()
    if not partial or body.calcField is not None:
        row.calc_field = (body.calcField or "").strip()
    if not partial or body.summaryField is not None:
        row.summary_field = (body.summaryField or "").strip()
    if not partial or body.conditions is not None:
        row.conditions_json = dump_conditions(body.conditions or [])


def filtered_metrics(
    db: Session,
    tenant_id: int,
    keyword: str | None,
    metric_type: str | None,
    category: str | None,
    status: str | None,
):
    q = select(BiMetric).where(BiMetric.deleted == 0, BiMetric.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((BiMetric.metric_name.like(kw)) | (BiMetric.metric_code.like(kw)))
    if metric_type:
        q = q.where(BiMetric.metric_type == metric_type.strip().upper())
    if category:
        q = q.where(BiMetric.category == category.strip())
    if status:
        q = q.where(BiMetric.status == status.strip().upper())
    return q.order_by(BiMetric.id.desc())


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
    page_no, size = page_args(pageNo, pageSize)
    stmt = filtered_metrics(db, tenant_id, keyword, metricType, category, status)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([metric_vo(r, names) for r in rows], total, page_no, size)


@router.get("/fields")
def metric_fields(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    """设计器字段列表只返回启用指标。停用后从这里消失。"""
    tenant_id = tenant_of(actor)
    rows = list(
        db.scalars(
            select(BiMetric)
            .where(BiMetric.deleted == 0, BiMetric.tenant_id == tenant_id, BiMetric.status == "ENABLED")
            .order_by(BiMetric.id.desc())
        ).all()
    )
    return ok(
        {
            "fields": [
                {
                    "metricCode": row.metric_code,
                    "metricName": row.metric_name,
                    "unit": row.unit or "",
                    "category": row.category,
                }
                for row in rows
            ]
        }
    )


@router.get("/export")
def metric_export(
    keyword: str | None = None,
    metricType: str | None = None,
    category: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = filtered_metrics(db, tenant_id, keyword, metricType, category, status)
    rows = list(db.scalars(stmt).all())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "指标名称", "指标编码", "类型", "分类", "数据源", "计算公式", "计算频率", "单位", "状态"])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.metric_name,
                row.metric_code,
                row.metric_type,
                row.category,
                row.data_source or "",
                row.formula or "",
                row.calc_freq,
                row.unit or "",
                "启用" if row.status == "ENABLED" else "停用",
            ]
        )
    return ok({"filename": "指标.csv", "csv": buf.getvalue(), "count": len(rows)})


@router.post("/formula/generate")
def metric_generate(body: DraftPreviewBody, _: User = Depends(current_user)):
    sql, err = build_select_sql(body.dataSource, body.calcMethod, body.calcField, body.summaryField, body.conditions)
    if err:
        return fail(1192 if "1192" in err else 1001, err)
    return ok({"formula": sql})


@router.post("/preview-draft")
def metric_preview_draft(body: DraftPreviewBody, _: User = Depends(current_user)):
    formula = body.formula.strip()
    if not formula:
        formula, err = build_select_sql(
            body.dataSource, body.calcMethod, body.calcField, body.summaryField, body.conditions
        )
        if err:
            return fail(1192 if err and "1192" in err else 1001, err or "无法生成公式")
    blocked = formula_error(formula or "")
    if blocked:
        return fail(1192, blocked)
    return ok(
        {
            "formula": formula,
            "rows": [
                {"ip_group_name": "电竞一组", "metric_value": 1284600},
                {"ip_group_name": "体育二组", "metric_value": 892400},
            ],
            "note": "",
        }
    )


@router.post("")
def metric_create(body: MetricBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    name = body.metricName.strip()
    bad_name = name_error(name)
    if bad_name:
        return fail(1001, bad_name)
    mtype = body.metricType.strip().upper() or "BASIC"
    if mtype not in {"BASIC", "COMPOSITE"}:
        return fail(1001, "指标类型无效")
    freq = body.calcFreq.strip().upper() or "DAY"
    bad_freq = freq_error(freq)
    if bad_freq:
        return fail(1001, bad_freq)
    code = body.metricCode.strip()
    bad_code = code_error(db, tenant_id, code)
    if bad_code:
        return fail(1001, bad_code)
    formula = body.formula.strip()
    blocked = formula_error(formula)
    if blocked:
        return fail(1192, blocked)
    now = utcnow()
    row = BiMetric(
        metric_code=code or next_metric_code(db, tenant_id),
        metric_name=name,
        metric_type=mtype,
        category=body.category.strip() or "内容表现",
        calc_freq=freq,
        status="ENABLED",
        formula=formula,
        ref_count=0,
        creator_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    apply_builder(row, body, partial=False)
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
    candidate = body.formula.strip() if body.formula is not None else (row.formula or "")
    blocked = formula_error(candidate)
    if blocked:
        return fail(1192, blocked)
    if body.metricName is not None:
        name = body.metricName.strip()
        bad_name = name_error(name)
        if bad_name:
            return fail(1001, bad_name)
        row.metric_name = name
    if body.metricCode is not None:
        code = body.metricCode.strip()
        bad_code = code_error(db, tenant_id, code, ignore_id=row.id)
        if bad_code:
            return fail(1001, bad_code)
        if code:
            row.metric_code = code
    if body.metricType is not None:
        mtype = body.metricType.strip().upper()
        if mtype not in {"BASIC", "COMPOSITE"}:
            return fail(1001, "指标类型无效")
        row.metric_type = mtype
    if body.category is not None:
        row.category = body.category.strip() or row.category
    if body.calcFreq is not None:
        freq = body.calcFreq.strip().upper() or row.calc_freq
        bad_freq = freq_error(freq)
        if bad_freq:
            return fail(1001, bad_freq)
        row.calc_freq = freq
    if body.status is not None:
        st = body.status.strip().upper()
        if st not in {"ENABLED", "DISABLED"}:
            return fail(1001, "状态无效")
        row.status = st
    if body.formula is not None:
        row.formula = candidate
    apply_builder(row, body, partial=True)
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


ANALYSIS_FROM = "2026-09-01"
ANALYSIS_TO = "2026-09-30"


def analysis_day(raw: str) -> str | None:
    text = (raw or "").strip()[:10]
    if not text:
        return ""
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text


def analysis_window(date_start: str, date_end: str) -> tuple[str, str, str] | tuple[None, None, str]:
    """返回 (起, 止, '')；日期边错误时前两项为 None，第三项为提示。"""
    start = analysis_day(date_start)
    end = analysis_day(date_end)
    if start is None or end is None:
        return None, None, "日期格式应为 yyyy-MM-dd"
    if bool(start) != bool(end):
        return None, None, "请同时填写开始和结束日期"
    if start and end and start > end:
        return None, None, "开始日期不能晚于结束日期"
    return start, end, ""


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
    blocked = formula_error(row.formula or "")
    if blocked:
        return fail(1192, blocked)
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
    start, end, date_error = analysis_window(body.dateStart, body.dateEnd)
    if date_error:
        return fail(1001, date_error)
    view = body.view.strip().upper() or "DETAIL"
    if view not in {"DETAIL", "TREND"}:
        return fail(1001, "view 无效")
    outside = bool(start and end and (end < ANALYSIS_FROM or start > ANALYSIS_TO))
    tenant_id = tenant_of(actor)
    found: list[BiMetric] = []
    for mid in body.metricIds:
        row = db.get(BiMetric, mid)
        if row is None or row.deleted or row.tenant_id != tenant_id:
            return fail(1504, "资源不可用")
        blocked = formula_error(row.formula or "")
        if blocked:
            return fail(1192, blocked)
        if row.status != "ENABLED":
            return fail(1001, f"指标 {row.metric_name} 未启用")
        found.append(row)
    if outside:
        return ok(
            {
                "view": view,
                "rows": [],
                "series": [],
                "note": "",
                "empty": True,
                "emptyReason": "当前日期下暂无分析数据",
            }
        )
    rows_out: list[dict] = []
    series: list[dict] = []
    for row in found:
        rows_out.append(analyze_metric_row(row, body.dateStart, body.dateEnd, body.ipGroupId))
        series.append({"metricCode": row.metric_code, "points": mock_series(row, body.dateStart, body.dateEnd)})
    return ok(
        {
            "view": view,
            "rows": rows_out,
            "series": series if view == "TREND" else [],
            "note": "分析占位 · 未接 DW",
            "empty": False,
            "emptyReason": "",
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
    blocked = formula_error(row.formula or "")
    if blocked:
        return fail(1192, blocked)
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
