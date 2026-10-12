"""实名人主数据。证件号与手机号加密存储，列表与导出只出脱敏值。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import format_datetime
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.db.repository import Repository, assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.master.model import Cert, Realname, SimCard
from app.domains.resource.common import (
    audit_sensitive,
    dept_name,
    digest,
    fail,
    has_perm,
    limit,
    mask_keep,
    next_no,
    normalize_id,
    one,
    ref_blocked,
    remember,
    replay,
    text_of,
    token_of,
    user_map,
    valid_id_card,
    valid_mobile,
    valid_passport,
)
from app.services.exchange import remember_export

_STATUS = {"ENABLED": "启用", "DISABLED": "停用"}
_CERT_LABEL = {
    "PENDING_REVIEW": "待审",
    "EFFECTIVE": "生效",
    "EXPIRING": "即将到期",
    "EXPIRED": "已过期",
    "RECYCLED": "已回收",
}


def _row(ident: int) -> Realname:
    return Repository(Realname).get(int(ident))


def _check_doc(id_type: str, number: str) -> str:
    number = normalize_id(number)
    if id_type == "ID_CARD":
        if not valid_id_card(number):
            one("idNo", "身份证号格式不正确")
    elif id_type == "PASSPORT":
        if not valid_passport(number):
            one("idNo", "护照号须为 5 到 17 位字母或数字")
    elif not number or len(number) > 32:
        one("idNo", "请填写证件号")
    return number


def _latest_id_cert(realname_id: int) -> Cert | None:
    rows = list(
        get_session().scalars(
            select(Cert)
            .where(Cert.realname_id == realname_id, Cert.cert_type == "ID_CARD", Cert.status != "RECYCLED")
            .order_by(Cert.id.desc())
        )
    )
    return rows[0] if rows else None


def cert_expired(realname_id: int) -> bool:
    row = get_session().scalar(select(Cert.id).where(Cert.realname_id == int(realname_id), Cert.status == "EXPIRED"))
    return row is not None


def cert_state(realname_id: int) -> tuple[str, str]:
    row = _latest_id_cert(realname_id)
    if row is None:
        return "NONE", "未建档"
    if row.status == "EXPIRED":
        return "EXPIRED", "已过期"
    return row.status, _CERT_LABEL.get(row.status, row.status)


def _view(row: Realname, *, detail: bool = False) -> dict:
    users = user_map([row.user_id or 0])
    user = users.get(int(row.user_id or 0))
    state, state_label = cert_state(row.id)
    data = {
        "id": row.id,
        "realnameNo": row.realname_no or row.code or "",
        "name": row.name,
        "idType": row.id_type or "",
        "idNoMasked": mask_keep(row.id_no_enc),
        "mobileMasked": mask_keep(row.mobile_enc),
        "agentName": row.agent_name or "",
        "agentMobileMasked": mask_keep(row.agent_mobile_enc),
        "userId": row.user_id,
        "userName": user.nickname if user is not None else "",
        "userStatus": user.status if user is not None else "",
        "certStatus": state,
        "certStatusLabel": state_label,
        "certExpired": state == "EXPIRED",
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "remark": row.remark or "",
        "canPlain": has_perm("ims:corp:realname:plain"),
        "updateTime": format_datetime(row.update_time),
    }
    if detail:
        data["certs"] = _certs(row.id)
        data["simCards"] = _sims(row.id)
        data["accountSummary"] = []
    return data


def _certs(realname_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(Cert).where(Cert.realname_id == realname_id).order_by(Cert.id.desc())))
    return [
        {
            "id": item.id,
            "certType": item.cert_type or "",
            "certNoMasked": mask_keep(item.cert_no_enc),
            "status": item.status,
            "statusLabel": _CERT_LABEL.get(item.status, item.status),
            "expireDate": item.expire_date.isoformat() if item.expire_date else "",
        }
        for item in rows
    ]


def _sims(realname_id: int) -> list[dict]:
    rows = list(get_session().scalars(select(SimCard).where(SimCard.realname_id == realname_id).order_by(SimCard.id.desc())))
    return [
        {
            "id": item.id,
            "simNo": item.sim_no or item.code or "",
            "phoneMasked": mask_keep(item.phone_number_enc),
            "operator": item.operator or "",
            "status": item.status,
            "statusLabel": _STATUS.get(item.status, item.status),
        }
        for item in rows
    ]


def _optional_mobile(body: dict, key: str, field: str, label: str) -> str | None:
    if key not in body:
        return None
    text = text_of(body, key)
    if not text:
        return ""
    if not valid_mobile(text):
        one(field, f"{label}须为 11 位数字")
    return text


def _apply_user(row: Realname, body: dict, creating: bool) -> None:
    if not creating and "userId" not in body:
        return
    raw = body.get("userId")
    if raw in (None, "", 0, "0"):
        row.user_id = None
        return
    from app.core.serialize import parse_api_id

    user_id = parse_api_id(raw)
    taken = get_session().scalar(select(Realname).where(Realname.user_id == user_id))
    if taken is not None and taken.id != row.id:
        one("userId", "该员工已关联实名人")
    row.user_id = user_id


def page(page_query: Page, params: dict) -> dict:
    where = []
    name = text_of(params, "name")
    if name:
        where.append(Realname.name.contains(name))
    id_type = text_of(params, "idType")
    if id_type:
        where.append(Realname.id_type == id_type)
    id_no = text_of(params, "idNo")
    if id_no:
        where.append(Realname.id_no_hash == digest(normalize_id(id_no)))
    status = text_of(params, "status")
    if status:
        where.append(Realname.status == status)
    rows, total = Repository(Realname).page(page_query, *where, order=[Realname.update_time.desc(), Realname.id.desc()])
    return page_result([_view(row) for row in rows], total, page_query)


def detail(ident: int) -> dict:
    return _view(_row(ident), detail=True)


def plain(ident: int) -> dict:
    row = _row(ident)
    audit_sensitive("REALNAME", row.id, "id_no")
    if row.mobile_enc:
        audit_sensitive("REALNAME", row.id, "mobile")
    return {
        "id": row.id,
        "idNo": row.id_no_enc or "",
        "mobile": row.mobile_enc or "",
        "agentMobile": row.agent_mobile_enc or "",
    }


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    row = Realname(status="ENABLED")
    _fill(row, body, creating=True)
    number = next_no("RN", "REALNAME")
    row.code = number
    row.realname_no = number
    row.name = row.name or ""
    Repository(Realname).create(row)
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


def _fill(row: Realname, body: dict, creating: bool) -> None:
    if creating or "name" in body:
        row.name = limit(text_of(body, "name"), "name", "姓名", 32, required=True)
    id_type = text_of(body, "idType") or (row.id_type or "")
    if creating or "idType" in body:
        id_type = text_of(body, "idType") or "ID_CARD"
        row.id_type = id_type
    if creating or text_of(body, "idNo"):
        number = _check_doc(row.id_type or "ID_CARD", text_of(body, "idNo"))
        hashed = digest(number)
        taken = get_session().scalar(select(Realname).where(Realname.id_no_hash == hashed))
        if taken is not None and taken.id != row.id:
            one("idNo", "该证件号已登记为实名人")
        row.id_no_enc = number
        row.id_no_hash = hashed
    elif creating:
        one("idNo", "请填写证件号")
    mobile = _optional_mobile(body, "mobile", "mobile", "手机号")
    if mobile is not None:
        row.mobile_enc = mobile or None
        row.mobile_hash = digest(mobile) if mobile else None
    if creating or "agentName" in body:
        row.agent_name = limit(text_of(body, "agentName"), "agentName", "中介人", 32)
    agent_mobile = _optional_mobile(body, "agentMobile", "agentMobile", "中介人电话")
    if agent_mobile is not None:
        row.agent_mobile_enc = agent_mobile or None
    if creating or "remark" in body:
        row.remark = limit(text_of(body, "remark"), "remark", "备注", 255)
    if creating or "status" in body:
        status = text_of(body, "status") or "ENABLED"
        if status not in _STATUS:
            fail([{"field": "status", "message": "状态不正确"}])
        row.status = status
    _apply_user(row, body, creating)


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
        Repository(Realname).soft_delete(int(ident))
    except BizError as exc:
        if exc.code == 1502:
            ref_blocked("实名人", exc)
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
    header = ["实名人编号", "姓名", "证件类型", "证件号", "手机号", "中介人", "关联员工", "证件状态", "状态"]
    body = [
        [
            item["realnameNo"],
            item["name"],
            item["idType"],
            item["idNoMasked"],
            item["mobileMasked"],
            item["agentName"],
            item["userName"] or "—",
            item["certStatusLabel"],
            item["statusLabel"],
        ]
        for item in rows
    ]
    return remember_export("实名人.xlsx", header, body, "realname")
