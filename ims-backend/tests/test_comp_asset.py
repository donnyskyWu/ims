import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import ExternalAccount, IpGroup

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_linked_account() -> str:
    ops = ops_session()
    try:
        group = IpGroup(group_name="竞品库组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ident = "comp_lib_linked"
        ops.add(
            ExternalAccount(
                account_identifier=ident,
                account_name="库联动账号",
                platform_type="DOUYIN",
                ip_group_id=group.id,
                follower_count=320_000,
                work_count=12,
                tenant_id=0,
            )
        )
        ops.commit()
        return ident
    finally:
        ops.close()


def test_comp_asset_list_seeds():
    auth = headers()
    resp = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 4
    assert any(row["compName"] == "Keep 官方" for row in body["data"]["list"])
    numbers = [row["assetNo"] for row in body["data"]["list"]]
    assert len(numbers) == len(set(numbers))
    assert all(no.startswith("CP") and len(no) >= 11 for no in numbers)


def test_duplicate_asset_nos_repaired_once():
    from app.core import SessionLocal
    from app.models import CompAsset

    db = SessionLocal()
    try:
        for name in ("重复甲", "重复乙", "重复丙"):
            db.add(
                CompAsset(
                    asset_no="CP20261011001",
                    comp_name_std=name,
                    platform="DOUYIN",
                    status="APPROVED",
                    tenant_id=0,
                    created_by=1,
                )
            )
        db.commit()
    finally:
        db.close()

    auth = headers()
    first = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    assert first["code"] == 0
    rows = [row for row in first["data"]["list"] if row["compName"] in {"重复甲", "重复乙", "重复丙"}]
    numbers = [row["assetNo"] for row in rows]
    assert len(numbers) == 3
    assert len(set(numbers)) == 3
    assert "CP20261011001" in numbers

    again = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    ).json()
    again_numbers = [
        row["assetNo"] for row in again["data"]["list"] if row["compName"] in {"重复甲", "重复乙", "重复丙"}
    ]
    assert sorted(again_numbers) == sorted(numbers)


def test_comp_asset_create_enriched_from_ops():
    ident = seed_linked_account()
    auth = headers()
    created = client.post(
        "/admin-api/ims/comp/asset",
        headers=auth,
        json={
            "compName": "健身教练艾伦",
            "platform": "DOUYIN",
            "compAccountId": ident,
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["assetNo"].startswith("CP")
    assert body["data"]["followerCount"] == 320_000

    listed = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"compName": "健身教练", "pageNo": 1, "pageSize": 5},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1


def test_comp_asset_detail_and_compare():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/comp/asset/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    ).json()
    numbers = [row["assetNo"] for row in listed["data"]["list"][:2]]
    detail = client.get(f"/admin-api/ims/comp/asset/{numbers[0]}", headers=auth).json()
    assert detail["code"] == 0, detail
    assert detail["data"]["auditStatusLabel"] == "已入库"
    assert detail["data"]["monitorSubscribed"] is True
    assert isinstance(detail["data"]["interactionTrend"], list)
    assert "topWorks" in detail["data"]

    compared = client.get(
        "/admin-api/ims/comp/asset/compare",
        headers=auth,
        params={"assetNos": ",".join(numbers)},
    ).json()
    assert compared["code"] == 0, compared
    assert compared["data"]["assetNos"] == numbers
    assert any(item["dimensionKey"] == "followerCount" for item in compared["data"]["dimensionMatrix"])
