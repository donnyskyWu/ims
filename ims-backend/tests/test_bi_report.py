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
    data = preview.json()["data"]
    assert data["rows"]
    assert data["kpis"]
    assert data["trend"]
    assert "平台" in data["columns"]
    assert "metric" not in data["columns"]
    status = client.get("/admin-api/ims/bi/report/account-status", headers=auth).json()["data"]
    assert status["rows"]
    assert "状态" in status["columns"]
    assert "note" not in status["columns"]


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


def test_bi_category_tree_import_and_scope_filter():
    auth = headers()
    cats = client.get("/admin-api/ims/bi/report/categories", headers=auth).json()["data"]["categories"]
    names = {item["name"] for item in cats}
    assert {"运营", "内容", "财务", "未分类"} <= names
    ops = next(item for item in cats if item["name"] == "运营")
    assert {child["name"] for child in ops["children"]} == {"日报", "周报", "大屏"}

    blank = client.post("/admin-api/ims/bi/report/category", headers=auth, json={"action": "add", "name": "  "})
    assert blank.json()["code"] == 1001

    added = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC分类", "parentId": 0},
    )
    assert added.json()["code"] == 0
    parent_id = added.json()["data"]["id"]
    child = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC子类", "parentId": parent_id},
    )
    assert child.json()["code"] == 0
    too_deep = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "add", "name": "TC三级", "parentId": child.json()["data"]["id"]},
    )
    assert too_deep.json()["code"] == 1001
    assert "两级" in too_deep.json()["msg"]

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "分类迁移报表", "reportType": "REPORT", "category": "TC分类", "shareScope": "ALL"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]
    assert created.json()["data"]["shareScope"] == "ALL"
    noted = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={
            "reportName": "口径说明报表",
            "reportType": "REPORT",
            "category": "日报",
            "shareScope": "PRIVATE",
            "metricNote": "GMV 为支付金额",
        },
    )
    assert noted.json()["code"] == 0
    assert noted.json()["data"]["status"] == "DRAFT"
    assert noted.json()["data"]["metricNote"] == "GMV 为支付金额"
    assert noted.json()["data"]["shareScope"] == "PRIVATE"

    scoped = client.get(
        "/admin-api/ims/bi/report/list",
        headers=auth,
        params={"shareScope": "ALL", "status": "DRAFT", "category": "TC分类"},
    )
    assert any(item["id"] == rid for item in scoped.json()["data"]["list"])
    hidden = client.get("/admin-api/ims/bi/report/list", headers=auth, params={"shareScope": "PRIVATE", "keyword": "分类迁移报表"})
    assert all(item["id"] != rid for item in hidden.json()["data"]["list"])

    removed = client.post(
        "/admin-api/ims/bi/report/category",
        headers=auth,
        json={"action": "delete", "categoryId": parent_id},
    )
    assert removed.json()["code"] == 0
    assert "未分类" in removed.json()["data"]["message"]
    detail = client.get(f"/admin-api/ims/bi/report/{rid}", headers=auth)
    assert detail.json()["data"]["category"] == "未分类"

    bad = client.post("/admin-api/ims/bi/report/import", headers=auth, json={"template": {"comps": []}})
    assert bad.json()["code"] == 1001
    imported = client.post(
        "/admin-api/ims/bi/report/import",
        headers=auth,
        json={
            "template": {
                "reportName": "导入日报",
                "reportType": "REPORT",
                "category": "日报",
                "comps": [{"id": "c1", "type": "KPI", "title": "GMV", "dataset": "missing_ds"}],
            }
        },
    )
    assert imported.json()["code"] == 0
    assert imported.json()["data"]["compCount"] == 1
    assert imported.json()["data"]["warnings"]


def test_bi_publish_config_grants_tc_r6_and_card_actions():
    from app.bi_br212_seed import _clone_admin_perms
    from app.core import SessionLocal
    from app.models import Role, User, UserRole
    from app.scope import refresh_user_scope
    from app.security import hash_password

    auth = headers()
    db = SessionLocal()
    try:
        viewer = User(
            username="tc_r6",
            nickname="主播R6",
            mobile="13900003636",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(viewer)
        db.flush()
        role = Role(
            role_name="R6本域",
            role_key="bi:tc-r6",
            data_scope="SELF",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        _clone_admin_perms(db, role.id)
        db.add(UserRole(user_id=viewer.id, role_id=role.id, tenant_id=0))
        refresh_user_scope(db, viewer.id)
        db.commit()
        viewer_id = viewer.id
    finally:
        db.close()

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "可见日报", "reportType": "REPORT", "category": "日报"},
    )
    rid = created.json()["data"]["id"]
    bare = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert bare.json()["code"] == 0
    assert bare.json()["data"]["version"] == 1

    published = client.post(
        f"/admin-api/ims/bi/report/{rid}/publish",
        headers=auth,
        json={
            "dest": "CENTER",
            "shareScope": "SPECIFIED",
            "opPerm": "READONLY",
            "rowPerm": "INHERIT",
            "viewerIds": [viewer_id],
        },
    )
    body = published.json()
    assert body["code"] == 0
    assert body["data"]["version"] == 2
    assert body["data"]["shareScope"] == "SPECIFIED"
    assert body["data"]["opPerm"] == "READONLY"

    token = client.post("/admin-api/ims/auth/login", json={"username": "tc_r6", "password": "Admin@123"}).json()["data"]["accessToken"]
    viewer_headers = {"Authorization": f"Bearer {token}"}
    listed = client.get("/admin-api/ims/bi/report/list", headers=viewer_headers, params={"keyword": "可见日报"})
    assert any(item["reportName"] == "可见日报" for item in listed.json()["data"]["list"])
    hidden = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "私有草稿", "reportType": "REPORT", "category": "日报"},
    )
    private_id = hidden.json()["data"]["id"]
    missed = client.get("/admin-api/ims/bi/report/list", headers=viewer_headers, params={"keyword": "私有草稿"})
    assert all(item["id"] != private_id for item in missed.json()["data"]["list"])

    copied = client.post(f"/admin-api/ims/bi/report/{rid}/copy", headers=auth)
    assert copied.json()["code"] == 0
    assert copied.json()["data"]["reportName"].endswith("副本")
    assert copied.json()["data"]["version"] == 1
    assert copied.json()["data"]["status"] == "DRAFT"
    exported = client.get(f"/admin-api/ims/bi/report/{rid}/export", headers=auth)
    assert exported.json()["data"]["template"]["reportName"] == "可见日报"
    records = client.get(f"/admin-api/ims/bi/report/{rid}/publish/list", headers=auth)
    assert len(records.json()["data"]["list"]) >= 1
