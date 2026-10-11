import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import Role, RoleMenu, RolePerm, UserRole
from app.scope import refresh_user_scope


client = TestClient(app)


def login(username="admin", password="Admin@123") -> dict:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0, res.json()
    return {"Authorization": f"Bearer {res.json()['data']['accessToken']}"}


def create_user(headers: dict, username: str, mobile: str) -> int:
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": username, "nickname": username, "mobile": mobile, "password": "Pass@123"},
    )
    assert created.json()["code"] == 0, created.json()
    return int(created.json()["data"]["id"])


def grant(user_id: int, key: str, code: str, level: str, scope: str = "ALL") -> None:
    db = SessionLocal()
    try:
        role = Role(role_name=key, role_key=key, data_scope=scope, status="ENABLED", source="MANUAL")
        db.add(role)
        db.flush()
        menu_id = 11 if code == "system:user:query" else 12
        db.add(RoleMenu(role_id=role.id, menu_id=menu_id, perm_code=code, tenant_id=0))
        db.add(RolePerm(role_id=role.id, module_code="system", perm_code=code, perm_level=level, tenant_id=0))
        db.add(UserRole(user_id=user_id, role_id=role.id, tenant_id=0))
        db.commit()
        refresh_user_scope(db, user_id)
        db.commit()
    finally:
        db.close()


def test_no_role_is_403_and_workbench_stays_open():
    headers = login()
    user_id = create_user(headers, "norole", "13622220001")
    token = login("norole", "Pass@123")
    denied = client.get("/admin-api/ims/system/user/page", headers=token)
    assert denied.status_code == 403
    assert denied.json()["code"] == 403
    assert denied.json()["msg"] == "无操作权限"
    live = client.get("/admin-api/ims/ip-group/list", headers=token)
    assert live.status_code == 403
    assert live.json()["code"] == 403
    board = client.get("/admin-api/ims/auth/workbench/dashboard", headers=token)
    assert board.status_code == 200
    assert board.json()["code"] == 0
    access = client.get("/admin-api/ims/auth/access", headers=token).json()["data"]
    assert access["admin"] is False
    assert access["fullCatalog"] is False
    assert access["permCodes"] == []
    assert access["routes"] == ["/ims/workbench", "/ims/workbench/messages", "/ims/workbench/todos"]
    assert user_id


def test_multi_role_union_and_write_level():
    headers = login()
    user_id = create_user(headers, "union", "13622220002")
    grant(user_id, "perm-user-r", "system:user:query", "R")
    grant(user_id, "perm-role-w", "system:role:query", "RWD")
    token = login("union", "Pass@123")
    access = client.get("/admin-api/ims/auth/access", headers=token).json()["data"]
    assert access["admin"] is False
    assert access["fullCatalog"] is False
    assert set(access["permCodes"]) == {"system:user:query", "system:role:query"}
    assert access["permLevels"]["system:user:query"] == "R"
    assert access["permLevels"]["system:role:query"] == "RWD"
    assert "/ims/system/user" in access["routes"]
    assert "/ims/system/role" in access["routes"]
    assert "/ims/live/sessions" not in access["routes"]
    users = client.get("/admin-api/ims/system/user/page", headers=token)
    assert users.json()["code"] == 0
    roles = client.get("/admin-api/ims/system/role/list", headers=token)
    assert roles.json()["code"] == 0
    blocked_write = client.post(
        "/admin-api/ims/system/user",
        headers=token,
        json={"username": "nope", "nickname": "不能建", "mobile": "13622220099", "password": "Pass@123"},
    )
    assert blocked_write.status_code == 403
    assert blocked_write.json()["code"] == 403
    menu = client.get("/admin-api/ims/system/menu/tree", headers=token)
    assert menu.status_code == 403
    assert menu.json()["code"] == 403
    made = client.post(
        "/admin-api/ims/system/role",
        headers=token,
        json={"roleName": "并集新建", "roleKey": "union_made", "dataScope": "SELF"},
    )
    assert made.json()["code"] == 0, made.json()
    assert made.json()["data"]["roleKey"] == "union_made"
    admin = login()
    admin_access = client.get("/admin-api/ims/auth/access", headers=admin).json()["data"]
    assert admin_access["admin"] is True
    assert admin_access["fullCatalog"] is True
    assert client.get("/admin-api/ims/system/menu/tree", headers=admin).json()["code"] == 0


def test_reader_cannot_open_unrelated_system_api():
    headers = login()
    user_id = create_user(headers, "onlyuser", "13622220003")
    grant(user_id, "perm-only-user", "system:user:query", "R")
    token = login("onlyuser", "Pass@123")
    denied = client.get("/admin-api/ims/system/role/list", headers=token)
    assert denied.status_code == 403
    assert denied.json()["code"] == 403
    assert denied.json()["msg"] == "无操作权限"
