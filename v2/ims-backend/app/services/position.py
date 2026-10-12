"""岗位供给。新角色立即生效，旧自动角色 24 小时后回收。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.auth.model import AuthEventLog, PositionRoleExtra, PositionRoleRule, PositionRuleRole, PositionRuleVersion
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
        parked = session.scalar(
            select(PositionRoleRule).where(
                PositionRoleRule.position_code == position_code,
                PositionRoleRule.archived == 0,
                PositionRoleRule.status == "DISABLED",
            )
        )
        if parked is not None:
            user.position_code = position_code
            user.perm_version = int(user.perm_version or 1) + 1
            session.flush()
            return {"duplicated": False, "roleIds": [], "skipped": "DISABLED_RULE"}
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
        rule = PositionRoleRule(
            position_code=position_code,
            role_id=role.id,
            version=1,
            status="ENABLED",
            archived=0,
            rule_name=position_code[:64],
            active_slot=position_code[:64],
        )
        session.add(rule)
        session.flush()
        session.add(PositionRuleRole(rule_id=rule.id, role_id=role.id, role_type="MAIN"))
        _write_version(rule, [], "AUTO_CREATE", operator_id=0)
        _todo_for_role_admins(role.id, position_code)
    extra_ids = _extra_role_ids(rule.id)
    new_ids = [rule.role_id, *extra_ids]
    removed = {
        row.role_id
        for row in session.scalars(select(UserRole).where(UserRole.user_id == user_id, UserRole.manual_removed == 1))
    }
    links = list(session.scalars(select(UserRole).where(UserRole.user_id == user_id, UserRole.manual_removed == 0)))
    old_position = user.position_code
    if old_position and old_position != position_code:
        for link in links:
            if link.source != "DINGTALK_AUTO" or link.grant_position_code != old_position:
                continue
            if link.role_id in new_ids:
                continue
            if link.revoke_at is None:
                link.revoke_at = now_naive() + timedelta(hours=24)
    for role_id in new_ids:
        if role_id in removed:
            continue
        current = next((link for link in links if link.role_id == role_id and link.source == "DINGTALK_AUTO"), None)
        if current is None:
            session.add(
                UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    source="DINGTALK_AUTO",
                    grant_position_code=position_code,
                    manual_removed=0,
                    rule_id=rule.id,
                    rule_version=rule.version,
                )
            )
        else:
            current.grant_position_code = position_code
            current.revoke_at = None
            current.rule_id = rule.id
            current.rule_version = rule.version
    user.position_code = position_code
    user.perm_version = int(user.perm_version or 1) + 1
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
        current.active_slot = None
        if current.rule_name:
            current.rule_name = f"{current.rule_name[:40]}~{current.id}"[:64]
        version = current.version + 1
        if current.role_id:
            old_role = session.get(Role, current.role_id)
            if old_role and old_role.position_code == position_code:
                old_role.position_code = None
        session.flush()
    rule = PositionRoleRule(
        position_code=position_code,
        role_id=main_role_id,
        version=version,
        status="ENABLED",
        archived=0,
        rule_name=position_code[:64],
        active_slot=position_code[:64],
    )
    session.add(rule)
    session.flush()
    _replace_role_rows(rule.id, main_role_id, extra_role_ids)
    _write_version(rule, extra_role_ids, "CREATE" if version == 1 else "EDIT")
    role = session.get(Role, main_role_id)
    if role is not None:
        role.position_code = position_code
    session.flush()
    return {"ruleId": rule.id, "version": version}


def revoke_expired() -> int:
    session = get_session()
    now = now_naive()
    rows = list(session.scalars(select(UserRole).where(UserRole.revoke_at.is_not(None), UserRole.revoke_at <= now, UserRole.source == "DINGTALK_AUTO")))
    touched: set[int] = set()
    for row in rows:
        touched.add(row.user_id)
        session.delete(row)
    for user_id in touched:
        user = session.get(User, user_id)
        if user is not None:
            user.perm_version = int(user.perm_version or 1) + 1
    return len(rows)


def _extra_role_ids(rule_id: int) -> list[int]:
    session = get_session()
    typed = [row.role_id for row in session.scalars(select(PositionRuleRole).where(PositionRuleRole.rule_id == rule_id, PositionRuleRole.role_type == "EXTRA"))]
    if typed:
        return typed
    return [row.role_id for row in session.scalars(select(PositionRoleExtra).where(PositionRoleExtra.rule_id == rule_id))]


def _replace_role_rows(rule_id: int, main_role_id: int, extra_role_ids: list[int]) -> None:
    session = get_session()
    for row in session.scalars(select(PositionRoleExtra).where(PositionRoleExtra.rule_id == rule_id)):
        session.delete(row)
    for row in session.scalars(select(PositionRuleRole).where(PositionRuleRole.rule_id == rule_id)):
        session.delete(row)
    session.flush()
    session.add(PositionRuleRole(rule_id=rule_id, role_id=main_role_id, role_type="MAIN"))
    for index, role_id in enumerate(extra_role_ids):
        session.add(PositionRoleExtra(rule_id=rule_id, role_id=role_id, sort=index))
        session.add(PositionRuleRole(rule_id=rule_id, role_id=role_id, role_type="EXTRA"))


def _write_version(rule: PositionRoleRule, extra_role_ids: list[int], change_type: str, operator_id: int | None = None) -> None:
    from app.core.context import get_ctx

    ctx = get_ctx()
    actor = operator_id if operator_id is not None else (ctx.user_id if ctx and ctx.user_id else 0)
    get_session().add(
        PositionRuleVersion(
            rule_id=rule.id,
            version=rule.version,
            rule_name=rule.rule_name,
            main_role_id=rule.role_id,
            extra_role_ids=list(extra_role_ids),
            description=rule.description,
            status=rule.status,
            change_type=change_type,
            operator_id=actor or None,
        )
    )


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
