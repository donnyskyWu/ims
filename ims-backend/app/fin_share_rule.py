"""FIN-003 分成规则：列表 / 创建 / 编辑新版本 / 停用 / 试算。

校验：fixedRate 与阶梯比例落在 (0, 1]；阶梯区间不重叠且连续（1146）。
同范围启用的固定比例按分成对象各取一条（优先级高者生效），对象不少于 2 个时合计必须等于 1.0000（V2-E2，1146）。
同范围同对象已有启用规则时须 confirmConflict 显式确认（1147）。
编辑只递增 version，不回写 ims_fin_share_result（FIN-S-R5）。
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.fin import actor_may_share_write
from app.models import FinShareRule, User

router = APIRouter(prefix="/fin", tags=["fin-share-rule"])

RATE_Q = Decimal("0.0001")
MONEY_Q = Decimal("0.01")
ONE = Decimal("1.0000")
SHARE_TARGETS = frozenset({"DAREN", "REALNAME", "TEAM"})
BASE_TYPES = frozenset({"GMV", "GROSS_PROFIT", "NET_PROFIT"})
RATE_TYPES = frozenset({"FIXED", "LADDER"})
PLATFORMS = frozenset({"DYS", "KS", "WX", "TM", "JD", "OTA"})
DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
MSG_1146_RATE = "固定比例须在 (0, 1] 内"
MSG_1147 = "存在同范围同对象优先级冲突规则，确认强制保存？"


class LadderItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    min: float | int | str | None = None
    max: float | int | str | None = None
    rate: float | int | str | None = None


class ScopeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    platforms: list[str] | None = None
    accountIds: list[int] | None = None
    ipGroupIds: list[int] | None = None


class EffectiveRangeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    start: str | None = Field(default=None, alias="from")
    to: str | None = None


class FinShareRuleBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ruleName: str | None = None
    shareTarget: str | None = None
    baseType: str | None = None
    rateType: str | None = None
    fixedRate: float | int | str | None = None
    ladderConfig: list[LadderItem] | None = None
    scope: ScopeBody | None = None
    priority: int | None = None
    effectiveRange: EffectiveRangeBody | None = None
    confirmConflict: bool = False
    clientToken: str | None = None


class FinShareSimulateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ruleId: int | None = None
    draftRule: FinShareRuleBody | None = None
    simulateBase: float | int | str | None = None


def q_rate(value: Decimal) -> Decimal:
    return value.quantize(RATE_Q, rounding=ROUND_HALF_UP)


def q_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def dec(value) -> Decimal:
    return Decimal(str(value))


def rate_text(value: Decimal) -> str:
    return f"{q_rate(value):.4f}"


def money_text(value: Decimal) -> str:
    return f"{q_money(value):.2f}"


def parse_rate(value) -> tuple[Decimal | None, str | None]:
    if value is None or value == "":
        return None, MSG_1146_RATE
    try:
        raw = dec(value)
    except Exception:
        return None, MSG_1146_RATE
    if raw <= 0 or raw > 1:
        return None, MSG_1146_RATE
    rated = q_rate(raw)
    if rated <= 0 or rated > 1:
        return None, MSG_1146_RATE
    return rated, None


def parse_money(value, label: str) -> tuple[Decimal | None, str | None]:
    if value is None or value == "":
        return None, f"{label}必填"
    try:
        raw = dec(value)
    except Exception:
        return None, f"{label}格式非法"
    if raw < 0:
        return None, f"{label}不能为负"
    return q_money(raw), None


def norm_scope(raw) -> tuple[dict | None, str | None]:
    data = raw or {}
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    try:
        platforms = sorted({str(item).strip() for item in (data.get("platforms") or []) if str(item).strip()})
        account_ids = sorted({int(item) for item in (data.get("accountIds") or [])})
        ip_group_ids = sorted({int(item) for item in (data.get("ipGroupIds") or [])})
    except (TypeError, ValueError):
        return None, "适用范围格式非法"
    unknown = [item for item in platforms if item not in PLATFORMS]
    if unknown:
        return None, "平台编码非法"
    if any(item <= 0 for item in account_ids + ip_group_ids):
        return None, "适用范围编号非法"
    return {"platforms": platforms, "accountIds": account_ids, "ipGroupIds": ip_group_ids}, None


def scope_key(scope: dict) -> str:
    return (
        f"p:{','.join(scope.get('platforms') or [])}"
        f"|a:{','.join(str(item) for item in scope.get('accountIds') or [])}"
        f"|g:{','.join(str(item) for item in scope.get('ipGroupIds') or [])}"
    )


def normalize_ladder(items: list[LadderItem] | None) -> tuple[list[dict] | None, str | None]:
    if not items:
        return None, "阶梯配置不能为空"
    parsed: list[dict] = []
    for item in items:
        lower, err = parse_money(item.min, "阶梯下限")
        if err or lower is None:
            return None, err or "阶梯下限必填"
        upper = None
        if item.max is not None and item.max != "":
            upper, err = parse_money(item.max, "阶梯上限")
            if err or upper is None:
                return None, err or "阶梯上限格式非法"
            if upper <= lower:
                return None, "阶梯区间重叠"
        rated, err = parse_rate(item.rate)
        if err or rated is None:
            return None, "阶梯比例须在 (0, 1] 内"
        parsed.append({"min": lower, "max": upper, "rate": rated})
    parsed.sort(key=lambda row: row["min"])
    for index, row in enumerate(parsed):
        last = index == len(parsed) - 1
        if row["max"] is None and not last:
            return None, "仅末档上限可为空"
        if not last:
            nxt = parsed[index + 1]
            if nxt["min"] < row["max"]:
                return None, "阶梯区间重叠"
            if nxt["min"] > row["max"]:
                return None, "阶梯区间不连续"
    return parsed, None


def validate_rule(body: FinShareRuleBody) -> tuple[dict | None, int | None, str | None]:
    name = (body.ruleName or "").strip()
    if not name:
        return None, 1001, "规则名称必填"
    if len(name) > 64:
        return None, 1001, "规则名称不能超过 64 字"
    if body.shareTarget not in SHARE_TARGETS:
        return None, 1001, "分成对象非法"
    if body.baseType not in BASE_TYPES:
        return None, 1001, "分成基数非法"
    if body.rateType not in RATE_TYPES:
        return None, 1001, "比例方式非法"
    if body.priority is None:
        return None, 1001, "优先级必填"
    window = body.effectiveRange
    start = (window.start if window else "") or ""
    start = start.strip()
    end = ((window.to if window else "") or "").strip()
    if not DATE_RE.match(start):
        return None, 1001, "生效开始日必填"
    if end and not DATE_RE.match(end):
        return None, 1001, "生效结束日格式非法"
    if end and end < start:
        return None, 1001, "生效结束日不能早于开始日"
    scope, err = norm_scope(body.scope)
    if err or scope is None:
        return None, 1001, err or "适用范围格式非法"
    fixed = None
    ladder = None
    if body.rateType == "FIXED":
        fixed, err = parse_rate(body.fixedRate)
        if err or fixed is None:
            return None, 1146, err or MSG_1146_RATE
    else:
        ladder, err = normalize_ladder(body.ladderConfig)
        if err or ladder is None:
            return None, 1146, err or "阶梯配置非法"
    return (
        {
            "ruleName": name,
            "shareTarget": body.shareTarget,
            "baseType": body.baseType,
            "rateType": body.rateType,
            "fixedRate": fixed,
            "ladderConfig": ladder,
            "scope": scope,
            "priority": int(body.priority),
            "effectiveFrom": start,
            "effectiveTo": end,
        },
        None,
        None,
    )


def ladder_store(rows: list[dict] | None) -> list[dict] | None:
    if not rows:
        return None
    stored = []
    for row in rows:
        stored.append(
            {
                "min": money_text(row["min"]),
                "max": None if row["max"] is None else money_text(row["max"]),
                "rate": rate_text(row["rate"]),
            }
        )
    return stored


def ladder_load(raw) -> list[dict]:
    loaded = []
    for row in raw or []:
        loaded.append(
            {
                "min": q_money(dec(row["min"])),
                "max": None if row.get("max") in (None, "") else q_money(dec(row["max"])),
                "rate": q_rate(dec(row["rate"])),
            }
        )
    return loaded


def rule_vo(row: FinShareRule) -> dict:
    scope, _err = norm_scope(row.rule_scope or {})
    fixed = None if row.fixed_rate is None else float(q_rate(dec(row.fixed_rate)))
    ladder = None
    if row.ladder_config:
        ladder = [
            {
                "min": float(item["min"]),
                "max": None if item["max"] is None else float(item["max"]),
                "rate": float(item["rate"]),
            }
            for item in ladder_load(row.ladder_config)
        ]
    return {
        "id": row.id,
        "ruleName": row.rule_name,
        "shareTarget": row.share_target,
        "baseType": row.base_type,
        "rateType": row.rate_type,
        "fixedRate": fixed,
        "ladderConfig": ladder,
        "scope": scope or {"platforms": [], "accountIds": [], "ipGroupIds": []},
        "priority": row.priority,
        "version": row.version or 1,
        "status": row.status,
        "effectiveRange": {"from": row.effective_from, "to": row.effective_to or None},
    }


def enabled_rules(db: Session, tenant_id: int) -> list[FinShareRule]:
    return list(
        db.scalars(
            select(FinShareRule).where(
                FinShareRule.tenant_id == tenant_id,
                FinShareRule.deleted == 0,
                FinShareRule.status == "ENABLED",
            )
        ).all()
    )


def same_scope(row: FinShareRule, scope: dict) -> bool:
    current, _err = norm_scope(row.rule_scope or {})
    return scope_key(current or {}) == scope_key(scope)


def conflicts_of(rows: list[FinShareRule], payload: dict, rule_id: int | None) -> list[int]:
    found = []
    for row in rows:
        if rule_id is not None and row.id == rule_id:
            continue
        if row.share_target != payload["shareTarget"]:
            continue
        if not same_scope(row, payload["scope"]):
            continue
        found.append(row.id)
    return found


def winning_rates(rows: list[FinShareRule], payload: dict, rule_id: int | None) -> dict[str, Decimal]:
    best: dict[str, tuple[int, Decimal]] = {}
    for row in rows:
        if rule_id is not None and row.id == rule_id:
            continue
        if row.rate_type != "FIXED" or row.fixed_rate is None:
            continue
        if not same_scope(row, payload["scope"]):
            continue
        rate = q_rate(dec(row.fixed_rate))
        prev = best.get(row.share_target)
        if prev is None or row.priority >= prev[0]:
            best[row.share_target] = (int(row.priority or 0), rate)
    if payload["rateType"] == "FIXED" and payload["fixedRate"] is not None:
        rate = q_rate(payload["fixedRate"])
        prev = best.get(payload["shareTarget"])
        if prev is None or int(payload["priority"]) >= prev[0]:
            best[payload["shareTarget"]] = (int(payload["priority"]), rate)
    return {key: value[1] for key, value in best.items()}


def sum_error(rates: dict[str, Decimal]) -> str | None:
    if len(rates) < 2:
        return None
    total = q_rate(sum(rates.values(), Decimal("0")))
    if total != ONE:
        return f"多对象分成比例合计须等于 1.0000（当前 {rate_text(total)}）"
    return None


def apply_payload(row: FinShareRule, payload: dict) -> None:
    row.rule_name = payload["ruleName"]
    row.share_target = payload["shareTarget"]
    row.base_type = payload["baseType"]
    row.rate_type = payload["rateType"]
    row.fixed_rate = payload["fixedRate"]
    row.ladder_config = ladder_store(payload["ladderConfig"])
    row.rule_scope = payload["scope"]
    row.priority = payload["priority"]
    row.effective_from = payload["effectiveFrom"]
    row.effective_to = payload["effectiveTo"]
    row.updated_at = utcnow()


def load_rule(db: Session, tenant_id: int, rule_id: int) -> FinShareRule | None:
    return db.scalar(
        select(FinShareRule).where(
            FinShareRule.id == rule_id,
            FinShareRule.tenant_id == tenant_id,
            FinShareRule.deleted == 0,
        )
    )


def simulate_fixed(base: Decimal, rate: Decimal) -> tuple[Decimal, list[dict]]:
    amount = q_money(base * rate)
    return amount, [{"range": "固定", "rateApplied": float(rate), "amount": float(amount)}]


def simulate_ladder(base: Decimal, rows: list[dict]) -> tuple[Decimal, list[dict]]:
    details = []
    total = Decimal("0.00")
    for row in rows:
        lower = row["min"]
        upper = row["max"]
        rate = row["rate"]
        if base <= lower:
            portion = Decimal("0.00")
        else:
            cap = base if upper is None else min(base, upper)
            portion = q_money(cap - lower)
            if portion < 0:
                portion = Decimal("0.00")
        amount = q_money(portion * rate)
        if portion <= 0:
            continue
        upper_text = "∞" if upper is None else money_text(upper)
        details.append(
            {
                "range": f"{money_text(lower)}~{upper_text}",
                "rateApplied": float(rate),
                "amount": float(amount),
            }
        )
        total = q_money(total + amount)
    return total, details


def reject_writer(db: Session, actor: User):
    if not actor_may_share_write(db, actor):
        return fail(1008, "无分成规则维护权限")
    return None


@router.get("/share/rules")
def share_rules(
    pageNo: int = 1,
    pageSize: int = 20,
    shareTarget: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    denied = reject_writer(db, actor)
    if denied is not None:
        return denied
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(FinShareRule).where(FinShareRule.deleted == 0, FinShareRule.tenant_id == tenant_id)
    if shareTarget:
        if shareTarget not in SHARE_TARGETS:
            return fail(1001, "分成对象非法")
        stmt = stmt.where(FinShareRule.share_target == shareTarget)
    if status:
        if status not in {"ENABLED", "DISABLED"}:
            return fail(1001, "规则状态非法")
        stmt = stmt.where(FinShareRule.status == status)
    rows = db.scalars(stmt.order_by(FinShareRule.priority.desc(), FinShareRule.id.desc())).all()
    start = (page_no - 1) * size
    page_rows = rows[start : start + size]
    return paged([rule_vo(row) for row in page_rows], len(rows), page_no, size)


@router.post("/share/rule")
def share_rule_create(
    body: FinShareRuleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    denied = reject_writer(db, actor)
    if denied is not None:
        return denied
    tenant_id = tenant_of(actor)
    token = (body.clientToken or "").strip()
    if token:
        existing = db.scalar(
            select(FinShareRule).where(
                FinShareRule.tenant_id == tenant_id,
                FinShareRule.client_token == token,
                FinShareRule.deleted == 0,
            )
        )
        if existing is not None:
            return ok(rule_vo(existing))
    payload, code, msg = validate_rule(body)
    if payload is None:
        return fail(code or 1001, msg or "参数非法")
    rows = enabled_rules(db, tenant_id)
    summed = sum_error(winning_rates(rows, payload, None))
    if summed:
        return fail(1146, summed)
    hit = conflicts_of(rows, payload, None)
    if hit and not body.confirmConflict:
        return fail(1147, MSG_1147, {"conflictRuleIds": hit})
    row = FinShareRule(
        status="ENABLED",
        version=1,
        client_token=token or None,
        created_by=actor.id,
        tenant_id=tenant_id,
        deleted=0,
    )
    apply_payload(row, payload)
    db.add(row)
    db.flush()
    return ok(rule_vo(row))


@router.put("/share/rule/{rule_id}")
def share_rule_update(
    rule_id: int,
    body: FinShareRuleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    denied = reject_writer(db, actor)
    if denied is not None:
        return denied
    tenant_id = tenant_of(actor)
    row = load_rule(db, tenant_id, rule_id)
    if row is None:
        return fail(1504, "分成规则不存在")
    payload, code, msg = validate_rule(body)
    if payload is None:
        return fail(code or 1001, msg or "参数非法")
    if row.status == "ENABLED":
        rows = enabled_rules(db, tenant_id)
        summed = sum_error(winning_rates(rows, payload, row.id))
        if summed:
            return fail(1146, summed)
        hit = conflicts_of(rows, payload, row.id)
        if hit and not body.confirmConflict:
            return fail(1147, MSG_1147, {"conflictRuleIds": hit})
    apply_payload(row, payload)
    row.version = int(row.version or 1) + 1
    db.flush()
    return ok(rule_vo(row))


@router.delete("/share/rule/{rule_id}")
def share_rule_disable(
    rule_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    denied = reject_writer(db, actor)
    if denied is not None:
        return denied
    tenant_id = tenant_of(actor)
    row = load_rule(db, tenant_id, rule_id)
    if row is None:
        return fail(1504, "分成规则不存在")
    row.status = "DISABLED"
    row.updated_at = utcnow()
    db.flush()
    return ok(None)


@router.post("/share/simulate")
def share_simulate(
    body: FinShareSimulateBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    denied = reject_writer(db, actor)
    if denied is not None:
        return denied
    base, err = parse_money(body.simulateBase, "试算基数")
    if err or base is None:
        return fail(1001, err or "试算基数必填")
    payload = None
    if body.draftRule is not None:
        payload, code, msg = validate_rule(body.draftRule)
        if payload is None:
            return fail(code or 1001, msg or "规则参数非法")
    elif body.ruleId:
        row = load_rule(db, tenant_of(actor), int(body.ruleId))
        if row is None:
            return fail(1504, "分成规则不存在")
        payload = {
            "rateType": row.rate_type,
            "fixedRate": None if row.fixed_rate is None else q_rate(dec(row.fixed_rate)),
            "ladderConfig": ladder_load(row.ladder_config),
        }
    else:
        return fail(1001, "请指定规则或草稿")
    if payload["rateType"] == "FIXED":
        amount, detail = simulate_fixed(base, payload["fixedRate"])
    else:
        amount, detail = simulate_ladder(base, payload["ladderConfig"])
    return ok(
        {
            "simulateBase": float(base),
            "shareAmount": float(amount),
            "calcDetail": detail,
        }
    )
