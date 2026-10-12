"""设备领用、流转、归还、报废与状态标记。不发起审批。"""
from __future__ import annotations

from sqlalchemy import select, update

from app.core.clock import today
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.device.ledger import add_event, holders, load, timeline
from app.domains.device.model import AssetLedger
from app.domains.device.support import (
    ASSET_STATUS,
    CONDITION,
    limit,
    one,
    parse_day,
    reason_code,
    reason_label,
    require_active_user,
    site_message,
    user_brief,
    viewer_id,
)
from app.domains.resource.common import text_of as _text

_CHECKOUT_FROM = {"PENDING_REVIEW", "RETURNED", "IDLE"}


def _expect(row: AssetLedger, body: dict) -> None:
    raw = body.get("version")
    if raw in (None, ""):
        return
    try:
        version = int(raw)
    except (TypeError, ValueError):
        one("version", "版本不正确")
        return
    if version != int(row.version or 1):
        raise BizError(1001, "状态已变化，请刷新")


def _save(row: AssetLedger, expected: str, **values) -> AssetLedger:
    session = get_session()
    version = int(row.version or 1)
    values["version"] = version + 1
    result = session.execute(
        update(AssetLedger)
        .where(
            AssetLedger.id == row.id,
            AssetLedger.version == version,
            AssetLedger.status == expected,
            AssetLedger.deleted == 0,
        )
        .values(**values)
    )
    if int(result.rowcount or 0) != 1:
        session.expire_all()
        fresh = session.get(AssetLedger, row.id)
        if fresh is not None and fresh.status == "IN_USE" and expected != "IN_USE":
            raise BizError(1012, "资产已被领用")
        raise BizError(1001, "状态已变化，请刷新")
    session.expire(row)
    session.refresh(row)
    return row


def checkout(ident: int, body: dict) -> dict:
    row = load(ident)
    _expect(row, body)
    if row.status == "IN_USE":
        raise BizError(1012, "资产已被领用")
    if row.status not in _CHECKOUT_FROM:
        raise BizError(1015, "当前状态不允许此操作")
    user = require_active_user(body.get("userId") or body.get("ownerUserId"), "userId", "领用人")
    found = parse_day(body.get("checkoutDate") or today().isoformat(), "checkoutDate", required=True, label="领用日期")
    purpose = limit(_text(body, "purpose"), "purpose", "用途说明", 256)
    previous = row.owner_user_id
    before = row.status
    _save(row, before, status="IN_USE", owner_user_id=user.id)
    add_event(row, "CHECKOUT", "领用", reason=purpose, detail=purpose, from_owner=previous, to_owner=user.id, from_status=before, to_status="IN_USE")
    site_message(user.id, "资产领用", f"你已领用资产 {row.asset_code}", _page(row, row.id), "ASSET_CHECKOUT", f"checkout:{row.id}:{row.version}")
    get_session().flush()
    from app.domains.device.ledger import _view

    return _view(row, detail=True)


def transfer(ident: int, body: dict) -> dict:
    row = load(ident)
    _expect(row, body)
    if row.status != "IN_USE":
        raise BizError(1015, "当前状态不允许此操作")
    user = require_active_user(body.get("userId") or body.get("ownerUserId"), "userId", "目标责任人")
    if int(user.id) == int(row.owner_user_id or 0):
        one("userId", "目标责任人不能与当前责任人相同")
    code = reason_code(_text(body, "reason"))
    if not code:
        one("reason", "请选择流转原因")
    note = limit(_text(body, "remark") or _text(body, "comment"), "remark", "说明", 256)
    previous = row.owner_user_id
    before_name = user_brief(previous)["name"]
    _save(row, "IN_USE", owner_user_id=user.id)
    label = reason_label(code)
    detail = f"{before_name} → {user.nickname}（{label}）"
    add_event(row, "TRANSFER", "流转", reason=label, detail=detail, from_owner=previous, to_owner=user.id, from_status="IN_USE", to_status="IN_USE")
    route = _page(row, row.id)
    site_message(int(previous or 0), "资产流转", f"资产 {row.asset_code} 已流转给 {user.nickname}", route, "ASSET_TRANSFER", f"transfer-from:{row.id}:{row.version}")
    site_message(user.id, "资产流转", f"资产 {row.asset_code} 已流转给你", route, "ASSET_TRANSFER", f"transfer-to:{row.id}:{row.version}")
    get_session().flush()
    from app.domains.device.ledger import _view

    return _view(row, detail=True)


def give_back(ident: int, body: dict) -> dict:
    row = load(ident)
    _expect(row, body)
    if row.status != "IN_USE":
        raise BizError(1015, "当前状态不允许此操作")
    found = parse_day(body.get("returnDate") or today().isoformat(), "returnDate", required=True, label="归还日期")
    checkout_day = _last_checkout_date(row.id)
    if checkout_day and found < checkout_day:
        one("returnDate", "归还日期不能早于领用日期")
    condition = _text(body, "condition") or _text(body, "deviceCondition")
    if condition in CONDITION.values():
        condition = {label: code for code, label in CONDITION.items()}[condition]
    if condition not in CONDITION:
        one("condition", "请选择设备状况")
    note = limit(_text(body, "remark") or _text(body, "comment"), "remark", "说明", 256)
    if condition == "DAMAGED" and not note:
        one("remark", "有损坏时请填写说明")
    previous = row.owner_user_id
    operator = viewer_id()
    _save(row, "IN_USE", status="RETURNED", owner_user_id=operator or None)
    detail = CONDITION[condition] + (f"：{note}" if note else "")
    add_event(row, "RETURN", "归还", reason=detail, detail=detail, from_owner=previous, to_owner=operator or None, from_status="IN_USE", to_status="RETURNED")
    get_session().flush()
    from app.domains.device.ledger import _view

    data = _view(row, detail=True)
    data["holders"] = holders(row.id)
    return data


def scrap(ident: int, body: dict) -> dict:
    row = load(ident)
    _expect(row, body)
    if row.status == "IN_USE":
        raise BizError(1015, "请先归还再报废")
    if row.status not in {"RETURNED", "IDLE", "REPAIRING"}:
        raise BizError(1015, "当前状态不允许此操作")
    reason = limit(_text(body, "reason"), "reason", "报废原因", 256, required=True)
    previous = row.owner_user_id
    before = row.status
    _save(row, before, status="SCRAPPED")
    add_event(row, "SCRAP", "报废", reason=reason, detail=reason, from_owner=previous, to_owner=previous, from_status=before, to_status="SCRAPPED")
    get_session().flush()
    from app.domains.device.ledger import _view

    return _view(row, detail=True)


def mark_status(ident: int, body: dict) -> dict:
    row = load(ident)
    _expect(row, body)
    target = _text(body, "status")
    if target not in ASSET_STATUS:
        one("status", "请选择状态")
    allowed = {
        ("RETURNED", "IDLE"),
        ("IDLE", "RETURNED"),
        ("RETURNED", "REPAIRING"),
        ("IDLE", "REPAIRING"),
        ("REPAIRING", "RETURNED"),
    }
    if (row.status, target) not in allowed:
        raise BizError(1015, "当前状态不允许此操作")
    before = row.status
    title = "维修完成" if before == "REPAIRING" and target == "RETURNED" else f"标记为{ASSET_STATUS[target]}"
    _save(row, before, status=target)
    add_event(row, "MARK_STATUS", title, detail=title, from_status=before, to_status=target, from_owner=row.owner_user_id, to_owner=row.owner_user_id)
    get_session().flush()
    from app.domains.device.ledger import _view

    return _view(row, detail=True)


def events(ident: int) -> dict:
    load(ident)
    return {"list": timeline(ident)}


def _page(row: AssetLedger, ident: int) -> str:
    base = "/ims/corp/device/live" if row.asset_type in {"LIVE", "SHOOT"} else "/ims/corp/device/office"
    return f"{base}?assetId={ident}"


def _last_checkout_date(asset_id: int):
    from app.domains.device.model import AssetEvent

    row = get_session().scalar(
        select(AssetEvent).where(AssetEvent.asset_id == asset_id, AssetEvent.event_type == "CHECKOUT").order_by(AssetEvent.id.desc())
    )
    if row is None or row.event_time is None:
        return None
    return row.event_time.date()
