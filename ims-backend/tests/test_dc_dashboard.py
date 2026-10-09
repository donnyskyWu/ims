import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import DcSyncTask, Role, RolePerm, UserRole
from app.scope import refresh_user_scope

client = TestClient(app)


def headers(username: str = "admin", password: str = "Admin@123") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login", json={"username": username, "password": password}
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def layout(widget_key: str = "gmv-card", widget_type: str = "METRIC_CARD", y: int = 0) -> dict:
    return {
        "widgetKey": widget_key,
        "widgetType": widget_type,
        "position": {"x": 0, "y": y, "w": 3, "h": 2},
        "config": {"metricKey": "totalGmv"},
    }


def test_dashboard_layout_create_update_and_list():
    auth = headers()
    empty = client.get("/admin-api/ims/dc/dashboard/list", headers=auth)
    assert empty.json()["code"] == 0
    assert empty.json()["data"] == []

    invalid = client.post(
        "/admin-api/ims/dc/dashboard",
        headers=auth,
        json={"dashboardName": "坏布局", "layoutConfig": [layout(widget_type="PIE")]},
    )
    assert invalid.json()["code"] == 1001

    created = client.post(
        "/admin-api/ims/dc/dashboard",
        headers=auth,
        json={
            "dashboardName": "经营总览",
            "refreshCron": "0 * * * *",
            "layoutConfig": [layout(), layout("health", "HEALTH_PANEL", 2)],
        },
    )
    body = created.json()
    assert body["code"] == 0
    dashboard_id = body["data"]["id"]
    assert body["data"]["dashboardName"] == "经营总览"

    listed = client.get("/admin-api/ims/dc/dashboard/list", headers=auth).json()["data"]
    assert listed[0]["id"] == dashboard_id
    assert listed[0]["status"] == "ENABLED"
    assert len(listed[0]["layoutConfig"]) == 2
    assert listed[0]["layoutConfig"][1]["widgetType"] == "HEALTH_PANEL"

    updated = client.put(
        f"/admin-api/ims/dc/dashboard/{dashboard_id}",
        headers=auth,
        json={
            "dashboardName": "经营总览-已保存",
            "layoutConfig": [layout("gmv-card", "METRIC_CARD", 1)],
        },
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"] is None
    again = client.get("/admin-api/ims/dc/dashboard/list", headers=auth).json()["data"]
    assert again[0]["dashboardName"] == "经营总览-已保存"
    assert again[0]["layoutConfig"][0]["position"]["y"] == 1

    missing = client.put(
        "/admin-api/ims/dc/dashboard/999999",
        headers=auth,
        json={"dashboardName": "不存在", "layoutConfig": []},
    )
    assert missing.json()["code"] == 1504


def test_dashboard_layout_requires_r1_or_r4():
    auth = headers()
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": "dcviewer", "nickname": "看板只读", "mobile": "13700002222", "password": "Pass@123"},
    )
    user_id = int(created.json()["data"]["id"])
    db = SessionLocal()
    try:
        role = Role(role_name="看板只读", role_key="dc-viewer", data_scope="SELF", status="ENABLED", source="MANUAL")
        db.add(role)
        db.flush()
        db.add(RolePerm(role_id=role.id, module_code="dc", perm_code="dc:dashboard:query", perm_level="R"))
        db.add(UserRole(user_id=user_id, role_id=role.id, tenant_id=0))
        db.commit()
        refresh_user_scope(db, user_id)
        db.commit()
    finally:
        db.close()
    viewer = headers("dcviewer", "Pass@123")
    listed = client.get("/admin-api/ims/dc/dashboard/list", headers=viewer)
    assert listed.json()["code"] == 0
    denied = client.post(
        "/admin-api/ims/dc/dashboard",
        headers=viewer,
        json={"dashboardName": "越权", "layoutConfig": []},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == 1008


def test_dashboard_freshness_and_delay_alarm():
    auth = headers()
    fresh = client.get("/admin-api/ims/dc/dashboard/freshness", headers=auth)
    data = fresh.json()["data"]
    assert fresh.json()["code"] == 0
    assert data["target"] == 60
    assert data["isAlarm"] is False
    assert data["businessToDwsDelayMinutes"] <= 60
    assert len(data["syncTaskStatus"]) == 3
    assert {row["status"] for row in data["syncTaskStatus"]} == {"SUCCESS"}
    assert data["dataAsOf"]

    db = SessionLocal()
    try:
        row = db.query(DcSyncTask).filter(DcSyncTask.task_name.contains("聚合层")).one()
        row.last_run_at = utcnow() - timedelta(minutes=90)
        row.status = "SUCCESS"
        db.commit()
    finally:
        db.close()
    delayed = client.get("/admin-api/ims/dc/dashboard/freshness", headers=auth).json()["data"]
    assert delayed["isAlarm"] is True
    assert delayed["businessToDwsDelayMinutes"] >= 90
    dws = next(item for item in delayed["syncTaskStatus"] if "聚合层" in item["taskName"])
    assert dws["status"] == "DELAYED"


def test_dashboard_overview_health_dimension():
    auth = headers()
    missing = client.get("/admin-api/ims/dc/dashboard/overview", headers=auth)
    assert missing.json()["code"] == 1001
    overview = client.get(
        "/admin-api/ims/dc/dashboard/overview", headers=auth, params={"statPeriod": "2026-10"}
    ).json()
    assert overview["code"] == 0
    for key in ("totalGmv", "totalCost", "netProfit", "sessionCount", "accountCount", "assetCount", "dataAsOf", "refreshedAt"):
        assert key in overview["data"]
    health = client.get("/admin-api/ims/dc/dashboard/health", headers=auth).json()
    assert health["code"] == 0
    assert health["data"]["target"] == 98
    assert isinstance(health["data"]["isAlarm"], bool)
    assert isinstance(health["data"]["trend"], list)
    bad = client.get(
        "/admin-api/ims/dc/dashboard/dimension",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "CITY"},
    )
    assert bad.json()["code"] == 1001
    dimension = client.get(
        "/admin-api/ims/dc/dashboard/dimension",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "PLATFORM"},
    ).json()
    assert dimension["code"] == 0
    assert isinstance(dimension["data"], list)
