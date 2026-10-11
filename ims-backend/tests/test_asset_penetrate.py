"""#65 · E2E-S5-03/04 实名人→资产 5 层与资产→使用人三态。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.crypto import encrypt_text, sha256_hex
from app.main import app
from app.models import FinProfit, LiveSession
from app.ops_db import ops_session
from app.ops_models import Phone, PlatformAccount, Realname

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _admin_id(auth: dict) -> int:
    return int(client.get("/admin-api/ims/system/user/page", headers=auth).json()["data"]["list"][0]["id"])


def _person() -> int:
    ops = ops_session()
    try:
        row = Realname(
            real_name="穿透实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800001111"),
            phone_sha256=sha256_hex("13800001111"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        return int(row.id)
    finally:
        ops.close()


def _create(auth: dict, code: str, **extra) -> dict:
    body = {"assetCode": code, "assetName": code, "assetType": "OFFICE", **extra}
    res = client.post("/admin-api/ims/asset/ledger", headers=auth, json=body)
    return res.json()


def test_forward_realname_chain_within_five_and_1013_past_five():
    auth = headers()
    person_id = _person()
    root = _create(auth, "AS-PY-L1", realnameId=person_id)
    assert root["code"] == 0, root
    parent = "AS-PY-L1"
    ids = {1: root["data"]["id"]}
    for level in range(2, 6):
        code = f"AS-PY-L{level}"
        created = _create(auth, code, parentAssetCode=parent)
        assert created["code"] == 0, created
        ids[level] = created["data"]["id"]
        parent = code

    within = client.get(
        "/admin-api/ims/asset/forward/trace/0",
        headers=auth,
        params={"realnameId": person_id},
    ).json()
    assert within["code"] == 0, within
    nodes = within["data"]["nodes"]
    assert within["data"]["depth"] == 5
    assert [node["layer"] for node in nodes] == ["PERSON", "ASSET", "ASSET", "ASSET", "ASSET", "ASSET"]
    assert [node["level"] for node in nodes if node["layer"] == "ASSET"] == [1, 2, 3, 4, 5]
    assert [node["assetCode"] for node in nodes if node["layer"] == "ASSET"] == [f"AS-PY-L{n}" for n in range(1, 6)]
    assert nodes[0]["label"] == "穿***人"
    assert len(within["data"]["edges"]) == 5

    over_token = client.get(
        f"/admin-api/ims/asset/forward/trace/{ids[1]}",
        headers=auth,
        params={"layers": "L1,L2,L3,L4,L5,L6"},
    ).json()
    assert over_token["code"] == 1013

    sixth = _create(auth, "AS-PY-L6", parentAssetCode="AS-PY-L5")
    assert sixth["code"] == 0, sixth
    blocked = client.get(
        "/admin-api/ims/asset/forward/trace/0",
        headers=auth,
        params={"realnameId": person_id},
    ).json()
    assert blocked["code"] == 1013
    leaf = client.get(f"/admin-api/ims/asset/forward/trace/{sixth['data']['id']}", headers=auth).json()
    assert leaf["code"] == 1013
    kept = client.get(f"/admin-api/ims/asset/forward/trace/{ids[5]}", headers=auth).json()
    assert kept["code"] == 0
    assert kept["data"]["depth"] == 5

    missing_parent = _create(auth, "AS-PY-ORPHAN", parentAssetCode="AS-NO-SUCH")
    assert missing_parent["code"] == 1011
    listed = client.get("/admin-api/ims/asset/ledger/page", headers=auth, params={"assetCode": "AS-PY-ORPHAN"}).json()
    assert listed["data"]["total"] == 0
    missing_person = client.get(
        "/admin-api/ims/asset/forward/trace/0",
        headers=auth,
        params={"realnameId": 99999},
    ).json()
    assert missing_person["code"] == 1500


def test_reverse_holders_distinguish_three_asset_states():
    auth = headers()
    admin_id = _admin_id(auth)

    def flow(code: str, steps: list[str]) -> int:
        created = _create(auth, code)
        assert created["code"] == 0, created
        asset_id = created["data"]["id"]
        if "checkout" in steps:
            checked = client.post(
                f"/admin-api/ims/asset/ledger/{asset_id}/checkout",
                headers=auth,
                json={"ownerUserId": admin_id, "purpose": "办公领用"},
            ).json()
            assert checked["code"] == 0, checked
        if "use" in steps:
            used = client.post(
                f"/admin-api/ims/asset/ledger/{asset_id}/use",
                headers=auth,
                json={"remark": "现场使用"},
            ).json()
            assert used["code"] == 0, used
        if "return" in steps:
            returned = client.post(
                f"/admin-api/ims/asset/ledger/{asset_id}/return",
                headers=auth,
                json={"remark": "归还入库"},
            ).json()
            assert returned["code"] == 0, returned
        if "scrap" in steps:
            scrapped = client.post(
                f"/admin-api/ims/asset/ledger/{asset_id}/scrap",
                headers=auth,
                json={"remark": "无法修复"},
            ).json()
            assert scrapped["code"] == 0, scrapped
        return asset_id

    in_use = flow("AS-PY-USE", ["checkout"])
    returned = flow("AS-PY-RET", ["checkout", "use", "return"])
    scrapped = flow("AS-PY-SCR", ["checkout", "use", "return", "scrap"])

    detail = client.get(f"/admin-api/ims/asset/ledger/{scrapped}", headers=auth).json()
    assert detail["code"] == 0
    assert [row["status"] for row in detail["data"]["holders"]] == ["IN_USE", "RETURNED", "SCRAPPED"]
    assert {row["statusLabel"] for row in detail["data"]["holders"]} == {"使用中", "已归还", "已报废"}
    assert all(row["userName"] == "管理员" for row in detail["data"]["holders"])

    forward = client.get(f"/admin-api/ims/asset/forward/detail/{scrapped}", headers=auth).json()
    assert forward["code"] == 0, forward
    assert [row["status"] for row in forward["data"]["holders"]] == ["IN_USE", "RETURNED", "SCRAPPED"]
    assert forward["data"]["bindAccounts"] == []
    assert forward["data"]["financeSummary"]["costMasked"] is False

    listed = client.get(
        f"/admin-api/ims/asset/reverse/by-person/{admin_id}",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "includeHistory": True},
    ).json()
    assert listed["code"] == 0, listed
    by_code = {item["assetCode"]: item["status"] for item in listed["data"]["list"]}
    assert by_code["AS-PY-USE"] == "IN_USE"
    assert by_code["AS-PY-RET"] == "RETURNED"
    assert by_code["AS-PY-SCR"] == "SCRAPPED"
    assert listed["data"]["summary"] == {"total": 3, "inUse": 1, "returned": 1, "scrapped": 1}
    assert in_use and returned and scrapped


def test_forward_chain_layers_are_independent_and_cost_is_read_only():
    auth = headers()
    created = _create(auth, "AS-CHAIN-1", assetType="LIVE", assetName="直播灯")
    assert created["code"] == 0, created
    asset_id = created["data"]["id"]
    first = client.get(f"/admin-api/ims/asset/forward/chain/{asset_id}", headers=auth, params={"layer": "L1"}).json()
    assert first["code"] == 0, first
    assert first["data"]["asset"]["assetCode"] == "AS-CHAIN-1"
    assert first["data"]["asset"]["assetType"] == "LIVE"
    assert "accounts" not in first["data"]
    accounts = client.get(f"/admin-api/ims/asset/forward/chain/{asset_id}", headers=auth, params={"layer": "L2"}).json()
    assert accounts["data"]["accounts"] == []
    people = client.get(f"/admin-api/ims/asset/forward/chain/{asset_id}", headers=auth, params={"layer": "L3"}).json()
    assert people["data"]["persons"] == []
    sessions = client.get(f"/admin-api/ims/asset/forward/chain/{asset_id}", headers=auth, params={"layer": "L4"}).json()
    assert sessions["data"]["sessions"] == []
    cost = client.get(f"/admin-api/ims/asset/forward/chain/{asset_id}", headers=auth, params={"layer": "L5"}).json()
    assert cost["data"]["cost"]["totalCost"] == 0
    assert cost["data"]["cost"]["totalRevenue"] == 0
    assert cost["data"]["cost"]["costMasked"] is False
    assert cost["data"]["cost"]["sessionCount"] == 0
    blocked = client.get(f"/admin-api/ims/asset/forward/chain/{asset_id}", headers=auth, params={"layer": "L6"}).json()
    assert blocked["code"] == 1013
    assert blocked["msg"] == "穿透层级超限"
    missing = client.get("/admin-api/ims/asset/forward/chain/99999999", headers=auth, params={"layer": "L1"}).json()
    assert missing["code"] == 1011


def test_phone_forward_chain_follows_bound_accounts_and_session_cost():
    auth = headers()
    stamp = uuid.uuid4().hex[:8]
    ops = ops_session()
    try:
        phone = Phone(
            phone_enc=encrypt_text(f"136{stamp[:8]}"),
            phone_sha256=sha256_hex(f"phone-{stamp}"),
            phone_code=f"PH-{stamp}",
            phone_model="测试机",
            device_number=f"DV-{stamp}",
            status="IN_USE",
            keeper_id=1,
            purchase_date="2026-04-01",
            tenant_id=0,
        )
        ops.add(phone)
        ops.flush()
        account = PlatformAccount(
            account_no=f"AC-PH-{stamp}",
            account_name=f"手机号{stamp}",
            platform_type="DOUYIN",
            phone_id=phone.id,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        phone_id = int(phone.id)
        account_id = int(account.id)
    finally:
        ops.close()
    code = f"IMS20261011DY{stamp[:4].upper()}"
    db = SessionLocal()
    try:
        db.add(
            LiveSession(
                session_code=code,
                account_id=account_id,
                topic="手机场次",
                session_status="ENDED",
                platform="DOUYIN",
                responsible_user_id=1,
                tenant_id=0,
            )
        )
        db.add(FinProfit(session_code=code, revenue=12.5, total_cost=3.25, tenant_id=0))
        db.commit()
    finally:
        db.close()

    first = client.get(
        f"/admin-api/ims/asset/forward/chain/{phone_id}",
        headers=auth,
        params={"layer": "L1", "subject": "phone"},
    ).json()
    assert first["code"] == 0, first
    assert first["data"]["asset"]["assetCode"] == f"PH-{stamp}"
    assert first["data"]["asset"]["assetType"] == "PHONE"
    assert first["data"]["asset"]["bindCount"] == 1
    assert first["data"]["subject"] == "phone"
    accounts = client.get(
        f"/admin-api/ims/asset/forward/chain/{phone_id}",
        headers=auth,
        params={"layer": "L2", "subject": "phone"},
    ).json()
    assert accounts["data"]["accounts"][0]["accountNo"] == f"AC-PH-{stamp}"
    assert accounts["data"]["accounts"][0]["nickname"] == f"手机号{stamp}"
    sessions = client.get(
        f"/admin-api/ims/asset/forward/chain/{phone_id}",
        headers=auth,
        params={"layer": "L4", "subject": "phone"},
    ).json()
    assert sessions["data"]["sessions"][0]["sessionCode"] == code
    cost = client.get(
        f"/admin-api/ims/asset/forward/chain/{phone_id}",
        headers=auth,
        params={"layer": "L5", "subject": "phone"},
    ).json()
    assert cost["data"]["cost"]["totalCost"] == 3.25
    assert cost["data"]["cost"]["totalRevenue"] == 12.5
    assert cost["data"]["cost"]["sessionCount"] == 1
    blocked = client.get(
        f"/admin-api/ims/asset/forward/chain/{phone_id}",
        headers=auth,
        params={"layer": "L6", "subject": "phone"},
    ).json()
    assert blocked["code"] == 1013
    missing = client.get(
        "/admin-api/ims/asset/forward/chain/99999998",
        headers=auth,
        params={"layer": "L1", "subject": "phone"},
    ).json()
    assert missing["code"] == 1011
