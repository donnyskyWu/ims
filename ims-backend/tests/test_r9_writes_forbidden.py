"""BUG-080：标准 R9（tc_r9）只有查询级权限，列出的写接口必须 HTTP 403。"""

import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import Role, User, UserRole

client = TestClient(app)

# 实名人没有写入接口（只有 GET /corp/resource/realname/page 与 /{id}），这里不造 POST。
WRITES = (
    ("POST", "/admin-api/ims/master/platform-account", {"platformType": "DOUYIN", "accountName": "r9-deny"}),
    ("POST", "/admin-api/ims/account/apply", {"accountId": 1, "purpose": "领用", "planStart": "2026-01-01", "planEnd": "2026-01-02"}),
    ("POST", "/admin-api/ims/account/return/submit", {"accountId": 1, "remark": "归还"}),
    ("POST", "/admin-api/ims/account/transfer", {"accountId": 1, "transferType": "RECALL", "reasonType": "OTHER", "remark": "收回"}),
    ("POST", "/admin-api/ims/account/transfer", {"accountId": 1, "transferType": "TRANSFER", "toUserId": 1, "reasonType": "OTHER", "remark": "流转"}),
    ("POST", "/admin-api/ims/account/recharge", {"accountId": 1, "amount": 1, "channel": "ALIPAY", "rechargeDate": "2026-01-01"}),
    ("POST", "/admin-api/ims/account/1/unfreeze", {"remark": "解冻"}),
    ("POST", "/admin-api/ims/account/1/recycle", {"remark": "回收回池"}),
    ("POST", "/admin-api/ims/cost/account/1/process", {"amount": 1}),
    ("POST", "/admin-api/ims/fin/period/close", {"periodMonth": "2026-01"}),
    ("POST", "/admin-api/ims/fin/cost/S1", {"commissionRate": 0.1}),
    ("POST", "/admin-api/ims/fin/cost/S1/correction", {"corrected": {"commissionRate": 0.1}, "correctionReason": "更正"}),
    ("PUT", "/admin-api/ims/fin/cost/S1/confirm", None),
    ("PUT", "/admin-api/ims/fin/share/result/1/audit", {"conclusion": "APPROVE", "auditRole": "FINANCE", "remark": ""}),
    ("POST", "/admin-api/ims/fin/share/rule", {"ruleName": "r9-deny"}),
)


def login(username="tc_r9", password="Admin@123") -> dict:
    logged = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert logged.status_code == 200, logged.text
    token = logged.json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_tc_r9_is_query_only_and_writes_403():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "tc_r9", User.deleted == 0))
        assert user is not None
        role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
        roles = list(db.scalars(select(Role).where(Role.id.in_(role_ids), Role.deleted == 0)).all())
        assert [role.role_key for role in roles] == ["R9"]
    finally:
        db.close()

    headers = login()
    access = client.get("/admin-api/ims/auth/access", headers=headers).json()["data"]
    assert access["admin"] is False
    assert access["permCodes"]
    assert all("W" not in level and "D" not in level for level in access["permLevels"].values())
    readable = client.get("/admin-api/ims/corp/resource/realname/page", headers=headers)
    assert readable.status_code == 200
    assert readable.json()["code"] == 0

    for method, path, body in WRITES:
        response = client.request(method, path, headers=headers, json=body)
        assert response.status_code == 403, (method, path, response.status_code, response.text)
        assert response.json()["code"] == 403, (method, path, response.json())
