"""BI-002 多维下钻。

维度白名单只有《全局开发规范》DrillDimension 六枚举。
契约示例里的「部门→团队→人」「年→月→日」层级名不在这六枚举内，不另造 dimensionKey。
可逐级下钻的链是「自助六维」：平台→账号→场次→人员→日期→主体。
「平台→账号→场次」是该链的合法前缀，对应契约示例的第一条。
"""

from __future__ import annotations

import csv
import io
import json
import secrets
import time
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import report_row_visible
from app.corp import tenant_of
from app.models import BiQueryLog, BiReportDef, User

router = APIRouter(tags=["bi-drill"])

DRILL_CHAIN: list[tuple[str, str]] = [
    ("PLATFORM", "平台"),
    ("ACCOUNT", "账号"),
    ("SESSION", "场次"),
    ("PERSON", "人员"),
    ("DATE", "日期"),
    ("SUBJECT", "主体"),
]

# 第二条只覆盖契约示例「平台→账号→场次」，键必须是六枚举的前缀。
DRILL_TREES: list[tuple[str, list[tuple[str, str]]]] = [
    ("自助六维", DRILL_CHAIN),
    ("平台→账号→场次", DRILL_CHAIN[:3]),
]

DRILL_SAMPLES: dict[str, list[tuple[str, int, int]]] = {
    "PLATFORM": [("抖音", 186400, 621), ("视频号", 412800, 1376)],
    "ACCOUNT": [("神鱼官方", 120000, 400), ("神鱼精选", 66400, 221)],
    "SESSION": [("LS-20260928-01", 42000, 140), ("LS-20260929-02", 38000, 126)],
    "PERSON": [("主播-林晓", 28000, 90), ("主播-周宁", 14000, 50)],
    "DATE": [("2026-09-28", 15000, 48), ("2026-09-29", 13000, 42)],
    "SUBJECT": [("神鱼文化", 15000, 48)],
}

LABELS = {key: label for key, label in DRILL_CHAIN}
# 样本值归属的平台。筛选 PLATFORM 时只留下这一侧的行。
PLATFORM_LINEAGE = {
    "抖音": "抖音",
    "视频号": "视频号",
    "神鱼官方": "抖音",
    "神鱼精选": "抖音",
    "LS-20260928-01": "抖音",
    "LS-20260929-02": "抖音",
    "主播-林晓": "抖音",
    "主播-周宁": "抖音",
    "2026-09-28": "抖音",
    "2026-09-29": "抖音",
    "神鱼文化": "抖音",
}
# 本地桩不真等 30 秒。日期跨度（含首尾）是 BR-204 / V3-B6 的可重复触发条件。
SPAN_ASYNC_DAYS = 180
SPAN_TERMINATE_DAYS = 366
ASYNC_STUB_MS = 10000
TERMINATED_MS = 30001
OVER_30S_MS = 30000
ASYNC_MSG = "查询超过 10 秒已转异步（V3-B6）"
TERMINATE_MSG = "查询超 30 秒已终止（BR-204），建议缩小筛选范围"
EXPORT_TTL_SEC = 60
XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MEDIA = "text/csv; charset=utf-8"
_EXPORTS: dict[str, tuple[float, bytes, str, str, int]] = {}


class DrillBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportId: int | None = None
    dashboardId: int | None = None
    drillPath: list[str] = Field(default_factory=list)
    direction: str = "DOWN"
    filterContext: dict[str, str | int | float] = Field(default_factory=dict)
    pageNo: int = 1
    pageSize: int = 20


class CellDrillBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportId: int
    cellDimensions: dict[str, str | int | float] = Field(default_factory=dict)
    drillToDetail: bool = False


def tree_payload() -> dict:
    trees = []
    for name, levels in DRILL_TREES:
        trees.append(
            {
                "treeName": name,
                "levels": [
                    {"level": index + 1, "dimensionKey": key, "dimensionLabel": label}
                    for index, (key, label) in enumerate(levels)
                ],
            }
        )
    return {"trees": trees}


def path_legal(path: list[str]) -> bool:
    if not path:
        return False
    for _, levels in DRILL_TREES:
        keys = [key for key, _ in levels]
        if path == keys[: len(path)]:
            return True
    return False


def normalize_path(raw: list[str]) -> list[str]:
    return [str(item).strip() for item in raw if str(item).strip()]


def guard_report(db: Session, request: Request, actor: User, report_id: int | None):
    if report_id is None:
        return None
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return fail(1008, "无权查看该报表")
    scope = getattr(request.state, "scope", None)
    if not report_row_visible(db, row, actor, scope):
        return fail(1008, "无权查看该报表")
    return None


def guard_targets(db: Session, request: Request, actor: User, report_id: int | None, dashboard_id: int | None):
    blocked = guard_report(db, request, actor, report_id)
    if blocked is not None:
        return blocked
    if dashboard_id is not None and dashboard_id != report_id:
        return guard_report(db, request, actor, dashboard_id)
    return None


def filtered_samples(key: str, filter_context: dict) -> list[tuple[str, int, int]]:
    rows = list(DRILL_SAMPLES[key])
    platform = str(filter_context.get("PLATFORM") or "").strip()
    if platform:
        rows = [row for row in rows if PLATFORM_LINEAGE.get(row[0]) == platform]
    date_from = str(filter_context.get("dateFrom") or "").strip()[:10]
    date_to = str(filter_context.get("dateTo") or "").strip()[:10]
    if key == "DATE" and len(date_from) == 10 and len(date_to) == 10:
        rows = [row for row in rows if date_from <= row[0] <= date_to]
    return rows


def drill_payload(path: list[str], direction: str, filter_context: dict, page_no: int, page_size: int) -> dict:
    key = path[-1]
    label = LABELS[key]
    samples = filtered_samples(key, filter_context)
    start = max(0, (page_no - 1) * page_size)
    page = samples[start : start + page_size]
    rows = [
        {"dimensionKey": key, "dimensionValue": value, "gmv": gmv, "orders": orders}
        for value, gmv, orders in page
    ]
    return {
        "queryMode": "SYNC",
        "costMs": 12,
        "columns": [
            {"fieldKey": "dimensionValue", "fieldLabel": label, "dataType": "DIMENSION"},
            {"fieldKey": "gmv", "fieldLabel": "GMV", "dataType": "METRIC"},
            {"fieldKey": "orders", "fieldLabel": "订单数", "dataType": "METRIC"},
        ],
        "rows": rows,
        "total": len(samples),
        "cacheHit": True,
        "dataAsOf": "2026-10-03T14:00:00+08:00",
        "drillPath": path,
        "direction": direction,
        "filterContext": filter_context,
        "dimensionKey": key,
        "dimensionLabel": label,
        "dataset": "METRIC_LIB",
    }


def span_status(filter_context: dict) -> str:
    """NONE 未带日期；SYNC 可同步；ASYNC 超过半年；TERMINATE 超过一年；BAD 日期无效。"""
    raw_from = str(filter_context.get("dateFrom") or "").strip()[:10]
    raw_to = str(filter_context.get("dateTo") or "").strip()[:10]
    if not raw_from and not raw_to:
        return "NONE"
    if len(raw_from) != 10 or len(raw_to) != 10:
        return "BAD"
    try:
        start = datetime.strptime(raw_from, "%Y-%m-%d").date()
        end = datetime.strptime(raw_to, "%Y-%m-%d").date()
    except ValueError:
        return "BAD"
    if end < start:
        return "BAD"
    days = (end - start).days + 1
    if days > SPAN_TERMINATE_DAYS:
        return "TERMINATE"
    if days > SPAN_ASYNC_DAYS:
        return "ASYNC"
    return "SYNC"


def report_label(db: Session, actor: User, report_id: int | None) -> str:
    if not report_id:
        return "预览与下钻"
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_of(actor):
        return "预览与下钻"
    return (row.report_name or "预览与下钻")[:128]


def record_bi_query(
    db: Session,
    actor: User,
    report_id: int | None,
    report_name: str,
    query_kind: str,
    query_mode: str,
    cost_ms: float,
    result_rows: int,
) -> BiQueryLog:
    row = BiQueryLog(
        report_id=int(report_id or 0),
        report_name=(report_name or "预览与下钻")[:128],
        query_kind=(query_kind or "DRILL")[:16],
        query_mode=(query_mode or "SYNC")[:16],
        cost_ms=float(cost_ms or 0),
        result_rows=int(result_rows or 0),
        query_user_id=actor.id,
        tenant_id=tenant_of(actor),
    )
    db.add(row)
    db.flush()
    return row


def async_payload(row: BiQueryLog, path: list[str], filter_context: dict, report_name: str) -> dict:
    key = path[-1] if path else "PLATFORM"
    return {
        "queryMode": "ASYNC",
        "taskId": f"BQ{row.id}",
        "message": ASYNC_MSG,
        "reportTitle": report_name,
        "costMs": ASYNC_STUB_MS,
        "columns": [],
        "rows": [],
        "total": 0,
        "cacheHit": False,
        "dataAsOf": "2026-10-03T14:00:00+08:00",
        "drillPath": path,
        "filterContext": filter_context,
        "dimensionKey": key,
        "dimensionLabel": LABELS.get(key, key),
        "dataset": "METRIC_LIB",
    }


def span_response(
    db: Session,
    actor: User,
    report_id: int | None,
    report_name: str,
    query_kind: str,
    path: list[str],
    filter_context: dict,
):
    status = span_status(filter_context)
    if status == "BAD":
        return fail(1001, "筛选日期范围无效")
    if status == "TERMINATE":
        record_bi_query(db, actor, report_id, report_name, query_kind, "TERMINATED", TERMINATED_MS, 0)
        return fail(1194, TERMINATE_MSG)
    if status == "ASYNC":
        row = record_bi_query(db, actor, report_id, report_name, query_kind, "ASYNC", ASYNC_STUB_MS, 0)
        return ok(async_payload(row, path, filter_context, report_name))
    return None


def parse_filter_context(raw: str) -> tuple[dict | None, object | None]:
    if not raw.strip():
        return {}, None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, fail(1001, "filterContext 不是合法 JSON")
    if not isinstance(parsed, dict):
        return None, fail(1001, "filterContext 须为对象")
    return parsed, None


def export_matrix(payload: dict) -> list[list[str]]:
    columns = payload["columns"]
    header = [str(col["fieldLabel"]) for col in columns]
    body = []
    for row in payload["rows"]:
        body.append([str(row.get(col["fieldKey"], "")) for col in columns])
    return [header, *body]


def build_csv(rows: list[list[str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def build_xlsx(rows: list[list[str]]) -> bytes:
    from app.dc_trace import build_xlsx as dc_build_xlsx

    return dc_build_xlsx(rows)


def purge_exports(now: float) -> None:
    dead = [key for key, item in _EXPORTS.items() if item[0] < now]
    for key in dead:
        _EXPORTS.pop(key, None)


def issue_export(actor_id: int, body: bytes, media: str, filename: str) -> dict:
    now = time.time()
    purge_exports(now)
    token = secrets.token_urlsafe(24)
    _EXPORTS[token] = (now + EXPORT_TTL_SEC, body, media, filename, actor_id)
    return {
        "downloadUrl": f"/admin-api/ims/bi/query/export/file?token={token}",
        "expiresIn": EXPORT_TTL_SEC,
        "fileName": filename,
    }


@router.get("/dimension-tree")
def dimension_tree(_: User = Depends(current_user)):
    return ok(tree_payload())


@router.post("/drill")
def query_drill(
    body: DrillBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    blocked = guard_targets(db, request, actor, body.reportId, body.dashboardId)
    if blocked is not None:
        return blocked
    direction = (body.direction or "").strip().upper()
    if direction not in {"DOWN", "UP"}:
        return fail(1001, "direction 仅支持 DOWN 或 UP")
    path = normalize_path(body.drillPath)
    if not path:
        return fail(1001, "下钻路径为空")
    if not path_legal(path):
        return fail(1195, "已到达预定义层级末端或路径非法")
    page_no = body.pageNo if body.pageNo and body.pageNo > 0 else 1
    page_size = body.pageSize if body.pageSize and body.pageSize > 0 else 20
    page_size = min(page_size, 200)
    ctx = {str(key): "" if value is None else str(value) for key, value in body.filterContext.items()}
    name = report_label(db, actor, body.reportId)
    blocked_span = span_response(db, actor, body.reportId, name, "DRILL", path, ctx)
    if blocked_span is not None:
        return blocked_span
    started = time.perf_counter()
    payload = drill_payload(path, direction, ctx, page_no, page_size)
    payload["costMs"] = max(round((time.perf_counter() - started) * 1000, 1), 1)
    record_bi_query(db, actor, body.reportId, name, "DRILL", "SYNC", payload["costMs"], payload["total"])
    return ok(payload)


@router.post("/cell-drill")
def cell_drill(
    body: CellDrillBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    blocked = guard_report(db, request, actor, body.reportId)
    if blocked is not None:
        return blocked
    dims = {str(key): "" if value is None else str(value) for key, value in body.cellDimensions.items()}
    session_code = dims.get("SESSION", "")
    if body.drillToDetail and session_code:
        return ok(
            {
                "jumpType": "MODULE_DETAIL",
                "jumpUrl": f"/ims/live/sessions?sessionCode={quote(session_code)}",
                "jumpParams": {"sessionCode": session_code},
            }
        )
    if dims.get("ACCOUNT"):
        entry_type = "ACCOUNT"
        keyword = dims["ACCOUNT"]
    else:
        entry_type = "PLATFORM"
        keyword = dims.get("PLATFORM") or dims.get("dimensionValue") or ""
    return ok(
        {
            "jumpType": "DC_TRACE",
            "jumpUrl": f"/ims/dc/trace?entryType={quote(entry_type)}&keyword={quote(keyword)}",
            "jumpParams": {"entryType": entry_type, "keyword": keyword},
        }
    )


@router.get("/export")
def query_export(
    request: Request,
    reportId: int | None = None,
    dashboardId: int | None = None,
    drillPath: str = "",
    filterContext: str = "",
    format: str = "XLSX",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    blocked = guard_targets(db, request, actor, reportId, dashboardId)
    if blocked is not None:
        return blocked
    fmt = (format or "").strip().upper()
    if fmt not in {"XLSX", "CSV"}:
        return fail(1001, "format 仅支持 XLSX 或 CSV")
    path = normalize_path(drillPath.split(","))
    if not path:
        path = ["PLATFORM"]
    if not path_legal(path):
        return fail(1195, "已到达预定义层级末端或路径非法")
    ctx, err = parse_filter_context(filterContext)
    if err is not None:
        return err
    ctx = {str(key): "" if value is None else str(value) for key, value in (ctx or {}).items()}
    name = report_label(db, actor, reportId)
    blocked_span = span_response(db, actor, reportId, name, "EXPORT", path, ctx)
    if blocked_span is not None:
        return blocked_span
    payload = drill_payload(path, "DOWN", ctx, 1, 200)
    matrix = export_matrix(payload)
    if fmt == "CSV":
        body = build_csv(matrix)
        media = CSV_MEDIA
        filename = "bi_drill.csv"
    else:
        body = build_xlsx(matrix)
        media = XLSX_MEDIA
        filename = "bi_drill.xlsx"
    record_bi_query(db, actor, reportId, name, "EXPORT", "SYNC", 1, payload["total"])
    return ok(issue_export(actor.id, body, media, filename))


@router.get("/export/file")
def query_export_file(token: str, actor: User = Depends(current_user)):
    now = time.time()
    purge_exports(now)
    item = _EXPORTS.get(token)
    if item is None or item[0] < now:
        return fail(1002, "下载链接已过期")
    if item[4] != actor.id:
        return fail(1008, "无数据权限")
    _expires, body, media, filename, _user_id = item
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def can_view_bi_perf(db: Session, actor: User) -> bool:
    from app.live import role_tags

    tags = role_tags(db, actor)
    return bool(tags & {"r1", "r9", "sys:admin"})


@router.get("/perf-stats")
def query_perf_stats(
    dateRange: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_view_bi_perf(db, actor):
        return fail(1008, "无数据权限")
    from app.dc_trace import default_perf_parts, parse_range_param, percentile_ms, utc_bounds

    parts, error = parse_range_param(dateRange)
    if error:
        return fail(1001, error)
    if parts is None:
        parts = default_perf_parts()
    start, end = utc_bounds(parts)
    rows = list(
        db.scalars(
            select(BiQueryLog)
            .where(
                BiQueryLog.tenant_id == tenant_of(actor),
                BiQueryLog.created_at >= start,
                BiQueryLog.created_at <= end,
            )
            .order_by(BiQueryLog.id.asc())
        ).all()
    )
    costs = [float(row.cost_ms or 0) for row in rows]
    buckets: dict[int, dict] = {}
    for row in rows:
        if float(row.cost_ms or 0) < OVER_30S_MS:
            continue
        bucket = buckets.get(int(row.report_id or 0))
        if bucket is None:
            bucket = {
                "reportId": int(row.report_id or 0),
                "reportName": row.report_name or "预览与下钻",
                "costs": [],
            }
            buckets[int(row.report_id or 0)] = bucket
        if row.report_name:
            bucket["reportName"] = row.report_name
        bucket["costs"].append(float(row.cost_ms or 0))
    slow_reports = [
        {
            "reportId": bucket["reportId"],
            "reportName": bucket["reportName"],
            "avgCostMs": round(sum(bucket["costs"]) / len(bucket["costs"]), 1),
            "queryCount": len(bucket["costs"]),
        }
        for bucket in buckets.values()
    ]
    slow_reports.sort(key=lambda item: (-item["avgCostMs"], item["reportId"]))
    avg = round(sum(costs) / len(costs), 1) if costs else 0.0
    return ok(
        {
            "totalQueries": len(rows),
            "avgCostMs": avg,
            "p95CostMs": percentile_ms(costs, 95),
            "over30sCount": sum(1 for cost in costs if cost >= OVER_30S_MS),
            "asyncConvertedCount": sum(1 for row in rows if row.query_mode == "ASYNC"),
            "topSlowReports": slow_reports[:20],
        }
    )
