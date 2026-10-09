"""BI 报表中心（M6 标准预览）+ 报表管理目录（W9-6 biList）。"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import primary_dept_id, report_row_visible, restrict_report_def
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiReportDef, User

router = APIRouter(prefix="/bi/report", tags=["bi-report"])

BJ = timezone(timedelta(hours=8))

REPORT_CATEGORIES = [
    {"code": "content", "name": "内容分析", "children": ["作品表现", "账号经营"]},
    {"code": "finance", "name": "经营财务", "children": ["成本效率", "ROI"]},
]


class ReportCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportName: str
    reportType: str = "REPORT"
    category: str = "内容分析"
    subCategory: str = ""


class ReportUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportName: str = ""
    layoutJson: dict | None = None


class ReportQueryBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportId: int | None = None
    compId: str = ""
    components: list[dict] = Field(default_factory=list)


class PreviewRunBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportId: int | None = None
    dateFrom: str = ""
    dateTo: str = ""
    ipGroupId: int | None = None
    platform: str = ""
    timeGrain: str = "DAY"


class PreviewDrillBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportId: int | None = None
    dimension: str = "platform"
    drillPath: list[str] = Field(default_factory=list)
    cellMetric: str = "gmv"


DATASETS = [
    {
        "code": "METRIC_LIB",
        "name": "指标库",
        "fields": [
            {"name": "metricName", "label": "指标名", "type": "string"},
            {"name": "metricValue", "label": "指标值", "type": "number"},
        ],
    },
    {
        "code": "CUSTOM_QUERY",
        "name": "已发布自定义查询",
        "fields": [
            {"name": "dim", "label": "维度", "type": "string"},
            {"name": "value", "label": "数值", "type": "number"},
        ],
    },
]

COMP_LIB = [
    {"type": "KPI", "name": "KPI 卡片", "defaultSize": {"w": 240, "h": 120}},
    {"type": "BAR", "name": "柱状图", "defaultSize": {"w": 480, "h": 280}},
    {"type": "LINE", "name": "折线图", "defaultSize": {"w": 480, "h": 280}},
    {"type": "TABLE", "name": "表格", "defaultSize": {"w": 640, "h": 320}},
]


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_report_no(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(BiReportDef).where(BiReportDef.deleted == 0, BiReportDef.tenant_id == tenant_id)
    )
    seq = int(count or 0) + 1
    return f"RPT-{seq:04d}"


def parse_layout(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def report_def_vo(row: BiReportDef, names: dict[int, str]) -> dict:
    layout = parse_layout(row.layout_json)
    return {
        "id": row.id,
        "reportNo": row.report_no,
        "reportName": row.report_name,
        "reportType": row.report_type,
        "category": row.category,
        "subCategory": row.sub_category,
        "status": row.status,
        "layoutMode": layout.get("layoutMode", "FREE"),
        "comps": layout.get("comps", []),
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }

STANDARD_REPORTS = [
    {
        "code": "unified-account",
        "title": "全平台账号视图",
        "desc": "八平台账号统一视图 · 粉丝/作品/互动横向对比",
        "tags": ["unified-account", "UX-M6 §4.1"],
    },
    {
        "code": "account-status",
        "title": "账号状态监控",
        "desc": "账号健康度与异常分布 · 异常原因归因",
        "tags": ["account-status", "UX-M6 §4.2"],
    },
    {
        "code": "video-output",
        "title": "短视频产出统计",
        "desc": "短视频产出量与互动表现 · 按 IP 组归因",
        "tags": ["video-output", "UX-M6 §4.3"],
    },
    {
        "code": "live-duration",
        "title": "直播时长统计",
        "desc": "作者 × 日期直播时长聚合（小时）",
        "tags": ["live-duration", "UX-M6 §4.4"],
    },
    {
        "code": "cost-allocation",
        "title": "账号成本分摊",
        "desc": "账号成本分摊至 IP 组 · 成本/GMV 效率口径",
        "tags": ["cost-allocation", "UX-M6 §4.5"],
    },
    {
        "code": "roi",
        "title": "ROI 分析报表",
        "desc": "IP 组 ROI = 营收 / 成本",
        "tags": ["roi", "UX-M6 §4.6"],
    },
    {
        "code": "team-config",
        "title": "IP 团队人员配置",
        "desc": "IP 团队人员配置与产能 · 人效口径见组织人效",
        "tags": ["team-config", "UX-M6 §4.7"],
    },
    {
        "code": "account-alert",
        "title": "账号异常预警",
        "desc": "账号异常预警清单 · 与预警中心同源去重",
        "tags": ["account-alert", "UX-M6 §4.8"],
    },
]

MOCK_ROWS = {
    "unified-account": [
        {"platform": "抖音", "accountName": "神鱼体育官方", "followerCount": 128000, "workCount": 342},
        {"platform": "视频号", "accountName": "神鱼精选", "followerCount": 86000, "workCount": 198},
    ],
    "roi": [
        {"ipGroupName": "电竞一组", "revenue": 520000, "cost": 310000, "roi": 1.68},
        {"ipGroupName": "体育二组", "revenue": 410000, "cost": 280000, "roi": 1.46},
    ],
}


@router.get("/catalog")
def report_catalog(_: User = Depends(current_user)):
    return ok({"reports": STANDARD_REPORTS})


@router.get("/categories")
def report_categories(_: User = Depends(current_user)):
    return ok({"categories": REPORT_CATEGORIES})


@router.get("/datasets")
def report_datasets(_: User = Depends(current_user)):
    return ok({"datasets": DATASETS, "compLib": COMP_LIB})


@router.get("/list")
def report_manage_list(
    request: Request,
    keyword: str | None = None,
    reportType: str | None = None,
    category: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    from app.bi_br212_seed import ensure_bi_br212_seed

    ensure_bi_br212_seed(db)
    q = restrict_report_def(
        select(BiReportDef).where(BiReportDef.deleted == 0, BiReportDef.tenant_id == tenant_id),
        request.state.scope,
        tenant_id,
    )
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((BiReportDef.report_name.like(kw)) | (BiReportDef.report_no.like(kw)))
    if reportType:
        q = q.where(BiReportDef.report_type == reportType.strip().upper())
    if category:
        q = q.where(BiReportDef.category == category.strip())
    if status:
        q = q.where(BiReportDef.status == status.strip().upper())
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(BiReportDef.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([report_def_vo(r, names) for r in rows], total, page_no, size)


@router.post("")
def report_manage_create(body: ReportCreateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    name = body.reportName.strip()
    if not name:
        return fail(1001, "报表名称必填")
    rtype = body.reportType.strip().upper() or "REPORT"
    if rtype not in {"REPORT", "DASHBOARD"}:
        return fail(1001, "报表类型无效")
    now = utcnow()
    row = BiReportDef(
        report_no=next_report_no(db, tenant_id),
        report_name=name,
        report_type=rtype,
        category=body.category.strip() or "内容分析",
        sub_category=body.subCategory.strip(),
        status="DRAFT",
        layout_json="{}",
        creator_id=actor.id,
        dept_id=primary_dept_id(db, actor.id, tenant_id),
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.creator_id])
    return ok(report_def_vo(row, names))


@router.get("/{report_id:int}")
def report_design_get(
    report_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "报表不存在")
    if not report_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    names = user_names(db, [row.creator_id])
    return ok(report_def_vo(row, names))


@router.put("/{report_id:int}")
def report_design_save(
    report_id: int,
    body: ReportUpdateBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "报表不存在")
    if not report_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    if body.reportName.strip():
        row.report_name = body.reportName.strip()
    if body.layoutJson is not None:
        layout = body.layoutJson
        if "layoutMode" not in layout:
            layout = {**layout, "layoutMode": "FREE"}
        row.layout_json = json.dumps(layout, ensure_ascii=False)
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    return ok(report_def_vo(row, names))


@router.post("/{report_id:int}/publish")
def report_design_publish(
    report_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "报表不存在")
    if not report_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    vo = report_def_vo(row, names)
    return ok({**vo, "dest": "center", "shareUrl": f"/ims/bi/report/list?highlight={row.id}"})


@router.post("/query")
def report_design_query(body: ReportQueryBody, _: User = Depends(current_user)):
    comp_id = body.compId or "preview"
    rows = [
        {"dim": "示例A", "value": 128},
        {"dim": "示例B", "value": 96},
    ]
    return ok(
        {
            "compId": comp_id,
            "status": "SYNC",
            "columns": list(rows[0].keys()),
            "rows": rows,
            "total": len(rows),
        }
    )


PREVIEW_TABLE = [
    {"platform": "抖音", "gmv": 186400, "orders": 621, "mom": "+6.2%"},
    {"platform": "视频号", "gmv": 412800, "orders": 1376, "mom": "+6.2%"},
    {"platform": "斗鱼", "gmv": 96700, "orders": 322, "mom": "-2.1%"},
    {"platform": "快手", "gmv": 61200, "orders": 204, "mom": "-2.1%"},
]
# 预览指标卡的本地样本窗。落在窗外时只空指标卡，不下钻过滤（下钻过滤属查询性能切片）。
SAMPLE_FROM = "2026-09-01"
SAMPLE_TO = "2026-10-03"


def preview_day(raw: str) -> str | None:
    text = (raw or "").strip()[:10]
    if not text:
        return ""
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text

DRILL_CHILDREN = {
    "抖音": [{"account": "神鱼官方", "gmv": 120000, "orders": 400, "mom": "+5.1%"}],
    "视频号": [{"account": "神鱼精选", "gmv": 280000, "orders": 900, "mom": "+4.8%"}],
}


@router.post("/preview/run")
def report_preview_run(
    body: PreviewRunBody,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    title = "运营日报"
    if body.reportId:
        row = db.get(BiReportDef, body.reportId)
        if row and not row.deleted and row.tenant_id == tenant_id:
            if not report_row_visible(db, row, actor, request.state.scope):
                return fail(1008, "无权查看该报表")
            title = row.report_name
    day_from = preview_day(body.dateFrom)
    day_to = preview_day(body.dateTo)
    if day_from is None or day_to is None:
        return fail(1001, "日期格式应为 yyyy-MM-dd")
    if day_from and day_to and day_from > day_to:
        return fail(1001, "开始日期不能晚于结束日期")
    outside = bool(day_from and day_to and (day_to < SAMPLE_FROM or day_from > SAMPLE_TO))
    t0 = time.perf_counter()
    rows = [dict(r) for r in PREVIEW_TABLE]
    if body.platform and not outside:
        plat = body.platform.strip()
        rows = [r for r in rows if r["platform"] == plat] or rows[:1]
    elapsed = int((time.perf_counter() - t0) * 1000) + 856
    filters = {
        "dateFrom": day_from or body.dateFrom,
        "dateTo": day_to or body.dateTo,
        "ipGroupId": body.ipGroupId,
        "platform": body.platform,
        "timeGrain": body.timeGrain,
    }
    if outside:
        return ok(
            {
                "reportTitle": title,
                "filters": filters,
                "kpis": [],
                "trend": [],
                "pie": [],
                "columns": ["platform", "gmv", "orders", "mom"],
                "rows": [],
                "total": 0,
                "drillPath": [],
                "queryCostMs": elapsed,
                "cacheHit": False,
                "dataAsOf": "2026-10-03T14:00:00+08:00",
                "dataset": "METRIC_LIB",
                "empty": True,
                "emptyReason": "当前筛选下暂无指标",
            }
        )
    return ok(
        {
            "reportTitle": title,
            "filters": filters,
            "kpis": [
                {"label": "GMV（近 30 天累计）", "value": "¥412.8 万", "delta": "+18.6%"},
                {"label": "直播场次", "value": "14 场", "delta": "覆盖 4 平台"},
                {"label": "互动率均值", "value": "4.7%", "delta": "达标线 4.0%"},
            ],
            "trend": [{"label": f"W{i + 1}", "value": v} for i, v in enumerate([62, 78, 55, 92, 71, 86])],
            "pie": [{"name": r["platform"], "value": r["gmv"]} for r in PREVIEW_TABLE],
            "columns": ["platform", "gmv", "orders", "mom"],
            "rows": rows,
            "total": len(rows),
            "drillPath": [],
            "queryCostMs": elapsed,
            "cacheHit": True,
            "dataAsOf": "2026-10-03T14:00:00+08:00",
            "dataset": "METRIC_LIB",
            "empty": False,
            "emptyReason": "",
        }
    )


@router.post("/preview/drill")
def report_preview_drill(body: PreviewDrillBody, _: User = Depends(current_user)):
    path = [p.strip() for p in body.drillPath if p.strip()]
    if not path:
        return fail(1001, "下钻路径为空")
    parent = path[-1]
    children = DRILL_CHILDREN.get(parent)
    if children is None:
        rows = [
            {
                "sessionCode": "LS-20260928-01",
                "gmv": 42000,
                "orders": 140,
                "mom": "+3.2%",
            }
        ]
        columns = ["sessionCode", "gmv", "orders", "mom"]
        next_dim = "session"
    else:
        rows = children
        columns = ["account", "gmv", "orders", "mom"]
        next_dim = "account"
    return ok(
        {
            "dimension": body.dimension,
            "drillPath": path,
            "nextDimension": next_dim,
            "columns": columns,
            "rows": rows,
            "total": len(rows),
            "penetrateTarget": "MODULE_DETAIL",
            "note": "BI-002 单元格穿透占位 · 可链 DC-001",
        }
    )


@router.get("/{code}")
def report_preview(
    code: str,
    ipGroupId: int | None = None,
    platform: str | None = None,
    _: Session = Depends(db_session),
    __: User = Depends(current_user),
):
    meta = next((item for item in STANDARD_REPORTS if item["code"] == code), None)
    if meta is None:
        return fail(1001, "未知报表 code")
    rows = MOCK_ROWS.get(code)
    if rows is None:
        rows = [{"metric": "sample", "value": 1, "note": f"占位数据 · {code}"}]
    return ok(
        {
            "code": code,
            "title": meta["title"],
            "filters": {"ipGroupId": ipGroupId, "platform": platform or ""},
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
            "total": len(rows),
            "dataAsOf": "2026-09-30T23:59:59+08:00",
        }
    )
