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


def _owner_and_kb(auth: dict) -> tuple[int, int]:
    users = client.get(
        "/admin-api/ims/system/user/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5, "username": "admin"},
    )
    owner_id = int(users.json()["data"]["list"][0]["id"])
    created = client.post(
        "/admin-api/ims/air/kb",
        headers=auth,
        json={"kbName": "TC上传库单测", "secretLevel": "INTERNAL", "ownerUserId": owner_id},
    )
    assert created.json()["code"] == 0
    return owner_id, int(created.json()["data"]["id"])


def test_kb_upload_empty_and_modes():
    auth = headers()
    _, kb_id = _owner_and_kb(auth)

    empty = client.post("/admin-api/ims/air/kb/doc/upload", headers=auth, json={})
    assert empty.status_code == 200
    assert empty.json()["code"] == 1001
    assert "网络" not in (empty.json().get("msg") or "")

    bad_ext = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={"kbId": kb_id, "fileName": "notes.exe"},
    )
    assert bad_ext.json()["code"] == 1001

    before = client.get("/admin-api/ims/air/kb/tree", headers=auth).json()["data"]
    before_count = next(item["docCount"] for item in before if item["id"] == kb_id)

    uploaded = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={"kbId": kb_id, "fileName": "手册.pdf", "fileSize": 12, "contentType": "application/pdf"},
    )
    assert uploaded.json()["code"] == 0
    assert uploaded.json()["data"]["auditStatus"] == ["PENDING"]

    missing_text = client.post(
        "/admin-api/ims/air/kb/doc/import-text",
        headers=auth,
        json={"kbId": kb_id, "title": "只有标题"},
    )
    assert missing_text.json()["code"] == 1001

    text = client.post(
        "/admin-api/ims/air/kb/doc/import-text",
        headers=auth,
        json={"kbId": kb_id, "title": "粘贴笔记", "content": "正文"},
    )
    assert text.json()["code"] == 0
    assert text.json()["data"]["auditStatus"] == ["PENDING"]

    bad_url = client.post(
        "/admin-api/ims/air/kb/doc/import-url",
        headers=auth,
        json={"kbId": kb_id, "urls": ["ftp://example.com/a"]},
    )
    assert bad_url.json()["code"] == 1001

    empty_url = client.post("/admin-api/ims/air/kb/doc/import-url", headers=auth, json={"kbId": kb_id, "urls": []})
    assert empty_url.json()["code"] == 1001

    url = client.post(
        "/admin-api/ims/air/kb/doc/import-url",
        headers=auth,
        json={"kbId": kb_id, "urls": ["https://example.com/doc"]},
    )
    assert url.json()["code"] == 0

    low = client.post(
        "/admin-api/ims/air/kb/doc/upload",
        headers=auth,
        json={"kbId": kb_id, "fileName": "公开.txt", "secretLevel": "PUBLIC"},
    )
    assert low.json()["code"] == 1001
    assert "密级" in low.json()["msg"]

    after = client.get("/admin-api/ims/air/kb/tree", headers=auth).json()["data"]
    after_count = next(item["docCount"] for item in after if item["id"] == kb_id)
    assert after_count == before_count + 3
