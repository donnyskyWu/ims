"""工作台首页聚合。业务卡片本批固定为 0。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.message.service import unread_count
from app.domains.system.model import Dept, Role, User, UserRole
from app.domains.todo.service import my_count

# 外协角色。仅当用户的全部角色都是该角色时隐藏四张业务卡（WB-08）。
_OUTSOURCE = "R10"


def greeting_by_hour(hour: int) -> str:
    if 5 <= hour < 11:
        return "早上好"
    if 11 <= hour < 13:
        return "中午好"
    if 13 <= hour < 18:
        return "下午好"
    if 18 <= hour < 23:
        return "晚上好"
    return "凌晨好"


def dashboard() -> dict:
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None:
        raise BizError(1008)
    session = get_session()
    user = session.get(User, int(ctx.user_id))
    dept_name = ""
    if user is not None and user.main_dept_id:
        dept = session.get(Dept, user.main_dept_id)
        dept_name = dept.name if dept is not None else ""
    role_names = []
    role_keys = []
    if user is not None:
        links = list(session.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.manual_removed == 0)))
        for link in links:
            role = session.get(Role, link.role_id)
            if role is None or role.deleted or role.status != "ENABLED":
                continue
            role_names.append(role.name)
            role_keys.append(role.role_key)
    counted = my_count()
    unread = unread_count()
    name = ""
    if user is not None:
        name = user.nickname or user.username or ""
    return {
        "greeting": greeting_by_hour(now_naive().hour),
        "displayName": name,
        "deptName": dept_name,
        "roleSummary": "、".join(role_names),
        "todoCount": counted["total"],
        "unreadMessageCount": unread["count"],
        "myAccountCount": 0,
        "myAssetCount": 0,
        "myCertCount": 0,
        "myCertWarningCount": 0,
        "myLiveSessionCount": 0,
        "todoCountByType": counted["byType"],
        "bizCardsVisible": not (role_keys and all(key == _OUTSOURCE for key in role_keys)),
    }
