import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    return headers_for("admin")


def headers_for(username: str) -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_eff_relation_create_list_coverage():
    auth = headers()
    uid = 1
    created = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={
            "userId": uid,
            "relationType": "PRIMARY",
            "targetType": "IP_GROUP",
            "targetId": 1,
            "targetName": "测试 IP 组",
            "shareRatio": 100,
        },
    )
    assert created.json()["code"] == 0

    listed = client.get("/admin-api/ims/eff/relation/list", headers=auth, params={"userId": uid, "pageNo": 1, "pageSize": 5})
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1

    cov = client.get("/admin-api/ims/eff/relation/coverage", headers=auth)
    assert cov.json()["code"] == 0
    assert "coverageRate" in cov.json()["data"]


def test_eff_primary_conflict_1198():
    import random

    auth = headers()
    uid = random.randint(900_000, 999_989)
    first = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetName": "A", "shareRatio": 100},
    )
    assert first.json()["code"] == 0
    second = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetName": "B", "shareRatio": 100},
    )
    assert second.json()["code"] == 1198


def test_eff_board_primary_100_plus_part_time_60_is_not_over():
    import random

    from app.core import SessionLocal
    from app.models import EffRelation, User

    auth = headers()
    uid = random.randint(900_000, 999_989)
    before = client.get("/admin-api/ims/eff/metrics/board", headers=auth).json()["data"]["overShareUserCount"]
    primary = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetName": "主归属", "shareRatio": 100},
    )
    assert primary.json()["code"] == 0, primary.json()
    part = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PART_TIME", "targetName": "兼职", "shareRatio": 60},
    )
    assert part.json()["code"] == 0, part.json()
    after = client.get("/admin-api/ims/eff/metrics/board", headers=auth).json()["data"]["overShareUserCount"]
    assert after == before

    db = SessionLocal()
    try:
        tenant_id = db.query(User).filter(User.username == "admin").one().tenant_id
        now_rows = [
            EffRelation(
                user_id=uid,
                relation_type="PART_TIME",
                target_type="IP_GROUP",
                target_id=2,
                target_name="绕过校验",
                share_ratio=50,
                effective_from="2026-01-01",
                status="ACTIVE",
                tenant_id=tenant_id,
            )
        ]
        db.add_all(now_rows)
        db.commit()
    finally:
        db.close()
    bumped = client.get("/admin-api/ims/eff/metrics/board", headers=auth).json()["data"]["overShareUserCount"]
    assert bumped == before + 1


def test_bug_c053_board_uses_live_ledger_not_placeholder():
    import random
    from datetime import datetime, timedelta, timezone

    from app.core import SessionLocal
    from app.models import LiveReport, LiveSession, User

    auth = headers()
    board = client.get("/admin-api/ims/eff/metrics/board", headers=auth).json()["data"]
    assert board["avgGmvPerCap"] != 286000
    assert board["avgSessionsPerMonth"] != 4.8
    assert board["avgWorksPerMonth"] != 9.6
    assert board["capacityUtilization"] is None
    assert "people" in board
    assert "chart" in board

    uid = random.randint(900_000, 999_989)
    created = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetName": "看板IP组", "shareRatio": 100},
    )
    assert created.json()["code"] == 0, created.json()
    period = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m")
    code = f"IMS-EFF-{uid}"
    db = SessionLocal()
    try:
        tenant_id = db.query(User).filter(User.username == "admin").one().tenant_id
        db.add(
            LiveSession(
                session_code=code,
                account_id=1,
                responsible_user_id=uid,
                plan_start_time=f"{period}-15T20:00:00+08:00",
                session_status="DONE",
                tenant_id=tenant_id,
            )
        )
        db.add(LiveReport(session_code=code, gmv=20000, tenant_id=tenant_id))
        db.commit()
    finally:
        db.close()

    again = client.get(
        "/admin-api/ims/eff/metrics/board",
        headers=auth,
        params={"keyword": "看板IP组"},
    ).json()["data"]
    # 姓名筛选匹配的是用户姓名，目标名不会命中；用无筛选结果里的该用户行核对 GMV。
    full = client.get("/admin-api/ims/eff/metrics/board", headers=auth).json()["data"]
    row = next(item for item in full["people"] if item["userId"] == uid)
    assert row["primaryName"] == "看板IP组"
    assert row["attributedGmv"] == 20000
    assert row["primaryShare"] == 100
    assert row["shareTotal"] == 0
    assert row["score"] is None
    assert full["avgGmvPerCap"] not in (None, 286000)
    assert any(item["gmv"] >= 20000 for item in full["chart"])
    assert again["avgGmvPerCap"] == full["avgGmvPerCap"]


def test_bug_c054_change_delete_and_permission_message():
    import random

    from app.core import SessionLocal
    from app.models import Role, RolePerm, User, UserRole
    from app.security import hash_password

    auth = headers()
    uid = random.randint(900_000, 999_989)
    created = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetType": "IP_GROUP", "targetName": "原IP组", "shareRatio": 100},
    )
    assert created.json()["code"] == 0, created.json()
    relation_id = created.json()["data"]["id"]
    changed = client.put(
        f"/admin-api/ims/eff/relation/{relation_id}",
        headers=auth,
        json={
            "action": "TRANSFER",
            "newTargetType": "IP_GROUP",
            "newTargetId": 9,
            "newTargetName": "新IP组",
            "effectiveDate": "2026-10-12",
        },
    )
    assert changed.json()["code"] == 0, changed.json()
    new_id = changed.json()["data"]["newRelationId"]
    assert changed.json()["data"]["oldEffectiveTo"] == "2026-10-12"
    listed = client.get("/admin-api/ims/eff/relation/list", headers=auth, params={"userId": uid, "pageSize": 20}).json()["data"]["list"]
    by_id = {row["id"]: row for row in listed}
    assert by_id[relation_id]["status"] == "HISTORICAL"
    assert by_id[new_id]["status"] == "ACTIVE"
    assert by_id[new_id]["targetName"] == "新IP组"
    removed = client.delete(f"/admin-api/ims/eff/relation/{new_id}", headers=auth)
    assert removed.json()["code"] == 0, removed.json()
    caps = client.get("/admin-api/ims/eff/relation/coverage", headers=auth).json()["data"]
    assert caps["canCreate"] is True
    assert caps["canDelete"] is True

    username = f"tc_r2_{uid}"
    db = SessionLocal()
    try:
        user = User(
            username=username,
            nickname="无权限同事",
            mobile=f"139{uid % 100000000:08d}"[:11],
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        role = Role(
            role_name="只读同事",
            role_key=f"eff:reader:{uid}",
            data_scope="SELF",
            status="ENABLED",
            source="MANUAL",
            tenant_id=0,
        )
        naked = User(
            username=f"tc_naked_{uid}",
            nickname="无角色",
            mobile=f"138{uid % 100000000:08d}"[:11],
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add_all([user, role, naked])
        db.flush()
        db.add(RolePerm(role_id=role.id, module_code="eff", perm_code="ims:eff:none", perm_level="R", tenant_id=0))
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.commit()
    finally:
        db.close()

    reader = headers_for(username)
    denied = client.post(
        "/admin-api/ims/eff/relation",
        headers=reader,
        json={"userId": uid, "relationType": "PART_TIME", "targetName": "越权", "shareRatio": 10},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == 1008
    assert denied.json()["msg"] == "无权限建立归属"
    reader_caps = client.get("/admin-api/ims/eff/relation/coverage", headers=reader).json()["data"]
    assert reader_caps["canCreate"] is False
    assert reader_caps["canDelete"] is False
    naked_token = headers_for(f"tc_naked_{uid}")
    blocked = client.get("/admin-api/ims/eff/relation/list", headers=naked_token)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == 1008
    assert blocked.json()["msg"]


def test_bug_c055_primary_and_part_time_messages():
    import random

    auth = headers()
    uid = random.randint(900_000, 999_989)
    first = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetName": "主", "shareRatio": 100},
    )
    assert first.json()["code"] == 0, first.json()
    second = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PRIMARY", "targetName": "又一个主", "shareRatio": 100},
    )
    assert second.json()["code"] == 1198
    assert second.json()["msg"] == "该人员已有生效主归属（BR-213 在职唯一主归属）"
    part = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PART_TIME", "targetName": "兼职甲", "shareRatio": 60},
    )
    assert part.json()["code"] == 0, part.json()
    over = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": uid, "relationType": "PART_TIME", "targetName": "兼职乙", "shareRatio": 50},
    )
    assert over.json()["code"] == 1199
    assert over.json()["msg"] == "该人员兼职分摊合计 110% 超 100%"


def test_eff_inventory_snapshot():
    auth = headers()
    snap = client.get("/admin-api/ims/eff/inventory/snapshot", headers=auth)
    assert snap.json()["code"] == 0
    data = snap.json()["data"]
    assert "coverageRate" in data
    assert "period" in data


def _role_user(db, username: str, role_key: str, data_scope: str, mobile: str):
    from app.models import Role, RolePerm, User, UserRole
    from app.security import hash_password

    user = User(
        username=username,
        nickname=username,
        mobile=mobile,
        password_hash=hash_password("Admin@123"),
        status="ENABLED",
        tenant_id=0,
    )
    role = Role(
        role_name=username,
        role_key=role_key,
        data_scope=data_scope,
        status="ENABLED",
        source="MANUAL",
        tenant_id=0,
    )
    db.add_all([user, role])
    db.flush()
    db.add(RolePerm(role_id=role.id, module_code="eff", perm_code="ims:eff:relation:query", perm_level="R", tenant_id=0))
    db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
    return user, role


def test_bug_c054_relation_list_scope_r7_self_r4_all():
    """R7 只看本人归属；R4 看全部。同时持有两角色时取最宽。"""
    from app.core import SessionLocal
    from app.models import User, UserRole

    auth = headers()
    db = SessionLocal()
    try:
        r7, role_r7 = _role_user(db, "tc_r7", "r7", "ALL", "13900000071")
        r4, role_r4 = _role_user(db, "tc_r4", "r4", "SELF", "13900000041")
        mix = User(
            username="tc_r7_r4",
            nickname="tc_r7_r4",
            mobile="13900000074",
            password_hash=r7.password_hash,
            status="ENABLED",
            tenant_id=0,
        )
        db.add(mix)
        db.flush()
        db.add(UserRole(user_id=mix.id, role_id=role_r7.id, tenant_id=0))
        db.add(UserRole(user_id=mix.id, role_id=role_r4.id, tenant_id=0))
        db.commit()
        r7_id = r7.id
        r4_id = r4.id
    finally:
        db.close()

    own = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": r7_id, "relationType": "PRIMARY", "targetName": "本人主归属", "shareRatio": 100},
    )
    assert own.json()["code"] == 0, own.json()
    other = client.post(
        "/admin-api/ims/eff/relation",
        headers=auth,
        json={"userId": r4_id, "relationType": "PRIMARY", "targetName": "他人主归属", "shareRatio": 100},
    )
    assert other.json()["code"] == 0, other.json()

    r7_headers = headers_for("tc_r7")
    own_list = client.get("/admin-api/ims/eff/relation/list", headers=r7_headers, params={"pageSize": 50}).json()
    assert own_list["code"] == 0
    assert own_list["data"]["total"] >= 1
    assert {row["userId"] for row in own_list["data"]["list"]} == {r7_id}
    hidden = client.get(
        "/admin-api/ims/eff/relation/list",
        headers=r7_headers,
        params={"userId": r4_id, "pageSize": 50},
    ).json()
    assert hidden["data"]["total"] == 0
    assert hidden["data"]["list"] == []

    r4_headers = headers_for("tc_r4")
    seen_own = client.get(
        "/admin-api/ims/eff/relation/list",
        headers=r4_headers,
        params={"userId": r7_id, "pageSize": 50},
    ).json()["data"]
    seen_other = client.get(
        "/admin-api/ims/eff/relation/list",
        headers=r4_headers,
        params={"userId": r4_id, "pageSize": 50},
    ).json()["data"]
    assert seen_own["total"] >= 1
    assert {row["userId"] for row in seen_own["list"]} == {r7_id}
    assert seen_other["total"] >= 1
    assert {row["userId"] for row in seen_other["list"]} == {r4_id}

    mix_headers = headers_for("tc_r7_r4")
    widest = client.get(
        "/admin-api/ims/eff/relation/list",
        headers=mix_headers,
        params={"userId": r4_id, "pageSize": 50},
    ).json()["data"]
    assert widest["total"] >= 1
    assert {row["userId"] for row in widest["list"]} == {r4_id}
