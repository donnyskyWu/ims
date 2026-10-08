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


def test_bi_report_catalog_and_preview():
    auth = headers()
    catalog = client.get("/admin-api/ims/bi/report/catalog", headers=auth)
    assert catalog.json()["code"] == 0
    reports = catalog.json()["data"]["reports"]
    assert len(reports) == 8

    preview = client.get("/admin-api/ims/bi/report/unified-account", headers=auth)
    assert preview.json()["code"] == 0
    assert preview.json()["data"]["rows"]


def test_bi_report_manage_create_list():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "W9 测试报表", "reportType": "DASHBOARD", "category": "内容分析"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]
    assert created.json()["data"]["reportType"] == "DASHBOARD"

    listed = client.get("/admin-api/ims/bi/report/list", headers=auth, params={"keyword": "W9", "pageNo": 1, "pageSize": 5})
    assert listed.json()["code"] == 0
    assert any(r["id"] == rid for r in listed.json()["data"]["list"])

    cats = client.get("/admin-api/ims/bi/report/categories", headers=auth)
    assert cats.json()["code"] == 0
    assert cats.json()["data"]["categories"]
