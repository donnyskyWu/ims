"""#130 · 升级链路配置、待升级时间轴、非目标人 1166。"""

import os
import uuid
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import _ensure_cloned_user
from app.core import SessionLocal, utcnow
from app.main import app
from app.models import AlertRecord

client = TestClient(app)
PEER = "e2e_alert_peer"


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def ensure_peer() -> None:
    db = SessionLocal()
    try:
        _ensure_cloned_user(
            db,
            username=PEER,
            nickname="预警旁观者",
            mobile="13900000130",
            role_key="alert:peer",
            role_name="预警旁观者",
        )
        db.commit()
    finally:
        db.close()


def config_body(level1: int, level2: int, severe: int = 2) -> dict:
    return {
        "level1TimeoutMinutes": level1,
        "level2TimeoutMinutes": level2,
        "severeStartLevel": severe,
        "level1Receivers": {"dynamicTarget": "RESPONSIBLE_PERSON"},
        "level2Receivers": {"dynamicTarget": "DEPT_LEADER", "extraUserIds": []},
        "level3Receivers": {"roleCodes": ["R4", "R1"]},
    }


def test_escalate_chain_l3_skip_and_non_target_1166():
    admin = headers()
    ensure_peer()
    peer = headers(PEER)
    try:
        denied = client.put("/admin-api/ims/alert/escalate/config", headers=peer, json=config_body(30, 60))
        assert denied.status_code == 403
        assert denied.json()["code"] == 1008

        bad = client.put("/admin-api/ims/alert/escalate/config", headers=admin, json=config_body(30, 60, 1))
        assert bad.json()["code"] == 1001

        saved = client.put("/admin-api/ims/alert/escalate/config", headers=admin, json=config_body(0, 0))
        assert saved.json()["code"] == 0
        assert saved.json()["data"] is None

        code = f"esc.l2.{uuid.uuid4().hex[:8]}"
        created = client.post(
            "/admin-api/ims/alert/rule",
            headers=admin,
            json={
                "ruleCode": code,
                "ruleName": "升级立即到三级",
                "thresholdExpr": "delayMinutes>1",
                "level": 2,
                "enabled": True,
            },
        )
        assert created.json()["code"] == 0
        rule_id = created.json()["data"]["id"]
        alert_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=admin).json()["data"]["alertNo"]

        pending = client.get(
            "/admin-api/ims/alert/escalate/pending",
            headers=admin,
            params={"currentLevel": 3, "pageNo": 1, "pageSize": 50},
        )
        assert pending.json()["code"] == 0
        row = next(item for item in pending.json()["data"]["list"] if item["alertNo"] == alert_no)
        assert row["currentLevel"] == 3
        assert row["level"] == "L2"
        assert row["nextEscalateAt"] == ""

        axis = client.get(f"/admin-api/ims/alert/escalate/timeline/{alert_no}", headers=admin)
        levels = [node["escalationLevel"] for node in axis.json()["data"]["timeline"]]
        assert levels == [1, 2, 3]
        assert axis.json()["data"]["timeline"][0]["escalatedTo"][0]["roleLabel"] == "责任人"
        assert any(person["roleLabel"] == "系统管理员" for person in axis.json()["data"]["timeline"][2]["escalatedTo"])

        hidden = client.get(f"/admin-api/ims/alert/escalate/timeline/{alert_no}", headers=peer)
        assert hidden.json()["code"] == 1008

        blocked = client.put(
            f"/admin-api/ims/alert/check/{alert_no}/respond",
            headers=peer,
            json={"response": "CONFIRM"},
        )
        assert blocked.json()["code"] == 1166

        stopped = client.put(
            f"/admin-api/ims/alert/check/{alert_no}/respond",
            headers=admin,
            json={"response": "CONFIRM", "handleRemark": "停止升级"},
        )
        assert stopped.json()["code"] == 0
        assert stopped.json()["data"]["responseStatus"] == "CONFIRMED"
        assert stopped.json()["data"]["escalationStopped"] is True

        again = client.get(
            "/admin-api/ims/alert/escalate/pending",
            headers=admin,
            params={"pageNo": 1, "pageSize": 50},
        )
        assert all(item["alertNo"] != alert_no for item in again.json()["data"]["list"])

        client.put("/admin-api/ims/alert/escalate/config", headers=admin, json=config_body(30, 60, 2))
        severe_code = f"esc.l3.{uuid.uuid4().hex[:8]}"
        severe = client.post(
            "/admin-api/ims/alert/rule",
            headers=admin,
            json={
                "ruleCode": severe_code,
                "ruleName": "严重级二级起跳",
                "thresholdExpr": "delayMinutes>1",
                "level": 3,
                "enabled": True,
            },
        )
        severe_id = severe.json()["data"]["id"]
        severe_no = client.post(f"/admin-api/ims/alert/check/run/{severe_id}", headers=admin).json()["data"]["alertNo"]
        db = SessionLocal()
        try:
            record = db.query(AlertRecord).filter(AlertRecord.alert_no == severe_no).one()
            record.occurred_at = utcnow() - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        early = client.get(f"/admin-api/ims/alert/escalate/timeline/{severe_no}", headers=admin).json()["data"]
        assert early["currentLevel"] == 2
        assert [node["escalationLevel"] for node in early["timeline"]] == [2]

        db = SessionLocal()
        try:
            record = db.query(AlertRecord).filter(AlertRecord.alert_no == severe_no).one()
            record.occurred_at = utcnow() - timedelta(minutes=61)
            db.commit()
        finally:
            db.close()
        later = client.get(f"/admin-api/ims/alert/escalate/timeline/{severe_no}", headers=admin).json()["data"]
        assert later["currentLevel"] == 3
        assert [node["escalationLevel"] for node in later["timeline"]] == [2, 3]

        outsider = client.put(
            f"/admin-api/ims/alert/check/{severe_no}/respond",
            headers=peer,
            json={"response": "FALSE_ALARM"},
        )
        assert outsider.json()["code"] == 1166
        closed = client.put(
            f"/admin-api/ims/alert/check/{severe_no}/respond",
            headers=admin,
            json={"response": "FALSE_ALARM", "falseAlarmReason": "演练"},
        )
        assert closed.json()["data"]["responseStatus"] == "FALSE_ALARM"
        repeat = client.put(
            f"/admin-api/ims/alert/check/{severe_no}/respond",
            headers=admin,
            json={"response": "RESOLVE"},
        )
        assert repeat.json()["code"] == 1167
    finally:
        client.put("/admin-api/ims/alert/escalate/config", headers=admin, json=config_body(30, 60, 2))
