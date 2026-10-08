import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import (
    E2E_ACCT_FINANCE_USER,
    E2E_ACCT_PEER_USER,
    E2E_POOL_ACCOUNT_NO,
    E2E_XFER_ACCOUNT_NO,
    refresh_acct_e2e_pool,
)
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


def account_id_of(account_no: str) -> int:
    ops = ops_session()
    try:
        row = ops.scalar(
            select(PlatformAccount.id).where(
                PlatformAccount.account_no == account_no,
                PlatformAccount.deleted == 0,
            )
        )
        assert row is not None
        return int(row)
    finally:
        ops.close()


def pool_account_id() -> int:
    return account_id_of(E2E_POOL_ACCOUNT_NO)


def user_id_of(username: str) -> int:
    from app.core import SessionLocal

    db = SessionLocal()
    try:
        row = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        assert row is not None
        return int(row.id)
    finally:
        db.close()


def checkout_in_use(auth: dict, account_id: int) -> None:
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
    assert apply.json()["code"] == 0, apply.json()
    apply_id = apply.json()["data"]["id"]
    approve = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/approve",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approve.json()["code"] == 0, approve.json()
    confirm = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/confirm",
        headers=auth,
        json={"passwordReset": True},
    )
    assert confirm.json()["code"] == 0, confirm.json()


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


def test_acct_other_user_1021_and_transfer_holder_change():
    auth = headers()
    peer_auth = headers(E2E_ACCT_PEER_USER)
    account_id = account_id_of(E2E_XFER_ACCOUNT_NO)
    admin_id = user_id_of("admin")
    peer_id = user_id_of(E2E_ACCT_PEER_USER)

    blocked_pool = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "池内不可流转",
        },
    )
    assert blocked_pool.json()["code"] == 1023

    checkout_in_use(auth, account_id)

    other = client.post(
        "/admin-api/ims/account/apply",
        headers=peer_auth,
        json={
            "accountId": account_id,
            "purpose": "他人领用",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    assert other.json()["code"] == 1021
    assert "已被领用" in other.json()["msg"]

    same_holder = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": admin_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "自己",
        },
    )
    assert same_holder.json()["code"] == 1001

    recall = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "收回不在本切片",
        },
    )
    assert recall.json()["code"] == 1001

    created = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 流转",
        },
    )
    assert created.json()["code"] == 0, created.json()
    transfer_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "PENDING_CONFIRM"
    assert created.json()["data"]["transferNo"].startswith("TR")
    assert created.json()["data"]["toUserName"] == "流转同事"

    dup = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "TRANSFER_POSITION",
            "remark": "重复流转",
        },
    )
    assert dup.json()["code"] == 1023

    wrong = client.put(
        f"/admin-api/ims/account/transfer/{transfer_id}/confirm",
        headers=auth,
        json={"accept": True},
    )
    assert wrong.json()["code"] == 1008

    revoked = client.put(
        f"/admin-api/ims/account/transfer/{transfer_id}/revoke",
        headers=auth,
        json={"remark": "pytest 撤销"},
    )
    assert revoked.json()["code"] == 0

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row.status == "IN_USE"
        assert row.holder_user_id == admin_id
    finally:
        ops.close()

    again = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 再次流转",
        },
    )
    assert again.json()["code"] == 0, again.json()
    transfer_id = again.json()["data"]["id"]

    confirmed = client.put(
        f"/admin-api/ims/account/transfer/{transfer_id}/confirm",
        headers=peer_auth,
        json={"accept": True},
    )
    assert confirmed.json()["code"] == 0, confirmed.json()

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row.status == "IN_USE"
        assert row.holder_user_id == peer_id
    finally:
        ops.close()

    listed = client.get(
        "/admin-api/ims/account/transfer/list",
        headers=auth,
        params={"accountId": account_id, "status": "EFFECTIVE"},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1
    assert listed.json()["data"]["list"][0]["status"] == "EFFECTIVE"
    assert listed.json()["data"]["list"][0]["toUserName"] == "流转同事"

    tl = client.get(f"/admin-api/ims/account/timeline/{account_id}", headers=auth)
    events = tl.json()["data"]["list"]
    transfer_events = [item for item in events if item["eventType"] == "TRANSFER"]
    assert transfer_events
    assert "流转同事" in transfer_events[0]["snapshotSummary"]
    assert "管理员" in transfer_events[0]["snapshotSummary"]
