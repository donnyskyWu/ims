"""BUG-047 引擎分成：核准后按规则生成分成单并从净利扣除。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.fin import net_profit_rate
from app.fin_policy import EDIT_COST_BEFORE_CONFIRM, commission_amount, net_rate_denominator
from app.main import app
from app.models import LiveReport, LiveSession
from tests.test_fin_share_rule import rule_body
from tests.test_live import headers

client = TestClient(app)


def test_fin_policy_matches_confirmed_rules():
    assert EDIT_COST_BEFORE_CONFIRM is True
    assert commission_amount(50000, 2000, 0.05) == 2500
    assert net_rate_denominator(50000, 2000) == 48000
    assert net_profit_rate(50000, 2000, 30940) == 64.46


def seed_confirmed_session(code: str, account_id: int, gmv: float, refund: float) -> None:
    db = SessionLocal()
    try:
        db.add(
            LiveSession(
                session_code=code,
                account_id=account_id,
                platform="DOUYIN",
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


def test_engine_daren_share_on_dys0003():
    auth = headers()
    code = "IMS20261011DYS0003"
    account_id = 91003
    scope = {"platforms": ["DYS"], "accountIds": [account_id], "ipGroupIds": []}
    create_rule(
        auth,
        ruleName="达人毛利一成",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.1,
        priority=10,
        scope=scope,
    )
    seed_confirmed_session(code, account_id, 10000, 0)
    saved = submit_engine(auth, code, commissionRate=0.525, fixedCost=8000)
    assert saved["shareDaren"] == 475
    assert saved["commissionAmount"] == 5250
    profit = client.get(f"/admin-api/ims/fin/profit/{code}", headers=auth).json()["data"]
    assert profit["grossProfit"] == 4750
    assert profit["netProfit"] == -3725
    bills = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code}).json()["data"]["list"]
    daren = [row for row in bills if row["shareTarget"] == "DAREN"]
    assert len(daren) == 1
    assert daren[0]["shareAmount"] == 475
    assert daren[0]["shareBase"] == 4750


def test_engine_keeps_higher_priority_rule_on_dys0004():
    auth = headers()
    code = "IMS20261011DYS0004"
    account_id = 91004
    scope = {"platforms": ["DYS"], "accountIds": [account_id], "ipGroupIds": []}
    create_rule(
        auth,
        ruleName="达人毛利一成",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.1,
        priority=10,
        scope=scope,
    )
    create_rule(
        auth,
        ruleName="达人毛利一二",
        shareTarget="DAREN",
        baseType="GROSS_PROFIT",
        fixedRate=0.12,
        priority=20,
        scope=scope,
        confirmConflict=True,
    )
    seed_confirmed_session(code, account_id, 10000, 0)
    saved = submit_engine(auth, code, commissionRate=0.05)
    assert saved["shareDaren"] == 1140
    bills = client.get("/admin-api/ims/fin/share/results", headers=auth, params={"sessionCode": code}).json()["data"]["list"]
    daren = [row for row in bills if row["shareTarget"] == "DAREN"]
    assert len(daren) == 1
    assert daren[0]["shareAmount"] == 1140
    assert daren[0]["ruleName"] == "达人毛利一二"
