"""TC-20 BUG-C056～C060。每个用例只覆盖对应修复，不跑全量。"""

import os
import uuid

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


def test_c058_dedup_live_window_and_real_groups():
    auth = headers()
    listed = client.get("/admin-api/ims/alert/dedup/list", headers=auth, params={"pageNo": 1, "pageSize": 10})
    body = listed.json()
    assert body["code"] == 0
    live = next(row for row in body["data"]["list"] if row["policyCode"] == "DEDUP-LIVE")
    assert live["windowMinutes"] == 30
    assert body["data"]["summary"]["windowMinutes"] == 30
    assert body["data"]["summary"]["groupCount"] == 0
    assert "30 分钟" in body["data"]["summary"]["ruleText"]

    from app.core import SessionLocal
    from app.models import AlertDedupPolicy

    db = SessionLocal()
    try:
        row = db.query(AlertDedupPolicy).filter(AlertDedupPolicy.policy_code == "DEDUP-LIVE").one()
        row.window_minutes = 15
        db.commit()
    finally:
        db.close()

    repaired = client.get("/admin-api/ims/alert/dedup/list", headers=auth)
    live = next(row for row in repaired.json()["data"]["list"] if row["policyCode"] == "DEDUP-LIVE")
    assert live["windowMinutes"] == 30

    code = f"c058.{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": code, "ruleName": "同源试跑", "thresholdExpr": "delayMinutes>1", "level": 3, "enabled": True},
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    first = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    second = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    assert first.json()["code"] == 0 and second.json()["code"] == 0
    assert first.json()["data"]["alertNo"] != second.json()["data"]["alertNo"]

    grouped = client.get("/admin-api/ims/alert/dedup/list", headers=auth).json()["data"]
    assert grouped["summary"]["groupCount"] == 1
    assert grouped["summary"]["savedCount"] == 1
    group = grouped["groups"][0]
    assert group["count"] == 2
    assert group["windowMinutes"] == 30
    assert group["ruleCode"] == code
    assert set(group["alertNos"]) == {first.json()["data"]["alertNo"], second.json()["data"]["alertNo"]}

    records = client.get("/admin-api/ims/alert/check/records", headers=auth, params={"ruleCode": code, "pageSize": 10})
    data = records.json()["data"]
    assert data["levelCounts"]["L3"] >= 2
    assert data["list"][0]["responseStatus"] == "OPEN"
