"""账号域共用校验、编号、时间线与范围。"""
from __future__ import annotations

import json
import re
from datetime import date

from sqlalchemy import select

from app.core.clock import format_datetime, now_naive, today
from app.core.context import get_ctx
from app.core.errors import BizError
from app.db.repository import assert_dict_values, validate_refs_on_write
from app.db.session import get_session
from app.domains.master.model import Company, PersonalAccount, Phone, PlatformAccount, Realname, SimCard
from app.domains.resource.common import fen_to_yuan, has_perm, mask_keep, text_of
from app.domains.system.model import DictData, Timeline, User

PLATFORMS = ("DOUYIN", "KUAISHOU", "WECHAT_CHANNELS", "XIAOHONGSHU", "WECHAT_MP")
PLATFORM_CODE = {
    "DOUYIN": "DYS",
    "KUAISHOU": "KSH",
    "WECHAT_CHANNELS": "WXS",
    "XIAOHONGSHU": "XHS",
    "WECHAT_MP": "GZH",
    "OTHER": "OTH",
}
PLATFORM_LABEL = {
    "DOUYIN": "抖音",
    "KUAISHOU": "快手",
    "WECHAT_CHANNELS": "视频号",
    "XIAOHONGSHU": "小红书",
    "WECHAT_MP": "公众号",
    "WECHAT_OFFICIAL": "公众号",
}
ACCOUNT_STATUS = {
    "IN_POOL": "池可领用",
    "IN_USE": "在用",
    "FROZEN": "冻结",
    "RETURNED": "已归还",
    "CANCELLED": "已注销",
}
OPEN_APPLY = {"PENDING_APPROVAL", "PENDING_HANDOVER"}
_ALIAS = {"WECHAT_OFFICIAL": "WECHAT_MP"}


def fail(errors: list[dict]) -> None:
    raise BizError(1001, data={"fieldErrors": errors})


def one(field: str, message: str) -> None:
    fail([{"field": field, "message": message}])


def limit(value: str, field: str, label: str, max_len: int, required: bool = False) -> str:
    if required and not value:
        one(field, f"请填写{label}")
    if len(value) > max_len:
        one(field, f"{label}不能超过 {max_len} 字")
    return value


def viewer_id() -> int:
    ctx = get_ctx()
    return int(ctx.user_id) if ctx and ctx.user_id else 0


def owner_limit() -> int | None:
    """非全部数据范围时，只看本人负责的账号。"""
    ctx = get_ctx()
    if ctx is None or ctx.system or ctx.skip_scope:
        return None
    scopes = {item for item in (ctx.data_scopes or set()) if item}
    if not scopes or "ALL" in scopes:
        return None
    return int(ctx.user_id or 0)


def mask_amount() -> bool:
    ctx = get_ctx()
    if ctx is None or ctx.system:
        return False
    scopes = {item for item in (ctx.data_scopes or set()) if item}
    if "ALL" not in scopes:
        return False
    writes = {
        "ims:corp:account:create",
        "ims:corp:account:update",
        "ims:corp:account:export",
        "ims:account:recharge:create",
        "ims:account:recharge:verify",
        "ims:account:recharge:export",
        "ims:corp:account:personal:export",
    }
    return not (set(ctx.perm_codes or []) & writes)


def money_text(fen: int | None) -> str:
    if mask_amount():
        return "****"
    return fen_to_yuan(int(fen or 0))


def amount_fen(value, field: str = "amount") -> int:
    if value in (None, ""):
        one(field, "请填写金额")
    text = str(value).strip()
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        one(field, "金额须为大于 0 的数字，最多两位小数")
    whole, _, frac = text.partition(".")
    frac = (frac + "00")[:2]
    cents = int(whole) * 100 + int(frac)
    if cents <= 0:
        one(field, "金额须大于 0")
    return cents


def parse_day(value, field: str, required: bool = False, label: str = "日期") -> date | None:
    if value in (None, ""):
        if required:
            one(field, f"请填写{label}")
        return None
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        one(field, f"{label}格式错误")
        return None


def canon_platform(value: str) -> str:
    text = (value or "").strip().upper()
    return _ALIAS.get(text, text)


def require_platform(value: str) -> str:
    platform = canon_platform(value)
    if platform not in PLATFORMS:
        raise BizError(1503, "字典值非法", data={"field": "platform"})
    _dict("dict_platform_type", platform, "platform")
    return platform


def _dict(dict_type: str, value: str, field: str) -> None:
    row = get_session().scalar(
        select(DictData)
        .where(DictData.dict_type == dict_type, DictData.dict_value.collate("utf8mb4_bin") == value)
        .execution_options(skip_tenant=True)
    )
    if row is None or row.status != "ENABLED" or int(row.deleted or 0) != 0:
        raise BizError(1503, "字典值非法", data={"field": field})


def require_dict(dict_type: str, value: str, field: str, label: str) -> str:
    text = (value or "").strip()
    if not text:
        one(field, f"请选择{label}")
    _dict(dict_type, text, field)
    return text


def user_of(ident: int | None) -> User | None:
    if not ident:
        return None
    return get_session().get(User, int(ident))


def user_brief(ident: int | None) -> dict:
    user = user_of(ident)
    if user is None:
        return {"userId": ident, "name": "", "resigned": False, "deptId": None}
    return {
        "userId": user.id,
        "name": user.nickname or user.username,
        "resigned": user.status == "RESIGNED",
        "deptId": user.main_dept_id,
    }


def require_active_user(ident, field: str, label: str = "用户"):
    if ident in (None, "", 0, "0"):
        one(field, f"请选择{label}")
    from app.core.serialize import parse_api_id

    try:
        number = int(parse_api_id(ident))
    except BizError:
        one(field, f"请选择{label}")
        return None
    user = user_of(number)
    if user is None or int(user.deleted or 0) != 0:
        raise BizError(1500, f"关联的{label}不存在")
    if user.status != "ACTIVE":
        raise BizError(1501, f"关联的{label}已停用，不可选择")
    return user


def require_resigned(ident) -> User:
    from app.core.serialize import parse_api_id

    if ident in (None, "", 0, "0"):
        one("userId", "请选择离职人")
    try:
        number = int(parse_api_id(ident))
    except BizError:
        one("userId", "请选择离职人")
        number = 0
    user = user_of(number)
    if user is None or int(user.deleted or 0) != 0:
        raise BizError(1500, "关联的用户不存在")
    if user.status != "RESIGNED":
        one("userId", "请选择已离职人员")
    return user


def company_of(ident, required: bool = False) -> Company | None:
    return _ref(Company, ident, "companyId", "公司", required, disabled_status="DISABLED")


def realname_of(ident, required: bool = False) -> Realname | None:
    return _ref(Realname, ident, "realnameId", "实名人", required, disabled_status="DISABLED")


def sim_of(ident) -> SimCard | None:
    return _ref(SimCard, ident, "simCardId", "手机卡", False, disabled_status="DISABLED")


def phone_of(ident) -> Phone | None:
    row = _ref(Phone, ident, "phoneId", "手机", False, disabled_status="")
    if row is not None and row.status == "SCRAPPED":
        raise BizError(1015, "当前状态不允许此操作")
    return row


def _ref(model, ident, field: str, label: str, required: bool, disabled_status: str):
    if ident in (None, "", 0, "0"):
        if required:
            one(field, f"请选择{label}")
        return None
    from app.core.serialize import parse_api_id

    try:
        number = int(parse_api_id(ident))
    except BizError:
        one(field, f"请选择{label}")
        return None
    row = get_session().get(model, number)
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1500, f"关联的{label}不存在")
    status = getattr(row, "status", None)
    if disabled_status and status == disabled_status:
        raise BizError(1501, f"关联的{label}已停用，不可选择")
    return row


def next_no(prefix: str, column) -> str:
    rows = list(get_session().scalars(select(column).where(column.like(f"{prefix}%"))))
    highest = 0
    for item in rows:
        tail = str(item or "")[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    width = 3 if prefix.startswith("AC-") or prefix.startswith("PA-") else 4
    return f"{prefix}{highest + 1:0{width}d}"


def account_no_for(platform: str, raw: str) -> str:
    text = (raw or "").strip()
    if text:
        return limit(text, "accountNo", "账号编号", 32)
    stamp = today().strftime("%Y%m%d")
    code = PLATFORM_CODE.get(platform, "OTH")
    return next_no(f"AC-{code}-{stamp}-", PlatformAccount.account_no)


def personal_no(raw: str) -> str:
    text = (raw or "").strip()
    if text:
        return limit(text, "accountNo", "账号编号", 32)
    return next_no(f"PA-{today().strftime('%Y%m%d')}-", PersonalAccount.account_no)


def stamp_no(prefix: str, column) -> str:
    return next_no(prefix + today().strftime("%Y%m%d"), column)


def save(row) -> None:
    validate_refs_on_write(row)
    assert_dict_values(row)
    session = get_session()
    session.add(row)
    session.flush()


def account_row(ident: int) -> PlatformAccount:
    row = get_session().get(PlatformAccount, int(ident))
    if row is None or int(row.deleted or 0) != 0:
        raise BizError(1504, "账号不存在")
    return row


def visible(row: PlatformAccount) -> None:
    owner = owner_limit()
    if owner is None:
        return
    if int(row.owner_user_id or 0) == owner:
        return
    from app.domains.account.model import AccountApply, AccountTransfer

    session = get_session()
    apply_hit = session.scalar(select(AccountApply.id).where(AccountApply.account_id == row.id, AccountApply.applicant_user_id == owner))
    transfer_hit = session.scalar(
        select(AccountTransfer.id).where(
            AccountTransfer.account_id == row.id,
            (AccountTransfer.from_user_id == owner) | (AccountTransfer.to_user_id == owner),
        )
    )
    if apply_hit or transfer_hit:
        return
    raise BizError(1008, "您无权查看该账号")


def log_event(account_id: int, event_type: str, title: str, detail: str = "", ref: str = "") -> None:
    get_session().add(
        Timeline(
            biz_type="ACCOUNT",
            biz_id=int(account_id),
            event_type=event_type,
            title=title[:100],
            detail={"text": detail, "ref": ref} if detail or ref else None,
            operator_id=viewer_id() or None,
            event_time=now_naive(),
        )
    )


def replay(token: str | None):
    text = (token or "").strip()
    if not text:
        return None
    from app.core.redis_client import get_redis

    cached = get_redis().get(f"ims:idem:b7:{viewer_id()}:{text}")
    if not cached:
        return None
    return json.loads(cached)


def remember(token: str | None, payload: dict) -> None:
    text = (token or "").strip()
    if not text:
        return
    from app.core.redis_client import get_redis

    get_redis().set(f"ims:idem:b7:{viewer_id()}:{text}", json.dumps(payload, default=str, ensure_ascii=False), ex=86400)


def token_of(body: dict) -> str:
    from app.domains.resource.common import token_of as raw

    return raw(body)


def names(company_id, realname_id, sim_id, phone_id) -> dict:
    company = get_session().get(Company, company_id) if company_id else None
    person = get_session().get(Realname, realname_id) if realname_id else None
    card = get_session().get(SimCard, sim_id) if sim_id else None
    phone = get_session().get(Phone, phone_id) if phone_id else None
    owner = user_brief(None)
    return {
        "companyName": company.name if company else "",
        "realnameName": mask_keep(person.name, 1, 1) if person and person.name else "",
        "simMasked": card.name if card else "",
        "phoneNo": phone.device_no or "" if phone else "",
        "owner": owner,
    }


def mismatch(account: PlatformAccount) -> list[str]:
    if not account.sim_card_id or not account.realname_id:
        return []
    card = get_session().get(SimCard, account.sim_card_id)
    if card is None or not card.realname_id:
        return []
    if int(card.realname_id) != int(account.realname_id):
        return ["REALNAME_MISMATCH"]
    return []


def dept_name(user_id: int | None) -> str:
    user = user_of(user_id)
    if user is None or not user.main_dept_id:
        return ""
    from app.domains.system.model import Dept

    dept = get_session().get(Dept, user.main_dept_id)
    return dept.name if dept else ""


def page_slice(rows: list, page) -> tuple[list, int]:
    total = len(rows)
    start = (page.page_no - 1) * page.page_size
    return rows[start : start + page.page_size], total


def when(value) -> str:
    return format_datetime(value) if value else ""
