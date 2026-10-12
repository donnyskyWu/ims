"""手机卡主数据。号码与 ICCID 加密，绑定手机设备留给 B6。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.clock import format_datetime, today
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.serialize import parse_api_id, parse_date
from app.db.repository import Repository, assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.master.model import Realname, SimCard
from app.domains.resource.common import (
    audit_sensitive,
    digest,
    fen_to_yuan,
    has_perm,
    limit,
    mask_keep,
    money_to_fen,
    next_no,
    one,
    ref_blocked,
    remember,
    replay,
    text_of,
    token_of,
    user_map,
    valid_iccid,
    valid_mobile,
)
from app.services.exchange import remember_export

_STATUS = {"ENABLED": "启用", "DISABLED": "停用"}
_OPERATOR = {"CMCC": "移动", "CUCC": "联通", "CTCC": "电信", "CBN": "广电"}
_CYCLE = {"MONTH": "月", "QUARTER": "季", "HALF_YEAR": "半年", "YEAR": "年"}


def _row(ident: int) -> SimCard:
    return Repository(SimCard).get(int(ident))


def _pay_tone(value: date | None) -> str:
    if value is None:
        return ""
    days = (value - today()).days
    if days < 0:
        return "danger"
    if days <= 7:
        return "warning"
    return ""


def _view(row: SimCard, *, detail: bool = False) -> dict:
    users = user_map([row.assigned_user_id or 0])
    keeper = users.get(int(row.assigned_user_id or 0))
    person = get_session().get(Realname, row.realname_id) if row.realname_id else None
    data = {
        "id": row.id,
        "simNo": row.sim_no or row.code or "",
        "phoneMasked": mask_keep(row.phone_number_enc),
        "phoneTail": (row.phone_number_enc or "")[-4:],
        "iccidMasked": mask_keep(row.iccid_enc),
        "operator": row.operator or "",
        "operatorLabel": _OPERATOR.get(row.operator or "", row.operator or ""),
        "isPrimary": bool(row.is_primary),
        "realnameId": row.realname_id,
        "realnameName": person.name if person is not None else "",
        "realnameStatus": person.status if person is not None else "",
        "assignedUserId": row.assigned_user_id,
        "keeperName": keeper.nickname if keeper is not None else "",
        "phoneName": "—",
        "packageName": row.package_name or "",
        "monthlyRent": fen_to_yuan(row.monthly_rent),
        "paymentCycle": row.payment_cycle or "",
        "paymentCycleLabel": _CYCLE.get(row.payment_cycle or "", row.payment_cycle or ""),
        "activatedAt": row.activated_at.isoformat() if row.activated_at else "",
        "nextPaymentDate": row.next_payment_date.isoformat() if row.next_payment_date else "",
        "paymentTone": _pay_tone(row.next_payment_date),
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "warnings": [],
        "canPlain": has_perm("ims:corp:sim:plain"),
        "updateTime": format_datetime(row.update_time),
    }
    if detail:
        data["linkedAccounts"] = []
    return data


def _fill(row: SimCard, body: dict, creating: bool) -> None:
    if body.get("phone") and not text_of(body, "phoneNumber"):
        body["phoneNumber"] = body.get("phone")
    if creating or text_of(body, "phoneNumber"):
        phone = text_of(body, "phoneNumber")
        if not valid_mobile(phone):
            one("phoneNumber", "号码须为 11 位数字")
        hashed = digest(phone)
        taken = get_session().scalar(select(SimCard).where(SimCard.phone_number_hash == hashed))
        if taken is not None and taken.id != row.id:
            one("phoneNumber", "号码已存在")
        row.phone_number_enc = phone
        row.phone_number_hash = hashed
        row.name = mask_keep(phone)
    elif creating:
        one("phoneNumber", "请填写号码")
    if creating or "operator" in body:
        operator = text_of(body, "operator")
        if not operator:
            one("operator", "请选择运营商")
        row.operator = operator
    if creating or text_of(body, "iccid"):
        iccid = text_of(body, "iccid")
        if iccid:
            if not valid_iccid(iccid):
                one("iccid", "ICCID 须为 19 到 20 位数字")
            hashed = digest(iccid)
            taken = get_session().scalar(select(SimCard).where(SimCard.iccid_hash == hashed))
            if taken is not None and taken.id != row.id:
                one("iccid", "ICCID 已存在")
            row.iccid_enc = iccid
            row.iccid_hash = hashed
    if creating or "isPrimary" in body:
        row.is_primary = 1 if body.get("isPrimary") in (True, 1, "1", "true", "YES") else 0
    if creating or "realnameId" in body:
        raw = body.get("realnameId")
        row.realname_id = parse_api_id(raw) if raw not in (None, "", 0, "0") else None
    if creating or "assignedUserId" in body:
        raw = body.get("assignedUserId")
        row.assigned_user_id = parse_api_id(raw) if raw not in (None, "", 0, "0") else None
    if creating or "packageName" in body:
        row.package_name = limit(text_of(body, "packageName"), "packageName", "套餐名", 64)
    if creating or "monthlyRent" in body:
        row.monthly_rent = money_to_fen(body.get("monthlyRent", 0 if creating else row.monthly_rent))
    elif creating:
        row.monthly_rent = 0
    if creating or "paymentCycle" in body:
        cycle = text_of(body, "paymentCycle")
        row.payment_cycle = cycle or None
    activated = _date(body, "activatedAt") if creating or "activatedAt" in body else row.activated_at
    payment = _date(body, "nextPaymentDate") if creating or "nextPaymentDate" in body else row.next_payment_date
    if creating or "activatedAt" in body:
        row.activated_at = activated
    if creating or "nextPaymentDate" in body:
        row.next_payment_date = payment
    if row.activated_at and row.next_payment_date and row.next_payment_date < row.activated_at:
        one("nextPaymentDate", "下次缴费日不能早于开卡日")
    if creating or "status" in body:
        status = text_of(body, "status") or "ENABLED"
        if status not in _STATUS:
            one("status", "状态不正确")
        row.status = status


def _date(body: dict, key: str):
    raw = body.get(key)
    if raw in (None, ""):
        return None
    try:
        return parse_date(raw)
    except BizError:
        one(key, "日期格式须为年-月-日")
    return None


def page(page_query: Page, params: dict) -> dict:
    where = []
    phone = text_of(params, "phoneNumber") or text_of(params, "phone")
    if phone:
        where.append(SimCard.phone_number_hash == digest(phone))
    operator = text_of(params, "operator")
    if operator:
        where.append(SimCard.operator == operator)
    if params.get("realnameId"):
        where.append(SimCard.realname_id == parse_api_id(params.get("realnameId")))
    if params.get("assignedUserId"):
        where.append(SimCard.assigned_user_id == parse_api_id(params.get("assignedUserId")))
    status = text_of(params, "status")
    if status:
        where.append(SimCard.status == status)
    rows, total = Repository(SimCard).page(page_query, *where, order=[SimCard.update_time.desc(), SimCard.id.desc()])
    return page_result([_view(row) for row in rows], total, page_query)


def detail(ident: int) -> dict:
    return _view(_row(ident), detail=True)


def plain(ident: int) -> dict:
    row = _row(ident)
    audit_sensitive("SIM", row.id, "phone")
    if row.iccid_enc:
        audit_sensitive("SIM", row.id, "iccid")
    return {"id": row.id, "phone": row.phone_number_enc or "", "phoneNumber": row.phone_number_enc or "", "iccid": row.iccid_enc or ""}


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    row = SimCard(status="ENABLED", monthly_rent=0, is_primary=0)
    _fill(row, body, creating=True)
    number = next_no("SIM", "SIM")
    row.code = number
    row.sim_no = number
    Repository(SimCard).create(row)
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = _row(ident)
    _fill(row, body, creating=False)
    validate_refs_on_write(row)
    assert_dict_values(row)
    get_session().flush()
    return _view(row)


def set_status(ident: int, body: dict) -> dict:
    row = _row(ident)
    status = text_of(body, "status")
    if status not in _STATUS:
        one("status", "状态不正确")
    row.status = status
    assert_dict_values(row)
    get_session().flush()
    return _view(row)


def remove(ident: int) -> dict:
    try:
        Repository(SimCard).soft_delete(int(ident))
    except BizError as exc:
        if exc.code == 1502:
            ref_blocked("手机卡", exc)
        raise
    return {}


def export(params: dict) -> dict:
    rows = []
    page_no = 1
    total = 1
    while len(rows) < total:
        chunk = page(Page(page_no, 100), params)
        total = chunk["total"]
        rows.extend(chunk["list"])
        if not chunk["list"]:
            break
        page_no += 1
    header = ["卡编号", "号码", "ICCID", "运营商", "实名人", "保管人", "月租", "下次缴费日", "状态"]
    body = [
        [
            item["simNo"],
            item["phoneMasked"],
            item["iccidMasked"],
            item["operatorLabel"],
            item["realnameName"],
            item["keeperName"],
            item["monthlyRent"],
            item["nextPaymentDate"],
            item["statusLabel"],
        ]
        for item in rows
    ]
    return remember_export("手机卡.xlsx", header, body, "sim_card")
