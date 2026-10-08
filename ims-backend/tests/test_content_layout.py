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


def test_content_layout_create_publish_list():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content/layout-template",
        headers=auth,
        json={"templateName": "赛事快讯双栏", "previewHtml": "<div>demo</div>"},
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "DRAFT"
    tpl_id = body["data"]["id"]

    pub = client.post(f"/admin-api/ims/content/layout-template/{tpl_id}/publish", headers=auth)
    assert pub.json()["code"] == 0
    assert pub.json()["data"]["status"] == "ENABLED"

    listed = client.get(
        "/admin-api/ims/content/layout-template/list",
        headers=auth,
        params={"templateName": "赛事", "status": "ENABLED", "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert any(row["id"] == tpl_id for row in listed.json()["data"]["list"])
