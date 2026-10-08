"""AIR Key 明文一次、QPM 第 61 次 429、换新限额立即生效。时钟注入，不睡眠。"""

import os
import uuid
from datetime import datetime, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.air_key import hash_key, set_qpm_clock
from app.models import AirApiKey, AirMcpLog, Notify

client = TestClient(app)

MCP_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "skills.list", "arguments": {}},
}


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def make_user(auth: dict) -> int:
    suffix = uuid.uuid4().hex[:8]
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={
            "username": f"qpm{suffix}",
            "nickname": f"qpm{suffix}",
            "password": "Admin@123",
            "mobile": f"136{suffix}",
        },
    )
    assert created.json()["code"] == 0, created.text
    return int(created.json()["data"]["id"])


def generate(auth: dict, user_id: int, token: str, qpm: int | None = None) -> dict:
    payload: dict = {
        "userId": user_id,
        "deviceName": "个人通用",
        "expireAt": "2099-01-01",
        "clientToken": token,
    }
    if qpm is not None:
        payload["qpmLimit"] = qpm
    created = client.post("/admin-api/ims/air/key/generate", headers=auth, json=payload)
    assert created.json()["code"] == 0, created.text
    return created.json()["data"]


def mcp(plain: str, *, query: bool = False):
    if query:
        return client.post("/ims/mcp", params={"key": plain}, json=MCP_BODY)
    return client.post("/ims/mcp", headers={"Authorization": f"Bearer {plain}"}, json=MCP_BODY)


def test_generate_plain_once_and_61st_call_is_429():
    auth = headers()
    user_id = make_user(auth)
    issued = generate(auth, user_id, "plain-once")
    plain = issued["plainKey"]
    key_id = issued["keyId"]
    assert plain.startswith("air-")
    assert issued["qpmLimit"] == 60
    assert "configSnippets" in issued

    replay = client.post(
        "/admin-api/ims/air/key/generate",
        headers=auth,
        json={
            "userId": user_id,
            "deviceName": "个人通用",
            "expireAt": "2099-01-01",
            "clientToken": "plain-once",
        },
    )
    assert replay.json()["code"] == 1001
    assert plain not in replay.text

    again = client.post(
        "/admin-api/ims/air/key/generate",
        headers=auth,
        json={
            "userId": user_id,
            "deviceName": "个人通用",
            "expireAt": "2099-01-01",
            "clientToken": "plain-once-2",
        },
    )
    assert again.json()["code"] == 1001
    assert "BR-019" in again.json()["msg"]

    page = client.get("/admin-api/ims/air/cfg/key/page", headers=auth, params={"pageNo": 1, "pageSize": 100})
    assert plain not in page.text
    listed = next(row for row in page.json()["data"]["list"] if row["keyCode"] == issued["keyCode"])
    assert listed["qpmLimit"] == 60
    assert listed["keyMask"] != plain
    assert listed["keyMask"].startswith("air-")

    db = SessionLocal()
    try:
        stored = db.get(AirApiKey, key_id)
        assert stored is not None
        assert stored.key_hash == hash_key(plain)
        assert plain not in stored.key_hash
        assert stored.key_mask != plain
    finally:
        db.close()

    missing = client.post("/ims/mcp", json=MCP_BODY)
    assert missing.status_code == 401
    assert missing.json()["jsonrpc"] == "2.0"
    assert "msg" not in missing.json()

    moment = datetime(2026, 10, 8, 8, 0, 0)
    set_qpm_clock(lambda: moment)
    try:
        responses = [mcp(plain) for _ in range(61)]
        assert [item.status_code for item in responses[:60]] == [200] * 60
        denied = responses[60]
        assert denied.status_code == 429
        body = denied.json()
        assert body["jsonrpc"] == "2.0"
        assert body["error"]["code"] == 429
        assert body["error"]["message"] == "QPM 超限"
        assert "msg" not in body

        db = SessionLocal()
        try:
            denied_logs = list(
                db.scalars(
                    select(AirMcpLog).where(AirMcpLog.key_id == key_id, AirMcpLog.result_code == "429")
                ).all()
            )
            assert len(denied_logs) == 1
            assert denied_logs[0].tool == "skills.list"
            note = db.scalar(
                select(Notify).where(
                    Notify.event_type == "AIR_QPM_EXCEEDED",
                    Notify.biz_key.like(f"key:{key_id}:%"),
                    Notify.deleted == 0,
                )
            )
            assert note is not None
        finally:
            db.close()

        set_qpm_clock(lambda: moment + timedelta(minutes=1))
        rolled = mcp(plain, query=True)
        assert rolled.status_code == 200
        assert rolled.json()["jsonrpc"] == "2.0"
        assert "result" in rolled.json()
    finally:
        set_qpm_clock(None)

    revoked = client.post(f"/admin-api/ims/air/key/{key_id}/revoke", headers=auth, json={"reason": "测试吊销"})
    assert revoked.json()["code"] == 0
    assert mcp(plain).status_code == 401


def test_renew_qpm_applies_in_the_same_minute():
    auth = headers()
    user_id = make_user(auth)
    issued = generate(auth, user_id, "renew-qpm", qpm=2)
    plain = issued["plainKey"]
    key_id = issued["keyId"]
    moment = datetime(2026, 10, 8, 9, 30, 0)
    set_qpm_clock(lambda: moment)
    try:
        assert [mcp(plain).status_code for _ in range(2)] == [200, 200]
        blocked = mcp(plain)
        assert blocked.status_code == 429

        renewed = client.post(
            f"/admin-api/ims/air/key/{key_id}/renew",
            headers=auth,
            json={"qpmLimit": 4, "expireAt": "2099-06-01", "deviceName": "个人通用"},
        )
        assert renewed.json()["code"] == 0, renewed.text
        fresh = renewed.json()["data"]
        new_plain = fresh["plainKey"]
        assert fresh["qpmLimit"] == 4
        assert new_plain.startswith("air-")
        assert new_plain != plain

        assert [mcp(new_plain).status_code for _ in range(4)] == [200, 200, 200, 200]
        assert mcp(new_plain).status_code == 429
        assert mcp(plain).status_code == 429

        page = client.get("/admin-api/ims/air/cfg/key/page", headers=auth, params={"pageNo": 1, "pageSize": 100})
        assert new_plain not in page.text
        row = next(item for item in page.json()["data"]["list"] if item["keyCode"] == fresh["keyCode"])
        assert row["qpmLimit"] == 4
    finally:
        set_qpm_clock(None)
