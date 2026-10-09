"""DC-003 全链路看板：经营总览、链路健康度、维度下钻到场次。

总览与下钻读已核算利润（与场次成本核准后的 ims_fin_profit 一致）。
健康度按日期范围内可见场次计算全链路关联，不回写业务表。
看板布局设计器与同步任务清单不在本模块。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.bi_br212 import primary_dept_id
from app.corp import ops_db, tenant_of
from app.dc_profit_trace import parse_asset_ids
from app.fin import collect_visible_profits, money, session_period_month
from app.live import BJ, restrict_sessions
from app.models import LiveReport, LiveSession, User
from app.ops_models import IpGroup, PlatformAccount

router = APIRouter(prefix="/dc/dashboard", tags=["dc-dashboard"])

OVERVIEW_DIMS = frozenset({"PLATFORM", "IP_GROUP", "TEAM"})
DRILL_DIMS = ("PLATFORM", "ACCOUNT", "IP_GROUP", "TEAM", "REALNAME")
HEALTH_TARGET = 98
PLATFORM_LABEL = {
    "DOUYIN": "抖音",
    "KUAISHOU": "快手",
    "XHS": "小红书",
    "XIAOHONGSHU": "小红书",
    "WECHAT_OFFICIAL": "公众号",
    "WECHAT_CHANNELS": "视频号",
}


def hour_stamp() -> str:
    now = datetime.now(BJ).replace(minute=0, second=0, microsecond=0)
    return now.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_month(stat_period: str):
    period = (stat_period or "").strip()
    if len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:7].isdigit():
        return None, fail(1001, "统计周期须为 yyyy-MM")
    month = int(period[5:7])
    if month < 1 or month > 12:
        return None, fail(1001, "统计周期须为 yyyy-MM")
    return period, None


def parse_date_range(raw: str):
    text = (raw or "").strip()
    if not text:
        now = datetime.now(BJ)
        start = now.replace(day=1)
        if now.month == 12:
            nxt = start.replace(year=now.year + 1, month=1)
        else:
            nxt = start.replace(month=now.month + 1)
        end = nxt - timedelta(days=1)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), None
    parts = [part.strip()[:10] for part in text.split(",") if part.strip()]
    if len(parts) != 2 or parts[0] > parts[1]:
        return None, None, fail(1001, "dateRange 须为开始日,结束日")
    try:
        datetime.strptime(parts[0], "%Y-%m-%d")
        datetime.strptime(parts[1], "%Y-%m-%d")
    except ValueError:
        return None, None, fail(1001, "dateRange 须为开始日,结束日")
    return parts[0], parts[1], None


def anchor_day(session: LiveSession) -> str:
    raw = (session.actual_start or session.plan_start_time or "")[:10]
    if len(raw) == 10 and raw[4] == "-":
        return raw
    code = session.session_code or ""
    if code.startswith("IMS") and len(code) >= 11 and code[3:11].isdigit():
        return f"{code[3:7]}-{code[7:9]}-{code[9:11]}"
    return ""


def in_month(session: LiveSession, stat_period: str) -> bool:
    return session_period_month(session.plan_start_time or "", session.session_code) == stat_period


def percent(hit: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round(hit * 100.0 / total, 1)


def visible_sessions(db: Session, actor: User, scope) -> list[LiveSession]:
    return list(db.scalars(restrict_sessions(select(LiveSession), actor, scope).order_by(LiveSession.id.desc())).all())


def month_profits(db: Session, actor: User, scope, tenant_id: int, stat_period: str):
    rows = collect_visible_profits(db, actor, scope, tenant_id)
    return [(profit, session, cost) for profit, session, cost in rows if in_month(session, stat_period)]


def chain_complete(session: LiveSession) -> bool:
    return bool(
        int(session.account_id or 0) > 0
        and int(session.realname_person_id or 0) > 0
        and int(session.responsible_user_id or 0) > 0
        and parse_asset_ids(session.device_asset_ids or "[]")
    )


def load_accounts(ops: Session, sessions: list[LiveSession]) -> tuple[dict[int, PlatformAccount], dict[int, str]]:
    ids = {int(session.account_id) for session in sessions if session.account_id}
    accounts: dict[int, PlatformAccount] = {}
    groups: dict[int, str] = {}
    if not ids:
        return accounts, groups
    rows = ops.scalars(select(PlatformAccount).where(PlatformAccount.id.in_(ids), PlatformAccount.deleted == 0)).all()
    accounts = {row.id: row for row in rows}
    group_ids = {row.ip_group_id for row in rows if row.ip_group_id}
    if group_ids:
        group_rows = ops.scalars(select(IpGroup).where(IpGroup.id.in_(group_ids), IpGroup.deleted == 0)).all()
        groups = {row.id: row.group_name or f"IP组#{row.id}" for row in group_rows}
    return accounts, groups


def dimension_of(
    db: Session,
    session: LiveSession,
    dimension: str,
    accounts: dict[int, PlatformAccount],
    groups: dict[int, str],
    tenant_id: int,
) -> tuple[str, str]:
    if dimension == "PLATFORM":
        value = session.platform or "UNKNOWN"
        return value, PLATFORM_LABEL.get(value, value)
    if dimension == "ACCOUNT":
        account = accounts.get(int(session.account_id or 0))
        number = (account.account_no if account else "") or session.account_no or str(session.account_id or 0)
        label_name = (account.account_name if account else "") or ""
        label = f"{number} {label_name}".strip()
        return number or "0", label or number or "未分配"
    if dimension == "IP_GROUP":
        account = accounts.get(int(session.account_id or 0))
        group_id = int(account.ip_group_id) if account and account.ip_group_id else 0
        if not group_id:
            return "0", "未分配"
        return str(group_id), groups.get(group_id) or f"IP组#{group_id}"
    if dimension == "REALNAME":
        person_id = int(session.realname_person_id or 0)
        if not person_id:
            return "0", "未分配"
        name = (session.realname_name or "").strip() or f"实名人#{person_id}"
        return str(person_id), name
    user_id = int(session.responsible_user_id or 0)
    dept_id = primary_dept_id(db, user_id, tenant_id) if user_id else 0
    if not dept_id:
        return "0", "未分配"
    return str(dept_id), f"部门#{dept_id}"


@router.get("/overview")
def dashboard_overview(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    kind = (dimensionType or "").strip().upper()
    if kind and kind not in OVERVIEW_DIMS:
        return fail(1001, "总览维度仅支持 PLATFORM、IP_GROUP、TEAM")
    rows = month_profits(db, actor, request.state.scope, tenant_of(actor), period)
    gmv = money(sum(profit.revenue for profit, _session, _cost in rows))
    total_cost = money(sum(profit.total_cost for profit, _session, _cost in rows))
    net = money(sum(profit.net_profit for profit, _session, _cost in rows))
    accounts = {int(session.account_id) for _profit, session, _cost in rows if session.account_id}
    assets: set[int] = set()
    for _profit, session, _cost in rows:
        assets.update(parse_asset_ids(session.device_asset_ids or "[]"))
    stamped = hour_stamp()
    return ok(
        {
            "totalGmv": gmv,
            "totalCost": total_cost,
            "netProfit": net,
            "sessionCount": len(rows),
            "accountCount": len(accounts),
            "assetCount": len(assets),
            "dataAsOf": stamped,
            "refreshedAt": stamped,
            "statPeriod": period,
        }
    )


@router.get("/health")
def dashboard_health(
    request: Request,
    dateRange: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    start, end, err = parse_date_range(dateRange)
    if err is not None:
        return err
    sessions = [
        session
        for session in visible_sessions(db, actor, request.state.scope)
        if start <= anchor_day(session) <= end
    ]
    complete = sum(1 for session in sessions if chain_complete(session))
    relation = percent(complete, len(sessions))
    account_ids = {int(session.account_id) for session in sessions if session.account_id}
    digitized = 0
    if account_ids:
        found = ops.scalars(
            select(PlatformAccount.id).where(PlatformAccount.id.in_(account_ids), PlatformAccount.deleted == 0)
        ).all()
        digitized = len(set(found))
    codes = [session.session_code for session in sessions if session.session_code]
    traced = 0
    if codes:
        reported = db.scalars(
            select(LiveReport.session_code).where(
                LiveReport.deleted == 0,
                LiveReport.tenant_id == tenant_of(actor),
                LiveReport.session_code.in_(codes),
            )
        ).all()
        traced = len(set(reported))
    by_day: dict[str, list[LiveSession]] = {}
    for session in sessions:
        by_day.setdefault(anchor_day(session), []).append(session)
    trend = [
        {
            "statDate": day,
            "completeRate": percent(sum(1 for session in rows if chain_complete(session)), len(rows)),
        }
        for day, rows in sorted(by_day.items())
    ]
    return ok(
        {
            "assetRelationCompleteRate": relation,
            "target": HEALTH_TARGET,
            "isAlarm": relation < HEALTH_TARGET,
            "trend": trend,
            "accountDigitizationRate": percent(digitized, len(account_ids)),
            "ledgerTraceRate": percent(traced, len(sessions)),
            "dateRange": [start, end],
        }
    )


@router.get("/dimension")
def dashboard_dimension(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "PLATFORM",
    drillTo: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    dimension = (dimensionType or "").strip().upper()
    if dimension not in DRILL_DIMS:
        return fail(1001, "维度仅支持 PLATFORM、ACCOUNT、IP_GROUP、TEAM、REALNAME")
    tenant_id = tenant_of(actor)
    rows = month_profits(db, actor, request.state.scope, tenant_id, period)
    sessions = [session for _profit, session, _cost in rows]
    accounts, groups = load_accounts(ops, sessions)
    target = (drillTo or "").strip()
    grouped: dict[str, dict] = {}
    for profit, session, _cost in rows:
        value, label = dimension_of(db, session, dimension, accounts, groups, tenant_id)
        if target and value != target:
            continue
        bucket = grouped.setdefault(
            value,
            {"dimensionValue": value, "dimensionLabel": label, "gmv": 0.0, "netProfit": 0.0, "children": []},
        )
        bucket["gmv"] = money(bucket["gmv"] + float(profit.revenue or 0))
        bucket["netProfit"] = money(bucket["netProfit"] + float(profit.net_profit or 0))
        bucket["children"].append(
            {
                "dimensionValue": session.session_code,
                "gmv": money(profit.revenue),
                "netProfit": money(profit.net_profit),
                "sessionCount": 1,
            }
        )
    items = []
    for bucket in grouped.values():
        children = sorted(bucket["children"], key=lambda row: row["gmv"] or 0, reverse=True)
        items.append(
            {
                "dimensionValue": bucket["dimensionValue"],
                "dimensionLabel": bucket["dimensionLabel"],
                "gmv": bucket["gmv"],
                "netProfit": bucket["netProfit"],
                "sessionCount": len(children),
                "children": children,
            }
        )
    items.sort(key=lambda row: row["gmv"] or 0, reverse=True)
    return ok(items)
