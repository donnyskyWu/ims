import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import Base, SessionLocal, engine
from app.main import app, init_db
from app.models import PositionRule, RolePerm, User, UserRole


client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def admin_role_id(token: str) -> int:
    rows = client.get("/admin-api/ims/system/role/list", headers=auth(token)).json()["data"]
    for row in rows:
        if row["status"] == "ENABLED":
            return row["id"]
    raise AssertionError("no enabled role")


def test_rule_version_does_not_change_applied_users():
    token = login()
    headers = auth(token)
    role_id = admin_role_id(token)
    created = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "直播运营岗供给", "dingtalkPosition": "直播运营", "grantRoleIds": [role_id]},
    )
    assert created.json()["code"] == 0
    body = created.json()["data"]
    assert body["version"] == 1
    rule_id = body["id"]
    again = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "重复", "dingtalkPosition": "直播运营", "grantRoleIds": [role_id]},
    )
    assert again.json()["code"] == 1001

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "admin"))
        before = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id == user.id))
        rule = db.get(PositionRule, rule_id)
        rule.applied_user_count = 1
        db.commit()
        user_id = user.id
    finally:
        db.close()

    edited = client.put(
        f"/admin-api/ims/auth/position/rule/{rule_id}",
        headers=headers,
        json={"ruleName": "直播运营岗供给", "dingtalkPosition": "直播运营", "description": "新版本", "grantRoleIds": [role_id]},
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["version"] == 2
    assert edited.json()["data"]["appliedUserCount"] == 0
    db = SessionLocal()
    try:
        old = db.get(PositionRule, rule_id)
        assert old.status == "DISABLED"
        assert old.applied_user_count == 1
        after = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id == user_id))
        assert after == before
        blocked = old.id
    finally:
        db.close()

    denied = client.delete(f"/admin-api/ims/auth/position/rule/{blocked}", headers=headers, params={"confirmText": "DELETE"})
    assert denied.json()["code"] == 1001
    db = SessionLocal()
    try:
        row = db.get(PositionRule, blocked)
        row.applied_user_count = 0
        db.commit()
        new_id = edited.json()["data"]["id"]
    finally:
        db.close()
    removed = client.delete(f"/admin-api/ims/auth/position/rule/{blocked}", headers=headers, params={"confirmText": "DELETE"})
    assert removed.json()["code"] == 0
    listed = client.get("/admin-api/ims/auth/position/rules", headers=headers).json()["data"]["list"]
    assert any(item["id"] == new_id and item["version"] == 2 for item in listed)
    assert all(item["id"] != blocked for item in listed)


def test_pending_role_is_rejected_and_auto_create_is_idempotent():
    token = login()
    headers = auth(token)
    pending = client.post("/admin-api/ims/system/role/from-position", headers=headers, json={"dingtalkPosition": "场控"})
    assert pending.json()["data"]["status"] == "PENDING_CONFIG"
    pending_id = pending.json()["data"]["roleId"]
    rejected = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "场控供给", "dingtalkPosition": "场控", "grantRoleIds": [pending_id]},
    )
    assert rejected.json()["code"] == 1002

    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": "r4user", "nickname": "只读", "mobile": "13600003333", "password": "Pass@123"},
    )
    assert created.json()["code"] == 0
    r4 = login("r4user", "Pass@123")
    forbidden = client.post(
        "/admin-api/ims/auth/position/role-auto-create",
        headers=auth(r4),
        json={"dingtalkPosition": "场控"},
    )
    assert forbidden.status_code == 403

    first = client.post("/admin-api/ims/auth/position/role-auto-create", headers=headers, json={"dingtalkPosition": "场控"})
    assert first.json()["code"] == 0
    assert first.json()["data"]["created"] is False
    assert first.json()["data"]["roleId"] == pending_id
    assert first.json()["data"]["status"] == "PENDING_CONFIG"
    second = client.post("/admin-api/ims/auth/position/role-auto-create", headers=headers, json={"dingtalkPosition": "新岗位甲"})
    assert second.json()["data"]["created"] is True
    assert second.json()["data"]["source"] == "DINGTALK_AUTO"
    assert second.json()["data"]["status"] == "PENDING_CONFIG"
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(RolePerm).where(RolePerm.role_id == second.json()["data"]["roleId"])) == 0
    finally:
        db.close()
    alias = client.get("/admin-api/ims/auth/position/templates", headers=headers)
    assert alias.json()["code"] == 0
