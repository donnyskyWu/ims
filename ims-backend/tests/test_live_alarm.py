"""#134 LIVE-003 规则命中、10 分钟去重、处置与只读统计。"""

import os
import uuid
from datetime import datetime, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account() -> tuple[int, int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="告警公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="告警组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="告警实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011134"),
            phone_enc=encrypt_text("13800001134"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600001134"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-ALARM-OK",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no=f"DY-ALARM-{uuid.uuid4().hex[:6]}",
            account_name="告警账号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        return account.id, person.id, phone.id
    finally:
        ops.close()


def register_and_report(auth: dict, viewer: int, topic: str = "pytest 告警专场") -> str:
    account_id, person_id, phone_id = seed_account()
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "realnamePersonId": person_id,
            "responsibleUserId": 1,
            "deviceAssetIds": [phone_id],
            "platform": "DOUYIN",
            "topic": topic,
            "planStartTime": "2026-10-09T20:00:00+08:00",
            "planEndTime": "2026-10-09T22:00:00+08:00",
        },
    )
    assert reg.json()["code"] == 0, reg.json()
    code = reg.json()["data"]["sessionCode"]
    start = datetime(2026, 10, 9, 20, 0)
    end = start + timedelta(hours=2)
    report = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json={
            "actualStart": start.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "actualEnd": end.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "gmv": 100,
            "refundAmount": 0,
            "orderCount": 2,
            "viewerCount": viewer,
            "peakOnline": 20,
            "newFans": 1,
            "adCost": 10,
        },
    )
    assert report.json()["code"] == 0, report.json()
    return code


def rule_body(**overrides) -> dict:
    body = {
        "ruleName": "场观过低",
        "ruleType": "THRESHOLD",
        "ruleExpr": {"metric": "viewer_count", "operator": "LT", "threshold": 500},
        "level": 2,
        "notifyUsers": [1],
        "status": "ENABLED",
    }
    body.update(overrides)
    return body


def test_illegal_expr_1009_then_hot_update_hits_and_dedup():
    auth = headers()
    bad = client.post(
        "/admin-api/ims/live/alarm/rule",
        headers=auth,
        json=rule_body(ruleExpr={"metric": "viewer_count", "operator": "BAD", "threshold": 1}),
    )
    assert bad.json()["code"] == 1009
    assert "1009" in bad.json()["msg"]

    created = client.post("/admin-api/ims/live/alarm/rule", headers=auth, json=rule_body(ruleExpr={"metric": "viewer_count", "operator": "LT", "threshold": 1}))
    assert created.json()["code"] == 0, created.json()
    rule_id = created.json()["data"]["id"]
    assert created.json()["data"]["ruleExprSummary"]

    code = register_and_report(auth, viewer=80)
    quiet = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": code})
    assert quiet.json()["code"] == 0
    assert quiet.json()["data"]["total"] == 0

    updated = client.put(
        f"/admin-api/ims/live/alarm/rule/{rule_id}",
        headers=auth,
        json=rule_body(),
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"] is None

    first = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": code, "alarmLevel": 2})
    assert first.json()["data"]["total"] == 1
    row = first.json()["data"]["list"][0]
    assert row["handleStatus"] == "UNHANDLED"
    assert row["mergeCount"] == 1
    assert "低于阈值" in row["alarmContent"]
    assert row["notifyChannel"] == "IN_APP"

    second = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": code})
    assert second.json()["data"]["total"] == 1
    assert second.json()["data"]["list"][0]["mergeCount"] == 2


def test_handle_then_terminal_and_stats_readonly():
    auth = headers()
    created = client.post("/admin-api/ims/live/alarm/rule", headers=auth, json=rule_body(ruleName="处置规则", level=3))
    rule_id = created.json()["data"]["id"]
    code = register_and_report(auth, viewer=10)
    listed = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": code})
    record_id = listed.json()["data"]["list"][0]["id"]

    handled = client.put(
        f"/admin-api/ims/live/alarm/record/{record_id}/handle",
        headers=auth,
        json={"handleStatus": "HANDLED", "handleRemark": "已核对场观"},
    )
    assert handled.json()["code"] == 0
    assert handled.json()["data"] is None

    again = client.put(
        f"/admin-api/ims/live/alarm/record/{record_id}/handle",
        headers=auth,
        json={"handleStatus": "FALSE_ALARM", "handleRemark": "重复"},
    )
    assert again.json()["code"] == 1001

    shown = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": code, "handleStatus": "HANDLED"})
    row = shown.json()["data"]["list"][0]
    assert row["handleRemark"] == "已核对场观"
    assert row["handlerName"]

    stats = client.get("/admin-api/ims/live/alarm/stats", headers=auth)
    data = stats.json()["data"]
    assert data["byLevel"]["3"] >= 1
    assert data["byHandleStatus"]["HANDLED"] >= 1
    assert len(data["trend"]) == 7
    assert any(item["ruleName"] == "处置规则" for item in data["byRule"])

    removed = client.delete(f"/admin-api/ims/live/alarm/rule/{rule_id}", headers=auth, params={"confirmText": "NO"})
    assert removed.json()["code"] == 1001
    gone = client.delete(f"/admin-api/ims/live/alarm/rule/{rule_id}", headers=auth, params={"confirmText": "DELETE"})
    assert gone.json()["code"] == 0
    listed_rules = client.get("/admin-api/ims/live/alarm/rules", headers=auth, params={"keyword": "处置规则"})
    assert listed_rules.json()["data"]["total"] == 0


def test_blacklist_event_hit_and_disabled_rule_skips():
    auth = headers()
    created = client.post(
        "/admin-api/ims/live/alarm/rule",
        headers=auth,
        json=rule_body(
            ruleName="违禁词",
            ruleType="EVENT",
            ruleExpr={"metric": "blacklist", "operator": "HIT", "threshold": 1},
            level=1,
        ),
    )
    assert created.json()["code"] == 0, created.json()
    rule_id = created.json()["data"]["id"]
    code = register_and_report(auth, viewer=900, topic="正常主题不含敏感词")
    missed = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": code, "alarmLevel": 1})
    assert missed.json()["data"]["total"] == 0

    banned = register_and_report(auth, viewer=900, topic="含违禁宣传")
    hit = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": banned})
    assert hit.json()["data"]["total"] == 1
    assert "违禁词命中" in hit.json()["data"]["list"][0]["alarmContent"]

    client.put(
        f"/admin-api/ims/live/alarm/rule/{rule_id}",
        headers=auth,
        json=rule_body(
            ruleName="违禁词",
            ruleType="EVENT",
            ruleExpr={"metric": "blacklist", "operator": "HIT", "threshold": 1},
            status="DISABLED",
        ),
    )
    other = register_and_report(auth, viewer=900, topic="再来一条违禁")
    skipped = client.get("/admin-api/ims/live/alarm/records", headers=auth, params={"sessionCode": other})
    assert skipped.json()["data"]["total"] == 0
