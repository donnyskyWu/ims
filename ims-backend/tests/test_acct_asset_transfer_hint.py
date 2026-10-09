"""#123 · 账号流转/收回时，绑定资产提示同步转移，并给相关责任人发工作台消息。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.acct_seed import E2E_ACCT_PEER_USER, E2E_SUM_DEPT_USER, refresh_acct_e2e_pool
from app.core import SessionLocal
from app.main import app
from app.models import AssetLedger, Todo, User, WorkMessage
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, PlatformAccount

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def user_id(username: str) -> int:
    db = SessionLocal()
    try:
        row = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        assert row is not None
        return int(row.id)
    finally:
        db.close()


def refresh_pool() -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        refresh_acct_e2e_pool(db, admin)
        db.commit()
    finally:
        db.close()


def make_pool_account(account_no: str, holder_id: int) -> int:
    ops = ops_session()
    try:
        company = ops.scalar(select(Company).where(Company.deleted == 0).limit(1))
        group = ops.scalar(select(IpGroup).where(IpGroup.deleted == 0).limit(1))
        if company is None or group is None:
            company = Company(company_name="E2E领用公司", status="ENABLED", tenant_id=0)
            group = IpGroup(group_name="E2E领用组", status="ENABLED", tenant_id=0)
            ops.add_all([company, group])
            ops.flush()
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            holder_user_id=holder_id,
            status="IN_POOL",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


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


def bind_office(auth: dict, account_no: str, code: str) -> dict:
    created = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={
            "assetCode": code,
            "assetName": f"办公显示器 {code}",
            "assetType": "OFFICE",
            "accountNo": account_no,
        },
    )
    assert created.json()["code"] == 0, created.json()
    return created.json()["data"]


def message_rows(transfer_id: int) -> list[dict]:
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(WorkMessage).where(
                WorkMessage.ref_type == "acct_asset_transfer",
                WorkMessage.ref_id == transfer_id,
            )
        ).all()
        return [
            {
                "user_id": int(row.user_id),
                "content": row.content,
                "source_module": row.source_module,
                "read_flag": int(row.read_flag),
            }
            for row in rows
        ]
    finally:
        db.close()


def test_transfer_hints_bound_assets_and_notifies_without_todo():
    refresh_pool()
    auth = headers()
    peer = headers(E2E_ACCT_PEER_USER)
    admin_id = user_id("admin")
    peer_id = user_id(E2E_ACCT_PEER_USER)
    owner_id = user_id(E2E_SUM_DEPT_USER)
    stamp = uuid.uuid4().hex[:8]
    account_no = f"AC-HINT-{stamp}"
    account_id = make_pool_account(account_no, admin_id)
    checkout_in_use(auth, account_id)
    asset = bind_office(auth, account_no, f"AS-HINT-{stamp}")
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{asset['id']}/checkout",
        headers=auth,
        json={"ownerUserId": owner_id, "purpose": "办公领用"},
    )
    assert checked.json()["code"] == 0, checked.json()

    created = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 资产同步转移",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["status"] == "PENDING_CONFIRM"
    assert body["data"]["assetTransferHint"] == "该账号绑定了 1 项资产，是否同步发起资产转移？"
    assert body["data"]["boundAssets"][0]["assetCode"] == f"AS-HINT-{stamp}"
    assert body["data"]["boundAssets"][0]["ownerUserId"] == owner_id
    transfer_id = body["data"]["id"]

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row is not None
        assert row.holder_user_id == admin_id
        assert row.status == "IN_USE"
    finally:
        ops.close()

    rows = message_rows(transfer_id)
    assert {item["user_id"] for item in rows} == {admin_id, peer_id, owner_id}
    assert all(item["source_module"] == "ACCT" for item in rows)
    assert all("请同步办理资产转移" in item["content"] for item in rows)
    assert all(item["read_flag"] == 0 for item in rows)

    db = SessionLocal()
    try:
        todos = db.scalar(
            select(func.count())
            .select_from(Todo)
            .where(Todo.ref_type == "acct_asset_transfer", Todo.ref_id == transfer_id)
        )
        assert int(todos or 0) == 0
    finally:
        db.close()

    listed = client.get(
        "/admin-api/ims/auth/workbench/messages",
        headers=peer,
        params={"pageNo": 1, "pageSize": 50, "read": False},
    ).json()
    assert listed["code"] == 0
    assert any(item["title"] == f"资产同步转移：{account_no}" for item in listed["data"]["list"])

    confirmed = client.put(
        f"/admin-api/ims/account/transfer/{transfer_id}/confirm",
        headers=peer,
        json={"accept": True},
    )
    confirmed_body = confirmed.json()
    assert confirmed_body["code"] == 0, confirmed_body
    assert confirmed_body["data"]["assetTransferHint"] == "该账号绑定了 1 项资产，是否同步发起资产转移？"
    assert len(message_rows(transfer_id)) == 3

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row is not None
        assert row.holder_user_id == peer_id
    finally:
        ops.close()


def test_transfer_without_assets_has_no_hint():
    refresh_pool()
    auth = headers()
    admin_id = user_id("admin")
    peer_id = user_id(E2E_ACCT_PEER_USER)
    stamp = uuid.uuid4().hex[:8]
    account_id = make_pool_account(f"AC-PLAIN-{stamp}", admin_id)
    checkout_in_use(auth, account_id)
    created = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 无资产流转",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["boundAssets"] == []
    assert body["data"]["assetTransferHint"] is None
    assert message_rows(body["data"]["id"]) == []


def test_scrapped_asset_does_not_hint():
    refresh_pool()
    auth = headers()
    admin_id = user_id("admin")
    peer_id = user_id(E2E_ACCT_PEER_USER)
    stamp = uuid.uuid4().hex[:8]
    account_no = f"AC-SCRAP-{stamp}"
    account_id = make_pool_account(account_no, admin_id)
    checkout_in_use(auth, account_id)
    asset = bind_office(auth, account_no, f"AS-SCRAP-{stamp}")
    db = SessionLocal()
    try:
        row = db.get(AssetLedger, asset["id"])
        assert row is not None
        row.status = "SCRAPPED"
        db.commit()
    finally:
        db.close()
    created = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "TRANSFER",
            "toUserId": peer_id,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 报废资产不提示",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["boundAssets"] == []
    assert body["data"]["assetTransferHint"] is None
    assert message_rows(body["data"]["id"]) == []


def test_recall_notifies_holder_when_assets_bound():
    refresh_pool()
    auth = headers()
    admin_id = user_id("admin")
    stamp = uuid.uuid4().hex[:8]
    account_no = f"AC-RECALL-HINT-{stamp}"
    account_id = make_pool_account(account_no, admin_id)
    checkout_in_use(auth, account_id)
    bind_office(auth, account_no, f"AS-RECALL-{stamp}")
    created = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": account_id,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "pytest 收回并提示资产",
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    assert body["data"]["status"] == "EFFECTIVE"
    assert body["data"]["assetTransferHint"] == "该账号绑定了 1 项资产，是否同步发起资产转移？"
    rows = message_rows(body["data"]["id"])
    assert [item["user_id"] for item in rows] == [admin_id]
    assert "AS-RECALL-" in rows[0]["content"]
