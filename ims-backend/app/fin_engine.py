"""核准利润计算时，按启用的分成规则匹配场次并生成分成。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.live import platform_code
from app.models import FinCost, FinShareRule, LiveReport, LiveSession
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

_PARTS: dict[int, list[dict]] = {}


def money(value: float) -> float:
    return round(float(value or 0), 2)


def session_biz_day(session: LiveSession) -> str:
    raw = (session.plan_start_time or "").strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    code = session.session_code or ""
    if len(code) >= 11 and code.startswith("IMS") and code[3:11].isdigit():
        ymd = code[3:11]
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:8]}"
    return ""


def platform_hit(rule_platforms: list, session_platform: str) -> bool:
    raw = (session_platform or "").strip().upper()
    code = platform_code(raw) if raw else ""
    allowed = {item for item in (raw, code) if item}
    return any(str(item).strip().upper() in allowed for item in rule_platforms)


def rule_in_scope(rule: FinShareRule, session: LiveSession, ip_group_id: int, day: str) -> bool:
    scope = rule.rule_scope or {}
    platforms = list(scope.get("platforms") or [])
    accounts = [int(item) for item in (scope.get("accountIds") or [])]
    groups = [int(item) for item in (scope.get("ipGroupIds") or [])]
    if platforms and not platform_hit(platforms, session.platform):
        return False
    if accounts and int(session.account_id or 0) not in accounts:
        return False
    if groups and int(ip_group_id or 0) not in groups:
        return False
    start = (rule.effective_from or "").strip()
    end = (rule.effective_to or "").strip()
    if day:
        if start and day < start:
            return False
        if end and day > end:
            return False
    return True


def account_ip_group(account_id: int) -> int:
    if not account_id:
        return 0
    ops = ops_session()
    try:
        account = ops.get(PlatformAccount, int(account_id))
        if account is None or not account.ip_group_id:
            return 0
        return int(account.ip_group_id)
    finally:
        ops.close()


def base_amounts(report: LiveReport, cost: FinCost) -> dict[str, float]:
    gmv = money(report.gmv)
    refund = money(report.refund_amount)
    commission = money(cost.commission_amount)
    gross = money(gmv - refund - commission)
    operating = money(gross - money(cost.ad_cost) - money(cost.recharge_cost))
    pre_share = money(operating - money(cost.fixed_cost) - money(cost.sample_cost))
    return {"GMV": gmv, "GROSS_PROFIT": gross, "NET_PROFIT": pre_share}


def remember_parts(cost: FinCost, parts: list[dict]) -> None:
    _PARTS[id(cost)] = parts


def cached_parts(cost: FinCost) -> list[dict] | None:
    return _PARTS.get(id(cost))


def apply_engine_shares(db: Session, session: LiveSession, report: LiveReport, cost: FinCost) -> list[dict]:
    from app.fin_share_rule import dec, enabled_rules, ladder_load, q_rate, simulate_fixed, simulate_ladder

    day = session_biz_day(session)
    ip_group_id = account_ip_group(int(session.account_id or 0))
    bases = base_amounts(report, cost)
    winners: dict[str, FinShareRule] = {}
    for rule in enabled_rules(db, int(cost.tenant_id or session.tenant_id or 0)):
        if not rule_in_scope(rule, session, ip_group_id, day):
            continue
        prev = winners.get(rule.share_target)
        if prev is None or int(rule.priority or 0) > int(prev.priority or 0) or (
            int(rule.priority or 0) == int(prev.priority or 0) and int(rule.id or 0) > int(prev.id or 0)
        ):
            winners[rule.share_target] = rule

    labels = {"GMV": "GMV", "GROSS_PROFIT": "毛利", "NET_PROFIT": "净利润"}
    names = {"DAREN": "达人", "REALNAME": session.realname_name or "实名人", "TEAM": "团队"}
    refs = {
        "DAREN": int(session.responsible_user_id or 0),
        "REALNAME": int(session.realname_person_id or 0),
        "TEAM": 0,
    }
    parts: list[dict] = []
    for target, rule in winners.items():
        base = bases.get(rule.base_type, bases["NET_PROFIT"])
        if rule.rate_type == "FIXED" and rule.fixed_rate is not None:
            amount, _detail = simulate_fixed(dec(base), q_rate(dec(rule.fixed_rate)))
            formula = f"{labels.get(rule.base_type, rule.base_type)}×{float(q_rate(dec(rule.fixed_rate))) * 100:.2f}%"
        else:
            amount, _detail = simulate_ladder(dec(max(base, 0)), ladder_load(rule.ladder_config))
            formula = "阶梯"
        share = money(float(amount))
        if share <= 0:
            continue
        parts.append(
            {
                "shareTarget": target,
                "shareAmount": share,
                "shareBase": money(base),
                "ruleId": int(rule.id),
                "ruleName": rule.rule_name,
                "formula": formula,
                "targetRefId": refs.get(target, 0),
                "targetRefName": names.get(target, target),
            }
        )

    by_target = {part["shareTarget"]: part["shareAmount"] for part in parts}
    daren = money(by_target.get("DAREN", 0))
    realname = money(by_target.get("REALNAME", 0))
    team = money(by_target.get("TEAM", 0))
    cost.share_daren = daren
    cost.share_realname = realname
    cost.total_cost = money(
        money(cost.commission_amount)
        + money(cost.ad_cost)
        + money(cost.recharge_cost)
        + money(cost.fixed_cost)
        + money(cost.sample_cost)
        + daren
        + realname
        + team
    )
    remember_parts(cost, parts)
    return parts


def load_session(db: Session, tenant_id: int, session_code: str) -> LiveSession | None:
    return db.scalar(
        select(LiveSession).where(
            LiveSession.session_code == session_code,
            LiveSession.deleted == 0,
            LiveSession.tenant_id == tenant_id,
        )
    )
