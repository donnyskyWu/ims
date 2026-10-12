"""标准夹具。叠在种子之上。"""
from __future__ import annotations

from sqlalchemy import select

from app.core.context import system_context, use_context
from app.core.security import hash_password
from app.db.session import get_session
from app.domains.demo.model import DemoOrder
from app.domains.master.model import IpGroup, IpMember
from app.domains.system.model import Dept, Menu, Role, RoleMenu, Tenant, TenantPackage, TenantPackageMenu, User, UserDept, UserRole
from tools.seed.apply import apply

ROOT, D1, D11, D12, D2, DX = 10, 11, 12, 13, 14, 15
U_ADMIN, U_DEPT, U_IPG, U_SELF, U_RO, U_NONE, U_FROZEN, U_RESIGNED, T2_ADMIN = 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 2001
U_OVERLAP, U_D11, U_D12 = 1101, 1102, 1103
PASSWORD = "Abc12345"


def build(env: str = "test") -> None:
    apply(env)
    session = get_session()
    with use_context(system_context(1)):
        _tenant2(session)
        _depts(session)
        _roles(session)
        _users(session)
        _orders(session)
        session.flush()


def _tenant2(session):
    if session.get(TenantPackage, 2) is None:
        session.add(TenantPackage(id=2, name="仅系统管理", status="ENABLED", tenant_id=1))
        session.flush()
        menu = session.scalar(select(Menu).where(Menu.name == "系统管理", Menu.type == "DIR"))
        session.add(TenantPackageMenu(package_id=2, menu_id=menu.id, tenant_id=1))
    if session.get(Tenant, 2) is None:
        session.add(Tenant(id=2, name="租户二", package_id=2, status="ENABLED", tenant_id=1))
    session.flush()


def _depts(session):
    specs = [
        (D1, ROOT, "市场部", "DINGTALK", 100),
        (D11, D1, "市场一组", "DINGTALK", 101),
        (D12, D1, "市场二组", "LOCAL", None),
        (D2, ROOT, "技术部", "DINGTALK", 200),
    ]
    root = session.get(Dept, ROOT)
    for ident, parent_id, name, source, ding in specs:
        if session.get(Dept, ident) is None:
            parent = session.get(Dept, parent_id)
            row = Dept(
                id=ident,
                parent_id=parent_id,
                name=name,
                source=source,
                status="ENABLED",
                dingtalk_dept_id=ding,
                path=f"{parent.path}{ident}/",
                tenant_id=1,
            )
            session.add(row)
    session.flush()


def _roles(session):
    specs = [
        (202, "fix_dept", "夹具部门", "DEPT", ["ims:demo:order:query", "ims:system:user:query", "ims:system:dept:query", "ims:demo:order:create"]),
        (203, "fix_ipg", "夹具IP组", "IP_GROUP", ["ims:demo:order:query"]),
        (204, "fix_self", "夹具本人", "SELF", ["ims:demo:order:query"]),
        (205, "fix_ro", "夹具只读", "ALL", ["ims:system:user:query", "ims:demo:order:query"]),
        (206, "fix_t2", "夹具租户二", "ALL", ["ims:system:user:query", "ims:demo:order:query", "ims:system:menu:create"]),
    ]
    menus = {menu.perm_code: menu for menu in session.scalars(select(Menu)) if menu.perm_code}
    for ident, key, name, scope, codes in specs:
        tenant = 2 if ident == 206 else 1
        with use_context(system_context(tenant)):
            if session.get(Role, ident) is None:
                session.add(Role(id=ident, role_key=key, name=name, source="MANUAL", status="ENABLED", data_scope=scope, is_standard=0, tenant_id=tenant))
                session.flush()
                for code in codes:
                    session.add(RoleMenu(role_id=ident, menu_id=menus[code].id, tenant_id=tenant))
                session.flush()


def _add_user(session, ident, username, nickname, status, role_id, depts, main, tenant=1):
    if session.get(User, ident):
        return
    password = hash_password(PASSWORD)
    session.add(
        User(
            id=ident,
            username=username,
            nickname=nickname,
            password_hash=password,
            status=status,
            tenant_id=tenant,
            main_dept_id=main,
            source="LOCAL",
        )
    )
    session.flush()
    if role_id:
        session.add(UserRole(user_id=ident, role_id=role_id, source="MANUAL", tenant_id=tenant))
    for dept_id in depts:
        session.add(UserDept(user_id=ident, dept_id=dept_id, is_main=1 if dept_id == main else 0, source="LOCAL", tenant_id=tenant))
    session.flush()


def _users(session):
    _add_user(session, U_ADMIN, "u_admin", "管理员", "ACTIVE", 101, [D1], D1)
    _add_user(session, U_DEPT, "u_dept", "部门用户", "ACTIVE", 202, [D1, D2], D1)
    _add_user(session, U_IPG, "u_ipg", "IP组用户", "ACTIVE", 203, [D2], D2)
    _add_user(session, U_SELF, "u_self", "本人用户", "ACTIVE", 204, [D2], D2)
    _add_user(session, U_RO, "u_ro", "只读用户", "ACTIVE", 205, [D2], D2)
    _add_user(session, U_NONE, "u_none", "无权限", "ACTIVE", None, [DX], DX)
    _add_user(session, U_FROZEN, "u_frozen", "冻结", "FROZEN", 101, [D2], D2)
    _add_user(session, U_RESIGNED, "u_resigned", "离职", "RESIGNED", 101, [DX], DX)
    _add_user(session, U_OVERLAP, "u_overlap", "兼任", "ACTIVE", None, [D1, D11], D1)
    _add_user(session, U_D11, "u_d11", "一组", "ACTIVE", None, [D11], D11)
    _add_user(session, U_D12, "u_d12", "二组", "ACTIVE", None, [D12], D12)
    if session.get(IpGroup, 21) is None:
        session.add(IpGroup(id=21, name="G1", code="G1", status="ENABLED", tenant_id=1))
        session.flush()
        session.add(IpMember(group_id=21, user_id=U_IPG, tenant_id=1))
    with use_context(system_context(2)):
        _add_user(session, T2_ADMIN, "t2_admin", "租户二管理员", "ACTIVE", 206, [], None, tenant=2)


def _orders(session):
    rows = [
        ("OD1", D1, None, U_ADMIN, 1),
        ("OD2", D2, None, U_ADMIN, 1),
        ("OD11", D11, None, U_ADMIN, 1),
        ("OD12", D12, None, U_ADMIN, 1),
        ("OG1", None, 21, U_IPG, 1),
        ("OSELF", None, None, U_SELF, 1),
        ("T2A", D1, None, T2_ADMIN, 2),
        ("T2B", D1, None, T2_ADMIN, 2),
    ]
    for code, dept, ipg, owner, tenant in rows:
        if session.scalar(select(DemoOrder).where(DemoOrder.code == code, DemoOrder.tenant_id == tenant)):
            continue
        with use_context(system_context(tenant)):
            session.add(DemoOrder(code=code, name=code, dept_id=dept, ip_group_id=ipg, owner_user_id=owner, status="ACTIVE", tenant_id=tenant, amount=1))
            session.flush()
