"""B2 测试环境造数。导入本模块不会执行；生产环境调用会被拒绝。"""
from __future__ import annotations

import argparse
import os

ALLOWED = {"test", "e2e"}


def assert_allowed(env: str | None = None) -> None:
    name = (env if env is not None else os.environ.get("IMS_ENV") or "").strip().lower()
    if not name:
        from app.core.config import get_settings

        name = str(getattr(get_settings(), "env", "") or "").lower()
    if name not in ALLOWED:
        raise RuntimeError("生产环境拒绝执行造数")


def _session():
    assert_allowed()
    from app.core.context import system_context, use_context
    from app.db.session import session_scope
    from app.main import create_app

    create_app()
    return session_scope, system_context, use_context


def seed() -> None:
    """补齐 B2 用例部门、角色、账号、样例日志。已有账号不覆盖密码。"""
    session_scope, system_context, use_context = _session()
    from sqlalchemy import select

    from app.core.clock import now_naive
    from app.core.security import hash_password
    from app.domains.message.model import NotifyRecord
    from app.domains.system.model import Dept, LoginLog, OperateLog, Role, TenantPackage, User

    password = hash_password("Test1234")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            root = session.get(Dept, 10) or session.scalar(select(Dept).where(Dept.parent_id == 0))
            if root is None:
                raise RuntimeError("请先执行基础种子")
            market1 = _dept(session, root, "市场一部")
            market2 = _dept(session, root, "市场二部")
            admin_dept = _dept(session, root, "行政部")
            _dept(session, root, "本地小组", source="LOCAL")
            _dept(session, root, "待分配", source="SYSTEM")
            _dept(session, root, "孤儿组", source="LOCAL", local_orphan=1)
            live = _role(session, "e2e_live", "测试-直播运营", "DEPT", ["ims:system:user:query"])
            scope = _role(session, "e2e_scope", "测试-本部门用户管理", "DEPT", ["ims:system:user:query", "ims:system:user:update"])
            _role(session, "e2e_review", "测试-内容一级审核", "DEPT", ["ims:system:user:query"])
            r1 = session.scalar(select(Role).where(Role.role_key == "R1"))
            r2 = session.scalar(select(Role).where(Role.role_key == "R2"))
            accounts = [
                ("test_admin", "测试管理员", "ACTIVE", r1, [market1], market1, password),
                ("test_xz", "测试行政", "ACTIVE", r2, [admin_dept], admin_dept, password),
                ("test_yg", "测试员工", "ACTIVE", live, [market1], market1, password),
                ("test_scope", "测试范围", "ACTIVE", scope, [market1], market1, password),
                ("test_norole", "测试无角色", "ACTIVE", None, [market1], market1, password),
                ("test_ding", "测试钉钉", "ACTIVE", None, [market1], market1, None),
                ("test_frozen", "测试冻结", "FROZEN", r1, [market1], market1, password),
                ("test_resigned", "测试离职", "RESIGNED", r1, [market1], market1, password),
                ("test_multi", "测试兼任", "ACTIVE", live, [market1, market2], market1, password),
            ]
            for username, nickname, status, role, depts, main, secret in accounts:
                _user(session, username, nickname, status, role, depts, main, secret)
            if session.scalar(select(TenantPackage).where(TenantPackage.name == "标准套餐")) is None:
                session.add(TenantPackage(name="标准套餐", status="ENABLED", remark="本期已交付菜单", tenant_id=1))
            current = now_naive()
            if session.scalar(select(OperateLog).where(OperateLog.action == "B2样例")) is None:
                session.add(OperateLog(operator_name="测试管理员", module="用户", action="B2样例", success=1, path="/admin-api/ims/system/user", method="POST", params_digest="{}", tenant_id=1, creator=0, create_time=current))
            if session.scalar(select(LoginLog).where(LoginLog.username == "test_admin", LoginLog.result == "SUCCESS")) is None:
                session.add(LoginLog(username="test_admin", login_type="PASSWORD", result="SUCCESS", channel="PASSWORD", ip="127.0.0.1", tenant_id=1, creator=0, create_time=current))
            if session.scalar(select(NotifyRecord).where(NotifyRecord.biz_key == "b2-seed-failed")) is None:
                admin = session.scalar(select(User).where(User.username == "test_admin"))
                session.add(NotifyRecord(event_type="业务通知", biz_key="b2-seed-failed", receiver_id=admin.id, channel="SITE", status="FAILED", title="样例失败通知", tenant_id=1, creator=0))
                session.add(NotifyRecord(event_type="业务通知", biz_key="b2-seed-sent", receiver_id=admin.id, channel="SITE", status="SENT", title="样例成功通知", tenant_id=1, creator=0))


def _dept(session, parent, name: str, source: str = "LOCAL", local_orphan: int = 0):
    from sqlalchemy import select

    from app.domains.system.model import Dept

    found = session.scalar(select(Dept).where(Dept.name == name, Dept.tenant_id == 1))
    if found is not None:
        return found
    row = Dept(parent_id=parent.id, name=name, path=parent.path, source=source, status="ENABLED", local_orphan=local_orphan, tenant_id=1)
    session.add(row)
    session.flush()
    row.path = f"{parent.path}{row.id}/"
    return row


def _role(session, key: str, name: str, scope: str, perms: list[str]):
    from sqlalchemy import select

    from app.domains.system.model import Menu, Role, RoleMenu

    found = session.scalar(select(Role).where(Role.role_key == key))
    if found is not None:
        return found
    row = Role(role_key=key, name=name, source="MANUAL", status="ENABLED", data_scope=scope, tenant_id=1)
    session.add(row)
    session.flush()
    menus = list(session.scalars(select(Menu).where(Menu.perm_code.in_(perms))))
    for menu in menus:
        session.add(RoleMenu(role_id=row.id, menu_id=menu.id, tenant_id=1))
    return row


def _user(session, username, nickname, status, role, depts, main, secret):
    from sqlalchemy import select

    from app.domains.system.model import User, UserDept, UserRole

    found = session.scalar(select(User).where(User.username == username))
    if found is not None:
        return found
    user = User(username=username, nickname=nickname, password_hash=secret, status=status, source="LOCAL", main_dept_id=main.id if main else None, tenant_id=1)
    session.add(user)
    session.flush()
    for dept in depts:
        session.add(UserDept(user_id=user.id, dept_id=dept.id, is_main=1 if main and dept.id == main.id else 0, source="LOCAL", tenant_id=1))
    if role is not None:
        session.add(UserRole(user_id=user.id, role_id=role.id, source="MANUAL", tenant_id=1))
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B2 测试造数")
    parser.add_argument("command", choices=["seed"])
    parser.parse_args(argv)
    seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
