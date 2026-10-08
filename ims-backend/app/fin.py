"""场次财务 FIN-001 成本录入 · FIN-002 利润列表（W8-1/W8-2）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, tenant_of, user_names
from app.live import get_session, iso, restrict_sessions
from app.models import FinCost, FinProfit, LiveReport, LiveSession, User

router = APIRouter(prefix="/fin", tags=["fin"])

BJ = timezone(timedelta(hours=8))
SHARE_TYPES = frozenset({"MANUAL", "ENGINE"})
ENTRY_STATUSES = frozenset({"DRAFT", "SUBMITTED", "CONFIRMED"})


class FinCostEntryBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    commissionRate: float = Field(ge=0, le=1)
    adCost: float = Field(ge=0, default=0)
    rechargeCost: float = Field(ge=0, default=0)
    fixedCost: float = Field(ge=0, default=0)
    sampleCost: float = Field(ge=0, default=0)
    shareCostType: str = "MANUAL"
    shareDaren: float = Field(ge=0, default=0)
    shareRealname: float = Field(ge=0, default=0)
    remark: str = ""
    asDraft: bool = False


def money(value: float) -> float:
    return round(float(value or 0), 2)


def approved_report(db: Session, session_code: str, tenant_id: int) -> LiveReport | None:
    report = db.scalar(
        select(LiveReport).where(
            LiveReport.session_code == session_code,
            LiveReport.deleted == 0,
            LiveReport.tenant_id == tenant_id,
            LiveReport.entry_status == "CONFIRMED",
        )
    )
    return report


def load_fin_cost(db: Session, tenant_id: int, session_code: str) -> FinCost | None:
    return db.scalar(
        select(FinCost).where(
            FinCost.session_code == session_code,
            FinCost.deleted == 0,
            FinCost.tenant_id == tenant_id,
        )
    )


def calc_amounts(gmv: float, body: FinCostEntryBody) -> dict[str, float]:
    commission = money(gmv * body.commissionRate)
    total = money(
        commission
        + body.adCost
        + body.rechargeCost
        + body.fixedCost
        + body.sampleCost
        + body.shareDaren
        + body.shareRealname
    )
    return {"commissionAmount": commission, "totalCost": total}


def validate_body(body: FinCostEntryBody) -> str | None:
    if body.shareCostType not in SHARE_TYPES:
        return "分成方式无效"
    if body.shareCostType == "MANUAL" and (body.shareDaren < 0 or body.shareRealname < 0):
        return "分成金额无效"
    return None


def cost_vo(db: Session, row: FinCost) -> dict:
    names = user_names(db, [row.entry_user_id])
    return {
        "id": row.id,
        "sessionCode": row.session_code,
        "platform": row.platform,
        "costGmv": money(row.cost_gmv),
        "costRefund": money(row.cost_refund),
        "commissionRate": round(float(row.commission_rate or 0), 4),
        "commissionAmount": money(row.commission_amount),
        "adCost": money(row.ad_cost),
        "rechargeCost": money(row.recharge_cost),
        "fixedCost": money(row.fixed_cost),
        "sampleCost": money(row.sample_cost),
        "shareDaren": money(row.share_daren),
        "shareRealname": money(row.share_realname),
        "shareCostType": row.share_cost_type,
        "totalCost": money(row.total_cost),
        "entryStatus": row.entry_status,
        "entryUserId": row.entry_user_id,
        "entryUserName": names.get(row.entry_user_id, ""),
        "entryAt": iso(row.entry_at) if row.entry_at else "",
        "clientToken": row.client_token or "",
        "remark": row.remark or "",
    }


def hours_since(ts: str | None) -> float:
    if not ts:
        return 0.0
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    delta = utcnow().replace(tzinfo=BJ) - dt.astimezone(BJ)
    return round(max(delta.total_seconds(), 0) / 3600, 1)


def session_fin_visible(db: Session, actor: User, scope, session: LiveSession) -> bool:
    stmt = restrict_sessions(select(LiveSession.id), actor, scope).where(LiveSession.id == session.id)
    return db.scalar(stmt) is not None


def apply_cost_row(row: FinCost, session: LiveSession, report: LiveReport, body: FinCostEntryBody, actor: User) -> None:
    amounts = calc_amounts(float(report.gmv or 0), body)
    row.platform = session.platform
    row.cost_gmv = money(report.gmv)
    row.cost_refund = money(report.refund_amount)
    row.commission_rate = round(body.commissionRate, 4)
    row.commission_amount = amounts["commissionAmount"]
    row.ad_cost = money(body.adCost)
    row.recharge_cost = money(body.rechargeCost)
    row.fixed_cost = money(body.fixedCost)
    row.sample_cost = money(body.sampleCost)
    row.share_daren = money(body.shareDaren)
    row.share_realname = money(body.shareRealname)
    row.share_cost_type = body.shareCostType
    row.total_cost = amounts["totalCost"]
    row.entry_status = "DRAFT" if body.asDraft else "SUBMITTED"
    row.entry_user_id = actor.id
    row.entry_at = utcnow()
    row.remark = body.remark or ""


def upsert_profit(db: Session, session_code: str, report: LiveReport, cost: FinCost, tenant_id: int) -> FinProfit:
    revenue = money(report.gmv)
    refund = money(report.refund_amount)
    total_cost = money(cost.total_cost)
    gross = money(revenue - refund - cost.commission_amount)
    net = money(revenue - refund - total_cost)
    profit = load_profit(db, tenant_id, session_code)
    if profit is None:
        profit = FinProfit(session_code=session_code, tenant_id=tenant_id)
        db.add(profit)
    profit.revenue = revenue
    profit.refund_amount = refund
    profit.total_cost = total_cost
    profit.gross_profit = gross
    profit.net_profit = net
    profit.calc_status = "CALCULATED"
    profit.calc_version = (profit.calc_version or 0) + 1
    db.flush()
    return profit


def load_profit(db: Session, tenant_id: int, session_code: str) -> FinProfit | None:
    return db.scalar(
        select(FinProfit).where(
            FinProfit.session_code == session_code,
            FinProfit.deleted == 0,
            FinProfit.tenant_id == tenant_id,
        )
    )


def operating_profit(gross: float, cost: FinCost | None) -> float:
    if cost is None:
        return money(gross)
    return money(gross - float(cost.ad_cost or 0) - float(cost.recharge_cost or 0))


def net_profit_rate(revenue: float, refund: float, net: float) -> float:
    base = money(revenue) - money(refund)
    if base <= 0:
        return 0.0
    return round(net * 100 / base, 2)


def calc_rule_snapshot(profit: FinProfit, cost: FinCost | None) -> dict:
    params: dict[str, float] = {
        "revenue": money(profit.revenue),
        "refund": money(profit.refund_amount),
        "totalCost": money(profit.total_cost),
    }
    if cost is not None:
        params.update(
            {
                "commissionAmount": money(cost.commission_amount),
                "adCost": money(cost.ad_cost),
                "rechargeCost": money(cost.recharge_cost),
                "fixedCost": money(cost.fixed_cost),
                "sampleCost": money(cost.sample_cost),
                "shareDaren": money(cost.share_daren),
                "shareRealname": money(cost.share_realname),
            }
        )
    return {
        "formula": "netProfit = revenue - refund - totalCost; grossProfit = revenue - refund - commission",
        "params": params,
    }


def settlement_status(calc_status: str) -> str:
    if calc_status in ("", "PENDING"):
        return "PENDING_CALC"
    if calc_status == "CALCULATED":
        return "READY"
    if calc_status == "RECALCULATED":
        return "IN_SETTLEMENT"
    return "DONE"


def profit_vo(
    db: Session,
    profit: FinProfit,
    session: LiveSession,
    cost: FinCost | None,
    *,
    include_session: bool = True,
) -> dict:
    gross = money(profit.gross_profit)
    operating = operating_profit(gross, cost)
    net = money(profit.net_profit)
    vo = {
        "id": profit.id,
        "sessionCode": profit.session_code,
        "grossProfit": gross,
        "operatingProfit": operating,
        "netProfit": net,
        "netProfitRate": net_profit_rate(profit.revenue, profit.refund_amount, net),
        "calcRuleSnapshot": calc_rule_snapshot(profit, cost),
        "calcVersion": profit.calc_version or 1,
        "calcStatus": profit.calc_status or "PENDING",
        "calculatedAt": iso(profit.updated_at) if profit.updated_at else "",
        "settlementStatus": settlement_status(profit.calc_status or "PENDING"),
    }
    if include_session:
        vo.update(
            {
                "platform": session.platform,
                "sessionTitle": session.topic or session.session_code,
                "gmv": money(profit.revenue),
            }
        )
    return vo


def session_in_date_range(session: LiveSession, date_from: str, date_to: str) -> bool:
    anchor = (session.actual_start or session.plan_start_time or "")[:10]
    if not anchor:
        return True
    if date_from and anchor < date_from:
        return False
    if date_to and anchor > date_to:
        return False
    return True


def collect_visible_profits(
    db: Session,
    actor: User,
    scope,
    tenant_id: int,
    *,
    session_code: str = "",
    platform: str = "",
    calc_status: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[tuple[FinProfit, LiveSession, FinCost | None]]:
    stmt = select(FinProfit).where(FinProfit.deleted == 0, FinProfit.tenant_id == tenant_id)
    if session_code:
        stmt = stmt.where(FinProfit.session_code.contains(session_code))
    if calc_status:
        stmt = stmt.where(FinProfit.calc_status == calc_status)
    rows = db.scalars(stmt.order_by(FinProfit.id.desc())).all()
    items: list[tuple[FinProfit, LiveSession, FinCost | None]] = []
    for profit in rows:
        session = db.scalar(
            select(LiveSession).where(
                LiveSession.session_code == profit.session_code,
                LiveSession.deleted == 0,
                LiveSession.tenant_id == tenant_id,
            )
        )
        if session is None:
            continue
        if platform and session.platform != platform:
            continue
        if not session_in_date_range(session, date_from, date_to):
            continue
        if not session_fin_visible(db, actor, scope, session):
            continue
        cost = load_fin_cost(db, tenant_id, profit.session_code)
        items.append((profit, session, cost))
    return items


@router.get("/profit/list")
def profit_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    platform: str = "",
    calcStatus: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    visible = collect_visible_profits(
        db,
        actor,
        request.state.scope,
        tenant_id,
        session_code=sessionCode,
        platform=platform,
        calc_status=calcStatus,
        date_from=dateFrom,
        date_to=dateTo,
    )
    total = len(visible)
    start = (page_no - 1) * size
    page_items = visible[start : start + size]
    return ok(
        {
            "list": [profit_vo(db, p, s, c) for p, s, c in page_items],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
        }
    )


@router.get("/profit/summary")
def profit_summary(
    request: Request,
    dateFrom: str = "",
    dateTo: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    visible = collect_visible_profits(
        db,
        actor,
        request.state.scope,
        tenant_id,
        date_from=dateFrom,
        date_to=dateTo,
    )
    calculated = [item for item in visible if item[0].calc_status in ("CALCULATED", "RECALCULATED")]
    total_revenue = sum(money(p.revenue) for p, _, _ in calculated)
    total_cost = sum(money(p.total_cost) for p, _, _ in calculated)
    total_net = sum(money(p.net_profit) for p, _, _ in calculated)
    ready = sum(1 for p, _, _ in calculated if settlement_status(p.calc_status) == "READY")
    in_settlement = sum(1 for p, _, _ in calculated if settlement_status(p.calc_status) == "IN_SETTLEMENT")
    return ok(
        {
            "sessionCount": len(calculated),
            "totalRevenue": money(total_revenue),
            "totalCost": money(total_cost),
            "totalNetProfit": money(total_net),
            "readySettlementCount": ready,
            "inSettlementCount": in_settlement,
        }
    )


@router.get("/profit/{session_code}")
def profit_detail(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    profit = load_profit(db, tenant_id, session_code)
    cost = load_fin_cost(db, tenant_id, session_code)
    if profit is None or profit.calc_status in ("", "PENDING") or cost is None or cost.entry_status != "CONFIRMED":
        return fail(1145, "该场次成本未核准，利润未计算")
    return ok(profit_vo(db, profit, session, cost, include_session=True))


@router.get("/cost/pending-sessions")
def cost_pending_sessions(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    platform: str = "",
    sessionCode: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    scope = request.state.scope
    stmt = restrict_sessions(select(LiveSession), actor, scope)
    if platform:
        stmt = stmt.where(LiveSession.platform == platform)
    if sessionCode:
        stmt = stmt.where(LiveSession.session_code.contains(sessionCode))
    sessions = db.scalars(stmt.order_by(LiveSession.id.desc())).all()
    entered = {
        row.session_code
        for row in db.scalars(
            select(FinCost).where(FinCost.deleted == 0, FinCost.tenant_id == tenant_id)
        ).all()
    }
    items: list[dict] = []
    for session in sessions:
        if session.session_code in entered:
            continue
        report = approved_report(db, session.session_code, tenant_id)
        if report is None:
            continue
        approved_at = report.submitted_at or iso(report.updated_at) or ""
        hrs = hours_since(approved_at)
        items.append(
            {
                "sessionCode": session.session_code,
                "platform": session.platform,
                "sessionTitle": session.topic or session.session_code,
                "gmv": money(report.gmv),
                "refund": money(report.refund_amount),
                "adCost": money(report.ad_cost),
                "approvedAt": approved_at or "",
                "hoursSinceApprove": hrs,
                "isOver48h": hrs >= 48,
            }
        )
    total = len(items)
    start = (page_no - 1) * size
    page_items = items[start : start + size]
    return ok({"list": page_items, "total": total, "pageNo": page_no, "pageSize": size})


@router.get("/cost/list")
def cost_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    entryStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    stmt = select(FinCost).where(FinCost.deleted == 0, FinCost.tenant_id == tenant_id)
    if sessionCode:
        stmt = stmt.where(FinCost.session_code.contains(sessionCode))
    if entryStatus:
        stmt = stmt.where(FinCost.entry_status == entryStatus)
    rows = db.scalars(stmt.order_by(FinCost.id.desc())).all()
    visible: list[FinCost] = []
    for row in rows:
        session = db.scalar(
            select(LiveSession).where(
                LiveSession.session_code == row.session_code,
                LiveSession.deleted == 0,
                LiveSession.tenant_id == tenant_id,
            )
        )
        if session is None:
            continue
        if not session_fin_visible(db, actor, request.state.scope, session):
            continue
        visible.append(row)
    total = len(visible)
    start = (page_no - 1) * size
    page_rows = visible[start : start + size]
    return ok(
        {
            "list": [cost_vo(db, row) for row in page_rows],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
        }
    )


@router.get("/cost/complete-rate")
def cost_complete_rate(
    request: Request,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    scope = request.state.scope
    stmt = restrict_sessions(select(LiveSession), actor, scope)
    sessions = db.scalars(stmt).all()
    approved_codes: list[str] = []
    unentered: list[dict] = []
    for session in sessions:
        report = approved_report(db, session.session_code, tenant_id)
        if report is None:
            continue
        approved_codes.append(session.session_code)
        cost = load_fin_cost(db, tenant_id, session.session_code)
        if cost is None or cost.entry_status == "DRAFT":
            approved_at = report.submitted_at or iso(report.updated_at) or ""
            hrs = hours_since(approved_at)
            if hrs >= 48:
                unentered.append(
                    {
                        "sessionCode": session.session_code,
                        "platform": session.platform,
                        "approvedAt": approved_at or "",
                        "hoursSinceApprove": hrs,
                    }
                )
    entered_count = sum(
        1
        for code in approved_codes
        if (c := load_fin_cost(db, tenant_id, code)) is not None and c.entry_status in ("SUBMITTED", "CONFIRMED")
    )
    approved_count = len(approved_codes)
    rate = round(entered_count * 100 / approved_count, 2) if approved_count else 100.0
    return ok(
        {
            "approvedSessionCount": approved_count,
            "costEnteredCount": entered_count,
            "completeRate": rate,
            "unenteredOver48h": unentered,
        }
    )


@router.post("/cost/{session_code}")
def cost_submit(
    request: Request,
    session_code: str,
    body: FinCostEntryBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
    clientToken: str | None = Header(default=None),
):
    if not clientToken:
        return fail(1001, "clientToken 必填")
    err = validate_body(body)
    if err:
        return fail(1001, err)
    tenant_id = tenant_of(actor)
    existing_token = db.scalar(
        select(FinCost).where(
            FinCost.client_token == clientToken,
            FinCost.deleted == 0,
            FinCost.tenant_id == tenant_id,
        )
    )
    if existing_token:
        return ok(cost_vo(db, existing_token))
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    report = approved_report(db, session_code, tenant_id)
    if report is None:
        return fail(1141, "场次未核准下播数据")
    row = load_fin_cost(db, tenant_id, session_code)
    if row is not None and row.entry_status == "CONFIRMED":
        return fail(1142, "成本已核准不可重复录入")
    if row is None:
        row = FinCost(session_code=session_code, tenant_id=tenant_id, client_token=clientToken)
        db.add(row)
    apply_cost_row(row, session, report, body, actor)
    row.client_token = clientToken
    db.flush()
    return ok(cost_vo(db, row))


@router.get("/cost/{session_code}")
def cost_detail(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    row = load_fin_cost(db, tenant_id, session_code)
    if row is None:
        return fail(1141, "成本未录入")
    return ok(cost_vo(db, row))


@router.put("/cost/{session_code}")
def cost_update(
    request: Request,
    session_code: str,
    body: FinCostEntryBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    err = validate_body(body)
    if err:
        return fail(1001, err)
    tenant_id = tenant_of(actor)
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    report = approved_report(db, session_code, tenant_id)
    if report is None:
        return fail(1141, "场次未核准下播数据")
    row = load_fin_cost(db, tenant_id, session_code)
    if row is None:
        return fail(1141, "成本未录入")
    if row.entry_status == "CONFIRMED":
        return fail(1142, "成本已核准")
    apply_cost_row(row, session, report, body, actor)
    db.flush()
    return ok(cost_vo(db, row))


@router.put("/cost/{session_code}/confirm")
def cost_confirm(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    report = approved_report(db, session_code, tenant_id)
    if report is None:
        return fail(1141, "场次未核准下播数据")
    row = load_fin_cost(db, tenant_id, session_code)
    if row is None or row.entry_status not in ("DRAFT", "SUBMITTED"):
        return fail(1141, "成本未提交")
    row.entry_status = "CONFIRMED"
    profit = upsert_profit(db, session_code, report, row, tenant_id)
    db.flush()
    return ok(
        {
            "entryStatus": "CONFIRMED",
            "profitTaskId": f"PT-{profit.id}",
            "message": "成本已核准，利润已计算",
        }
    )
