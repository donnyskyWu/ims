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


def test_bi_metric_create_preview_delete():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": "互动次数 W9", "metricType": "BASIC", "category": "内容表现"},
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]
    assert created.json()["data"]["metricCode"].startswith("M")

    preview = client.post(f"/admin-api/ims/bi/metric/{mid}/preview", headers=auth, json={})
    assert preview.json()["code"] == 0
    assert preview.json()["data"]["value"] > 0

    listed = client.get("/admin-api/ims/bi/metric/list", headers=auth, params={"keyword": "W9", "pageNo": 1, "pageSize": 5})
    assert listed.json()["code"] == 0
    assert any(r["id"] == mid for r in listed.json()["data"]["list"])

    analysis = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2026-09-01", "dateEnd": "2026-09-30", "view": "DETAIL"},
    )
    assert analysis.json()["code"] == 0
    assert analysis.json()["data"]["rows"][0]["metricId"] == mid

    deleted = client.delete(f"/admin-api/ims/bi/metric/{mid}", headers=auth)
    assert deleted.json()["code"] == 0
