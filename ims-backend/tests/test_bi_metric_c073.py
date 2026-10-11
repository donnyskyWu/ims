"""BUG-C073：趋势序列与明细同一份数据，不再另造 09-24~09-29。"""

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


def test_analysis_trend_dates_match_detail_rows():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": "C073播放量", "metricCode": "M00001", "metricType": "BASIC", "unit": "次"},
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]

    ran = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={
            "metricIds": [mid],
            "ipGroupName": "全部",
            "dateStart": "2026-09-01",
            "dateEnd": "2026-09-30",
            "view": "TREND",
        },
    )
    data = ran.json()["data"]
    assert ran.json()["code"] == 0
    assert len(data["rows"]) == 2
    assert {row["statDate"] for row in data["rows"]} == {"2026-09-30"}
    detail = {(row["statDate"], row["ipGroupName"], row["value"]) for row in data["rows"]}
    points = {
        (point["date"], point["ipGroupName"], point["value"])
        for item in data["series"]
        for point in item["points"]
    }
    assert points == detail
    assert {point["date"] for item in data["series"] for point in item["points"]} == {"2026-09-30"}
