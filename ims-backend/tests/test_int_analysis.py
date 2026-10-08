import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import InternalAccount, InternalContent, IpGroup

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_works() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="内部分析组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add_all(
            [
                InternalContent(
                    title="晚间集锦",
                    account_name="神鱼电竞A",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    play_count=1_284_000,
                    completion_rate=38.0,
                    publish_time="2026-10-01 20:00:00",
                    tenant_id=0,
                ),
                InternalContent(
                    title="训练周记",
                    account_name="体育号B",
                    platform_type="KUAISHOU",
                    ip_group_id=group.id,
                    play_count=62_000,
                    completion_rate=11.0,
                    publish_time="2026-10-02 12:00:00",
                    tenant_id=0,
                ),
                InternalContent(
                    title="日常花絮",
                    account_name="神鱼好物",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    play_count=89_000,
                    completion_rate=26.0,
                    publish_time="2026-10-03 09:00:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_int_work_page_all_and_hit():
    seed_works()
    auth = headers()
    all_resp = client.get(
        "/admin-api/ims/int-analysis/work/page",
        headers=auth,
        params={"segment": "ALL", "pageNo": 1, "pageSize": 20},
    )
    body = all_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 3
    assert any(row["isHit"] for row in body["data"]["list"])

    hit_resp = client.get(
        "/admin-api/ims/int-analysis/work/page",
        headers=auth,
        params={"segment": "HIT", "pageNo": 1, "pageSize": 20},
    )
    hit_body = hit_resp.json()
    assert hit_body["code"] == 0
    assert hit_body["data"]["total"] == 1
    assert hit_body["data"]["list"][0]["title"] == "晚间集锦"


def test_int_work_low_score_requires_threshold():
    seed_works()
    auth = headers()
    missing = client.get(
        "/admin-api/ims/int-analysis/work/page",
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
        "/admin-api/ims/int-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE", "pageNo": 1, "pageSize": 20},
    )
    low_body = low_resp.json()
    assert low_body["code"] == 0
    assert low_body["data"]["total"] == 1
    assert low_body["data"]["list"][0]["title"] == "训练周记"


def seed_internal_accounts() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="内部账号组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add_all(
            [
                InternalAccount(
                    account_identifier="int_high_dy",
                    account_name="神鱼高粉号",
                    platform_type="DOUYIN",
                    ip_group_id=group.id,
                    follower_count=320_000,
                    content_count=86,
                    last_synced_at="2026-10-05 09:00:00",
                    tenant_id=0,
                ),
                InternalAccount(
                    account_identifier="int_low_ks",
                    account_name="体育低粉号",
                    platform_type="KUAISHOU",
                    ip_group_id=group.id,
                    follower_count=620,
                    content_count=9,
                    last_synced_at="2026-10-04 15:30:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_int_account_page_all_and_high_fans():
    seed_internal_accounts()
    auth = headers()
    all_resp = client.get(
        "/admin-api/ims/int-analysis/account/page",
        headers=auth,
        params={"segment": "ALL", "pageNo": 1, "pageSize": 20},
    )
    body = all_resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert any(row["tagHighFans"] for row in body["data"]["list"])
    assert body["data"]["list"][0]["ipGroupName"] == "内部账号组"

    high_resp = client.get(
        "/admin-api/ims/int-analysis/account/page",
        headers=auth,
        params={"segment": "HIGH_FANS", "pageNo": 1, "pageSize": 20},
    )
    high_body = high_resp.json()
    assert high_body["code"] == 0
    assert high_body["data"]["total"] == 1
    assert high_body["data"]["list"][0]["accountName"] == "神鱼高粉号"


def test_int_account_low_fans_requires_threshold():
    seed_internal_accounts()
    auth = headers()
    missing = client.get(
        "/admin-api/ims/int-analysis/account/page",
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
        "/admin-api/ims/int-analysis/account/page",
        headers=auth,
        params={"segment": "LOW_FANS", "pageNo": 1, "pageSize": 20},
    )
    low_body = low_resp.json()
    assert low_body["code"] == 0
    assert low_body["data"]["total"] == 1
    assert low_body["data"]["list"][0]["accountName"] == "体育低粉号"
