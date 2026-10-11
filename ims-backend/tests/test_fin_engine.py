"""BUG-050 分成引擎：核准并算完利润后生成分成单，从净利润扣除。

同一范围、同一对象只命中优先级最高的一条。佣金基数、核准前改成本、净利率分母仍保持现有实现。
"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.core import SessionLocal
from app.fin import net_profit_rate
from app.fin_policy import EDIT_COST_BEFORE_CONFIRM, commission_amount, net_rate_denominator
from app.models import LiveReport, LiveSession
from tests.test_fin_share_rule import rule_body
from tests.test_live import headers

client = TestClient(app)


def test_fin_policy_matches_confirmed_rules():
    assert EDIT_COST_BEFORE_CONFIRM is True
    assert commission_amount(50000, 2000, 0.05) == 2500
    assert net_rate_denominator(50000, 2000) == 48000
    assert net_profit_rate(50000, 2000, 30940) == 64.46


def seed_confirmed_session(code: str, account_id: int, gmv: float, refund: float, topic: str = "") -> None:
    db = SessionLocal()
    try:
        db.add(
            LiveSession(
                session_code=code,
                account_id=account_id,
                platform="DOUYIN",
                topic=topic,
                plan_start_time="2026-10-11T20:00:00+08:00",
                session_status="ENDED",
                responsible_user_id=1,
                tenant_id=0,
            )
        )
        db.add(
            LiveReport(
                session_code=code,
                gmv=gmv,
                refund_amount=refund,
                entry_status="CONFIRMED",
                tenant_id=0,
            )
        )
        db.commit()
    finally:
        db.close()


def create_rule(auth: dict, **overrides) -> None:
    created = client.post("/admin-api/ims/fin/share/rule", headers=auth, json=rule_body(**overrides))
    assert created.json()["code"] == 0, created.json()


def submit_engine(auth: dict, code: str, **costs) -> dict:
    payload = {
        "commissionRate": 0.05,
        "adCost": 0,
        "rechargeCost": 0,
        "fixedCost": 0,
        "sampleCost": 0,
        "shareCostType": "ENGINE",
        "shareDaren": 0,
        "shareRealname": 0,
    }
    payload.update(costs)
    created = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=payload,
    )
    assert created.json()["code"] == 0, created.json()
    confirmed = client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0, confirmed.json()
    return created.json()["data"]


ALL_SCOPE = {"platforms": [], "accountIds": [], "ipGroupIds": []}


def test_engine_daren_share_on_dys0003():
    """IMS20261011DYS0003：GMV 5000、退款 0、固定 8000、佣金 5%，达人分成 4750×10%=475，净利 -3725。"""
    auth = headers()
    code = "IMS20261011DYS0003"
    create_rule(
        auth,
        ruleName="TC-达人分成B",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.1,
        priority=10,
        scope=ALL_SCOPE,
    )
    seed_confirmed_session(code, 91003, 5000, 0)
    saved = submit_engine(auth, code, commissionRate=0.05, fixedCost=8000)
    assert saved["shareDaren"] == 475
    assert saved["commissionAmount"] == 250
    profit = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth).json()["data"]
    assert profit["grossProfit"] == 4750
    assert profit["netProfit"] == -3725
    bills = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code}).json()["data"]["list"]
    daren = [row for row in bills if row["shareTarget"] == "DAREN"]
    assert len(daren) == 1
    assert daren[0]["shareAmount"] == 475
    assert daren[0]["shareBase"] == 4750
    assert daren[0]["ruleName"] == "TC-达人分成B"
    assert daren[0]["status"] == "PENDING_AUDIT"


def test_engine_keeps_higher_priority_rule_on_dys0004():
    """IMS20261011DYS0004：只命中 TC-达人高优 9500×12%=1140，不叠加 TC-达人分成B，净利 7360。"""
    auth = headers()
    code = "IMS20261011DYS0004"
    create_rule(
        auth,
        ruleName="TC-达人分成B",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.1,
        priority=10,
        scope=ALL_SCOPE,
    )
    create_rule(
        auth,
        ruleName="TC-达人高优",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.12,
        priority=20,
        scope=ALL_SCOPE,
        confirmConflict=True,
    )
    seed_confirmed_session(code, 91004, 10000, 0)
    saved = submit_engine(auth, code, commissionRate=0.05, fixedCost=1000)
    assert saved["shareDaren"] == 1140
    profit = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth).json()["data"]
    assert profit["grossProfit"] == 9500
    assert profit["netProfit"] == 7360
    bills = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code}).json()["data"]["list"]
    daren = [row for row in bills if row["shareTarget"] == "DAREN"]
    assert len(daren) == 1
    assert daren[0]["shareAmount"] == 1140
    assert daren[0]["shareBase"] == 9500
    assert daren[0]["ruleName"] == "TC-达人高优"
    assert daren[0]["status"] == "PENDING_AUDIT"
    assert all(row["ruleName"] != "TC-达人分成B" for row in bills)


def test_engine_ls1_daren_share_is_gross_times_ten_percent():
    """ST-05：LS-1 引擎达人分成 = 毛利 45,500 × 10% = ¥4,550。"""
    auth = headers()
    code = "IMS20261011DYS0001"
    account_id = 91001
    scope = {"platforms": ["DYS"], "accountIds": [account_id], "ipGroupIds": []}
    create_rule(
        auth,
        ruleName="LS-1达人毛利一成",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.1,
        priority=10,
        scope=scope,
    )
    seed_confirmed_session(code, account_id, 50000, 2000, topic="LS-1")
    saved = submit_engine(auth, code, commissionRate=0.05, adCost=5000, rechargeCost=1000, fixedCost=3000, sampleCost=0)
    assert saved["commissionAmount"] == 2500
    assert saved["shareDaren"] == 4550
    profit = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth).json()["data"]
    assert profit["grossProfit"] == 45500
    assert profit["netProfit"] == 31950
    bills = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code}).json()["data"]["list"]
    daren = [row for row in bills if row["shareTarget"] == "DAREN"]
    assert len(daren) == 1
    assert daren[0]["shareAmount"] == 4550
    assert daren[0]["shareBase"] == 45500
