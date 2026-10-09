"""离职归还单：未闭环关闭权限返回 1024（RET-R3 / BR-015）。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import AccountReturnOrder, AssetLedger, CertArchive, Todo, User
from app.ops_db import ops_session
from app.ops_models import PlatformAccount
from app.security import hash_password

client = TestClient(app)


def headers(username: str = "admin", password: str = "Admin@123") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _user(username: str) -> int:
    db = SessionLocal()
    try:
        row = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        if row is None:
            row = User(
                username=username,
                nickname=username,
                mobile="1390000" + str(abs(hash(username)) % 10000).zfill(4),
                password_hash=hash_password("Admin@123"),
                status="ENABLED",
                tenant_id=0,
                deleted=0,
            )
            db.add(row)
            db.commit()
        return int(row.id)
    finally:
        db.close()


def _account(holder_id: int, account_no: str) -> int:
    ops = ops_session()
    try:
        row = ops.scalar(select(PlatformAccount).where(PlatformAccount.account_no == account_no, PlatformAccount.deleted == 0))
        if row is None:
            row = PlatformAccount(
                account_no=account_no,
                account_name=account_no,
                platform_type="DOUYIN",
                holder_user_id=holder_id,
                status="IN_USE",
                tenant_id=0,
            )
            ops.add(row)
        else:
            row.holder_user_id = holder_id
            row.status = "IN_USE"
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _asset(auth: dict, code: str, owner_id: int) -> int:
    created = client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": code, "assetName": code, "assetType": "OFFICE"},
    ).json()
    assert created["code"] == 0, created
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{created['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": owner_id, "purpose": "离职前在用"},
    ).json()
    assert checked["code"] == 0, checked
    return int(created["data"]["id"])


def _cert(holder_id: int, name: str) -> int:
    db = SessionLocal()
    try:
        row = CertArchive(
            holder_user_id=holder_id,
            holder_name=name,
            cert_type="ID_CARD",
            cert_no_enc="enc",
            cert_no_hash=f"hash-{name}",
            issue_date="2020-01-01",
            expire_date="2030-01-01",
            status="EFFECTIVE",
            tenant_id=0,
        )
        db.add(row)
        db.commit()
        return int(row.id)
    finally:
        db.close()


def _generate(auth: dict, user_id: int, day: str = "2026-10-09") -> dict:
    return client.post(
        "/admin-api/ims/account/return/generate",
        headers=auth,
        json={"userId": user_id, "dingtalkResignDate": day, "manual": True},
    ).json()


def test_close_and_disable_return_1024_until_items_are_returned():
    auth = headers()
    user_id = _user("resign_1024")
    peer_id = _user("resign_peer")
    account_id = _account(user_id, "AC-RT-1024")
    asset_id = _asset(auth, "AS-RT-1024", user_id)
    cert_id = _cert(user_id, "resign_1024")

    missing = _generate(auth, 99999999)
    assert missing["code"] == 1500

    bad_day = client.post(
        "/admin-api/ims/account/return/generate",
        headers=auth,
        json={"userId": user_id, "dingtalkResignDate": "2026/10/09", "manual": True},
    ).json()
    assert bad_day["code"] == 1001

    created = _generate(auth, user_id)
    assert created["code"] == 0, created
    assert created["data"]["returnNo"].startswith("RT20261009")
    kinds = {item["itemType"] for item in created["data"]["items"]}
    assert kinds == {"ACCOUNT", "ASSET", "CERT"}
    order_id = created["data"]["id"]

    again = _generate(auth, user_id)
    assert again["code"] == 1001
    assert created["data"]["returnNo"] in again["msg"]

    blocked = client.put(f"/admin-api/ims/account/return/{order_id}/close", headers=auth, json={}).json()
    assert blocked["code"] == 1024, blocked
    assert "禁止关闭权限" in blocked["msg"]

    disabled = client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=auth,
        json={"status": "DISABLED"},
    ).json()
    assert disabled["code"] == 1024, disabled

    account_item = next(item for item in created["data"]["items"] if item["itemType"] == "ACCOUNT")
    self_transfer = client.put(
        f"/admin-api/ims/account/return/item/{account_item['id']}",
        headers=auth,
        json={"itemStatus": "TRANSFERRED", "transferToUserId": user_id},
    ).json()
    assert self_transfer["code"] == 1001

    dispute = client.put(
        f"/admin-api/ims/account/return/item/{account_item['id']}",
        headers=auth,
        json={"itemStatus": "DISPUTED", "remark": ""},
    ).json()
    assert dispute["code"] == 1001

    transferred = client.put(
        f"/admin-api/ims/account/return/item/{account_item['id']}",
        headers=auth,
        json={"itemStatus": "TRANSFERRED", "transferToUserId": peer_id, "remark": "交给同事"},
    ).json()
    assert transferred["code"] == 0, transferred

    still = client.put(f"/admin-api/ims/account/return/{order_id}/close", headers=auth, json={}).json()
    assert still["code"] == 1024

    detail = client.get(f"/admin-api/ims/account/return/{order_id}", headers=auth).json()
    assert detail["code"] == 0, detail
    for item in detail["data"]["items"]:
        if item["itemStatus"] in {"RETURNED", "TRANSFERRED"}:
            continue
        done = client.put(
            f"/admin-api/ims/account/return/item/{item['id']}",
            headers=auth,
            json={"itemStatus": "RETURNED"},
        ).json()
        assert done["code"] == 0, done

    closed = client.put(f"/admin-api/ims/account/return/{order_id}/close", headers=auth, json={}).json()
    assert closed["code"] == 0, closed
    detail = client.get(f"/admin-api/ims/account/return/{order_id}", headers=auth).json()
    assert detail["data"]["status"] == "CLOSED"

    db = SessionLocal()
    ops = ops_session()
    try:
        user = db.get(User, user_id)
        assert user.status == "DISABLED"
        asset = db.get(AssetLedger, asset_id)
        assert asset.status == "RETURNED"
        assert asset.owner_user_id is None
        cert = db.get(CertArchive, cert_id)
        assert cert.status == "RECYCLED"
        account = ops.get(PlatformAccount, account_id)
        assert account.holder_user_id == peer_id
        assert account.status == "IN_USE"
    finally:
        ops.close()
        db.close()

    allowed = client.put(
        f"/admin-api/ims/system/user/{user_id}",
        headers=auth,
        json={"status": "DISABLED"},
    ).json()
    assert allowed["code"] == 0, allowed


def test_overdue_return_suspends_and_notifies_admin():
    auth = headers()
    user_id = _user("resign_late")
    _account(user_id, "AC-RT-LATE")
    created = _generate(auth, user_id, "2026-10-01")
    assert created["code"] == 0, created
    listed = client.get("/admin-api/ims/account/return/list", headers=auth, params={"userId": user_id}).json()
    assert listed["code"] == 0, listed
    row = listed["data"]["list"][0]
    assert row["status"] == "EXCEPTION_SUSPENDED"
    assert row["overdue"] is True
    db = SessionLocal()
    try:
        order = db.get(AccountReturnOrder, created["data"]["id"])
        assert order.status == "EXCEPTION_SUSPENDED"
        todo = db.scalar(
            select(Todo).where(Todo.ref_type == "acct_return", Todo.ref_id == order.id, Todo.status == "PENDING")
        )
        assert todo is not None
        assert "逾期" in todo.title
    finally:
        db.close()
