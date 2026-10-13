"""个人账号台账。不参与领用、流转、归还、冲话费和采集。"""
from __future__ import annotations

from sqlalchemy import or_, select

from app.core.crypto import hmac_hash
from app.core.errors import BizError
from app.core.pagination import page_result
from app.db.repository import Repository
from app.db.session import get_session
from app.domains.account.support import (
    limit,
    page_slice,
    personal_no,
    remember,
    replay,
    require_active_user,
    require_dict,
    text_of,
    token_of,
    user_brief,
    when,
)
from app.domains.master.model import PersonalAccount
from app.domains.resource.common import mask_keep, valid_mobile
from app.services.exchange import remember_export

_TYPE = {"WEWORK": "企业微信", "WECHAT": "个人微信"}
_STATUS = {"ENABLED": "启用", "DISABLED": "停用"}


def page(page_query, params: dict) -> dict:
    rows = _filtered(params)
    chunk, total = page_slice(rows, page_query)
    return page_result([_view(row) for row in chunk], total, page_query)


def detail(ident: int) -> dict:
    return _view(_row(ident))


def create(body: dict) -> dict:
    cached = replay(token_of(body))
    if cached:
        return cached
    row = PersonalAccount(status="ENABLED", name="")
    _fill(row, body, creating=True)
    number = personal_no(text_of(body, "accountNo"))
    _unique(number, None)
    row.account_no = number
    row.code = number
    from app.domains.account.support import save

    save(row)
    payload = _view(row)
    remember(token_of(body), payload)
    return payload


def update(ident: int, body: dict) -> dict:
    row = _row(ident)
    _fill(row, body, creating=False)
    from app.domains.account.support import save

    save(row)
    return _view(row)


def set_status(ident: int, body: dict) -> dict:
    row = _row(ident)
    status = text_of(body, "status")
    require_dict("dict_common_status", status, "status", "状态")
    row.status = status
    from app.domains.account.support import save

    save(row)
    return _view(row)


def remove(ident: int) -> dict:
    Repository(PersonalAccount).soft_delete(_row(ident).id)
    return {}


def export(params: dict) -> dict:
    rows = [_view(row) for row in _filtered(params)]
    header = ["账号编号", "类型", "昵称", "归属员工", "手机号", "状态"]
    body = [[item["accountNo"], item["accountTypeLabel"], item["nickname"], item["ownerName"], item["mobileMask"], item["statusLabel"]] for item in rows]
    return remember_export("个人账号.xlsx", header, body, "account_personal")


def _row(ident: int) -> PersonalAccount:
    row = get_session().get(PersonalAccount, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    return row


def _fill(row: PersonalAccount, body: dict, creating: bool) -> None:
    if creating or "accountType" in body:
        row.account_type = require_dict("dict_personal_account_type", text_of(body, "accountType"), "accountType", "类型")
    if creating or "nickname" in body:
        row.nickname = limit(text_of(body, "nickname"), "nickname", "昵称", 64, required=True)
        row.name = row.nickname
    if creating or "ownerUserId" in body:
        raw = body.get("ownerUserId")
        if raw in (None, "", 0, "0"):
            row.owner_user_id = None
        else:
            row.owner_user_id = require_active_user(raw, "ownerUserId", "归属员工").id
    if creating or "mobile" in body:
        mobile = text_of(body, "mobile")
        if mobile:
            if not valid_mobile(mobile):
                from app.domains.account.support import one

                one("mobile", "手机号须为 11 位数字")
            row.mobile_mask = mask_keep(mobile)
            row.mobile_hash = hmac_hash(mobile)
        elif "mobile" in body:
            row.mobile_mask = ""
            row.mobile_hash = ""
    if "remark" in body or creating:
        row.remark = limit(text_of(body, "remark"), "remark", "备注", 256)


def _unique(number: str, current: int | None) -> None:
    found = get_session().scalar(select(PersonalAccount).where(PersonalAccount.account_no == number))
    if found is not None and found.id != current:
        from app.domains.account.support import one

        one("accountNo", "账号编号已存在")


def _filtered(params: dict) -> list[PersonalAccount]:
    stmt = select(PersonalAccount).order_by(PersonalAccount.update_time.desc(), PersonalAccount.id.desc())
    kind = text_of(params, "accountType")
    if kind:
        require_dict("dict_personal_account_type", kind, "accountType", "类型")
        stmt = stmt.where(PersonalAccount.account_type == kind)
    status = text_of(params, "status")
    if status:
        require_dict("dict_common_status", status, "status", "状态")
        stmt = stmt.where(PersonalAccount.status == status)
    owner = text_of(params, "ownerUserId")
    if owner:
        from app.core.serialize import parse_api_id

        stmt = stmt.where(PersonalAccount.owner_user_id == int(parse_api_id(owner)))
    keyword = text_of(params, "keyword")
    if keyword:
        stmt = stmt.where(or_(PersonalAccount.account_no.contains(keyword), PersonalAccount.nickname.contains(keyword)))
    return list(get_session().scalars(stmt))


def _view(row: PersonalAccount) -> dict:
    owner = user_brief(row.owner_user_id)
    return {
        "id": row.id,
        "accountNo": row.account_no or row.code or "",
        "accountType": row.account_type or "",
        "accountTypeLabel": _TYPE.get(row.account_type or "", row.account_type or ""),
        "nickname": row.nickname or row.name,
        "ownerUserId": row.owner_user_id,
        "ownerName": owner["name"],
        "mobileMask": row.mobile_mask or "",
        "status": row.status,
        "statusLabel": _STATUS.get(row.status, row.status),
        "remark": row.remark or "",
        "updateTime": when(row.update_time),
    }
