import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import LiveSession, User

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


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
