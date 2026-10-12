"""幂等种子。已存在的菜单名、参数值不覆盖。培训 AI 不进系统参数。"""
from __future__ import annotations

from sqlalchemy import select

from app.catalog import DICT_ROWS, DICT_TYPE_NAMES, MENU_TREE
from app.core.context import system_context, use_context
from app.core.security import hash_password
from app.db.session import get_session
from app.domains.system.model import (
    DictData,
    DictType,
    Menu,
    Param,
    Role,
    RoleMenu,
    Tenant,
    TenantPackage,
    TenantPackageMenu,
    User,
    UserRole,
)
from app.domains.system.service import init_tenant

ROLES = [
    (101, "R1", "系统管理员", "ALL"),
    (102, "R2", "行政管理员", "ALL"),
    (103, "R3", "财务", "ALL"),
    (104, "R4", "运营管理者", "ALL"),
    (105, "R5", "运营组长", "DEPT"),
    (106, "R6", "审核", "DEPT"),
    (107, "R7", "运营人员", "SELF"),
    (108, "R8", "内容编辑", "DEPT"),
    (109, "R9", "数据分析师", "ALL"),
    (110, "R10", "外协", "SELF"),
    (111, "R11", "AI资产管理员", "ALL"),
]

PARAMS = [
    ("perf.grade.excellent", "优秀线", "绩效", "NUMBER", "90", "0", "100"),
    ("content.review.level1.role", "一级审核角色", "内容", "ROLE_REF", "", None, None),
    ("dingtalk.notify.enabled", "钉钉通知开关", "通知", "TEXT", "true", None, None),
    ("dingtalk_attendance.app_secret", "考勤应用密钥", "钉钉考勤", "SECRET", "", None, None),
    ("air.model.base_url", "内容模型地址", "内容", "TEXT", "http://127.0.0.1:9/air", None, None),
]


def apply(env: str = "test") -> None:
    session = get_session()
    with use_context(system_context(1)):
        _packages(session)
        _dicts(session)
        menus = _menus(session)
        _params(session)
        _roles(session, menus)
        _users(session)
        _tenant_dept(session)
        if env == "e2e":
            _e2e_roles(session)
        session.flush()


def _packages(session):
    if session.get(TenantPackage, 1) is None:
        session.add(TenantPackage(id=1, name="全量", status="ENABLED", tenant_id=1))
    if session.get(Tenant, 1) is None:
        session.add(Tenant(id=1, name="平台", package_id=1, status="ENABLED", tenant_id=1))
    session.flush()


def _dicts(session):
    for key, name in DICT_TYPE_NAMES.items():
        if session.scalar(select(DictType).where(DictType.dict_type == key)) is None:
            session.add(DictType(dict_type=key, name=name, status="ENABLED", tenant_id=1))
    session.flush()
    for dict_type, value, label, color, ext in DICT_ROWS:
        exists = session.scalar(select(DictData).where(DictData.dict_type == dict_type, DictData.dict_value == value))
        if exists is None:
            session.add(
                DictData(
                    dict_type=dict_type,
                    dict_value=value,
                    dict_label=label,
                    color_type=color,
                    status="ENABLED",
                    is_builtin=1,
                    ext_code=ext,
                    tenant_id=1,
                )
            )
    session.flush()


def _menus(session):
    by_perm = {}
    for item in MENU_TREE:
        parent = session.scalar(select(Menu).where(Menu.name == item["name"], Menu.parent_id == 0, Menu.type == "DIR"))
        if parent is None:
            parent = Menu(name=item["name"], type="DIR", path=item.get("path"), sort=item.get("sort") or 0, status="ENABLED", tenant_id=1, parent_id=0)
            session.add(parent)
            session.flush()
        for child in item["children"]:
            row = session.scalar(select(Menu).where(Menu.perm_code == child["perm"]))
            if row is None:
                row = Menu(name=child["name"], type="BUTTON", perm_code=child["perm"], parent_id=parent.id, status="ENABLED", tenant_id=1)
                session.add(row)
                session.flush()
            by_perm[child["perm"]] = row
    if session.scalar(select(TenantPackageMenu).where(TenantPackageMenu.package_id == 1)) is None:
        for menu in session.scalars(select(Menu)):
            session.add(TenantPackageMenu(package_id=1, menu_id=menu.id, tenant_id=1))
    session.flush()
    return by_perm


def _params(session):
    for key, name, group, value_type, value, lo, hi in PARAMS:
        row = session.scalar(select(Param).where(Param.param_key == key))
        if row is None:
            session.add(
                Param(
                    param_key=key,
                    name=name,
                    group_name=group,
                    value_type=value_type,
                    value=value,
                    default_value=value,
                    min_value=lo,
                    max_value=hi,
                    is_builtin=1,
                    tenant_id=1,
                )
            )
    session.flush()


def _roles(session, menus):
    all_codes = list(menus)
    for ident, key, name, scope in ROLES:
        row = session.get(Role, ident)
        if row is None:
            row = Role(
                id=ident,
                role_key=key,
                name=name,
                source="MANUAL",
                status="ENABLED",
                data_scope=scope,
                is_standard=1,
                tenant_id=1,
            )
            session.add(row)
            session.flush()
        linked = set(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id == ident)))
        codes = _codes_for(key, all_codes)
        for code in codes:
            menu = menus[code]
            if menu.id not in linked:
                session.add(RoleMenu(role_id=ident, menu_id=menu.id, tenant_id=1))
    session.flush()


def _codes_for(key: str, all_codes: list[str]) -> list[str]:
    if key == "R1":
        return list(all_codes)
    if key == "R9":
        return [code for code in all_codes if code.endswith(":query") and "plain" not in code]
    if key == "R3":
        return [code for code in all_codes if "plain" in code or code.endswith(":query") or code.startswith("ims:system:")]
    if key in {"R5", "R7", "R10"}:
        return [code for code in all_codes if code.endswith(":query")]
    return [code for code in all_codes if code.startswith("ims:system:")]


def _users(session):
    password = hash_password("Abc12345")
    if session.get(User, 1) is None:
        session.add(User(id=1, username="admin", nickname="超级管理员", password_hash=password, status="ACTIVE", tenant_id=1, source="LOCAL"))
        session.flush()
        session.add(UserRole(user_id=1, role_id=101, source="MANUAL", tenant_id=1))
    if session.get(User, 8) is None:
        session.add(User(id=8, username="data-migration", nickname="数据迁移", password_hash=password, status="ACTIVE", tenant_id=1, source="LOCAL"))
    session.flush()


def _tenant_dept(session):
    from app.domains.system.model import Dept

    if session.get(Dept, 10) is None:
        init_tenant(1, root_id=10, pending_id=15)


def _e2e_roles(session):
    if session.scalar(select(Role).where(Role.role_key == "e2e_admin")) is None:
        session.add(Role(role_key="e2e_admin", name="测试-管理员", source="MANUAL", status="ENABLED", data_scope="ALL", is_standard=0, tenant_id=1))
