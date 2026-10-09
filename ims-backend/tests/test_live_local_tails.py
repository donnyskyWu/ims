"""#197 · 风险检查空列表、草稿零分母、未绑定 Football 同步。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.live_fin_e2e_seed import E2E_LEDGER_SESSION
from app.main import app
from test_live_report_pack import full_report, headers, register, seed_account

client = TestClient(app)


def test_seeded_session_has_empty_risk_checks_and_unbound_sync():
    auth = headers()
    detail = client.get(f"/admin-api/ims/live/sessions/{E2E_LEDGER_SESSION}", headers=auth)
    assert detail.json()["code"] == 0, detail.json()
    body = detail.json()["data"]
    assert body["riskCheckResults"] == []
    assert body["riskLevel"] == "GREEN"
    assert body["metricsSnapshot"]["footballRoomBasic"] is None
    assert body["metricsSnapshot"]["syncStatus"] == "UNLINKED"

    blocked = client.post(f"/admin-api/ims/live/sessions/{E2E_LEDGER_SESSION}/football-sync", headers=auth, json={})
    assert blocked.json()["code"] == 1041
    assert "未绑定" in blocked.json()["msg"]


def test_draft_zero_denominator_and_reversed_times():
    auth = headers()
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)

    saved = client.put(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(orderCount=0, adCost=0, gmv=80),
    )
    assert saved.json()["code"] == 0, saved.json()
    report = client.get(f"/admin-api/ims/live/report/{code}", headers=auth)
    data = report.json()["data"]
    assert data["entryStatus"] == "DRAFT"
    assert data["avgOrderValue"] is None
    assert data["roas"] is None
    assert data["gmv"] == 80
    session = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth)
    assert session.json()["data"]["sessionStatus"] == "APPROVED"
    assert session.json()["data"]["riskCheckResults"]

    zero_lines = client.put(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(gmv=100, orderCount=2, adCost=0, costDetails=[{"costType": "AD", "amount": 0}]),
    )
    assert zero_lines.json()["code"] == 0, zero_lines.json()
    after_lines = client.get(f"/admin-api/ims/live/report/{code}", headers=auth).json()["data"]
    assert after_lines["avgOrderValue"] == 50.0
    assert after_lines["roas"] is None
    assert after_lines["costDetails"][0]["amount"] == 0

    reversed_time = client.put(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(actualEnd="2026-10-08T19:00:00+08:00"),
    )
    assert reversed_time.json()["code"] == 1001
    assert "晚于" in reversed_time.json()["msg"]
    kept = client.get(f"/admin-api/ims/live/report/{code}", headers=auth).json()["data"]
    assert kept["actualEnd"] == "2026-10-08T22:00:00+08:00"
    assert kept["entryStatus"] == "DRAFT"
    still = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth)
    assert still.json()["data"]["sessionStatus"] == "APPROVED"
