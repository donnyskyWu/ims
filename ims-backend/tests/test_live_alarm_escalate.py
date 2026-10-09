"""#142 · LIVE 告警 30 分钟升级桩（ALM-R3）与 L3 钉钉/短信桩（ALM-R1），不外呼。"""

import os
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.core import SessionLocal
from app.live_alarm import AGED_SESSION, FRESH_L2_SESSION, FRESH_L3_SESSION, clock, ingest_alarm, stamp
from app.models import User, WorkMessage

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_seeded_rows_split_stub_and_thirty_minute_escalate():
    auth = headers()
    body = client.get(
        "/admin-api/ims/live/alarm/records",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50},
    ).json()
    assert body["code"] == 0
    rows = {item["sessionCode"]: item for item in body["data"]["list"]}

    aged = rows[AGED_SESSION]
    assert aged["alarmLevel"] == 3
    assert aged["escalated"] is True
    assert "DINGTALK_STUB" in aged["notifyChannels"]
    assert "SMS_STUB" in aged["notifyChannels"]
    assert "ESCALATE_STUB" in aged["notifyChannels"]

    fresh_l3 = rows[FRESH_L3_SESSION]
    assert fresh_l3["escalated"] is False
    assert "DINGTALK_STUB" in fresh_l3["notifyChannels"]
    assert "SMS_STUB" in fresh_l3["notifyChannels"]
    assert "ESCALATE_STUB" not in fresh_l3["notifyChannels"]

    fresh_l2 = rows[FRESH_L2_SESSION]
    assert fresh_l2["escalated"] is False
    assert fresh_l2["notifyChannels"] == ["IN_APP"]

    director = headers("live_director")
    messages = client.get(
        "/admin-api/ims/auth/workbench/messages",
        headers=director,
        params={"pageNo": 1, "pageSize": 20, "read": False},
    ).json()
    assert messages["code"] == 0
    hit = [item for item in messages["data"]["list"] if item["title"] == f"直播告警已升级：{AGED_SESSION}"]
    assert len(hit) == 1
    assert hit[0]["channel"] == "IN_APP"
    assert "未调用钉钉" in hit[0]["content"]
    assert "未调用短信" in hit[0]["content"]

    again = client.get(
        "/admin-api/ims/auth/workbench/messages",
        headers=director,
        params={"pageNo": 1, "pageSize": 20, "read": False},
    ).json()
    titles = [item["title"] for item in again["data"]["list"] if item["title"].startswith("直播告警已升级：")]
    assert titles.count(f"直播告警已升级：{AGED_SESSION}") == 1

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "live_director"))
        assert user is not None
        count = db.scalar(
            select(func.count()).select_from(WorkMessage).where(
                WorkMessage.user_id == user.id,
                WorkMessage.ref_type == "live_alarm_escalate",
                WorkMessage.title == f"直播告警已升级：{AGED_SESSION}",
            )
        )
        assert count == 1
    finally:
        db.close()


def test_dedup_within_ten_minutes_and_handle():
    code = "IMS20261009PY1001"
    moment = clock()
    db = SessionLocal()
    try:
        first = ingest_alarm(
            db,
            tenant_id=0,
            rule_id=0,
            rule_name="场观骤降",
            session_code=code,
            alarm_level=2,
            alarm_content="场观波动",
            occur_at=stamp(moment),
        )
        second = ingest_alarm(
            db,
            tenant_id=0,
            rule_id=0,
            rule_name="场观骤降",
            session_code=code,
            alarm_level=2,
            alarm_content="场观波动",
            occur_at=stamp(moment + timedelta(minutes=1)),
        )
        assert first.id == second.id
        assert second.merge_count == 2
        db.commit()
        record_id = second.id
    finally:
        db.close()

    auth = headers()
    listed = client.get(
        "/admin-api/ims/live/alarm/records",
        headers=auth,
        params={"sessionCode": code, "pageSize": 20},
    ).json()
    assert listed["code"] == 0
    assert listed["data"]["total"] == 1
    assert listed["data"]["list"][0]["mergeCount"] == 2
    assert "×2" in listed["data"]["list"][0]["alarmContent"]
    assert listed["data"]["list"][0]["escalated"] is False

    handled = client.put(
        f"/admin-api/ims/live/alarm/record/{record_id}/handle",
        headers=auth,
        json={"handleStatus": "HANDLED", "handleRemark": "已核对"},
    ).json()
    assert handled["code"] == 0
    again = client.put(
        f"/admin-api/ims/live/alarm/record/{record_id}/handle",
        headers=auth,
        json={"handleStatus": "FALSE_ALARM", "handleRemark": "重复"},
    ).json()
    assert again["code"] == 1001


def test_rule_rejects_illegal_expr_and_hot_updates():
    auth = headers()
    bad = client.post(
        "/admin-api/ims/live/alarm/rule",
        headers=auth,
        json={
            "ruleName": "非法窗口",
            "ruleType": "THRESHOLD",
            "ruleExpr": {"metric": "viewer_drop", "operator": "PCT_DROP", "threshold": 30, "window": 0},
            "level": 3,
            "notifyUsers": [1],
            "status": "ENABLED",
        },
    ).json()
    assert bad["code"] == 1009

    created = client.post(
        "/admin-api/ims/live/alarm/rule",
        headers=auth,
        json={
            "ruleName": "场观骤降热更新",
            "ruleType": "THRESHOLD",
            "ruleExpr": {"metric": "viewer_drop", "operator": "PCT_DROP", "threshold": 30, "window": 5},
            "level": 3,
            "notifyUsers": [1],
            "status": "ENABLED",
        },
    ).json()
    assert created["code"] == 0
    rule_id = created["data"]["id"]
    assert created["data"]["ruleExpr"]["threshold"] == 30

    updated = client.put(
        f"/admin-api/ims/live/alarm/rule/{rule_id}",
        headers=auth,
        json={
            "ruleName": "场观骤降热更新",
            "ruleType": "THRESHOLD",
            "ruleExpr": {"metric": "viewer_drop", "operator": "PCT_DROP", "threshold": 40, "window": 5},
            "level": 2,
            "notifyUsers": [1],
            "status": "ENABLED",
        },
    ).json()
    assert updated["code"] == 0

    listed = client.get("/admin-api/ims/live/alarm/rules", headers=auth, params={"keyword": "热更新"}).json()
    assert listed["code"] == 0
    hit = listed["data"]["list"][0]
    assert hit["ruleExpr"]["threshold"] == 40
    assert hit["level"] == 2
    assert "40" in hit["ruleExprSummary"]

    denied = client.delete(f"/admin-api/ims/live/alarm/rule/{rule_id}", headers=auth).json()
    assert denied["code"] == 1001
    removed = client.delete(
        f"/admin-api/ims/live/alarm/rule/{rule_id}",
        headers=auth,
        params={"confirmText": "DELETE"},
    ).json()
    assert removed["code"] == 0
    after = client.get("/admin-api/ims/live/alarm/rules", headers=auth, params={"keyword": "热更新"}).json()
    assert after["data"]["total"] == 0


def test_alarm_stats_shape():
    auth = headers()
    body = client.get("/admin-api/ims/live/alarm/stats", headers=auth).json()
    assert body["code"] == 0
    data = body["data"]
    assert set(data["byLevel"]) == {"1", "2", "3"}
    assert data["byLevel"]["3"] >= 2
    assert len(data["trend"]) == 7
    assert data["byHandleStatus"]["UNHANDLED"] >= 1
