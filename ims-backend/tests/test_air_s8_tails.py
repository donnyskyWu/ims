"""AIR/S8 本地尾巴：Key 列表筛选空结果、审计报表过滤、解冻清空认证失败窗口。"""

import os
import uuid
from datetime import datetime, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import app
from app.air_key import set_qpm_clock
from app.models import AirAuthFail, AirApiKey

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def make_user(auth: dict, prefix: str) -> tuple[int, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}{suffix}"
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={
            "username": username,
            "nickname": username,
            "password": "Admin@123",
            "mobile": f"139{suffix}",
        },
    )
    assert created.json()["code"] == 0, created.text
    return int(created.json()["data"]["id"]), username


def generate_key(auth: dict, user_id: int) -> dict:
    created = client.post(
        "/admin-api/ims/air/key/generate",
        headers=auth,
        json={
            "userId": user_id,
            "deviceName": "个人通用",
            "expireAt": "2099-01-01",
            "clientToken": uuid.uuid4().hex,
        },
    )
    assert created.json()["code"] == 0, created.text
    return created.json()["data"]


def mcp(plain: str, name: str, arguments: dict | None = None):
    return client.post(
        "/ims/mcp",
        headers={"Authorization": f"Bearer {plain}"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        },
    )


def key_page(auth: dict, **params):
    res = client.get("/admin-api/ims/air/cfg/key/page", headers=auth, params={"pageNo": 1, "pageSize": 100, **params})
    assert res.json()["code"] == 0, res.text
    return res.json()["data"]


def test_key_list_filters_to_empty_and_back():
    auth = headers()
    user_id, username = make_user(auth, "keyf")
    missing = key_page(auth, userName=username)
    assert missing["total"] == 0
    assert missing["list"] == []

    issued = generate_key(auth, user_id)
    listed = key_page(auth, userName=username, status="ACTIVE")
    assert listed["total"] == 1
    assert listed["list"][0]["keyCode"] == issued["keyCode"]
    assert listed["list"][0]["status"] == "ACTIVE"

    frozen_before = key_page(auth, userName=username, status="FROZEN")
    assert frozen_before["total"] == 0

    bad = client.get(
        "/admin-api/ims/air/cfg/key/page",
        headers=auth,
        params={"status": "NOPE", "pageNo": 1, "pageSize": 10},
    )
    assert bad.json()["code"] == 1001

    frozen = client.post(
        f"/admin-api/ims/air/key/{issued['keyId']}/freeze",
        headers=auth,
        json={"reason": "管理员停用"},
    )
    assert frozen.json()["code"] == 0, frozen.text
    after = key_page(auth, userName=username, status="FROZEN")
    assert after["total"] == 1
    assert after["list"][0]["freezeReason"] == "管理员停用"
    assert key_page(auth, userName=username, status="ACTIVE")["total"] == 0

    unknown = key_page(auth, userName=f"no-such-{uuid.uuid4().hex[:6]}")
    assert unknown["total"] == 0


def test_audit_report_filters_keyword_key_and_dates():
    auth = headers()
    user_id, username = make_user(auth, "audf")
    issued = generate_key(auth, user_id)
    called = mcp(issued["plainKey"], "skills.get", {"code": "SKL-NO-SUCH"})
    assert called.status_code == 403

    matched = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"keyword": username, "tool": "skills.get", "result": "FAIL", "keyCode": issued["keyCode"], "pageNo": 1, "pageSize": 20},
    )
    assert matched.json()["code"] == 0, matched.text
    rows = matched.json()["data"]["list"]
    assert rows
    assert {row["keyCode"] for row in rows} == {issued["keyCode"]}
    assert {row["tool"] for row in rows} == {"skills.get"}
    assert all(row["resultCode"] != "SUCCESS" for row in rows)

    past = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"keyCode": issued["keyCode"], "dateRange": "1999-01-01,1999-01-02", "pageNo": 1, "pageSize": 20},
    )
    assert past.json()["code"] == 0, past.text
    assert past.json()["data"]["total"] == 0

    missing_key = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"keyCode": "KEY-NO-SUCH", "pageNo": 1, "pageSize": 20},
    )
    assert missing_key.json()["data"]["total"] == 0

    invalid = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"dateRange": "2020-13-01,2020-13-02"},
    )
    assert invalid.json()["code"] == 1001


def test_unfreeze_clears_auth_fail_window():
    auth = headers()
    user_id, _username = make_user(auth, "unfr")
    issued = generate_key(auth, user_id)
    plain = issued["plainKey"]
    base = datetime(2026, 10, 8, 4, 0, 0)
    try:
        set_qpm_clock(lambda: base)
        for _ in range(10):
            denied = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
            assert denied.status_code == 403
    finally:
        set_qpm_clock(None)

    db = SessionLocal()
    try:
        key = db.get(AirApiKey, issued["keyId"])
        assert key is not None
        assert key.status == "FROZEN"
        assert key.freeze_reason == "认证失败锁定"
        fails = int(db.scalar(select(func.count()).select_from(AirAuthFail).where(AirAuthFail.key_id == key.id)) or 0)
        assert fails >= 10
    finally:
        db.close()

    blocked = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
    assert blocked.status_code == 401

    revived = client.post(f"/admin-api/ims/air/key/{issued['keyId']}/unfreeze", headers=auth)
    assert revived.json()["code"] == 0, revived.text
    active = client.post(f"/admin-api/ims/air/key/{issued['keyId']}/unfreeze", headers=auth)
    assert active.json()["code"] == 1001

    db = SessionLocal()
    try:
        key = db.get(AirApiKey, issued["keyId"])
        assert key.status == "ACTIVE"
        assert key.freeze_reason == ""
        fails = int(db.scalar(select(func.count()).select_from(AirAuthFail).where(AirAuthFail.key_id == key.id)) or 0)
        assert fails == 0
    finally:
        db.close()

    try:
        set_qpm_clock(lambda: base + timedelta(minutes=1))
        again = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
        assert again.status_code == 403
    finally:
        set_qpm_clock(None)

    db = SessionLocal()
    try:
        key = db.get(AirApiKey, issued["keyId"])
        assert key.status == "ACTIVE"
        fails = int(db.scalar(select(func.count()).select_from(AirAuthFail).where(AirAuthFail.key_id == key.id)) or 0)
        assert fails == 1
    finally:
        db.close()

    revoked = client.post(f"/admin-api/ims/air/key/{issued['keyId']}/revoke", headers=auth)
    assert revoked.json()["code"] == 0
    frozen = client.post(f"/admin-api/ims/air/key/{issued['keyId']}/freeze", headers=auth, json={"reason": "管理员停用"})
    assert frozen.json()["code"] == 1001
    opened = client.post(f"/admin-api/ims/air/key/{issued['keyId']}/unfreeze", headers=auth)
    assert opened.json()["code"] == 1001
