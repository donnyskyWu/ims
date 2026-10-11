import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import User
from app.ops_db import ops_session
from app.ops_models import IpGroup

client = TestClient(app)


def seed_ip_group(name: str) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").one()
        tenant_id = user.tenant_id
    finally:
        db.close()
    ops = ops_session()
    try:
        row = IpGroup(group_name=name, level="L1", status="ENABLED", tenant_id=tenant_id, deleted=0)
        ops.add(row)
        ops.commit()
        return name
    finally:
        ops.close()


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

    group_name = seed_ip_group(f"C044-{code}")
    run = client.post(
        "/admin-api/ims/analysis/query-tool/run",
        headers=auth,
        json={"mode": "DRILL", "templateCode": code},
    )
    body_run = run.json()
    assert body_run["code"] == 0
    assert body_run["data"]["queryMode"] == "SYNC"
    assert "未接 DW" not in str(body_run)
    assert any(row.get("group_name") == group_name for row in body_run["data"]["rows"])
    assert body_run["data"]["levelState"]["breadcrumbs"]

    draft = client.post(
        "/admin-api/ims/analysis/query-tool/run",
        headers=auth,
        json={
            "mode": "DRILL",
            "inlineTemplate": {
                "mode": "DRILL",
                "payloadJson": {"levels": [{"label": "IP组", "entityCode": "IP_GROUP"}]},
            },
        },
    )
    assert draft.json()["code"] == 0
    assert draft.json()["data"]["queryMode"] == "SYNC"
    assert draft.json()["data"]["templateCode"] is None


def test_query_tool_menu_seed_and_revoke():
    auth = headers()
    created = client.post(
        "/admin-api/ims/analysis/query-tool/template",
        headers=auth,
        json={"name": "侧栏模板", "mode": "DRILL", "desc": "menu"},
    )
    code = created.json()["data"]["templateCode"]
    blocked = client.post(
        "/admin-api/ims/analysis/query-tool/menu-seed",
        headers=auth,
        json={"templateCode": code, "menuTitle": "侧栏模板", "parentMenuCode": "ims:analysis:query-tool-group"},
    )
    assert blocked.json()["code"] == 1001
    client.post(f"/admin-api/ims/analysis/query-tool/template/{code}/publish", headers=auth)
    seeded = client.post(
        "/admin-api/ims/analysis/query-tool/menu-seed",
        headers=auth,
        json={"templateCode": code, "menuTitle": "周产出", "parentMenuCode": "ims:analysis:query-tool-group"},
    )
    assert seeded.json()["code"] == 0, seeded.json()
    assert seeded.json()["data"]["routePath"] == f"/ims/analysis/query-tool/run/{code}"
    detail = client.get(f"/admin-api/ims/analysis/query-tool/template/{code}", headers=auth)
    assert detail.json()["data"]["menuPathLabel"] == "已挂 L3 数据分析"
    assert detail.json()["data"]["menuSeed"] is True
    removed = client.delete(f"/admin-api/ims/analysis/query-tool/template/{code}", headers=auth)
    assert removed.json()["code"] == 1265
    revoked = client.delete(f"/admin-api/ims/analysis/query-tool/menu-seed/{code}", headers=auth)
    assert revoked.json()["code"] == 0
    assert revoked.json()["data"]["menuSeed"] is False


def test_query_tool_name_and_drill_depth():
    auth = headers()
    empty = client.post(
        "/admin-api/ims/analysis/query-tool/template",
        headers=auth,
        json={"name": "  ", "mode": "DRILL"},
    )
    assert empty.json()["code"] == 1001
    levels = [{"levelIndex": i, "label": f"L{i}", "entityCode": "IP_GROUP"} for i in range(6)]
    over = client.post(
        "/admin-api/ims/analysis/query-tool/template",
        headers=auth,
        json={"name": "层级过多", "mode": "DRILL", "payloadJson": {"levels": levels}},
    )
    assert over.json()["code"] == 1001
    assert "5" in over.json()["msg"]
