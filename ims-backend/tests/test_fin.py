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
    data = detail.json()["data"]
    assert data["grossProfit"] == 93000.0
    assert data["operatingProfit"] == 87900.0
    assert data["netProfit"] == 81400.0
    params = data["calcRuleSnapshot"]["params"]
    assert params["revenue"] == 100000.0
    assert params["refund"] == 2000.0
    assert params["commissionAmount"] == 5000.0
    assert params["adCost"] == 5000.0
    assert params["rechargeCost"] == 100.0
    assert params["fixedCost"] == 2000.0
    assert params["sampleCost"] == 500.0
    assert params["shareDaren"] == 3000.0
    assert params["shareRealname"] == 1000.0
    gross = round(params["revenue"] - params["refund"] - params["commissionAmount"], 2)
    operating = round(gross - params["adCost"] - params["rechargeCost"], 2)
    net = round(
        operating - params["fixedCost"] - params["sampleCost"] - params["shareDaren"] - params["shareRealname"],
        2,
    )
    assert gross == 93000.0
    assert operating == 87900.0
    assert net == 81400.0
    assert data["grossProfit"] == gross
    assert data["operatingProfit"] == operating
    assert data["netProfit"] == net
    assert round(params["revenue"] - params["refund"] - params["totalCost"], 2) == net
    formula = data["calcRuleSnapshot"]["formula"]
    assert "netProfit = revenue - refund - totalCost" in formula
    assert "grossProfit = revenue - refund - commission" in formula
    assert "operatingProfit = grossProfit - adCost - rechargeCost" in formula


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


def test_live_fin_e2e_seed_deps():
    """#50 FIN closure：E2E 种子账号/手机存在且账号绑定实名人。"""
    from sqlalchemy import select

    from app.core import SessionLocal
    from app.live_fin_e2e_seed import E2E_FIN_ACCOUNT_NO, E2E_FIN_PHONE_CODE, ensure_live_fin_e2e_deps
    from app.models import User
    from app.ops_db import ops_session
    from app.ops_models import Phone, PlatformAccount

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin", User.deleted == 0).first()
        assert admin is not None
        ensure_live_fin_e2e_deps(db, admin)
    finally:
        db.close()
    ops = ops_session()
    try:
        account = ops.scalar(
            select(PlatformAccount).where(
                PlatformAccount.account_no == E2E_FIN_ACCOUNT_NO, PlatformAccount.deleted == 0
            )
        )
        phone = ops.scalar(
            select(Phone).where(Phone.phone_code == E2E_FIN_PHONE_CODE, Phone.deleted == 0)
        )
        assert account is not None and account.realname_id
        assert phone is not None
    finally:
        ops.close()


def test_fin_cost_correction_recalc_profit_and_share_trace():
    """#54 E2E-S3-04：成本更正 → 利润 RECALCULATED · 分成明细同步。"""
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)

    listed = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"sessionCode": code})
    assert listed.json()["data"]["list"][0]["calcStatus"] == "CALCULATED"
    assert listed.json()["data"]["list"][0]["netProfit"] == 81400.0

    token = uuid.uuid4().hex
    corrected = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": token},
        json={
            "correctionReason": "E2E 投放补录",
            "corrected": {
                "commissionRate": 0.05,
                "adCost": 6000,
                "rechargeCost": 100,
                "fixedCost": 2000,
                "sampleCost": 500,
                "shareCostType": "MANUAL",
                "shareDaren": 3500,
                "shareRealname": 1000,
            },
        },
    )
    body = corrected.json()
    assert body["code"] == 0
    assert body["data"]["recalcTriggered"] is True
    assert body["data"]["correctionNo"]
    assert any(e["item"] == "投放成本" for e in body["data"]["blueEntries"])

    dup = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": token},
        json={
            "correctionReason": "ignored",
            "corrected": {
                "commissionRate": 0.05,
                "adCost": 6000,
                "rechargeCost": 100,
                "fixedCost": 2000,
                "sampleCost": 500,
                "shareCostType": "MANUAL",
                "shareDaren": 3500,
                "shareRealname": 1000,
            },
        },
    )
    assert dup.json()["code"] == 0
    assert dup.json()["data"]["correctionNo"] == body["data"]["correctionNo"]

    profit = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"sessionCode": code})
    row = profit.json()["data"]["list"][0]
    assert row["calcStatus"] == "RECALCULATED"
    assert row["netProfit"] == 79900.0
    assert row["calcVersion"] >= 2

    share = client.get(f"/admin-api/ims/dc/profit-trace/share-detail/{code}", headers=auth)
    daren = next(x for x in share.json()["data"] if x["shareTarget"] == "DAREN")
    assert daren["shareAmount"] == 3500.0


def test_fin_share_audit_payoff_amounts_sum_to_total():
    """#57 E2E-S3-05：核准成本后分成单双审 → PAID_OFF，拆分累计=总额。"""
    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)

    listed = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code})
    assert listed.json()["code"] == 0
    rows = listed.json()["data"]["list"]
    assert len(rows) == 2
    assert {row["shareTarget"] for row in rows} == {"DAREN", "REALNAME"}
    assert sum(row["shareAmount"] for row in rows) == 4000.0
    assert all(row["calcDetail"]["shareTotal"] == 4000.0 for row in rows)
    assert all(row["status"] == "PENDING_AUDIT" for row in rows)

    early = client.put(
        f"/admin-api/ims/fin/share/result/{rows[0]['id']}/payoff",
        headers=auth,
        json={"payoffNote": "too soon"},
    )
    assert early.json()["code"] == 1148

    denied = client.put(
        f"/admin-api/ims/fin/share/result/{rows[0]['id']}/audit",
        headers=auth,
        json={"conclusion": "APPROVE", "auditRole": "NOPE"},
    )
    assert denied.json()["code"] == 1149

    for row in rows:
        fin = client.put(
            f"/admin-api/ims/fin/share/result/{row['id']}/audit",
            headers=auth,
            json={"conclusion": "APPROVE", "auditRole": "FINANCE", "remark": "fin"},
        )
        assert fin.json()["code"] == 0
        assert fin.json()["data"]["status"] == "PENDING_AUDIT"
        assert fin.json()["data"]["finAuditPassed"] is True
        assert fin.json()["data"]["bothPassed"] is False

        biz = client.put(
            f"/admin-api/ims/fin/share/result/{row['id']}/audit",
            headers=auth,
            json={"conclusion": "APPROVE", "auditRole": "BUSINESS"},
        )
        assert biz.json()["code"] == 0
        assert biz.json()["data"]["status"] == "AUDITED"
        assert biz.json()["data"]["bothPassed"] is True

        paid = client.put(
            f"/admin-api/ims/fin/share/result/{row['id']}/payoff",
            headers=auth,
            json={"payoffNote": "paid", "payoffVoucher": {"fileName": "v.txt", "fileKey": "k"}},
        )
        assert paid.json()["code"] == 0
        assert paid.json()["data"] is None

    again = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code, "status": "PAID_OFF"})
    paid_rows = again.json()["data"]["list"]
    assert len(paid_rows) == 2
    assert sum(row["shareAmount"] for row in paid_rows) == 4000.0


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


def _session_in_period(auth: dict, plan_start: str, deps: tuple[int, int, int, int]) -> str:
    account_id, person_id, phone_id, _room_id = deps
    payload = register_payload(account_id, person_id, phone_id, None)
    payload["planStartTime"] = plan_start
    payload["planEndTime"] = "2099-06-15T22:00:00+08:00"
    payload["topic"] = f"pytest period {uuid.uuid4().hex[:6]}"
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=payload,
    )
    assert reg.json()["code"] == 0, reg.json()
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
            "actualStart": "2099-06-15T20:00:00+08:00",
            "actualEnd": "2099-06-15T22:00:00+08:00",
            "gmv": 100000.0,
            "refundAmount": 2000.0,
            "orderCount": 120,
            "viewerCount": 5000,
            "peakOnline": 800,
            "newFans": 200,
            "adCost": 5000.0,
        },
    )
    assert report.json()["code"] == 0, report.json()
    confirm = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirm.json()["code"] == 0, confirm.json()
    return code


def _cost_body(**overrides) -> dict:
    body = {
        "commissionRate": 0.05,
        "adCost": 5000,
        "rechargeCost": 100,
        "fixedCost": 2000,
        "sampleCost": 500,
        "shareCostType": "MANUAL",
        "shareDaren": 3000,
        "shareRealname": 1000,
    }
    body.update(overrides)
    return body


def test_fin_period_close_locks_writes_then_r4_red_correction():
    """#59 · 结账 LOCKED · 写入 1142 · 未审批更正 1155 · R4 通过后红冲。"""
    auth = headers()
    deps = seed_live_deps()
    code = _session_in_period(auth, "2099-06-15T20:00:00+08:00", deps)
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=_cost_body(),
    )
    assert created.json()["code"] == 0, created.json()
    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0, confirmed.json()

    opened = client.get("/admin-api/ims/fin/period", headers=auth, params={"periodMonth": "2099-06"})
    assert opened.json()["code"] == 0
    assert opened.json()["data"]["financeStatus"] == "OPEN"
    assert client.post("/admin-api/ims/fin/period/close", headers=auth, json={"periodMonth": "2099-13"}).json()["code"] == 1001

    closed = client.post("/admin-api/ims/fin/period/close", headers=auth, json={"periodMonth": "2099-06"})
    assert closed.json()["code"] == 0, closed.json()
    assert closed.json()["data"]["financeStatus"] == "LOCKED"
    again = client.post("/admin-api/ims/fin/period/close", headers=auth, json={"periodMonth": "2099-06"})
    assert again.json()["code"] == 0
    assert again.json()["data"]["financeStatus"] == "LOCKED"

    other = _session_in_period(auth, "2099-06-16T20:00:00+08:00", deps)
    denied = client.post(
        f"/admin-api/ims/fin/cost/{other}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=_cost_body(),
    )
    assert denied.json()["code"] == 1142
    assert "财务期间已结账" in denied.json()["msg"]

    recalc = client.post(f"/admin-api/ims/fin/profit/recalc/{code}", headers=auth)
    assert recalc.json()["code"] == 1142

    blocked = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"correctionReason": "锁后未批", "corrected": _cost_body(adCost=4000)},
    )
    assert blocked.json()["code"] == 1155
    assert "R4" in blocked.json()["msg"]

    shares = client.get(
        "/admin-api/ims/fin/share/results",
        headers=auth,
        params={"sessionCode": code, "pageNo": 1, "pageSize": 10},
    ).json()["data"]["list"]
    assert shares
    audit = client.put(
        f"/admin-api/ims/fin/share/result/{shares[0]['id']}/audit",
        headers=auth,
        json={"conclusion": "APPROVE", "auditRole": "FINANCE", "remark": "locked"},
    )
    assert audit.json()["code"] == 1142

    templates = client.get(
        "/admin-api/ims/flow/template/list",
        headers=auth,
        params={"templateName": "费用报销", "status": "PUBLISHED", "pageNo": 1, "pageSize": 10},
    )
    assert templates.json()["code"] == 0, templates.json()
    tpl = next(row for row in templates.json()["data"]["list"] if row["templateCode"] == "FL-REIMB")
    started = client.post(
        "/admin-api/ims/flow/instance",
        headers=auth,
        json={
            "templateId": tpl["id"],
            "businessKey": f"FIN-LOCK-{code}",
            "formData": {"title": f"锁后更正 {code}", "sessionCode": code},
        },
    )
    assert started.json()["code"] == 0, started.json()
    assert started.json()["data"]["instanceStatus"] == "RUNNING"
    todos = client.get(
        "/admin-api/ims/flow/task/my-todo",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50},
    ).json()["data"]["list"]
    task = next(row for row in todos if (row.get("formData") or {}).get("title") == f"锁后更正 {code}")
    handled = client.put(
        f"/admin-api/ims/flow/task/{task['id']}/handle",
        headers=auth,
        json={"action": "APPROVE", "comment": "R4 锁后更正"},
    )
    assert handled.json()["code"] == 0, handled.json()
    assert handled.json()["data"]["newStatus"] == "APPROVED"

    fixed = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"correctionReason": "锁后红冲投放", "corrected": _cost_body(adCost=4000)},
    )
    body = fixed.json()
    assert body["code"] == 0, body
    assert body["data"]["recalcTriggered"] is True
    assert any(entry["item"] == "投放成本" and entry["amount"] == -1000 for entry in body["data"]["redEntries"])
    profit = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth)
    assert profit.json()["code"] == 0, profit.json()
    assert profit.json()["data"]["calcStatus"] == "RECALCULATED"
    assert profit.json()["data"]["netProfit"] == 82400.0

    # 默认 2026-10 场次不受 2099-06 结账影响
    open_month = _session_in_period(auth, "2026-10-06T20:00:00+08:00", deps)
    still = client.post(
        f"/admin-api/ims/fin/cost/{open_month}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=_cost_body(),
    )
    assert still.json()["code"] == 0, still.json()


def test_fin_profit_history_versions_stay_immutable():
    """#107：核准 / 手动重算 / 成本更正各留一版，旧版金额不可改。"""
    auth = headers()
    missing = client.get("/admin-api/ims/fin/profit/history/IMS0000000000000000", headers=auth)
    assert missing.json()["code"] == 1504

    code = approved_session(auth)
    denied = client.get(f"/admin-api/ims/fin/profit/history/{code}", headers=auth)
    assert denied.json()["code"] == 1145

    confirm_cost_for_session(auth, code)
    first = client.get(f"/admin-api/ims/fin/profit/history/{code}", headers=auth).json()
    assert first["code"] == 0, first
    assert len(first["data"]) == 1
    v1 = first["data"][0]
    assert v1["calcVersion"] == 1
    assert v1["triggerType"] == "AUTO_CONFIRM"
    assert v1["triggerReason"] == "成本核准自动计算"
    assert v1["calcStatus"] == "CALCULATED"
    assert v1["netProfit"] == 81400.0
    assert v1["grossProfit"] == 93000.0
    assert v1["operatingProfit"] == 87900.0

    manual = client.post(f"/admin-api/ims/fin/profit/recalc/{code}", headers=auth)
    assert manual.json()["code"] == 0, manual.json()
    assert manual.json()["data"]["calcVersion"] == 2
    assert manual.json()["data"]["calcStatus"] == "RECALCULATED"

    listed = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"sessionCode": code}).json()
    assert listed["data"]["list"][0]["calcVersion"] == 2
    assert listed["data"]["list"][0]["netProfit"] == 81400.0

    mid = client.get(f"/admin-api/ims/fin/profit/history/{code}", headers=auth).json()["data"]
    assert [row["calcVersion"] for row in mid] == [2, 1]
    assert mid[0]["triggerType"] == "MANUAL"
    assert mid[0]["triggerReason"] == "手动触发重算"
    assert mid[0]["netProfit"] == 81400.0
    assert mid[0]["operatingProfit"] == 87900.0
    assert mid[1]["netProfit"] == 81400.0
    assert mid[1]["operatingProfit"] == 87900.0

    token = uuid.uuid4().hex
    corrected = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": token},
        json={
            "correctionReason": "E2E 投放补录",
            "corrected": {
                "commissionRate": 0.05,
                "adCost": 6000,
                "rechargeCost": 100,
                "fixedCost": 2000,
                "sampleCost": 500,
                "shareCostType": "MANUAL",
                "shareDaren": 3500,
                "shareRealname": 1000,
            },
        },
    )
    body = corrected.json()
    assert body["code"] == 0, body
    assert body["data"]["recalcTriggered"] is True

    dup = client.post(
        f"/admin-api/ims/fin/cost/{code}/correction",
        headers={**auth, "clientToken": token},
        json={
            "correctionReason": "ignored",
            "corrected": {
                "commissionRate": 0.05,
                "adCost": 1,
                "shareCostType": "MANUAL",
            },
        },
    )
    assert dup.json()["code"] == 0
    assert dup.json()["data"]["correctionNo"] == body["data"]["correctionNo"]

    versions = client.get(f"/admin-api/ims/fin/profit/history/{code}", headers=auth).json()["data"]
    assert [row["calcVersion"] for row in versions] == [3, 2, 1]
    assert versions[0]["triggerType"] == "AUTO_CORRECTION"
    assert versions[0]["triggerReason"] == "E2E 投放补录"
    assert versions[0]["calcStatus"] == "RECALCULATED"
    assert versions[0]["netProfit"] == 79900.0
    assert versions[0]["grossProfit"] == 93000.0
    assert versions[0]["operatingProfit"] == 86900.0
    assert versions[1]["netProfit"] == 81400.0
    assert versions[1]["operatingProfit"] == 87900.0
    assert versions[2]["triggerType"] == "AUTO_CONFIRM"
    assert versions[2]["netProfit"] == 81400.0
    assert versions[2]["operatingProfit"] == 87900.0

    after = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"sessionCode": code}).json()
    assert after["data"]["list"][0]["calcVersion"] == 3
    assert after["data"]["list"][0]["netProfit"] == 79900.0
    assert after["data"]["list"][0]["calcStatus"] == "RECALCULATED"


def _profit_on_day(auth: dict, deps: tuple[int, int, int, int], day: str, gmv: float, cost: dict) -> str:
    account_id, person_id, phone_id, _room_id = deps
    payload = register_payload(account_id, person_id, phone_id, None)
    payload["topic"] = f"pytest metric {uuid.uuid4().hex[:6]}"
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=payload,
    )
    assert reg.json()["code"] == 0, reg.json()
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
            "actualStart": f"{day}T20:00:00+08:00",
            "actualEnd": f"{day}T22:00:00+08:00",
            "gmv": gmv,
            "refundAmount": 0,
            "orderCount": 10,
            "viewerCount": 100,
            "peakOnline": 20,
            "newFans": 1,
            "adCost": cost.get("adCost", 0),
        },
    )
    assert report.json()["code"] == 0, report.json()
    confirm = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirm.json()["code"] == 0, confirm.json()
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=_cost_body(**cost),
    )
    assert created.json()["code"] == 0, created.json()
    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0, confirmed.json()
    return code


def test_fin_profit_list_sorts_by_metric_and_summarizes():
    """#111 · 毛利 / 经营利润 / 净利润切换排序，汇总跟随口径；负数净利润可落库。"""
    auth = headers()
    deps = seed_live_deps()
    stamp = uuid.uuid4().int
    day = f"{2060 + stamp % 25:04d}-{1 + (stamp // 25) % 12:02d}-{1 + (stamp // 400) % 27:02d}"
    high_gross = _profit_on_day(
        auth,
        deps,
        day,
        100000,
        {"adCost": 120000, "rechargeCost": 0, "fixedCost": 0, "sampleCost": 0, "shareDaren": 0, "shareRealname": 0},
    )
    high_net = _profit_on_day(
        auth,
        deps,
        day,
        30000,
        {"adCost": 0, "rechargeCost": 0, "fixedCost": 0, "sampleCost": 0, "shareDaren": 0, "shareRealname": 0},
    )

    def listed(kind: str):
        res = client.get(
            "/admin-api/ims/fin/profit/list",
            headers=auth,
            params={"dateFrom": day, "dateTo": day, "profitType": kind, "pageNo": 1, "pageSize": 20},
        )
        body = res.json()
        assert body["code"] == 0, body
        assert body["data"]["profitType"] == kind
        assert body["data"]["total"] == 2
        return body["data"]["list"]

    net_rows = listed("NET")
    assert [row["sessionCode"] for row in net_rows] == [high_net, high_gross]
    assert net_rows[0]["netProfit"] == 28500.0
    assert net_rows[0]["grossProfit"] == 28500.0
    assert net_rows[1]["netProfit"] == -25000.0
    assert net_rows[1]["grossProfit"] == 95000.0
    assert net_rows[1]["operatingProfit"] == -25000.0

    gross_rows = listed("GROSS")
    assert [row["sessionCode"] for row in gross_rows] == [high_gross, high_net]

    operating_rows = listed("OPERATING")
    assert [row["sessionCode"] for row in operating_rows] == [high_net, high_gross]

    default_rows = client.get(
        "/admin-api/ims/fin/profit/list",
        headers=auth,
        params={"dateFrom": day, "dateTo": day, "pageSize": 20},
    ).json()
    assert default_rows["data"]["profitType"] == "NET"
    assert [row["sessionCode"] for row in default_rows["data"]["list"]] == [high_net, high_gross]

    bad = client.get("/admin-api/ims/fin/profit/list", headers=auth, params={"profitType": "GMV"})
    assert bad.json()["code"] == 1001

    summary = client.get(
        "/admin-api/ims/fin/profit/summary",
        headers=auth,
        params={"dateFrom": day, "dateTo": day, "profitType": "GROSS"},
    ).json()
    assert summary["code"] == 0, summary
    assert summary["data"]["profitType"] == "GROSS"
    assert summary["data"]["shownProfit"] == 123500.0
    assert summary["data"]["totalNetProfit"] == 3500.0
    assert summary["data"]["totalOperatingProfit"] == 3500.0
    assert summary["data"]["sessionCount"] == 2

    net_summary = client.get(
        "/admin-api/ims/fin/profit/summary",
        headers=auth,
        params={"dateFrom": day, "dateTo": day, "profitType": "net"},
    ).json()
    assert net_summary["data"]["profitType"] == "NET"
    assert net_summary["data"]["shownProfit"] == 3500.0
