"""#224 · Key 白名单筛选、吊销原因，以及用量/审计日期边角。"""

import os
import uuid
from datetime import date, timedelta

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


def key_page(auth: dict, **params):
    res = client.get("/admin-api/ims/air/cfg/key/page", headers=auth, params={"pageNo": 1, "pageSize": 100, **params})
    body = res.json()
    assert body["code"] == 0, res.text
    return body["data"]


def test_key_page_filters_whitelist_and_empty_copy_inputs():
    auth = headers()
    seeded = key_page(auth, whitelistOn="true")
    assert seeded["total"] >= 1
    assert all(row["whitelist"] for row in seeded["list"])
    assert any(row["keyCode"] == "KEY-0001" for row in seeded["list"])

    user_id, _username = make_user(auth, "wl")
    issued = generate_key(auth, user_id)
    opened = key_page(auth, whitelistOn="true")
    assert issued["keyCode"] not in {row["keyCode"] for row in opened["list"]}

    closed = key_page(auth, whitelistOn="false", userName=_username)
    assert [row["keyCode"] for row in closed["list"]] == [issued["keyCode"]]
    assert closed["list"][0]["whitelist"] == ""

    missing = key_page(auth, userName=f"no-such-{uuid.uuid4().hex[:6]}", whitelistOn="true")
    assert missing["total"] == 0
    assert missing["list"] == []

    bad = client.get(
        "/admin-api/ims/air/cfg/key/page",
        headers=auth,
        params={"whitelistOn": "maybe", "pageNo": 1, "pageSize": 10},
    )
    assert bad.json()["code"] == 1001
    assert bad.json()["msg"] == "whitelistOn 仅支持 true 或 false"


def test_revoke_keeps_manual_reason():
    auth = headers()
    user_id, username = make_user(auth, "rvk")
    issued = generate_key(auth, user_id)
    revoked = client.post(
        f"/admin-api/ims/air/key/{issued['keyId']}/revoke",
        headers=auth,
        json={"reason": "管理员手工"},
    )
    assert revoked.json()["code"] == 0, revoked.text
    again = client.post(
        f"/admin-api/ims/air/key/{issued['keyId']}/revoke",
        headers=auth,
        json={"reason": "覆盖失败"},
    )
    assert again.json()["code"] == 0
    listed = key_page(auth, userName=username, status="REVOKED")
    assert listed["total"] == 1
    assert listed["list"][0]["freezeReason"] == "管理员手工"
    assert listed["list"][0]["status"] == "REVOKED"

    other_id, other_name = make_user(auth, "rv2")
    other = generate_key(auth, other_id)
    bare = client.post(f"/admin-api/ims/air/key/{other['keyId']}/revoke", headers=auth)
    assert bare.json()["code"] == 0, bare.text
    bare_row = key_page(auth, userName=other_name, status="REVOKED")["list"][0]
    assert bare_row["freezeReason"] == "管理员手工"


def test_audit_span_tool_and_usage_inverted_dates():
    auth = headers()
    wide = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"dateRange": "2020-01-01,2020-07-01", "pageNo": 1, "pageSize": 20},
    )
    assert wide.json()["code"] == 1001
    assert wide.json()["msg"] == "查询区间不能超过 180 天"

    past = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"dateRange": "1999-01-01,1999-01-02", "pageNo": 1, "pageSize": 20},
    )
    assert past.json()["code"] == 0, past.text
    assert past.json()["data"]["total"] == 0

    inverted = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"dateRange": "2026-12-02,2026-12-01"},
    )
    assert inverted.json()["code"] == 1001
    assert inverted.json()["msg"] == "结束日不能早于开始日"

    bad_tool = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"tool": "knowledge.get"},
    )
    assert bad_tool.json()["code"] == 1001
    assert "skills.list" in bad_tool.json()["msg"]

    today = date.today()
    start = (today + timedelta(days=2)).isoformat()
    end = (today + timedelta(days=1)).isoformat()
    usage = client.get(
        "/admin-api/ims/air/usage/stat",
        headers=auth,
        params={"by": "PERSON", "dateRange": f"{start},{end}"},
    )
    assert usage.json()["code"] == 1001
    assert usage.json()["msg"] == "结束日不能早于开始日"
