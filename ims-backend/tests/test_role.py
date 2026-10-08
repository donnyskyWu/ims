import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import Base, SessionLocal, engine
from app.main import app, init_db
from app.models import UserRole


client = TestClient(app)


def login() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def leaves(headers: dict) -> list[dict]:
    tree = client.get("/admin-api/ims/system/menu/tree", headers=headers).json()["data"]

    def walk(nodes):
        for node in nodes:
            if node.get("permCode"):
                yield node
            yield from walk(node.get("children") or [])

    return list(walk(tree))


def bind(user_id: int, role_id: int) -> None:
    db = SessionLocal()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, tenant_id=0))
        db.commit()
    finally:
        db.close()


def test_role_menu_scope_position_and_union():
    headers = login()
    menu_rows = leaves(headers)
    ops = next(row for row in menu_rows if str(row["permCode"]).startswith("ops:"))
    other = next(row for row in menu_rows if row["id"] != ops["id"])
    created = client.post("/admin-api/ims/system/role/from-position", headers=headers, json={"dingtalkPosition": "直播运营"})
    assert created.json()["code"] == 0
    role_id = created.json()["data"]["roleId"]
    assert created.json()["data"]["status"] == "PENDING_CONFIG"
    assert created.json()["data"]["menuIds"] == []
    saved = client.put(
        f"/admin-api/ims/system/role/{role_id}/menus",
        headers=headers,
        json={"menuIds": [ops["id"], other["id"]]},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["status"] == "ENABLED"
    detail = client.put(
        f"/admin-api/ims/system/role/{role_id}/perm-detail",
        headers=headers,
        json={"permDetail": {ops["permCode"]: "R", other["permCode"]: "RWD"}},
    )
    assert detail.json()["code"] == 0
    scope = client.put(
        f"/admin-api/ims/system/role/{role_id}/data-scope",
        headers=headers,
        json={"dataScope": "DEPT"},
    )
    assert scope.json()["data"]["dataScope"] == "DEPT"
    child = client.put(
        f"/admin-api/ims/system/role/{role_id}/data-scope",
        headers=headers,
        json={"dataScope": "DEPT_AND_CHILD"},
    )
    assert child.json()["code"] == 1008
    missing = client.put(
        f"/admin-api/ims/system/role/{role_id}/perm-detail",
        headers=headers,
        json={"permDetail": {"nope:missing": "R"}},
    )
    assert missing.json()["code"] == 1212
    pos = client.put(
        f"/admin-api/ims/system/role/{role_id}/dingtalk-position",
        headers=headers,
        json={"dingtalkPosition": "直播运营"},
    )
    assert pos.json()["code"] == 0
    second = client.post("/admin-api/ims/system/role/from-position", headers=headers, json={"dingtalkPosition": "编导"})
    second_id = second.json()["data"]["roleId"]
    client.put(
        f"/admin-api/ims/system/role/{second_id}/menus",
        headers=headers,
        json={"menuIds": [other["id"]]},
    )
    clash = client.put(
        f"/admin-api/ims/system/role/{second_id}/dingtalk-position",
        headers=headers,
        json={"dingtalkPosition": "直播运营"},
    )
    assert clash.json()["code"] == 1001
    bob = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": "carol", "nickname": "卡罗", "mobile": "13700002222", "password": "Pass@123"},
    )
    user_id = int(bob.json()["data"]["id"])
    bind(user_id, role_id)
    bind(user_id, second_id)
    preview = client.post(f"/admin-api/ims/system/role/{role_id}/preview", headers=headers, json={"userId": str(user_id)})
    codes = set(preview.json()["data"]["userPermCodes"])
    assert ops["permCode"] in codes
    assert other["permCode"] in codes
    listed = client.get("/admin-api/ims/system/role/list", headers=headers).json()["data"]
    row = next(item for item in listed if item["id"] == role_id)
    assert row["source"] == "DINGTALK_AUTO"
    assert row["dataScope"] == "DEPT"


def test_from_position_is_idempotent_and_pending_grants_nothing():
    headers = login()
    first = client.post("/admin-api/ims/system/role/from-position", headers=headers, json={"dingtalkPosition": "主播达人"})
    body = first.json()["data"]
    assert body["created"] is True
    assert body["status"] == "PENDING_CONFIG"
    assert body["todoId"]
    again = client.post("/admin-api/ims/system/role/from-position", headers=headers, json={"dingtalkPosition": "主播达人"})
    assert again.json()["data"]["created"] is False
    assert again.json()["data"]["roleId"] == body["roleId"]
    assert again.json()["data"]["status"] == "PENDING_CONFIG"
    bob = client.post(
        "/admin-api/ims/system/user",
        headers=headers,
        json={"username": "dave", "nickname": "戴夫", "mobile": "13600003333", "password": "Pass@123"},
    )
    user_id = int(bob.json()["data"]["id"])
    bind(user_id, body["roleId"])
    preview = client.post(
        f"/admin-api/ims/system/role/{body['roleId']}/preview",
        headers=headers,
        json={"userId": user_id},
    )
    assert preview.json()["data"]["userPermCodes"] == []
    assert preview.json()["data"]["pendingIgnored"] is True


def test_missing_role_and_position_preview_route():
    headers = login()
    missing = client.put("/admin-api/ims/system/role/99999/data-scope", headers=headers, json={"dataScope": "SELF"})
    assert missing.json()["code"] == 1504
    assert missing.json()["msg"] == "资源不可用"
    gone = client.post("/admin-api/ims/auth/position/preview", headers=headers, json={"userId": 1})
    assert gone.status_code == 404
