"""DC-003 全链路看板：布局设计器 + 新鲜度，以及总览/健康度/维度的最小聚合。

契约路径与《DC-数据中心-API契约》§2.3 一致。#129 的 overview/health/dimension
尚未进入 main，本模块把这些只读聚合和布局、freshness 放在同一路由下，避免另起路径。
列表额外带回 layoutConfig，供布局设计器再次打开已保存画布（契约字段之外的只读扩展）。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import tenant_of, user_names
from app.dc_trace import amounts_masked
from app.fin import money, session_period_month
from app.live import restrict_sessions, role_tags
from app.models import DcDashboard, DcSyncTask, FinProfit, LiveReport, LiveSession, User, UserDept

router = APIRouter(prefix="/dc/dashboard", tags=["dc-dashboard"])

BJ = timezone(timedelta(hours=8))
WIDGET_TYPES = {"METRIC_CARD", "TREND_CHART", "RANK_LIST", "HEALTH_PANEL"}
DIMENSIONS = {"PLATFORM", "ACCOUNT", "IP_GROUP", "TEAM", "REALNAME"}
DEFAULT_CRON = "0 * * * *"
HEALTH_TARGET = 98
FRESH_TARGET = 60
DWS_TASK = "DWD→DWS 聚合层刷新"
DEFAULT_TASKS = (
    ("ODS→DWD 业务台账同步", 12),
    (DWS_TASK, 28),
    ("DWS→ADS 看板缓存", 35),
)
PLATFORM_LABEL = {
    "DOUYIN": "抖音",
    "KUAISHOU": "快手",
    "XHS": "小红书",
    "XIAOHONGSHU": "小红书",
    "WECHAT_OFFICIAL": "公众号",
    "WECHAT_CHANNELS": "视频号",
}
MONTH_RE_LEN = 7


class DashboardBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    dashboardName: str | None = None
    layoutConfig: object | None = None
    refreshCron: str | None = None


def iso_utc(dt: datetime | None) -> str:
    if dt is None:
        return ""
    aware = dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def hour_stamp() -> str:
    now = datetime.now(BJ).replace(minute=0, second=0, microsecond=0)
    return now.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def shanghai_today() -> str:
    return datetime.now(BJ).strftime("%Y-%m-%d")


def can_configure(db: Session, actor: User) -> bool:
    tags = role_tags(db, actor)
    return bool(tags & {"r1", "r4", "sys:admin"})


def parse_month(stat_period: str):
    period = (stat_period or "").strip()
    if len(period) != MONTH_RE_LEN or period[4] != "-":
        return None
    year, month = period[:4], period[5:7]
    if not year.isdigit() or not month.isdigit():
        return None
    if not 1 <= int(month) <= 12:
        return None
    return period


def parse_day(value: str) -> str | None:
    text = (value or "").strip()[:10]
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        return None
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return text


def session_day(session: LiveSession) -> str:
    raw = (session.plan_start_time or session.actual_start or "")[:10]
    if parse_day(raw):
        return raw
    code = session.session_code or ""
    if code.startswith("IMS") and len(code) >= 11 and code[3:11].isdigit():
        return f"{code[3:7]}-{code[7:9]}-{code[9:11]}"
    return ""


def asset_ids_of(session: LiveSession) -> list[int]:
    try:
        raw = json.loads(session.device_asset_ids or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    found: list[int] = []
    for item in raw:
        if isinstance(item, bool):
            continue
        try:
            found.append(int(item))
        except (TypeError, ValueError):
            continue
    return found


def layout_of(raw: str) -> list:
    try:
        parsed = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def as_grid_int(value, low: int, high: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < low or value > high:
        return None
    return value


def normalize_layout(raw) -> tuple[list | None, str | None]:
    if raw is None:
        return [], None
    if not isinstance(raw, list):
        return None, "layoutConfig 须为组件数组"
    widgets: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            return None, "布局组件格式无效"
        key = str(item.get("widgetKey") or "").strip()
        if not key or len(key) > 64:
            return None, "widgetKey 必填且不超过 64 字"
        if key in seen:
            return None, "widgetKey 不能重复"
        seen.add(key)
        kind = str(item.get("widgetType") or "").strip().upper()
        if kind not in WIDGET_TYPES:
            return None, "组件类型仅支持指标卡、趋势图、排行、健康面板"
        position = item.get("position")
        if not isinstance(position, dict):
            return None, "组件位置无效"
        x = as_grid_int(position.get("x"), 0, 24)
        y = as_grid_int(position.get("y"), 0, 200)
        w = as_grid_int(position.get("w"), 1, 24)
        h = as_grid_int(position.get("h"), 1, 24)
        if None in (x, y, w, h):
            return None, "组件位置须为网格整数"
        config = item.get("config") if "config" in item else {}
        if not isinstance(config, dict):
            return None, "组件配置须为对象"
        widgets.append(
            {
                "widgetKey": key,
                "widgetType": kind,
                "position": {"x": x, "y": y, "w": w, "h": h},
                "config": config,
            }
        )
    return widgets, None


def normalize_cron(raw: str | None, fallback: str) -> tuple[str | None, str | None]:
    if raw is None:
        return fallback, None
    text = raw.strip()
    if not text:
        return fallback, None
    if len(text) > 64:
        return None, "refreshCron 过长"
    return text, None


def dashboard_vo(row: DcDashboard, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "dashboardName": row.dashboard_name,
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id, ""),
        "status": row.status,
        "refreshCron": row.refresh_cron or DEFAULT_CRON,
        "refreshedAt": iso_utc(row.refreshed_at or row.updated_at),
        "layoutConfig": layout_of(row.layout_config),
    }


def load_dashboard(db: Session, tenant_id: int, dashboard_id: int) -> DcDashboard | None:
    row = db.get(DcDashboard, dashboard_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    return row


def visible_sessions(db: Session, actor: User, scope, stat_period: str) -> list[LiveSession]:
    rows = list(db.scalars(restrict_sessions(select(LiveSession), actor, scope)).all())
    return [row for row in rows if session_period_month(row.plan_start_time or "", row.session_code) == stat_period]


def load_reports(db: Session, tenant_id: int, codes: list[str]) -> dict[str, LiveReport]:
    if not codes:
        return {}
    rows = db.scalars(
        select(LiveReport).where(
            LiveReport.deleted == 0,
            LiveReport.tenant_id == tenant_id,
            LiveReport.session_code.in_(codes),
        )
    ).all()
    return {row.session_code: row for row in rows}


def load_profits(db: Session, tenant_id: int, codes: list[str]) -> dict[str, FinProfit]:
    if not codes:
        return {}
    rows = db.scalars(
        select(FinProfit).where(
            FinProfit.deleted == 0,
            FinProfit.tenant_id == tenant_id,
            FinProfit.session_code.in_(codes),
        )
    ).all()
    return {row.session_code: row for row in rows}


def account_context(sessions: list[LiveSession]):
    from app.ops_db import ops_session
    from app.ops_models import IpGroup, PlatformAccount

    ids = {session.account_id for session in sessions if session.account_id}
    if not ids:
        return {}, {}
    ops = ops_session()
    try:
        accounts = {
            row.id: row
            for row in ops.scalars(
                select(PlatformAccount).where(PlatformAccount.id.in_(ids), PlatformAccount.deleted == 0)
            ).all()
        }
        group_ids = {row.ip_group_id for row in accounts.values() if row.ip_group_id}
        groups: dict[int, str] = {}
        if group_ids:
            group_rows = ops.scalars(select(IpGroup).where(IpGroup.id.in_(group_ids), IpGroup.deleted == 0)).all()
            groups = {row.id: row.group_name or f"IP组#{row.id}" for row in group_rows}
        return accounts, groups
    finally:
        ops.close()


def dept_labels(db: Session, tenant_id: int, user_ids: set[int]) -> dict[int, tuple[str, str]]:
    if not user_ids:
        return {}
    rows = db.scalars(
        select(UserDept).where(UserDept.user_id.in_(user_ids), UserDept.tenant_id == tenant_id)
    ).all()
    found: dict[int, tuple[str, str]] = {}
    for row in rows:
        if row.user_id not in found:
            found[row.user_id] = (str(row.dept_id), f"部门#{row.dept_id}")
    return found


def bucket_add(bucket: dict, gmv: float, profit: float) -> None:
    bucket["gmv"] += gmv
    bucket["netProfit"] += profit
    bucket["sessionCount"] += 1


def new_bucket(value: str, label: str) -> dict:
    return {
        "dimensionValue": value,
        "dimensionLabel": label,
        "gmv": 0.0,
        "netProfit": 0.0,
        "sessionCount": 0,
        "children": {},
    }


def dimension_key(
    session: LiveSession,
    dimension: str,
    accounts: dict,
    groups: dict[int, str],
    depts: dict[int, tuple[str, str]],
    names: dict[int, str],
) -> tuple[str, str, tuple[str, str] | None]:
    if dimension == "PLATFORM":
        value = session.platform or "UNKNOWN"
        account = accounts.get(session.account_id)
        number = (account.account_no if account else "") or session.account_no or str(session.account_id or 0)
        label_name = (account.account_name if account else "") or ""
        child = (number, f"{number} {label_name}".strip() or number)
        return value, PLATFORM_LABEL.get(value, value), child
    if dimension == "ACCOUNT":
        account = accounts.get(session.account_id)
        number = (account.account_no if account else "") or session.account_no or str(session.account_id or 0)
        label_name = (account.account_name if account else "") or ""
        return number, f"{number} {label_name}".strip() or number, None
    if dimension == "IP_GROUP":
        account = accounts.get(session.account_id)
        group_id = account.ip_group_id if account and account.ip_group_id else 0
        if not group_id:
            return "0", "未分配", None
        return str(group_id), groups.get(group_id) or f"IP组#{group_id}", None
    if dimension == "TEAM":
        pair = depts.get(int(session.responsible_user_id or 0))
        if pair is None:
            return "0", "未分配", None
        return pair[0], pair[1], None
    user_id = int(session.realname_person_id or 0)
    label = session.realname_name or names.get(user_id) or "未登记"
    return str(user_id or label), label, None


def money_or_mask(value: float, masked: bool):
    if masked:
        return None
    return money(value)


def ensure_sync_tasks(db: Session, tenant_id: int) -> list[DcSyncTask]:
    rows = list(
        db.scalars(
            select(DcSyncTask).where(DcSyncTask.deleted == 0, DcSyncTask.tenant_id == tenant_id).order_by(DcSyncTask.id.asc())
        ).all()
    )
    if rows:
        return rows
    now = utcnow()
    created: list[DcSyncTask] = []
    for name, delay in DEFAULT_TASKS:
        row = DcSyncTask(
            task_name=name,
            last_run_at=now - timedelta(minutes=delay),
            status="SUCCESS",
            delay_minutes=delay,
            tenant_id=tenant_id,
            created_at=now,
        )
        db.add(row)
        created.append(row)
    db.flush()
    return created


def task_view(row: DcSyncTask, now: datetime) -> dict:
    last = row.last_run_at or now
    delay = max(0, int((now - last).total_seconds() // 60))
    stored = (row.status or "SUCCESS").upper()
    if stored == "FAILED":
        status = "FAILED"
    elif delay > FRESH_TARGET:
        status = "DELAYED"
    else:
        status = "SUCCESS"
    return {
        "taskName": row.task_name,
        "lastRunAt": iso_utc(last),
        "status": status,
        "delayMinutes": delay,
        "_last": last,
    }


@router.get("/list")
def dashboard_list(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    rows = list(
        db.scalars(
            select(DcDashboard).where(DcDashboard.deleted == 0, DcDashboard.tenant_id == tenant_id)
        ).all()
    )
    rows.sort(key=lambda row: (0 if row.status == "ENABLED" else 1, row.id))
    names = user_names(db, {row.owner_user_id for row in rows})
    return ok([dashboard_vo(row, names) for row in rows])


@router.post("")
def dashboard_create(
    body: DashboardBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_configure(db, actor):
        return fail(1008, "仅管理员与运营总监可配置看板")
    name = (body.dashboardName or "").strip()
    if not name:
        return fail(1001, "看板名称必填")
    if len(name) > 64:
        return fail(1001, "看板名称不超过 64 字")
    widgets, error = normalize_layout(body.layoutConfig)
    if error:
        return fail(1001, error)
    cron, cron_error = normalize_cron(body.refreshCron, DEFAULT_CRON)
    if cron_error:
        return fail(1001, cron_error)
    now = utcnow()
    row = DcDashboard(
        dashboard_name=name,
        owner_user_id=actor.id,
        status="ENABLED",
        refresh_cron=cron or DEFAULT_CRON,
        layout_config=json.dumps(widgets or [], ensure_ascii=False),
        refreshed_at=now,
        tenant_id=tenant_of(actor),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return ok({"id": row.id, "dashboardName": row.dashboard_name})


@router.put("/{dashboard_id}")
def dashboard_update(
    dashboard_id: int,
    body: DashboardBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not can_configure(db, actor):
        return fail(1008, "仅管理员与运营总监可配置看板")
    row = load_dashboard(db, tenant_of(actor), dashboard_id)
    if row is None:
        return fail(1504, "看板不存在")
    if body.dashboardName is not None:
        name = body.dashboardName.strip()
        if not name:
            return fail(1001, "看板名称必填")
        if len(name) > 64:
            return fail(1001, "看板名称不超过 64 字")
        row.dashboard_name = name
    if body.layoutConfig is not None:
        widgets, error = normalize_layout(body.layoutConfig)
        if error:
            return fail(1001, error)
        row.layout_config = json.dumps(widgets or [], ensure_ascii=False)
    if body.refreshCron is not None:
        cron, cron_error = normalize_cron(body.refreshCron, row.refresh_cron or DEFAULT_CRON)
        if cron_error:
            return fail(1001, cron_error)
        row.refresh_cron = cron or DEFAULT_CRON
    now = utcnow()
    row.refreshed_at = now
    row.updated_at = now
    return ok(None)


@router.get("/freshness")
def dashboard_freshness(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    rows = ensure_sync_tasks(db, tenant_of(actor))
    now = utcnow()
    tasks = [task_view(row, now) for row in rows]
    dws = next((item for item in tasks if item["taskName"] == DWS_TASK), None)
    business_delay = dws["delayMinutes"] if dws else max((item["delayMinutes"] for item in tasks), default=0)
    alarm = business_delay > FRESH_TARGET or any(item["status"] != "SUCCESS" for item in tasks)
    stamps = [item["_last"] for item in tasks if item["status"] != "FAILED"]
    data_as_of = iso_utc(min(stamps) if stamps else now)
    public = [
        {
            "taskName": item["taskName"],
            "lastRunAt": item["lastRunAt"],
            "status": item["status"],
            "delayMinutes": item["delayMinutes"],
        }
        for item in tasks
    ]
    return ok(
        {
            "businessToDwsDelayMinutes": business_delay,
            "target": FRESH_TARGET,
            "isAlarm": alarm,
            "syncTaskStatus": public,
            "dataAsOf": data_as_of,
        }
    )


@router.get("/overview")
def dashboard_overview(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    del dimensionType
    period = parse_month(statPeriod)
    if period is None:
        return fail(1001, "统计周期须为 yyyy-MM")
    sessions = visible_sessions(db, actor, request.state.scope, period)
    codes = [row.session_code for row in sessions]
    tenant_id = tenant_of(actor)
    reports = load_reports(db, tenant_id, codes)
    profits = load_profits(db, tenant_id, codes)
    total_gmv = 0.0
    total_cost = 0.0
    net_profit = 0.0
    accounts: set[int] = set()
    assets: set[int] = set()
    for session in sessions:
        if session.account_id:
            accounts.add(session.account_id)
        assets.update(asset_ids_of(session))
        report = reports.get(session.session_code)
        if report is not None and report.entry_status == "CONFIRMED":
            total_gmv += float(report.gmv or 0)
        profit = profits.get(session.session_code)
        if profit is not None:
            total_cost += float(profit.total_cost or 0)
            net_profit += float(profit.net_profit or 0)
    masked = amounts_masked(db, actor, request)
    return ok(
        {
            "totalGmv": money_or_mask(total_gmv, masked),
            "totalCost": money_or_mask(total_cost, masked),
            "netProfit": money_or_mask(net_profit, masked),
            "sessionCount": len(sessions),
            "accountCount": len(accounts),
            "assetCount": len(assets),
            "dataAsOf": hour_stamp(),
            "refreshedAt": hour_stamp(),
        }
    )


@router.get("/health")
def dashboard_health(
    request: Request,
    dateRange: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    start, end = None, None
    text = (dateRange or "").strip()
    if text:
        parts = [part.strip()[:10] for part in text.split(",") if part.strip()]
        if len(parts) != 2:
            return fail(1001, "dateRange 须为开始日,结束日")
        start, end = parse_day(parts[0]), parse_day(parts[1])
        if start is None or end is None or start > end:
            return fail(1001, "dateRange 须为开始日,结束日")
    else:
        end = shanghai_today()
        start_dt = datetime.strptime(end, "%Y-%m-%d") - timedelta(days=29)
        start = start_dt.strftime("%Y-%m-%d")
    rows = list(db.scalars(restrict_sessions(select(LiveSession), actor, request.state.scope)).all())
    picked = []
    for session in rows:
        day = session_day(session)
        if day and start <= day <= end:
            picked.append((session, day))
    by_day: dict[str, list[LiveSession]] = {}
    for session, day in picked:
        by_day.setdefault(day, []).append(session)
    trend = []
    linked = 0
    digitized = 0
    traced = 0
    codes = [session.session_code for session, _day in picked]
    reports = load_reports(db, tenant_of(actor), codes)
    for day in sorted(by_day):
        day_rows = by_day[day]
        day_linked = sum(1 for session in day_rows if asset_ids_of(session))
        rate = round(day_linked * 100 / len(day_rows), 1)
        trend.append({"statDate": day, "completeRate": rate})
    for session, _day in picked:
        if asset_ids_of(session):
            linked += 1
        if session.account_id:
            digitized += 1
        report = reports.get(session.session_code)
        if report is not None and report.entry_status == "CONFIRMED":
            traced += 1
    total = len(picked)
    asset_rate = 100.0 if total == 0 else round(linked * 100 / total, 1)
    account_rate = 100.0 if total == 0 else round(digitized * 100 / total, 1)
    ledger_rate = 100.0 if total == 0 else round(traced * 100 / total, 1)
    return ok(
        {
            "assetRelationCompleteRate": asset_rate,
            "target": HEALTH_TARGET,
            "isAlarm": total > 0 and asset_rate < HEALTH_TARGET,
            "trend": trend,
            "accountDigitizationRate": account_rate,
            "ledgerTraceRate": ledger_rate,
        }
    )


@router.get("/dimension")
def dashboard_dimension(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "",
    drillTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    period = parse_month(statPeriod)
    if period is None:
        return fail(1001, "统计周期须为 yyyy-MM")
    dimension = (dimensionType or "").strip().upper()
    if dimension not in DIMENSIONS:
        return fail(1001, "维度仅支持平台、账号、IP组、团队、实名人")
    sessions = visible_sessions(db, actor, request.state.scope, period)
    accounts, groups = account_context(sessions)
    tenant_id = tenant_of(actor)
    user_ids = {int(session.responsible_user_id or 0) for session in sessions}
    user_ids.discard(0)
    depts = dept_labels(db, tenant_id, user_ids)
    names = user_names(db, user_ids)
    reports = load_reports(db, tenant_id, [session.session_code for session in sessions])
    profits = load_profits(db, tenant_id, [session.session_code for session in sessions])
    buckets: dict[str, dict] = {}
    for session in sessions:
        value, label, child = dimension_key(session, dimension, accounts, groups, depts, names)
        report = reports.get(session.session_code)
        gmv = float(report.gmv or 0) if report is not None and report.entry_status == "CONFIRMED" else 0.0
        profit_row = profits.get(session.session_code)
        profit = float(profit_row.net_profit or 0) if profit_row is not None else 0.0
        bucket = buckets.get(value)
        if bucket is None:
            bucket = new_bucket(value, label)
            buckets[value] = bucket
        bucket_add(bucket, gmv, profit)
        if child is not None:
            child_value, child_label = child
            child_bucket = bucket["children"].get(child_value)
            if child_bucket is None:
                child_bucket = {"dimensionValue": child_value, "dimensionLabel": child_label, "gmv": 0.0, "netProfit": 0.0, "sessionCount": 0}
                bucket["children"][child_value] = child_bucket
            bucket_add(child_bucket, gmv, profit)
    masked = amounts_masked(db, actor, request)
    drill = (drillTo or "").strip()
    payload = []
    for bucket in buckets.values():
        if drill and bucket["dimensionValue"] != drill:
            continue
        children = [
            {
                "dimensionValue": child["dimensionValue"],
                "gmv": money_or_mask(child["gmv"], masked),
                "netProfit": money_or_mask(child["netProfit"], masked),
                "sessionCount": child["sessionCount"],
            }
            for child in bucket["children"].values()
        ]
        item = {
            "dimensionValue": bucket["dimensionValue"],
            "dimensionLabel": bucket["dimensionLabel"],
            "gmv": money_or_mask(bucket["gmv"], masked),
            "netProfit": money_or_mask(bucket["netProfit"], masked),
            "sessionCount": bucket["sessionCount"],
        }
        if children:
            item["children"] = children
        payload.append(item)
    payload.sort(key=lambda item: (-item["sessionCount"], item["dimensionLabel"]))
    return ok(payload)
