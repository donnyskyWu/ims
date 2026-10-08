"""experts.assemble 产物结构、授权落库、审计日志，以及连续认证失败冻结。"""

import os
import uuid
from datetime import datetime, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.air_key import set_qpm_clock
from app.core import SessionLocal
from app.main import app
from app.models import AirApiKey, AirExpertGrant, AirMcpLog, Notify, User

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def make_user(auth: dict, prefix: str) -> int:
    suffix = uuid.uuid4().hex[:8]
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={
            "username": f"{prefix}{suffix}",
            "nickname": f"{prefix}{suffix}",
            "password": "Admin@123",
            "mobile": f"138{suffix}",
        },
    )
    assert created.json()["code"] == 0, created.text
    return int(created.json()["data"]["id"])


def generate_key(auth: dict, user_id: int) -> str:
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
    return created.json()["data"]["plainKey"]


def publish_skill(auth: dict, name: str) -> dict:
    created = client.post(
        "/admin-api/ims/air/skill",
        headers=auth,
        json={"skillName": name, "category": "内容生产"},
    )
    skill = created.json()["data"]
    client.put(f"/admin-api/ims/air/skill/{skill['id']}/submit-audit", headers=auth)
    approved = client.put(
        f"/admin-api/ims/air/skill/{skill['id']}/audit",
        headers=auth,
        json={"approve": True},
    )
    assert approved.json()["data"]["status"] == "PUBLISHED"
    return approved.json()["data"]


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


def test_assemble_package_grant_and_audit_log():
    auth = headers()
    owner_id = make_user(auth, "exp")
    outsider_id = make_user(auth, "exo")
    skill = publish_skill(auth, f"组装技能{uuid.uuid4().hex[:6]}")
    created = client.post(
        "/admin-api/ims/air/expert",
        headers=auth,
        json={
            "expertName": f"组装专家{uuid.uuid4().hex[:6]}",
            "scene": "直播复盘",
            "systemPrompt": "只组装，不执行模型。",
            "skillIds": [skill["id"]],
            "toolWhitelist": ["experts.assemble"],
        },
    )
    assert created.json()["code"] == 0, created.text
    expert_id = created.json()["data"]["id"]
    code = created.json()["data"]["expertCode"]
    client.put(f"/admin-api/ims/air/expert/{expert_id}/publish", headers=auth)
    granted = client.post(
        "/admin-api/ims/air/expert/grant",
        headers=auth,
        json={"expertId": expert_id, "grantType": "PERSON", "grantId": owner_id},
    )
    assert granted.json()["code"] == 0, granted.text
    db = SessionLocal()
    try:
        row = db.get(AirExpertGrant, granted.json()["data"]["grantId"])
        assert row is not None
        assert row.status == "ACTIVE"
        assert row.grant_type == "PERSON"
        assert row.grant_id_ref == owner_id
    finally:
        db.close()

    owner_key = generate_key(auth, owner_id)
    outsider_key = generate_key(auth, outsider_id)
    hidden = mcp(outsider_key, "experts.list")
    assert code not in [item["code"] for item in hidden.json()["result"]["items"]]
    denied = mcp(outsider_key, "experts.assemble", {"code": code, "message": "你好"})
    assert denied.status_code == 403
    assert denied.json()["error"]["message"] == "未授权"
    assert "knowledgeContext" not in denied.json()

    listed = mcp(owner_key, "experts.list")
    assert code in [item["code"] for item in listed.json()["result"]["items"]]
    packed = mcp(owner_key, "experts.assemble", {"code": code, "message": "请复盘"})
    assert packed.status_code == 200, packed.text
    body = packed.json()
    assert "msg" not in body
    result = body["result"]
    assert set(result) == {"systemPrompt", "skillRefs", "guidelines"}
    assert result["systemPrompt"] == "只组装，不执行模型。"
    assert result["skillRefs"] == [{"code": skill["skillNo"], "md": ""}]
    assert "网关不执行模型" in result["guidelines"]
    assert "knowledgeContext" not in result
    assert "knowledge_context" not in result

    client.put(f"/admin-api/ims/air/skill/{skill['id']}/status", headers=auth, json={"status": "DISABLED"})
    dropped = mcp(owner_key, "experts.assemble", {"code": code, "message": "再来一次"})
    assert dropped.status_code == 200
    assert dropped.json()["result"]["skillRefs"] == []

    db = SessionLocal()
    try:
        logs = list(
            db.scalars(
                select(AirMcpLog).where(AirMcpLog.tool == "experts.assemble", AirMcpLog.user_id == owner_id)
            ).all()
        )
        assert len(logs) == 2
        assert all(row.token_cnt == 0 for row in logs)
        assert all(row.cost_ms >= 0 for row in logs)
        assert {row.filter_hit for row in logs} == {0, 1}
        key_id = logs[0].key_id
    finally:
        db.close()

    audit = client.get(
        "/admin-api/ims/air/mcp/audit-log",
        headers=auth,
        params={"tool": "experts.assemble", "keyId": key_id, "result": "SUCCESS", "pageNo": 1, "pageSize": 10},
    )
    assert audit.json()["code"] == 0, audit.text
    rows = audit.json()["data"]["list"]
    assert len(rows) == 2
    assert {row["tool"] for row in rows} == {"experts.assemble"}
    assert {row["tokenCnt"] for row in rows} == {0}
    assert {row["filterHit"] for row in rows} == {0, 1}
    assert all(row["costMs"] >= 0 and row["authNote"] for row in rows)


def test_ten_auth_failures_freeze_key():
    auth = headers()
    user_id = make_user(auth, "frz")
    plain = generate_key(auth, user_id)
    base = datetime(2026, 10, 8, 3, 0, 0)
    try:
        set_qpm_clock(lambda: base)
        for _ in range(9):
            denied = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
            assert denied.status_code == 403
        db = SessionLocal()
        try:
            key = db.scalar(select(AirApiKey).where(AirApiKey.owner_user_id == user_id, AirApiKey.deleted == 0))
            assert key is not None
            assert key.status == "ACTIVE"
            key_id = key.id
        finally:
            db.close()

        set_qpm_clock(lambda: base + timedelta(minutes=11))
        still = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
        assert still.status_code == 403
        db = SessionLocal()
        try:
            key = db.get(AirApiKey, key_id)
            assert key.status == "ACTIVE"
        finally:
            db.close()

        set_qpm_clock(lambda: base + timedelta(minutes=12))
        for _ in range(8):
            assert mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"}).status_code == 403
        locked = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
        assert locked.status_code == 403
        blocked = mcp(plain, "skills.get", {"code": "SKL-NO-SUCH"})
        assert blocked.status_code == 401
        assert "FROZEN" in blocked.json()["error"]["message"]
    finally:
        set_qpm_clock(None)

    db = SessionLocal()
    try:
        key = db.get(AirApiKey, key_id)
        assert key.status == "FROZEN"
        assert key.freeze_reason == "认证失败锁定"
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        notes = list(
            db.scalars(select(Notify).where(Notify.event_type == "AIR_AUTH_LOCK", Notify.deleted == 0)).all()
        )
        receivers = {row.receiver_user_id for row in notes if row.biz_key.startswith(f"key:{key_id}:")}
        assert user_id in receivers
        assert admin is not None and admin.id in receivers
    finally:
        db.close()
