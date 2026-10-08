import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app, init_db
from app.core import Base, engine
from app.ops_db import OpsBase, ops_engine

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_content_save_enqueues_outbox_when_football_unconfigured():
    auth = headers()
    create = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "方案同步测试", "body": "正文", "matchType": 1, "matchScheme": []},
    )
    assert create.json()["code"] == 0
    cid = create.json()["data"]["id"]
    assert create.json()["data"]["fbSyncStatus"] == "COMPENSATING"

    status = client.get(f"/admin-api/ims/content/{cid}/fb-sync", headers=auth)
    assert status.json()["code"] == 0
    assert status.json()["data"]["pendingOutboxCount"] >= 1

    outbox = client.get("/admin-api/ims/content/fb-sync/outbox/page", headers=auth)
    assert outbox.json()["code"] == 0
    assert outbox.json()["data"]["total"] >= 1


def test_content_fb_sync_success_with_stub(monkeypatch):
    monkeypatch.setenv("IMS_FOOTBALL_ARTICLE_STUB", "success")
    auth = headers()
    create = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "Football 成功", "body": "x", "matchScheme": []},
    )
    assert create.json()["code"] == 0
    cid = create.json()["data"]["id"]
    assert create.json()["data"]["fbSyncStatus"] == "SYNCED"
    assert create.json()["data"]["authorArticleId"]

    retry = client.post(f"/admin-api/ims/content/{cid}/fb-sync", headers=auth)
    assert retry.json()["code"] == 0


def test_delete_drafts_shelf_off_outbox(monkeypatch):
    monkeypatch.setenv("IMS_FOOTBALL_ARTICLE_STUB", "success")
    auth = headers()
    create = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "待删草稿", "body": "y", "matchScheme": []},
    )
    cid = create.json()["data"]["id"]
    assert create.json()["data"]["authorArticleId"]

    deleted = client.delete(f"/admin-api/ims/content/{cid}", headers=auth)
    assert deleted.json()["code"] == 0

    outbox = client.get(
        "/admin-api/ims/content/fb-sync/outbox/page",
        headers=auth,
        params={"syncStatus": "SUCCESS"},
    )
    actions = [row["action"] for row in outbox.json()["data"]["list"]]
    assert "SHELF_OFF" in actions
