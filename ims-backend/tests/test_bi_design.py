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


def test_bi_design_datasets_save_publish():
    auth = headers()
    ds = client.get("/admin-api/ims/bi/report/datasets", headers=auth)
    assert ds.json()["code"] == 0
    assert ds.json()["data"]["compLib"]

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "W9 设计器", "reportType": "REPORT", "category": "内容分析"},
    )
    rid = created.json()["data"]["id"]

    layout = {
        "layoutMode": "FREE",
        "comps": [{"id": "c1", "type": "KPI", "title": "粉丝", "x": 40, "y": 40, "w": 240, "h": 120}],
    }
    saved = client.put(f"/admin-api/ims/bi/report/{rid}", headers=auth, json={"layoutJson": layout})
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["comps"][0]["title"] == "粉丝"

    preview = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "c1", "components": layout["comps"]},
    )
    assert preview.json()["code"] == 0

    pub = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert pub.json()["code"] == 0
    assert pub.json()["data"]["status"] == "PUBLISHED"
