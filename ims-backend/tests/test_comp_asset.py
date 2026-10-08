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
