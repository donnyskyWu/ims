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


def test_eff_inventory_snapshot():
    auth = headers()
    snap = client.get("/admin-api/ims/eff/inventory/snapshot", headers=auth)
    assert snap.json()["code"] == 0
    data = snap.json()["data"]
    assert "coverageRate" in data
    assert "period" in data
