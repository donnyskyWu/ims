"""技能审核发布后，命中授权的 Key 能在 skills.list 看到；停用后立即看不到；未授权 skills.get 返回 403。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import AirEvent, AirSkillGrant, Role, UserDept, UserRole

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
            "mobile": f"137{suffix}",
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
    plain = created.json()["data"]["plainKey"]
    assert plain.startswith("air-")
    return plain


def publish_skill(auth: dict, name: str) -> dict:
    created = client.post(
        "/admin-api/ims/air/skill",
        headers=auth,
        json={"skillName": name, "category": "内容生产"},
    )
    assert created.json()["code"] == 0, created.text
    skill = created.json()["data"]
    submitted = client.put(f"/admin-api/ims/air/skill/{skill['id']}/submit-audit", headers=auth)
    assert submitted.json()["data"]["status"] == "PENDING"
    assert submitted.json()["data"]["auditStatus"] == "PENDING"
    approved = client.put(
        f"/admin-api/ims/air/skill/{skill['id']}/audit",
        headers=auth,
        json={"approve": True},
    )
    assert approved.json()["code"] == 0, approved.text
    assert approved.json()["data"]["status"] == "PUBLISHED"
    assert approved.json()["data"]["auditStatus"] == "APPROVED"
    return approved.json()["data"]


def grant(auth: dict, skill_id: int, grant_type: str, grant_id: int, all_staff: bool = False) -> dict:
    created = client.post(
        "/admin-api/ims/air/skill/grant",
        headers=auth,
        json={"skillId": skill_id, "grantType": grant_type, "grantId": grant_id, "allStaff": all_staff},
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


def listed_codes(plain: str) -> list[str]:
    response = mcp(plain, "skills.list")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["jsonrpc"] == "2.0"
    assert "msg" not in body
    return [item["code"] for item in body["result"]["items"]]


def test_published_skill_lists_for_granted_keys_then_hides_on_disable():
    auth = headers()
    person_id = make_user(auth, "skp")
    dept_user_id = make_user(auth, "skd")
    role_user_id = make_user(auth, "skr")
    outsider_id = make_user(auth, "sko")
    dept_id = 88089
    db = SessionLocal()
    try:
        db.add(UserDept(user_id=dept_user_id, dept_id=dept_id, tenant_id=0))
        role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
        assert role is not None
        role_id = role.id
        db.add(UserRole(user_id=role_user_id, role_id=role_id, tenant_id=0))
        db.commit()
    finally:
        db.close()

    skill = publish_skill(auth, f"可见性{uuid.uuid4().hex[:6]}")
    skill_id = skill["id"]
    code = skill["skillNo"]
    person_key = generate_key(auth, person_id)
    dept_key = generate_key(auth, dept_user_id)
    role_key = generate_key(auth, role_user_id)
    outsider_key = generate_key(auth, outsider_id)

    assert code not in listed_codes(person_key)

    person_grant = grant(auth, skill_id, "PERSON", person_id)
    assert person_grant["status"] == "ACTIVE"
    assert person_grant["grantType"] == "PERSON"
    assert person_grant["syncEventId"].startswith("air-evt-")
    dept_grant = grant(auth, skill_id, "DEPT", dept_id)
    assert dept_grant["grantType"] == "DEPT"
    assert dept_grant["grantName"] == f"部门#{dept_id}"
    role_grant = grant(auth, skill_id, "ROLE", role_id)
    assert role_grant["grantType"] == "ROLE"

    db = SessionLocal()
    try:
        event_id = int(person_grant["syncEventId"].removeprefix("air-evt-"))
        event = db.get(AirEvent, event_id)
        assert event is not None
        assert event.event_type == "SKILL_GRANT"
        assert event.payload["skillId"] == skill_id
    finally:
        db.close()

    for plain in (person_key, dept_key, role_key):
        codes = listed_codes(plain)
        assert code in codes
        response = mcp(plain, "skills.list")
        item = next(row for row in response.json()["result"]["items"] if row["code"] == code)
        assert item["name"] == skill["skillName"]
        assert item["ver"]
    assert code not in listed_codes(outsider_key)

    denied = mcp(outsider_key, "skills.get", {"code": code})
    assert denied.status_code == 403
    body = denied.json()
    assert body["jsonrpc"] == "2.0"
    assert body["error"]["code"] == 403
    assert body["error"]["message"] == "未授权"
    assert "msg" not in body
    allowed = mcp(person_key, "skills.get", {"code": code})
    assert allowed.status_code == 200
    assert allowed.json()["result"]["code"] == code

    missing = mcp(person_key, "skills.get", {"code": "SKL-NO-SUCH"})
    assert missing.status_code == 403

    revoked = client.delete(f"/admin-api/ims/air/skill/grant/{person_grant['grantId']}", headers=auth)
    assert revoked.json()["code"] == 0
    assert revoked.json()["data"] is None
    assert code not in listed_codes(person_key)
    assert code in listed_codes(dept_key)
    assert code in listed_codes(role_key)

    disabled = client.put(
        f"/admin-api/ims/air/skill/{skill_id}/status",
        headers=auth,
        json={"status": "DISABLED"},
    )
    assert disabled.json()["code"] == 0
    assert disabled.json()["data"] is None
    detail = client.get(f"/admin-api/ims/air/skill/{skill_id}", headers=auth)
    assert detail.json()["data"]["status"] == "DISABLED"
    assert any(item["status"] == "ACTIVE" and item["grantType"] == "DEPT" for item in detail.json()["data"]["grants"])
    for plain in (person_key, dept_key, role_key, outsider_key):
        assert code not in listed_codes(plain)
        hidden = mcp(plain, "skills.get", {"code": code})
        assert hidden.status_code == 403

    enabled = client.put(
        f"/admin-api/ims/air/skill/{skill_id}/status",
        headers=auth,
        json={"status": "ENABLED"},
    )
    assert enabled.json()["code"] == 0
    assert code in listed_codes(dept_key)
    assert code in listed_codes(role_key)
    assert code not in listed_codes(person_key)
    assert mcp(outsider_key, "skills.get", {"code": code}).status_code == 403

    db = SessionLocal()
    try:
        kept = db.get(AirSkillGrant, dept_grant["grantId"])
        assert kept is not None
        assert kept.status == "ACTIVE"
    finally:
        db.close()


def test_grant_requires_published_skill_and_known_target():
    auth = headers()
    created = client.post(
        "/admin-api/ims/air/skill",
        headers=auth,
        json={"skillName": f"未发布{uuid.uuid4().hex[:6]}", "category": "内容生产"},
    )
    skill_id = created.json()["data"]["id"]
    blocked = client.post(
        "/admin-api/ims/air/skill/grant",
        headers=auth,
        json={"skillId": skill_id, "grantType": "PERSON", "grantId": 1},
    )
    assert blocked.json()["code"] == 1001
    assert "BR-025" in blocked.json()["msg"]

    skill = publish_skill(auth, f"对象{uuid.uuid4().hex[:6]}")
    unknown = client.post(
        "/admin-api/ims/air/skill/grant",
        headers=auth,
        json={"skillId": skill["id"], "grantType": "PERSON", "grantId": 99999999},
    )
    assert unknown.json()["code"] == 1001
    assert unknown.json()["msg"] == "授权对象不存在"
    bad_dept = client.post(
        "/admin-api/ims/air/skill/grant",
        headers=auth,
        json={"skillId": skill["id"], "grantType": "DEPT", "grantId": 424242},
    )
    assert bad_dept.json()["code"] == 1001
    assert bad_dept.json()["msg"] == "授权对象不存在"

    opened = grant(auth, skill["id"], "PERSON", 1, all_staff=True)
    assert opened["allStaff"] is True
    assert opened["grantName"] == "全员"
    plain = generate_key(auth, make_user(auth, "ska"))
    assert skill["skillNo"] in listed_codes(plain)
    client.delete(f"/admin-api/ims/air/skill/grant/{opened['grantId']}", headers=auth)
    assert skill["skillNo"] not in listed_codes(plain)
