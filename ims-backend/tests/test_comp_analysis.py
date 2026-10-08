import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import ExternalAccount, ExternalWork, IpGroup

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_external_works() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="竞品监测组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add_all(
            [
                ExternalWork(
                    platform_work_id="dy-hit-001",
                    title="对手爆款复盘",
                    account_name="竞品号A",
                    account_identifier="comp_a_ks",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    play_count=2_100_000,
                    like_count=88_000,
                    completion_rate=42.0,
                    publish_time="2026-10-01 18:00:00",
                    tenant_id=0,
                ),
                ExternalWork(
                    platform_work_id="ks-low-002",
                    title="对手日常更新",
                    account_name="竞品号B",
                    account_identifier="comp_b_ks",
                    platform_type="KUAISHOU",
                    ip_group_id=group.id,
                    play_count=45_000,
                    like_count=320,
                    completion_rate=9.5,
                    publish_time="2026-10-02 11:00:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_comp_work_page_all_and_hit():
    seed_external_works()
    auth = headers()
    all_resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "ALL", "pageNo": 1, "pageSize": 20},
    )
    body = all_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert any(row["isHit"] for row in body["data"]["list"])
    assert any(row["likeCount"] == 88_000 for row in body["data"]["list"])

    hit_resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "HIT", "pageNo": 1, "pageSize": 20},
    )
    hit_body = hit_resp.json()
    assert hit_body["code"] == 0
    assert hit_body["data"]["total"] == 1
    assert hit_body["data"]["list"][0]["title"] == "对手爆款复盘"


def seed_external_accounts() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="竞品账号组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add_all(
            [
                ExternalAccount(
                    account_identifier="comp_high_dy",
                    account_name="竞品高粉号",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    follower_count=520_000,
                    work_count=128,
                    last_synced_at="2026-10-05 09:00:00",
                    tenant_id=0,
                ),
                ExternalAccount(
                    account_identifier="comp_low_ks",
                    account_name="竞品低粉号",
                    platform_type="KUAISHOU",
                    ip_group_id=group.id,
                    follower_count=800,
                    work_count=12,
                    last_synced_at="2026-10-04 15:30:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_comp_account_page_all_and_high_fans():
    seed_external_accounts()
    auth = headers()
    all_resp = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "ALL", "pageNo": 1, "pageSize": 20},
    )
    body = all_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert any(row["isHighFans"] for row in body["data"]["list"])
    assert body["data"]["list"][0]["followerCount"] == 520_000

    high_resp = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "HIGH_FANS", "pageNo": 1, "pageSize": 20},
    )
    high_body = high_resp.json()
    assert high_body["code"] == 0
    assert high_body["data"]["total"] == 1
    assert high_body["data"]["list"][0]["accountName"] == "竞品高粉号"


def test_comp_account_low_fans_requires_threshold():
    seed_external_accounts()
    auth = headers()
    missing = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "LOW_FANS", "pageNo": 1, "pageSize": 20},
    )
    assert missing.json()["code"] == 1251

    created = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "FANS",
            "platformType": "",
            "lowFans": 1000,
            "highFans": 100000,
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0

    low_resp = client.get(
        "/admin-api/ims/comp-analysis/account/page",
        headers=auth,
        params={"segment": "LOW_FANS", "pageNo": 1, "pageSize": 20},
    )
    low_body = low_resp.json()
    assert low_body["code"] == 0
    assert low_body["data"]["total"] == 1
    assert low_body["data"]["list"][0]["accountName"] == "竞品低粉号"


def test_comp_work_low_score_requires_threshold():
    seed_external_works()
    auth = headers()
    missing = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE", "pageNo": 1, "pageSize": 20},
    )
    assert missing.json()["code"] == 1251

    created = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "WORK",
            "platformType": "",
            "hotValue": "1000000",
            "lowValue": "20",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0

    low_resp = client.get(
        "/admin-api/ims/comp-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE", "pageNo": 1, "pageSize": 20},
    )
    low_body = low_resp.json()
    assert low_body["code"] == 0
    assert low_body["data"]["total"] == 1
    assert low_body["data"]["list"][0]["title"] == "对手日常更新"
