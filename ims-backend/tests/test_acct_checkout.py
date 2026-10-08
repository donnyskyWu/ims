import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import (
    E2E_ACCT_FINANCE_USER,
    E2E_ACCT_PEER_USER,
    E2E_POOL_ACCOUNT_NO,
    E2E_RECALL_ACCOUNT_NO,
    E2E_RECON_ACCOUNT_NO,
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


def _recharge(
    auth: dict,
    account_id: int,
    amount: float,
    voucher: str | None = None,
    token: str | None = None,
    recharge_date: str = "2026-10-08",
):
    return client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": token or uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "amount": amount,
            "channel": "ALIPAY",
            "rechargeDate": recharge_date,
            "voucherUrl": voucher,
        },
    )


def _verify(auth: dict, account_id: int, month: str, platform: float | None):
    body: dict = {"month": month, "accountIds": [account_id]}
    if platform is not None:
        body["platformConsumed"] = platform
    return client.post("/admin-api/ims/account/recharge/verify", headers=auth, json=body)


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

    recall_blank = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "",
        },
    )
    assert recall_blank.json()["code"] == 1001

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


def test_acct_recall_freezes_and_blocks_1022():
    auth = headers()
    peer_auth = headers(E2E_ACCT_PEER_USER)
    from app.core import SessionLocal

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        refresh_acct_e2e_pool(db, admin)
        db.commit()
    finally:
        db.close()

    account_id = account_id_of(E2E_RECALL_ACCOUNT_NO)
    admin_id = user_id_of("admin")
    peer_id = user_id_of(E2E_ACCT_PEER_USER)

    pool_recall = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "池内不可收回",
        },
    )
    assert pool_recall.json()["code"] == 1023

    checkout_in_use(auth, account_id)

    peer_recall = client.post(
        "/admin-api/ims/account/transfer",
        headers=peer_auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "VIOLATION",
            "remark": "同事不可收回",
        },
    )
    assert peer_recall.json()["code"] == 1008

    with_target = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "收回不指定新人",
        },
    )
    assert with_target.json()["code"] == 1001

    pending = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "先挂起流转",
        },
    )
    assert pending.json()["code"] == 0, pending.json()
    pending_id = pending.json()["data"]["id"]
    blocked = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "待确认中不可收回",
        },
    )
    assert blocked.json()["code"] == 1023
    revoked = client.put(
        f"/admin-api/ims/account/transfer/{pending_id}/revoke",
        headers=auth,
        json={"remark": "撤销以便收回"},
    )
    assert revoked.json()["code"] == 0

    created = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 收回冻结",
        },
    )
    assert created.json()["code"] == 0, created.json()
    data = created.json()["data"]
    assert data["transferType"] == "RECALL"
    assert data["status"] == "EFFECTIVE"
    assert data["transferNo"].startswith("TR")
    assert data["toUserId"] is None
    assert data["toUserName"] is None
    recall_id = data["id"]

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row.status == "FROZEN"
        assert row.holder_user_id == admin_id
    finally:
        ops.close()

    apply_blocked = client.post(
        "/admin-api/ims/account/apply",
        headers=peer_auth,
        json={
            "accountId": account_id,
            "purpose": "冻结后再领用",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    assert apply_blocked.json()["code"] == 1022
    assert "冻结" in apply_blocked.json()["msg"]

    transfer_blocked = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "冻结后再流转",
        },
    )
    assert transfer_blocked.json()["code"] == 1022

    again = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "PRE_RESIGN",
            "remark": "重复收回",
        },
    )
    assert again.json()["code"] == 1022

    confirm_done = client.put(
        f"/admin-api/ims/account/transfer/{recall_id}/confirm",
        headers=auth,
        json={"accept": True},
    )
    assert confirm_done.json()["code"] == 1023

    listed = client.get(
        "/admin-api/ims/account/transfer/list",
        headers=auth,
        params={"accountId": account_id, "transferType": "RECALL"},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["list"][0]["status"] == "EFFECTIVE"
    assert listed.json()["data"]["list"][0]["transferType"] == "RECALL"

    tl = client.get(f"/admin-api/ims/account/timeline/{account_id}", headers=auth)
    freeze_events = [item for item in tl.json()["data"]["list"] if item["eventType"] == "FREEZE"]
    assert freeze_events
    assert "FROZEN" in freeze_events[0]["snapshotSummary"]
    assert "管理员" in freeze_events[0]["snapshotSummary"]


def test_acct_reconcile_variance_boundary_1026():
    """BR-017：|冲话费 − 平台消费| / 平台消费。1.99% 通过，2.00% 返回 1026 并生成财务核查工单。"""
    from app.core import SessionLocal
    from app.models import AccountRecharge, AccountRechargeVerify, Todo

    auth = headers()
    _reset_pool()
    account_id = account_id_of(E2E_RECON_ACCOUNT_NO)

    missing = _verify(auth, account_id, "2026-09", None)
    assert missing.json()["code"] == 1001
    assert "平台消费数据拉取失败" in missing.json()["msg"]

    invalid = _verify(auth, account_id, "2026-09", 0)
    assert invalid.json()["code"] == 1001
    assert "大于 0" in invalid.json()["msg"]

    empty = _verify(auth, account_id, "2026-07", 100)
    assert empty.json()["code"] == 1001
    assert "无冲话费" in empty.json()["msg"]

    small = _recharge(auth, account_id, 101.99, recharge_date="2026-09-15")
    assert small.json()["code"] == 0, small.json()
    passed = _verify(auth, account_id, "2026-09", 100)
    assert passed.json()["code"] == 0, passed.json()
    passed_data = passed.json()["data"]
    assert passed_data["diffRateText"] == "1.99%"
    assert passed_data["overThreshold"] is False
    assert passed_data["verifyStatus"] == "MATCHED"
    assert passed_data["diffAmount"] == 1.99
    assert passed_data["totalRecharge"] == 101.99
    assert passed_data["platformConsumed"] == 100
    assert passed_data["workOrderId"] is None
    assert passed_data["verifyTaskId"].startswith("VR")

    listed = client.get(
        "/admin-api/ims/account/recharge/list",
        headers=auth,
        params={"accountId": account_id, "month": "2026-09"},
    )
    assert listed.json()["data"]["list"][0]["verifyStatus"] == "MATCHED"
    assert listed.json()["data"]["list"][0]["verifyDiff"] == 1.99

    blocked = _recharge(auth, account_id, 102, recharge_date="2026-08-15")
    assert blocked.json()["code"] == 0, blocked.json()
    over = _verify(auth, account_id, "2026-08", 100)
    assert over.json()["code"] == 1026
    assert "2.00%" in over.json()["msg"]
    over_data = over.json()["data"]
    assert over_data["diffRateText"] == "2.00%"
    assert over_data["overThreshold"] is True
    assert over_data["verifyStatus"] == "DIFF"
    assert over_data["diffAmount"] == 2
    assert over_data["workOrderId"]

    diff_list = client.get(
        "/admin-api/ims/account/recharge/list",
        headers=auth,
        params={"accountId": account_id, "month": "2026-08"},
    )
    assert diff_list.json()["data"]["list"][0]["verifyStatus"] == "DIFF"

    scale_ok = _recharge(auth, account_id, 10199, voucher="RC-SCALE-199", recharge_date="2026-06-01")
    assert scale_ok.json()["code"] == 0, scale_ok.json()
    scale_pass = _verify(auth, account_id, "2026-06", 10000)
    assert scale_pass.json()["code"] == 0, scale_pass.json()
    assert scale_pass.json()["data"]["diffRateText"] == "1.99%"

    scale_bad = _recharge(auth, account_id, 10200, voucher="RC-SCALE-200", recharge_date="2026-05-01")
    assert scale_bad.json()["code"] == 0, scale_bad.json()
    scale_over = _verify(auth, account_id, "2026-05", 10000)
    assert scale_over.json()["code"] == 1026
    assert scale_over.json()["data"]["diffRateText"] == "2.00%"

    db = SessionLocal()
    try:
        tickets = list(db.scalars(select(Todo).where(Todo.task_type == "acct_reconcile")).all())
        texts = [f"{row.title} {row.content}" for row in tickets]
        assert any("2.00%" in text and "1026" in text for text in texts)
        assert all("1.99%" not in text for text in texts)
        assert db.scalar(select(AccountRechargeVerify).where(AccountRechargeVerify.month == "2026-07")) is None
        untouched = db.scalar(
            select(AccountRecharge).where(
                AccountRecharge.account_id == account_id,
                AccountRecharge.recharge_date == "2026-09-15",
            )
        )
        assert untouched is not None
        assert untouched.verify_status == "MATCHED"
    finally:
        db.close()
