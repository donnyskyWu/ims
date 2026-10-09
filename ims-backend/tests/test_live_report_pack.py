"""#80 · 下播缺字段 1046 / 更正单 1047 / 超过 24 小时督办 1048。"""

import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.crypto import encrypt_text
from app.main import app
from app.models import LiveAlarmRecord, LiveReport, LiveSession, Todo, User, WorkMessage
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

client = TestClient(app)
BJ = timezone(timedelta(hours=8))


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account() -> tuple[int, int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="下播公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="下播组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="下播实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011046"),
            phone_enc=encrypt_text("13800001046"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600001046"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-LIVE-1046",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-PY-1046",
            account_name="下播号",
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


def register(auth: dict, account_id: int, person_id: int, phone_id: int) -> str:
    body = {
        "accountId": account_id,
        "realnamePersonId": person_id,
        "responsibleUserId": 1,
        "deviceAssetIds": [phone_id],
        "platform": "DOUYIN",
        "topic": "下播闭环专场",
        "planStartTime": "2026-10-08T20:00:00+08:00",
        "planEndTime": "2026-10-08T22:00:00+08:00",
    }
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=body,
    )
    assert created.json()["code"] == 0, created.json()
    assert created.json()["data"]["sessionStatus"] == "APPROVED"
    return created.json()["data"]["sessionCode"]


def full_report(**overrides) -> dict:
    body = {
        "actualStart": "2026-10-08T20:00:00+08:00",
        "actualEnd": "2026-10-08T22:00:00+08:00",
        "gmv": 100.126,
        "refundAmount": 1.2,
        "orderCount": 4,
        "viewerCount": 80,
        "peakOnline": 20,
        "newFans": 3,
        "adCost": 10,
    }
    body.update(overrides)
    return body


def test_missing_fields_then_submit_rounds_money():
    auth = headers()
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)
    missing = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(gmv=None, viewerCount=None),
    )
    assert missing.json()["code"] == 1046
    assert set(missing.json()["data"]["missing"]) == {"gmv", "viewerCount"}
    still = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth)
    assert still.json()["data"]["sessionStatus"] == "APPROVED"
    assert still.json()["data"]["report"] is None

    negative = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json=full_report(refundAmount=-1),
    )
    assert negative.json()["code"] == 1001

    submitted = client.post(f"/admin-api/ims/live/report/{code}", headers=auth, json=full_report())
    assert submitted.json()["code"] == 0, submitted.json()
    data = submitted.json()["data"]
    assert data["entryStatus"] == "SUBMITTED"
    assert data["gmv"] == 100.13
    assert data["durationMinutes"] == 120
    assert data["avgOrderValue"] == 25.03
    ended = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth)
    assert ended.json()["data"]["sessionStatus"] == "ENDED"


def test_readonly_1047_and_correction_keeps_status():
    auth = headers()
    account_id, person_id, phone_id = seed_account()
    code = register(auth, account_id, person_id, phone_id)
    submitted = client.post(f"/admin-api/ims/live/report/{code}", headers=auth, json=full_report(gmv=200))
    assert submitted.json()["code"] == 0, submitted.json()

    blocked_put = client.put(f"/admin-api/ims/live/report/{code}", headers=auth, json=full_report(gmv=1))
    assert blocked_put.json()["code"] == 1047
    blocked_post = client.post(f"/admin-api/ims/live/report/{code}", headers=auth, json=full_report(gmv=1))
    assert blocked_post.json()["code"] == 1047
    unchanged = client.get(f"/admin-api/ims/live/report/{code}", headers=auth)
    assert unchanged.json()["data"]["gmv"] == 200
    assert unchanged.json()["data"]["entryStatus"] == "SUBMITTED"

    no_reason = client.post(
        f"/admin-api/ims/live/report/{code}/correction",
        headers=auth,
        json={**full_report(gmv=80), "correctionReason": "  "},
    )
    assert no_reason.json()["code"] == 1001
    missing = client.post(
        f"/admin-api/ims/live/report/{code}/correction",
        headers=auth,
        json={**full_report(gmv=None), "correctionReason": "漏了 GMV"},
    )
    assert missing.json()["code"] == 1046

    corrected = client.post(
        f"/admin-api/ims/live/report/{code}/correction",
        headers=auth,
        json={**full_report(gmv=80.2), "correctionReason": "客单复核"},
    )
    assert corrected.json()["code"] == 0, corrected.json()
    trace = corrected.json()["data"]
    assert trace["correctionId"]
    assert trace["before"]["gmv"] == 200
    assert trace["after"]["gmv"] == 80.2
    detail = client.get(f"/admin-api/ims/live/report/{code}", headers=auth)
    assert detail.json()["data"]["gmv"] == 80.2
    assert detail.json()["data"]["entryStatus"] == "SUBMITTED"
    assert detail.json()["data"]["corrections"][0]["correctionReason"] == "客单复核"

    confirmed = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0
    after_confirm = client.put(f"/admin-api/ims/live/report/{code}", headers=auth, json=full_report(gmv=1))
    assert after_confirm.json()["code"] == 1047
    again = client.post(
        f"/admin-api/ims/live/report/{code}/correction",
        headers=auth,
        json={**full_report(gmv=90), "correctionReason": "核准后仍留痕"},
    )
    assert again.json()["code"] == 0, again.json()
    final = client.get(f"/admin-api/ims/live/report/{code}", headers=auth)
    assert final.json()["data"]["entryStatus"] == "CONFIRMED"
    assert final.json()["data"]["gmv"] == 90
    assert len(final.json()["data"]["corrections"]) == 2


def _insert_ended(code: str, hours_ago: int) -> int:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        assert admin is not None
        ended = datetime.now(BJ) - timedelta(hours=hours_ago)
        started = ended - timedelta(hours=2)
        start_iso = started.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        ended_iso = ended.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        row = db.scalar(select(LiveSession).where(LiveSession.session_code == code))
        if row is None:
            row = LiveSession(
                session_code=code,
                account_id=1,
                account_no="AC-PY-1048",
                realname_person_id=1,
                realname_name="下播实名人",
                responsible_user_id=admin.id,
                device_asset_ids="[]",
                platform="DOUYIN",
                topic="超时未录",
                plan_start_time=start_iso,
                plan_end_time=ended_iso,
                session_status="ENDED",
                actual_start=start_iso,
                actual_end=ended_iso,
                creator=admin.id,
                tenant_id=admin.tenant_id or 0,
                football_sync_status="UNLINKED",
            )
            db.add(row)
        else:
            row.deleted = 0
            row.session_status = "ENDED"
            row.responsible_user_id = admin.id
            row.actual_start = start_iso
            row.actual_end = ended_iso
            row.plan_start_time = start_iso
            row.plan_end_time = ended_iso
            row.topic = "超时未录"
        report = db.scalar(select(LiveReport).where(LiveReport.session_code == code))
        if report is not None:
            report.deleted = 1
            report.entry_status = "DRAFT"
        db.commit()
        return row.id
    finally:
        db.close()


def test_overdue_pending_hints_1048_and_creates_supervision_once():
    auth = headers()
    session_id = _insert_ended("IMS20261006DYS1048", 48)
    _insert_ended("IMS20261006DYS1040", 2)

    pending = client.get("/admin-api/ims/live/report/pending", headers=auth, params={"overdueOnly": True})
    body = pending.json()
    assert body["code"] == 1048
    assert body["msg"] == "24小时录入超时督办"
    assert body["data"]["hintCode"] == 1048
    codes = [item["sessionCode"] for item in body["data"]["list"]]
    assert "IMS20261006DYS1048" in codes
    assert "IMS20261006DYS1040" not in codes
    hit = next(item for item in body["data"]["list"] if item["sessionCode"] == "IMS20261006DYS1048")
    assert hit["overdueHours"] >= 48
    assert hit["overdue"] is True
    assert hit["urgeChannels"] == ["IN_APP", "DINGTALK", "SMS"]
    assert body["data"]["overdueCount"] >= 1

    db = SessionLocal()
    try:
        todos = db.scalars(
            select(Todo).where(Todo.task_type == "live_report_overdue", Todo.ref_id == session_id, Todo.status == "PENDING")
        ).all()
        assert len(todos) == 1
        assert "1048" in todos[0].title
        messages = db.scalars(
            select(WorkMessage).where(WorkMessage.ref_type == "live_report_overdue", WorkMessage.ref_id == session_id)
        ).all()
        by_channel = {item.channel: item for item in messages}
        assert set(by_channel) == {"IN_APP", "DINGTALK", "SMS"}
        assert by_channel["IN_APP"].title.startswith("下播超时督办 1048")
        assert "钉钉本地桩，未外发" in by_channel["DINGTALK"].content
        assert "短信本地桩，未外发" in by_channel["SMS"].content
        alarms = db.scalars(
            select(LiveAlarmRecord).where(
                LiveAlarmRecord.session_code == "IMS20261006DYS1048",
                LiveAlarmRecord.rule_name == "下播超时督办",
                LiveAlarmRecord.deleted == 0,
            )
        ).all()
        assert len(alarms) == 1
        assert "1048" in alarms[0].alarm_content
    finally:
        db.close()

    again = client.get("/admin-api/ims/live/report/pending", headers=auth, params={"overdueOnly": True})
    assert again.json()["code"] == 1048
    db = SessionLocal()
    try:
        todo_count = db.scalar(
            select(func.count()).select_from(Todo).where(Todo.task_type == "live_report_overdue", Todo.ref_id == session_id)
        )
        assert todo_count == 1
        message_count = db.scalar(
            select(func.count()).select_from(WorkMessage).where(
                WorkMessage.ref_type == "live_report_overdue", WorkMessage.ref_id == session_id
            )
        )
        assert message_count == 3
    finally:
        db.close()

    mixed = client.get("/admin-api/ims/live/report/pending", headers=auth)
    mixed_codes = [item["sessionCode"] for item in mixed.json()["data"]["list"]]
    assert "IMS20261006DYS1048" in mixed_codes
    assert "IMS20261006DYS1040" in mixed_codes
    assert mixed.json()["code"] == 1048

    filed = client.post(
        "/admin-api/ims/live/report/IMS20261006DYS1048",
        headers=auth,
        json=full_report(),
    )
    assert filed.json()["code"] == 0, filed.json()
    quiet = client.get("/admin-api/ims/live/report/pending", headers=auth, params={"overdueOnly": True})
    quiet_body = quiet.json()
    quiet_codes = [item["sessionCode"] for item in quiet_body["data"]["list"]]
    assert "IMS20261006DYS1048" not in quiet_codes
    assert "IMS20261006DYS1040" not in quiet_codes
    assert quiet_body["code"] == (0 if not quiet_codes else 1048)
    db = SessionLocal()
    try:
        todo = db.scalar(select(Todo).where(Todo.task_type == "live_report_overdue", Todo.ref_id == session_id))
        assert todo is not None
        assert todo.status == "DONE"
        report = db.scalar(select(LiveReport).where(LiveReport.session_code == "IMS20261006DYS1048", LiveReport.deleted == 0))
        assert report is not None
        assert report.entry_status == "SUBMITTED"
    finally:
        db.close()
