import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import AccountCost, AuthorUser, InternalAccount, InternalContent, IpGroup, PlatformAccount


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


def test_disabled_ip_group_hidden_from_selectors_and_reference_1501():
    auth = headers()
    created = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "停用引用组", "groupType": "SMALL", "parentId": None},
    )
    # 小组必须挂大组；先建大组再停用小组。
    assert created.json()["code"] == 1003
    big = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "停用引用大组", "groupType": "BIG"},
    )
    big_id = big.json()["data"]
    small = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "停用引用组", "groupType": "SMALL", "parentId": big_id},
    )
    gid = small.json()["data"]
    off = client.put("/admin-api/ims/ip-group/update", headers=auth, json={"id": gid, "status": 0})
    assert off.json()["code"] == 0
    hidden = client.get("/admin-api/ims/ip-group/list", headers=auth, params={"keyword": "停用引用组"})
    assert all(row["groupName"] != "停用引用组" for row in hidden.json()["data"]["list"])
    shown = client.get(
        "/admin-api/ims/ip-group/list",
        headers=auth,
        params={"keyword": "停用引用组", "status": 0},
    )
    assert any(row["id"] == gid and row["status"] == 0 for row in shown.json()["data"]["list"])
    tree = client.get("/admin-api/ims/ip-group/tree", headers=auth).json()["data"]
    parent = next(row for row in tree if row["id"] == big_id)
    node = next(child for child in parent["children"] if child["id"] == gid)
    assert node["status"] == 0
    sheet = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": gid, "workDate": "2026-10-11"},
    )
    assert sheet.json()["code"] == 1501
    on = client.put("/admin-api/ims/ip-group/update", headers=auth, json={"id": gid, "status": 1})
    assert on.json()["code"] == 0
    visible = client.get("/admin-api/ims/ip-group/list", headers=auth, params={"keyword": "停用引用组"})
    assert any(row["id"] == gid and row["status"] == 1 for row in visible.json()["data"]["list"])


def test_ip_group_member_user_position_and_count():
    auth = headers()
    big = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "成员大组", "groupType": "BIG"},
    )
    big_id = big.json()["data"]
    small = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "成员小组", "groupType": "SMALL", "parentId": big_id},
    )
    gid = small.json()["data"]
    missing = client.post(
        f"/admin-api/ims/ip-group/{gid}/members",
        headers=auth,
        json={"userId": 99999, "position": "LIVE_OPS", "relationType": "PRIMARY"},
    )
    assert missing.json()["code"] == 1204
    bad_position = client.post(
        f"/admin-api/ims/ip-group/{gid}/members",
        headers=auth,
        json={"userId": 1, "position": "NOT_A_POSITION", "relationType": "PRIMARY"},
    )
    assert bad_position.json()["code"] == 1503
    empty_position = client.post(
        f"/admin-api/ims/ip-group/{gid}/members",
        headers=auth,
        json={"userId": 1, "position": "", "relationType": "PRIMARY"},
    )
    assert empty_position.json()["code"] == 1001
    added = client.post(
        f"/admin-api/ims/ip-group/{gid}/members",
        headers=auth,
        json={"userId": 1, "position": "EDITOR", "relationType": "PRIMARY"},
    )
    assert added.json()["code"] == 0
    members = client.get(f"/admin-api/ims/ip-group/{gid}/members", headers=auth)
    row = members.json()["data"][0]
    assert row["userName"] == "管理员"
    assert row["position"] == "EDITOR"
    assert row["positionName"] == "编辑"
    assert row["relationType"] == "PRIMARY"
    assert row["relationTypeName"] == "主职"
    tree = client.get("/admin-api/ims/ip-group/tree", headers=auth).json()["data"]
    parent = next(item for item in tree if item["id"] == big_id)
    node = next(child for child in parent["children"] if child["id"] == gid)
    assert node["memberCount"] == 1


def test_ip_group_member_edit_and_remove():
    auth = headers()
    big = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "成员编辑大组", "groupType": "BIG"},
    )
    big_id = big.json()["data"]
    small = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "成员编辑小组", "groupType": "SMALL", "parentId": big_id},
    )
    gid = small.json()["data"]
    added = client.post(
        f"/admin-api/ims/ip-group/{gid}/members",
        headers=auth,
        json={"userId": 1, "position": "EDITOR", "relationType": "PRIMARY"},
    )
    assert added.json()["code"] == 0
    member_id = client.get(f"/admin-api/ims/ip-group/{gid}/members", headers=auth).json()["data"][0]["id"]
    saved = client.put(
        f"/admin-api/ims/ip-group/{gid}/members/{member_id}",
        headers=auth,
        json={"position": "LIVE_OPS", "relationType": "PART_TIME"},
    )
    assert saved.json()["code"] == 0
    row = client.get(f"/admin-api/ims/ip-group/{gid}/members", headers=auth).json()["data"][0]
    assert row["position"] == "LIVE_OPS"
    assert row["positionName"] == "直播运营"
    assert row["relationType"] == "PART_TIME"
    assert row["relationTypeName"] == "兼职"
    removed = client.delete(f"/admin-api/ims/ip-group/{gid}/members/{member_id}", headers=auth)
    assert removed.json()["code"] == 0
    assert client.get(f"/admin-api/ims/ip-group/{gid}/members", headers=auth).json()["data"] == []
    tree = client.get("/admin-api/ims/ip-group/tree", headers=auth).json()["data"]
    parent = next(item for item in tree if item["id"] == big_id)
    node = next(child for child in parent["children"] if child["id"] == gid)
    assert node["memberCount"] == 0


def test_ip_group_stats_roll_up_children_and_blank_roi(monkeypatch):
    auth = headers()
    big_id = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "统计大组", "groupType": "BIG"},
    ).json()["data"]
    left_id = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "统计一组", "groupType": "SMALL", "parentId": big_id},
    ).json()["data"]
    right_id = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "统计二组", "groupType": "SMALL", "parentId": big_id},
    ).json()["data"]
    other_id = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "统计旁组", "groupType": "BIG"},
    ).json()["data"]
    empty_id = client.post(
        "/admin-api/ims/ip-group/create",
        headers=auth,
        json={"groupName": "统计空组", "groupType": "BIG"},
    ).json()["data"]

    ops = ops_session()
    try:
        ops.add_all(
            [
                InternalAccount(
                    account_identifier="stat-a",
                    account_name="统计账号A",
                    platform_type="DOUYIN",
                    ip_group_id=left_id,
                    follower_count=10,
                    content_count=2,
                    tenant_id=0,
                ),
                InternalAccount(
                    account_identifier="stat-b",
                    account_name="统计账号B",
                    platform_type="DOUYIN",
                    ip_group_id=right_id,
                    follower_count=7,
                    content_count=4,
                    tenant_id=0,
                ),
                InternalAccount(
                    account_identifier="stat-other",
                    account_name="旁组账号",
                    platform_type="DOUYIN",
                    ip_group_id=other_id,
                    follower_count=100,
                    content_count=50,
                    tenant_id=0,
                ),
                InternalContent(title="内部A1", ip_group_id=left_id, tenant_id=0),
                InternalContent(title="内部A2", ip_group_id=left_id, tenant_id=0),
                InternalContent(title="内部B1", ip_group_id=right_id, tenant_id=0),
                InternalContent(title="旁组内容", ip_group_id=other_id, tenant_id=0),
            ]
        )
        left_account = PlatformAccount(
            account_no="STAT-A",
            account_name="平台A",
            platform_type="DOUYIN",
            ip_group_id=left_id,
            tenant_id=0,
        )
        right_account = PlatformAccount(
            account_no="STAT-B",
            account_name="平台B",
            platform_type="KUAISHOU",
            ip_group_id=right_id,
            tenant_id=0,
        )
        ops.add_all([left_account, right_account])
        ops.flush()
        ops.add(AccountCost(account_id=left_account.id, amount=10, tenant_id=0))
        ops.commit()
    finally:
        ops.close()

    def fake_revenue(**kwargs):
        return 20.0, None

    monkeypatch.setattr("app.ip_group.sum_revenue", fake_revenue)
    big = client.get(f"/admin-api/ims/ip-group/{big_id}/stats", headers=auth).json()["data"]
    assert big["followerCount"] == 17
    assert big["contentCount"] == 6
    assert big["accountCount"] == 2
    assert big["internalContentCount"] == 3
    assert big["costTotal"] == 10
    assert big["revenueTotal"] == 40
    assert big["roiAvg"] == 4
    assert big["revenueDelayed"] is False

    left = client.get(f"/admin-api/ims/ip-group/{left_id}/stats", headers=auth).json()["data"]
    assert left["followerCount"] == 10
    assert left["contentCount"] == 2
    assert left["accountCount"] == 1
    assert left["internalContentCount"] == 2
    assert left["roiAvg"] == 2

    empty = client.get(f"/admin-api/ims/ip-group/{empty_id}/stats", headers=auth).json()["data"]
    assert empty["followerCount"] == 0
    assert empty["contentCount"] == 0
    assert empty["accountCount"] == 0
    assert empty["internalContentCount"] == 0
    assert empty["costTotal"] == 0
    assert empty["revenueTotal"] == 0
    assert empty["roiAvg"] is None
    assert empty["revenueDelayed"] is False

    monkeypatch.setattr("app.ip_group.sum_revenue", lambda **kwargs: (None, "timeout"))
    delayed = client.get(f"/admin-api/ims/ip-group/{left_id}/stats", headers=auth).json()["data"]
    assert delayed["revenueDelayed"] is True
    assert delayed["revenueTotal"] is None
    assert delayed["roiAvg"] is None


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
