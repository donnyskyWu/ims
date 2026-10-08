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


def test_query_tool_template_page_and_run():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/analysis/query-tool/template/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    )
    body = listed.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 4

    created = client.post(
        "/admin-api/ims/analysis/query-tool/template",
        headers=auth,
        json={"name": "W9 QT 草稿", "mode": "DRILL", "desc": "test"},
    )
    assert created.json()["code"] == 0
    code = created.json()["data"]["templateCode"]

    published = client.post(f"/admin-api/ims/analysis/query-tool/template/{code}/publish", headers=auth)
    assert published.json()["code"] == 0

    run = client.post(
        "/admin-api/ims/analysis/query-tool/run",
        headers=auth,
        json={"mode": "DRILL", "templateCode": code},
    )
    assert run.json()["code"] == 0
    assert run.json()["data"]["queryMode"] == "SYNC"
    assert len(run.json()["data"]["rows"]) >= 1
