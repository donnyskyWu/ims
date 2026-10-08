"""#65 · E2E-S5-03/04 实名人→资产 5 层与资产→使用人三态。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text, sha256_hex
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Realname

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
    assert {row["statusLabel"] for row in detail["data"]["holders"]} == {"在用", "已归还", "已报废"}
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
