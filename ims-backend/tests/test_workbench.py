import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.core import Base, SessionLocal, engine, utcnow
from app.main import app, init_db
from app.models import Todo, User, WorkMessage


client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_todos_are_personal_and_preview_caps_at_ten():
    token = login()
    headers = auth(token)
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": "other", "nickname": "别人", "mobile": "13600004444", "password": "Pass@123"},
    )
    other_id = int(created.json()["data"]["id"])
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").one()
        now = utcnow()
        db.add(
            Todo(
                assignee_user_id=other_id,
                task_type="review",
                title="别人的待办",
                status="PENDING",
                deadline=now + timedelta(days=1),
            )
        )
        db.add(
            Todo(
                assignee_user_id=admin.id,
                task_type="review",
                title="已逾期",
                status="PENDING",
                deadline=now - timedelta(hours=2),
            )
        )
        for index in range(11):
            db.add(
                Todo(
                    assignee_user_id=admin.id,
                    task_type="approval",
                    title=f"待办{index}",
                    status="PENDING",
                    deadline=now + timedelta(days=index + 1),
                )
            )
        db.commit()
        overdue_id = db.query(Todo).filter(Todo.title == "已逾期").one().id
    finally:
        db.close()

    anonymous = client.get("/admin-api/ims/auth/workbench/todos")
    assert anonymous.status_code == 401

    page = client.get("/admin-api/ims/auth/workbench/todos", headers=headers, params={"pageSize": 10}).json()
    assert page["code"] == 0
    # seed() 会给 admin 放一条 E2E-WB-CLOSE，计数在用例自造的 12 条之外。
    assert page["data"]["total"] == 13
    assert len(page["data"]["list"]) == 10
    assert page["data"]["list"][0]["title"] == "已逾期"
    assert page["data"]["list"][0]["overdue"] is True
    assert all(row["title"] != "别人的待办" for row in page["data"]["list"])

    closed = client.put(
        f"/admin-api/ims/auth/workbench/todos/{overdue_id}",
        headers=headers,
        json={"action": "CLOSE"},
    )
    assert closed.json()["code"] == 0
    other = login("other", "Pass@123")
    hidden = client.put(
        f"/admin-api/ims/auth/workbench/todos/{overdue_id}",
        headers=auth(other),
        json={"action": "DONE"},
    )
    assert hidden.json()["code"] == 1504
    board = client.get("/admin-api/ims/auth/workbench/dashboard", headers=headers).json()["data"]
    assert board["todoCount"] == 12
    assert board["unreadMessageCount"] == 1


def test_workbench_dashboard_includes_flow_todo_count():
    token = login()
    headers = auth(token)
    board = client.get("/admin-api/ims/auth/workbench/dashboard", headers=headers).json()
    assert board["code"] == 0
    data = board["data"]
    assert "flowTodoCount" in data
    assert isinstance(data["flowTodoCount"], int)
    assert data["flowTodoCount"] >= 1
    preview = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=headers,
        params={"pageNo": 1, "pageSize": 5},
    ).json()
    assert preview["code"] == 0
    assert preview["data"]["total"] == data["flowTodoCount"]


def test_workbench_e2e_seed_todo_and_message():
    token = login()
    headers = auth(token)
    board = client.get("/admin-api/ims/auth/workbench/dashboard", headers=headers).json()
    assert board["code"] == 0
    todos = client.get("/admin-api/ims/auth/workbench/todos", headers=headers, params={"pageSize": 50}).json()
    assert todos["code"] == 0
    assert any(row["title"] == "E2E-WB-CLOSE" and row["status"] == "PENDING" for row in todos["data"]["list"])
    messages = client.get("/admin-api/ims/auth/workbench/messages", headers=headers).json()
    assert messages["code"] == 0
    assert any(row["title"] == "E2E-WB-MSG" and row["read"] is False for row in messages["data"]["list"])


def test_message_read_is_idempotent():
    token = login()
    headers = auth(token)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").one()
        db.add(WorkMessage(user_id=admin.id, title="系统通知", content="请查看", channel="IN_APP"))
        db.add(WorkMessage(user_id=admin.id + 99, title="他人消息", content="不可见", channel="IN_APP"))
        db.commit()
        message_id = db.query(WorkMessage).filter(WorkMessage.title == "系统通知").one().id
    finally:
        db.close()
    first = client.put(f"/admin-api/ims/auth/workbench/messages/{message_id}/read", headers=headers)
    second = client.put(f"/admin-api/ims/auth/workbench/messages/{message_id}/read", headers=headers)
    assert first.status_code == 200 and first.json()["code"] == 0
    assert second.status_code == 200 and second.json()["code"] == 0
    listed = client.get("/admin-api/ims/auth/workbench/messages", headers=headers).json()["data"]
    mine = next(row for row in listed["list"] if row["title"] == "系统通知")
    assert listed["total"] == 2
    assert mine["read"] is True
    board = client.get("/admin-api/ims/auth/workbench/dashboard", headers=headers).json()["data"]
    assert board["unreadMessageCount"] == 1
