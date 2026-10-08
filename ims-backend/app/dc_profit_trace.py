"""DC-002 利润反查（只读 · W8-3 首片）。"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_name, utcnow
from app.corp import page_args, tenant_of, user_names
from app.fin import (
    collect_visible_profits,
    load_fin_cost,
    load_profit,
    money,
    operating_profit,
)
from app.live import get_session, iso
from app.models import FinCost, FinProfit, LiveSession, User

router = APIRouter(prefix="/dc/profit-trace", tags=["dc-profit-trace"])


def stat_period(session: LiveSession) -> str:
    anchor = (session.actual_start or session.plan_start_time or "")[:7]
    return anchor or ""


def trace_row_vo(
    db: Session,
    profit: FinProfit,
    session: LiveSession,
    cost: FinCost | None,
) -> dict:
    gross = money(profit.gross_profit)
    operating = operating_profit(gross, cost)
    net = money(profit.net_profit)
    return {
        "sessionCode": profit.session_code,
        "sessionTitle": session.topic or session.session_code,
        "platform": session.platform,
        "netProfit": net,
        "grossProfit": gross,
        "operatingProfit": operating,
        "calcVersion": profit.calc_version or 1,
        "statPeriod": stat_period(session),
        "isAbnormal": False,
    }


def parse_asset_ids(raw: str) -> list[int]:
    if not raw or raw == "[]":
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    ids: list[int] = []
    for item in data:
        if isinstance(item, int):
            ids.append(item)
        elif isinstance(item, str) and item.isdigit():
            ids.append(int(item))
    return ids


def cost_detail_rows(cost: FinCost | None, *, masked: bool) -> list[dict]:
    if cost is None:
        return []
    items = [
        ("commission", "平台佣金", money(cost.commission_amount)),
        ("ad", "投流成本", money(cost.ad_cost)),
        ("recharge", "充值成本", money(cost.recharge_cost)),
        ("fixed", "固定成本", money(cost.fixed_cost)),
        ("sample", "样品成本", money(cost.sample_cost)),
        ("shareDaren", "达人分成", money(cost.share_daren)),
        ("shareRealname", "实名人分成", money(cost.share_realname)),
    ]
    rows: list[dict] = []
    for key, label, amount in items:
        rows.append(
            {
                "costItem": key,
                "costItemLabel": label,
                "amount": None if masked else amount,
            }
        )
    return rows


def share_detail_rows(cost: FinCost | None, session: LiveSession, *, masked: bool) -> list[dict]:
    if cost is None:
        return []
    rows: list[dict] = []
    if cost.share_daren or cost.share_cost_type:
        rows.append(
            {
                "shareTarget": "DAREN",
                "targetRefId": session.account_id,
                "targetRefName": session.account_no or "",
                "shareBase": None if masked else money(cost.cost_gmv),
                "shareAmount": None if masked else money(cost.share_daren),
                "status": cost.entry_status,
            }
        )
    if cost.share_realname or session.realname_person_id:
        rows.append(
            {
                "shareTarget": "REALNAME",
                "targetRefId": session.realname_person_id,
                "targetRefName": mask_name(session.realname_name) if masked else (session.realname_name or ""),
                "shareBase": None if masked else money(cost.cost_gmv),
                "shareAmount": None if masked else money(cost.share_realname),
                "status": cost.entry_status,
            }
        )
    return rows


def chain_ready(profit: FinProfit | None, cost: FinCost | None) -> bool:
    return (
        profit is not None
        and profit.calc_status not in ("", "PENDING")
        and cost is not None
        and cost.entry_status == "CONFIRMED"
    )


@router.get("/list")
def profit_trace_list(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    sessionCode: str = "",
    platform: str = "",
    calcStatus: str = "",
    accountId: int = 0,
    responsibleUserId: int = 0,
    statPeriod: str = "",
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
    )
    if accountId:
        visible = [item for item in visible if item[1].account_id == accountId]
    if responsibleUserId:
        visible = [item for item in visible if item[1].responsible_user_id == responsibleUserId]
    if statPeriod:
        visible = [item for item in visible if stat_period(item[1]) == statPeriod]
    calculated = [item for item in visible if item[0].calc_status in ("CALCULATED", "RECALCULATED")]
    total = len(calculated)
    start = (page_no - 1) * size
    page_items = calculated[start : start + size]
    return ok(
        {
            "list": [trace_row_vo(db, p, s, c) for p, s, c in page_items],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
            "dataAsOf": iso(utcnow()),
        }
    )


@router.get("/share-detail/{session_code}")
def profit_trace_share_detail(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    cost = load_fin_cost(db, tenant_id, session_code)
    profit = load_profit(db, tenant_id, session_code)
    if not chain_ready(profit, cost):
        return fail(1145, "该场次成本未核准，利润未计算")
    masked = request.state.scope is not None and request.state.scope.kind == "SELF"
    return ok(share_detail_rows(cost, session, masked=masked))


@router.get("/{session_code}")
def profit_trace_chain(
    request: Request,
    session_code: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    started = time.perf_counter()
    tenant_id = tenant_of(actor)
    session = get_session(db, actor, request.state.scope, session_code)
    if session is None:
        return fail(1504, "资源不可用")
    profit = load_profit(db, tenant_id, session_code)
    cost = load_fin_cost(db, tenant_id, session_code)
    if not chain_ready(profit, cost):
        return fail(1145, "该场次成本未核准，利润未计算")
    masked = request.state.scope is not None and request.state.scope.kind == "SELF"
    names = user_names(db, [session.responsible_user_id])
    asset_ids = parse_asset_ids(session.device_asset_ids or "[]")
    assets = [{"assetId": aid, "assetCode": f"AST-{aid}"} for aid in asset_ids]
    live_date = (session.actual_start or session.plan_start_time or "")[:10]
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    return ok(
        {
            "sessionCode": session_code,
            "chain": {
                "profit": trace_row_vo(db, profit, session, cost),
                "session": {
                    "sessionCode": session.session_code,
                    "sessionTitle": session.topic or session.session_code,
                    "liveDate": live_date,
                    "platform": session.platform,
                },
                "account": {
                    "accountId": session.account_id,
                    "accountNo": session.account_no or "",
                    "nickname": session.account_no or "",
                },
                "assets": assets,
                "responsibleUser": {
                    "userId": session.responsible_user_id,
                    "userName": names.get(session.responsible_user_id, ""),
                },
                "realnamePersons": [
                    {
                        "userId": session.realname_person_id,
                        "userName": mask_name(session.realname_name) if masked else (session.realname_name or ""),
                        "roleType": "REALNAME",
                    }
                ]
                if session.realname_person_id
                else [],
                "costDetail": cost_detail_rows(cost, masked=masked),
                "shareDetail": share_detail_rows(cost, session, masked=masked),
            },
            "queryCostMs": elapsed,
            "dataAsOf": iso(utcnow()),
        }
    )
