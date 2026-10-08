import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import MeetDailyReport, User

client = TestClient(app)
BJ = timezone(timedelta(hours=8))


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_meet_daily_template_and_submit():
    auth = headers()
    tpl = client.get("/admin-api/ims/meet/daily/template", headers=auth)
    assert tpl.json()["code"] == 0
    assert any(s["key"] == "done" for s in tpl.json()["data"]["sections"])

    today = datetime.now(BJ).strftime("%Y-%m-%d")
    draft = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={
            "reportDate": today,
            "contentDone": "完成联调",
            "contentPlan": "明日验收",
            "contentIssue": "无",
            "asDraft": True,
        },
    )
    assert draft.json()["code"] == 0
    assert draft.json()["data"]["submitStatus"] == "DRAFT"

    submit = client.post(
        "/admin-api/ims/meet/daily",
        headers=auth,
        json={
            "reportDate": today,
            "contentDone": "完成联调",
            "contentPlan": "明日验收",
            "contentIssue": "无",
            "asDraft": False,
        },
    )
    assert submit.json()["code"] == 0
    assert submit.json()["data"]["submitStatus"] == "SUBMITTED"

    by_date = client.get(f"/admin-api/ims/meet/daily/{today}", headers=auth)
    assert by_date.json()["data"]["contentDone"] == "完成联调"

    mine = client.get("/admin-api/ims/meet/daily/list", headers=auth, params={"onlyMine": True, "pageNo": 1, "pageSize": 5})
    assert mine.json()["code"] == 0
    assert mine.json()["data"]["total"] >= 1


def test_meet_daily_1112_after_submitted():
    auth = headers()
    day = (datetime.now(BJ) - timedelta(days=1)).strftime("%Y-%m-%d")
    created = client.post(
        "/admin-api/ims/meet/daily",
        headers=auth,
        json={
            "reportDate": day,
            "contentDone": "A",
            "contentPlan": "B",
            "contentIssue": "C",
            "asDraft": False,
        },
    )
    assert created.json()["code"] == 0
    report_id = created.json()["data"]["id"]

    blocked = client.put(
        f"/admin-api/ims/meet/daily/{report_id}",
        headers=auth,
        json={
            "reportDate": day,
            "contentDone": "改正文",
            "contentPlan": "B",
            "contentIssue": "C",
            "asDraft": False,
        },
    )
    assert blocked.json()["code"] == 1112

    ok_sup = client.put(
        f"/admin-api/ims/meet/daily/{report_id}",
        headers=auth,
        json={
            "reportDate": day,
            "contentDone": "A",
            "contentPlan": "B",
            "contentIssue": "C",
            "supplement": "补充说明段",
            "asDraft": False,
        },
    )
    assert ok_sup.json()["code"] == 0
    assert ok_sup.json()["data"]["supplement"] == "补充说明段"


def seed_submitted_report_for_peer(report_date: str) -> int:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        peer = db.scalar(select(User).where(User.username == "meet_peer", User.deleted == 0))
        if peer is None:
            peer = User(
                username="meet_peer",
                nickname="日报同事",
                mobile="13622223333",
                password_hash=admin.password_hash,
                status="ENABLED",
                tenant_id=0,
            )
            db.add(peer)
            db.flush()
        existing = db.scalar(
            select(MeetDailyReport).where(
                MeetDailyReport.deleted == 0,
                MeetDailyReport.user_id == peer.id,
                MeetDailyReport.report_date == report_date,
            )
        )
        if existing is not None:
            return int(existing.id)
        now = utcnow()
        row = MeetDailyReport(
            user_id=peer.id,
            dept_id=0,
            user_name=peer.nickname or peer.username,
            dept_name="测试部",
            report_date=report_date,
            content_done="同事完成项",
            content_plan="明日",
            content_issue="无",
            submit_status="SUBMITTED",
            submitted_at=now,
            is_on_time=1,
            tenant_id=0,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id)
    finally:
        db.close()


def test_meet_daily_team_list_excludes_self():
    auth = headers()
    day = (datetime.now(BJ) - timedelta(days=2)).strftime("%Y-%m-%d")
    seed_submitted_report_for_peer(day)
    team = client.get(
        "/admin-api/ims/meet/daily/team/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "submitStatus": "SUBMITTED"},
    )
    assert team.json()["code"] == 0
    ids = {r["userId"] for r in team.json()["data"]["list"]}
    db = SessionLocal()
    try:
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))
    finally:
        db.close()
    assert admin_id not in ids
    assert any(r["contentDone"] == "同事完成项" for r in team.json()["data"]["list"])


def test_meet_review_queue_and_two_level_read():
    auth = headers()
    day = (datetime.now(BJ) - timedelta(days=3)).strftime("%Y-%m-%d")
    report_id = seed_submitted_report_for_peer(day)

    q1 = client.get(
        "/admin-api/ims/meet/review/queue",
        headers=auth,
        params={"reviewLevel": 1, "pageNo": 1, "pageSize": 20},
    )
    assert q1.json()["code"] == 0
    assert any(r["id"] == report_id for r in q1.json()["data"]["list"])

    skip = client.put(
        f"/admin-api/ims/meet/review/{report_id}",
        headers=auth,
        json={"reviewLevel": 2, "action": "READ"},
    )
    assert skip.json()["code"] == 1113

    lv1 = client.put(
        f"/admin-api/ims/meet/review/{report_id}",
        headers=auth,
        json={"reviewLevel": 1, "action": "READ", "comment": "一级已读"},
    )
    assert lv1.json()["code"] == 0
    assert lv1.json()["data"]["nextLevel"] == 2

    q2 = client.get(
        "/admin-api/ims/meet/review/queue",
        headers=auth,
        params={"reviewLevel": 2, "pageNo": 1, "pageSize": 20},
    )
    assert any(r["id"] == report_id for r in q2.json()["data"]["list"])

    lv2 = client.put(
        f"/admin-api/ims/meet/review/{report_id}",
        headers=auth,
        json={"reviewLevel": 2, "action": "READ"},
    )
    assert lv2.json()["code"] == 0
    assert lv2.json()["data"]["nextLevel"] is None

    records = client.get(
        "/admin-api/ims/meet/review/records",
        headers=auth,
        params={"reportId": report_id, "pageNo": 1, "pageSize": 5},
    )
    assert records.json()["code"] == 0
    assert records.json()["data"]["total"] == 2


def test_meet_minutes_create_list_detail():
    auth = headers()
    when = datetime.now(BJ).strftime("%Y-%m-%dT15:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "W7-9 联调会",
            "meetingDate": when,
            "meetingRoom": "3F-A",
            "attendees": [{"userName": "admin"}],
            "summary": "纪要正文 P0",
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["minutesStatus"] == "MINUTES_RECORDED"
    mid = created.json()["data"]["id"]

    lst = client.get(
        "/admin-api/ims/meet/minutes/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "meetingTitle": "联调"},
    )
    assert lst.json()["code"] == 0
    assert any(r["id"] == mid for r in lst.json()["data"]["list"])

    detail = client.get(f"/admin-api/ims/meet/minutes/{mid}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["summary"] == "纪要正文 P0"


def test_meet_stat_on_time_rate_after_submit():
    auth = headers()
    today = datetime.now(BJ).strftime("%Y-%m-%d")
    client.post(
        "/admin-api/ims/meet/daily",
        headers=auth,
        json={
            "reportDate": today,
            "contentDone": "统计片",
            "contentPlan": "明日",
            "contentIssue": "无",
            "asDraft": False,
        },
    )
    stat = client.get(
        "/admin-api/ims/meet/stat/on-time-rate",
        headers=auth,
        params={"dateFrom": today, "dateTo": today},
    )
    assert stat.json()["code"] == 0
    assert stat.json()["data"]["totalOnTimeRate"] >= 0
    assert stat.json()["data"]["byPerson"]


def test_meet_minutes_registered_without_summary():
    auth = headers()
    when = (datetime.now(BJ) - timedelta(days=1)).strftime("%Y-%m-%dT09:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "仅登记会议",
            "meetingDate": when,
            "attendees": [],
            "summary": "",
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["minutesStatus"] == "REGISTERED"


def test_meet_minutes_archive_and_rate():
    auth = headers()
    when = datetime.now(BJ).strftime("%Y-%m-%dT14:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "归档测试会",
            "meetingDate": when,
            "summary": "结论已录入",
        },
    )
    mid = created.json()["data"]["id"]
    archived = client.put(f"/admin-api/ims/meet/minutes/{mid}/archive", headers=auth)
    assert archived.json()["code"] == 0
    assert archived.json()["data"]["minutesStatus"] == "ARCHIVED"
    assert archived.json()["data"]["archivedAt"]

    rate = client.get("/admin-api/ims/meet/minutes/archive-rate", headers=auth)
    assert rate.json()["code"] == 0
    assert rate.json()["data"]["archivedCount"] >= 1
