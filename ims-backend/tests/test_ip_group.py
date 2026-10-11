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
    big_node = next(row for row in tree.json()["data"] if row["groupName"] == "神鱼体育")
    assert big_node["children"][0]["groupName"] == "电竞一组"

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


def test_ip_group_create_field_rules():
    auth = headers()
    empty = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "  ", "groupType": "BIG"},
    )
    assert empty.json()["code"] == 1001
    assert "必填" in empty.json()["msg"]
    too_long = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "名" * 51, "groupType": "BIG"},
    )
    assert too_long.json()["code"] == 1001
    assert too_long.json()["msg"] == "名称长度 1-50 字符"
    bad_level = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "等级非法组", "groupType": "BIG", "level": "Z"},
    )
    assert bad_level.json()["code"] == 1503
    long_desc = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "描述超长组", "groupType": "BIG", "description": "描" * 201},
    )
    assert long_desc.json()["code"] == 1001
    assert "0-200" in long_desc.json()["msg"]
    created = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={
            "groupName": "字段组",
            "groupType": "BIG",
            "leaderUserId": 1,
            "level": "A",
            "description": "一组说明",
        },
    )
    assert created.json()["code"] == 0
    listed = client.get("/admin-api/ims/ip-group/list", headers=auth, params={"keyword": "字段组"})
    row = next(item for item in listed.json()["data"]["list"] if item["groupName"] == "字段组")
    assert row["level"] == "A"
    assert row["remark"] == "一组说明"
    assert row["leaderUserId"] == 1
    assert row["leaderUserName"] == "管理员"
    plain = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "无组长大组", "groupType": "BIG"},
    )
    assert plain.json()["code"] == 0
    listed_plain = client.get("/admin-api/ims/ip-group/list", headers=auth, params={"keyword": "无组长大组"})
    plain_row = next(item for item in listed_plain.json()["data"]["list"] if item["groupName"] == "无组长大组")
    assert plain_row["leaderUserId"] in (None, 0)


def test_ip_group_update_fields_without_changing_type():
    auth = headers()
    created = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "待编辑大组", "groupType": "BIG", "level": "A"},
    )
    gid = created.json()["data"]
    before = client.get("/admin-api/ims/ip-group/tree", headers=auth).json()["data"]
    node = next(row for row in before if row["id"] == gid)
    assert node["groupType"] == "BIG"
    updated = client.put(
        "/admin-api/ims/ip-group/update",
        headers=auth,
        json={
            "id": gid,
            "groupName": "已编辑大组",
            "leaderUserId": 1,
            "level": "B",
            "remark": "改后备注",
            "sortOrder": 8,
        },
    )
    assert updated.json()["code"] == 0
    after = client.get("/admin-api/ims/ip-group/tree", headers=auth).json()["data"]
    node = next(row for row in after if row["id"] == gid)
    assert node["groupName"] == "已编辑大组"
    assert node["groupType"] == "BIG"
    assert node["level"] == "B"
    assert node["remark"] == "改后备注"
    assert node["sortOrder"] == 8
    assert node["leaderUserName"] == "管理员"
    assert node["updatedAt"]
    assert node["createdAt"]
    blocked = client.put(
        "/admin-api/ims/ip-group/update",
        headers=auth,
        json={"id": gid, "level": "Z"},
    )
    assert blocked.json()["code"] == 1503


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
