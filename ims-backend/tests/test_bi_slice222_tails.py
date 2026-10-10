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


def test_analysis_date_edges_and_outside_window():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": "切片222互动", "metricType": "BASIC", "category": "内容表现"},
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]

    flipped = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2026-09-20", "dateEnd": "2026-09-01", "view": "DETAIL"},
    )
    assert flipped.json()["code"] == 1001
    assert "开始日期不能晚于结束日期" in flipped.json()["msg"]

    one_side = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2026-09-01", "dateEnd": "", "view": "DETAIL"},
    )
    assert one_side.json()["code"] == 1001
    assert "请同时填写开始和结束日期" in one_side.json()["msg"]

    outside = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2020-01-01", "dateEnd": "2020-01-02", "view": "DETAIL"},
    )
    body = outside.json()
    assert body["code"] == 0
    assert body["data"]["rows"] == []
    assert body["data"]["empty"] is True
    assert body["data"]["emptyReason"] == "当前日期下暂无分析数据"

    inside = client.post(
        "/admin-api/ims/bi/metric/analysis/run",
        headers=auth,
        json={"metricIds": [mid], "dateStart": "2026-09-01", "dateEnd": "2026-09-30", "view": "DETAIL"},
    )
    assert inside.json()["code"] == 0
    assert inside.json()["data"]["empty"] is False
    assert inside.json()["data"]["rows"][0]["metricId"] == mid

    miss = client.get(
        "/admin-api/ims/bi/metric/list",
        headers=auth,
        params={"keyword": "no-such-metric-222", "pageNo": 1, "pageSize": 10},
    )
    assert miss.json()["code"] == 0
    assert miss.json()["data"]["total"] == 0


def test_screen_missing_empty_widgets_and_filter_miss():
    auth = headers()
    missing = client.get("/admin-api/ims/bi/screen/999999999/preview", headers=auth)
    assert missing.json()["code"] == 1001
    assert missing.json()["msg"] == "大屏不存在"

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "切片222空大屏", "reportType": "DASHBOARD", "category": "内容分析"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]
    saved = client.put(
        f"/admin-api/ims/bi/report/{rid}",
        headers=auth,
        json={"layoutJson": {"layoutMode": "FREE", "theme": "dark", "comps": []}},
    )
    assert saved.json()["code"] == 0

    preview = client.get(f"/admin-api/ims/bi/screen/{rid}/preview", headers=auth)
    data = preview.json()["data"]
    assert preview.json()["code"] == 0
    assert data["widgets"] == []
    assert data["empty"] is True
    assert data["emptyReason"] == "暂无组件"

    detail = client.get(f"/admin-api/ims/bi/screen/{rid}", headers=auth)
    assert detail.json()["data"]["empty"] is True

    miss = client.get(
        "/admin-api/ims/bi/screen/list",
        headers=auth,
        params={"keyword": "no-such-screen-222", "pageNo": 1, "pageSize": 10},
    )
    assert miss.json()["code"] == 0
    assert miss.json()["data"]["total"] == 0

    reports = client.get(
        "/admin-api/ims/bi/report/list",
        headers=auth,
        params={"keyword": "no-such-report-222", "pageNo": 1, "pageSize": 10},
    )
    assert reports.json()["code"] == 0
    assert reports.json()["data"]["total"] == 0
