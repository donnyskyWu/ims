import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import ExternalAccount, ExternalWork, IpGroup, ThresholdConfig

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_monitor_theme_data() -> None:
    ops = ops_session()
    try:
        group = IpGroup(group_name="监测聚合组", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.flush()
        ops.add(
            ThresholdConfig(
                threshold_category="WORK",
                platform_type="",
                payload_json='{"hotValue":"1000000","lowValue":"20"}',
                status="ENABLED",
                tenant_id=0,
            )
        )
        ops.add_all(
            [
                ExternalAccount(
                    account_identifier="mon_theme_a",
                    account_name="主题A号",
                    platform_type="DOUYIN",
                    ip_theme="跑步健身",
                    industry="体育",
                    ip_group_id=group.id,
                    follower_count=12_000,
                    work_count=2,
                    tenant_id=0,
                ),
                ExternalAccount(
                    account_identifier="mon_theme_b",
                    account_name="主题B号",
                    platform_type="DOUYIN",
                    ip_theme="跑步健身",
                    industry="体育",
                    ip_group_id=group.id,
                    follower_count=8_000,
                    work_count=1,
                    tenant_id=0,
                ),
                ExternalWork(
                    platform_work_id="mon-hit-001",
                    title="主题爆款",
                    account_identifier="mon_theme_a",
                    platform_type="DOUYIN",
                    ip_theme="跑步健身",
                    industry="体育",
                    ip_group_id=group.id,
                    play_count=1_500_000,
                    completion_rate=35.0,
                    publish_time="2026-10-01 12:00:00",
                    tenant_id=0,
                ),
                ExternalWork(
                    platform_work_id="mon-daily-002",
                    title="主题日常",
                    account_identifier="mon_theme_b",
                    platform_type="DOUYIN",
                    ip_theme="跑步健身",
                    industry="体育",
                    ip_group_id=group.id,
                    play_count=50_000,
                    completion_rate=18.0,
                    publish_time="2026-10-02 08:00:00",
                    tenant_id=0,
                ),
                ExternalWork(
                    platform_work_id="mon-esports-003",
                    title="电竞更新",
                    account_identifier="mon_esports",
                    platform_type="KUAISHOU",
                    ip_theme="电竞赛事",
                    industry="电竞",
                    ip_group_id=group.id,
                    play_count=80_000,
                    completion_rate=22.0,
                    publish_time="2026-10-03 20:00:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
    finally:
        ops.close()


def test_monitor_ip_theme_page_aggregates():
    seed_monitor_theme_data()
    auth = headers()
    resp = client.get(
        "/admin-api/ims/monitor/ip-theme/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 2
    fitness = next(row for row in body["data"]["list"] if row["dimensionKey"] == "跑步健身")
    assert fitness["externalAccountCount"] == 2
    assert fitness["workCount"] == 2
    assert fitness["hitCount"] == 1


def test_monitor_industry_page_keyword():
    seed_monitor_theme_data()
    auth = headers()
    resp = client.get(
        "/admin-api/ims/monitor/industry/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "keyword": "电竞"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["list"][0]["dimensionKey"] == "电竞"
    assert body["data"]["list"][0]["workCount"] == 1
