"""BI 报表中心（M6 标准预览）+ 报表管理目录（W9-6 biList）。"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import primary_dept_id, report_row_visible, restrict_report_def
from app.bi_drill import guard_report, record_bi_query, report_label, span_response
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiReportCategory, BiReportDef, User

router = APIRouter(prefix="/bi/report", tags=["bi-report"])

BJ = timezone(timedelta(hours=8))


class ReportCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportName: str
    reportType: str = "REPORT"
    category: str = "内容分析"
    subCategory: str = ""
    shareScope: str = "PRIVATE"
    metricNote: str = ""


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
            {"name": "statDate", "label": "统计日期", "type": "date", "fieldType": "DIMENSION", "dataType": "DATE"},
            {"name": "platform", "label": "平台", "type": "string", "fieldType": "DIMENSION", "dataType": "STRING"},
            {
                "name": "gmv",
                "label": "GMV",
                "type": "number",
                "fieldType": "METRIC",
                "dataType": "NUMBER",
                "metricCode": "GMV_DAILY",
            },
            {
                "name": "orders",
                "label": "订单数",
                "type": "number",
                "fieldType": "METRIC",
                "dataType": "NUMBER",
                "metricCode": "ORDERS",
            },
            {
                "name": "liveCount",
                "label": "直播场次",
                "type": "number",
                "fieldType": "METRIC",
                "dataType": "NUMBER",
                "metricCode": "LIVE_COUNT",
            },
        ],
    },
    {
        "code": "CUSTOM_QUERY",
        "name": "已发布自定义查询",
        "fields": [
            {"name": "dim", "label": "维度", "type": "string", "fieldType": "DIMENSION", "dataType": "STRING"},
            {
                "name": "value",
                "label": "数值",
                "type": "number",
                "fieldType": "METRIC",
                "dataType": "NUMBER",
                "metricCode": "QUERY_VALUE",
            },
        ],
    },
]

# 开发 / E2E 用的少量指标样本，绑定 GMV、平台、统计日期后设计器按此渲染。
DESIGN_SEED = [
    {"statDate": "2026-09-01", "platform": "抖音", "gmv": 186400, "orders": 621, "liveCount": 4, "dim": "抖音", "value": 186400},
    {"statDate": "2026-09-02", "platform": "抖音", "gmv": 192100, "orders": 640, "liveCount": 5, "dim": "抖音", "value": 192100},
    {"statDate": "2026-09-01", "platform": "视频号", "gmv": 412800, "orders": 1376, "liveCount": 3, "dim": "视频号", "value": 412800},
    {"statDate": "2026-09-02", "platform": "视频号", "gmv": 398200, "orders": 1302, "liveCount": 3, "dim": "视频号", "value": 398200},
    {"statDate": "2026-09-03", "platform": "快手", "gmv": 61200, "orders": 204, "liveCount": 2, "dim": "快手", "value": 61200},
]

_EXPR_OK = re.compile(
    r"^(?:\s|\d+\.?\d*|\.?\d+|SUM|AVG|COUNT|MAX|MIN|gmv|orders|liveCount|cost|revenue|value|\+|-|\*|/|\(|\))+$",
    re.IGNORECASE,
)

COMP_LIB = [
    {"type": "LINE", "name": "折线图", "group": "CHART", "defaultSize": {"w": 480, "h": 280}},
    {"type": "BAR", "name": "柱状图", "group": "CHART", "defaultSize": {"w": 480, "h": 280}},
    {"type": "PIE", "name": "饼图", "group": "CHART", "defaultSize": {"w": 320, "h": 280}},
    {"type": "AREA", "name": "面积图", "group": "CHART", "defaultSize": {"w": 480, "h": 280}},
    {"type": "RADAR", "name": "雷达图", "group": "CHART", "defaultSize": {"w": 320, "h": 280}},
    {"type": "FUNNEL", "name": "漏斗图", "group": "CHART", "defaultSize": {"w": 320, "h": 280}},
    {"type": "DONUT", "name": "环形图", "group": "CHART", "defaultSize": {"w": 320, "h": 280}},
    {"type": "SCATTER", "name": "散点图", "group": "CHART", "defaultSize": {"w": 480, "h": 280}},
    {"type": "TABLE", "name": "数据表", "group": "CHART", "defaultSize": {"w": 640, "h": 320}},
    {"type": "DETAIL_TABLE", "name": "明细表", "group": "CHART", "defaultSize": {"w": 640, "h": 320}},
    {"type": "KPI", "name": "KPI 指标卡", "group": "CHART", "defaultSize": {"w": 240, "h": 120}},
    {"type": "RICH_TEXT", "name": "文字", "group": "CHART", "defaultSize": {"w": 320, "h": 120}},
    {"type": "DATE_RANGE", "name": "日期", "group": "FILTER", "defaultSize": {"w": 280, "h": 80}},
    {"type": "SELECT_SINGLE", "name": "下拉", "group": "FILTER", "defaultSize": {"w": 220, "h": 80}},
    {"type": "SELECT_MULTI", "name": "下拉多选", "group": "FILTER", "defaultSize": {"w": 220, "h": 80}},
    {"type": "TEXT_INPUT", "name": "文本", "group": "FILTER", "defaultSize": {"w": 220, "h": 80}},
    {"type": "CASCADE", "name": "级联", "group": "FILTER", "defaultSize": {"w": 280, "h": 80}},
    {"type": "NUMBER_RANGE", "name": "数值区间", "group": "FILTER", "defaultSize": {"w": 240, "h": 80}},
    {"type": "TAB", "name": "Tab", "group": "CONTAINER", "defaultSize": {"w": 480, "h": 280}},
    {"type": "GROUP", "name": "分组", "group": "CONTAINER", "defaultSize": {"w": 480, "h": 280}},
    {"type": "CARD", "name": "卡片容器", "group": "CONTAINER", "defaultSize": {"w": 320, "h": 200}},
    {"type": "BUTTON", "name": "按钮", "group": "ACTION", "defaultSize": {"w": 160, "h": 80}},
    {"type": "LINK", "name": "超链接", "group": "ACTION", "defaultSize": {"w": 200, "h": 80}},
    {"type": "JUMP", "name": "跳转", "group": "ACTION", "defaultSize": {"w": 200, "h": 80}},
    {"type": "TRIGGER", "name": "联动触发", "group": "ACTION", "defaultSize": {"w": 200, "h": 80}},
]


def field_catalog() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for dataset in DATASETS:
        for field in dataset["fields"]:
            index[field["name"]] = field
            code = field.get("metricCode")
            if code:
                index[str(code)] = field
    return index


def lookup_field(key: str) -> tuple[dict | None, bool]:
    text = (key or "").strip()
    if not text:
        return None, False
    found = field_catalog().get(text)
    if found is None:
        return None, True
    return found, False


def expr_ok(expression: str) -> bool:
    text = (expression or "").strip()
    if not text:
        return True
    return _EXPR_OK.fullmatch(text) is not None


def comp_field_error(comp: dict) -> tuple[int, str] | None:
    metric_key = str(comp.get("metricKey") or "").strip()
    dimension_key = str(comp.get("dimensionKey") or "").strip()
    custom = str(comp.get("customField") or "").strip()
    datasource = comp.get("datasourceConfig") if isinstance(comp.get("datasourceConfig"), dict) else {}
    field_key = str((datasource or {}).get("fieldKey") or "").strip()
    for key, expect in (
        (metric_key, "METRIC"),
        (field_key, "METRIC"),
        (dimension_key, "DIMENSION"),
        (custom, ""),
    ):
        found, illegal = lookup_field(key)
        if illegal:
            return 1191, "字段引用非法（1191）"
        if found is not None and expect and found.get("fieldType") != expect:
            return 1191, "字段引用非法（1191）"
    if not expr_ok(str(comp.get("calcExpression") or "")):
        return 1192, "计算字段表达式非法（1192）"
    return None


def layout_field_error(layout: dict) -> tuple[int, str] | None:
    comps = layout.get("comps") or []
    if not isinstance(comps, list):
        return None
    for comp in comps:
        if isinstance(comp, dict):
            err = comp_field_error(comp)
            if err is not None:
                return err
    return None


def _agg_value(values: list[float], agg: str) -> float:
    if not values:
        return 0
    if agg == "AVG":
        return round(sum(values) / len(values), 2)
    if agg == "COUNT":
        return float(len(values))
    if agg == "MAX":
        return max(values)
    if agg == "MIN":
        return min(values)
    return round(sum(values), 2)


def aggregate_seed(comp: dict) -> list[dict]:
    metric_key = str(comp.get("metricKey") or comp.get("customField") or "").strip()
    found, _ = lookup_field(metric_key)
    metric_name = str(found["name"]) if found else "gmv"
    dimension_key = str(comp.get("dimensionKey") or "").strip()
    agg = str(comp.get("agg") or "SUM").strip().upper()
    buckets: dict[str, list[float]] = {}
    order: list[str] = []
    for row in DESIGN_SEED:
        label = str(row.get(dimension_key, "合计")) if dimension_key else "合计"
        if label not in buckets:
            order.append(label)
            buckets[label] = []
        buckets[label].append(float(row.get(metric_name) or 0))
    rows: list[dict] = []
    for label in order:
        value = _agg_value(buckets[label], agg)
        item: dict = {"label": label, "value": value, metric_name: value}
        if dimension_key:
            item[dimension_key] = label
        rows.append(item)
    return rows


def comp_is_bound(comp: dict | None) -> bool:
    if not comp:
        return False
    return bool(
        str(comp.get("metricKey") or "").strip()
        or str(comp.get("dimensionKey") or "").strip()
        or str(comp.get("customField") or "").strip()
        or str(comp.get("calcExpression") or "").strip()
    )


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
        "shareScope": row.share_scope or "PRIVATE",
        "metricNote": row.metric_note or "",
        "version": int(row.version_no or 1),
        "compCount": len(layout.get("comps") or []) if isinstance(layout.get("comps"), list) else 0,
        "layoutMode": layout.get("layoutMode", "FREE"),
        "comps": layout.get("comps", []),
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }


DEFAULT_CATEGORY_TREE = [
    ("运营", ["日报", "周报", "大屏"]),
    ("内容", []),
    ("财务", []),
    ("未分类", []),
]


def ensure_categories(db: Session, tenant_id: int) -> None:
    count = db.scalar(
        select(func.count())
        .select_from(BiReportCategory)
        .where(BiReportCategory.deleted == 0, BiReportCategory.tenant_id == tenant_id)
    )
    if int(count or 0) > 0:
        return
    now = utcnow()
    for index, (name, children) in enumerate(DEFAULT_CATEGORY_TREE):
        parent = BiReportCategory(
            name=name,
            parent_id=0,
            sort_no=index,
            protected=1 if name == "未分类" else 0,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(parent)
        db.flush()
        for child_index, child in enumerate(children):
            db.add(
                BiReportCategory(
                    name=child,
                    parent_id=parent.id,
                    sort_no=child_index,
                    protected=0,
                    tenant_id=tenant_id,
                    created_at=now,
                    updated_at=now,
                )
            )
    db.flush()


def category_rows(db: Session, tenant_id: int) -> list[BiReportCategory]:
    ensure_categories(db, tenant_id)
    return list(
        db.scalars(
            select(BiReportCategory)
            .where(BiReportCategory.deleted == 0, BiReportCategory.tenant_id == tenant_id)
            .order_by(BiReportCategory.sort_no, BiReportCategory.id)
        ).all()
    )


def category_payload(db: Session, tenant_id: int) -> list[dict]:
    rows = category_rows(db, tenant_id)
    nodes: list[dict] = []
    for top in rows:
        if top.parent_id:
            continue
        children = [row for row in rows if row.parent_id == top.id]
        nodes.append(
            {
                "id": top.id,
                "code": top.name,
                "name": top.name,
                "parentId": 0,
                "protected": bool(top.protected),
                "children": [{"id": child.id, "name": child.name, "parentId": top.id} for child in children],
            }
        )
    return nodes

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
# 标准报表本地样本窗（dataAsOf 落在 2026-09）。未传日期时不截断。
REPORT_SAMPLE_FROM = "2026-09-01"
REPORT_SAMPLE_TO = "2026-09-30"
PLATFORM_LABEL = {
    "DOUYIN": "抖音",
    "抖音": "抖音",
    "WECHAT_CHANNELS": "视频号",
    "视频号": "视频号",
    "KUAISHOU": "快手",
    "快手": "快手",
    "DOUYU": "斗鱼",
    "斗鱼": "斗鱼",
}


@router.get("/catalog")
def report_catalog(_: User = Depends(current_user)):
    return ok({"reports": STANDARD_REPORTS})


class CategoryBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: str = "add"
    name: str = ""
    parentId: int = 0
    id: int = 0


class ImportBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    template: dict | None = None


@router.get("/categories")
def report_categories(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    return ok({"categories": category_payload(db, tenant_of(actor))})


@router.post("/category")
def report_category_save(body: CategoryBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    rows = category_rows(db, tenant_id)
    action = body.action.strip().lower() or "add"
    if action == "add":
        name = body.name.strip()
        if not name:
            return fail(1001, "分类名称必填")
        parent_id = int(body.parentId or 0)
        if parent_id:
            parent = next((row for row in rows if row.id == parent_id), None)
            if parent is None:
                return fail(1001, "上级分类不存在")
            if parent.parent_id:
                return fail(1001, "分类最多两级")
        if any(row.parent_id == parent_id and row.name == name for row in rows):
            return fail(1001, "同级分类名称已存在")
        now = utcnow()
        db.add(
            BiReportCategory(
                name=name,
                parent_id=parent_id,
                sort_no=len(rows) + 1,
                protected=0,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()
        return ok({"categories": category_payload(db, tenant_id)})
    if action == "rename":
        name = body.name.strip()
        if not name:
            return fail(1001, "分类名称必填")
        row = next((item for item in rows if item.id == body.id), None)
        if row is None:
            return fail(1001, "分类不存在")
        if row.protected or row.name == "未分类":
            return fail(1001, "未分类不能改名")
        row.name = name
        row.updated_at = utcnow()
        return ok({"categories": category_payload(db, tenant_id)})
    if action == "delete":
        row = next((item for item in rows if item.id == body.id), None)
        if row is None:
            return fail(1001, "分类不存在")
        if row.protected or row.name == "未分类":
            return fail(1001, "未分类不能删除")
        doomed = [row, *[item for item in rows if item.parent_id == row.id]]
        names = {item.name for item in doomed}
        reports = list(
            db.scalars(
                select(BiReportDef).where(BiReportDef.deleted == 0, BiReportDef.tenant_id == tenant_id)
            ).all()
        )
        moved = 0
        now = utcnow()
        for report in reports:
            if report.category in names or report.sub_category in names:
                report.category = "未分类"
                report.sub_category = ""
                report.updated_at = now
                moved += 1
        for item in doomed:
            item.deleted = 1
            item.updated_at = now
        db.flush()
        return ok({"categories": category_payload(db, tenant_id), "moved": moved})
    return fail(1001, "分类操作无效")


@router.post("/import")
def report_import(body: ImportBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    template = body.template if isinstance(body.template, dict) else None
    if template is None:
        return fail(1001, "文件格式不正确")
    name = str(template.get("reportName") or template.get("name") or "").strip()
    raw_comps = template.get("comps") if isinstance(template.get("comps"), list) else template.get("components")
    if not name or not isinstance(raw_comps, list):
        return fail(1001, "文件格式不正确")
    known = {item["code"] for item in DATASETS}
    warnings: list[dict] = []
    refs: list[str] = []
    for comp in raw_comps:
        if not isinstance(comp, dict):
            return fail(1001, "文件格式不正确")
        dataset = str(comp.get("dataset") or "").strip()
        if dataset:
            refs.append(dataset)
            if dataset not in known:
                warnings.append({"key": dataset, "message": f"数据源 {dataset} 需重新配置"})
    now = utcnow()
    rtype = str(template.get("reportType") or "REPORT").strip().upper()
    if rtype not in {"REPORT", "DASHBOARD"}:
        rtype = "REPORT"
    layout = {"layoutMode": template.get("layoutMode") or "FREE", "comps": raw_comps}
    row = BiReportDef(
        report_no=next_report_no(db, tenant_id),
        report_name=name,
        report_type=rtype,
        category=str(template.get("category") or "未分类").strip() or "未分类",
        sub_category=str(template.get("subCategory") or "").strip(),
        status="DRAFT",
        share_scope="PRIVATE",
        metric_note=str(template.get("metricNote") or ""),
        version_no=1,
        layout_json=json.dumps(layout, ensure_ascii=False),
        creator_id=actor.id,
        dept_id=primary_dept_id(db, actor.id, tenant_id),
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return ok(
        {
            "reportId": row.id,
            "formatOk": True,
            "componentCount": len(raw_comps),
            "datasetRefs": refs,
            "warnings": warnings,
        }
    )


@router.get("/datasets")
def report_datasets(_: User = Depends(current_user)):
    return ok({"datasets": DATASETS, "compLib": COMP_LIB})


@router.get("/list")
def report_manage_list(
    request: Request,
    keyword: str | None = None,
    reportType: str | None = None,
    category: str | None = None,
    subCategory: str | None = None,
    shareScope: str | None = None,
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
    if subCategory:
        q = q.where(BiReportDef.sub_category == subCategory.strip())
    elif category:
        q = q.where(BiReportDef.category == category.strip())
    if shareScope:
        q = q.where(BiReportDef.share_scope == shareScope.strip().upper())
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
    scope = body.shareScope.strip().upper() or "PRIVATE"
    if scope not in {"PRIVATE", "SPECIFIED", "ALL"}:
        return fail(1001, "可见范围无效")
    now = utcnow()
    row = BiReportDef(
        report_no=next_report_no(db, tenant_id),
        report_name=name,
        report_type=rtype,
        category=body.category.strip() or "未分类",
        sub_category=body.subCategory.strip(),
        status="DRAFT",
        share_scope=scope,
        metric_note=body.metricNote.strip(),
        version_no=1,
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
        blocked = layout_field_error(layout)
        if blocked is not None:
            code, msg = blocked
            return fail(code, msg)
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
    if row.status == "PUBLISHED":
        row.version_no = int(row.version_no or 1) + 1
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    vo = report_def_vo(row, names)
    return ok({**vo, "dest": "center", "shareUrl": f"/ims/bi/report/list?highlight={row.id}"})


@router.post("/query")
def report_design_query(
    body: ReportQueryBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    comp_id = body.compId or "preview"
    target = None
    for comp in body.components:
        if not isinstance(comp, dict):
            continue
        cid = str(comp.get("id") or comp.get("compId") or "")
        if cid == comp_id:
            target = comp
            break
    if target is None and len(body.components) == 1 and isinstance(body.components[0], dict):
        target = body.components[0]
    if target is not None:
        blocked = comp_field_error(target)
        if blocked is not None:
            code, msg = blocked
            return fail(code, msg)
    if comp_is_bound(target):
        rows = aggregate_seed(target or {})
    else:
        rows = [
            {"dim": "示例A", "value": 128},
            {"dim": "示例B", "value": 96},
        ]
    metric_total = round(sum(float(r.get("value") or 0) for r in rows), 2)
    started = time.perf_counter()
    elapsed = max(round((time.perf_counter() - started) * 1000, 1), 1)
    record_bi_query(
        db,
        actor,
        body.reportId,
        report_label(db, actor, body.reportId),
        "DESIGN",
        "SYNC",
        elapsed,
        len(rows),
    )
    return ok(
        {
            "compId": comp_id,
            "status": "SYNC",
            "queryMode": "SYNC",
            "costMs": elapsed,
            "columns": list(rows[0].keys()),
            "rows": rows,
            "total": len(rows),
            "metricTotal": metric_total,
            "cacheHit": True,
            "dataAsOf": "2026-10-03T14:00:00+08:00",
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
        blocked = guard_report(db, request, actor, body.reportId)
        if blocked is not None:
            return blocked
        row = db.get(BiReportDef, body.reportId)
        if row is not None:
            title = row.report_name
    day_from = preview_day(body.dateFrom)
    day_to = preview_day(body.dateTo)
    if day_from is None or day_to is None:
        return fail(1001, "日期格式应为 yyyy-MM-dd")
    if day_from and day_to and day_from > day_to:
        return fail(1001, "开始日期不能晚于结束日期")
    outside = bool(day_from and day_to and (day_to < SAMPLE_FROM or day_from > SAMPLE_TO))
    ctx = {
        "dateFrom": body.dateFrom,
        "dateTo": body.dateTo,
        "PLATFORM": body.platform or "",
    }
    blocked_span = span_response(db, actor, body.reportId, title, "PREVIEW", ["PLATFORM"], ctx)
    if blocked_span is not None:
        return blocked_span
    t0 = time.perf_counter()
    rows = [dict(r) for r in PREVIEW_TABLE]
    if body.platform and not outside:
        plat = body.platform.strip()
        rows = [r for r in rows if r["platform"] == plat] or rows[:1]
    elapsed = int((time.perf_counter() - t0) * 1000) + 856
    record_bi_query(db, actor, body.reportId, title, "PREVIEW", "SYNC", elapsed, len(rows))
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
            "queryMode": "SYNC",
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


def standard_platform(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    return PLATFORM_LABEL.get(text, text)


@router.get("/{code}")
def report_preview(
    code: str,
    ipGroupId: int | None = None,
    platform: str | None = None,
    dateFrom: str = "",
    dateTo: str = "",
    _: Session = Depends(db_session),
    __: User = Depends(current_user),
):
    meta = next((item for item in STANDARD_REPORTS if item["code"] == code), None)
    if meta is None:
        return fail(1001, "未知报表 code")
    day_from = ""
    day_to = ""
    if (dateFrom or "").strip() or (dateTo or "").strip():
        day_from = preview_day(dateFrom) or ""
        day_to = preview_day(dateTo) or ""
        if preview_day(dateFrom) is None or preview_day(dateTo) is None or not day_from or not day_to:
            return fail(1001, "日期格式应为 yyyy-MM-dd")
        if day_from > day_to:
            return fail(1001, "开始日期不能晚于结束日期")
    source = MOCK_ROWS.get(code)
    placeholder = source is None
    rows = [dict(item) for item in source] if source else [{"metric": "sample", "value": 1, "note": f"占位数据 · {code}"}]
    label = standard_platform(platform)
    outside = bool(day_from and day_to and (day_to < REPORT_SAMPLE_FROM or day_from > REPORT_SAMPLE_TO))
    empty = False
    empty_reason = ""
    filter_note = ""
    if outside:
        rows = []
        empty = True
        empty_reason = "当前日期下暂无数据"
    elif label and placeholder:
        rows = []
        empty = True
        empty_reason = "当前平台下暂无数据"
    elif label and any("platform" in item for item in rows):
        rows = [item for item in rows if item.get("platform") == label]
        if not rows:
            empty = True
            empty_reason = "当前平台下暂无数据"
    elif label:
        filter_note = "本报表不含平台列，筛选未改变结果"
    columns = list(rows[0].keys()) if rows else (list(source[0].keys()) if source else ["metric", "value", "note"])
    return ok(
        {
            "code": code,
            "title": meta["title"],
            "filters": {
                "ipGroupId": ipGroupId,
                "platform": label,
                "dateFrom": day_from,
                "dateTo": day_to,
            },
            "columns": columns,
            "rows": rows,
            "total": len(rows),
            "dataAsOf": "2026-09-30T23:59:59+08:00",
            "empty": empty,
            "emptyReason": empty_reason,
            "filterNote": filter_note,
        }
    )
