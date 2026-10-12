"""示例订单。"""
from __future__ import annotations

import time
from decimal import Decimal

from sqlalchemy import asc, desc, select
from sqlalchemy.exc import IntegrityError

from app.api.dump import dump_row
from app.core.context import get_ctx
from app.core.crypto import hmac_hash
from app.core.errors import BizError
from app.core.fault import faults
from app.core.pagination import Page, page_result
from app.db.changes import diff_and_log
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.demo.model import DemoNote, DemoOrder, DemoOrderItem, DemoShare
from app.domains.system.model import SensitiveViewLog


def _mask_mobile(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) < 7:
        return "****"
    return value[:3] + "****" + value[-4:]


def _mask_id(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) < 8:
        return "****"
    return value[:3] + "*" * (len(value) - 7) + value[-4:]


def _view(row: DemoOrder, *, plain: bool = False, cost_plain: bool = False) -> dict:
    data = dump_row(
        row,
        ["id", "code", "name", "dept_id", "ip_group_id", "owner_user_id", "amount", "rate", "status", "biz_time", "biz_date", "realname_id", "creator", "updater", "tenant_id", "create_time", "update_time"],
    )
    data["idCard"] = row.id_card if plain else _mask_id(row.id_card)
    data["mobile"] = row.mobile if plain else _mask_mobile(row.mobile)
    if cost_plain:
        data["cost"] = f"{Decimal(row.cost):.2f}" if row.cost is not None else None
    else:
        data["cost"] = "***" if row.cost is not None else None
    if row.rate is not None:
        shown = (Decimal(row.rate) * Decimal("100")).quantize(Decimal("0.01"))
        data["rate"] = int(shown) if shown == shown.to_integral() else float(shown)
    return data


def _perms():
    ctx = get_ctx()
    return ctx.perm_codes if ctx else set()


def create_order(payload: dict) -> dict:
    faults.raise_if("demo.boom")
    faults.raise_if("demo.db")
    delay = payload.get("testDelayMs")
    from app.core.config import get_settings

    if delay and get_settings().env == "test":
        time.sleep(int(delay) / 1000)
    row = DemoOrder(
        name=payload.get("name") or "",
        code=payload.get("code"),
        dept_id=payload.get("deptId"),
        ip_group_id=payload.get("ipGroupId"),
        owner_user_id=payload.get("ownerUserId"),
        amount=payload.get("amount"),
        rate=payload.get("rate"),
        status=payload.get("status") or "ACTIVE",
        biz_time=payload.get("bizTime"),
        biz_date=payload.get("bizDate"),
        realname_id=payload.get("realnameId"),
        cost=payload.get("cost"),
    )
    if payload.get("id"):
        row.id = int(payload["id"])
    if payload.get("idCard"):
        row.id_card = payload["idCard"]
        row.id_card_hash = hmac_hash(payload["idCard"])
    if payload.get("mobile"):
        row.mobile = payload["mobile"]
        row.mobile_hash = hmac_hash(payload["mobile"])
    ctx = get_ctx()
    if ctx and ctx.tenant_id:
        row.tenant_id = ctx.tenant_id
    Repository(DemoOrder).create(row)
    return _view(row, plain=True, cost_plain=True)


def update_order(payload: dict) -> dict:
    row = Repository(DemoOrder).get(int(payload["id"]))
    before = {col.name: getattr(row, col.name) for col in row.__table__.columns}
    if "name" in payload:
        row.name = payload["name"]
    if "amount" in payload:
        row.amount = payload["amount"]
    if "ownerUserId" in payload:
        row.owner_user_id = payload["ownerUserId"]
    if "mobile" in payload:
        row.mobile = payload["mobile"]
        row.mobile_hash = hmac_hash(payload["mobile"]) if payload["mobile"] else None
    if "status" in payload and payload["status"]:
        row.status = payload["status"]
    if "code" in payload:
        row.code = payload["code"]
    diff_and_log(row, before)
    try:
        get_session().flush()
    except IntegrityError as exc:
        get_session().rollback()
        detail = str(getattr(exc, "orig", exc))
        field = "code"
        for token, name in (("username", "username"), ("role_key", "roleKey"), ("code", "code")):
            if token in detail:
                field = name
                break
        raise BizError(1001, data={"fieldErrors": [{"field": field, "message": "该值已存在"}]}) from exc
    return _view(row, plain="ims:demo:order:plain" in _perms(), cost_plain="ims:demo:order:cost-plain" in _perms())


def get_order(ident: int) -> dict:
    faults.raise_if("demo.boom")
    faults.raise_if("demo.db")
    row = Repository(DemoOrder).get(ident)
    return _view(row, plain="ims:demo:order:plain" in _perms(), cost_plain="ims:demo:order:cost-plain" in _perms())


def plain_order(ident: int) -> dict:
    row = Repository(DemoOrder).get(ident)
    ctx = get_ctx()
    get_session().add(
        SensitiveViewLog(
            biz_type="ims_demo_order",
            biz_id=row.id,
            kind="id_card",
            viewer_id=ctx.user_id if ctx else None,
            ip=ctx.client_ip if ctx else "",
        )
    )
    return _view(row, plain=True, cost_plain="ims:demo:order:cost-plain" in _perms())


def delete_order(ident: int) -> dict:
    Repository(DemoOrder).soft_delete(ident)
    return {}


def page_orders(page: Page) -> dict:
    session = get_session()
    order = []
    mapping = {"createTime": DemoOrder.create_time, "amount": DemoOrder.amount}
    if page.sort_field:
        column = mapping[page.sort_field]
        order.append(asc(column) if page.sort_order == "asc" else desc(column))
    rows, total = Repository(DemoOrder).page(page, order=order or None)
    data = [_view(row, plain="ims:demo:order:plain" in _perms(), cost_plain="ims:demo:order:cost-plain" in _perms()) for row in rows]
    return page_result(data, total, page)


def share_visible(rows: list[DemoShare]) -> list[DemoShare]:
    ctx = get_ctx()
    if ctx is None:
        return []
    kept = []
    for row in rows:
        snap = row.publish_scope or {}
        dept_ids = set(snap.get("deptIds") or [])
        if ctx.user_id and ctx.user_id == row.owner_user_id:
            kept.append(row)
        elif set(ctx.dept_ids or []) & dept_ids:
            kept.append(row)
    return kept


def create_share(name: str, dept_id: int | None) -> dict:
    ctx = get_ctx()
    row = DemoShare(
        name=name,
        dept_id=dept_id,
        owner_user_id=ctx.user_id if ctx else None,
        publish_scope={"deptIds": list(ctx.dept_ids or []), "ownerId": ctx.user_id if ctx else None},
    )
    Repository(DemoShare).create(row)
    return dump_row(row)


def page_shares() -> list[dict]:
    rows = Repository(DemoShare).list()
    return [dump_row(row, ["id", "name", "dept_id", "owner_user_id"]) for row in share_visible(rows)]
