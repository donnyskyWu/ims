"""BUG-C042：分析窗口内返回 IP 组种子明细和趋势，窗外为空，不展示未接 DW。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_tc_r9_analysis_seed_rows_trend_and_ip_filter():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": "C042播放量", "metricCode": "C042_PLAY", "metricType": "BASIC", "unit": "次"},
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]

    ran = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2026-09-01", "dateEnd": "2026-09-30", "view": "DETAIL"},
    )
    body = ran.json()
    assert body["code"] == 0
    assert "未接 DW" not in str(body["data"])
    assert body["data"]["empty"] is False
    assert body["data"]["rows"][0]["metricId"] == mid
    names = {row["ipGroupName"] for row in body["data"]["rows"]}
    assert names == {"电竞一组", "体育二组"}
    assert body["data"]["rows"][0]["statDate"] == "2026-09-30"
    assert body["data"]["total"] == 2
    assert body["data"]["series"]
    assert len(body["data"]["series"][0]["points"]) >= 2

    one = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={
            "metricIds": [mid],
            "ipGroupName": "电竞一组",
            "dateStart": "2026-09-01",
            "dateEnd": "2026-09-30",
        },
    )
    only = one.json()["data"]["rows"]
    assert len(only) == 1
    assert only[0]["ipGroupName"] == "电竞一组"
    assert only[0]["value"] == 1284600

    outside = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2020-01-01", "dateEnd": "2020-01-02"},
    )
    assert outside.json()["data"]["rows"] == []
    assert outside.json()["data"]["emptyReason"] == "当前日期下暂无分析数据"
    assert outside.json()["data"]["series"] == []
