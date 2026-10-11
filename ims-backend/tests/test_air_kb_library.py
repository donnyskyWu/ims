import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_kb_create_tree_category_and_confidential_audit():
    auth = headers()
    users = client.get(
        "/admin-api/ims/system/user/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5, "username": "admin"},
    )
    assert users.json()["code"] == 0
    owner_id = int(users.json()["data"]["list"][0]["id"])

    empty = client.post("/admin-api/ims/air/kb", headers=auth, json={})
    assert empty.json()["code"] == 1001

    created = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC知识库单测", "secretLevel": "INTERNAL", "ownerUserId": owner_id},
    )
    assert created.json()["code"] == 0
    kb = created.json()["data"]
    assert kb["status"] == "PUBLISHED"
    assert kb["provider"] == "LOCAL"
    assert kb["kbNo"].startswith("KB-")

    secret = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC机密库单测", "secretLevel": "CONFIDENTIAL", "ownerUserId": owner_id},
    )
    assert secret.json()["code"] == 0
    secret_id = secret.json()["data"]["id"]
    assert secret.json()["data"]["status"] == "PENDING"
    assert secret.json()["data"]["grantsLimit"] == "仅 R1/R3/R4 可授权"

    denied = client.post(
        "/admin-api/ims/air/kb/audit",
        headers=auth,
        json={"kbId": secret_id, "approve": False},
    )
    assert denied.json()["code"] == 1001

    approved = client.post(
        "/admin-api/ims/air/kb/audit",
        headers=auth,
        json={"kbId": secret_id, "approve": True, "auditNote": "同意入库"},
    )
    assert approved.json()["code"] == 0
    assert approved.json()["data"]["status"] == "PUBLISHED"

    cat = client.post(
        "/admin-api/ims/air/kb/category",
        headers=auth,
        json={"kbId": kb["id"], "categoryName": "TC分类单测"},
    )
    assert cat.json()["code"] == 0
    cate_id = cat.json()["data"]["categoryId"]

    renamed = client.put(
        f"/admin-api/ims/air/kb/category/{cate_id}",
        headers=auth,
        json={"kbId": kb["id"], "categoryName": "TC分类改名"},
    )
    assert renamed.json()["code"] == 0

    tree = client.get("/admin-api/ims/air/kb/tree", headers=auth)
    assert tree.json()["code"] == 0
    node = next(item for item in tree.json()["data"] if item["id"] == kb["id"])
    assert node["secretLevel"] == "INTERNAL"
    names = [child["categoryName"] for child in node["children"]]
    assert "TC分类改名" in names

    removed = client.delete(
        f"/admin-api/ims/air/kb/category/{cate_id}",
        headers=auth,
        params={"kbId": kb["id"]},
    )
    assert removed.json()["code"] == 0


def test_kb_confidential_grant_blocks_plain_user():
    auth = headers()
    users = client.get(
        "/admin-api/ims/system/user/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5, "username": "admin"},
    )
    owner_id = int(users.json()["data"]["list"][0]["id"])
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": "kb_plain_c065", "nickname": "普通授权对象", "mobile": "13900006501", "password": "Pass@123"},
    )
    if created.json()["code"] != 0:
        listed = client.get(
            "/admin-api/ims/system/user/page",
            headers=auth,
            params={"pageNo": 1, "pageSize": 5, "username": "kb_plain_c065"},
        )
        plain_id = int(listed.json()["data"]["list"][0]["id"])
    else:
        plain_id = int(created.json()["data"]["id"])

    secret = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC机密授权单测", "secretLevel": "CONFIDENTIAL", "ownerUserId": owner_id},
    )
    kb_id = secret.json()["data"]["id"]
    client.post("/admin-api/ims/air/kb/audit", headers=auth, json={"kbId": kb_id, "approve": True})
    blocked = client.post(
        "/admin-api/ims/air/kb/grant",
        headers=auth,
        json={"kbId": kb_id, "grantType": "PERSON", "grantId": plain_id},
    )
    assert blocked.json()["code"] == 1001
    assert "仅 R1/R3/R4" in blocked.json()["msg"]

    allowed = client.post(
        "/admin-api/ims/air/kb/grant",
        headers=auth,
        json={"kbId": kb_id, "grantType": "PERSON", "grantId": owner_id, "expireAt": "2027-03-31"},
    )
    assert allowed.json()["code"] == 0
