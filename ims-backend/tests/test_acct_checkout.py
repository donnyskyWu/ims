import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import E2E_ACCT_FINANCE_USER, E2E_POOL_ACCOUNT_NO, refresh_acct_e2e_pool
from app.core import Base, engine
from app.main import app, init_db
from app.models import User
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import PlatformAccount
from sqlalchemy import select

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
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


def _reset_pool() -> int:
    from app.core import SessionLocal

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        refresh_acct_e2e_pool(db, admin)
        db.commit()
    finally:
        db.close()
    return pool_account_id()


def _recharge(auth: dict, account_id: int, amount: float, voucher: str | None = None, token: str | None = None):
    return client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": token or uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "amount": amount,
            "channel": "ALIPAY",
            "rechargeDate": "2026-10-08",
            "voucherUrl": voucher,
        },
    )


def test_acct_recharge_voucher_gate_and_finance_visibility():
    auth = headers()
    account_id = _reset_pool()

    small = _recharge(auth, account_id, 1000)
    assert small.json()["code"] == 0
    assert small.json()["data"]["voucherUrl"] is None
    assert small.json()["data"]["voucherAttached"] is False
    assert small.json()["data"]["verifyStatus"] == "UNVERIFIED"

    boundary = _recharge(auth, account_id, 5000)
    assert boundary.json()["code"] == 0

    blocked = _recharge(auth, account_id, 5000.01)
    assert blocked.json()["code"] == 1025

    missing_token = client.post(
        "/admin-api/ims/account/recharge",
        headers=auth,
        json={
            "accountId": account_id,
            "amount": 100,
            "channel": "ALIPAY",
            "rechargeDate": "2026-10-08",
        },
    )
    assert missing_token.json()["code"] == 1001

    voucher = "RC-E2E-VOUCHER-58"
    token = uuid.uuid4().hex
    paid = _recharge(auth, account_id, 6000, voucher, token)
    assert paid.json()["code"] == 0
    assert paid.json()["data"]["voucherAttached"] is True
    assert paid.json()["data"]["voucherUrl"] is None
    replay = _recharge(auth, account_id, 6000, voucher, token)
    assert replay.json()["code"] == 0
    assert replay.json()["data"]["id"] == paid.json()["data"]["id"]

    admin_list = client.get("/admin-api/ims/account/recharge/list", headers=auth, params={"accountId": account_id})
    assert admin_list.json()["code"] == 0
    rows = admin_list.json()["data"]["list"]
    assert admin_list.json()["data"]["total"] == 3
    big = next(row for row in rows if row["amount"] == 6000)
    assert big["voucherUrl"] is None
    assert big["voucherAttached"] is True
    assert all(row["voucherUrl"] is None for row in rows)

    finance = headers(E2E_ACCT_FINANCE_USER)
    fin_list = client.get(
        "/admin-api/ims/account/recharge/list",
        headers=finance,
        params={"accountId": account_id},
    )
    assert fin_list.json()["code"] == 0
    fin_big = next(row for row in fin_list.json()["data"]["list"] if row["amount"] == 6000)
    assert fin_big["voucherUrl"] == voucher

    tl = client.get(f"/admin-api/ims/account/timeline/{account_id}", headers=auth)
    assert "RECHARGE" in {item["eventType"] for item in tl.json()["data"]["list"]}
    assert voucher not in tl.json()["data"]["list"][0]["snapshotSummary"]
