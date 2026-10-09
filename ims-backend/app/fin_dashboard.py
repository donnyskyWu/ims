"""FIN-004 利润看板：按月汇总，下钻平台/账号/IP 组/达人/责任人，并导出 xlsx / pdf。

契约 DrillDim 没有「主体」。公司主体在账号 company_id 上，不作为本看板维度。
达人与责任人都取场次 responsible_user_id：场次表没有独立达人主键，分成单达人 targetRefId 同样取该字段。
总览按已核算利润实时汇总（刚核准的场次立刻可见）。refreshedAt 标到当前小时，作为 FIN-B-R1 的刷新时间。
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.corp import ops_db, tenant_of, user_names
from app.dc_trace import build_pdf, build_xlsx, matrix_lines
from app.fin import (
    AMOUNT_MASK,
    PERIOD_MONTH_RE,
    actor_masks_fin_amounts,
    collect_visible_profits,
    fin_view,
    mask_fin_amounts,
    money,
    net_profit_rate,
    operating_profit,
    profit_vo,
    session_period_month,
    visible_share_rows,
)
from app.live import BJ
from app.models import FinProfit, LiveSession, User
from app.ops_models import IpGroup, PlatformAccount

router = APIRouter(prefix="/fin/dashboard", tags=["fin-dashboard"])

DRILL_DIMS = ("PLATFORM", "ACCOUNT", "IP_GROUP", "DAREN", "OWNER")
PROFIT_TYPES = ("GROSS", "OPERATING", "NET")
GRANULARITY = ("DAY", "WEEK", "MONTH")
COST_ITEMS = (
    ("COMMISSION", "commission_amount"),
    ("AD", "ad_cost"),
    ("RECHARGE", "recharge_cost"),
    ("FIXED", "fixed_cost"),
    ("SAMPLE", "sample_cost"),
    ("SHARE_DAREN", "share_daren"),
    ("SHARE_REALNAME", "share_realname"),
)
PLATFORM_LABEL = {
    "DOUYIN": "抖音",
    "KUAISHOU": "快手",
    "XHS": "小红书",
    "XIAOHONGSHU": "小红书",
    "WECHAT_OFFICIAL": "公众号",
    "WECHAT_CHANNELS": "视频号",
}
XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MEDIA = "application/pdf"
EXPORT_TTL_SEC = 60
_EXPORTS: dict[str, tuple[float, bytes, str, str, int]] = {}


def hour_stamp() -> str:
    now = datetime.now(BJ).replace(minute=0, second=0, microsecond=0)
    return now.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_month(stat_period: str):
    period = (stat_period or "").strip()
    if not PERIOD_MONTH_RE.match(period):
        return None, fail(1001, "统计周期须为 yyyy-MM")
    return period, None


def parse_profit_type(profit_type: str) -> tuple[str | None, object | None]:
    kind = (profit_type or "NET").strip().upper() or "NET"
    if kind not in PROFIT_TYPES:
        return None, fail(1001, "口径仅支持 GROSS、OPERATING、NET")
    return kind, None


def shown_amount(profit: FinProfit, cost, profit_type: str) -> float:
    gross = money(profit.gross_profit)
    if profit_type == "GROSS":
        return gross
    if profit_type == "OPERATING":
        return operating_profit(gross, cost)
    return money(profit.net_profit)


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


def month_rows(db: Session, actor: User, scope, tenant_id: int, stat_period: str):
    rows = collect_visible_profits(db, actor, scope, tenant_id)
    return [(profit, session, cost) for profit, session, cost in rows if in_month(session, stat_period)]


def load_account_context(ops: Session, sessions: list[LiveSession]):
    ids = {session.account_id for session in sessions if session.account_id}
    accounts: dict[int, PlatformAccount] = {}
    groups: dict[int, str] = {}
    if not ids:
        return accounts, groups
    rows = ops.scalars(
        select(PlatformAccount).where(PlatformAccount.id.in_(ids), PlatformAccount.deleted == 0)
    ).all()
    accounts = {row.id: row for row in rows}
    group_ids = {row.ip_group_id for row in rows if row.ip_group_id}
    if group_ids:
        group_rows = ops.scalars(
            select(IpGroup).where(IpGroup.id.in_(group_ids), IpGroup.deleted == 0)
        ).all()
        groups = {row.id: row.group_name or f"IP组#{row.id}" for row in group_rows}
    return accounts, groups


def dimension_of(
    session: LiveSession,
    dimension: str,
    accounts: dict[int, PlatformAccount],
    groups: dict[int, str],
    names: dict[int, str],
) -> tuple[str, str]:
    if dimension == "PLATFORM":
        value = session.platform or "UNKNOWN"
        return value, PLATFORM_LABEL.get(value, value)
    if dimension == "ACCOUNT":
        account = accounts.get(session.account_id)
        number = (account.account_no if account else "") or session.account_no or str(session.account_id or 0)
        label_name = (account.account_name if account else "") or ""
        label = f"{number} {label_name}".strip()
        return number, label or number
    if dimension == "IP_GROUP":
        account = accounts.get(session.account_id)
        group_id = account.ip_group_id if account and account.ip_group_id else 0
        if not group_id:
            return "0", "未分配"
        return str(group_id), groups.get(group_id) or f"IP组#{group_id}"
    user_id = int(session.responsible_user_id or 0)
    name = names.get(user_id) or (f"用户#{user_id}" if user_id else "未分配")
    if dimension == "DAREN":
        return str(user_id), f"达人·{name}"
    return str(user_id), f"责任人·{name}"


def aggregate(rows, profit_type: str) -> dict:
    revenue = money(sum(profit.revenue for profit, _session, _cost in rows))
    refund = money(sum(profit.refund_amount for profit, _session, _cost in rows))
    total_cost = money(sum(profit.total_cost for profit, _session, _cost in rows))
    net = money(sum(profit.net_profit for profit, _session, _cost in rows))
    gross = money(sum(profit.gross_profit for profit, _session, _cost in rows))
    operating = money(sum(operating_profit(money(profit.gross_profit), cost) for profit, _session, cost in rows))
    shown = {"GROSS": gross, "OPERATING": operating, "NET": net}[profit_type]
    return {
        "totalGmv": revenue,
        "totalRefund": refund,
        "totalCost": total_cost,
        "grossProfit": gross,
        "operatingProfit": operating,
        "netProfit": net,
        "netProfitRate": net_profit_rate(revenue, refund, net),
        "shownProfit": shown,
        "shownProfitRate": net_profit_rate(revenue, refund, shown),
        "sessionCount": len(rows),
    }


def cost_structure(rows) -> list[dict]:
    amounts = {code: 0.0 for code, _attr in COST_ITEMS}
    for _profit, _session, cost in rows:
        if cost is None:
            continue
        for code, attr in COST_ITEMS:
            amounts[code] = money(amounts[code] + float(getattr(cost, attr) or 0))
    total = money(sum(amounts.values()))
    nonzero = [code for code, _attr in COST_ITEMS if amounts[code] > 0]
    items = []
    running = 0.0
    for code, _attr in COST_ITEMS:
        amount = amounts[code]
        if total <= 0 or amount <= 0:
            ratio = 0.0
        elif code == nonzero[-1]:
            ratio = round(1 - running, 4)
        else:
            ratio = round(amount / total, 4)
            running = round(running + ratio, 4)
        items.append({"costItem": code, "amount": amount, "ratio": ratio})
    return items


@router.get("/overview")
def dashboard_overview(
    request: Request,
    statPeriod: str = "",
    profitType: str = "NET",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    kind, err = parse_profit_type(profitType)
    if err is not None:
        return err
    rows = month_rows(db, actor, request.state.scope, tenant_of(actor), period)
    summary = aggregate(rows, kind or "NET")
    structure = cost_structure(rows)
    summary.update(
        {
            "profitType": kind,
            "statPeriod": period,
            "costStructureRatio": {item["costItem"]: item["ratio"] for item in structure},
            "refreshedAt": hour_stamp(),
        }
    )
    summary.pop("totalRefund", None)
    return ok(fin_view(db, actor, summary))


def bucket_of(day: str, granularity: str) -> str:
    if granularity == "MONTH":
        return day[:7]
    if granularity == "DAY":
        return day
    parsed = datetime.strptime(day, "%Y-%m-%d")
    iso = parsed.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def period_label(bucket: str, granularity: str) -> str:
    if granularity == "WEEK" and "-W" in bucket:
        week = int(bucket.split("-W", 1)[1])
        return f"第{week}~{week}周"
    return bucket


def previous_bucket(bucket: str, granularity: str) -> str | None:
    if granularity == "MONTH" and len(bucket) == 7:
        year, month = int(bucket[:4]), int(bucket[5:7])
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        return f"{year:04d}-{month:02d}"
    if granularity == "DAY" and len(bucket) == 10:
        parsed = datetime.strptime(bucket, "%Y-%m-%d") - timedelta(days=1)
        return parsed.strftime("%Y-%m-%d")
    if granularity == "WEEK" and "-W" in bucket:
        year, week = bucket.split("-W", 1)
        monday = datetime.fromisocalendar(int(year), int(week), 1) - timedelta(days=7)
        iso = monday.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return None


def yoy_bucket(bucket: str, granularity: str) -> str | None:
    if granularity == "MONTH" and len(bucket) == 7:
        return f"{int(bucket[:4]) - 1:04d}{bucket[4:]}"
    if granularity == "DAY" and len(bucket) == 10:
        try:
            parsed = datetime.strptime(bucket, "%Y-%m-%d").replace(year=int(bucket[:4]) - 1)
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d")
    if granularity == "WEEK" and "-W" in bucket:
        year, week = bucket.split("-W", 1)
        try:
            datetime.fromisocalendar(int(year) - 1, int(week), 1)
        except ValueError:
            return None
        return f"{int(year) - 1}-W{int(week):02d}"
    return None


def change_rate(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


def parse_date_range(date_range: str):
    parts = [part.strip()[:10] for part in (date_range or "").split(",") if part.strip()]
    if len(parts) != 2 or parts[0] > parts[1] or len(parts[0]) != 10 or len(parts[1]) != 10:
        return None, fail(1001, "dateRange 须为开始日,结束日")
    return parts, None


@router.get("/trend")
def dashboard_trend(
    request: Request,
    dateRange: str = "",
    granularity: str = "MONTH",
    profitType: str = "NET",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    grain = (granularity or "").strip().upper()
    if grain not in GRANULARITY:
        return fail(1001, "粒度仅支持 DAY、WEEK、MONTH")
    kind, err = parse_profit_type(profitType)
    if err is not None:
        return err
    bounds, err = parse_date_range(dateRange)
    if err is not None:
        return err
    start, end = bounds
    rows = collect_visible_profits(db, actor, request.state.scope, tenant_of(actor))
    grouped: dict[str, list] = {}
    for item in rows:
        _profit, session, _cost = item
        day = anchor_day(session)
        if not day or day < start or day > end:
            continue
        grouped.setdefault(bucket_of(day, grain), []).append(item)
    summaries = {bucket: aggregate(items, kind or "NET") for bucket, items in grouped.items()}
    points = []
    for bucket in sorted(summaries):
        summary = summaries[bucket]
        prev = summaries.get(previous_bucket(bucket, grain) or "")
        year_ago = summaries.get(yoy_bucket(bucket, grain) or "")
        points.append(
            {
                "statPeriod": bucket,
                "periodLabel": period_label(bucket, grain),
                "gmv": summary["totalGmv"],
                "cost": summary["totalCost"],
                "netProfit": summary["netProfit"],
                "netProfitRate": summary["netProfitRate"],
                "shownProfit": summary["shownProfit"],
                "momRate": change_rate(summary["shownProfit"], None if prev is None else prev["shownProfit"]),
                "yoyRate": change_rate(summary["shownProfit"], None if year_ago is None else year_ago["shownProfit"]),
            }
        )
    return ok(fin_view(db, actor, points))


def drill_items(
    db: Session,
    ops: Session,
    rows,
    dimension: str,
    profit_type: str,
    dimension_value: str,
    drill_to_session: bool,
) -> list[dict]:
    sessions = [session for _profit, session, _cost in rows]
    accounts, groups = load_account_context(ops, sessions)
    names = user_names(db, {int(session.responsible_user_id or 0) for session in sessions})
    grouped: dict[str, dict] = {}
    for profit, session, cost in rows:
        value, label = dimension_of(session, dimension, accounts, groups, names)
        if dimension_value and value != dimension_value:
            continue
        bucket = grouped.setdefault(
            value,
            {"dimensionValue": value, "dimensionLabel": label, "rows": []},
        )
        bucket["rows"].append((profit, session, cost))
    items = []
    for bucket in grouped.values():
        summary = aggregate(bucket["rows"], profit_type)
        item = {
            "dimensionValue": bucket["dimensionValue"],
            "dimensionLabel": bucket["dimensionLabel"],
            "totalGmv": summary["totalGmv"],
            "totalCost": summary["totalCost"],
            "netProfit": summary["netProfit"],
            "shownProfit": summary["shownProfit"],
            "sessionCount": summary["sessionCount"],
        }
        if drill_to_session:
            children = []
            for profit, session, cost in bucket["rows"]:
                child = profit_vo(db, profit, session, cost)
                child["shownProfit"] = shown_amount(profit, cost, profit_type)
                child["totalCost"] = money(profit.total_cost)
                child["accountNo"] = session.account_no
                children.append(child)
            item["children"] = children
        items.append(item)
    items.sort(key=lambda row: row["netProfit"], reverse=True)
    return items


@router.get("/drilldown")
def dashboard_drilldown(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "ACCOUNT",
    dimensionValue: str = "",
    drillToSession: bool = False,
    profitType: str = "NET",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    dimension = (dimensionType or "").strip().upper()
    if dimension not in DRILL_DIMS:
        return fail(1001, "维度仅支持 PLATFORM、ACCOUNT、IP_GROUP、DAREN、OWNER")
    kind, err = parse_profit_type(profitType)
    if err is not None:
        return err
    tenant_id = tenant_of(actor)
    rows = month_rows(db, actor, request.state.scope, tenant_id, period)
    return ok(
        fin_view(
            db,
            actor,
            drill_items(
                db,
                ops,
                rows,
                dimension,
                kind or "NET",
                (dimensionValue or "").strip(),
                drillToSession,
            ),
        )
    )


@router.get("/cost-structure")
def dashboard_cost_structure(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    if dimensionType and dimensionType.strip().upper() not in DRILL_DIMS:
        return fail(1001, "维度仅支持 PLATFORM、ACCOUNT、IP_GROUP、DAREN、OWNER")
    rows = month_rows(db, actor, request.state.scope, tenant_of(actor), period)
    return ok(fin_view(db, actor, cost_structure(rows)))


@router.get("/share-summary")
def dashboard_share_summary(
    request: Request,
    statPeriod: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    tenant_id = tenant_of(actor)
    shares = visible_share_rows(db, actor, request.state.scope, tenant_id)
    grouped: dict[tuple[str, int], dict] = {}
    for row in shares:
        session = db.scalar(
            select(LiveSession).where(
                LiveSession.session_code == row.session_code,
                LiveSession.deleted == 0,
                LiveSession.tenant_id == tenant_id,
            )
        )
        if session is None or not in_month(session, period):
            continue
        key = (row.share_target, int(row.target_ref_id or 0))
        bucket = grouped.setdefault(
            key,
            {
                "shareTarget": row.share_target,
                "targetRefId": int(row.target_ref_id or 0),
                "targetRefName": row.target_ref_name or "",
                "totalAmount": 0.0,
                "paidOffAmount": 0.0,
                "pendingAmount": 0.0,
                "sessions": set(),
            },
        )
        bucket["sessions"].add(row.session_code)
        if row.status == "REVERSED":
            continue
        bucket["totalAmount"] = money(bucket["totalAmount"] + money(row.share_amount))
        if row.status == "PAID_OFF":
            bucket["paidOffAmount"] = money(bucket["paidOffAmount"] + money(row.share_amount))
        elif row.status in ("PENDING_AUDIT", "AUDITED"):
            bucket["pendingAmount"] = money(bucket["pendingAmount"] + money(row.share_amount))
    data = []
    for bucket in grouped.values():
        data.append(
            {
                "shareTarget": bucket["shareTarget"],
                "targetRefId": bucket["targetRefId"],
                "targetRefName": bucket["targetRefName"],
                "totalAmount": bucket["totalAmount"],
                "sessionCount": len(bucket["sessions"]),
                "paidOffAmount": bucket["paidOffAmount"],
                "pendingAmount": bucket["pendingAmount"],
            }
        )
    data.sort(key=lambda item: item["totalAmount"], reverse=True)
    return ok(fin_view(db, actor, data))


def purge_exports(now: float) -> None:
    dead = [key for key, item in _EXPORTS.items() if item[0] < now]
    for key in dead:
        _EXPORTS.pop(key, None)


def export_money(value) -> str:
    if value == AMOUNT_MASK:
        return AMOUNT_MASK
    return f"{float(value or 0):.2f}"


def export_matrix(items: list[dict]) -> list[list[str]]:
    header = ["维度", "维度值", "场次", "GMV", "总成本", "净利润", "场次数"]
    body = [header]
    for item in items:
        body.append(
            [
                "汇总",
                str(item["dimensionLabel"]),
                "",
                export_money(item["totalGmv"]),
                export_money(item["totalCost"]),
                export_money(item["netProfit"]),
                str(item["sessionCount"]),
            ]
        )
        for child in item.get("children") or []:
            body.append(
                [
                    "场次",
                    str(item["dimensionLabel"]),
                    str(child.get("sessionCode") or ""),
                    export_money(child.get("gmv")),
                    export_money(child.get("totalCost")),
                    export_money(child.get("netProfit")),
                    "1",
                ]
            )
    return body


@router.get("/export")
def dashboard_export(
    request: Request,
    statPeriod: str = "",
    dimensionType: str = "ACCOUNT",
    format: str = "XLSX",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    period, err = parse_month(statPeriod)
    if err is not None:
        return err
    fmt = (format or "").strip().upper()
    if fmt not in ("XLSX", "PDF"):
        return fail(1001, "导出格式仅支持 XLSX 或 PDF")
    dimension = (dimensionType or "ACCOUNT").strip().upper()
    if dimension not in DRILL_DIMS:
        return fail(1001, "维度仅支持 PLATFORM、ACCOUNT、IP_GROUP、DAREN、OWNER")
    tenant_id = tenant_of(actor)
    rows = month_rows(db, actor, request.state.scope, tenant_id, period)
    items = drill_items(db, ops, rows, dimension, "NET", "", True)
    if actor_masks_fin_amounts(db, actor):
        items = mask_fin_amounts(items)
    matrix = export_matrix(items)
    if fmt == "PDF":
        body = build_pdf([f"FIN dashboard {period}", f"dimension {dimension}", *matrix_lines(matrix)])
        media = PDF_MEDIA
        filename = f"fin_dashboard_{period}.pdf"
    else:
        body = build_xlsx(matrix)
        media = XLSX_MEDIA
        filename = f"fin_dashboard_{period}.xlsx"
    now = time.time()
    purge_exports(now)
    token = secrets.token_urlsafe(24)
    _EXPORTS[token] = (now + EXPORT_TTL_SEC, body, media, filename, actor.id)
    return ok(
        {
            "downloadUrl": f"/admin-api/ims/fin/dashboard/export/file?token={token}",
            "expiresIn": EXPORT_TTL_SEC,
            "fileName": filename,
            "empty": len(items) == 0,
            "rowCount": max(len(matrix) - 1, 0),
        }
    )


@router.get("/export/file")
def dashboard_export_file(token: str, actor: User = Depends(current_user)):
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
