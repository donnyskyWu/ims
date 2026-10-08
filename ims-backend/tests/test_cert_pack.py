"""#77 · S6 证件催办、查看审计、异常访问报告。"""

import os
import uuid
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal, utcnow
from app.main import app
from app.models import CertRemindLog, Menu, Role, RoleMenu, User, UserRole
from app.security import hash_password

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def upload(auth: dict, holder: str, days: int, number: str):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": number,
            "fileKey": "local/cert/upload",
            "issueDate": "2020-01-01",
            "expireDate": (today + timedelta(days=days)).isoformat(),
        },
    )


def approve(auth: dict, cert_id: int):
    reviewed = client.put(
        f"/admin-api/ims/cert/archive/{cert_id}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert reviewed.json()["code"] == 0


def make_user(role_name: str, role_key: str) -> str:
    username = f"cert_{uuid.uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        user = User(
            username=username,
            nickname=role_name,
            mobile=f"139{uuid.uuid4().int % 10**8:08d}",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(user)
        db.flush()
        role = Role(
            role_name=role_name,
            role_key=role_key,
            data_scope="ALL",
            source="MANUAL",
            status="ENABLED",
            tenant_id=0,
        )
        db.add(role)
        db.flush()
        menu = db.scalar(select(Menu).where(Menu.deleted == 0))
        assert menu is not None
        db.add(RoleMenu(role_id=role.id, menu_id=menu.id, perm_code=menu.perm_code or "system:user:query", tenant_id=0))
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.commit()
        return username
    finally:
        db.close()


def test_cert_remind_repeats_without_consuming_scan_dedup():
    auth = headers()
    holder = "E2E催办证"
    number = "110101199001017701"
    created = upload(auth, holder, 30, number)
    body = created.json()
    assert body["code"] == 0, body
    approve(auth, body["data"]["id"])
    scan = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    assert scan.json()["code"] == 0
    assert scan.json()["data"]["created"] == 1

    listed = client.get("/admin-api/ims/cert/expire/list", headers=auth, params={"holderName": holder, "pageSize": 10})
    row = listed.json()["data"]["list"][0]
    assert row["level"] == "YELLOW"
    log_id = row["id"]

    missing = client.put(f"/admin-api/ims/cert/expire/99999999/remind", headers=auth, json={})
    assert missing.json()["code"] == 1039
    bad = client.put(f"/admin-api/ims/cert/expire/{log_id}/remind", headers=auth, json={"remindChannel": "SMS"})
    assert bad.json()["code"] == 1001

    first = client.put(f"/admin-api/ims/cert/expire/{log_id}/remind", headers=auth, json={})
    payload = first.json()
    assert payload["code"] == 0, payload
    assert payload["data"]["remindedAt"]
    assert number not in first.text

    second = client.put(
        f"/admin-api/ims/cert/expire/{log_id}/remind",
        headers=auth,
        json={"remindChannel": "APP"},
    )
    assert second.json()["code"] == 0, second.json()

    messages = client.get("/admin-api/ims/auth/workbench/messages", headers=auth, params={"pageNo": 1, "pageSize": 20})
    titles = [item["title"] for item in messages.json()["data"]["list"]]
    assert titles.count(f"证件催办：{holder}") == 3
    assert titles.count(f"证件黄色预警：{holder}") == 1
    channels = [item["channel"] for item in messages.json()["data"]["list"] if item["title"] == f"证件催办：{holder}"]
    assert "IN_APP" in channels
    assert "DINGTALK" in channels

    todos = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PENDING", "taskType": "cert_remind"},
    )
    remind_todos = [item for item in todos.json()["data"]["list"] if item["title"] == f"证件催办：{holder}"]
    assert len(remind_todos) == 2
    assert {item["taskType"] for item in remind_todos} == {"cert_remind"}

    again = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    assert again.json()["data"]["created"] == 0
    assert again.json()["data"]["skipped"] == 1
    messages_again = client.get("/admin-api/ims/auth/workbench/messages", headers=auth, params={"pageNo": 1, "pageSize": 20})
    again_titles = [item["title"] for item in messages_again.json()["data"]["list"]]
    assert again_titles.count(f"证件黄色预警：{holder}") == 1

    db = SessionLocal()
    try:
        stored = db.scalar(select(func.count()).select_from(CertRemindLog).where(CertRemindLog.expire_log_id == log_id))
        assert int(stored or 0) == 2
    finally:
        db.close()

    peer = make_user("证件只读", f"cert:ro:{uuid.uuid4().hex[:8]}")
    denied = client.put(f"/admin-api/ims/cert/expire/{log_id}/remind", headers=headers(peer), json={"remindChannel": "APP"})
    assert denied.status_code == 403
    assert denied.json()["code"] == 1008

    clerk = make_user("行政管理员", f"cert:r2:{uuid.uuid4().hex[:8]}")
    allowed = client.put(
        f"/admin-api/ims/cert/expire/{log_id}/remind",
        headers=headers(clerk),
        json={"remindChannel": "APP"},
    )
    assert allowed.json()["code"] == 0, allowed.json()
    blocked_audit = client.get("/admin-api/ims/cert/security/view-logs", headers=headers(clerk))
    assert blocked_audit.json()["code"] == 1008


def test_cert_view_logs_filter_and_risk_over_ten():
    auth = headers()
    samples = [
        ("E2E审计甲", "110101199001017711", 1),
        ("E2E审计乙", "110101199001017712", 10),
    ]
    cert_ids = {}
    for holder, number, _times in samples:
        created = upload(auth, holder, 400, number)
        body = created.json()
        assert body["code"] == 0, body
        approve(auth, body["data"]["id"])
        cert_ids[holder] = body["data"]["id"]

    for holder, number, times in samples:
        for _ in range(times):
            viewed = client.get(f"/admin-api/ims/corp/resource/certificate/{cert_ids[holder]}/view", headers=auth)
            assert viewed.json()["code"] == 0, viewed.json()
            assert number not in viewed.text

    listed = client.get(
        "/admin-api/ims/cert/security/view-logs",
        headers=auth,
        params={"certId": cert_ids["E2E审计甲"], "pageNo": 1, "pageSize": 20},
    )
    page = listed.json()
    assert page["code"] == 0, page
    assert page["data"]["total"] == 1
    row = page["data"]["list"][0]
    assert row["holderName"] == "E2E审计甲"
    assert row["viewLevel"] == 2
    assert "admin" in row["watermarkText"].lower()
    assert "110101199001017711" not in listed.text
    viewer_id = row["viewerUserId"]

    start = (utcnow() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    end = (utcnow() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    scoped = client.get(
        "/admin-api/ims/cert/security/view-logs",
        headers=auth,
        params=[
            ("viewerUserId", viewer_id),
            ("viewLevel", 2),
            ("timeRange", start),
            ("timeRange", end),
            ("pageSize", 50),
        ],
    )
    assert scoped.json()["code"] == 0
    assert scoped.json()["data"]["total"] >= 11

    quiet = client.get(
        "/admin-api/ims/cert/security/view-logs",
        headers=auth,
        params=[
            ("certId", cert_ids["E2E审计甲"]),
            ("timeRange", "1999-01-01 00:00:00"),
            ("timeRange", "1999-01-02 00:00:00"),
        ],
    )
    assert quiet.json()["data"]["total"] == 0

    bad_level = client.get("/admin-api/ims/cert/security/view-logs", headers=auth, params={"viewLevel": 9})
    assert bad_level.json()["code"] == 1001

    report = client.get("/admin-api/ims/cert/security/risk-report", headers=auth)
    data = report.json()["data"]
    matched = [item for item in data["highFrequencyUsers"] if item["userId"] == viewer_id]
    assert matched
    assert matched[0]["viewsInLastHour"] >= 11
    assert data["abnormalTotal"] >= 11

    peer = make_user("证件只读", f"cert:ro:{uuid.uuid4().hex[:8]}")
    denied = client.get("/admin-api/ims/cert/security/view-logs", headers=headers(peer))
    assert denied.json()["code"] == 1008
    denied_risk = client.get("/admin-api/ims/cert/security/risk-report", headers=headers(peer))
    assert denied_risk.json()["code"] == 1008
