import json
import os
import time
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import Base, SessionLocal, engine, utcnow
from app.dingtalk_crypto import pack
from app.main import app, init_db
from app.models import OrgEvent, Role, RolePerm, User, UserDept, UserMapping, UserRole
from app.org_sync import process_due


client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def post_event(payload: dict):
    body, headers = pack(json.dumps(payload, ensure_ascii=False), "1700000000000", "nonce-org")
    return client.post("/admin-api/ims/auth/org/event", json=body, headers=headers)


def hire(event_id="evt-hire-1", ding="dt-100", mobile="13700001111", dept=3) -> dict:
    return {
        "eventType": "hire",
        "dingtalkEventId": event_id,
        "unionId": "union-100",
        "payloadJson": {
            "dingtalkUserId": ding,
            "nickname": "新人",
            "mobile": mobile,
            "deptIds": [dept],
            "deptNames": ["内容部"],
            "afterDept": "内容部",
        },
    }


def mapping_count(db) -> int:
    """种子里的技能部门映射不算本次事件写入。"""
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserMapping)
            .where(UserMapping.dingtalk_user_id != "dt-e2e-air-dept")
        )
        or 0
    )


def consume(now=None) -> None:
    db = SessionLocal()
    try:
        process_due(db, now=now)
        db.commit()
    finally:
        db.close()


def test_event_is_signed_then_queued_without_writing_user():
    res = post_event(hire())
    assert res.json()["code"] == 0
    assert res.json()["data"] is None
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(OrgEvent)) == 1
        assert db.scalar(select(User).where(User.dingtalk_user_id == "dt-100")) is None
        assert mapping_count(db) == 0
    finally:
        db.close()


def test_bad_signature_does_not_enqueue():
    body, headers = pack(json.dumps(hire()), "1700000000000", "nonce-org")
    headers["sign"] = "0" * 40
    res = client.post("/admin-api/ims/auth/org/event", json=body, headers=headers)
    assert res.json()["code"] == 1001
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(OrgEvent)) == 0
    finally:
        db.close()


def test_idempotent_key_writes_one_local_user():
    assert post_event(hire()).json()["code"] == 0
    assert post_event(hire()).json()["code"] == 0
    other = hire()
    other["eventType"] = "dept_change"
    other["dingtalkEventId"] = "evt-hire-1"
    assert post_event(other).json()["code"] == 0
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(OrgEvent)) == 2
        process_due(db)
        db.commit()
        assert mapping_count(db) == 1
        user = db.scalar(select(User).where(User.dingtalk_user_id == "dt-100", User.deleted == 0))
        assert user is not None
        assert user.nickname == "新人"
        assert user.status == "ENABLED"
        depts = list(db.scalars(select(UserDept.dept_id).where(UserDept.user_id == user.id)).all())
        assert depts == [3]
    finally:
        db.close()
    token = login()
    page = client.get("/admin-api/ims/auth/org/users", headers=auth(token))
    body = page.json()["data"]["list"][0]
    assert body["mobileMasked"] == "137****1111"
    assert body["syncStatus"] == "SUCCESS"
    assert body["deadLetter"] is False


def test_retry_sixteen_times_then_dead_letter():
    payload = {"eventType": "hire", "dingtalkEventId": "evt-bad", "unionId": "", "payloadJson": {}}
    assert post_event(payload).json()["code"] == 0
    db = SessionLocal()
    try:
        moment = utcnow()
        event = db.scalar(select(OrgEvent).where(OrgEvent.dingtalk_event_id == "evt-bad"))
        for index in range(16):
            process_due(db, now=moment)
            db.commit()
            db.refresh(event)
            assert event.retry_count == index + 1
            if index < 15:
                expect = (60, 300, 900, 3600)[index if index < 3 else 3]
                delta = (event.next_retry_at - moment).total_seconds()
                assert abs(delta - expect) < 2
                moment = event.next_retry_at
            else:
                assert event.dead_letter == 1
                assert event.alert_code == "ims.org.dead_letter"
                assert event.next_retry_at is None
        process_due(db, now=moment + timedelta(days=3))
        db.commit()
        db.refresh(event)
        assert event.retry_count == 16
        assert event.dead_letter == 1
        assert mapping_count(db) == 0
    finally:
        db.close()


def test_reconcile_only_r1_and_metrics_br001():
    token = login()
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth(token),
        json={"username": "r4user", "nickname": "只读", "mobile": "13600002222", "password": "Pass@123"},
    )
    assert created.json()["code"] == 0
    r4 = login("r4user", "Pass@123")
    db = SessionLocal()
    try:
        reader = Role(role_name="只读", role_key="ops:reader", data_scope="ALL", status="ENABLED", source="MANUAL")
        db.add(reader)
        db.flush()
        db.add(RolePerm(role_id=reader.id, module_code="system", perm_code="system:user:query", perm_level="R"))
        reader_user = db.scalar(select(User).where(User.username == "r4user"))
        db.add(UserRole(user_id=reader_user.id, role_id=reader.id, tenant_id=0))
        db.commit()
    finally:
        db.close()
    denied = client.post("/admin-api/ims/auth/org/reconcile", headers=auth(r4), json={})
    assert denied.status_code == 403
    assert denied.json()["code"] == 403

    accepted = client.post("/admin-api/ims/auth/org/reconcile", headers=auth(token), json={})
    assert accepted.json()["code"] == 0
    assert accepted.json()["data"]["reconcileTaskId"].startswith("rc-")
    events = client.get("/admin-api/ims/auth/org/events", headers=auth(token)).json()["data"]
    assert events["total"] >= 1
    assert any(row["eventType"] == "reconcile" for row in events["list"])

    assert post_event(hire()).json()["code"] == 0
    consume()
    green = client.get("/admin-api/ims/auth/org/sync-metrics", headers=auth(token)).json()["data"]
    assert green["delayMillis"] < 300000
    assert green["level"] == "green"
    assert "avgSyncDelayMinutes" in green
    assert "successRate" in green

    db = SessionLocal()
    try:
        event = db.scalar(select(OrgEvent).where(OrgEvent.event_type == "hire"))
        event.created_at = event.synced_at - timedelta(minutes=10)
        db.commit()
    finally:
        db.close()
    red = client.get("/admin-api/ims/auth/org/sync-metrics", headers=auth(token)).json()["data"]
    assert red["delayMillis"] >= 300000
    assert red["level"] == "red"


def test_transfer_records_buffer_and_resign_freezes_local_user():
    assert post_event(hire()).json()["code"] == 0
    consume()
    transfer = {
        "eventType": "transfer",
        "dingtalkEventId": "evt-transfer-1",
        "unionId": "union-100",
        "beforeDept": "内容部",
        "payloadJson": {
            "dingtalkUserId": "dt-100",
            "deptIds": [8],
            "deptNames": ["直播部"],
            "beforeDept": "内容部",
            "afterDept": "直播部",
        },
    }
    assert post_event(transfer).json()["code"] == 0
    consume()
    db = SessionLocal()
    try:
        mapping = db.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt-100"))
        assert list(mapping.dept_ids) == [8]
        assert list(mapping.prev_dept_ids) == [3]
        assert mapping.buffer_until is not None
        assert mapping.buffer_until - mapping.last_sync_time >= timedelta(hours=23)
        user = db.get(User, mapping.user_id)
        username = user.username
    finally:
        db.close()

    token = login()
    user_id = client.get("/admin-api/ims/auth/org/users", headers=auth(token)).json()["data"]["list"][0]["userId"]
    changed = client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=auth(token),
        json={"password": "Pass@123"},
    )
    assert changed.json()["code"] == 0
    resign = {
        "eventType": "resign",
        "dingtalkEventId": "evt-resign-1",
        "unionId": "union-100",
        "payloadJson": {"dingtalkUserId": "dt-100"},
    }
    assert post_event(resign).json()["code"] == 0
    consume()
    locked = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Pass@123"})
    assert locked.json()["code"] == 1006
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.dingtalk_user_id == "dt-100"))
        assert user.status == "FROZEN"
    finally:
        db.close()


def test_callback_ack_stays_under_half_second():
    durations = []
    for index in range(30):
        payload = hire(event_id=f"evt-fast-{index}", ding=f"dt-fast-{index}", mobile=f"136{index:08d}")
        started = time.perf_counter()
        res = post_event(payload)
        durations.append(time.perf_counter() - started)
        assert res.json()["code"] == 0
    durations.sort()
    p95 = durations[max(int(len(durations) * 0.95) - 1, 0)]
    assert p95 < 0.5
    db = SessionLocal()
    try:
        assert mapping_count(db) == 0
    finally:
        db.close()
