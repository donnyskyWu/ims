"""B3 测试环境造数。导入本模块不会执行；生产环境调用会被拒绝。"""
from __future__ import annotations

import argparse
import os
from datetime import timedelta

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
    """给工作台用例准备七类待办、逾期、已读未读和跨用户隔离数据。"""
    session_scope, system_context, use_context = _session()
    from sqlalchemy import select

    from app.core.clock import now_naive
    from app.core.security import hash_password
    from app.domains.system.model import Dept, Role
    from app.domains.todo.service import cancel, complete, todo_create
    from tools.e2e_seed.b2 import _dept, _role, _user

    password = hash_password("Test1234")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            root = session.get(Dept, 10)
            if root is None:
                root = session.scalar(select(Dept).where(Dept.parent_id == 0))
            if root is None:
                raise RuntimeError("请先执行基础种子")
            market1 = _dept(session, root, "市场一部")
            market2 = _dept(session, root, "市场二部")
            live = _role(session, "e2e_live", "测试-直播运营", "DEPT", ["ims:system:user:query"])
            _grant(session, live, "ims:workbench:query")
            r1 = session.scalar(select(Role).where(Role.role_key == "R1"))
            r10 = session.scalar(select(Role).where(Role.role_key == "R10"))
            if r1 is None or r10 is None:
                raise RuntimeError("请先执行基础种子")
            _grant(session, r10, "ims:workbench:query")
            accounts = {
                "test_admin": _user(session, "test_admin", "测试管理员", "ACTIVE", r1, [market1], market1, password),
                "test_yg": _user(session, "test_yg", "测试员工", "ACTIVE", live, [market1], market1, password),
                "test_r10": _user(session, "test_r10", "测试外协", "ACTIVE", r10, [market1], market1, password),
                "test_empty": _user(session, "test_empty", "测试空数据", "ACTIVE", live, [market2], market2, password),
                "test_peer": _user(session, "test_peer", "测试同事", "ACTIVE", live, [market1], market1, password),
                "test_resigned": _user(session, "test_resigned", "测试离职", "RESIGNED", live, [market1], market1, password),
            }
            session.flush()
            current = now_naive()
            yg = accounts["test_yg"].id
            specs = [
                ("ACCT_APPLY", 93001, "APPROVAL", "领用审批样例", "请处理账号领用", "/ims/account/apply", "account", current + timedelta(days=2)),
                ("ACCT_RETURN", 93002, "RETURN", "账号归还样例", "请归还账号", "/ims/account/return", "account", current + timedelta(days=3)),
                ("CONTENT_REVIEW", 93003, "REVIEW", "内容审核样例", "请审核内容", "/ims/content/review", "content", current + timedelta(days=1)),
                ("WORK_TASK_CONFIRM", 93004, "CONFIRM", "任务确认样例", "请确认任务", "/ims/content/task", "content", current + timedelta(days=4)),
                ("CERT_EXPIRE", 93005, "WARNING", "证件到期样例", "证件已经逾期", "/ims/cert/expire", "cert", current - timedelta(days=2)),
                ("LIVE_ALARM", 93006, "ALERT", "直播告警样例", "直播出现告警", "/ims/live/alarm", "live", current + timedelta(days=1)),
                ("LEARN_TASK", 93007, "LEARN", "学习任务样例", "请完成学习", "/ims/train/learn", "train", current + timedelta(days=5)),
            ]
            for source_type, source_id, kind, title, summary, route, module, due in specs:
                todo_create(source_type, source_id, kind, title, user_ids=[yg], summary=summary, route=route, due_time=due, source_module=module)
            done = todo_create("ACCT_APPLY", 93008, "APPROVAL", "已处理样例", user_ids=[yg], summary="已经处理", route="/ims/account/apply", source_module="account")
            if done["status"] == "PENDING":
                complete(done["id"], yg)
            stopped = todo_create("CONTENT_REVIEW", 93009, "REVIEW", "已作废样例", user_ids=[yg], summary="已经作废", source_module="content")
            if stopped["status"] == "PENDING":
                cancel(stopped["id"], yg)
            todo_create("ACCT_APPLY", 93010, "APPROVAL", "外协指派审批", user_ids=[accounts["test_r10"].id], summary="只指派给外协", route="/ims/account/apply", source_module="account")
            todo_create("ACCT_APPLY", 93011, "APPROVAL", "[PEER]同事待办", user_ids=[accounts["test_peer"].id], summary="同事自己的待办", source_module="account")
            _message(session, yg, "审批结果通知", "您的领用申请已通过", route="/ims/account/apply", source_module="account", msg_type="TODO", read=False)
            _message(session, yg, "系统通知", "这是一条没有来源的系统通知", route=None, source_module="system", msg_type="SYSTEM", read=False)
            _message(session, yg, "未读提醒丙", "第三条未读消息", route=None, source_module="system", msg_type="SYSTEM", read=False)
            _message(session, yg, "已读通知甲", "已经读过的消息", route=None, source_module="system", msg_type="SYSTEM", read=True)
            _message(session, yg, "已读通知乙", "另一条已读消息", route=None, source_module="system", msg_type="SYSTEM", read=True)
            _message(session, accounts["test_peer"].id, "[PEER]同事消息", "同事自己的消息", route=None, source_module="system", msg_type="SYSTEM", read=False)


def _grant(session, role, perm: str) -> None:
    from sqlalchemy import select

    from app.domains.system.model import Menu, RoleMenu

    if role is None:
        return
    menu = session.scalar(select(Menu).where(Menu.perm_code == perm))
    if menu is None:
        return
    exists = session.scalar(select(RoleMenu).where(RoleMenu.role_id == role.id, RoleMenu.menu_id == menu.id))
    if exists is None:
        session.add(RoleMenu(role_id=role.id, menu_id=menu.id, tenant_id=1))


def _message(session, user_id: int, title: str, content: str, *, route: str | None, source_module: str, msg_type: str, read: bool) -> None:
    from sqlalchemy import select

    from app.core.clock import now_naive
    from app.domains.message.model import Message
    from app.domains.message.service import send_notify

    found = session.scalar(select(Message).where(Message.receiver_id == user_id, Message.title == title))
    if found is None:
        sent = send_notify(user_id, title, content, "工作台样例", f"b3-{user_id}-{title}", route=route, source_module=source_module, msg_type=msg_type)
        if sent.get("messageId"):
            found = session.get(Message, sent["messageId"])
    if found is not None and read and found.read_status != "READ":
        found.read_status = "READ"
        found.read_time = now_naive()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B3 测试造数")
    parser.add_argument("command", choices=["seed"])
    parser.parse_args(argv)
    seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
