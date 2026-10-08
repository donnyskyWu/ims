import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from tests.test_live import headers, register_payload, seed_live_deps

client = TestClient(app)


def approved_session(auth: dict) -> str:
    account_id, person_id, phone_id, room_id = seed_live_deps()
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=register_payload(account_id, person_id, phone_id, room_id),
    )
    assert reg.json()["code"] == 0
    code = reg.json()["data"]["sessionCode"]
    detail = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    if detail.get("sessionStatus") == "PENDING_RISK_CHECK":
        client.put(
            f"/admin-api/ims/live/register/{code}/approve",
            headers=auth,
            json={"approve": True},
        )
    report = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json={
            "actualStart": "2026-10-06T20:00:00+08:00",
            "actualEnd": "2026-10-06T22:00:00+08:00",
            "gmv": 100000.0,
            "refundAmount": 2000.0,
            "orderCount": 120,
            "viewerCount": 5000,
            "peakOnline": 800,
            "newFans": 200,
            "adCost": 5000.0,
        },
    )
    assert report.json()["code"] == 0
    confirm = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirm.json()["code"] == 0
    return code


def test_fin_cost_pending_submit_confirm():
    auth = headers()
    code = approved_session(auth)
    pending = client.get("/admin-api/ims/fin/cost/pending-sessions", headers=auth)
    assert pending.json()["code"] == 0
    codes = [row["sessionCode"] for row in pending.json()["data"]["list"]]
    assert code in codes

    token = uuid.uuid4().hex
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": token},
        json={
            "commissionRate": 0.05,
            "adCost": 5000,
            "rechargeCost": 100,
            "fixedCost": 2000,
            "sampleCost": 500,
            "shareCostType": "MANUAL",
            "shareDaren": 3000,
            "shareRealname": 1000,
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["entryStatus"] == "SUBMITTED"
    assert body["data"]["totalCost"] == 16600.0

    dup = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": token},
        json={"commissionRate": 0.05, "adCost": 0, "shareCostType": "MANUAL"},
    )
    assert dup.json()["data"]["totalCost"] == 16600.0

    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0
    assert confirmed.json()["data"]["entryStatus"] == "CONFIRMED"

    rate = client.get("/admin-api/ims/fin/cost/complete-rate", headers=auth)
    assert rate.json()["data"]["costEnteredCount"] >= 1

    listed = client.get("/admin-api/ims/fin/cost/list", headers=auth, params={"sessionCode": code})
    assert listed.json()["data"]["total"] >= 1
    assert listed.json()["data"]["list"][0]["entryStatus"] == "CONFIRMED"


def confirm_cost_for_session(auth: dict, code: str) -> None:
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "commissionRate": 0.05,
            "adCost": 5000,
            "rechargeCost": 100,
            "fixedCost": 2000,
            "sampleCost": 500,
            "shareCostType": "MANUAL",
            "shareDaren": 3000,
            "shareRealname": 1000,
        },
    )
    assert created.json()["code"] == 0
    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0


def test_fin_profit_list_and_detail():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)

    summary = client.get("/admin-api/ims/fin/profit/summary", headers=auth)
    assert summary.json()["code"] == 0
    assert summary.json()["data"]["sessionCount"] >= 1

    listed = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"sessionCode": code})
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1
    row = listed.json()["data"]["list"][0]
    assert row["calcStatus"] == "CALCULATED"
    assert row["netProfit"] == 81400.0

    detail = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["grossProfit"] == 93000.0


def test_dc_profit_trace_list_and_chain():
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)

    listed = client.get("/admin-api/ims/dc/profit-trace/list", headers=auth, params={"sessionCode": code})
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1
    row = listed.json()["data"]["list"][0]
    assert row["netProfit"] == 81400.0

    chain = client.get(f"/admin-api/ims/dc/profit-trace/{code}", headers=auth)
    body = chain.json()
    assert body["code"] == 0
    assert body["data"]["chain"]["session"]["sessionCode"] == code
    assert body["data"]["queryCostMs"] >= 0
    assert len(body["data"]["chain"]["costDetail"]) >= 5

    share = client.get(f"/admin-api/ims/dc/profit-trace/share-detail/{code}", headers=auth)
    assert share.json()["code"] == 0
    assert len(share.json()["data"]) >= 1


def test_dc_profit_trace_requires_confirmed_cost():
    auth = headers()
    code = approved_session(auth)
    denied = client.get(f"/admin-api/ims/dc/profit-trace/{code}", headers=auth)
    assert denied.json()["code"] == 1145


def test_fin_profit_detail_requires_confirmed_cost():
    auth = headers()
    code = approved_session(auth)
    denied = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth)
    assert denied.json()["code"] == 1145


def test_fin_e2e_live_confirmed_cost_profit_trace_chain():
    """W9 FIN 链路：直播 CONFIRMED → 成本录入/核准 → 利润 list → 利润反查 chain。"""
    auth = headers()
    code = approved_session(auth)

    pending = client.get("/admin-api/ims/fin/cost/pending-sessions", headers=auth)
    assert pending.json()["code"] == 0
    assert code in [row["sessionCode"] for row in pending.json()["data"]["list"]]

    token = uuid.uuid4().hex
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": token},
        json={
            "commissionRate": 0.05,
            "adCost": 5000,
            "rechargeCost": 100,
            "fixedCost": 2000,
            "sampleCost": 500,
            "shareCostType": "MANUAL",
            "shareDaren": 3000,
            "shareRealname": 1000,
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["entryStatus"] == "SUBMITTED"
    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0
    assert confirmed.json()["data"]["entryStatus"] == "CONFIRMED"

    listed = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"sessionCode": code})
    assert listed.json()["code"] == 0
    profit_row = listed.json()["data"]["list"][0]
    assert profit_row["calcStatus"] == "CALCULATED"
    assert profit_row["netProfit"] == 81400.0

    fin_detail = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth)
    assert fin_detail.json()["code"] == 0
    assert fin_detail.json()["data"]["sessionCode"] == code

    trace_list = client.get("/admin-api/ims/dc/profit-trace/list", headers=auth, params={"sessionCode": code})
    assert trace_list.json()["code"] == 0
    assert trace_list.json()["data"]["list"][0]["netProfit"] == 81400.0

    chain = client.get(f"/admin-api/ims/dc/profit-trace/{code}", headers=auth)
    body = chain.json()
    assert body["code"] == 0
    assert body["data"]["chain"]["session"]["sessionCode"] == code
    assert body["data"]["chain"]["profit"]["netProfit"] == 81400.0
    assert len(body["data"]["chain"]["costDetail"]) >= 5
    assert body["data"]["queryCostMs"] >= 0


def test_fin_cost_rejects_unapproved_session():
    auth = headers()
    account_id, person_id, phone_id, _ = seed_live_deps()
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=register_payload(account_id, person_id, phone_id, None),
    )
    code = reg.json()["data"]["sessionCode"]
    denied = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"commissionRate": 0.05, "adCost": 0, "shareCostType": "MANUAL"},
    )
    assert denied.json()["code"] == 1141
