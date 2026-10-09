import os
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import DcSyncTask, LiveSession, Role, RolePerm, User, UserRole
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


def test_dc_dashboard_rejects_bad_period_and_dimension():
    auth = headers()
    bad_period = client.get(
        "/admin-api/ims/dc/dashboard/overview", headers=auth, params={"statPeriod": "202610"}
    )
    assert bad_period.json()["code"] == 1001
    bad_dim = client.get(
        "/admin-api/ims/dc/dashboard/dimension",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "DAREN"},
    )
    assert bad_dim.json()["code"] == 1001
    bad_range = client.get(
        "/admin-api/ims/dc/dashboard/health", headers=auth, params={"dateRange": "2099-02-01"}
    )
    assert bad_range.json()["code"] == 1001


def test_dc_dashboard_overview_dimension_and_health_alarm():
    """DC-003：已核算场次进入总览与下钻；缺资产的场次把完整率打到 98% 以下。"""
    from tests.test_fin import approved_session, confirm_cost_for_session

    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)

    overview = client.get(
        "/admin-api/ims/dc/dashboard/overview", headers=auth, params={"statPeriod": "2026-10"}
    )
    body = overview.json()
    assert body["code"] == 0
    assert body["data"]["totalGmv"] >= 100000
    assert body["data"]["netProfit"] >= 81400
    assert body["data"]["sessionCount"] >= 1
    assert body["data"]["dataAsOf"].endswith("+08:00")
    assert body["data"]["refreshedAt"][14:16] == "00"

    drilled = client.get(
        "/admin-api/ims/dc/dashboard/dimension",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "PLATFORM", "drillTo": "DOUYIN"},
    )
    rows = drilled.json()["data"]
    assert len(rows) == 1
    assert rows[0]["dimensionLabel"] == "抖音"
    child = next(item for item in rows[0]["children"] if item["dimensionValue"] == code)
    assert child["gmv"] == 100000.0
    assert child["netProfit"] == 81400.0
    assert child["sessionCount"] == 1

    account_rows = client.get(
        "/admin-api/ims/dc/dashboard/dimension",
        headers=auth,
        params={"statPeriod": "2026-10", "dimensionType": "ACCOUNT"},
    ).json()["data"]
    assert any(item["dimensionValue"] for item in account_rows)

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        tenant_id = int(admin.tenant_id or 0)
        db.add(
            LiveSession(
                session_code="IMS20990115DYD0001",
                account_id=1,
                account_no="AC-DASH-GAP",
                realname_person_id=1,
                realname_name="缺资产",
                responsible_user_id=admin.id,
                device_asset_ids="[]",
                platform="DOUYIN",
                plan_start_time="2099-01-15T20:00:00+08:00",
                session_status="PENDING_RISK_CHECK",
                tenant_id=tenant_id,
                creator=admin.id,
            )
        )
        db.add(
            LiveSession(
                session_code="IMS20990115DYD0002",
                account_id=1,
                account_no="AC-DASH-OK",
                realname_person_id=1,
                realname_name="链路齐",
                responsible_user_id=admin.id,
                device_asset_ids="[9]",
                platform="DOUYIN",
                plan_start_time="2099-01-15T21:00:00+08:00",
                session_status="PENDING_RISK_CHECK",
                tenant_id=tenant_id,
                creator=admin.id,
            )
        )
        db.commit()
    finally:
        db.close()

    health = client.get(
        "/admin-api/ims/dc/dashboard/health",
        headers=auth,
        params={"dateRange": "2099-01-15,2099-01-15"},
    ).json()
    assert health["code"] == 0
    data = health["data"]
    assert data["assetRelationCompleteRate"] == 50.0
    assert data["target"] == 98
    assert data["isAlarm"] is True
    assert data["ledgerTraceRate"] == 0.0
    assert data["trend"] == [{"statDate": "2099-01-15", "completeRate": 50.0}]


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


def test_dashboard_freshness_failed_keeps_last_snapshot():
    """FAILED 仍告警；有成功任务时 dataAsOf 取成功快照，全部失败时不回落到当前时刻。"""
    auth = headers()
    assert client.get("/admin-api/ims/dc/dashboard/freshness", headers=auth).json()["code"] == 0
    success_at = utcnow().replace(microsecond=0) - timedelta(minutes=12)
    failed_at = utcnow().replace(microsecond=0) - timedelta(hours=4)
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        tenant_id = int(admin.tenant_id or 0)
        rows = list(
            db.scalars(
                select(DcSyncTask).where(DcSyncTask.deleted == 0, DcSyncTask.tenant_id == tenant_id)
            ).all()
        )
        assert rows
        for row in rows:
            row.status = "SUCCESS"
            row.last_run_at = success_at
        failed = next(row for row in rows if "看板缓存" in (row.task_name or ""))
        failed.status = "FAILED"
        failed.last_run_at = failed_at
        db.commit()
    finally:
        db.close()

    mixed = client.get("/admin-api/ims/dc/dashboard/freshness", headers=auth).json()["data"]
    assert mixed["isAlarm"] is True
    cache = next(item for item in mixed["syncTaskStatus"] if "看板缓存" in item["taskName"])
    assert cache["status"] == "FAILED"
    others = [item for item in mixed["syncTaskStatus"] if item is not cache]
    assert others
    assert {item["status"] for item in others} == {"SUCCESS"}
    mixed_as_of = datetime.fromisoformat(mixed["dataAsOf"])
    assert abs((mixed_as_of - success_at.replace(tzinfo=timezone.utc).astimezone(mixed_as_of.tzinfo)).total_seconds()) < 90

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        tenant_id = int(admin.tenant_id or 0)
        rows = list(
            db.scalars(
                select(DcSyncTask).where(DcSyncTask.deleted == 0, DcSyncTask.tenant_id == tenant_id)
            ).all()
        )
        for row in rows:
            row.status = "FAILED"
            row.last_run_at = failed_at
        db.commit()
    finally:
        db.close()
    stalled = client.get("/admin-api/ims/dc/dashboard/freshness", headers=auth).json()["data"]
    assert stalled["isAlarm"] is True
    assert {item["status"] for item in stalled["syncTaskStatus"]} == {"FAILED"}
    stalled_as_of = datetime.fromisoformat(stalled["dataAsOf"])
    age_minutes = (datetime.now(stalled_as_of.tzinfo) - stalled_as_of).total_seconds() / 60
    assert age_minutes > 120
