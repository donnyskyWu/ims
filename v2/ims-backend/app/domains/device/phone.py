"""手机设备。一机最多两张卡，写入手机卡上的 phone_id。"""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.clock import format_datetime, today
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.serialize import parse_api_id
from app.db.repository import Repository, assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.master.model import Phone, Realname, SimCard
from app.domains.resource.common import mask_keep, text_of
from app.domains.device.support import (
    PHONE_OS,
    PHONE_STATUS,
    amount_fen,
    limit,
    mask_imei,
    not_future,
    one,
    parse_day,
    phone_log,
    phone_logs,
    phone_no,
    remember,
    replay,
    require_active_user,
    token_of,
    user_brief,
)
from app.services.exchange import remember_export

_MAX_SIM = 2


def _row(ident: int) -> Phone:
    return Repository(Phone).get(int(ident))


def _sims(phone_id: int) -> list[SimCard]:
    return list(get_session().scalars(select(SimCard).where(SimCard.phone_id == int(phone_id)).order_by(SimCard.id.asc())))


def _sim_view(row: SimCard) -> dict:
    person = get_session().get(Realname, row.realname_id) if row.realname_id else None
    from app.domains.resource.sim import _OPERATOR

    return {
        "id": row.id,
        "simNo": row.sim_no or row.code or "",
        "phoneMasked": mask_keep(row.phone_number_enc) or "—",
        "operator": row.operator or "",
        "operatorLabel": _OPERATOR.get(row.operator or "", row.operator or ""),
        "realnameName": person.name if person is not None else "",
        "status": row.status,
        "statusLabel": "启用" if row.status == "ENABLED" else "停用",
    }


def _view(row: Phone, *, detail: bool = False) -> dict:
    keeper = user_brief(row.custodian_user_id)
    cards = _sims(row.id)
    data = {
        "id": row.id,
        "deviceNo": row.device_no or "",
        "model": row.model or "",
        "osType": row.os_type or "",
        "osLabel": PHONE_OS.get(row.os_type or "", row.os_type or ""),
        "imeiMasked": mask_imei(row.imei),
        "custodianUserId": row.custodian_user_id,
        "custodianName": keeper["name"],
        "custodianResigned": keeper["resigned"],
        "simText": "、".join(item["phoneMasked"] for item in (_sim_view(card) for card in cards)) or "—",
        "simCount": len(cards),
        "accountCount": len(_accounts(row.id)),
        "status": row.status,
        "statusLabel": PHONE_STATUS.get(row.status, row.status),
        "purchaseDate": row.purchase_date.isoformat() if row.purchase_date else "",
        "purchaseAmount": f"{int(row.purchase_amount or 0) / 100:.2f}",
        "remark": row.remark or "",
        "createTime": format_datetime(row.create_time),
    }
    if detail:
        data["sims"] = [_sim_view(card) for card in cards]
        accounts = _accounts(row.id)
        data["accounts"] = accounts
        data["accountEmpty"] = "" if accounts else "暂无绑定账号"
        data["timeline"] = phone_logs(row.id)
    return data


def _fill(row: Phone, body: dict, creating: bool) -> None:
    if creating or "model" in body:
        row.model = limit(text_of(body, "model"), "model", "型号", 64, required=True)
        row.name = row.model
    if creating or "osType" in body:
        os_type = text_of(body, "osType")
        if not os_type:
            one("osType", "请选择类型")
        if os_type not in PHONE_OS:
            raise BizError(1503, "字典值非法", data={"field": "osType"})
        row.os_type = os_type
    if creating or "custodianUserId" in body:
        user = require_active_user(body.get("custodianUserId"), "custodianUserId", "保管人")
        row.custodian_user_id = user.id
    if creating or "deviceNo" in body:
        if not creating and text_of(body, "deviceNo") and text_of(body, "deviceNo") != (row.device_no or ""):
            one("deviceNo", "设备编号创建后不可修改")
        if creating:
            number = text_of(body, "deviceNo") or phone_no()
            number = limit(number, "deviceNo", "设备编号", 32, required=True)
            taken = get_session().scalar(select(Phone).where(Phone.device_no == number))
            if taken is not None and taken.id != row.id:
                one("deviceNo", "设备编号已存在")
            row.device_no = number
            row.code = number
    if creating or "imei" in body:
        imei = text_of(body, "imei")
        if imei:
            if not imei.isdigit() or len(imei) != 15:
                one("imei", "IMEI 须为 15 位数字")
            taken = get_session().scalar(select(Phone).where(Phone.imei == imei))
            if taken is not None and taken.id != row.id:
                one("imei", "IMEI 已存在")
            row.imei = imei
        elif creating:
            row.imei = None
    if creating or "purchaseDate" in body:
        found = parse_day(body.get("purchaseDate"), "purchaseDate")
        not_future(found, "purchaseDate")
        row.purchase_date = found
    if creating or "purchaseAmount" in body:
        row.purchase_amount = amount_fen(body.get("purchaseAmount"), "purchaseAmount")
    if creating or "remark" in body:
        row.remark = limit(text_of(body, "remark"), "remark", "备注", 256) or None


def page(page_query: Page, params: dict) -> dict:
    where = []
    device_no = text_of(params, "deviceNo")
    if device_no:
        where.append(Phone.device_no.contains(device_no))
    model = text_of(params, "model")
    if model:
        where.append(Phone.model.contains(model))
    os_type = text_of(params, "osType")
    if os_type:
        where.append(Phone.os_type == os_type)
    if params.get("custodianUserId"):
        where.append(Phone.custodian_user_id == parse_api_id(params.get("custodianUserId")))
    status = text_of(params, "status")
    if status:
        where.append(Phone.status == status)
    rows, total = Repository(Phone).page(page_query, *where, order=[Phone.create_time.desc(), Phone.id.desc()])
    return page_result([_view(row) for row in rows], total, page_query)


def detail(ident: int) -> dict:
    return _view(_row(ident), detail=True)


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    row = Phone(status="IN_USE", purchase_amount=0)
    _fill(row, body, creating=True)
    row.status = "IN_USE"
    Repository(Phone).create(row)
    phone_log(row.id, "REGISTER", "登记手机", row.device_no or "")
    get_session().flush()
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = _row(ident)
    if row.status == "SCRAPPED":
        raise BizError(1015, "当前状态不允许此操作")
    before = row.model or ""
    _fill(row, body, creating=False)
    validate_refs_on_write(row)
    assert_dict_values(row)
    phone_log(row.id, "EDIT", "编辑手机", f"型号 {before} → {row.model or ''}")
    get_session().flush()
    return _view(row)


def set_status(ident: int, body: dict) -> dict:
    row = _row(ident)
    status = text_of(body, "status")
    if status not in PHONE_STATUS:
        raise BizError(1503, "字典值非法", data={"field": "status"})
    if row.status == "SCRAPPED":
        raise BizError(1015, "当前状态不允许此操作")
    if status == "SCRAPPED":
        reason = limit(text_of(body, "reason"), "reason", "报废原因", 256, required=True)
        _assert_free(row, "报废")
        row.status = status
        phone_log(row.id, "SCRAP", "报废", reason)
    else:
        if status == row.status:
            return _view(row)
        row.status = status
        phone_log(row.id, "STATUS", f"状态变更为{PHONE_STATUS[status]}", text_of(body, "reason"))
    assert_dict_values(row)
    get_session().flush()
    return _view(row)


def remove(ident: int) -> dict:
    row = _row(ident)
    cards = _sims(row.id)
    if cards:
        raise BizError(1502, f"该手机已被 {len(cards)} 张手机卡引用，不能删除")
    logs = phone_logs(row.id)
    extra = [item for item in logs if item["eventType"] not in {"REGISTER"}]
    if extra:
        raise BizError(1502, "该手机已有后续操作记录，不能删除")
    try:
        Repository(Phone).soft_delete(int(ident))
    except BizError as exc:
        if exc.code == 1502:
            from app.domains.resource.common import ref_blocked

            ref_blocked("手机", exc)
        raise
    return {}


def bind_sims(ident: int, body: dict) -> dict:
    row = _row(ident)
    if row.status == "SCRAPPED":
        raise BizError(1015, "当前状态不允许此操作")
    raw = body.get("simIds")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        one("simIds", "请选择手机卡")
    if len(raw) > _MAX_SIM:
        one("simIds", "一台手机最多绑定 2 张手机卡")
    wanted: list[int] = []
    for item in raw:
        try:
            wanted.append(int(parse_api_id(item)))
        except BizError:
            one("simIds", "请选择手机卡")
    if len(set(wanted)) != len(wanted):
        one("simIds", "手机卡不能重复选择")
    session = get_session()
    current = {card.id: card for card in _sims(row.id)}
    target: dict[int, SimCard] = {}
    for sim_id in wanted:
        card = session.get(SimCard, sim_id)
        if card is None or int(card.deleted or 0) != 0:
            raise BizError(1500, "关联的手机卡不存在", data={"field": "simIds"})
        if card.status != "ENABLED":
            raise BizError(1501, "关联的手机卡已停用，不可选择", data={"field": "simIds"})
        if card.phone_id and int(card.phone_id) != int(row.id):
            raise BizError(1012, "该手机卡已绑定其他手机")
        target[card.id] = card
    for sim_id, card in current.items():
        if sim_id not in target:
            card.phone_id = None
            phone_log(row.id, "UNBIND_SIM", "解绑手机卡", card.sim_no or "")
    for sim_id, card in target.items():
        if sim_id not in current:
            card.phone_id = row.id
            phone_log(row.id, "BIND_SIM", "绑定手机卡", card.sim_no or "")
    session.flush()
    return _view(row, detail=True)


def _accounts(phone_id: int) -> list[dict]:
    from app.domains.account.platform import linked_by_phone

    return linked_by_phone(phone_id)


def _assert_free(row: Phone, action: str) -> None:
    cards = _sims(row.id)
    if cards:
        raise BizError(1502, f"该手机已被 {len(cards)} 张手机卡引用，不能{action}")
    accounts = _accounts(row.id)
    if accounts:
        raise BizError(1502, f"该手机已被{len(accounts)}个平台账号引用，不能{action}")


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
    header = ["设备编号", "型号", "类型", "保管人", "绑定手机卡", "绑定账号数", "状态", "IMEI"]
    body = [
        [item["deviceNo"], item["model"], item["osLabel"], item["custodianName"], item["simText"], item["accountCount"], item["statusLabel"], item["imeiMasked"]]
        for item in rows
    ]
    return remember_export("手机设备.xlsx", header, body, "phone_device")


def selector(page_query: Page, params: dict) -> dict:
    keyword = text_of(params, "keyword")
    ids = text_of(params, "ids")
    stmt = select(Phone).where(Phone.status != "SCRAPPED").order_by(Phone.id.desc())
    if ids:
        wanted = [int(parse_api_id(item)) for item in ids.split(",") if item.strip()]
        rows = list(get_session().scalars(select(Phone).where(Phone.id.in_(wanted)))) if wanted else []
        return page_result([_selector(row) for row in rows], len(rows), page_query)
    rows = list(get_session().scalars(stmt))
    if keyword:
        rows = [row for row in rows if keyword in (row.device_no or "") or keyword in (row.model or "")]
    if not rows and not keyword:
        raise BizError(1221)
    start = (page_query.page_no - 1) * page_query.page_size
    chunk = rows[start : start + page_query.page_size]
    return page_result([_selector(row) for row in chunk], len(rows), page_query)


def _selector(row: Phone) -> dict:
    keeper = user_brief(row.custodian_user_id)
    return {
        "id": row.id,
        "deviceNo": row.device_no or "",
        "model": row.model or "",
        "custodianName": keeper["name"],
        "status": row.status,
        "statusLabel": PHONE_STATUS.get(row.status, row.status),
        "label": f"{row.device_no or ''} {row.model or ''}".strip(),
    }


def bound_count() -> int:
    return int(get_session().scalar(select(func.count()).select_from(Phone).where(Phone.status != "SCRAPPED")) or 0)
