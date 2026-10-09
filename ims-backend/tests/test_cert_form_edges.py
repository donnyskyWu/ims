"""#238 · 驳回原因必填，角色编码拒绝空格和超长。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def upload(auth: dict, holder: str) -> int:
    created = client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "PASSPORT",
            "certNoPlain": f"P{uuid.uuid4().hex[:10]}",
            "fileKey": "local/cert/edge",
            "issueDate": "2020-01-01",
            "expireDate": "2030-01-01",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    return int(body["data"]["id"])


def listed(auth: dict, holder: str) -> int:
    page = client.get(
        "/admin-api/ims/corp/resource/certificate/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "holderName": holder},
    )
    body = page.json()
    assert body["code"] == 0, body
    return int(body["data"]["total"])


def test_review_reject_requires_remark_and_approve_still_works():
    auth = headers()
    holder = f"E2E-Cert-Edge-{uuid.uuid4().hex[:8]}"
    cert_id = upload(auth, holder)
    assert listed(auth, holder) == 1

    missing = client.put(
        f"/admin-api/ims/cert/archive/{cert_id}/review",
        headers=auth,
        json={"action": "REJECT", "remark": "   "},
    )
    assert missing.json()["code"] == 1001
    assert "驳回须填写原因" in missing.json()["msg"]
    assert listed(auth, holder) == 1

    long_remark = client.put(
        f"/admin-api/ims/cert/archive/{cert_id}/review",
        headers=auth,
        json={"action": "REJECT", "remark": "原因" * 101},
    )
    assert long_remark.json()["code"] == 1001
    assert "不超过 200" in long_remark.json()["msg"]
    assert listed(auth, holder) == 1

    rejected = client.put(
        f"/admin-api/ims/cert/archive/{cert_id}/review",
        headers=auth,
        json={"action": "REJECT", "remark": "影像模糊"},
    )
    assert rejected.json()["code"] == 0
    assert listed(auth, holder) == 0

    other = f"E2E-Cert-Edge-Ok-{uuid.uuid4().hex[:8]}"
    other_id = upload(auth, other)
    approved = client.put(
        f"/admin-api/ims/cert/archive/{other_id}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approved.json()["code"] == 0
    assert listed(auth, other) == 1


def test_level_role_rejects_space_and_overlong_code():
    auth = headers()
    ok = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={
            "rules": [{"target": "ROLE", "targetCode": "sys:admin", "viewLevel": 2}],
            "l3Whitelist": [],
            "opacity": 0.12,
            "position": "bottom-right",
        },
    )
    assert ok.json()["code"] == 0

    spaced = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={
            "rules": [{"target": "ROLE", "targetCode": "sys admin", "viewLevel": 2}],
            "l3Whitelist": [],
        },
    )
    assert spaced.json()["code"] == 1001
    assert "不能含空格" in spaced.json()["msg"]

    long_code = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={
            "rules": [{"target": "ROLE", "targetCode": "r" * 65, "viewLevel": 2}],
            "l3Whitelist": [],
        },
    )
    assert long_code.json()["code"] == 1001
    assert "不超过 64" in long_code.json()["msg"]

    loaded = client.get("/admin-api/ims/cert/security/level-config", headers=auth).json()
    assert loaded["code"] == 0
    assert loaded["data"]["rules"][0]["targetCode"] == "sys:admin"

    reset = client.put(
        "/admin-api/ims/cert/security/level-config",
        headers=auth,
        json={"rules": [], "l3Whitelist": [], "opacity": 0.12, "position": "bottom-right"},
    )
    assert reset.json()["code"] == 0
