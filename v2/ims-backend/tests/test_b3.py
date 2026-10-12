"""B3 个人工作台：聚合、待办关闭、消息已读与路由冒烟。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.clock import freeze, now_naive
from app.core.context import system_context, use_context
from app.core.security import hash_password
from app.db.session import session_scope
from app.domains.message.service import send_notify
from app.domains.system.model import DictData, User, UserDept, UserRole
from app.domains.todo.model import Todo
from app.domains.todo.service import todo_create
from tests.conftest import auth, login
from tests.stddata import D1, PASSWORD, U_ADMIN, U_DEPT

API = "/admin-api/ims"
U_R10 = 1201


def _label(session, dict_type: str, value: str) -> str:
    row = session.scalar(select(DictData).where(DictData.dict_type == dict_type, DictData.dict_value == value))
    assert row is not None, value
    return row.dict_label


def _names(nodes: list[dict]) -> list[str]:
    found: list[str] = []
    for node in nodes:
        found.append(node["name"])
        found.extend(_names(node.get("children") or []))
    return found


def _todo(source_id: int, kind: str, title: str, *, user_id: int = U_ADMIN, summary: str = "", route: str | None = None, due=None, source_type: str = "MANUAL") -> dict:
    with session_scope(commit=True):
        with use_context(system_context(1)):
            return todo_create(
                source_type,
                source_id,
                kind,
                title,
                user_ids=[user_id],
                summary=summary,
                route=route,
                due_time=due,
                source_module="account",
            )


def test_b3_routes_registered(client):
    found = set(client.app.openapi()["paths"])
    expected = [
        "/admin-api/ims/workbench/dashboard",
        "/admin-api/ims/todo/my/page",
        "/admin-api/ims/todo/my/count",
        "/admin-api/ims/todo/my/complete",
        "/admin-api/ims/todo/my/{ident}",
        "/admin-api/ims/message/my/page",
        "/admin-api/ims/message/my/unread-count",
        "/admin-api/ims/message/my/read",
        "/admin-api/ims/message/my/read-all",
        "/admin-api/ims/message/my/{ident}",
        "/admin-api/ims/message/unread-count",
        "/admin-api/ims/message/read",
        "/admin-api/ims/message/read-all",
        "/admin-api/ims/auth/workbench/todos",
        "/admin-api/ims/auth/workbench/messages",
        "/admin-api/ims/auth/workbench/messages/read-all",
        "/admin-api/ims/auth/workbench/messages/{ident}/read",
        "/admin-api/ims/auth/workbench/todos/{ident}",
    ]
    missing = [path for path in expected if path not in found]
    assert missing == []


def test_dashboard_greeting_cards_and_menu(client):
    freeze(datetime(2026, 10, 12, 9, 30))
    headers = auth(client, "u_admin")
    body = client.get(f"{API}/workbench/dashboard", headers=headers).json()
    assert body["code"] == 0, body
    data = body["data"]
    assert data["greeting"] == "早上好"
    assert data["displayName"] == "管理员"
    assert data["myAccountCount"] == 0
    assert data["myAssetCount"] == 0
    assert data["myCertCount"] == 0
    assert data["myCertWarningCount"] == 0
    assert data["myLiveSessionCount"] == 0
    assert data["bizCardsVisible"] is True
    assert set(data["todoCountByType"]) == set()
    me = client.get(f"{API}/auth/me", headers=headers).json()
    assert "工作台" in _names(me["data"]["menus"])
    foreign = client.get(f"{API}/auth/me", headers=auth(client, "t2_admin")).json()
    assert [node["name"] for node in foreign["data"]["menus"]] == ["系统管理", "工作流"]
    with session_scope() as session:
        assert _label(session, "dict_todo_status", "DONE") == "已处理"
        assert _label(session, "dict_todo_type", "LEARN") == "学习"
        assert _label(session, "dict_todo_type", "ALERT") == "告警"
        assert _label(session, "dict_todo_type", "CONFIRM") == "确认"


def test_r10_hides_business_cards(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(
                User(
                    id=U_R10,
                    username="u_r10",
                    nickname="外协",
                    password_hash=hash_password(PASSWORD),
                    status="ACTIVE",
                    tenant_id=1,
                    main_dept_id=D1,
                    source="LOCAL",
                )
            )
            session.flush()
            session.add(UserRole(user_id=U_R10, role_id=110, source="MANUAL", tenant_id=1))
            session.add(UserDept(user_id=U_R10, dept_id=D1, is_main=1, source="LOCAL", tenant_id=1))
    body = client.get(f"{API}/workbench/dashboard", headers=auth(client, "u_r10")).json()
    assert body["code"] == 0, body
    assert body["data"]["bizCardsVisible"] is False
    assert body["data"]["displayName"] == "外协"


def test_todo_filter_sort_and_close(client):
    headers = auth(client, "u_admin")
    current = now_naive()
    late = _todo(9401, "WARNING", "逾期预警", summary="已经过期", due=current - timedelta(days=2))
    soon = _todo(9402, "LEARN", "学习未到期", summary="还早", due=current + timedelta(days=3))
    _todo(9403, "ALERT", "告警一条", summary="告警摘要")
    _todo(9404, "APPROVAL", "标题甲", summary="摘要乙")
    page = client.get(f"{API}/todo/my/page", headers=headers, params={"status": "PENDING", "pageSize": 20}).json()
    assert page["code"] == 0, page
    titles = [item["title"] for item in page["data"]["list"]]
    assert titles[0] == "逾期预警"
    assert "逾期" in page["data"]["list"][0]["deadlineText"]
    assert page["data"]["list"][0]["overdue"] is True
    learned = client.get(f"{API}/todo/my/page", headers=headers, params={"type": "LEARN", "status": "PENDING"}).json()
    assert [item["title"] for item in learned["data"]["list"]] == ["学习未到期"]
    alarm = client.get(f"{API}/todo/my/page", headers=headers, params={"type": "ALARM", "status": "PENDING"}).json()
    assert [item["title"] for item in alarm["data"]["list"]] == ["告警一条"]
    found = client.get(f"{API}/todo/my/page", headers=headers, params={"keyword": "摘要乙", "status": "PENDING"}).json()
    assert [item["title"] for item in found["data"]["list"]] == ["标题甲"]
    expired = client.get(f"{API}/todo/my/page", headers=headers, params={"status": "OVERDUE"}).json()
    expired_titles = [item["title"] for item in expired["data"]["list"]]
    assert "逾期预警" in expired_titles
    assert "学习未到期" not in expired_titles
    closed = client.post(f"{API}/todo/my/complete", headers=headers, json={"id": str(late["id"]), "remark": "手工关闭"}).json()
    assert closed["code"] == 0, closed
    assert closed["data"]["status"] == "DONE"
    again = client.post(f"{API}/todo/my/complete", headers=headers, json={"id": str(late["id"])}).json()
    assert again["code"] == 1296, again
    with session_scope() as session:
        row = session.get(Todo, int(late["id"]))
        assert row.close_remark == "手工关闭"
        assert row.status == "DONE"
    denied = client.post(f"{API}/todo/my/complete", headers=auth(client, "u_dept"), json={"id": str(soon["id"])}).json()
    assert denied["code"] == 1504, denied
    long_remark = client.post(f"{API}/todo/my/complete", headers=headers, json={"id": str(soon["id"]), "remark": "字" * 201}).json()
    assert long_remark["code"] == 1001


def test_open_placeholder_and_missing_document(client):
    headers = auth(client, "u_admin")
    live = _todo(9410, "APPROVAL", "占位待办", route="/ims/account/apply", source_type="ACCT_APPLY")
    opened = client.get(f"{API}/todo/my/{live['id']}", headers=headers, params={"intent": "open"}).json()
    assert opened["code"] == 0, opened
    assert opened["data"]["jump"]["state"] == "placeholder"
    assert opened["data"]["status"] == "PENDING"
    gone = _todo(9411, "APPROVAL", "单据没了", source_type="DOC_GONE")
    missing = client.get(f"{API}/todo/my/{gone['id']}", headers=headers, params={"intent": "open"}).json()
    assert missing["code"] == 1297, missing
    with session_scope() as session:
        assert session.get(Todo, int(gone["id"])).status == "PENDING"
    done = client.post(f"{API}/todo/my/complete", headers=headers, json={"id": str(gone["id"])}).json()
    assert done["code"] == 0, done
    assert done["data"]["status"] == "DONE"


def test_message_read_and_alias(client):
    headers = auth(client, "u_admin")
    with session_scope(commit=True):
        with use_context(system_context(1)):
            first = send_notify(U_ADMIN, "未读甲", "正文甲", "工作台", "b3-a", route="/ims/account/apply", source_module="account", msg_type="TODO")
            second = send_notify(U_ADMIN, "未读乙", "含关键词的正文", "工作台", "b3-b", source_module="system", msg_type="SYSTEM")
            peer = send_notify(U_DEPT, "同事消息", "别人的", "工作台", "b3-c", source_module="system")
    read_one = client.post(f"{API}/message/read", headers=headers, json={"ids": [str(first["messageId"])]}).json()
    assert read_one["code"] == 0, read_one
    assert read_one["data"]["readStatus"] == "READ"
    again = client.post(f"{API}/message/my/read", headers=headers, json={"ids": [str(first["messageId"])]}).json()
    assert again["code"] == 0, again
    assert again["data"]["readStatus"] == "READ"
    page = client.get(f"{API}/message/my/page", headers=headers, params={"readStatus": "ALL", "pageSize": 20}).json()
    assert page["data"]["list"][0]["title"] == "未读乙"
    keyword = client.get(f"{API}/message/my/page", headers=headers, params={"keyword": "关键词"}).json()
    assert [item["title"] for item in keyword["data"]["list"]] == ["未读乙"]
    unread = client.get(f"{API}/message/my/unread-count", headers=headers).json()
    assert unread["data"]["count"] >= 1
    cleared = client.post(f"{API}/message/read-all", headers=headers).json()
    assert cleared["code"] == 0, cleared
    assert cleared["data"]["count"] >= 1
    left = client.get(f"{API}/message/unread-count", headers=headers).json()
    assert left["data"]["count"] == 0
    hidden = client.get(f"{API}/message/my/{peer['messageId']}", headers=headers).json()
    assert hidden["code"] == 1504, hidden
    alias = client.get(f"{API}/auth/workbench/todos", headers=headers, params={"status": "PENDING"}).json()
    assert alias["code"] == 0, alias
    alias_msg = client.get(f"{API}/auth/workbench/messages", headers=headers).json()
    assert alias_msg["code"] == 0, alias_msg


def test_resigned_cannot_login(client):
    body = login(client, "u_resigned").json()
    assert body["code"] == 1216, body


def test_seed_refuses_production():
    import tools.e2e_seed.b3 as seed

    with pytest.raises(RuntimeError, match="生产环境拒绝执行造数"):
        seed.assert_allowed("prod")
    seed.assert_allowed("test")
    seed.assert_allowed("e2e")


def test_seed_sample_accounts(client):
    import tools.e2e_seed.b3 as seed

    seed.seed()
    yg = login(client, "test_yg", "Test1234").json()
    assert yg["code"] == 0, yg
    token = {"Authorization": f"Bearer {yg['data']['accessToken']}"}
    counted = client.get(f"{API}/todo/my/count", headers=token).json()
    assert counted["data"]["total"] >= 7
    page = client.get(f"{API}/todo/my/page", headers=token, params={"status": "ALL", "pageSize": 50}).json()
    titles = [item["title"] for item in page["data"]["list"]]
    assert not any(title.startswith("[PEER]") for title in titles)
    assert "已处理样例" in titles
    unread = client.get(f"{API}/message/unread-count", headers=token).json()
    assert unread["data"]["count"] >= 3
    resigned = login(client, "test_resigned", "Test1234").json()
    assert resigned["code"] == 1216, resigned
    r10 = login(client, "test_r10", "Test1234").json()
    assert r10["code"] == 0, r10
    r10_headers = {"Authorization": f"Bearer {r10['data']['accessToken']}"}
    mine = client.get(f"{API}/todo/my/page", headers=r10_headers, params={"status": "PENDING"}).json()
    assert [item["title"] for item in mine["data"]["list"]] == ["外协指派审批"]
    board = client.get(f"{API}/workbench/dashboard", headers=r10_headers).json()
    assert board["data"]["bizCardsVisible"] is False
