"""DC-002 利润反查（只读 · W8-3 首片）。"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import mask_name, utcnow
from app.corp import ops_db, page_args, tenant_of, user_names
from app.fin import (
    abnormal_marks,
    collect_visible_profits,
    load_fin_cost,
    load_profit,
    money,
    operating_profit,
    parse_day_range,
)
from app.live import get_session, iso
from app.models import FinCost, FinProfit, LiveSession, User, UserDept

router = APIRouter(prefix="/dc/profit-trace", tags=["dc-profit-trace"])

AGGREGATE_BY = frozenset({"PERSON", "ACCOUNT", "TEAM", "IP_GROUP", "MONTH"})


def stat_period(session: LiveSession) -> str:
    anchor = (session.actual_start or session.plan_start_time or "")[:7]
    return anchor or ""


def trace_row_vo(
    db: Session,
    profit: FinProfit,
    session: LiveSession,
    cost: FinCost | None,
    *,
    is_abnormal: bool = False,
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
        "isAbnormal": is_abnormal,
    }


def team_labels(db: Session, user_ids: set[int]) -> dict[int, tuple[str, str]]:
    labels = {uid: ("0", "未分配") for uid in user_ids}
    if not user_ids:
        return labels
    rows = db.scalars(select(UserDept).where(UserDept.user_id.in_(user_ids))).all()
    picked: dict[int, int] = {}
    for row in rows:
        current = picked.get(row.user_id)
        dept_id = int(row.dept_id or 0)
        if dept_id and (current is None or dept_id < current):
            picked[row.user_id] = dept_id
    for uid, dept_id in picked.items():
        labels[uid] = (str(dept_id), f"部门#{dept_id}")
    return labels


def aggregate_dimension(
    session: LiveSession,
    aggregate_by: str,
    accounts,
    groups,
    names: dict[int, str],
    teams: dict[int, tuple[str, str]],
) -> tuple[str, str]:
    if aggregate_by == "MONTH":
        value = stat_period(session) or "未知"
        return value, value
    if aggregate_by == "PERSON":
        uid = int(session.responsible_user_id or 0)
        name = names.get(uid) or (f"用户#{uid}" if uid else "未分配")
        return str(uid), name
    if aggregate_by == "TEAM":
        return teams.get(int(session.responsible_user_id or 0), ("0", "未分配"))
    from app.fin_dashboard import dimension_of

    return dimension_of(session, aggregate_by, accounts, groups, names)


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
    marks = abnormal_marks(
        collect_visible_profits(db, actor, request.state.scope, tenant_id)
    )
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
            "list": [
                trace_row_vo(db, p, s, c, is_abnormal=p.session_code in marks) for p, s, c in page_items
            ],
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


@router.get("/aggregate")
def profit_trace_aggregate(
    request: Request,
    aggregateBy: str = "PERSON",
    dimensionValue: str = "",
    dateRange: str = "",
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    kind = (aggregateBy or "").strip().upper()
    if kind not in AGGREGATE_BY:
        return fail(1001, "aggregateBy 仅支持 PERSON、ACCOUNT、TEAM、IP_GROUP、MONTH")
    date_from, date_to, err = parse_day_range(dateRange)
    if err:
        return fail(1001, err)
    tenant_id = tenant_of(actor)
    visible = collect_visible_profits(
        db,
        actor,
        request.state.scope,
        tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
    calculated = [item for item in visible if item[0].calc_status in ("CALCULATED", "RECALCULATED", "ABNORMAL")]
    marks = abnormal_marks(calculated)
    sessions = [session for _profit, session, _cost in calculated]
    if kind in ("ACCOUNT", "IP_GROUP"):
        from app.fin_dashboard import load_account_context

        accounts, groups = load_account_context(ops, sessions)
    else:
        accounts, groups = {}, {}
    user_ids = {int(session.responsible_user_id or 0) for session in sessions}
    names = user_names(db, user_ids)
    teams = team_labels(db, user_ids) if kind == "TEAM" else {}
    wanted = (dimensionValue or "").strip()
    grouped: dict[str, dict] = {}
    for profit, session, cost in calculated:
        value, label = aggregate_dimension(session, kind, accounts, groups, names, teams)
        if wanted and value != wanted:
            continue
        bucket = grouped.setdefault(value, {"dimensionValue": value, "dimensionLabel": label, "rows": []})
        bucket["rows"].append((profit, session, cost))
    data = []
    for bucket in grouped.values():
        rows = bucket["rows"]
        data.append(
            {
                "dimensionValue": bucket["dimensionValue"],
                "dimensionLabel": bucket["dimensionLabel"],
                "netProfit": money(sum(money(profit.net_profit) for profit, _session, _cost in rows)),
                "grossProfit": money(sum(money(profit.gross_profit) for profit, _session, _cost in rows)),
                "sessionCount": len(rows),
                "children": [
                    trace_row_vo(db, profit, session, cost, is_abnormal=profit.session_code in marks)
                    for profit, session, cost in rows
                ],
            }
        )
    data.sort(key=lambda item: item["netProfit"], reverse=True)
    return ok(data)


@router.get("/abnormal")
def profit_trace_abnormal(
    request: Request,
    pageNo: int = 1,
    pageSize: int = 20,
    platform: str = "",
    dateRange: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    date_from, date_to, err = parse_day_range(dateRange)
    if err:
        return fail(1001, err)
    page_no, size = page_args(pageNo, pageSize)
    visible = collect_visible_profits(
        db,
        actor,
        request.state.scope,
        tenant_of(actor),
        platform=platform,
        date_from=date_from,
        date_to=date_to,
    )
    calculated = [item for item in visible if item[0].calc_status in ("CALCULATED", "RECALCULATED", "ABNORMAL")]
    marks = abnormal_marks(calculated)
    rows = []
    for profit, session, cost in calculated:
        mark = marks.get(profit.session_code)
        if mark is None:
            continue
        vo = trace_row_vo(db, profit, session, cost, is_abnormal=True)
        vo.update(mark)
        rows.append(vo)
    rows.sort(key=lambda item: abs(float(item["deviationSigma"])), reverse=True)
    total = len(rows)
    start = (page_no - 1) * size
    return ok(
        {
            "list": rows[start : start + size],
            "total": total,
            "pageNo": page_no,
            "pageSize": size,
            "dataAsOf": iso(utcnow()),
        }
    )


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
