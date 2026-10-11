import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
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


def test_eff_inventory_snapshot():
    auth = headers()
    snap = client.get("/admin-api/ims/eff/inventory/snapshot", headers=auth)
    assert snap.json()["code"] == 0
    data = snap.json()["data"]
    assert "coverageRate" in data
    assert "period" in data
