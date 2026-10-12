"""岗位供给。新角色立即生效，旧自动角色 24 小时后回收。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.auth.model import AuthEventLog, PositionRoleExtra, PositionRoleRule
from app.domains.system.model import Role, User, UserRole
from app.domains.todo.model import Todo, TodoAssignee


def apply_position_change(user_id: int, position_code: str, event_id: str) -> dict:
    session = get_session()
    existed = session.scalar(select(AuthEventLog).where(AuthEventLog.event_id == event_id))
    if existed:
        return {"duplicated": True}
    user = session.get(User, user_id)
    if user is None:
        raise BizError(1504)
    session.add(AuthEventLog(event_id=event_id, event_type="POSITION", payload={"userId": user_id, "position": position_code}))
    rule = session.scalar(
        select(PositionRoleRule).where(
            PositionRoleRule.position_code == position_code,
            PositionRoleRule.archived == 0,
            PositionRoleRule.status == "ENABLED",
        )
    )
    if rule is None:
        role = Role(
            role_key=f"auto_{position_code}_{user.tenant_id}",
            name=f"待配置-{position_code}",
            source="DINGTALK_AUTO",
            status="PENDING_CONFIG",
            data_scope=None,
            position_code=position_code,
            is_standard=0,
        )
        session.add(role)
        session.flush()
        rule = PositionRoleRule(position_code=position_code, role_id=role.id, version=1, status="ENABLED", archived=0)
        session.add(rule)
        session.flush()
        _todo_for_role_admins(role.id, position_code)
    extra_ids = [row.role_id for row in session.scalars(select(PositionRoleExtra).where(PositionRoleExtra.rule_id == rule.id))]
    new_ids = [rule.role_id, *extra_ids]
    removed = {
        row.role_id
        for row in session.scalars(select(UserRole).where(UserRole.user_id == user_id, UserRole.manual_removed == 1))
    }
    links = list(session.scalars(select(UserRole).where(UserRole.user_id == user_id)))
    old_position = user.position_code
    if old_position and old_position != position_code:
        for link in links:
            if link.source == "DINGTALK_AUTO" and link.grant_position_code == old_position and link.manual_removed == 0:
                link.revoke_at = now_naive() + timedelta(hours=24)
    for role_id in new_ids:
        if role_id in removed:
            continue
        current = next((link for link in links if link.role_id == role_id), None)
        if current is None:
            session.add(
                UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    source="DINGTALK_AUTO",
                    grant_position_code=position_code,
                    manual_removed=0,
                )
            )
        elif current.manual_removed == 0:
            current.grant_position_code = position_code
            current.revoke_at = None
            current.source = "DINGTALK_AUTO"
    user.position_code = position_code
    session.flush()
    return {"duplicated": False, "roleIds": new_ids}


def set_rule_roles(position_code: str, main_role_id: int, extra_role_ids: list[int]) -> dict:
    if len(extra_role_ids) > 5:
        raise BizError(1001, data={"fieldErrors": [{"field": "extraRoleIds", "message": "附加角色不能超过 5 个"}]})
    session = get_session()
    current = session.scalar(
        select(PositionRoleRule).where(PositionRoleRule.position_code == position_code, PositionRoleRule.archived == 0)
    )
    version = 1
    if current is not None:
        current.archived = 1
        current.status = "DISABLED"
        version = current.version + 1
        if current.role_id:
            old_role = session.get(Role, current.role_id)
            if old_role and old_role.position_code == position_code:
                old_role.position_code = None
    rule = PositionRoleRule(position_code=position_code, role_id=main_role_id, version=version, status="ENABLED", archived=0)
    session.add(rule)
    session.flush()
    for index, role_id in enumerate(extra_role_ids):
        session.add(PositionRoleExtra(rule_id=rule.id, role_id=role_id, sort=index))
    role = session.get(Role, main_role_id)
    if role is not None:
        role.position_code = position_code
    session.flush()
    return {"ruleId": rule.id, "version": version}


def revoke_expired() -> int:
    session = get_session()
    now = now_naive()
    rows = list(session.scalars(select(UserRole).where(UserRole.revoke_at.is_not(None), UserRole.revoke_at <= now, UserRole.source == "DINGTALK_AUTO")))
    for row in rows:
        session.delete(row)
    return len(rows)


def _todo_for_role_admins(role_id: int, position_code: str) -> None:
    session = get_session()
    holders = _holders("ims:system:role:update")
    todo = Todo(
        type="CONFIRM",
        source_module="auth",
        source_type="POSITION_CONFIG",
        source_id=role_id,
        title=f"请配置岗位 {position_code}",
        status="PENDING",
        assignee_perm_code="ims:system:role:update",
    )
    session.add(todo)
    session.flush()
    for user_id in holders:
        session.add(TodoAssignee(todo_id=todo.id, user_id=user_id))


def _holders(perm: str) -> list[int]:
    from app.domains.system.model import Menu, RoleMenu

    session = get_session()
    menu_ids = [row.id for row in session.scalars(select(Menu).where(Menu.perm_code == perm))]
    if not menu_ids:
        return []
    role_ids = [row.role_id for row in session.scalars(select(RoleMenu).where(RoleMenu.menu_id.in_(menu_ids)))]
    if not role_ids:
        return []
    return list({row.user_id for row in session.scalars(select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.manual_removed == 0))})
