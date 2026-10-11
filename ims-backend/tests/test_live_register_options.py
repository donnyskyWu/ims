"""BUG-029 · 开播登记下拉只列使用中账号/手机，证件预检返回明细。"""

import os
import uuid
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.crypto import encrypt_text
from app.main import app
from app.models import AssetLedger, CertArchive
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed() -> dict[str, int]:
    ops = ops_session()
    try:
        company = Company(company_name="登记公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="登记组", status="ENABLED", tenant_id=0)
        active = Realname(
            real_name="在职实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011111"),
            phone_enc=encrypt_text("13800002001"),
            status="ENABLED",
            tenant_id=0,
        )
        stopped = Realname(
            real_name="停用实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011112"),
            phone_enc=encrypt_text("13800002002"),
            status="DISABLED",
            tenant_id=0,
        )
        expiring = Realname(
            real_name="临期实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011113"),
            phone_enc=encrypt_text("13800002003"),
            status="ENABLED",
            tenant_id=0,
        )
        expired = Realname(
            real_name="过期实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011114"),
            phone_enc=encrypt_text("13800002004"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600002001"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-REG-IN",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        idle = Phone(
            phone_enc=encrypt_text("13600002002"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-REG-POOL",
            status="POOL",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, active, stopped, expiring, expired, phone, idle])
        ops.flush()
        accounts = []
        for no, status, person in (
            ("AC-REG-IN", "IN_USE", active),
            ("AC-REG-FROZEN", "FROZEN", active),
            ("AC-REG-POOL", "POOL", active),
            ("AC-REG-BACK", "RETURNED", active),
        ):
            accounts.append(
                PlatformAccount(
                    account_no=no,
                    account_name=no,
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    company_id=company.id,
                    realname_id=person.id,
                    holder_user_id=1,
                    status=status,
                    tenant_id=0,
                )
            )
        ops.add_all(accounts)
        ops.commit()
        ids = {
            "active": active.id,
            "stopped": stopped.id,
            "expiring": expiring.id,
            "expired": expired.id,
            "phone": phone.id,
            "idle": idle.id,
            "in_use": accounts[0].id,
            "frozen": accounts[1].id,
        }
    finally:
        ops.close()
    db = SessionLocal()
    try:
        soon = (date.today() + timedelta(days=21)).isoformat()
        db.add_all(
            [
                AssetLedger(
                    asset_code="AST-LIVE-IN",
                    asset_name="在用直播设备",
                    asset_type="LIVE",
                    status="IN_USE",
                    tenant_id=0,
                ),
                AssetLedger(
                    asset_code="AST-LIVE-BACK",
                    asset_name="已归还直播设备",
                    asset_type="LIVE",
                    status="RETURNED",
                    tenant_id=0,
                ),
                AssetLedger(
                    asset_code="AST-OFFICE",
                    asset_name="办公设备",
                    asset_type="OFFICE",
                    status="IN_USE",
                    tenant_id=0,
                ),
                CertArchive(
                    holder_name="临期实名人",
                    cert_type="IDCARD",
                    expire_date=soon,
                    status="EXPIRING",
                    tenant_id=0,
                ),
                CertArchive(
                    holder_name="过期实名人",
                    cert_type="IDCARD",
                    expire_date="2020-01-01",
                    status="EXPIRED",
                    tenant_id=0,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
    return ids


def test_options_keep_in_use_accounts_phones_and_live_assets():
    auth = headers()
    ids = seed()
    body = client.get("/admin-api/ims/live/register/options", headers=auth).json()
    assert body["code"] == 0
    data = body["data"]
    account_ids = {item["id"] for item in data["accounts"]}
    assert ids["in_use"] in account_ids
    assert ids["frozen"] not in account_ids
    assert all(item["status"] == "IN_USE" for item in data["accounts"])
    phone_ids = {item["id"] for item in data["phones"]}
    assert ids["phone"] in phone_ids
    assert ids["idle"] not in phone_ids
    codes = {item["assetCode"] for item in data["devices"]}
    assert "AST-LIVE-IN" in codes
    assert "AST-LIVE-BACK" not in codes
    assert "AST-OFFICE" not in codes
    names = {item["realName"] for item in data["realnames"]}
    assert "停用实名人" in names
    assert "在职实名人" in names


def test_cert_preview_warns_expiring_and_blocks_expired():
    auth = headers()
    ids = seed()
    warn = client.get(
        "/admin-api/ims/live/register/cert-preview",
        headers=auth,
        params={"realnamePersonId": ids["expiring"]},
    ).json()
    assert warn["code"] == 0
    assert warn["data"]["level"] == "WARN"
    assert warn["data"]["blocked"] is False
    assert "剩余 21 天" in warn["data"]["detail"]

    locked = client.get(
        "/admin-api/ims/live/register/cert-preview",
        headers=auth,
        params={"realnamePersonId": ids["expired"]},
    ).json()
    assert locked["code"] == 0
    assert locked["data"]["level"] == "FAIL"
    assert locked["data"]["blocked"] is True
    assert "2020-01-01" in locked["data"]["detail"]

    stopped = client.get(
        "/admin-api/ims/live/register/cert-preview",
        headers=auth,
        params={"realnamePersonId": ids["stopped"]},
    ).json()
    assert stopped["code"] == 0
    assert stopped["data"]["level"] == "FAIL"
    assert stopped["data"]["blocked"] is False
    assert "未在职" in stopped["data"]["detail"]
