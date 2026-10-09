"""组织人员按本部门精确查看，下级部门不并入；对账报告与重放走本地桩。"""

import json
import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.dingtalk_crypto import pack
from app.main import app
from app.models import OrgEvent, Role, RolePerm, User, UserDept, UserRole
from app.security import hash_password

client = TestClient(app)
PARENT = 19410
CHILD = 19411


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def post_event(payload: dict):
    body, headers = pack(json.dumps(payload, ensure_ascii=False), "1700000000000", "nonce-org-194")
    return client.post("/admin-api/ims/auth/org/event", json=body, headers=headers)


def hire(event_id: str, ding: str, mobile: str, dept: int, name: str) -> dict:
    return {
        "eventType": "hire",
        "dingtalkEventId": event_id,
        "unionId": ding,
        "payloadJson": {
            "dingtalkUserId": ding,
            "nickname": name,
            "mobile": mobile,
            "deptIds": [dept],
            "deptNames": [name],
            "afterDept": name,
        },
    }


def consume() -> None:
    from app.org_sync import process_due

    db = SessionLocal()
    try:
        process_due(db)
        db.commit()
    finally:
        db.close()


def make_reader(username: str, scope: str, dept_id: int | None, perm: str | None) -> None:
    db = SessionLocal()
    try:
        user = User(
            username=username,
            nickname=username,
            mobile="13900019402" if username == "e2e_org_r2" else "13900019403",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        role = Role(
            role_name=username,
            role_key=f"org:{username}",
            data_scope=scope,
            status="ENABLED",
            source="MANUAL",
            tenant_id=0,
        )
        db.add_all([user, role])
        db.flush()
        if perm:
            db.add(RolePerm(role_id=role.id, module_code="auth", perm_code=perm, perm_level="R", tenant_id=0))
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        if dept_id:
            db.add(UserDept(user_id=user.id, dept_id=dept_id, tenant_id=0))
        db.commit()
    finally:
        db.close()


def names(token: str, dept_id: int | None = None) -> list[str]:
    params = {"pageNo": 1, "pageSize": 50}
    if dept_id:
        params["deptId"] = dept_id
    res = client.get("/admin-api/ims/auth/org/users", headers=auth(token), params=params)
    body = res.json()
    assert body["code"] == 0, body
    assert body["data"]["deptMatch"] == "EXACT"
    return [row["nickname"] for row in body["data"]["list"]]


def test_dept_filter_excludes_other_dept_and_r2_cannot_see_child():
    assert post_event(hire("evt-194-p", "dt-org-194-p", "13700019410", PARENT, "部门边父")).json()["code"] == 0
    assert post_event(hire("evt-194-c", "dt-org-194-c", "13700019411", CHILD, "部门边子")).json()["code"] == 0
    consume()
    make_reader("e2e_org_r2", "DEPT", PARENT, "auth:org:query")
    make_reader("e2e_org_outsider", "ALL", None, "system:user:query")

    admin = login()
    assert names(admin, PARENT) == ["部门边父"]
    assert names(admin, CHILD) == ["部门边子"]
    assert names(admin, 19499) == []

    r2 = login("e2e_org_r2")
    assert names(r2) == ["部门边父"]
    assert names(r2, CHILD) == []
    events = client.get("/admin-api/ims/auth/org/events", headers=auth(r2)).json()["data"]["list"]
    assert events
    assert all(row["afterDept"] != "部门边子" for row in events)
    assert all(row["eventType"] != "reconcile" for row in events)

    denied = client.get("/admin-api/ims/auth/org/users", headers=auth(login("e2e_org_outsider")))
    assert denied.status_code == 403
    assert denied.json()["code"] == 403

    report = client.get("/admin-api/ims/callback/dingtalk/reconcile/report", headers=auth(r2))
    assert report.status_code == 403
    replay = client.post(
        "/admin-api/ims/callback/dingtalk/retry-queue/replay",
        headers=auth(r2),
        json={"startTime": "2020-01-01T00:00:00", "endTime": "2020-01-02T00:00:00"},
    )
    assert replay.status_code == 403


def test_local_report_and_replay_do_not_call_dingtalk():
    token = login()
    empty = client.get("/admin-api/ims/callback/dingtalk/reconcile/report", headers=auth(token)).json()
    assert empty["code"] == 0
    assert empty["data"]["found"] is False
    assert empty["data"]["failures"] == []
    assert empty["data"]["source"] == "local"

    created = client.post("/admin-api/ims/auth/org/reconcile", headers=auth(token), json={})
    assert created.json()["code"] == 0
    report = client.get("/admin-api/ims/callback/dingtalk/reconcile/report", headers=auth(token)).json()["data"]
    assert report["found"] is True
    assert report["diffCount"] == 0
    assert report["fixedCount"] == 0
    assert report["failures"] == []
    assert report["source"] == "local"

    missed = client.post(
        "/admin-api/ims/callback/dingtalk/retry-queue/replay",
        headers=auth(token),
        json={"startTime": "2020-01-01T00:00:00", "endTime": "2020-01-02T00:00:00"},
    ).json()
    assert missed["code"] == 0
    assert missed["data"]["replayed"] == 0
    assert missed["data"]["source"] == "local"

    wide = client.post(
        "/admin-api/ims/callback/dingtalk/retry-queue/replay",
        headers=auth(token),
        json={"startTime": "2020-01-01T00:00:00", "endTime": "2020-01-09T00:00:00"},
    ).json()
    assert wide["code"] == 1001

    assert post_event(hire("evt-194-payload", "dt-org-194-pay", "13700019412", PARENT, "部门边载荷")).json()["code"] == 0
    consume()
    rows = client.get("/admin-api/ims/auth/org/events", headers=auth(token), params={"eventType": "hire"}).json()["data"]["list"]
    matched = [row for row in rows if row["dingtalkEventId"] == "evt-194-payload"]
    assert matched
    assert matched[0]["payloadJson"]["nickname"] == "部门边载荷"

    db = SessionLocal()
    try:
        db.add(
            OrgEvent(
                dingtalk_event_id="e2e-org-194-blank",
                event_type="dept_change",
                idempotency_key="e2e-org-194-blank|dept_change",
                payload_json="{}",
                sync_status="SUCCESS",
                retry_count=0,
                dead_letter=0,
                tenant_id=0,
            )
        )
        db.commit()
        blank_id = db.scalar(select(OrgEvent.id).where(OrgEvent.dingtalk_event_id == "e2e-org-194-blank"))
    finally:
        db.close()
    listed = client.get("/admin-api/ims/auth/org/events", headers=auth(token), params={"eventType": "dept_change"}).json()
    blank = [row for row in listed["data"]["list"] if row["id"] == blank_id]
    assert blank
    assert blank[0]["payloadJson"] == {}
