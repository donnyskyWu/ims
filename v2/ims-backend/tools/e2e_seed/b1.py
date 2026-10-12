"""B1 测试环境造数。导入本模块不会执行；生产环境调用会被拒绝。"""
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
    """写入 02 用例账号与岗位规则。已存在的账号不覆盖密码。"""
    session_scope, system_context, use_context = _session()
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.domains.auth.model import PositionRoleRule, PositionRuleRole, PositionRuleVersion, UserMapping
    from app.domains.system.model import Dept, DictData, Role, User, UserDept, UserRole

    password = hash_password("Test1234")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            dept = session.scalar(select(Dept).where(Dept.name == "信息部")) or session.scalar(select(Dept).limit(1))
            admin_key = "R" + "1"
            role = session.scalar(select(Role).where(Role.role_key == admin_key)) or session.scalar(select(Role).limit(1))
            if dept is None or role is None:
                raise RuntimeError("请先执行基础种子")
            accounts = [
                ("test_admin", "测试管理员", "ACTIVE", 0),
                ("test_xz", "测试行政", "ACTIVE", 0),
                ("test_yyzj", "测试运营总监", "ACTIVE", 0),
                ("test_yg", "测试员工", "ACTIVE", 0),
                ("test_scope", "测试范围", "ACTIVE", 0),
                ("test_norole", "测试无角色", "ACTIVE", 0),
                ("test_lock", "测试锁定", "ACTIVE", 0),
                ("test_frozen", "测试冻结", "FROZEN", 0),
                ("test_resigned", "测试离职", "RESIGNED", 0),
                ("test_reset", "测试改密", "ACTIVE", 1),
            ]
            for username, nickname, status, reset in accounts:
                found = session.scalar(select(User).where(User.username == username))
                if found is not None:
                    continue
                user = User(
                    username=username,
                    nickname=nickname,
                    password_hash=password,
                    status=status,
                    source="LOCAL",
                    main_dept_id=dept.id,
                    pwd_reset_required=reset,
                    tenant_id=1,
                )
                session.add(user)
                session.flush()
                session.add(UserDept(user_id=user.id, dept_id=dept.id, is_main=1, source="LOCAL", tenant_id=1))
                if username != "test_norole":
                    session.add(UserRole(user_id=user.id, role_id=role.id, source="MANUAL", tenant_id=1))
            for code, label in (("LIVE_OP", "直播运营"), ("ASSIST", "主播助理"), ("CONTROL", "场控"), ("LOCAL_A", "本地岗位甲")):
                row = session.scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == code))
                if row is None:
                    session.add(
                        DictData(
                            dict_type="dict_position",
                            dict_value=code,
                            dict_label=label,
                            status="ENABLED",
                            source="LOCAL" if code == "LOCAL_A" else "DINGTALK",
                            tenant_id=1,
                        )
                    )
            session.flush()
            if session.scalar(select(PositionRoleRule).where(PositionRoleRule.rule_name == "直播运营规则")) is None and role is not None:
                rule = PositionRoleRule(
                    position_code="LIVE_OP",
                    role_id=role.id,
                    version=1,
                    status="ENABLED",
                    archived=0,
                    rule_name="直播运营规则",
                    active_slot="LIVE_OP",
                    tenant_id=1,
                )
                session.add(rule)
                session.flush()
                session.add(PositionRuleRole(rule_id=rule.id, role_id=role.id, role_type="MAIN", tenant_id=1))
                session.add(
                    PositionRuleVersion(
                        rule_id=rule.id,
                        version=1,
                        rule_name=rule.rule_name,
                        main_role_id=role.id,
                        extra_role_ids=[],
                        status="ENABLED",
                        change_type="CREATE",
                        operator_id=0,
                        tenant_id=1,
                    )
                )
            _ = UserMapping


def reset_user(name: str) -> None:
    session_scope, system_context, use_context = _session()
    from sqlalchemy import select

    from app.domains.auth.model import UserMapping
    from app.domains.system.model import User

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            user = session.scalar(select(User).where(User.nickname == name))
            if user is None:
                return
            mapping = session.scalar(select(UserMapping).where(UserMapping.user_id == user.id))
            if mapping is not None:
                session.delete(mapping)
            user.deleted = user.id


def advance_revoke() -> None:
    session_scope, system_context, use_context = _session()
    from datetime import timedelta

    from sqlalchemy import select

    from app.core.clock import now_naive
    from app.domains.system.model import UserRole

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            for row in session.scalars(select(UserRole).where(UserRole.revoke_at.is_not(None))):
                row.revoke_at = now_naive() - timedelta(minutes=1)


def _insert_event(status: str, event_id: str, delay: int | None = None) -> None:
    session_scope, system_context, use_context = _session()
    from app.core.clock import now_naive
    from app.domains.auth.model import OrgSyncEvent

    current = now_naive()
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(
                OrgSyncEvent(
                    event_id=event_id,
                    event_type="user_modify",
                    biz_type="USER_UPDATE",
                    status=status,
                    subject_name=event_id,
                    event_time=current,
                    processed_time=current,
                    delay_seconds=delay,
                    tenant_id=1,
                )
            )


def fail_event() -> None:
    _insert_event("RETRYING", "e2e-retry")


def dead_event() -> None:
    _insert_event("DEAD", "e2e-dead")


def delay_events() -> None:
    _insert_event("SUCCESS", "e2e-delay", delay=360)


def fail_batch() -> None:
    session_scope, system_context, use_context = _session()
    from app.core.clock import now_naive
    from app.domains.auth.model import OrgSyncBatch

    current = now_naive()
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            for index in (1, 2):
                session.add(
                    OrgSyncBatch(
                        started_at=current,
                        finished_at=current,
                        status="FAILED",
                        error_code=5003,
                        trigger_type="MANUAL",
                        fail_reason="钉钉服务超时，请稍后再试",
                        tenant_id=1,
                    )
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B1 测试造数")
    parser.add_argument("command", choices=["seed", "reset-user", "advance-revoke", "fail-event", "dead-event", "delay-events", "fail-batch"])
    parser.add_argument("name", nargs="?")
    args = parser.parse_args(argv)
    if args.command == "seed":
        seed()
    elif args.command == "reset-user":
        if not args.name:
            raise SystemExit("请提供姓名")
        reset_user(args.name)
    elif args.command == "advance-revoke":
        advance_revoke()
    elif args.command == "fail-event":
        fail_event()
    elif args.command == "dead-event":
        dead_event()
    elif args.command == "delay-events":
        delay_events()
    else:
        fail_batch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
