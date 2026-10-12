"""公司资源共用校验、脱敏与引用提示。"""
from __future__ import annotations

import json
import re

from sqlalchemy import select

from app.core.context import get_ctx
from app.core.crypto import hmac_hash
from app.core.errors import BizError
from app.core.sequence import next_value
from app.db.session import get_session

_ID_W = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
_ID_M = "10X98765432"
_CC = "0123456789ABCDEFGHJKLMNPQRTUWXY"
_CW = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
_UNITS = {"手机卡": "张", "证件": "份", "平台账号": "个", "手机": "台", "公司": "家", "实名人": "个", "用户": "人"}


def fail(errors: list[dict]) -> None:
    raise BizError(1001, data={"fieldErrors": errors})


def one(field: str, message: str) -> None:
    fail([{"field": field, "message": message}])


def text_of(body: dict, key: str) -> str:
    value = body.get(key)
    if value is None:
        return ""
    return str(value).strip()


def limit(value: str, field: str, label: str, max_len: int, required: bool = False) -> str:
    if required and not value:
        one(field, f"请填写{label}")
    if len(value) > max_len:
        one(field, f"{label}不能超过 {max_len} 字")
    return value


def parse_int(value, field: str, label: str, low: int, high: int) -> int:
    if value is None or value == "":
        one(field, f"请填写{label}")
    try:
        if isinstance(value, bool) or isinstance(value, float):
            raise ValueError
        number = int(str(value))
    except (TypeError, ValueError):
        one(field, f"{label}须为整数")
    if number < low or number > high:
        one(field, f"{label}范围为 {low}～{high}")
    return number


def money_to_fen(value, field: str = "monthlyRent") -> int:
    if value is None or value == "":
        one(field, "请填写月租")
    text = str(value).strip()
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        one(field, "金额须为不小于 0 的数字，最多两位小数")
    whole, _, frac = text.partition(".")
    frac = (frac + "00")[:2]
    return int(whole) * 100 + int(frac)


def fen_to_yuan(value: int | None) -> str:
    cents = int(value or 0)
    return f"{cents // 100}.{cents % 100:02d}"


def mask_keep(value: str | None, head: int = 3, tail: int = 4) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= head + tail:
        return "****"
    return f"{text[:head]}****{text[-tail:]}"


def valid_mobile(value: str) -> bool:
    return bool(re.fullmatch(r"\d{11}", value))


def id_check_char(body: str) -> str:
    total = sum(int(ch) * weight for ch, weight in zip(body, _ID_W))
    return _ID_M[total % 11]


def valid_id_card(value: str) -> bool:
    text = value.strip().upper()
    if len(text) != 18 or not text[:17].isdigit():
        return False
    return text[-1] == id_check_char(text[:17])


def normalize_id(value: str) -> str:
    return value.strip().upper()


def valid_credit(value: str) -> bool:
    text = value.strip().upper()
    if len(text) != 18 or any(ch not in _CC for ch in text):
        return False
    total = sum(_CC.index(ch) * weight for ch, weight in zip(text[:17], _CW))
    return text[-1] == _CC[(31 - total % 31) % 31]


def normalize_credit(value: str) -> str:
    return value.strip().upper()


def valid_passport(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{5,17}", value))


def valid_iccid(value: str) -> bool:
    return bool(re.fullmatch(r"\d{19,20}", value))


def digest(value: str) -> str:
    return hmac_hash(value)


def next_no(prefix: str, rule: str) -> str:
    return f"{prefix}{next_value(rule):06d}"


def has_perm(code: str) -> bool:
    ctx = get_ctx()
    if ctx is None:
        return False
    if ctx.system:
        return True
    return code in (ctx.perm_codes or set())


def ref_blocked(entity: str, exc: BizError) -> None:
    refs = (exc.data or {}).get("refs") or []
    parts = []
    for item in refs:
        name = str(item.get("entity") or "关联数据")
        count = int(item.get("count") or 0)
        unit = _UNITS.get(name, "条")
        parts.append(f"{count}{unit}{name}")
    detail = "、".join(parts) or "关联数据"
    raise BizError(1502, f"该{entity}已被{detail}引用，不能删除")


def replay(token: str | None):
    text = (token or "").strip()
    if not text:
        return None
    ctx = get_ctx()
    uid = ctx.user_id if ctx else 0
    from app.core.redis_client import get_redis

    cached = get_redis().get(f"ims:idem:b5:{uid}:{text}")
    if not cached:
        return None
    return json.loads(cached)


def remember(token: str | None, payload: dict) -> None:
    text = (token or "").strip()
    if not text:
        return
    ctx = get_ctx()
    uid = ctx.user_id if ctx else 0
    from app.core.redis_client import get_redis

    get_redis().set(f"ims:idem:b5:{uid}:{text}", json.dumps(payload, ensure_ascii=False), ex=86400)


def token_of(body: dict) -> str:
    from app.api.runtime import current_request

    request = current_request()
    header = ""
    if request is not None:
        header = request.headers.get("x-client-token") or ""
    return header or str(body.get("clientToken") or "")


def user_map(ids: list[int]) -> dict[int, object]:
    from app.domains.system.model import User

    clean = [int(item) for item in ids if item]
    if not clean:
        return {}
    rows = get_session().scalars(select(User).where(User.id.in_(clean)).execution_options(include_deleted=True))
    return {int(row.id): row for row in rows}


def dept_name(user) -> str:
    if user is None or not getattr(user, "main_dept_id", None):
        return ""
    from app.domains.system.model import Dept

    dept = get_session().get(Dept, user.main_dept_id)
    return dept.name if dept is not None else ""


def user_ids_with_perm(code: str) -> list[int]:
    from app.domains.system.model import Menu, RoleMenu, User, UserRole

    session = get_session()
    menu_ids = list(session.scalars(select(Menu.id).where(Menu.perm_code == code)))
    if not menu_ids:
        return []
    role_ids = list(session.scalars(select(RoleMenu.role_id).where(RoleMenu.menu_id.in_(menu_ids))))
    if not role_ids:
        return []
    linked = list(
        session.scalars(select(UserRole.user_id).where(UserRole.role_id.in_(role_ids), UserRole.manual_removed == 0))
    )
    if not linked:
        return []
    rows = session.scalars(select(User.id).where(User.id.in_(linked), User.status == "ACTIVE"))
    return sorted({int(item) for item in rows})


def audit_sensitive(biz_type: str, biz_id: int, kind: str) -> None:
    from app.domains.system.model import SensitiveViewLog

    ctx = get_ctx()
    get_session().add(
        SensitiveViewLog(
            biz_type=biz_type,
            biz_id=int(biz_id),
            kind=kind,
            viewer_id=ctx.user_id if ctx else None,
            ip=ctx.client_ip if ctx else "",
        )
    )
    get_session().flush()
