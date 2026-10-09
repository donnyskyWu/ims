"""#138 · 已归还账号回收回池、池状态、交接凭证导出。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app
from app.acct_seed import ensure_acct_peer_user
from app.core import SessionLocal
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def make_account(account_no: str, status: str = "IN_POOL") -> int:
    ops = ops_session()
    try:
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type="DOUYIN",
            status=status,
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        ops.refresh(row)
        return int(row.id)
    finally:
        ops.close()


def checkout(auth: dict, account_id: int) -> None:
    apply = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "pytest 回收前领用",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    body = apply.json()
    assert body["code"] == 0, body
    apply_id = body["data"]["id"]
    approved = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/approve",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approved.json()["code"] == 0
    confirmed = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/confirm",
        headers=auth,
        json={"passwordReset": True},
    )
    assert confirmed.json()["code"] == 0, confirmed.json()


def test_recycle_returned_account_to_pool_and_export_voucher():
    auth = headers()
    account_id = make_account(f"AC-PY-RECYCLE-{uuid.uuid4().hex[:8]}")

    early = client.post(
        f"/admin-api/ims/account/{account_id}/recycle",
        headers=auth,
        json={"remark": "还在池里"},
    )
    assert early.json()["code"] == 1023

    blank = client.post(
        f"/admin-api/ims/account/{account_id}/recycle",
        headers=auth,
        json={"remark": "  "},
    )
    assert blank.json()["code"] == 1001

    checkout(auth, account_id)
    frozen = make_account(f"AC-PY-FROZEN-{uuid.uuid4().hex[:8]}", "FROZEN")
    frozen_blocked = client.post(
        f"/admin-api/ims/account/{frozen}/recycle",
        headers=auth,
        json={"remark": "冻结不能回收"},
    )
    assert frozen_blocked.json()["code"] == 1023
    assert "解冻" in frozen_blocked.json()["msg"]

    returned = client.post(
        "/admin-api/ims/account/return/submit",
        headers=auth,
        json={"accountId": account_id},
    )
    assert returned.json()["code"] == 0
    assert returned.json()["data"]["status"] == "RETURNED"

    db = SessionLocal()
    try:
        ensure_acct_peer_user(db)
        db.commit()
    finally:
        db.close()
    peer = headers("e2e_acct_peer")
    denied = client.post(
        f"/admin-api/ims/account/{account_id}/recycle",
        headers=peer,
        json={"remark": "同事不能回收"},
    )
    assert denied.json()["code"] == 1008

    done = client.post(
        f"/admin-api/ims/account/{account_id}/recycle",
        headers=auth,
        json={"remark": "pytest 回收回池"},
    )
    assert done.json()["code"] == 0, done.json()
    assert done.json()["data"]["status"] == "IN_POOL"

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row.status == "IN_POOL"
        assert row.holder_user_id is None
    finally:
        ops.close()

    again = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "回收后可再领用",
            "planStart": "2026-10-09",
            "planEnd": "2026-12-09",
        },
    )
    assert again.json()["code"] == 0, again.json()

    status = client.get("/admin-api/ims/corp/account/status/summary", headers=auth, params={"platformType": "DOUYIN"})
    body = status.json()
    assert body["code"] == 0, body
    assert body["data"]["counts"]["IN_POOL"] >= 1
    assert "RETURNED" in body["data"]["counts"]
    missing = client.get("/admin-api/ims/corp/account/status/summary", headers=auth)
    assert missing.json()["code"] == 1001

    events = client.get(
        "/admin-api/ims/account/timeline/events",
        headers=auth,
        params={"accountId": account_id, "eventType": "RECYCLE", "pageNo": 1, "pageSize": 10},
    )
    event_body = events.json()
    assert event_body["code"] == 0, event_body
    assert event_body["data"]["total"] >= 1
    assert event_body["data"]["list"][0]["eventLabel"] == "回收回池"
    assert "回收回池" in event_body["data"]["list"][0]["snapshotSummary"]

    bad_type = client.get(
        "/admin-api/ims/account/timeline/events",
        headers=auth,
        params={"eventType": "NOT_A_TYPE"},
    )
    assert bad_type.json()["code"] == 1001

    exported = client.get(f"/admin-api/ims/account/timeline/{account_id}/export", headers=auth)
    export_body = exported.json()
    assert export_body["code"] == 0, export_body
    assert export_body["data"]["exportTaskId"]
    assert export_body["data"]["message"] == "交接凭证已生成"
    download = export_body["data"]["downloadUrl"]
    file_res = client.get(download, headers=auth)
    assert file_res.status_code == 200
    assert file_res.content.startswith(b"%PDF")
    assert "回收回池" in file_res.content.decode("latin1", errors="ignore") or len(file_res.content) > 200

    expired = client.get(
        f"/admin-api/ims/account/timeline/{account_id}/export/file",
        headers=auth,
        params={"token": "missing-token"},
    )
    assert expired.json()["code"] == 1002
