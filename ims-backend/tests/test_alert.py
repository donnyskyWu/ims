import os
import uuid
from datetime import datetime, timedelta, timezone

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
    assert ack.json()["data"]["responseStatus"] == "CONFIRMED"

    handled = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "HANDLE"},
    )
    assert handled.json()["code"] == 0
    assert handled.json()["data"]["responseStatus"] == "RESOLVED"


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


def test_alert_rule_illegal_dsl_1009_and_valid_trigger_config():
    auth = headers()
    bad_op = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "dsl.bad.op",
            "ruleName": "非法操作符",
            "triggerConfig": {
                "source": "ims_fin_cost",
                "condition": {"field": "hours_since_approve", "op": "BAD", "value": 48},
            },
        },
    )
    assert bad_op.json()["code"] == 1009
    assert "1009" in bad_op.json()["msg"]

    bad_window = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "dsl.bad.window",
            "ruleName": "窗口越界",
            "triggerConfig": {
                "source": "ims_fin_cost",
                "condition": {"field": "hours_since_approve", "op": "GT", "value": 48},
                "mergeWindowMinutes": 1,
            },
        },
    )
    assert bad_window.json()["code"] == 1009

    bad_expr = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={"ruleCode": "dsl.bad.expr", "ruleName": "旧表达式", "thresholdExpr": "not a dsl"},
    )
    assert bad_expr.json()["code"] == 1009

    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "dsl.ok.cost",
            "ruleName": "合法 DSL",
            "triggerConfig": {
                "source": "ims_fin_cost",
                "condition": {"field": "hours_since_approve", "op": "GT", "value": 48},
                "mergeWindowMinutes": 30,
            },
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["thresholdExpr"] == "ims_fin_cost.hours_since_approve GT 48"


def test_alert_false_alarm_terminal_1167():
    auth = headers()
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "false.alarm.close",
            "ruleName": "误报关闭",
            "thresholdExpr": "delayMinutes>0",
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    assert run.json()["code"] == 0
    alert_no = run.json()["data"]["alertNo"]

    closed = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "FALSE_ALARM", "falseAlarmReason": "阈值过严"},
    )
    assert closed.json()["code"] == 0
    assert closed.json()["data"]["responseStatus"] == "FALSE_ALARM"
    assert "阈值过严" in closed.json()["data"]["content"]

    again = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"action": "HANDLE"},
    )
    assert again.json()["code"] == 1167

    created2 = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": "confirm.resolve.alias",
            "ruleName": "确认后处理",
            "thresholdExpr": "x>1",
            "enabled": True,
        },
    )
    rule2 = created2.json()["data"]["id"]
    alert2 = client.post(f"/admin-api/ims/alert/check/run/{rule2}", headers=auth).json()["data"]["alertNo"]
    confirmed = client.put(
        f"/admin-api/ims/alert/check/{alert2}/respond",
        headers=auth,
        json={"response": "CONFIRM"},
    )
    assert confirmed.json()["code"] == 0
    assert confirmed.json()["data"]["responseStatus"] == "CONFIRMED"
    resolved = client.put(
        f"/admin-api/ims/alert/check/{alert2}/respond",
        headers=auth,
        json={"response": "RESOLVE"},
    )
    assert resolved.json()["code"] == 0
    assert resolved.json()["data"]["responseStatus"] == "RESOLVED"
    terminal = client.put(
        f"/admin-api/ims/alert/check/{alert2}/respond",
        headers=auth,
        json={"response": "FALSE_ALARM"},
    )
    assert terminal.json()["code"] == 1167


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


def test_alert_confirm_repeat_rejected_then_resolve():
    auth = headers()
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": f"confirm.chain.{uuid.uuid4().hex[:8]}",
            "ruleName": "确认链",
            "thresholdExpr": "x>1",
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    alert_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]
    first = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"response": "CONFIRM"},
    )
    assert first.json()["data"]["responseStatus"] == "CONFIRMED"
    again = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"response": "CONFIRM"},
    )
    assert again.json()["code"] == 1001
    resolved = client.put(
        f"/admin-api/ims/alert/check/{alert_no}/respond",
        headers=auth,
        json={"response": "RESOLVE"},
    )
    assert resolved.json()["code"] == 0
    assert resolved.json()["data"]["responseStatus"] == "RESOLVED"


def test_alert_rule_put_hot_update_keeps_code():
    auth = headers()
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": f"edit.hot.{uuid.uuid4().hex[:8]}",
            "ruleName": "编辑前",
            "thresholdExpr": "delayMinutes>1",
            "level": 2,
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    updated = client.put(
        f"/admin-api/ims/alert/rule/{rule_id}",
        headers=auth,
        json={
            "ruleName": "编辑后",
            "thresholdExpr": "delayMinutes>9",
            "level": 3,
            "ruleCode": "should.not.apply",
        },
    )
    body = updated.json()
    assert body["code"] == 0
    assert body["data"]["ruleCode"] == created.json()["data"]["ruleCode"]
    assert body["data"]["ruleName"] == "编辑后"
    assert body["data"]["thresholdExpr"] == "delayMinutes>9"
    assert body["data"]["level"] == 3

    bad = client.put(
        f"/admin-api/ims/alert/rule/{rule_id}",
        headers=auth,
        json={
            "triggerConfig": {
                "source": "ims_fin_cost",
                "condition": {"field": "hours_since_approve", "op": "BAD", "value": 1},
            }
        },
    )
    assert bad.json()["code"] == 1009
    listed = client.get(
        "/admin-api/ims/alert/rule/list",
        headers=auth,
        params={"ruleName": "编辑后", "pageNo": 1, "pageSize": 5},
    )
    assert listed.json()["data"]["list"][0]["thresholdExpr"] == "delayMinutes>9"

    missing = client.put(
        "/admin-api/ims/alert/rule/99999999",
        headers=auth,
        json={"ruleName": "不存在"},
    )
    assert missing.json()["code"] == 1500


def test_alert_stats_overview_rates_and_range():
    auth = headers()
    code = f"stats.ov.{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": code,
            "ruleName": "统计窗口",
            "thresholdExpr": "delayMinutes>1",
            "level": 2,
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    open_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]
    resolved_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]
    closed = client.put(
        f"/admin-api/ims/alert/check/{resolved_no}/respond",
        headers=auth,
        json={"action": "HANDLE"},
    )
    assert closed.json()["data"]["responseStatus"] == "RESOLVED"

    from sqlalchemy import select

    from app.core import SessionLocal
    from app.models import AlertRecord

    window = datetime(1800, 1, 1) + timedelta(days=uuid.uuid4().int % 50000)
    day = window.strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        for alert_no, minutes in ((open_no, 0), (resolved_no, 12)):
            row = db.scalar(select(AlertRecord).where(AlertRecord.alert_no == alert_no))
            assert row is not None
            row.occurred_at = window.replace(hour=12, minute=0, second=0)
            row.updated_at = window.replace(hour=12, minute=minutes, second=0)
        db.commit()
    finally:
        db.close()

    bad_range = client.get(
        "/admin-api/ims/alert/stats/overview",
        headers=auth,
        params={"dateRange": "2020-02-02,2020-01-01"},
    )
    assert bad_range.json()["code"] == 1001

    overview = client.get(
        "/admin-api/ims/alert/stats/overview",
        headers=auth,
        params={"dateRange": f"{day},{day}"},
    )
    data = overview.json()["data"]
    assert overview.json()["code"] == 0
    assert data["totalAlertCount"] == 2
    assert data["byLevel"] == {"L1": 0, "L2": 2, "L3": 0}
    assert data["responseRate"] == 50.0
    assert data["resolutionRate"] == 50.0
    assert data["falseAlarmRate"] == 0.0
    assert data["deliveryRate"] == 100.0
    assert data["escalateRate"] == 50.0
    assert data["avgResponseMinutes"] == 12.0
    assert data["respondedCount"] == 1
    assert data["resolvedCount"] == 1


def _shift_alert(alert_no: str, occurred: datetime, updated: datetime | None = None) -> None:
    from sqlalchemy import select

    from app.core import SessionLocal
    from app.models import AlertRecord

    db = SessionLocal()
    try:
        row = db.scalar(select(AlertRecord).where(AlertRecord.alert_no == alert_no))
        assert row is not None
        row.occurred_at = occurred
        if updated is not None:
            row.updated_at = updated
        db.commit()
    finally:
        db.close()


def _enable_rule(auth: dict, code: str, level: int = 2) -> int:
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": code,
            "ruleName": code,
            "thresholdExpr": "delayMinutes>1",
            "level": level,
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    return created.json()["data"]["id"]


def test_alert_hit_stats_false_alarm_review_mark():
    auth = headers()
    code = f"hit.stats.{uuid.uuid4().hex[:8]}"
    rule_id = _enable_rule(auth, code, level=2)
    day = datetime(2099, 3, 2, 8, 0, 0)
    for _ in range(5):
        alert_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]
        closed = client.put(
            f"/admin-api/ims/alert/check/{alert_no}/respond",
            headers=auth,
            json={"response": "FALSE_ALARM", "falseAlarmReason": "阈值过紧"},
        )
        assert closed.json()["code"] == 0
        _shift_alert(alert_no, day, day + timedelta(minutes=4))

    listed = client.get(
        "/admin-api/ims/alert/rule/hit-stats",
        headers=auth,
        params={"dateRange": "2099-03-02,2099-03-02"},
    )
    assert listed.json()["code"] == 0
    rows = listed.json()["data"]
    assert len(rows) == 1
    assert rows[0]["ruleCode"] == code
    assert rows[0]["alertCount"] == 5
    assert rows[0]["falseAlarmCount"] == 5
    assert rows[0]["responseRate"] == 100.0
    assert rows[0]["lastHitAt"]

    bad = client.get(
        "/admin-api/ims/alert/rule/hit-stats",
        headers=auth,
        params={"dateRange": "2099-03-03,2099-03-02"},
    )
    assert bad.json()["code"] == 1001


def test_alert_weekly_report_suggestions_and_empty_week():
    auth = headers()
    code = f"weekly.{uuid.uuid4().hex[:8]}"
    rule_id = _enable_rule(auth, code, level=2)
    alert_no = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth).json()["data"]["alertNo"]
    _shift_alert(alert_no, datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=45))

    report = client.get("/admin-api/ims/alert/stats/weekly-report", headers=auth)
    body = report.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["totalAlerts"] == 1
    assert data["responseRate"] == 0.0
    assert data["topRules"][0]["ruleCode"] == code
    assert data["topRules"][0]["alertCount"] == 1
    assert len(data["weekRange"]) == 2
    assert data["escalatedAlerts"] == [
        {"alertNo": alert_no, "level": "L2", "currentLevel": 2},
    ]
    joined = " ".join(data["suggestions"])
    assert "BR-112" in joined
    assert "本地桩" in joined

    empty = client.get(
        "/admin-api/ims/alert/stats/weekly-report",
        headers=auth,
        params={"weekStart": "2099-06-01"},
    )
    assert empty.json()["code"] == 0
    assert empty.json()["data"]["totalAlerts"] == 0
    assert empty.json()["data"]["suggestions"] == []
    assert empty.json()["data"]["escalatedAlerts"] == []

    invalid = client.get(
        "/admin-api/ims/alert/stats/weekly-report",
        headers=auth,
        params={"weekStart": "not-a-date"},
    )
    assert invalid.json()["code"] == 1001


def test_alert_escalate_pending_levels_and_timeline_stub():
    auth = headers()
    normal = _enable_rule(auth, f"esc.n.{uuid.uuid4().hex[:8]}", level=2)
    severe = _enable_rule(auth, f"esc.s.{uuid.uuid4().hex[:8]}", level=3)
    fresh = client.post(f"/admin-api/ims/alert/check/run/{normal}", headers=auth).json()["data"]["alertNo"]
    mid = client.post(f"/admin-api/ims/alert/check/run/{normal}", headers=auth).json()["data"]["alertNo"]
    late = client.post(f"/admin-api/ims/alert/check/run/{normal}", headers=auth).json()["data"]["alertNo"]
    jumped = client.post(f"/admin-api/ims/alert/check/run/{severe}", headers=auth).json()["data"]["alertNo"]
    closed = client.post(f"/admin-api/ims/alert/check/run/{normal}", headers=auth).json()["data"]["alertNo"]
    done = client.put(
        f"/admin-api/ims/alert/check/{closed}/respond",
        headers=auth,
        json={"response": "RESOLVE", "handleRemark": "已处理"},
    )
    assert done.json()["code"] == 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _shift_alert(fresh, now - timedelta(minutes=10))
    _shift_alert(mid, now - timedelta(minutes=40))
    _shift_alert(late, now - timedelta(minutes=100))
    _shift_alert(jumped, now - timedelta(minutes=10))

    pending = client.get(
        "/admin-api/ims/alert/escalate/pending",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    assert pending.json()["code"] == 0
    rows = {item["alertNo"]: item for item in pending.json()["data"]["list"]}
    assert closed not in rows
    assert rows[fresh]["currentLevel"] == 1
    assert rows[fresh]["nextEscalateAt"]
    assert rows[mid]["currentLevel"] == 2
    assert rows[late]["currentLevel"] == 3
    assert rows[late]["nextEscalateAt"] == ""
    assert rows[jumped]["currentLevel"] == 2

    nxt = datetime.strptime(rows[fresh]["nextEscalateAt"], "%Y-%m-%dT%H:%M:%S+08:00").replace(
        tzinfo=timezone(timedelta(hours=8))
    )
    remain = (nxt - datetime.now(timezone(timedelta(hours=8)))).total_seconds() / 60.0
    assert 15 <= remain <= 25

    only_l1 = client.get(
        "/admin-api/ims/alert/escalate/pending",
        headers=auth,
        params={"currentLevel": 1, "pageNo": 1, "pageSize": 20},
    )
    l1_nos = [item["alertNo"] for item in only_l1.json()["data"]["list"]]
    assert l1_nos == [fresh]

    bad_level = client.get("/admin-api/ims/alert/escalate/pending", headers=auth, params={"currentLevel": 9})
    assert bad_level.json()["code"] == 1001

    timeline = client.get(f"/admin-api/ims/alert/escalate/timeline/{jumped}", headers=auth)
    assert timeline.json()["code"] == 0
    nodes = timeline.json()["data"]["timeline"]
    assert nodes[0]["skipped"] is True
    assert "ALR-E-R2" in nodes[0]["note"]
    assert timeline.json()["data"]["channelStub"].find("本地桩") >= 0
    assert timeline.json()["data"]["responseStatus"] == "OPEN"

    resolved_tl = client.get(f"/admin-api/ims/alert/escalate/timeline/{closed}", headers=auth)
    assert resolved_tl.json()["data"]["responseStatus"] == "RESOLVED"
    assert resolved_tl.json()["data"]["nextEscalateAt"] == ""

    missing = client.get("/admin-api/ims/alert/escalate/timeline/AL-MISSING", headers=auth)
    assert missing.json()["code"] == 1500

    stats = client.get("/admin-api/ims/alert/escalate/response-stats", headers=auth)
    assert stats.json()["code"] == 0
    assert stats.json()["data"]["target"] == 90.0
    assert stats.json()["data"]["totalAlerts"] == 5
    assert {item["level"] for item in stats.json()["data"]["byLevel"]} == {"L1", "L2", "L3"}

    trend = client.get("/admin-api/ims/alert/stats/response-rate", headers=auth)
    assert trend.json()["code"] == 0
    assert sum(item["alertCount"] for item in trend.json()["data"]) == 5


def test_alert_record_filters_receipt_and_my_alerts():
    auth = headers()
    code = f"receipt.filter.{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/admin-api/ims/alert/rule",
        headers=auth,
        json={
            "ruleCode": code,
            "ruleName": "回执筛选",
            "thresholdExpr": "delayMinutes>1",
            "level": 3,
            "enabled": True,
        },
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/alert/check/run/{rule_id}", headers=auth)
    body = run.json()
    assert body["code"] == 0
    alert_no = body["data"]["alertNo"]
    assert body["data"]["pushStatus"] == "DELIVERED"
    assert body["data"]["ruleCode"] == code
    channels = {item["channel"]: item for item in body["data"]["pushChannels"]}
    assert channels["WORKBENCH"]["success"] is True
    assert channels["DINGTALK"]["success"] is True
    assert channels["SMS"]["success"] is False

    from sqlalchemy import select

    from app.core import SessionLocal
    from app.models import AlertRecord

    window = datetime(1800, 1, 1) + timedelta(days=uuid.uuid4().int % 50000)
    day = window.strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        row = db.scalar(select(AlertRecord).where(AlertRecord.alert_no == alert_no))
        assert row is not None
        row.occurred_at = window.replace(hour=8, minute=0, second=0)
        db.commit()
    finally:
        db.close()

    listed = client.get(
        "/admin-api/ims/alert/check/records",
        headers=auth,
        params={
            "ruleCode": code,
            "level": "L3",
            "pushStatus": "DELIVERED",
            "responseStatus": "OPEN",
            "dateRange": f"{day},{day}",
            "pageNo": 1,
            "pageSize": 10,
        },
    )
    assert listed.json()["code"] == 0
    assert [row["alertNo"] for row in listed.json()["data"]["list"]] == [alert_no]

    missed = client.get(
        "/admin-api/ims/alert/check/records",
        headers=auth,
        params={"ruleCode": code, "pushStatus": "FAILED", "dateRange": f"{day},{day}"},
    )
    assert missed.json()["data"]["total"] == 0

    bad_level = client.get(
        "/admin-api/ims/alert/check/records",
        headers=auth,
        params={"level": "L9"},
    )
    assert bad_level.json()["code"] == 1001

    detail = client.get(f"/admin-api/ims/alert/check/{alert_no}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["escalationTimeline"] == []
    assert detail.json()["data"]["retryCount"] == 0
    assert detail.json()["data"]["sourceJumpUrl"] == "/ims/alert/rule"

    mine = client.get("/admin-api/ims/alert/check/my-alerts", headers=auth)
    assert mine.json()["code"] == 0
    hit = next(item for item in mine.json()["data"] if item["alertNo"] == alert_no)
    assert hit["isUnread"] is True

    db = SessionLocal()
    try:
        row = db.scalar(select(AlertRecord).where(AlertRecord.alert_no == alert_no))
        assert row is not None
        row.push_status = 3
        db.commit()
    finally:
        db.close()

    failed = client.get(
        "/admin-api/ims/alert/check/records",
        headers=auth,
        params={"ruleCode": code, "pushStatus": "FAILED", "dateRange": f"{day},{day}"},
    )
    assert failed.json()["data"]["list"][0]["alertNo"] == alert_no
    assert failed.json()["data"]["list"][0]["pushChannels"][0]["success"] is False

    stats = client.get(
        "/admin-api/ims/alert/check/delivery-stats",
        headers=auth,
        params={"dateRange": f"{day},{day}"},
    )
    assert stats.json()["code"] == 0
    payload = stats.json()["data"]
    assert payload["target"] == 99
    assert payload["totalShould"] == 1
    assert payload["totalDelivered"] == 0
    assert payload["failedAlerts"] == [{"alertNo": alert_no, "failedChannel": "SMS", "retryCount": 1}]

    again = client.get(f"/admin-api/ims/alert/check/{alert_no}", headers=auth)
    assert again.json()["data"]["retryCount"] == 1
    assert again.json()["data"]["pushStatus"] == "FAILED"

    todos = client.get("/admin-api/ims/home/todos", headers=auth, params={"pageNo": 1, "pageSize": 20})
    assert any(item.get("type") == "ALERT" and item.get("bizId") == alert_no for item in todos.json()["data"]["list"])
