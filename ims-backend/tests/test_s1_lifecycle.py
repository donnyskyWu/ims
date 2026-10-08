import json
import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.dingtalk_crypto import pack
from app.main import app
from app.models import PositionRule, Role, RolePerm, Todo, User, UserDept, UserRole
from app.org_sync import process_due

client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def post_event(payload: dict):
    body, headers = pack(json.dumps(payload, ensure_ascii=False), "1700000000000", "nonce-s1")
    return client.post("/admin-api/ims/auth/org/event", json=body, headers=headers)


def consume() -> None:
    db = SessionLocal()
    try:
        process_due(db)
        db.commit()
    finally:
        db.close()


def seed_rules() -> None:
    db = SessionLocal()
    try:
        anchor = Role(
            role_name="主播运营",
            role_key="e2e:anchor-ops",
            data_scope="ALL",
            status="ENABLED",
            source="MANUAL",
        )
        director = Role(
            role_name="编导",
            role_key="e2e:director-ops",
            data_scope="SELF",
            status="ENABLED",
            source="MANUAL",
        )
        db.add_all([anchor, director])
        db.flush()
        db.add(RolePerm(role_id=anchor.id, module_code="auth", perm_code="auth:workbench:query", perm_level="R"))
        db.add(RolePerm(role_id=director.id, module_code="auth", perm_code="content:plan:query", perm_level="R"))
        db.add(
            PositionRule(
                template_name="主播运营岗供给",
                dingtalk_position="主播运营",
                version=1,
                status="ENABLED",
                grant_role_ids=[anchor.id],
                applied_user_count=0,
                created_by=1,
            )
        )
        db.add(
            PositionRule(
                template_name="编导岗供给",
                dingtalk_position="编导",
                version=1,
                status="ENABLED",
                grant_role_ids=[director.id],
                applied_user_count=0,
                created_by=1,
            )
        )
        db.commit()
    finally:
        db.close()


def hire(event_id="evt-s1-hire", ding="dt-s1", mobile="13900007301", position="主播运营", dept=7301, dept_name="内容部"):
    return {
        "eventType": "hire",
        "dingtalkEventId": event_id,
        "unionId": "union-s1",
        "payloadJson": {
            "dingtalkUserId": ding,
            "nickname": "E2E主播小周",
            "mobile": mobile,
            "dingtalkPosition": position,
            "deptIds": [dept],
            "deptNames": [dept_name],
            "afterDept": dept_name,
        },
    }


def test_hire_grants_position_role_visible_on_org_users():
    seed_rules()
    assert post_event(hire()).json()["code"] == 0
    consume()
    token = login()
    page = client.get("/admin-api/ims/auth/org/users", headers=auth(token), params={"keyword": "E2E主播小周"})
    row = page.json()["data"]["list"][0]
    assert row["positionName"] == "主播运营"
    assert row["grantedRoleNames"] == ["主播运营"]
    assert "auth:workbench:query" in row["grantedPermCodes"]
    assert row["deptNames"] == ["内容部"]
    assert row["status"] == "ENABLED"
    assert row["permissionDiff"]["summary"] == "入职按岗位供给角色"
    assert row["permissionDiff"]["addedRoleNames"] == ["主播运营"]
    db = SessionLocal()
    try:
        rule = db.scalar(select(PositionRule).where(PositionRule.dingtalk_position == "主播运营", PositionRule.deleted == 0))
        assert rule.applied_user_count == 1
    finally:
        db.close()


def test_transfer_keeps_old_role_adds_new_and_dept_change_does_not():
    seed_rules()
    assert post_event(hire()).json()["code"] == 0
    consume()
    transfer = {
        "eventType": "transfer",
        "dingtalkEventId": "evt-s1-transfer",
        "unionId": "union-s1",
        "beforeDept": "内容部",
        "payloadJson": {
            "dingtalkUserId": "dt-s1",
            "dingtalkPosition": "编导",
            "deptIds": [7302],
            "deptNames": ["直播部"],
            "beforeDept": "内容部",
            "afterDept": "直播部",
        },
    }
    assert post_event(transfer).json()["code"] == 0
    consume()
    token = login()
    row = client.get(
        "/admin-api/ims/auth/org/users", headers=auth(token), params={"keyword": "dt-s1"}
    ).json()["data"]["list"][0]
    assert row["deptNames"] == ["直播部"]
    assert set(row["grantedRoleNames"]) == {"主播运营", "编导"}
    assert row["positionName"] == "编导"
    assert row["bufferUntil"]
    diff = row["permissionDiff"]
    assert diff["retainedRoleNames"] == ["主播运营"]
    assert diff["addedRoleNames"] == ["编导"]
    assert diff["removedRoleNames"] == []
    assert diff["beforeDept"] == "内容部"
    assert diff["afterDept"] == "直播部"
    assert "24 小时" in diff["summary"]

    other = hire(event_id="evt-s1-hire-b", ding="dt-s1b", mobile="13900007302", dept=3, dept_name="内容部")
    assert post_event(other).json()["code"] == 0
    consume()
    change = {
        "eventType": "dept_change",
        "dingtalkEventId": "evt-s1-dept",
        "unionId": "union-s1b",
        "beforeDept": "内容部",
        "payloadJson": {
            "dingtalkUserId": "dt-s1b",
            "deptIds": [9],
            "deptNames": ["投放部"],
            "beforeDept": "内容部",
            "afterDept": "投放部",
        },
    }
    assert post_event(change).json()["code"] == 0
    consume()
    changed = client.get(
        "/admin-api/ims/auth/org/users", headers=auth(token), params={"keyword": "dt-s1b"}
    ).json()["data"]["list"][0]
    assert changed["deptNames"] == ["投放部"]
    assert changed["grantedRoleNames"] == ["主播运营"]
    assert changed["permissionDiff"]["addedRoleNames"] == []
    assert changed["permissionDiff"]["summary"] == "部门变更，角色无增减"
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.dingtalk_user_id == "dt-s1b"))
        depts = list(db.scalars(select(UserDept.dept_id).where(UserDept.user_id == user.id)).all())
        assert depts == [9]
        roles = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
        assert len(roles) == 1
    finally:
        db.close()


def test_resign_freezes_login_and_opens_return_todo():
    seed_rules()
    assert post_event(hire()).json()["code"] == 0
    consume()
    token = login()
    user_id = client.get(
        "/admin-api/ims/auth/org/users", headers=auth(token), params={"keyword": "dt-s1"}
    ).json()["data"]["list"][0]["userId"]
    assert client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=auth(token),
        json={"password": "Pass@123"},
    ).json()["code"] == 0
    db = SessionLocal()
    try:
        username = db.scalar(select(User).where(User.dingtalk_user_id == "dt-s1")).username
    finally:
        db.close()
    assert client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Pass@123"}).json()["code"] == 0
    assert post_event(
        {
            "eventType": "resign",
            "dingtalkEventId": "evt-s1-resign",
            "unionId": "union-s1",
            "payloadJson": {"dingtalkUserId": "dt-s1"},
        }
    ).json()["code"] == 0
    consume()
    locked = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Pass@123"})
    assert locked.json()["code"] == 1006
    row = client.get(
        "/admin-api/ims/auth/org/users", headers=auth(token), params={"keyword": "dt-s1"}
    ).json()["data"]["list"][0]
    assert row["status"] == "FROZEN"
    assert row["deptNames"] == ["内容部"]
    assert row["positionName"] == "主播运营"
    db = SessionLocal()
    try:
        todo = db.scalar(select(Todo).where(Todo.ref_type == "org_resign", Todo.ref_id == user_id, Todo.status == "PENDING"))
        assert todo is not None
        assert todo.task_type == "return"
        assert "离职待归还" in todo.title
    finally:
        db.close()
