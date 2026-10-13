"""每次请求从库装载权限，授权变更立即生效。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.context import RequestContext
from app.core.errors import BizError
from app.db.session import get_session
from app.domains.master.model import IpGroup, IpMember
from app.domains.system.model import Menu, Role, RoleMenu, Tenant, TenantPackageMenu, User, UserDept, UserRole
from app.services.sessions import assert_tenant_open


def build_principal(user_id: int, tenant_id: int) -> RequestContext:
    session = get_session()
    user = session.get(User, user_id)
    if user is None or user.deleted or user.tenant_id != tenant_id:
        raise BizError(1002)
    if user.status in {"FROZEN", "RESIGNED"}:
        raise BizError(1002)
    assert_tenant_open(tenant_id)
    now = now_naive()
    role_rows = list(
        session.scalars(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.manual_removed == 0)
        )
    )
    active_roles = []
    for link in role_rows:
        if link.revoke_at is not None and link.revoke_at <= now:
            continue
        role = session.get(Role, link.role_id)
        if role is None or role.deleted or role.status != "ENABLED":
            continue
        active_roles.append(role)
    package_perms = _package_perm_codes(tenant_id)
    perm_codes: set[str] = set()
    scopes: set[str] = set()
    for role in active_roles:
        if role.data_scope:
            scopes.add(role.data_scope)
        menus = list(session.scalars(select(Menu).join(RoleMenu, RoleMenu.menu_id == Menu.id).where(RoleMenu.role_id == role.id)))
        for menu in menus:
            if not menu.perm_code:
                continue
            if package_perms is not None and menu.perm_code not in package_perms:
                continue
            perm_codes.add(menu.perm_code)
    dept_ids = [row.dept_id for row in session.scalars(select(UserDept).where(UserDept.user_id == user_id))]
    member_ids = [row.group_id for row in session.scalars(select(IpMember).where(IpMember.user_id == user_id))]
    leader_ids = list(session.scalars(select(IpGroup.id).where(IpGroup.leader_user_id == user_id)))
    ip_ids = list({int(item) for item in [*member_ids, *leader_ids] if item})
    return RequestContext(
        user_id=user.id,
        tenant_id=user.tenant_id,
        perm_codes=perm_codes,
        data_scopes=scopes,
        dept_ids=dept_ids,
        ip_group_ids=ip_ids,
        username=user.username,
        nickname=user.nickname,
        pwd_reset_required=bool(user.pwd_reset_required),
    )


def _package_perm_codes(tenant_id: int) -> set[str] | None:
    """平台租户不受套餐限制。返回 None 表示不限制。"""
    if tenant_id == 1:
        return None
    session = get_session()
    tenant = session.get(Tenant, tenant_id)
    if tenant is None or tenant.package_id is None:
        return set()
    menu_ids = set(
        session.scalars(select(TenantPackageMenu.menu_id).where(TenantPackageMenu.package_id == tenant.package_id))
    )
    if not menu_ids:
        return set()
    menus = list(session.scalars(select(Menu)))
    by_parent: dict[int, list] = {}
    for menu in menus:
        by_parent.setdefault(int(menu.parent_id or 0), []).append(menu)
    allowed_ids = set(menu_ids)
    stack = list(menu_ids)
    while stack:
        current = stack.pop()
        for child in by_parent.get(current, []):
            if child.id not in allowed_ids:
                allowed_ids.add(child.id)
                stack.append(child.id)
    return {menu.perm_code for menu in menus if menu.id in allowed_ids and menu.perm_code}
