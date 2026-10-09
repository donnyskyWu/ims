"""场次财务 FIN-001 成本录入 · FIN-002 利润列表（W8-1/W8-2）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, tenant_of, user_names
from app.live import get_session, iso, restrict_sessions
from app.models import (
    FinCost,
    FinPeriod,
    FinProfit,
    FinShareResult,
    FlowInstance,
    LiveReport,
    LiveSession,
    OperateLog,
    User,
)

router = APIRouter(prefix="/fin", tags=["fin"])

BJ = timezone(timedelta(hours=8))
SHARE_TYPES = frozenset({"MANUAL", "ENGINE"})
ENTRY_STATUSES = frozenset({"DRAFT", "SUBMITTED", "CONFIRMED"})
AUDIT_ROLES = frozenset({"FINANCE", "BUSINESS"})
LOCKED_SHARE_STATUSES = frozenset({"AUDITED", "PAID_OFF", "REVERSED"})
PERIOD_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
LOCK_MSG = "财务期间已结账，录入/核准/更正均冻结"
LOCK_ADJUST_MSG = "周期已锁定，锁后更正须 R4 审批"
LOCK_ADJUST_PREFIX = "FIN-LOCK-"


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


class FinCostCorrectionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    corrected: FinCostEntryBody
    correctionReason: str = Field(min_length=1)


class FinShareAuditBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    conclusion: str
    remark: str = ""
    auditRole: str


class FinSharePayoffVoucher(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    fileName: str = ""
    fileKey: str = ""


class FinSharePayoffBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    payoffVoucher: FinSharePayoffVoucher | None = None
    payoffNote: str = ""
    # 契约 2.3.8：负向调整走冲销，不另开 REST。reverse=true 时本接口改为红冲。
    reverse: bool = False
    reverseReason: str = ""


class FinPeriodCloseBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    periodMonth: str = ""


def money(value: float) -> float:
    return round(float(value or 0), 2)


def session_period_month(plan_start_time: str, session_code: str) -> str:
    """期间取计划开播月；无计划开播时回退场次号 IMS+yyyyMMdd。"""
    raw = (plan_start_time or "").strip()
    if len(raw) >= 7 and raw[4] == "-" and raw[:4].isdigit() and raw[5:7].isdigit():
        month = int(raw[5:7])
        if 1 <= month <= 12:
            return raw[:7]
    if session_code.startswith("IMS") and len(session_code) >= 11 and session_code[3:11].isdigit():
        return f"{session_code[3:7]}-{session_code[7:9]}"
    return datetime.now(BJ).strftime("%Y-%m")


def load_period(db: Session, tenant_id: int, period_month: str) -> FinPeriod | None:
    return db.scalar(
        select(FinPeriod).where(
            FinPeriod.tenant_id == tenant_id,
            FinPeriod.period_month == period_month,
            FinPeriod.deleted == 0,
        )
    )


def finance_status_of(db: Session, tenant_id: int, period_month: str) -> str:
    row = load_period(db, tenant_id, period_month)
    if row is not None and row.finance_status == "LOCKED":
        return "LOCKED"
    return "OPEN"


def period_of_session(db: Session, tenant_id: int, session: LiveSession) -> tuple[str, str]:
    month = session_period_month(session.plan_start_time or "", session.session_code)
    return month, finance_status_of(db, tenant_id, month)


def reject_if_period_locked(db: Session, tenant_id: int, session: LiveSession):
    _month, status = period_of_session(db, tenant_id, session)
    if status == "LOCKED":
        return fail(1142, LOCK_MSG)
    return None


def lock_adjust_key(session_code: str) -> str:
    return f"{LOCK_ADJUST_PREFIX}{session_code}"


def lock_adjust_approved(db: Session, tenant_id: int, session_code: str) -> bool:
    row = db.scalar(
        select(FlowInstance).where(
            FlowInstance.deleted == 0,
            FlowInstance.tenant_id == tenant_id,
            FlowInstance.business_key == lock_adjust_key(session_code),
            FlowInstance.instance_status == "APPROVED",
        )
    )
    return row is not None


def reject_locked_correction(db: Session, tenant_id: int, session: LiveSession):
    _month, status = period_of_session(db, tenant_id, session)
    if status != "LOCKED":
        return None
    if lock_adjust_approved(db, tenant_id, session.session_code):
        return None
    return fail(1155, LOCK_ADJUST_MSG)


def period_vo(db: Session, period_month: str, row: FinPeriod | None) -> dict:
    if row is None or row.finance_status != "LOCKED":
        return {
            "periodMonth": period_month,
            "financeStatus": "OPEN",
            "lockedAt": "",
            "lockedByName": "",
        }
    names = user_names(db, [row.locked_by])
    return {
        "periodMonth": row.period_month,
        "financeStatus": "LOCKED",
        "lockedAt": iso(row.locked_at) if row.locked_at else "",
        "lockedByName": names.get(row.locked_by, ""),
    }


def live_session_row(db: Session, tenant_id: int, session_code: str) -> LiveSession | None:
    return db.scalar(
        select(LiveSession).where(
            LiveSession.session_code == session_code,
            LiveSession.deleted == 0,
            LiveSession.tenant_id == tenant_id,
        )
    )


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
    session = live_session_row(db, row.tenant_id, row.session_code)
    plan = session.plan_start_time if session is not None else ""
    month = session_period_month(plan, row.session_code)
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
        "periodMonth": month,
        "financeStatus": finance_status_of(db, row.tenant_id, month),
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


def upsert_profit(
    db: Session,
    session_code: str,
    report: LiveReport,
    cost: FinCost,
    tenant_id: int,
    *,
    after_correction: bool = False,
) -> FinProfit:
    revenue = money(report.gmv)
    refund = money(report.refund_amount)
    total_cost = money(cost.total_cost)
    gross = money(revenue - refund - cost.commission_amount)
    net = money(revenue - refund - total_cost)
    profit = load_profit(db, tenant_id, session_code)
    first_calc = profit is None
    if profit is None:
        profit = FinProfit(session_code=session_code, tenant_id=tenant_id)
        db.add(profit)
    profit.revenue = revenue
    profit.refund_amount = refund
    profit.total_cost = total_cost
    profit.gross_profit = gross
    profit.net_profit = net
    if after_correction and not first_calc:
        profit.calc_status = "RECALCULATED"
    else:
        profit.calc_status = "CALCULATED"
    profit.calc_version = (profit.calc_version or 0) + 1
    db.flush()
    sync_share_results(db, tenant_id, session_code, cost, profit)
    return profit


CORRECTION_ITEMS: tuple[tuple[str, str], ...] = (
    ("commissionAmount", "平台佣金"),
    ("adCost", "投放成本"),
    ("rechargeCost", "冲话费摊销"),
    ("fixedCost", "固定成本"),
    ("sampleCost", "样品成本"),
    ("shareDaren", "达人分成"),
    ("shareRealname", "实名人分成"),
)


def cost_amount_snapshot(row: FinCost) -> dict[str, float]:
    return {
        "commissionAmount": money(row.commission_amount),
        "adCost": money(row.ad_cost),
        "rechargeCost": money(row.recharge_cost),
        "fixedCost": money(row.fixed_cost),
        "sampleCost": money(row.sample_cost),
        "shareDaren": money(row.share_daren),
        "shareRealname": money(row.share_realname),
    }


def correction_diff(before: dict[str, float], after: dict[str, float]) -> tuple[list[dict], list[dict]]:
    red: list[dict] = []
    blue: list[dict] = []
    for key, label in CORRECTION_ITEMS:
        delta = money(after[key] - before[key])
        if delta < 0:
            red.append({"item": label, "amount": delta})
        elif delta > 0:
            blue.append({"item": label, "amount": delta})
    return red, blue


_CORR_IDEM = re.compile(r"__IDEM:([0-9a-f]+):([^_\n]+)__")


def correction_idem_no(remark: str, client_token: str) -> str | None:
    for match in _CORR_IDEM.finditer(remark or ""):
        if match.group(1) == client_token:
            return match.group(2)
    return None


def remark_with_idem(reason: str, client_token: str, correction_no: str) -> str:
    base = reason.strip()[:400]
    return f"{base}\n__IDEM:{client_token}:{correction_no}__"[:512]


def correction_response_vo(correction_no: str, red: list[dict], blue: list[dict]) -> dict:
    return {
        "correctionNo": correction_no,
        "redEntries": red,
        "blueEntries": blue,
        "recalcTriggered": True,
    }


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


PROFIT_TYPES = ("GROSS", "OPERATING", "NET")


def parse_profit_type(profit_type: str) -> tuple[str | None, object | None]:
    """列表/汇总口径。缺省净利润。看板同名枚举，不另开 REST。"""
    kind = (profit_type or "NET").strip().upper() or "NET"
    if kind not in PROFIT_TYPES:
        return None, fail(1001, "口径仅支持 GROSS、OPERATING、NET")
    return kind, None


def metric_amount(profit: FinProfit, cost: FinCost | None, kind: str) -> float:
    gross = money(profit.gross_profit)
    if kind == "GROSS":
        return gross
    if kind == "OPERATING":
        return operating_profit(gross, cost)
    return money(profit.net_profit)


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


def sort_profits(
    visible: list[tuple[FinProfit, LiveSession, FinCost | None]],
    kind: str,
) -> list[tuple[FinProfit, LiveSession, FinCost | None]]:
    """口径金额降序；同金额按利润 id 降序，分页前后顺序稳定。"""
    return sorted(
        visible,
        key=lambda item: (metric_amount(item[0], item[2], kind), item[0].id or 0),
        reverse=True,
    )


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
    profitType: str = "NET",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    kind, err = parse_profit_type(profitType)
    if err is not None:
        return err
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    visible = sort_profits(
        collect_visible_profits(
            db,
            actor,
            request.state.scope,
            tenant_id,
            session_code=sessionCode,
            platform=platform,
            calc_status=calcStatus,
            date_from=dateFrom,
            date_to=dateTo,
        ),
        kind or "NET",
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
            "profitType": kind,
        }
    )


@router.get("/profit/summary")
def profit_summary(
    request: Request,
    sessionCode: str = "",
    platform: str = "",
    calcStatus: str = "",
    dateFrom: str = "",
    dateTo: str = "",
    profitType: str = "NET",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    kind, err = parse_profit_type(profitType)
    if err is not None:
        return err
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
    calculated = [item for item in visible if item[0].calc_status in ("CALCULATED", "RECALCULATED")]
    total_revenue = sum(money(p.revenue) for p, _, _ in calculated)
    total_cost = sum(money(p.total_cost) for p, _, _ in calculated)
    total_gross = sum(metric_amount(p, c, "GROSS") for p, _, c in calculated)
    total_operating = sum(metric_amount(p, c, "OPERATING") for p, _, c in calculated)
    total_net = sum(metric_amount(p, c, "NET") for p, _, c in calculated)
    shown = {"GROSS": total_gross, "OPERATING": total_operating, "NET": total_net}[kind or "NET"]
    ready = sum(1 for p, _, _ in calculated if settlement_status(p.calc_status) == "READY")
    in_settlement = sum(1 for p, _, _ in calculated if settlement_status(p.calc_status) == "IN_SETTLEMENT")
    return ok(
        {
            "sessionCount": len(calculated),
            "totalRevenue": money(total_revenue),
            "totalCost": money(total_cost),
            "totalGrossProfit": money(total_gross),
            "totalOperatingProfit": money(total_operating),
            "totalNetProfit": money(total_net),
            "shownProfit": money(shown),
            "profitType": kind,
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


@router.get("/period")
def period_status(
    periodMonth: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """期间状态。无行 = OPEN。结账动作见 AT-FIN-002 POST /fin/period/close。"""
    month = (periodMonth or "").strip()
    if not PERIOD_MONTH_RE.match(month):
        return fail(1001, "期间格式须为 yyyy-MM")
    tenant_id = tenant_of(actor)
    return ok(period_vo(db, month, load_period(db, tenant_id, month)))


@router.post("/period/close")
def period_close(
    body: FinPeriodCloseBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """结账 → FinanceStatus.LOCKED。已锁定重复调用幂等返回。"""
    month = (body.periodMonth or "").strip()
    if not PERIOD_MONTH_RE.match(month):
        return fail(1001, "期间格式须为 yyyy-MM")
    tenant_id = tenant_of(actor)
    row = load_period(db, tenant_id, month)
    now = utcnow()
    if row is None:
        row = FinPeriod(
            period_month=month,
            finance_status="LOCKED",
            locked_by=actor.id,
            locked_at=now,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.finance_status = "LOCKED"
        if row.locked_at is None:
            row.locked_by = actor.id
            row.locked_at = now
        row.updated_at = now
    db.flush()
    return ok(period_vo(db, month, row))


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
    locked = reject_if_period_locked(db, tenant_id, session)
    if locked is not None:
        return locked
    row = load_fin_cost(db, tenant_id, session_code)
    if row is not None and row.entry_status == "CONFIRMED":
        return fail(1141, "成本已核准，请走更正单")
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
    locked = reject_if_period_locked(db, tenant_id, session)
    if locked is not None:
        return locked
    row = load_fin_cost(db, tenant_id, session_code)
    if row is None:
        return fail(1141, "成本未录入")
    if row.entry_status == "CONFIRMED":
        return fail(1141, "成本已核准，请走更正单")
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
    locked = reject_if_period_locked(db, tenant_id, session)
    if locked is not None:
        return locked
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


@router.post("/cost/{session_code}/correction")
def cost_correction(
    request: Request,
    session_code: str,
    body: FinCostCorrectionBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
    clientToken: str | None = Header(default=None),
):
    if not clientToken:
        return fail(1001, "clientToken 必填")
    reason = (body.correctionReason or "").strip()
    if not reason:
        return fail(1144, "更正原因必填")
    err = validate_body(body.corrected)
    if err:
        return fail(1001, err)
    tenant_id = tenant_of(actor)
    row = load_fin_cost(db, tenant_id, session_code)
    if row is None or row.entry_status != "CONFIRMED":
        return fail(1141, "成本未核准，无法更正")
    existing_no = correction_idem_no(row.remark or "", clientToken)
    if existing_no:
        return ok(
            {
                "correctionNo": existing_no,
                "redEntries": [],
                "blueEntries": [],
                "recalcTriggered": True,
            }
        )
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    report = approved_report(db, session_code, tenant_id)
    if report is None:
        return fail(1141, "场次未核准下播数据")
    locked_adjust = reject_locked_correction(db, tenant_id, session)
    if locked_adjust is not None:
        return locked_adjust
    before = cost_amount_snapshot(row)
    apply_cost_row(row, session, report, body.corrected, actor)
    row.entry_status = "CONFIRMED"
    after = cost_amount_snapshot(row)
    red, blue = correction_diff(before, after)
    correction_no = f"CR-{row.id}-{int(utcnow().timestamp())}"
    row.remark = remark_with_idem(reason, clientToken, correction_no)
    upsert_profit(db, session_code, report, row, tenant_id, after_correction=True)
    db.flush()
    return ok(correction_response_vo(correction_no, red, blue))


@router.post("/profit/recalc/{session_code}")
def profit_recalc(
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
    if row is None or row.entry_status != "CONFIRMED":
        return fail(1145, "该场次成本未核准，利润未计算")
    locked = reject_if_period_locked(db, tenant_id, session)
    if locked is not None:
        return locked
    profit = upsert_profit(db, session_code, report, row, tenant_id, after_correction=True)
    db.flush()
    return ok(
        {
            "calcVersion": profit.calc_version or 1,
            "calcStatus": "RECALCULATED",
            "message": "利润已重算",
        }
    )


def actor_may_share_write(db: Session, actor: User) -> bool:
    """窄切片：本地 sys:admin 代财务审 + 业务审 + 发放（R3/R4 分岗留后续）。"""
    from app.scope import enabled_roles

    return any(role.role_key == "sys:admin" for role in enabled_roles(db, actor))


def share_parts(session: LiveSession, cost: FinCost) -> list[dict]:
    parts: list[dict] = []
    daren = money(cost.share_daren)
    realname = money(cost.share_realname)
    if daren > 0:
        parts.append(
            {
                "shareTarget": "DAREN",
                "shareAmount": daren,
                "targetRefId": int(session.responsible_user_id or 0),
                "targetRefName": "达人",
            }
        )
    if realname > 0:
        parts.append(
            {
                "shareTarget": "REALNAME",
                "shareAmount": realname,
                "targetRefId": int(session.realname_person_id or 0),
                "targetRefName": session.realname_name or "实名人",
            }
        )
    return parts


def sync_share_results(
    db: Session,
    tenant_id: int,
    session_code: str,
    cost: FinCost,
    profit: FinProfit,
) -> None:
    """利润落库后按手工分成额生成/刷新待审分成单。已审/已发放不改写。全部已冲销时只标记新单已补。"""
    session = db.scalar(
        select(LiveSession).where(
            LiveSession.session_code == session_code,
            LiveSession.deleted == 0,
            LiveSession.tenant_id == tenant_id,
        )
    )
    if session is None:
        return
    existing = db.scalars(
        select(FinShareResult).where(
            FinShareResult.tenant_id == tenant_id,
            FinShareResult.session_code == session_code,
        )
    ).all()
    active = [row for row in existing if row.deleted == 0]
    parts = share_parts(session, cost)
    if any(row.status in ("AUDITED", "PAID_OFF") for row in active):
        return
    reversed_rows = [row for row in active if row.status == "REVERSED"]
    pending_rows = [row for row in active if row.status == "PENDING_AUDIT"]
    if reversed_rows and not pending_rows:
        # 唯一键是场次+对象，不能再插一张待审单。金额变化时在原单留「新单已补」。
        by_part = {part["shareTarget"]: part for part in parts}
        for row in reversed_rows:
            part = by_part.get(row.share_target)
            new_amount = money(part["shareAmount"]) if part else 0.0
            if money(row.share_amount) == new_amount:
                continue
            detail = dict(row.calc_detail or {})
            detail["replaced"] = True
            detail["replacementAmount"] = new_amount
            detail["replacedNote"] = "已冲销（新单已补）"
            row.calc_detail = detail
        db.flush()
        return
    if any(row.status in LOCKED_SHARE_STATUSES for row in active):
        return
    share_total = money(sum(part["shareAmount"] for part in parts))
    by_target = {row.share_target: row for row in existing}
    keep = {part["shareTarget"] for part in parts}
    for part in parts:
        row = by_target.get(part["shareTarget"])
        detail = {
            "mode": "MANUAL",
            "shareTotal": share_total,
            "partAmount": part["shareAmount"],
            "formula": "sum(shareAmount)=shareDaren+shareRealname",
        }
        created = row is None
        if row is None:
            row = FinShareResult(
                session_code=session_code,
                tenant_id=tenant_id,
                rule_id=0,
                rule_name="手工分成",
                share_target=part["shareTarget"],
                status="PENDING_AUDIT",
            )
            db.add(row)
        amount_changed = (not created) and row.deleted == 0 and money(row.share_amount) != part["shareAmount"]
        row.rule_id = 0
        row.rule_name = "手工分成"
        row.target_ref_id = part["targetRefId"]
        row.target_ref_name = part["targetRefName"]
        row.share_base = money(profit.net_profit)
        row.share_amount = part["shareAmount"]
        row.calc_detail = detail
        row.deleted = 0
        if created or amount_changed or row.status not in ("PENDING_AUDIT",):
            row.status = "PENDING_AUDIT"
            row.fin_audit_passed = 0
            row.biz_audit_passed = 0
    for row in active:
        if row.share_target not in keep and row.status == "PENDING_AUDIT":
            row.deleted = 1
    db.flush()


SHARE_ITEM_LABEL = {"DAREN": "达人分成", "REALNAME": "实名人分成", "TEAM": "团队分成"}


def actor_display(actor: User) -> str:
    return (actor.nickname or actor.username or "").strip() or str(actor.id)


def share_result_vo(row: FinShareResult) -> dict:
    detail = row.calc_detail or {}
    return {
        "id": row.id,
        "sessionCode": row.session_code,
        "ruleId": row.rule_id or 0,
        "ruleName": row.rule_name or "手工分成",
        "shareTarget": row.share_target,
        "targetRefId": row.target_ref_id or 0,
        "targetRefName": row.target_ref_name or "",
        "shareBase": money(row.share_base),
        "shareAmount": money(row.share_amount),
        "calcDetail": detail,
        "status": row.status,
        "finAuditPassed": bool(row.fin_audit_passed),
        "bizAuditPassed": bool(row.biz_audit_passed),
        "auditedBy": row.audited_by or None,
        "auditedAt": iso(row.audited_at) if row.audited_at else None,
        "paidOffAt": iso(row.paid_off_at) if row.paid_off_at else None,
        "redEntries": detail.get("redEntries") or [],
        "reverseAudit": detail.get("reverseAudit"),
        "replaced": bool(detail.get("replaced")),
        "replacementAmount": detail.get("replacementAmount"),
        "replacedNote": detail.get("replacedNote") or "",
        "auditTrail": detail.get("auditTrail") or [],
    }


def write_share_reverse_log(
    db: Session,
    actor: User,
    row: FinShareResult,
    *,
    reason: str,
    from_status: str,
    red_amount: float,
    result_code: int,
) -> None:
    detail = {
        "shareId": row.id,
        "sessionCode": row.session_code,
        "shareTarget": row.share_target,
        "action": "REVERSE",
        "fromStatus": from_status,
        "reason": reason,
        "redAmount": red_amount,
        "code": result_code,
    }
    now = utcnow()
    db.add(
        OperateLog(
            module="财务",
            action="冲销分成单",
            operator_id=actor.id,
            operator_name=actor_display(actor),
            path=f"PUT /fin/share/result/{row.id}/payoff",
            detail_json=json.dumps(detail, ensure_ascii=False),
            result_code=result_code,
            creator=actor.id,
            updater=actor.id,
            tenant_id=tenant_of(actor),
            created_at=now,
            updated_at=now,
        )
    )


def apply_share_reverse(
    db: Session,
    actor: User,
    row: FinShareResult,
    reason: str,
    *,
    allow_pending: bool = False,
):
    """红冲原单，不改 share_amount。成功返回 VO；失败返回 fail 响应。"""
    cleaned = (reason or "").strip()
    from_status = row.status
    red_amount = money(-money(row.share_amount))
    if not cleaned:
        write_share_reverse_log(
            db, actor, row, reason="", from_status=from_status, red_amount=0, result_code=1144
        )
        db.flush()
        return fail(1144, "冲销原因必填")
    if row.status == "REVERSED":
        write_share_reverse_log(
            db,
            actor,
            row,
            reason=cleaned[:512],
            from_status=from_status,
            red_amount=red_amount,
            result_code=1150,
        )
        db.flush()
        return fail(1150, "分成单已冲销，不可重复冲销")
    allowed = {"AUDITED", "PAID_OFF"}
    if allow_pending:
        allowed.add("PENDING_AUDIT")
    if row.status not in allowed:
        write_share_reverse_log(
            db,
            actor,
            row,
            reason=cleaned[:512],
            from_status=from_status,
            red_amount=red_amount,
            result_code=1150,
        )
        db.flush()
        return fail(1150, "分成单未双审，不可冲销")
    now = utcnow()
    detail = dict(row.calc_detail or {})
    audit = {
        "actorId": actor.id,
        "actorName": actor_display(actor),
        "reversedAt": iso(now),
        "reason": cleaned[:512],
        "fromStatus": from_status,
        "resultCode": 0,
    }
    trail = list(detail.get("auditTrail") or [])
    trail.append({**audit, "action": "REVERSE", "redAmount": red_amount})
    detail["redEntries"] = [{"item": SHARE_ITEM_LABEL.get(row.share_target, "分成"), "amount": red_amount}]
    detail["reverseAudit"] = audit
    detail["auditTrail"] = trail
    row.calc_detail = detail
    row.status = "REVERSED"
    row.audited_by = actor.id
    row.audited_at = now
    write_share_reverse_log(
        db,
        actor,
        row,
        reason=cleaned[:512],
        from_status=from_status,
        red_amount=red_amount,
        result_code=0,
    )
    db.flush()
    return ok(share_result_vo(row))


def audit_result_vo(row: FinShareResult) -> dict:
    both = bool(row.fin_audit_passed) and bool(row.biz_audit_passed)
    return {
        "status": row.status,
        "finAuditPassed": bool(row.fin_audit_passed),
        "bizAuditPassed": bool(row.biz_audit_passed),
        "bothPassed": both and row.status == "AUDITED",
    }


def visible_share_rows(
    db: Session,
    actor: User,
    scope,
    tenant_id: int,
    *,
    session_code: str = "",
    share_target: str = "",
    status: str = "",
) -> list[FinShareResult]:
    stmt = select(FinShareResult).where(FinShareResult.deleted == 0, FinShareResult.tenant_id == tenant_id)
    if session_code:
        stmt = stmt.where(FinShareResult.session_code.contains(session_code))
    if share_target:
        stmt = stmt.where(FinShareResult.share_target == share_target)
    if status:
        stmt = stmt.where(FinShareResult.status == status)
    rows = db.scalars(stmt.order_by(FinShareResult.id.desc())).all()
    visible: list[FinShareResult] = []
    for row in rows:
        session = db.scalar(
            select(LiveSession).where(
                LiveSession.session_code == row.session_code,
                LiveSession.deleted == 0,
                LiveSession.tenant_id == tenant_id,
            )
        )
        if session is None or not session_fin_visible(db, actor, scope, session):
            continue
        visible.append(row)
    return visible


def load_visible_share(
    db: Session,
    actor: User,
    scope,
    tenant_id: int,
    share_id: int,
) -> FinShareResult | None:
    row = db.scalar(
        select(FinShareResult).where(
            FinShareResult.id == share_id,
            FinShareResult.deleted == 0,
            FinShareResult.tenant_id == tenant_id,
        )
    )
    if row is None:
        return None
    session = db.scalar(
        select(LiveSession).where(
            LiveSession.session_code == row.session_code,
            LiveSession.deleted == 0,
            LiveSession.tenant_id == tenant_id,
        )
    )
    if session is None or not session_fin_visible(db, actor, scope, session):
        return None
    return row


@router.get("/share/results")
def share_results(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    shareTarget: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tenant_id = tenant_of(actor)
    visible = visible_share_rows(
        db,
        actor,
        request.state.scope,
        tenant_id,
        session_code=sessionCode,
        share_target=shareTarget,
        status=status,
    )
    total = len(visible)
    start = (page_no - 1) * size
    page_rows = visible[start : start + size]
    return ok(
        {
            "list": [share_result_vo(row) for row in page_rows],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
        }
    )


@router.put("/share/result/{share_id}/audit")
def share_result_audit(
    request: Request,
    share_id: int,
    body: FinShareAuditBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if body.auditRole not in AUDIT_ROLES or not actor_may_share_write(db, actor):
        return fail(1149, "无该审批角色权限")
    if body.conclusion not in ("APPROVE", "REJECT"):
        return fail(1001, "审批结论无效")
    tenant_id = tenant_of(actor)
    row = load_visible_share(db, actor, request.state.scope, tenant_id, share_id)
    if row is None:
        return fail(1504, "资源不可用")
    session = live_session_row(db, tenant_id, row.session_code)
    if session is not None:
        locked = reject_if_period_locked(db, tenant_id, session)
        if locked is not None:
            return locked
    if row.status in ("PAID_OFF", "REVERSED"):
        return fail(1148, "分成单当前状态不可审批")
    if body.conclusion == "REJECT":
        reversed_resp = apply_share_reverse(
            db,
            actor,
            row,
            body.remark or "审批驳回",
            allow_pending=True,
        )
        if not isinstance(reversed_resp, dict):
            return reversed_resp
        return ok(audit_result_vo(row))
    if body.auditRole == "FINANCE":
        row.fin_audit_passed = 1
    else:
        row.biz_audit_passed = 1
    row.audited_by = actor.id
    row.audited_at = utcnow()
    if row.fin_audit_passed and row.biz_audit_passed:
        row.status = "AUDITED"
    else:
        row.status = "PENDING_AUDIT"
    db.flush()
    return ok(audit_result_vo(row))


@router.put("/share/result/{share_id}/payoff")
def share_result_payoff(
    request: Request,
    share_id: int,
    body: FinSharePayoffBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if not actor_may_share_write(db, actor):
        return fail(1149, "无该审批角色权限")
    tenant_id = tenant_of(actor)
    row = load_visible_share(db, actor, request.state.scope, tenant_id, share_id)
    if row is None:
        return fail(1504, "资源不可用")
    session = live_session_row(db, tenant_id, row.session_code)
    if session is not None:
        locked = reject_if_period_locked(db, tenant_id, session)
        if locked is not None:
            return locked
    if body.reverse:
        return apply_share_reverse(db, actor, row, body.reverseReason or body.payoffNote)
    if row.status == "PAID_OFF":
        return ok(None)
    if row.status != "AUDITED":
        return fail(1148, "双审未齐")
    row.status = "PAID_OFF"
    row.paid_off_at = utcnow()
    row.payoff_note = (body.payoffNote or "")[:256]
    if body.payoffVoucher is not None:
        row.payoff_voucher = {
            "fileName": body.payoffVoucher.fileName,
            "fileKey": body.payoffVoucher.fileKey,
        }
    db.flush()
    return ok(None)
