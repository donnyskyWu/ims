import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import AuthorUser, IpGroup, PlatformAccount


client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_ip_group_tree_members_and_accounts_cascade():
    auth = headers()
    big = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "神鱼体育", "groupType": "BIG", "leaderUserId": 1, "level": "S"},
    )
    assert big.json()["code"] == 0
    big_id = big.json()["data"]
    small = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "电竞一组", "groupType": "SMALL", "parentId": big_id, "leaderUserId": 1, "level": "A"},
    )
    assert small.json()["code"] == 0
    small_id = small.json()["data"]

    tree = client.get("/admin-api/ims/ip-group/tree", headers=auth)
    assert tree.json()["code"] == 0
    mine = next(row for row in tree.json()["data"] if row["groupName"] == "神鱼体育")
    assert mine["children"][0]["groupName"] == "电竞一组"

    member = client.post(
        f"/admin-api/ims/ip-group/{small_id}/members",
        headers=auth,
        json={"userId": 1, "position": "OPERATOR", "relationType": "PRIMARY"},
    )
    assert member.json()["code"] == 0
    members = client.get(f"/admin-api/ims/ip-group/{small_id}/members", headers=auth)
    assert members.json()["data"][0]["userName"] == "管理员"

    ops = ops_session()
    try:
        account = PlatformAccount(
            account_no="DY-001",
            account_name="测试抖音号",
            platform_type="DOUYIN",
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.flush()
        account_id = account.id
        author = AuthorUser(author_name="测试作者", ip_group_id=small_id, user_id=1, status="ENABLED", tenant_id=0)
        ops.add(author)
        ops.commit()
        author_id = author.id
    finally:
        ops.close()

    blocked = client.post(
        f"/admin-api/ims/ip-group/{big_id}/accounts",
        headers=auth,
        json={"accountIds": [account_id]},
    )
    assert blocked.json()["code"] == 1203

    bind = client.post(
        f"/admin-api/ims/ip-group/{small_id}/accounts",
        headers=auth,
        json={"accountIds": [account_id]},
    )
    assert bind.json()["code"] == 0
    accounts = client.get(f"/admin-api/ims/ip-group/{small_id}/accounts", headers=auth)
    assert accounts.json()["code"] == 0
    assert len(accounts.json()["data"]) == 1
    assert accounts.json()["data"][0]["platformType"] == "DOUYIN"

    anchor = client.post(
        f"/admin-api/ims/ip-group/{small_id}/anchors",
        headers=auth,
        json={"anchorUserIds": [author_id], "isPrimary": True},
    )
    assert anchor.json()["code"] == 0
    anchors = client.get(f"/admin-api/ims/ip-group/{small_id}/anchors", headers=auth)
    assert anchors.json()["data"][0]["isPrimary"] is True


def test_ip_group_delete_guard_and_duplicate_name():
    auth = headers()
    created = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "唯一大组", "groupType": "BIG"},
    )
    gid = created.json()["data"]
    dup = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "唯一大组", "groupType": "BIG"},
    )
    assert dup.json()["code"] == 1002
    client.post(
        f"/admin-api/ims/ip-group/{gid}/members",
        headers=auth,
        json={"userId": 1, "position": "OPS_LEADER"},
    )
    deleted = client.delete(f"/admin-api/ims/ip-group/delete?id={gid}", headers=auth)
    assert deleted.json()["code"] == 1005
