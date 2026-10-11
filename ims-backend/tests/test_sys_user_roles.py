import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app, init_db
from app.models import Role, UserRole

client = TestClient(app)


def login(username: str = "admin", password: str = "Admin@123") -> str:
    return client.post("/admin-api/ims/auth/login", json={"username": username, "password": password}).json()["data"][
        "accessToken"
    ]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_user_page_and_detail_expose_roles_and_depts():
    token = login()
    headers = auth(token)
    roles = client.get("/admin-api/ims/system/role/list", headers=headers).json()["data"]
    admin_role = next(row for row in roles if row["roleKey"] == "sys:admin")
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={
            "username": "role-user",
            "nickname": "角色测试",
            "mobile": "13700003333",
            "password": "Pass@123",
            "roleIds": [admin_role["id"]],
            "deptIds": [11],
        },
    )
    body = created.json()
    assert body["code"] == 0
    user_id = int(body["data"]["id"])
    assert admin_role["id"] in body["data"]["roleIds"]
    assert body["data"]["roleNames"]
    assert body["data"]["deptIds"] == [11]

    page = client.get("/admin-api/ims/system/user/page", headers=headers, params={"username": "role-user"}).json()
    row = page["data"]["list"][0]
    assert row["mobile"] == "137****3333"
    assert admin_role["roleName"] in row["roleNames"]

    detail = client.get(f"/admin-api/ims/system/user/{user_id}", headers=headers).json()
    assert detail["code"] == 0
    assert detail["data"]["mobile"] == "13700003333"
    assert detail["data"]["roleIds"] == [admin_role["id"]]


def test_user_role_replace_respects_tenant():
    token = login()
    headers = auth(token)
    created = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": "role-swap", "nickname": "换角色", "mobile": "13700004444", "password": "Pass@123"},
    )
    user_id = int(created.json()["data"]["id"])
    roles = client.get("/admin-api/ims/system/role/list", headers=headers).json()["data"]
    swap_role = next(row for row in roles if row["roleKey"] != "sys:admin")

    updated = client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=headers,
        json={"roleIds": [swap_role["id"]]},
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"]["roleIds"] == [swap_role["id"]]

    db = SessionLocal()
    try:
        links = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id)).all())
        assert links == [swap_role["id"]]
        ghost = Role(
            role_name="跨租户",
            role_key="ghost:tenant9",
            data_scope="SELF",
            status="ENABLED",
            source="MANUAL",
            tenant_id=9,
        )
        db.add(ghost)
        db.commit()
        db.refresh(ghost)
        ghost_id = ghost.id
    finally:
        db.close()

    denied = client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=headers,
        json={"roleIds": [ghost_id]},
    )
    assert denied.json()["code"] == 1504

    missing = client.get("/admin-api/ims/system/user/999999", headers=headers)
    assert missing.json()["code"] == 1504
