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


def test_standard_report_platform_and_date_edges():
    auth = headers()
    douyin = client.get("/admin-api/ims/bi/report/unified-account", headers=auth, params={"platform": "DOUYIN"})
    body = douyin.json()
    assert body["code"] == 0
    assert [row["platform"] for row in body["data"]["rows"]] == ["抖音"]
    assert body["data"]["empty"] is False

    missing = client.get("/admin-api/ims/bi/report/unified-account", headers=auth, params={"platform": "KUAISHOU"})
    empty = missing.json()["data"]
    assert empty["rows"] == []
    assert empty["empty"] is True
    assert empty["emptyReason"] == "当前平台下暂无数据"

    outside = client.get(
        "/admin-api/ims/bi/report/unified-account",
        headers=auth,
        params={"dateFrom": "2026-08-01", "dateTo": "2026-08-02"},
    )
    assert outside.json()["data"]["emptyReason"] == "当前日期下暂无数据"

    flipped = client.get(
        "/admin-api/ims/bi/report/unified-account",
        headers=auth,
        params={"dateFrom": "2026-09-20", "dateTo": "2026-09-01"},
    )
    assert flipped.json()["code"] == 1001

    roi = client.get("/admin-api/ims/bi/report/roi", headers=auth, params={"platform": "DOUYIN"})
    roi_body = roi.json()["data"]
    assert roi_body["empty"] is False
    assert len(roi_body["rows"]) == 2
    assert roi_body["filterNote"] == "本报表不含平台列，筛选未改变结果"

    placeholder = client.get("/admin-api/ims/bi/report/account-status", headers=auth, params={"platform": "DOUYIN"})
    assert placeholder.json()["data"]["emptyReason"] == "当前平台下暂无数据"

    plain = client.get("/admin-api/ims/bi/report/unified-account", headers=auth)
    assert plain.json()["data"]["total"] == 2


def test_drill_filter_empty_reason_and_denied_report():
    auth = headers()
    drill = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={"drillPath": ["PLATFORM"], "direction": "DOWN", "filterContext": {"PLATFORM": "快手"}},
    )
    body = drill.json()
    assert body["code"] == 0
    assert body["data"]["rows"] == []
    assert body["data"]["empty"] is True
    assert body["data"]["emptyReason"] == "当前筛选下该层暂无数据"

    denied = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"reportId": 999999, "dateFrom": "2026-09-01", "dateTo": "2026-10-03"},
    )
    assert denied.json()["code"] == 1008


def test_subscribe_next_push_cancel_and_snapshot_before_push():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "本地尾订阅", "reportType": "REPORT", "category": "内容分析"},
    )
    rid = created.json()["data"]["id"]
    sub = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "本地尾周报", "reportId": rid, "period": "WEEK", "pushTime": "周一 09:00"},
    )
    sid = sub.json()["data"]["id"]
    assert sub.json()["data"]["nextPushAt"] == "周一 09:00"
    before = client.get(f"/admin-api/ims/bi/subscribe/snapshot/{sid}", headers=auth)
    assert before.json()["data"]["empty"] is True
    assert before.json()["data"]["rows"] == []
    assert before.json()["data"]["emptyReason"] == "尚未推送，暂无快照"

    paused = client.put(f"/admin-api/ims/bi/subscribe/{sid}", headers=auth, json={"status": "PAUSED"})
    assert paused.json()["data"]["nextPushAt"] == "—"
    client.put(f"/admin-api/ims/bi/subscribe/{sid}", headers=auth, json={"status": "ACTIVE"})

    daily = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "本地尾可取消", "reportId": rid, "period": "DAY", "pushTime": "09:00"},
    )
    daily_id = daily.json()["data"]["id"]
    assert daily.json()["data"]["nextPushAt"] == "明日 09:00"
    removed = client.delete(f"/admin-api/ims/bi/subscribe/{daily_id}", headers=auth)
    assert removed.json()["code"] == 0
    again = client.get("/admin-api/ims/bi/subscribe/list", headers=auth, params={"pageNo": 1, "pageSize": 200})
    assert all(row["id"] != daily_id for row in again.json()["data"]["list"])

    kept = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "本地尾已推送", "reportId": rid, "period": "MONTH", "pushTime": "09:00"},
    )
    kept_id = kept.json()["data"]["id"]
    assert kept.json()["data"]["nextPushAt"] == "下月1日 09:00"
    push = client.post(f"/admin-api/ims/bi/subscribe/{kept_id}/push-now", headers=auth)
    assert push.json()["code"] == 0
    after = client.get(f"/admin-api/ims/bi/subscribe/snapshot/{kept_id}", headers=auth)
    assert after.json()["data"]["empty"] is False
    assert after.json()["data"]["rows"]
