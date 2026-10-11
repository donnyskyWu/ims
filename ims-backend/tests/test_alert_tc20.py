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


def test_c059_trial_carries_object_and_inbox_once():
    from datetime import date, datetime, timedelta, timezone

    from sqlalchemy import func, select

    from app.core import SessionLocal
    from app.models import CertArchive, User, WorkMessage

    auth = headers()
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        tenant = admin.tenant_id or 0
        today = date.today()
        db.add(
            CertArchive(
                holder_name="CERT-FAR",
                cert_type="OTHER",
                expire_date=(today + timedelta(days=90)).isoformat(),
                status="EFFECTIVE",
                tenant_id=tenant,
            )
        )
        near = CertArchive(
            holder_name="CERT-B",
            cert_type="IDCARD",
            expire_date=(today + timedelta(days=10)).isoformat(),
            status="EFFECTIVE",
            tenant_id=tenant,
        )
        db.add(near)
        db.commit()
        cert_id = near.id
    finally:
        db.close()

    code = f"TC_C_CERT_EXPIRE.{uuid.uuid4().hex[:6]}"
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": code,
            "ruleName": "TC_C证件到期",
            "thresholdExpr": "days_left<=30",
            "level": 2,
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    first = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    body = first.json()
    assert body["code"] == 0
    data = body["data"]
    alert_no = data["alertNo"]
    assert data["objectLabel"] == "CERT-B · IDCARD"
    assert data["sourceRefType"] == "CERT"
    assert data["sourceRefId"] == cert_id
    assert "对象：CERT-B · IDCARD" in data["content"]
    assert data["pushStatus"] == "DELIVERED"
    channels = {item["channel"]: item for item in data["pushChannels"]}
    assert channels["WORKBENCH"]["success"] is True
    assert channels["DINGTALK"]["stub"] is True
    assert channels["DINGTALK"]["outbound"] is False

    detail = client.get(f"/admin-api/ims/alert/check/{alert_no}", headers=auth)
    assert detail.json()["data"]["objectLabel"] == "CERT-B · IDCARD"
    assert detail.json()["data"]["sourceJumpUrl"] == "/ims/corp/resource/certificate"

    inbox = client.get(
        "/admin-api/ims/auth/workbench/messages",
        headers=auth,
        params={"channel": "IN_APP", "keyword": alert_no, "pageSize": 10},
    )
    messages = inbox.json()["data"]["list"]
    assert len(messages) == 1
    assert messages[0]["channel"] == "IN_APP"
    assert messages[0]["sourceModule"] == "ALERT"
    assert "CERT-B" in messages[0]["content"]

    db = SessionLocal()
    try:
        ding = db.scalar(
            select(func.count())
            .select_from(WorkMessage)
            .where(WorkMessage.ref_type == "alert", WorkMessage.channel == "DINGTALK", WorkMessage.title.like(f"%{alert_no}%"))
        )
        assert int(ding or 0) == 0
    finally:
        db.close()

    second = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    assert second.json()["code"] == 0
    assert second.json()["data"]["alertNo"] == alert_no
    assert second.json()["data"]["mergedCount"] == 2
    again = client.get(
        "/admin-api/ims/auth/workbench/messages",
        headers=auth,
        params={"channel": "IN_APP", "keyword": alert_no, "pageSize": 10},
    )
    assert again.json()["data"]["total"] == 1

    db = SessionLocal()
    try:
        from app.models import AlertRecord

        row = db.scalar(select(AlertRecord).where(AlertRecord.alert_no == alert_no))
        assert row is not None
        row.occurred_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=31)
        db.commit()
    finally:
        db.close()
    third = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    assert third.json()["code"] == 0
    assert third.json()["data"]["alertNo"] != alert_no
    assert third.json()["data"]["objectLabel"] == "CERT-B · IDCARD"

    plain = f"plain.{uuid.uuid4().hex[:8]}"
    other = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": plain, "ruleName": "回执筛选", "thresholdExpr": "delayMinutes>1", "level": 3, "enabled": True},
    )
    other_id = other.json()["data"]["id"]
    left = client.post(f"/admin-api/ims/alert/check/run/{other_id}", headers=auth).json()["data"]
    right = client.post(f"/admin-api/ims/alert/check/run/{other_id}", headers=auth).json()["data"]
    assert left["alertNo"] != right["alertNo"]
    assert left["sourceRefType"] == "MANUAL"
    assert left["objectLabel"] == ""
    jumped = client.get(f"/admin-api/ims/alert/check/{left['alertNo']}", headers=auth)
    assert jumped.json()["data"]["sourceJumpUrl"] == "/ims/alert/rule"
    noted = client.get(
        "/admin-api/ims/auth/workbench/messages",
        headers=auth,
        params={"channel": "IN_APP", "keyword": left["alertNo"], "pageSize": 5},
    )
    assert noted.json()["data"]["total"] == 1


def test_c060_handle_drawer_flow_keeps_direct_resolve():
    auth = headers()
    code = f"c060.{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": code, "ruleName": "处置抽屉", "thresholdExpr": "delayMinutes>1", "level": 2, "enabled": True},
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    alert_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]

    handling = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "CONFIRM", "handleRemark": "现场已核对"},
    )
    assert handling.json()["code"] == 0
    assert handling.json()["data"]["responseStatus"] == "CONFIRMED"
    assert handling.json()["data"]["escalationStopped"] is True
    assert "处理说明：现场已核对" in handling.json()["data"]["content"]

    detail = client.get(f"/admin-api/ims/alert/check/{alert_no}", headers=auth).json()["data"]
    labels = [node["label"] for node in detail["dispositionTimeline"]]
    assert labels == ["触发", "处置"]
    assert detail["dispositionTimeline"][1]["note"] == "现场已核对"

    recovered = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "RESOLVE", "handleRemark": "已恢复"},
    )
    assert recovered.json()["code"] == 0
    assert recovered.json()["data"]["responseStatus"] == "RESOLVED"
    again = client.get(f"/admin-api/ims/alert/check/{alert_no}", headers=auth).json()["data"]
    assert [node["label"] for node in again["dispositionTimeline"]] == ["触发", "处置", "恢复"]

    direct = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]
    closed = client.put(
        f"/admin-api/ims/alert/check/{direct}/respond",
        headers=auth,
        json={"action": "HANDLE", "handleRemark": "直接处理"},
    )
    assert closed.json()["code"] == 0
    assert closed.json()["data"]["responseStatus"] == "RESOLVED"


def test_c056_rule_fields_and_finance_module():
    auth = headers()
    listed = client.get("/admin-api/ims/alert/rule/list", headers=auth, params={"pageNo": 1, "pageSize": 5})
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["financeOnly"] is False
    assert "直播管理" in listed.json()["data"]["monitorModules"]
    assert "财务核算" in listed.json()["data"]["monitorModules"]

    code = f"c056.{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": code,
            "ruleName": "证件规则字段",
            "thresholdExpr": "days_left<=30",
            "level": 2,
            "enabled": False,
            "sourceModule": "证件档案",
            "notifyMode": "BOTH",
            "ruleDesc": "证件剩余天数",
        },
    )
    assert created.json()["code"] == 0
    data = created.json()["data"]
    assert data["sourceModule"] == "证件档案"
    assert data["notifyMode"] == "BOTH"
    assert data["notifyModeLabel"] == "站内+钉钉"
    assert data["ruleDesc"] == "证件剩余天数"
    assert data["escalationChain"] == "30/60 分钟 · 严重从二级起跳"

    bad = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": f"{code}.bad", "ruleName": "非法对象", "sourceModule": "不存在的模块", "enabled": False},
    )
    assert bad.json()["code"] == 1001

    omitted = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": f"{code}.plain", "ruleName": "不带来源", "thresholdExpr": "delayMinutes>1", "enabled": False},
    )
    assert omitted.json()["code"] == 0
    assert omitted.json()["data"]["sourceModule"] == ""

    fin_login = client.post("/admin-api/ims/auth/login", json={"username": "e2e_acct_r3", "password": "Admin@123"})
    assert fin_login.json()["code"] == 0
    fin = {"Authorization": f"Bearer {fin_login.json()['data']['accessToken']}"}
    fin_list = client.get("/admin-api/ims/alert/rule/list", headers=fin, params={"pageNo": 1, "pageSize": 5})
    assert fin_list.json()["code"] == 0
    assert fin_list.json()["data"]["financeOnly"] is True
    assert fin_list.json()["data"]["monitorModules"] == ["财务核算"]
    denied = client.post(
        "/admin-api/ims/alert/rule",
        headers=fin,
        json={
            "ruleCode": f"{code}.live",
            "ruleName": "财务越权对象",
            "thresholdExpr": "delayMinutes>1",
            "sourceModule": "直播管理",
            "enabled": False,
        },
    )
    assert denied.json()["code"] == 1001
    allowed = client.post(
        "/admin-api/ims/alert/rule",
        headers=fin,
        json={
            "ruleCode": f"{code}.fin",
            "ruleName": "财务成本规则",
            "thresholdExpr": "delayMinutes>1",
            "sourceModule": "财务核算",
            "notifyMode": "IN_APP",
            "enabled": False,
        },
    )
    assert allowed.json()["code"] == 0
    assert allowed.json()["data"]["sourceModule"] == "财务核算"


def test_c056_backfill_cert_module():
    """旧规则 source_module 为空时，列表按编码归到证件档案并写回。创建响应仍为空。"""
    auth = headers()
    suffix = uuid.uuid4().hex[:6]
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": f"TC_C_CERT_EXPIRE.{suffix}",
            "ruleName": "证件到期",
            "thresholdExpr": "days_left<=30",
            "enabled": False,
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["sourceModule"] == ""

    plain = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": f"plain.delay.{suffix}",
            "ruleName": "不带来源",
            "thresholdExpr": "delayMinutes>1",
            "enabled": False,
        },
    )
    assert plain.json()["code"] == 0

    listed = client.get(
        "/admin-api/ims/alert/rule/list",
        headers=auth,
        params={"ruleName": "证件到期", "pageNo": 1, "pageSize": 20},
    )
    body = listed.json()
    assert body["code"] == 0
    row = next(item for item in body["data"]["list"] if item["ruleCode"] == f"TC_C_CERT_EXPIRE.{suffix}")
    assert row["sourceModule"] == "证件档案"

    again = client.get(
        "/admin-api/ims/alert/rule/list",
        headers=auth,
        params={"ruleName": "不带来源", "pageNo": 1, "pageSize": 20},
    )
    kept = next(item for item in again.json()["data"]["list"] if item["ruleCode"] == f"plain.delay.{suffix}")
    assert kept["sourceModule"] == ""


def test_c057_rule_name_unique_1165():
    auth = headers()
    suffix = uuid.uuid4().hex[:8]
    first = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": f"c057.a.{suffix}", "ruleName": f"同名规则{suffix}", "thresholdExpr": "delayMinutes>1", "enabled": False},
    )
    assert first.json()["code"] == 0
    second = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": f"c057.b.{suffix}", "ruleName": f"同名规则{suffix}", "thresholdExpr": "delayMinutes>1", "enabled": False},
    )
    assert second.json()["code"] == 1165
    assert "规则名称已存在" in second.json()["msg"]

    other = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": f"c057.c.{suffix}", "ruleName": f"另一个{suffix}", "thresholdExpr": "delayMinutes>1", "enabled": False},
    )
    assert other.json()["code"] == 0
    renamed = client.put(
        f"/admin-api/ims/alert/rule/{other.json()['data']['id']}",
        headers=auth,
        json={"ruleName": f"同名规则{suffix}"},
    )
    assert renamed.json()["code"] == 1165
    kept = client.put(
        f"/admin-api/ims/alert/rule/{first.json()['data']['id']}",
        headers=auth,
        json={"ruleName": f"同名规则{suffix}", "thresholdExpr": "delayMinutes>2"},
    )
    assert kept.json()["code"] == 0
    assert kept.json()["data"]["thresholdExpr"] == "delayMinutes>2"
