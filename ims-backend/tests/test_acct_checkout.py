import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import E2E_POOL_ACCOUNT_NO, refresh_acct_e2e_pool
from app.core import Base, engine
from app.main import app, init_db
from app.models import User
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import PlatformAccount
from sqlalchemy import select

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def pool_account_id() -> int:
    ops = ops_session()
    try:
        row = ops.scalar(
            select(PlatformAccount.id).where(
                PlatformAccount.account_no == E2E_POOL_ACCOUNT_NO,
                PlatformAccount.deleted == 0,
            )
        )
        assert row is not None
        return int(row)
    finally:
        ops.close()


def test_acct_checkout_and_return_flow():
    auth = headers()
    from app.core import SessionLocal

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        refresh_acct_e2e_pool(db, admin)
        db.commit()
    finally:
        db.close()

    account_id = pool_account_id()
    apply = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "pytest 领用",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    assert apply.json()["code"] == 0
    apply_id = apply.json()["data"]["id"]

    dup = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "重复",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    assert dup.json()["code"] == 1023

    approve = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/approve",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approve.json()["code"] == 0

    confirm = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/confirm",
        headers=auth,
        json={"passwordReset": True},
    )
    assert confirm.json()["code"] == 0

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row.status == "IN_USE"
        assert row.holder_user_id == 1
    finally:
        ops.close()

    blocked = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "1021",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    assert blocked.json()["code"] == 1021

    ret = client.post(
        "/admin-api/ims/account/return/submit",
        headers=auth,
        json={"accountId": account_id},
    )
    assert ret.json()["code"] == 0
    assert ret.json()["data"]["status"] == "RETURNED"

    tl = client.get(f"/admin-api/ims/account/timeline/{account_id}", headers=auth)
    types = {item["eventType"] for item in tl.json()["data"]["list"]}
    assert "APPLY" in types
    assert "RETURN" in types
