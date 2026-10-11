import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import MeetDailyReport, Role, RolePerm, Todo, User, UserRole, WorkMessage

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


def test_meet_daily_direct_submit_without_draft():
    auth = headers()
    tpl = client.get("/admin-api/ims/meet/daily/template", headers=auth)
    sections = {item["key"]: item["required"] for item in tpl.json()["data"]["sections"]}
    assert sections["done"] is True
    assert sections["plan"] is False
    assert sections["issue"] is False
    assert any(item["value"] == "SHORT_VIDEO" for item in tpl.json()["data"]["reportTypes"])

    empty = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={"reportDate": "2026-09-01", "asDraft": False},
    )
    assert empty.json()["code"] == 1001
    assert "必填" in empty.json()["msg"]

    day = "2026-09-02"
    created = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={
            "reportDate": day,
            "reportType": "短视频",
            "contentDone": "直接提交",
            "asDraft": False,
        },
    )
    body = created.json()
    assert body["code"] in (0, 1111)
    if body["code"] == 0:
        assert body["data"]["submitStatus"] == "SUBMITTED"
        assert body["data"]["reportType"] == "SHORT_VIDEO"
        assert body["data"]["contentPlan"] == ""

    friday = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={"reportDate": "2026-10-09", "contentDone": "周五", "asDraft": False},
    )
    assert friday.json()["code"] == 1001


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
    data = stat.json()["data"]
    assert data["totalOnTimeRate"] >= 0
    assert data["byPerson"]
    assert "weekSubmitCount" in data
    assert len(data["trend7"]) == 7
    assert "fieldCompletenessAvg" in data


def test_meet_minutes_register_requires_title_time_attendees():
    auth = headers()
    empty = client.post("/admin-api/ims/meet/minutes", headers=auth, json={})
    assert empty.json()["code"] == 1001
    assert "必填" in empty.json()["msg"]
    named = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "预约字段",
            "meetingDate": datetime.now(BJ).strftime("%Y-%m-%dT16:30:00+08:00"),
            "durationMinutes": 90,
            "meetingRoom": "2F-会议室 A",
            "agenda": "对齐进度",
            "attendees": [{"userId": 1, "userName": "admin"}],
        },
    )
    assert named.json()["code"] == 0
    assert named.json()["data"]["minutesStatus"] == "REGISTERED"
    assert named.json()["data"]["agenda"] == "对齐进度"
    assert named.json()["data"]["durationMinutes"] == 90
    people = client.get("/admin-api/ims/meet/minutes/participants", headers=auth)
    assert people.json()["code"] == 0
    assert any(item["username"] == "admin" for item in people.json()["data"]["list"])


def test_meet_minutes_registered_without_summary():
    auth = headers()
    when = (datetime.now(BJ) - timedelta(days=1)).strftime("%Y-%m-%dT09:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "仅登记会议",
            "meetingDate": when,
            "attendees": [{"userName": "admin"}],
            "summary": "",
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["minutesStatus"] == "REGISTERED"


def _scoped_user(username: str, nickname: str, scope: str) -> int:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        assert admin is not None
        role = Role(
            role_name=nickname,
            role_key=f"meet:{username}",
            data_scope=scope,
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        db.add(
            RolePerm(
                role_id=role.id,
                module_code="MEET",
                perm_code="meet:query",
                perm_level="R",
                tenant_id=0,
            )
        )
        user = User(
            username=username,
            nickname=nickname,
            mobile=f"138{abs(hash(username)) % 100000000:08d}",
            password_hash=admin.password_hash,
            status="ENABLED",
            tenant_id=0,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.commit()
        return int(user.id)
    finally:
        db.close()


def _auth(username: str) -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_meet_minutes_visible_to_organizer_recorder_and_attendee():
    attendee_id = _scoped_user("meet_attendee", "参会甲", "SELF")
    _scoped_user("meet_stranger", "路人乙", "SELF")
    _scoped_user("meet_host", "发起人", "DEPT")
    host = _auth("meet_host")
    when = datetime.now(BJ).strftime("%Y-%m-%dT11:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=host,
        json={
            "meetingTitle": "范围可见会议",
            "meetingDate": when,
            "attendees": [{"userId": attendee_id, "userName": "参会甲"}],
        },
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]

    own = client.get(
        "/admin-api/ims/meet/minutes/list",
        headers=host,
        params={"pageNo": 1, "pageSize": 20, "meetingTitle": "范围可见"},
    )
    assert any(row["id"] == mid for row in own.json()["data"]["list"])

    guest = client.get(
        "/admin-api/ims/meet/minutes/list",
        headers=_auth("meet_attendee"),
        params={"pageNo": 1, "pageSize": 20, "meetingTitle": "范围可见"},
    )
    assert any(row["id"] == mid for row in guest.json()["data"]["list"])
    detail = client.get(f"/admin-api/ims/meet/minutes/{mid}", headers=_auth("meet_attendee"))
    assert detail.json()["code"] == 0

    stranger = client.get(
        "/admin-api/ims/meet/minutes/list",
        headers=_auth("meet_stranger"),
        params={"pageNo": 1, "pageSize": 20, "meetingTitle": "范围可见"},
    )
    assert stranger.json()["code"] == 0
    assert all(row["id"] != mid for row in stranger.json()["data"]["list"])
    hidden = client.get(f"/admin-api/ims/meet/minutes/{mid}", headers=_auth("meet_stranger"))
    assert hidden.json()["code"] == 1004


def test_meet_minutes_archive_and_rate():
    auth = headers()
    when = datetime.now(BJ).strftime("%Y-%m-%dT14:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "归档测试会",
            "meetingDate": when,
            "attendees": [{"userName": "admin"}],
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


def test_meet_minutes_record_action_ai_and_archive_lock():
    auth = headers()
    db = SessionLocal()
    admin = db.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    admin_id = int(admin.id)
    db.close()
    when = datetime.now(BJ).strftime("%Y-%m-%dT18:00:00+08:00")
    created = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "纪要主流程",
            "meetingDate": when,
            "agenda": "对齐行动项",
            "attendees": [{"userId": admin_id, "userName": "admin"}],
        },
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]
    empty = client.put(f"/admin-api/ims/meet/minutes/{mid}", headers=auth, json={"summary": "  "})
    assert empty.json()["code"] == 1001

    saved = client.put(
        f"/admin-api/ims/meet/minutes/{mid}",
        headers=auth,
        json={
            "summary": "会议结论：本周完成联调",
            "decisions": [{"description": "按期归档"}],
            "actionItems": [
                {
                    "description": "回填联调结果",
                    "responsibleUserId": admin_id,
                    "dueDate": "2026-10-20",
                }
            ],
        },
    )
    body = saved.json()
    assert body["code"] == 0
    assert body["data"]["minutesStatus"] == "MINUTES_RECORDED"
    assert body["data"]["decisions"][0]["description"] == "按期归档"
    item_id = body["data"]["actionItems"][0]["itemId"]
    assert item_id > 100

    db = SessionLocal()
    todo = db.scalar(select(Todo).where(Todo.ref_type == "meet_action", Todo.ref_id == item_id))
    assert todo is not None
    assert todo.assignee_user_id == admin_id
    assert todo.status == "PENDING"
    db.close()

    missing = client.put(f"/admin-api/ims/meet/minutes/action-item/{item_id}", headers=auth, json={})
    assert missing.json()["code"] == 1118
    _scoped_user("meet_action_stranger", "行动路人", "SELF")
    stranger = client.put(
        f"/admin-api/ims/meet/minutes/action-item/{item_id}",
        headers=_auth("meet_action_stranger"),
        json={"closeRemark": "不是我的"},
    )
    assert stranger.json()["code"] == 1118

    closed = client.put(
        f"/admin-api/ims/meet/minutes/action-item/{item_id}",
        headers=auth,
        json={"closeRemark": "已在联调环境核对"},
    )
    assert closed.json()["code"] == 0
    assert closed.json()["data"]["actionItems"][0]["status"] == "CLOSED"

    draft = client.post(f"/admin-api/ims/meet/minutes/{mid}/ai-draft", headers=auth)
    assert draft.json()["code"] == 0
    assert draft.json()["data"]["provider"] == "stub"
    assert "AI 初稿" in draft.json()["data"]["summary"]

    archived = client.put(f"/admin-api/ims/meet/minutes/{mid}/archive", headers=auth)
    assert archived.json()["data"]["minutesStatus"] == "ARCHIVED"
    locked = client.put(
        f"/admin-api/ims/meet/minutes/{mid}",
        headers=auth,
        json={"summary": "试图改正文"},
    )
    assert locked.json()["code"] == 1117
    noted = client.put(
        f"/admin-api/ims/meet/minutes/{mid}",
        headers=auth,
        json={"appendix": "会后更正：时间以日历为准"},
    )
    assert noted.json()["code"] == 0
    assert "会后更正" in noted.json()["data"]["appendix"]
    assert noted.json()["data"]["summary"] == "会议结论：本周完成联调"


def test_meet_review_follow_up_creates_todo_and_closes():
    auth = headers()
    day = (datetime.now(BJ) - timedelta(days=4)).strftime("%Y-%m-%d")
    report_id = seed_submitted_report_for_peer(day)
    missing = client.put(
        f"/admin-api/ims/meet/review/{report_id}",
        headers=auth,
        json={"reviewLevel": 1, "action": "MARK_FOLLOW_UP", "followUpItems": [{"description": "只写了描述"}]},
    )
    assert missing.json()["code"] == 1001

    db = SessionLocal()
    admin_id = int(db.scalar(select(User.id).where(User.username == "admin")))
    db.close()
    marked = client.put(
        f"/admin-api/ims/meet/review/{report_id}",
        headers=auth,
        json={
            "reviewLevel": 1,
            "action": "MARK_FOLLOW_UP",
            "comment": "请补充数据",
            "followUpItems": [
                {"description": "补一张截图", "responsibleUserId": admin_id, "dueDate": "2026-10-18"}
            ],
        },
    )
    assert marked.json()["code"] == 0
    records = client.get(
        "/admin-api/ims/meet/review/records",
        headers=auth,
        params={"reportId": report_id, "action": "MARK_FOLLOW_UP"},
    )
    item = records.json()["data"]["list"][0]["followUpItems"][0]
    assert item["status"] == "OPEN"
    item_id = item["itemId"]
    db = SessionLocal()
    todo = db.scalar(select(Todo).where(Todo.ref_type == "meet_follow", Todo.ref_id == item_id))
    assert todo is not None and todo.assignee_user_id == admin_id
    db.close()

    _scoped_user("meet_follow_stranger", "跟进路人", "SELF")
    denied = client.put(
        f"/admin-api/ims/meet/review/follow-up/{item_id}",
        headers=_auth("meet_follow_stranger"),
        json={"closeRemark": "不是我的"},
    )
    assert denied.json()["code"] == 1115
    closed = client.put(
        f"/admin-api/ims/meet/review/follow-up/{item_id}",
        headers=auth,
        json={"closeRemark": "截图已补"},
    )
    assert closed.json()["code"] == 0
    db = SessionLocal()
    todo = db.scalar(select(Todo).where(Todo.ref_type == "meet_follow", Todo.ref_id == item_id))
    assert todo is not None and todo.status == "DONE"
    db.close()


def test_meet_room_conflict_and_invitation():
    guest_id = _scoped_user("meet_guest", "受邀人", "SELF")
    auth = headers()
    when = "2026-10-21T10:00:00+08:00"
    first = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "上午会",
            "meetingDate": when,
            "durationMinutes": 60,
            "meetingRoom": "2F-会议室 A",
            "attendees": [{"userId": guest_id, "userName": "受邀人"}],
        },
    )
    assert first.json()["code"] == 0
    clash = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "冲突会",
            "meetingDate": "2026-10-21T10:30:00+08:00",
            "durationMinutes": 30,
            "meetingRoom": "2F-会议室 A",
            "attendees": [{"userId": guest_id, "userName": "受邀人"}],
        },
    )
    assert clash.json()["code"] == 1001
    assert "会议室已被占用" in clash.json()["msg"]
    online = client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={
            "meetingTitle": "线上不冲突",
            "meetingDate": when,
            "meetingRoom": "线上",
            "attendees": [{"userName": "外部嘉宾", "external": True}],
        },
    )
    assert online.json()["code"] == 0
    db = SessionLocal()
    notes = list(db.scalars(select(WorkMessage).where(WorkMessage.user_id == guest_id, WorkMessage.ref_type == "meet_minutes")).all())
    db.close()
    assert len(notes) == 1
    assert notes[0].title == "会议邀请"


def test_meet_daily_duplicate_echoes_1111_and_locks_body():
    auth = headers()
    day = "2026-10-08"
    created = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={"reportDate": day, "reportType": "OPS", "contentDone": "运营事项", "asDraft": False},
    )
    assert created.json()["code"] == 0
    again = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={"reportDate": day, "reportType": "OPS", "contentDone": "运营事项", "asDraft": False},
    )
    assert again.json()["code"] == 1111
    assert again.json()["msg"] == "今日日报已存在"
    assert again.json()["data"]["contentDone"] == "运营事项"
    changed = client.post(
        "/admin-api/ims/meet/daily/submit",
        headers=auth,
        json={"reportDate": day, "contentDone": "改掉正文", "asDraft": False},
    )
    assert changed.json()["code"] == 1112
    listed = client.get(
        "/admin-api/ims/meet/daily/list",
        headers=auth,
        params={"onlyMine": True, "reportType": "OPS", "reviewState": "PENDING", "pageSize": 20},
    )
    assert any(row["reportDate"] == day and row["fieldCompleteness"] >= 0 for row in listed.json()["data"]["list"])


def test_meet_minutes_bucket_today_and_ended():
    auth = headers()
    today = datetime.now(BJ).strftime("%Y-%m-%dT09:30:00+08:00")
    past = (datetime.now(BJ) - timedelta(days=3)).strftime("%Y-%m-%dT09:00:00+08:00")
    client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={"meetingTitle": "今天这场", "meetingDate": today, "durationMinutes": 30, "attendees": [{"userName": "admin"}]},
    )
    client.post(
        "/admin-api/ims/meet/minutes",
        headers=auth,
        json={"meetingTitle": "已经结束", "meetingDate": past, "durationMinutes": 30, "attendees": [{"userName": "admin"}]},
    )
    today_list = client.get("/admin-api/ims/meet/minutes/list", headers=auth, params={"bucket": "today", "pageSize": 20})
    titles = [row["meetingTitle"] for row in today_list.json()["data"]["list"]]
    assert "今天这场" in titles
    assert "已经结束" not in titles
    ended = client.get("/admin-api/ims/meet/minutes/list", headers=auth, params={"bucket": "ended", "pageSize": 20})
    ended_titles = [row["meetingTitle"] for row in ended.json()["data"]["list"]]
    assert "已经结束" in ended_titles
