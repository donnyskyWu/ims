"""#206 · 场次账号/责任人、待录入责任人、告警时段与规则筛选。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.live_fin_e2e_seed import E2E_LEDGER_SESSION
from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_session_list_filters_by_account_and_owner():
    auth = headers()
    detail = client.get(f"/admin-api/ims/live/sessions/{E2E_LEDGER_SESSION}", headers=auth)
    body = detail.json()
    assert body["code"] == 0, body
    account_id = body["data"]["accountId"]
    owner_id = body["data"]["responsibleUserId"]
    assert account_id and owner_id

    hit = client.get(
        "/admin-api/ims/live/sessions/list",
        headers=auth,
        params={
            "sessionCode": E2E_LEDGER_SESSION,
            "accountId": account_id,
            "responsibleUserId": owner_id,
        },
    )
    assert hit.json()["code"] == 0, hit.json()
    assert [row["sessionCode"] for row in hit.json()["data"]["list"]] == [E2E_LEDGER_SESSION]

    exported = client.get(
        "/admin-api/ims/live/ledger/export",
        headers=auth,
        params={"sessionCode": E2E_LEDGER_SESSION, "accountId": account_id, "responsibleUserId": owner_id},
    )
    assert exported.json()["code"] == 0, exported.json()

    wrong_account = client.get(
        "/admin-api/ims/live/sessions/list",
        headers=auth,
        params={"sessionCode": E2E_LEDGER_SESSION, "accountId": 999999991},
    )
    assert wrong_account.json()["data"]["list"] == []

    wrong_owner = client.get(
        "/admin-api/ims/live/sessions/list",
        headers=auth,
        params={"sessionCode": E2E_LEDGER_SESSION, "responsibleUserId": 999999991},
    )
    assert wrong_owner.json()["data"]["list"] == []


def test_pending_owner_filter_miss_is_empty():
    auth = headers()
    pending = client.get(
        "/admin-api/ims/live/report/pending",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "responsibleUserId": 999999991},
    )
    body = pending.json()
    assert body["code"] == 0, body
    assert body["data"]["list"] == []


def test_alarm_time_range_and_rule_keyword_miss():
    auth = headers()
    records = client.get(
        "/admin-api/ims/live/alarm/records",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "timeRange": ["1999-01-01", "1999-01-02"]},
    )
    body = records.json()
    assert body["code"] == 0, body
    assert body["data"]["list"] == []

    rules = client.get(
        "/admin-api/ims/live/alarm/rules",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "keyword": "不存在的规则名-206", "ruleType": "EVENT", "status": "DISABLED"},
    )
    listed = rules.json()
    assert listed["code"] == 0, listed
    assert listed["data"]["list"] == []
