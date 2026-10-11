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
    names = [item["name"] for item in cats.json()["data"]["categories"]]
    assert "运营" in names
    assert "未分类" in names


def test_bi_report_publish_version_starts_at_one():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "版本报表", "reportType": "REPORT", "category": "内容"},
    )
    rid = created.json()["data"]["id"]
    assert created.json()["data"]["version"] == 1
    first = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert first.json()["code"] == 0
    assert first.json()["data"]["status"] == "PUBLISHED"
    assert first.json()["data"]["version"] == 1
    second = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert second.json()["data"]["version"] == 2


def test_bi_report_create_requires_scope_and_note():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={
            "reportName": "口径报表",
            "reportType": "REPORT",
            "category": "运营",
            "subCategory": "日报",
            "shareScope": "PRIVATE",
            "metricNote": "GMV 为支付金额",
        },
    )
    assert created.json()["code"] == 0
    data = created.json()["data"]
    assert data["status"] == "DRAFT"
    assert data["shareScope"] == "PRIVATE"
    assert data["metricNote"] == "GMV 为支付金额"
    assert data["category"] == "运营"
    assert data["subCategory"] == "日报"
    assert data["version"] == 1


def test_bi_report_category_import_and_filters():
    auth = headers()
    empty = client.post("/admin-api/ims/bi/report/category", headers=auth, json={"action": "add", "name": "  ", "parentId": 0})
    assert empty.json()["code"] == 1001

    added = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC分类", "parentId": 0},
    )
    assert added.json()["code"] == 0
    parent = next(item for item in added.json()["data"]["categories"] if item["name"] == "TC分类")
    child = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC子类", "parentId": parent["id"]},
    )
    assert child.json()["code"] == 0
    child_row = next(
        item
        for cat in child.json()["data"]["categories"]
        if cat["name"] == "TC分类"
        for item in cat["children"]
        if item["name"] == "TC子类"
    )
    grandchild = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC三级", "parentId": child_row["id"]},
    )
    assert grandchild.json()["code"] == 1001

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "分类下报表", "reportType": "REPORT", "category": "TC分类", "subCategory": "TC子类"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]

    listed = client.get(
        "/admin-api/ims/bi/report/list",
        headers=auth,
        params={"subCategory": "TC子类", "shareScope": "PRIVATE", "status": "DRAFT"},
    )
    assert any(row["id"] == rid for row in listed.json()["data"]["list"])

    removed = client.post("/admin-api/ims/bi/report/category", headers=auth, json={"action": "delete", "id": parent["id"]})
    assert removed.json()["code"] == 0
    assert all(item["name"] != "TC分类" for item in removed.json()["data"]["categories"])
    moved = client.get("/admin-api/ims/bi/report/list", headers=auth, params={"keyword": "分类下报表"})
    hit = next(row for row in moved.json()["data"]["list"] if row["id"] == rid)
    assert hit["category"] == "未分类"

    bad = client.post("/admin-api/ims/bi/report/import", headers=auth, json={"template": {"reportName": ""}})
    assert bad.json()["code"] == 1001
    imported = client.post(
        "/admin-api/ims/bi/report/import",
        headers=auth,
        json={
            "template": {
                "reportName": "导入日报",
                "comps": [{"id": "c1", "type": "KPI", "title": "GMV", "dataset": "MISSING_DS"}],
            }
        },
    )
    body = imported.json()
    assert body["code"] == 0
    assert body["data"]["formatOk"] is True
    assert body["data"]["componentCount"] == 1
    assert body["data"]["warnings"]
