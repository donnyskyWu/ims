"""#127 · 证件数字化率、查看级别、原图签名链接。"""

import os
import time
import uuid
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import app
from app.cert_access import TICKETS
from app.models import CertViewLog, Menu, Role, RoleMenu, User, UserRole
from app.security import hash_password

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def upload(auth: dict, holder: str, number: str, days: int = 400):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": number,
            "fileKey": f"local/cert/{number}",
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


def make_user(role_name: str) -> str:
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
            role_key=f"cert:{uuid.uuid4().hex[:8]}",
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


def metrics(auth: dict) -> dict:
    body = client.get("/admin-api/ims/cert/archive/digital-metrics", headers=auth).json()
    assert body["code"] == 0, body
    return body["data"]


def test_digital_rate_level_and_signed_file_url():
    auth = headers()
    before = metrics(auth)
    holder = f"UT-Cert-URL-{uuid.uuid4().hex[:8]}"
    number = f"UT{uuid.uuid4().hex[:12]}"
    created = upload(auth, holder, number)
    body = created.json()
    assert body["code"] == 0, body
    cert_id = body["data"]["id"]
    assert "certNoPlain" not in body["data"]
    pending = metrics(auth)
    assert pending["totalExpected"] == before["totalExpected"] + 1
    assert pending["digitalizedCount"] == before["digitalizedCount"]
    assert pending["digitalizedRate"] == round(pending["digitalizedCount"] / pending["totalExpected"], 4)

    blocked = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=auth).json()
    assert blocked["code"] == 1033
    assert "1033" in blocked["msg"]

    approve(auth, cert_id)
    still = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=auth).json()
    assert still["code"] == 1034
    assert "1034" in still["msg"]
    done = metrics(auth)
    assert done["digitalizedCount"] == before["digitalizedCount"] + 1
    assert done["totalExpected"] == before["totalExpected"] + 1
    assert done["digitalizedRate"] == round(done["digitalizedCount"] / done["totalExpected"], 4)

    peer = headers(make_user("普通同事"))
    denied = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=peer,
        json={"rules": [], "l3Whitelist": []},
    ).json()
    assert denied["code"] == 1008

    missing = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={"rules": [{"target": "ROLE", "targetCode": "sys:admin", "viewLevel": 2}], "l3Whitelist": [99999999]},
    ).json()
    assert missing["code"] == 1500

    plain_user = make_user("普通同事")
    db = SessionLocal()
    try:
        plain_id = db.scalar(select(User.id).where(User.username == plain_user))
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))
    finally:
        db.close()
    rejected = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={"rules": [{"target": "ROLE", "targetCode": "sys:admin", "viewLevel": 3}], "l3Whitelist": [plain_id]},
    ).json()
    assert rejected["code"] == 1001

    saved = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={
            "rules": [{"target": "ROLE", "targetCode": "sys:admin", "viewLevel": 2}],
            "l3Whitelist": [],
            "opacity": 0.12,
            "position": "bottom-right",
        },
    ).json()
    assert saved["code"] == 0
    loaded = client.get("/admin-api/ims/cert/security/level-config", headers=auth).json()
    assert loaded["code"] == 0
    assert loaded["data"]["rules"][0]["targetCode"] == "sys:admin"
    assert loaded["data"]["l3Whitelist"] == []

    opened = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=auth).json()
    assert opened["code"] == 0, opened
    assert opened["data"]["expiresInSeconds"] == 60
    assert "管理员" in opened["data"]["watermark"]["text"]
    assert number not in str(opened)
    token = opened["data"]["signedUrl"].split("token=", 1)[1]
    preview = client.get("/admin-api/ims/cert/archive/file", headers=auth, params={"token": token}).json()
    assert preview["code"] == 0
    assert preview["data"]["download"] is False
    assert "禁止下载" in preview["data"]["preview"]
    assert "fileKey" not in preview["data"]

    TICKETS[token]["exp"] = time.time() - 5
    expired = client.get("/admin-api/ims/cert/archive/file", headers=auth, params={"token": token}).json()
    assert expired["code"] == 1002

    clerk_name = make_user("行政专员")
    clerk = headers(clerk_name)
    clerk_blocked = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=clerk).json()
    assert clerk_blocked["code"] == 1034
    db = SessionLocal()
    try:
        clerk_id = db.scalar(select(User.id).where(User.username == clerk_name))
    finally:
        db.close()
    lifted = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={
            "rules": [{"target": "ROLE", "targetCode": "sys:admin", "viewLevel": 2}],
            "l3Whitelist": [admin_id, clerk_id],
        },
    ).json()
    assert lifted["code"] == 0
    plain = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=clerk).json()
    assert plain["code"] == 0, plain
    assert "watermark" not in plain["data"]
    plain_token = plain["data"]["signedUrl"].split("token=", 1)[1]
    stolen = client.get("/admin-api/ims/cert/archive/file", headers=auth, params={"token": plain_token}).json()
    assert stolen["code"] == 1008
    own = client.get("/admin-api/ims/cert/archive/file", headers=clerk, params={"token": plain_token}).json()
    assert own["code"] == 0
    assert own["data"]["viewLevel"] == 3
    assert own["data"]["download"] is False
    assert own["data"]["fileKey"] == f"local/cert/{number}"


def test_file_url_eleventh_view_is_1035():
    auth = headers()
    saved = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={"rules": [{"target": "ROLE", "targetCode": "sys:admin", "viewLevel": 2}], "l3Whitelist": []},
    ).json()
    assert saved["code"] == 0
    holder = f"UT-Cert-FreqURL-{uuid.uuid4().hex[:8]}"
    number = f"FQ{uuid.uuid4().hex[:12]}"
    created = upload(auth, holder, number)
    cert_id = created.json()["data"]["id"]
    approve(auth, cert_id)
    for _ in range(10):
        opened = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=auth).json()
        assert opened["code"] == 0, opened
    blocked = client.get(f"/admin-api/ims/cert/archive/{cert_id}/file-url", headers=auth).json()
    assert blocked["code"] == 1035
    db = SessionLocal()
    try:
        count = int(
            db.scalar(
                select(func.count()).select_from(CertViewLog).where(CertViewLog.cert_id == cert_id, CertViewLog.deleted == 0)
            )
            or 0
        )
    finally:
        db.close()
    assert count == 10
