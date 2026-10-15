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
            phone_model="绑定手机",
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


def test_profit_trace_shows_bound_device_name_and_code():
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
    detail = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    if detail.get("sessionStatus") == "PENDING_RISK_CHECK":
        approved = client.put(
            f"/admin-api/ims/live/register/{code}/approve",
            headers=auth,
            json={"approve": True},
        )
        assert approved.json()["code"] == 0, approved.json()
    assert client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth).json()["code"] == 0
    assert client.put(f"/admin-api/ims/live/register/{code}/end", headers=auth).json()["code"] == 0
    report = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json={
            "actualStart": "2026-10-20T20:00:00+08:00",
            "actualEnd": "2026-10-20T22:00:00+08:00",
            "gmv": 100000.0,
            "refundAmount": 2000.0,
            "orderCount": 120,
            "viewerCount": 5000,
            "peakOnline": 800,
            "newFans": 200,
            "adCost": 5000.0,
        },
    )
    assert report.json()["code"] == 0, report.json()
    confirmed = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0, confirmed.json()
    cost = client.post(
        f"/admin-api/ims/fin/cost/{code}",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "commissionRate": 0.05,
            "adCost": 5000,
            "rechargeCost": 100,
            "fixedCost": 2000,
            "sampleCost": 500,
            "shareCostType": "MANUAL",
            "shareDaren": 3000,
            "shareRealname": 1000,
        },
    )
    assert cost.json()["code"] == 0, cost.json()
    assert client.put(f"/admin-api/ims/fin/cost/{code}/confirm", headers=auth).json()["code"] == 0

    chain = client.get(f"/admin-api/ims/dc/profit-trace/{code}", headers=auth)
    body = chain.json()
    assert body["code"] == 0, body
    assets = {item["assetId"]: item for item in body["data"]["chain"]["assets"]}
    assert assets[phone_id]["assetName"] == "绑定手机"
    assert assets[phone_id]["assetCode"] == "PY-BIND"
    assert assets[asset_id]["assetName"] == "绑定直播灯"
    assert assets[asset_id]["assetCode"] == "AST-BIND-LIVE"
    assert f"AST-{phone_id}" not in {item["assetCode"] for item in assets.values()}
    assert f"AST-{asset_id}" not in {item["assetCode"] for item in assets.values()}
    assert body["data"]["chain"]["profit"]["netProfit"] == 81400.0


def test_tagged_asset_is_not_replaced_by_a_phone_with_the_same_id():
    auth = headers()
    account_id, person_id, phone_id, _asset_id = seed()
    ops = ops_session()
    try:
        decoy = Phone(
            phone_enc=encrypt_text("13600003399"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="E2E-FIN-PHONE",
            phone_model="iPhone 15",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add(decoy)
        ops.commit()
        decoy_id = decoy.id
    finally:
        ops.close()
    db = SessionLocal()
    try:
        db.add(
            AssetLedger(
                id=decoy_id,
                asset_code="TC-LIVE-A",
                asset_name="TC-直播设备A",
                asset_type="LIVE",
                status="IN_USE",
                tenant_id=0,
            )
        )
        db.commit()
    finally:
        db.close()
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "realnamePersonId": person_id,
            "responsibleUserId": 1,
            "deviceAssetIds": [
                {"kind": "PHONE", "id": phone_id},
                {"kind": "ASSET", "id": decoy_id},
            ],
            "platform": "DOUYIN",
            "topic": "设备绑定专场",
            "planStartTime": "2026-10-20T20:00:00+08:00",
        },
    )
    assert created.json()["code"] == 0, created.json()
    code = created.json()["data"]["sessionCode"]
    detail = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    by_kind = {item["kind"]: item for item in detail["boundDevices"]}
    assert by_kind["ASSET"]["assetName"] == "TC-直播设备A"
    assert by_kind["ASSET"]["assetCode"] == "TC-LIVE-A"
    assert by_kind["PHONE"]["assetName"] == "绑定手机"
    assert "iPhone 15" not in {item["assetName"] for item in detail["boundDevices"]}
    timeline = client.get(f"/admin-api/ims/asset/ledger/{decoy_id}", headers=auth).json()["data"]["timeline"]
    assert any(item["eventType"] == "BIND_SESSION" and code in item["remark"] for item in timeline)


def test_supplement_plan_on_another_date_does_not_fail():
    auth = headers()
    account_id, person_id, phone_id, _asset_id = seed()
    created = client.post(
        "/admin-api/ims/live/ledger/supplement",
        headers=auth,
        json={
            "sessionCreate": {
                "accountId": account_id,
                "realnamePersonId": person_id,
                "responsibleUserId": 1,
                "deviceAssetIds": [phone_id],
                "platform": "DOUYIN",
                "topic": "改期补录",
                "planStartTime": "2020-02-02T20:00",
            },
            "sessionReport": {
                "actualStart": "2020-02-02T20:00",
                "actualEnd": "2020-01-15T22:00:00+08:00",
                "gmv": 10,
                "refundAmount": 0,
                "orderCount": 1,
                "viewerCount": 10,
                "peakOnline": 5,
                "newFans": 1,
                "adCost": 0,
            },
            "supplementReason": "改到二月",
        },
    )
    assert created.json()["code"] == 0, created.json()
