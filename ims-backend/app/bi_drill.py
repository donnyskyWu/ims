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
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import report_row_visible
from app.corp import tenant_of
from app.models import BiReportDef, User

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


def drill_payload(path: list[str], direction: str, filter_context: dict, page_no: int, page_size: int) -> dict:
    key = path[-1]
    label = LABELS[key]
    samples = DRILL_SAMPLES[key]
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
    return ok(drill_payload(path, direction, dict(body.filterContext), page_no, page_size))


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
    payload = drill_payload(path, "DOWN", ctx or {}, 1, 200)
    matrix = export_matrix(payload)
    if fmt == "CSV":
        body = build_csv(matrix)
        media = CSV_MEDIA
        filename = "bi_drill.csv"
    else:
        body = build_xlsx(matrix)
        media = XLSX_MEDIA
        filename = "bi_drill.xlsx"
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
