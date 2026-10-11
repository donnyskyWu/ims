"""BUG-033 · 登记直播设备后，资产时间线记下绑定场次。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.crypto import encrypt_text
from app.main import app
from app.models import AssetLedger
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed() -> tuple[int, int, int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="绑定公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="绑定组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="绑定实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001013301"),
            phone_enc=encrypt_text("13800003301"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600003301"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-BIND",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-BIND",
            account_name="绑定场次号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        ids = (account.id, person.id, phone.id)
    finally:
        ops.close()
    db = SessionLocal()
    try:
        asset = AssetLedger(
            id=900_000_033,
            asset_code="AST-BIND-LIVE",
            asset_name="绑定直播灯",
            asset_type="LIVE",
            status="IN_USE",
            tenant_id=0,
        )
        db.add(asset)
        db.commit()
        return (*ids, asset.id)
    finally:
        db.close()


def test_register_writes_bind_session_on_the_asset_timeline():
    auth = headers()
    account_id, person_id, phone_id, asset_id = seed()
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "realnamePersonId": person_id,
            "responsibleUserId": 1,
            "deviceAssetIds": [phone_id, asset_id],
            "platform": "DOUYIN",
            "topic": "设备绑定专场",
            "planStartTime": "2026-10-20T20:00:00+08:00",
        },
    )
    assert created.json()["code"] == 0, created.json()
    code = created.json()["data"]["sessionCode"]
    detail = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    kinds = {(item["kind"], item["assetName"]) for item in detail["boundDevices"]}
    assert ("ASSET", "绑定直播灯") in kinds
    assert any(item["kind"] == "PHONE" for item in detail["boundDevices"])

    asset = client.get(f"/admin-api/ims/asset/ledger/{asset_id}", headers=auth)
    assert asset.json()["code"] == 0, asset.json()
    timeline = asset.json()["data"]["timeline"]
    hit = next(item for item in timeline if item["eventType"] == "BIND_SESSION")
    assert hit["remark"] == f"绑定场次 {code}"
    assert hit["toStatus"] == "IN_USE"
