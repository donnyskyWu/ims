"""BI 报表中心（M6 标准预览）+ 报表管理目录（W9-6 biList）。"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import primary_dept_id, report_row_visible, restrict_report_def, share_grant_clause
from app.bi_drill import guard_report, record_bi_query, report_label, span_response
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import BiReportCategory, BiReportDef, BiReportPublish, User

router = APIRouter(prefix="/bi/report", tags=["bi-report"])

BJ = timezone(timedelta(hours=8))

CATEGORY_TREE = [
    ("运营", 0, ["日报", "周报", "大屏"]),
    ("内容", 0, []),
    ("财务", 0, []),
    ("未分类", 1, []),
]


class ReportCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportName: str
    reportType: str = "REPORT"
    category: str = "内容分析"
    subCategory: str = ""
    shareScope: str = "PRIVATE"
    metricNote: str = ""


class CategoryBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    action: str = "add"
    name: str = ""
    parentId: int = 0
    categoryId: int = 0


class ImportBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    template: dict | None = None


class ReportUpdateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reportName: str = ""
    layoutJson: dict | None = None
    keepVersion: bool = False


class PublishBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    dest: str = "CENTER"
    shareScope: str = ""
    opPerm: str = "READONLY"
    rowPerm: str = "INHERIT"
    viewerIds: list[int] = Field(default_factory=list)
    menuName: str = ""
    accessType: str = "SHARE_LINK"


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


def _field(key: str, label: str, ftype: str, dtype: str, metric_code: str = "") -> dict:
    item = {
        "fieldKey": key,
        "fieldLabel": label,
        "fieldType": ftype,
        "dataType": dtype,
        "name": key,
        "label": label,
        "type": "number" if dtype == "NUMBER" else "string",
    }
    if metric_code:
        item["metricCode"] = metric_code
    return item


# 开发 / E2E 用的指标事实样本（METRIC_LIB）。绑定 GMV、统计日期等字段后按这里取数。
METRIC_FACT = [
    {"statDate": "2026-10-01", "platform": "抖音", "gmv": 186400, "orders": 621, "liveSessions": 4, "interactRate": 4.7},
    {"statDate": "2026-10-02", "platform": "视频号", "gmv": 412800, "orders": 1376, "liveSessions": 6, "interactRate": 5.1},
    {"statDate": "2026-10-03", "platform": "快手", "gmv": 96800, "orders": 310, "liveSessions": 3, "interactRate": 3.9},
]
CUSTOM_FACT = [
    {"dim": "内容", "value": 128},
    {"dim": "投放", "value": 96},
]

DATASETS = [
    {
        "code": "METRIC_LIB",
        "name": "指标库",
        "datasetSource": "METRIC_LIB",
        "enabled": True,
        "freshnessMinutes": 15,
        "rowCountEstimate": len(METRIC_FACT),
        "fields": [
            _field("statDate", "统计日期", "DIMENSION", "DATE"),
            _field("platform", "平台", "DIMENSION", "STRING"),
            _field("gmv", "GMV", "METRIC", "NUMBER", "GMV_DAILY"),
            _field("orders", "订单数", "METRIC", "NUMBER", "ORDER_CNT"),
            _field("liveSessions", "直播场次", "METRIC", "NUMBER", "LIVE_SESSIONS"),
            _field("interactRate", "互动率", "METRIC", "NUMBER", "INTERACT_RATE"),
        ],
    },
    {
        "code": "CUSTOM_QUERY",
        "name": "已发布自定义查询",
        "datasetSource": "CUSTOM_QUERY",
        "enabled": True,
        "freshnessMinutes": 15,
        "rowCountEstimate": len(CUSTOM_FACT),
        "fields": [
            _field("dim", "维度", "DIMENSION", "STRING"),
            _field("value", "数值", "METRIC", "NUMBER", "CQ_VALUE"),
        ],
    },
    {
        "code": "DWS_AGGREGATION",
        "name": "宽表聚合",
        "datasetSource": "DWS_AGGREGATION",
        "enabled": False,
        "freshnessMinutes": 15,
        "rowCountEstimate": 0,
        "note": "P2+",
        "fields": [],
    },
]


def _comp(type_: str, name: str, group: str, w: int, h: int) -> dict:
    return {"type": type_, "name": name, "group": group, "defaultSize": {"w": w, "h": h}}


COMP_LIB = [
    _comp("KPI", "KPI 指标卡", "CHART", 240, 120),
    _comp("BAR", "柱状图", "CHART", 480, 280),
    _comp("LINE", "折线图", "CHART", 480, 280),
    _comp("PIE", "饼图", "CHART", 360, 280),
    _comp("DONUT", "环形图", "CHART", 360, 280),
    _comp("RADAR", "雷达图", "CHART", 360, 280),
    _comp("FUNNEL", "漏斗图", "CHART", 360, 280),
    _comp("SCATTER", "散点图", "CHART", 480, 280),
    _comp("TABLE", "数据表", "CHART", 640, 320),
    _comp("DETAIL_TABLE", "明细表", "CHART", 640, 320),
    _comp("RICH_TEXT", "富文本", "CHART", 320, 120),
    _comp("DATE_RANGE", "日期范围", "FILTER", 280, 80),
    _comp("SELECT_SINGLE", "下拉单选", "FILTER", 240, 80),
    _comp("SELECT_MULTI", "下拉多选", "FILTER", 240, 80),
    _comp("TEXT_INPUT", "文本输入", "FILTER", 240, 80),
    _comp("NUMBER_RANGE", "数值区间", "FILTER", 280, 80),
    _comp("GROUP", "分组容器", "CONTAINER", 480, 320),
    _comp("CARD", "卡片容器", "CONTAINER", 320, 200),
    _comp("TAB", "Tab 容器", "CONTAINER", 640, 320),
    _comp("BUTTON", "按钮", "ACTION", 160, 80),
    _comp("LINK", "跳转链接", "ACTION", 200, 80),
    _comp("TRIGGER", "联动触发件", "ACTION", 200, 80),
]

_AGG = {"SUM", "AVG", "COUNT", "MAX", "MIN"}
_CALL = re.compile(r"(SUM|AVG|COUNT|MAX|MIN)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", re.I)
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def dataset_fields(code: str) -> dict[str, dict]:
    for item in DATASETS:
        if item["code"] == code:
            return {field["fieldKey"]: field for field in item.get("fields") or []}
    return {}


def fact_rows(code: str) -> list[dict]:
    if code == "CUSTOM_QUERY":
        return [dict(row) for row in CUSTOM_FACT]
    if code == "DWS_AGGREGATION":
        return []
    return [dict(row) for row in METRIC_FACT]


def aggregate_values(rows: list[dict], key: str, agg: str) -> float:
    vals: list[float] = []
    for row in rows:
        if key not in row:
            continue
        try:
            vals.append(float(row[key]))
        except (TypeError, ValueError):
            continue
    kind = (agg or "SUM").upper()
    if not vals:
        return 0
    if kind == "AVG":
        return round(sum(vals) / len(vals), 2)
    if kind == "COUNT":
        return float(len(vals))
    if kind == "MAX":
        return max(vals)
    if kind == "MIN":
        return min(vals)
    return round(sum(vals), 2)


def expr_error(expr: str, fields: dict[str, dict]) -> int | None:
    text = (expr or "").strip()
    if not text:
        return None
    if not re.fullmatch(r"[0-9A-Za-z_+\-*/().,\s]+", text):
        return 1192
    calls = list(_CALL.finditer(text))
    if not calls and _IDENT.search(text):
        return 1192
    for match in calls:
        key = match.group(2)
        meta = fields.get(key)
        if meta is None:
            return 1191
        if meta.get("fieldType") != "METRIC":
            return 1191
    stripped = _CALL.sub("0", text)
    if _IDENT.search(stripped):
        return 1192
    if not re.fullmatch(r"[0-9+\-*/().\s]+", stripped):
        return 1192
    return None


def eval_expr(expr: str, rows: list[dict]) -> float:
    def repl(match: re.Match) -> str:
        return str(aggregate_values(rows, match.group(2), match.group(1)))

    replaced = _CALL.sub(repl, expr)
    value = eval(replaced, {"__builtins__": {}}, {})  # noqa: S307 — 已限制为白名单函数与四则运算
    return round(float(value), 4)


def binding_error(comp: dict) -> int | None:
    dataset = str(comp.get("dataset") or "METRIC_LIB")
    if dataset == "DWS_AGGREGATION":
        return 1191
    fields = dataset_fields(dataset)
    if dataset not in {item["code"] for item in DATASETS}:
        return 1191
    metric = str(comp.get("metric") or comp.get("fieldKey") or "").strip()
    dimension = str(comp.get("dimension") or "").strip()
    calc = str(comp.get("calcExpression") or "").strip()
    if metric:
        meta = fields.get(metric)
        if meta is None or meta.get("fieldType") != "METRIC":
            return 1191
    if dimension:
        meta = fields.get(dimension)
        if meta is None or meta.get("fieldType") != "DIMENSION":
            return 1191
    if calc:
        return expr_error(calc, fields)
    return None


def project_comp(comp: dict) -> dict:
    dataset = str(comp.get("dataset") or "METRIC_LIB")
    rows = fact_rows(dataset)
    fields = dataset_fields(dataset)
    metric = str(comp.get("metric") or "").strip()
    dimension = str(comp.get("dimension") or "").strip()
    agg = str(comp.get("agg") or "SUM").upper()
    if agg not in _AGG:
        agg = "SUM"
    calc = str(comp.get("calcExpression") or "").strip()
    if calc:
        value = eval_expr(calc, rows)
        return {"columns": ["label", "value"], "rows": [{"label": calc, "value": value}], "total": 1}
    if metric and dimension:
        grouped: dict[str, list] = {}
        for row in rows:
            grouped.setdefault(str(row.get(dimension, "")), []).append(row)
        out = []
        for key, bucket in grouped.items():
            value = aggregate_values(bucket, metric, agg)
            out.append({"dim": key, dimension: key, "value": value, metric: value})
        return {"columns": [dimension, metric], "rows": out, "total": len(out)}
    if metric:
        value = aggregate_values(rows, metric, agg)
        label = fields.get(metric, {}).get("fieldLabel", metric)
        return {"columns": ["label", "value"], "rows": [{"label": label, "value": value}], "total": 1}
    columns = list(rows[0].keys()) if rows else []
    return {"columns": columns, "rows": rows, "total": len(rows)}


def target_comp(body: ReportQueryBody) -> dict:
    comps = body.components or []
    wanted = (body.compId or "").strip()
    if wanted and wanted != "preview":
        for item in comps:
            if str(item.get("id") or item.get("compId") or "") == wanted:
                return item
    return comps[0] if comps else {}


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
        "version": int(row.report_version or 1),
        "opPerm": row.op_perm or "READONLY",
        "rowPerm": row.row_perm or "INHERIT",
        "publishDest": row.publish_dest or "CENTER",
        "menuName": row.menu_name or "",
        "viewerIds": [int(item) for item in (row.viewer_ids or "").split(",") if item.strip().isdigit()],
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

COLUMN_LABEL = {
    "platform": "平台",
    "accountName": "账号",
    "followerCount": "粉丝数",
    "workCount": "作品数",
    "statusName": "状态",
    "health": "健康度",
    "reason": "异常原因",
    "ipGroupName": "IP组",
    "outputCount": "产出量",
    "interact": "互动量",
    "author": "作者",
    "statDate": "日期",
    "liveHours": "直播时长",
    "cost": "成本",
    "gmv": "GMV",
    "revenue": "营收",
    "roi": "ROI",
    "member": "人员",
    "roleName": "角色",
    "capacity": "产能",
    "alertName": "预警",
    "levelName": "级别",
}
# 无仓库时的标准报表种子。ipGroupId 只参与筛选，不作为展示列。
STANDARD_SEED = {
    "unified-account": [
        {"platform": "抖音", "accountName": "神鱼体育官方", "followerCount": 128000, "workCount": 342, "statDate": "2026-09-12"},
        {"platform": "视频号", "accountName": "神鱼精选", "followerCount": 86000, "workCount": 198, "statDate": "2026-09-18"},
    ],
    "account-status": [
        {"accountName": "神鱼体育官方", "platform": "抖音", "statusName": "正常", "health": 92, "reason": "—"},
        {"accountName": "神鱼精选", "platform": "视频号", "statusName": "关注", "health": 71, "reason": "互动下滑"},
        {"accountName": "快手旗舰", "platform": "快手", "statusName": "异常", "health": 48, "reason": "登录失效"},
    ],
    "video-output": [
        {"ipGroupName": "电竞一组", "ipGroupId": 1, "platform": "抖音", "outputCount": 28, "interact": 12600, "statDate": "2026-09-08"},
        {"ipGroupName": "体育二组", "ipGroupId": 2, "platform": "视频号", "outputCount": 16, "interact": 8400, "statDate": "2026-09-21"},
    ],
    "live-duration": [
        {"author": "主播-林晓", "statDate": "2026-09-11", "liveHours": 6.5, "platform": "抖音"},
        {"author": "主播-周宁", "statDate": "2026-09-19", "liveHours": 4.0, "platform": "视频号"},
        {"author": "主播-林晓", "statDate": "2026-09-26", "liveHours": 5.5, "platform": "抖音"},
    ],
    "cost-allocation": [
        {"accountName": "神鱼体育官方", "ipGroupName": "电竞一组", "cost": 18600, "gmv": 128400},
        {"accountName": "神鱼精选", "ipGroupName": "体育二组", "cost": 9200, "gmv": 86400},
    ],
    "roi": [
        {"ipGroupName": "电竞一组", "revenue": 520000, "cost": 310000, "roi": 1.68},
        {"ipGroupName": "体育二组", "revenue": 410000, "cost": 280000, "roi": 1.46},
    ],
    "team-config": [
        {"ipGroupName": "电竞一组", "member": "林晓", "roleName": "主播", "capacity": 18},
        {"ipGroupName": "电竞一组", "member": "周宁", "roleName": "运营", "capacity": 12},
        {"ipGroupName": "体育二组", "member": "陈可", "roleName": "主播", "capacity": 15},
    ],
    "account-alert": [
        {"accountName": "快手旗舰", "alertName": "登录失效", "levelName": "高", "statDate": "2026-09-22"},
        {"accountName": "神鱼精选", "alertName": "互动下滑", "levelName": "中", "statDate": "2026-09-24"},
        {"accountName": "神鱼体育官方", "alertName": "证书临期", "levelName": "低", "statDate": "2026-09-27"},
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


def ensure_report_categories(db: Session, tenant_id: int) -> None:
    count = db.scalar(
        select(func.count()).select_from(BiReportCategory).where(
            BiReportCategory.deleted == 0,
            BiReportCategory.tenant_id == tenant_id,
        )
    )
    if int(count or 0) > 0:
        return
    now = utcnow()
    for name, system, children in CATEGORY_TREE:
        parent = BiReportCategory(
            name=name,
            parent_id=0,
            system_flag=system,
            tenant_id=tenant_id,
            created_at=now,
        )
        db.add(parent)
        db.flush()
        for child in children:
            db.add(
                BiReportCategory(
                    name=child,
                    parent_id=parent.id,
                    system_flag=0,
                    tenant_id=tenant_id,
                    created_at=now,
                )
            )
    db.flush()


def category_rows(db: Session, tenant_id: int) -> list[BiReportCategory]:
    ensure_report_categories(db, tenant_id)
    return list(
        db.scalars(
            select(BiReportCategory)
            .where(BiReportCategory.deleted == 0, BiReportCategory.tenant_id == tenant_id)
            .order_by(BiReportCategory.id)
        ).all()
    )


def category_tree(db: Session, tenant_id: int) -> list[dict]:
    rows = category_rows(db, tenant_id)
    children: dict[int, list[BiReportCategory]] = {}
    for row in rows:
        children.setdefault(int(row.parent_id or 0), []).append(row)
    tree = []
    for row in children.get(0, []):
        kids = children.get(row.id, [])
        tree.append(
            {
                "id": row.id,
                "code": str(row.id),
                "name": row.name,
                "parentId": 0,
                "system": bool(row.system_flag),
                "children": [
                    {
                        "id": kid.id,
                        "code": str(kid.id),
                        "name": kid.name,
                        "parentId": row.id,
                        "system": False,
                        "children": [],
                    }
                    for kid in kids
                ],
            }
        )
    return tree


def category_match_names(db: Session, tenant_id: int, name: str) -> list[str]:
    rows = category_rows(db, tenant_id)
    found = next((row for row in rows if row.name == name), None)
    if found is None:
        return [name]
    names = [found.name]
    if not found.parent_id:
        names.extend(row.name for row in rows if row.parent_id == found.id)
    return names


def category_report_count(db: Session, tenant_id: int, names: list[str]) -> int:
    if not names:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(BiReportDef)
            .where(
                BiReportDef.deleted == 0,
                BiReportDef.tenant_id == tenant_id,
                or_(BiReportDef.category.in_(names), BiReportDef.sub_category.in_(names)),
            )
        )
        or 0
    )


def category_node(db: Session, tenant_id: int, category_id: int) -> BiReportCategory | None:
    row = db.get(BiReportCategory, category_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    return row


@router.get("/categories")
def report_categories(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    return ok({"categories": category_tree(db, tenant_of(actor))})


@router.post("/category")
def report_category_save(body: CategoryBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    ensure_report_categories(db, tenant_id)
    action = (body.action or "add").strip().lower()
    if action == "add":
        name = body.name.strip()
        if not name:
            return fail(1001, "请填写分类名称")
        parent_id = int(body.parentId or 0)
        if parent_id:
            parent = category_node(db, tenant_id, parent_id)
            if parent is None:
                return fail(1001, "上级分类不存在")
            if parent.parent_id:
                return fail(1001, "分类最多两级")
        dup = db.scalar(
            select(BiReportCategory).where(
                BiReportCategory.deleted == 0,
                BiReportCategory.tenant_id == tenant_id,
                BiReportCategory.parent_id == parent_id,
                BiReportCategory.name == name,
            )
        )
        if dup is not None:
            return fail(1001, "分类已存在")
        row = BiReportCategory(
            name=name,
            parent_id=parent_id,
            system_flag=0,
            tenant_id=tenant_id,
            created_at=utcnow(),
        )
        db.add(row)
        db.flush()
        return ok({"id": row.id, "name": row.name, "parentId": row.parent_id, "level": 2 if parent_id else 1})
    if action == "rename":
        row = category_node(db, tenant_id, int(body.categoryId or 0))
        if row is None:
            return fail(1001, "分类不存在")
        name = body.name.strip()
        if not name:
            return fail(1001, "请填写分类名称")
        if row.system_flag or row.name == "未分类":
            return fail(1001, "未分类不能改名")
        previous = row.name
        row.name = name
        reports = list(
            db.scalars(
                select(BiReportDef).where(
                    BiReportDef.deleted == 0,
                    BiReportDef.tenant_id == tenant_id,
                    BiReportDef.category == previous,
                )
            ).all()
        )
        for report in reports:
            report.category = name
        return ok({"id": row.id, "name": row.name})
    if action == "delete":
        row = category_node(db, tenant_id, int(body.categoryId or 0))
        if row is None:
            return fail(1001, "分类不存在")
        if row.system_flag or row.name == "未分类":
            return fail(1001, "未分类不能删除")
        rows = category_rows(db, tenant_id)
        removing = [row] + [item for item in rows if item.parent_id == row.id]
        names = [item.name for item in removing]
        occupied = category_report_count(db, tenant_id, names)
        if occupied:
            return fail(1001, f"该分类下有 {occupied} 个报表，请先移动")
        for item in removing:
            item.deleted = 1
        return ok({"deleted": len(removing), "message": "分类已删除"})
    return fail(1001, "分类操作无效")


@router.post("/import")
def report_import(body: ImportBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    template = body.template
    if not isinstance(template, dict):
        return fail(1001, "文件格式不正确")
    name = str(template.get("reportName") or template.get("name") or "").strip()
    comps = template.get("comps")
    if comps is None:
        comps = template.get("components")
    layout = template.get("layoutJson")
    if comps is None and isinstance(layout, dict):
        comps = layout.get("comps") or layout.get("components") or []
    if not name or not isinstance(comps, list):
        return fail(1001, "文件格式不正确")
    known = {item["code"] for item in DATASETS if item.get("enabled", True)}
    warnings = []
    seen: set[str] = set()
    for comp in comps:
        if not isinstance(comp, dict):
            return fail(1001, "文件格式不正确")
        dataset = str(comp.get("dataset") or "").strip()
        if dataset and dataset not in known and dataset not in seen:
            seen.add(dataset)
            warnings.append({"key": dataset, "message": f"数据源 {dataset} 需重新配置"})
    tenant_id = tenant_of(actor)
    rtype = str(template.get("reportType") or "REPORT").strip().upper() or "REPORT"
    if rtype not in {"REPORT", "DASHBOARD"}:
        rtype = "REPORT"
    scope = str(template.get("shareScope") or "PRIVATE").strip().upper() or "PRIVATE"
    if scope not in {"PRIVATE", "SPECIFIED", "ALL"}:
        scope = "PRIVATE"
    now = utcnow()
    row = BiReportDef(
        report_no=next_report_no(db, tenant_id),
        report_name=name,
        report_type=rtype,
        category=str(template.get("category") or "未分类").strip() or "未分类",
        sub_category="",
        status="DRAFT",
        share_scope=scope,
        layout_json=json.dumps({"layoutMode": "FREE", "comps": comps}, ensure_ascii=False),
        creator_id=actor.id,
        dept_id=primary_dept_id(db, actor.id, tenant_id),
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.creator_id])
    vo = report_def_vo(row, names)
    return ok(
        {
            **vo,
            "reportId": row.id,
            "compCount": len(comps),
            "warnings": warnings,
            "formatOk": True,
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
    status: str | None = None,
    shareScope: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    from app.bi_br212_seed import ensure_bi_br212_seed

    ensure_bi_br212_seed(db)
    scoped_ids = restrict_report_def(
        select(BiReportDef.id).where(BiReportDef.deleted == 0, BiReportDef.tenant_id == tenant_id),
        request.state.scope,
        tenant_id,
    )
    granted_ids = select(BiReportDef.id).where(share_grant_clause(actor))
    q = select(BiReportDef).where(BiReportDef.id.in_(scoped_ids.union(granted_ids)))
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((BiReportDef.report_name.like(kw)) | (BiReportDef.report_no.like(kw)))
    if reportType:
        q = q.where(BiReportDef.report_type == reportType.strip().upper())
    if category:
        names = category_match_names(db, tenant_id, category.strip())
        q = q.where(BiReportDef.category.in_(names))
    if status:
        q = q.where(BiReportDef.status == status.strip().upper())
    if shareScope:
        q = q.where(BiReportDef.share_scope == shareScope.strip().upper())
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
    scope = (body.shareScope or "PRIVATE").strip().upper() or "PRIVATE"
    if scope not in {"PRIVATE", "SPECIFIED", "ALL"}:
        return fail(1001, "可见范围无效")
    now = utcnow()
    row = BiReportDef(
        report_no=next_report_no(db, tenant_id),
        report_name=name,
        report_type=rtype,
        category=body.category.strip() or "内容分析",
        sub_category=body.subCategory.strip(),
        status="DRAFT",
        share_scope=scope,
        metric_note=(body.metricNote or "").strip()[:512],
        report_version=1,
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
        if row.status == "PUBLISHED" and not body.keepVersion:
            row.report_version = int(row.report_version or 1) + 1
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    return ok(report_def_vo(row, names))


def pack_viewer_ids(ids: list[int]) -> str:
    clean = []
    for item in ids:
        try:
            num = int(item)
        except (TypeError, ValueError):
            continue
        if num > 0 and num not in clean:
            clean.append(num)
    if not clean:
        return ""
    return "," + ",".join(str(item) for item in clean) + ","


def publish_vo(row: BiReportPublish, names: dict[int, str]) -> dict:
    return {
        "publishId": row.id,
        "reportId": row.report_id,
        "dest": row.dest,
        "shareScope": row.share_scope,
        "opPerm": row.op_perm,
        "rowPerm": row.row_perm,
        "menuName": row.menu_name,
        "accessType": row.access_type,
        "snapshotVersion": row.snapshot_version,
        "status": row.status,
        "shareUrl": row.share_url,
        "publisherName": names.get(row.publisher_id, ""),
        "publishedAt": iso(row.created_at),
    }


@router.post("/{report_id:int}/copy")
def report_copy(
    report_id: int,
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    src = db.get(BiReportDef, report_id)
    if src is None or src.deleted or src.tenant_id != tenant_id:
        return fail(1001, "报表不存在")
    if not report_row_visible(db, src, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    now = utcnow()
    row = BiReportDef(
        report_no=next_report_no(db, tenant_id),
        report_name=f"{src.report_name}副本"[:128],
        report_type=src.report_type,
        category=src.category,
        sub_category=src.sub_category,
        status="DRAFT",
        share_scope="PRIVATE",
        metric_note=src.metric_note or "",
        report_version=1,
        layout_json=src.layout_json or "{}",
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


@router.get("/{report_id:int}/export")
def report_export(
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
    layout = parse_layout(row.layout_json)
    return ok(
        {
            "template": {
                "reportName": row.report_name,
                "reportType": row.report_type,
                "category": row.category,
                "version": int(row.report_version or 1),
                "layoutJson": layout,
            }
        }
    )


@router.delete("/{report_id:int}")
def report_delete(
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
    row.deleted = 1
    row.updated_at = utcnow()
    return ok({"id": row.id, "deleted": True})


@router.get("/{report_id:int}/publish/list")
def report_publish_list(
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
    rows = list(
        db.scalars(
            select(BiReportPublish)
            .where(
                BiReportPublish.report_id == report_id,
                BiReportPublish.deleted == 0,
                BiReportPublish.tenant_id == tenant_id,
            )
            .order_by(BiReportPublish.id.desc())
        ).all()
    )
    names = user_names(db, [item.publisher_id for item in rows])
    return ok({"list": [publish_vo(item, names) for item in rows]})


@router.post("/{report_id:int}/publish")
def report_design_publish(
    report_id: int,
    request: Request,
    body: PublishBody | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(BiReportDef, report_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "报表不存在")
    if not report_row_visible(db, row, actor, request.state.scope):
        return fail(1008, "无权查看该报表")
    cfg = body or PublishBody()
    dest = (cfg.dest or "CENTER").strip().upper()
    if dest not in {"CENTER", "MENU"}:
        return fail(1001, "发布去向无效")
    menu_name = (cfg.menuName or "").strip()
    if dest == "MENU" and not menu_name:
        return fail(1001, "请填写菜单名称")
    scope = (cfg.shareScope or row.share_scope or "PRIVATE").strip().upper()
    if scope not in {"PRIVATE", "SPECIFIED", "ALL"}:
        return fail(1001, "可见范围无效")
    op_perm = (cfg.opPerm or "READONLY").strip().upper()
    if op_perm not in {"READONLY", "EXPORT"}:
        return fail(1001, "操作权限无效")
    row_perm = (cfg.rowPerm or "INHERIT").strip().upper()
    if row_perm not in {"INHERIT", "SNAPSHOT"}:
        return fail(1001, "行权限无效")
    viewers = pack_viewer_ids(cfg.viewerIds)
    if scope == "SPECIFIED" and not viewers:
        return fail(1001, "请选择可见用户")
    republish = row.status == "PUBLISHED"
    row.status = "PUBLISHED"
    if republish:
        row.report_version = int(row.report_version or 1) + 1
    elif not row.report_version:
        row.report_version = 1
    row.share_scope = scope
    row.op_perm = op_perm
    row.row_perm = row_perm
    row.publish_dest = dest
    row.menu_name = menu_name if dest == "MENU" else ""
    row.viewer_ids = viewers if scope == "SPECIFIED" else ""
    row.updated_at = utcnow()
    share_url = f"/ims/bi/report/list?highlight={row.id}"
    record = BiReportPublish(
        report_id=row.id,
        dest=dest,
        share_scope=scope,
        op_perm=op_perm,
        row_perm=row_perm,
        viewer_ids=row.viewer_ids,
        menu_name=row.menu_name,
        access_type=(cfg.accessType or "SHARE_LINK").strip().upper() or "SHARE_LINK",
        snapshot_version=int(row.report_version or 1),
        status="ACTIVE",
        share_url=share_url,
        publisher_id=actor.id,
        tenant_id=tenant_id,
        created_at=row.updated_at,
    )
    db.add(record)
    db.flush()
    names = user_names(db, [row.creator_id, actor.id])
    vo = report_def_vo(row, names)
    return ok(
        {
            **vo,
            "dest": dest,
            "publishId": record.id,
            "shareUrl": share_url,
            "menuNote": "发布去向已记为单独菜单，本次不写入系统菜单" if dest == "MENU" else "",
        }
    )


@router.post("/query")
def report_design_query(
    body: ReportQueryBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    comp = target_comp(body)
    comp_id = body.compId or str(comp.get("id") or "preview")
    if comp:
        err = binding_error(comp)
        if err == 1191:
            return fail(1191, "字段引用非法")
        if err == 1192:
            return fail(1192, "计算字段表达式非法")
        projected = project_comp(comp)
        dataset = str(comp.get("dataset") or "METRIC_LIB")
    else:
        rows = fact_rows("METRIC_LIB")
        projected = {"columns": list(rows[0].keys()) if rows else [], "rows": rows, "total": len(rows)}
        dataset = "METRIC_LIB"
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
        int(projected["total"]),
    )
    return ok(
        {
            "compId": comp_id,
            "status": "SYNC",
            "queryMode": "SYNC",
            "costMs": elapsed,
            "columns": projected["columns"],
            "rows": projected["rows"],
            "total": projected["total"],
            "cacheHit": True,
            "dataAsOf": "2026-10-03T14:00:00+08:00",
            "dataset": dataset,
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


def standard_visuals(title: str, rows: list[dict], grain: str) -> tuple[list[dict], list[dict]]:
    numeric_key = ""
    label_key = ""
    for row in rows:
        for key, value in row.items():
            if key == "ipGroupId":
                continue
            if not numeric_key and isinstance(value, (int, float)) and key != "roi":
                numeric_key = key
            if not label_key and isinstance(value, str) and key in {"statDate", "platform", "ipGroupName", "accountName", "author"}:
                label_key = key
        if numeric_key and label_key:
            break
    total = 0.0
    if numeric_key:
        total = float(sum(float(row.get(numeric_key) or 0) for row in rows))
    kpis = [
        {"metric": "记录数", "value": len(rows), "note": title},
        {
            "metric": COLUMN_LABEL.get(numeric_key, "合计") if numeric_key else "合计",
            "value": round(total, 2) if numeric_key else 0,
            "note": "种子数据合计",
        },
    ]
    if not rows or not numeric_key:
        return kpis, []
    if grain == "WEEK":
        trend = [{"label": "当周", "value": round(total, 2)}]
    elif grain == "MONTH":
        trend = [{"label": "当月", "value": round(total, 2)}]
    else:
        trend = []
        for row in rows:
            label = str(row.get(label_key) or row.get("statDate") or title)
            trend.append({"label": label, "value": float(row.get(numeric_key) or 0)})
    return kpis, trend


@router.get("/{code}")
def report_preview(
    code: str,
    ipGroupId: int | None = None,
    platform: str | None = None,
    dateFrom: str = "",
    dateTo: str = "",
    timeGrain: str = "DAY",
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
    source = STANDARD_SEED.get(code) or []
    rows = [dict(item) for item in source]
    label = standard_platform(platform)
    grain = (timeGrain or "DAY").strip().upper()
    if grain not in {"DAY", "WEEK", "MONTH"}:
        grain = "DAY"
    outside = bool(day_from and day_to and (day_to < REPORT_SAMPLE_FROM or day_from > REPORT_SAMPLE_TO))
    empty = False
    empty_reason = ""
    filter_note = ""
    if outside:
        rows = []
        empty = True
        empty_reason = "当前日期下暂无数据"
    else:
        if label and any("platform" in item for item in source):
            rows = [item for item in rows if item.get("platform") == label]
            if not rows:
                empty = True
                empty_reason = "当前平台下暂无数据"
        elif label:
            filter_note = "本报表不含平台列，筛选未改变结果"
        if ipGroupId and not empty and any("ipGroupId" in item for item in source):
            rows = [item for item in rows if int(item.get("ipGroupId") or 0) == int(ipGroupId)]
            if not rows:
                empty = True
                empty_reason = "当前 IP 组下暂无数据"
                filter_note = ""
        elif ipGroupId:
            extra = "本报表不含 IP 组，筛选未改变结果"
            filter_note = f"{filter_note} · {extra}" if filter_note else extra
    display_keys = [key for key in (rows[0].keys() if rows else (source[0].keys() if source else [])) if key != "ipGroupId"]
    columns = [COLUMN_LABEL.get(key, key) for key in display_keys]
    display_rows = [{COLUMN_LABEL.get(key, key): item.get(key) for key in display_keys} for item in rows]
    kpis, trend = standard_visuals(meta["title"], rows, grain)
    return ok(
        {
            "code": code,
            "title": meta["title"],
            "filters": {
                "ipGroupId": ipGroupId,
                "platform": label,
                "dateFrom": day_from,
                "dateTo": day_to,
                "timeGrain": grain,
            },
            "kpis": kpis,
            "trend": trend,
            "columns": columns,
            "rows": display_rows,
            "total": len(display_rows),
            "dataAsOf": "2026-09-30T23:59:59+08:00",
            "empty": empty,
            "emptyReason": empty_reason,
            "filterNote": filter_note,
        }
    )
