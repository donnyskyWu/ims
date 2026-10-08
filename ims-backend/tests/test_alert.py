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


def test_alert_rule_create_list_run_respond():
    auth = headers()
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "live.data.delay",
            "ruleName": "直播数据延迟",
            "thresholdExpr": "delayMinutes>30",
            "enabled": True,
        },
    )
    body = created.json()
    assert body["code"] == 0
    rule_id = body["data"]["id"]

    listed = client.get(
        "/admin-api/ims/alert/rule/list",
        headers=auth,
        params={"ruleName": "直播", "enabled": True, "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1

    run = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    assert run.json()["code"] == 0
    alert_no = run.json()["data"]["alertNo"]

    records = client.get(
        "/admin-api/ims/alert/check/records",
        headers=auth,
        params={"pageNo": 1, "pageSize": 5},
    )
    assert any(r["alertNo"] == alert_no for r in records.json()["data"]["list"])

    ack = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "ACK"},
    )
    assert ack.json()["code"] == 0
    assert ack.json()["data"]["responseStatus"] == "ACK"

    handled = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "HANDLE"},
    )
    assert handled.json()["code"] == 0
    assert handled.json()["data"]["responseStatus"] == "HANDLED"


def test_alert_rule_duplicate_code_1165():
    auth = headers()
    code = "dup.rule.w9"
    first = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": code, "ruleName": "A", "enabled": False},
    )
    assert first.json()["code"] == 0
    second = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": code, "ruleName": "B", "enabled": False},
    )
    assert second.json()["code"] == 1165


def test_alert_dedup_and_history_summary():
    auth = headers()
    dedup = client.get("/admin-api/ims/alert/dedup/list", headers=auth, params={"pageNo": 1, "pageSize": 10})
    assert dedup.json()["code"] == 0
    assert dedup.json()["data"]["total"] >= 2

    summary = client.get("/admin-api/ims/alert/history/summary", headers=auth)
    assert summary.json()["code"] == 0
    assert "totalAlerts" in summary.json()["data"]


def test_alert_rule_trial_alias_matches_run():
    auth = headers()
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "trial.alias.smoke",
            "ruleName": "试跑别名",
            "thresholdExpr": "x>1",
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]

    trial = client.post(f"/admin-api/ims/alert/rule/{rule_id}/trial", headers=auth)
    assert trial.json()["code"] == 0
    assert trial.json()["data"]["alertNo"]
