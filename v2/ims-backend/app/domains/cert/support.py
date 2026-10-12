"""证件共用：范围、分级、剩余天数。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.clock import today
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.serialize import parse_api_id, parse_date
from app.db.session import get_session
from app.domains.master.model import Cert, Realname
from app.domains.resource.common import dept_name, mask_keep, user_map

LONG_TERM = date(9999, 12, 31)
ACTIVE = ("EFFECTIVE", "EXPIRING")
_STATUS = {
    "PENDING_REVIEW": "待审",
    "EFFECTIVE": "生效",
    "EXPIRING": "即将到期",
    "EXPIRED": "已过期-锁定",
    "RECYCLED": "已回收",
}
_LEVEL = {"YELLOW": "黄色", "RED": "红色", "LOCKED": "锁定"}
_TASK = {"WARNING": "预警中", "RENEW_RESOLVED": "已换证", "EXPIRED_LOCKED": "已锁定"}


def status_label(value: str | None) -> str:
    return _STATUS.get(value or "", value or "")


def warn_label(value: str | None) -> str:
    return _LEVEL.get(value or "", value or "")


def task_label(value: str | None) -> str:
    return _TASK.get(value or "", value or "")


def parse_day(value, field: str, label: str) -> date:
    if value in (None, ""):
        from app.domains.resource.common import one

        one(field, f"请填写{label}")
    try:
        return parse_date(value)
    except BizError:
        from app.domains.resource.common import one

        one(field, f"{label}格式不正确")
    raise AssertionError("unreachable")


def ident_of(value) -> int:
    return int(parse_api_id(value))


def remain(expire: date | None) -> dict:
    if expire is None:
        return {"remainDays": None, "remainText": "", "remainTone": ""}
    if expire == LONG_TERM:
        return {"remainDays": None, "remainText": "长期", "remainTone": ""}
    days = (expire - today()).days
    if days <= 0:
        tone = "danger"
        text = "已过期"
    elif days <= 7:
        tone = "danger"
        text = f"{days} 天"
    elif days <= 30:
        tone = "warning"
        text = f"{days} 天"
    else:
        tone = "success"
        text = f"{days} 天"
    return {"remainDays": days, "remainText": text, "remainTone": tone}


def warn_level_for(expire: date | None) -> str | None:
    if expire is None or expire == LONG_TERM:
        return None
    days = (expire - today()).days
    if days <= 0:
        return "LOCKED"
    if days <= 7:
        return "RED"
    if days <= 30:
        return "YELLOW"
    return None


def scope_realname_ids() -> list[int] | None:
    """全部数据不限制；部门看本部门关联员工；其余只看本人关联的实名人。"""
    ctx = get_ctx()
    if ctx is None or ctx.system or "ALL" in (ctx.data_scopes or set()):
        return None
    from app.domains.system.model import User

    session = get_session()
    if "DEPT" in (ctx.data_scopes or set()):
        dept_ids = [int(item) for item in (ctx.dept_ids or [])]
        user_ids = set()
        if dept_ids:
            user_ids.update(int(item) for item in session.scalars(select(User.id).where(User.main_dept_id.in_(dept_ids))))
        if ctx.user_id:
            user_ids.add(int(ctx.user_id))
        if not user_ids:
            return [-1]
        found = [int(item) for item in session.scalars(select(Realname.id).where(Realname.user_id.in_(user_ids)))]
        return found or [-1]
    if not ctx.user_id:
        return [-1]
    found = [int(item) for item in session.scalars(select(Realname.id).where(Realname.user_id == int(ctx.user_id)))]
    return found or [-1]


def load_cert(ident: int) -> Cert:
    from app.db.repository import Repository

    return Repository(Cert).get(int(ident))


def holder(realname_id: int | None) -> dict:
    if not realname_id:
        return {"realnameId": None, "holderName": "", "deptName": "", "holderUserId": None, "external": True}
    row = get_session().get(Realname, int(realname_id))
    if row is None:
        return {"realnameId": realname_id, "holderName": "", "deptName": "", "holderUserId": None, "external": True}
    users = user_map([row.user_id or 0])
    user = users.get(int(row.user_id or 0))
    return {
        "realnameId": row.id,
        "holderName": row.name,
        "deptName": dept_name(user),
        "holderUserId": row.user_id,
        "external": row.user_id is None,
        "realnameStatus": row.status,
    }


def masked_no(row: Cert) -> str:
    return mask_keep(row.cert_no_enc)


def role_ids() -> set[int]:
    ctx = get_ctx()
    if ctx is None or not ctx.user_id:
        return set()
    from app.domains.system.model import UserRole

    rows = get_session().scalars(
        select(UserRole.role_id).where(UserRole.user_id == int(ctx.user_id), UserRole.manual_removed == 0)
    )
    return {int(item) for item in rows}


def level_row():
    from app.domains.cert.model import CertLevelConfig

    session = get_session()
    row = session.scalar(select(CertLevelConfig).order_by(CertLevelConfig.id.asc()))
    return row


def view_level(cert: Cert) -> str:
    """L3 白名单优先，其次 L2 角色，再次本人证件，其余 L1。"""
    ctx = get_ctx()
    uid = int(ctx.user_id) if ctx and ctx.user_id else 0
    config = level_row()
    l3 = {int(item) for item in ((config.l3_user_ids if config else None) or [])}
    l2 = {int(item) for item in ((config.l2_role_ids if config else None) or [])}
    if uid and uid in l3:
        return "L3"
    if role_ids() & l2:
        return "L2"
    person = holder(cert.realname_id)
    if uid and person.get("holderUserId") and int(person["holderUserId"]) == uid:
        return "L2"
    return "L1"


def watermark_text() -> str:
    from app.domains.file.service import viewer_label

    return viewer_label()
