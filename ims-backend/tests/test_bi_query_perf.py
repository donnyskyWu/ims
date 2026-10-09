"""BI-002 筛选下钻、导出与查询性能监控（BR-204 / V3-B6）。"""

import os
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.acct_seed import _ensure_cloned_user
from app.core import SessionLocal
from app.main import app

client = TestClient(app)
BJ = timezone(timedelta(hours=8))


def headers(username: str = "admin", password: str = "Admin@123") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": password},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def perf(auth: dict) -> dict:
    today = datetime.now(BJ).date()
    start = today - timedelta(days=6)
    res = client.get(
        "/admin-api/ims/bi/query/perf-stats",
        headers=auth,
        params={"dateRange": f"{start.isoformat()},{today.isoformat()}"},
    )
    body = res.json()
    assert body["code"] == 0, body
    return body["data"]


def test_platform_filter_narrows_drill_and_export():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "平台筛选", "reportType": "REPORT", "category": "内容分析"},
    )
    report_id = created.json()["data"]["id"]
    drilled = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={
            "reportId": report_id,
            "drillPath": ["PLATFORM"],
            "direction": "DOWN",
            "filterContext": {"PLATFORM": "视频号", "dateFrom": "2026-09-01", "dateTo": "2026-10-03"},
        },
    )
    body = drilled.json()
    assert body["code"] == 0, body
    assert body["data"]["queryMode"] == "SYNC"
    assert [row["dimensionValue"] for row in body["data"]["rows"]] == ["视频号"]

    dated = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={
            "reportId": report_id,
            "drillPath": ["PLATFORM", "ACCOUNT", "SESSION", "PERSON", "DATE"],
            "direction": "DOWN",
            "filterContext": {"PLATFORM": "抖音", "dateFrom": "2026-09-29", "dateTo": "2026-09-29"},
        },
    )
    dated_body = dated.json()
    assert dated_body["code"] == 0, dated_body
    assert [row["dimensionValue"] for row in dated_body["data"]["rows"]] == ["2026-09-29"]

    exported = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={
            "reportId": report_id,
            "drillPath": "PLATFORM",
            "filterContext": '{"PLATFORM":"视频号"}',
            "format": "CSV",
        },
    )
    csv_body = exported.json()
    assert csv_body["code"] == 0, csv_body
    text = client.get(csv_body["data"]["downloadUrl"], headers=auth).content.decode("utf-8-sig")
    assert "视频号" in text
    assert "抖音" not in text


def test_wide_span_async_then_terminate_shows_on_perf_stats():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "跨度监控", "reportType": "REPORT", "category": "内容分析"},
    )
    report_id = created.json()["data"]["id"]
    before = perf(auth)

    async_res = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={
            "reportId": report_id,
            "drillPath": ["PLATFORM"],
            "direction": "DOWN",
            "filterContext": {"dateFrom": "2026-01-01", "dateTo": "2026-10-03"},
        },
    )
    async_body = async_res.json()
    assert async_body["code"] == 0, async_body
    assert async_body["data"]["queryMode"] == "ASYNC"
    assert async_body["data"]["taskId"].startswith("BQ")
    assert "V3-B6" in async_body["data"]["message"]

    stopped = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={
            "reportId": report_id,
            "dateFrom": "2020-01-01",
            "dateTo": "2026-10-03",
            "platform": "抖音",
        },
    )
    stopped_body = stopped.json()
    assert stopped.status_code == 200
    assert stopped_body["code"] == 1194
    assert "BR-204" in stopped_body["msg"]

    after = perf(auth)
    assert after["asyncConvertedCount"] == before["asyncConvertedCount"] + 1
    assert after["over30sCount"] == before["over30sCount"] + 1
    assert after["totalQueries"] >= before["totalQueries"] + 2
    slow = next(item for item in after["topSlowReports"] if item["reportId"] == report_id)
    assert slow["reportName"] == "跨度监控"
    assert slow["avgCostMs"] > 30000
    assert slow["queryCount"] >= 1

    bad = client.get(
        "/admin-api/ims/bi/query/perf-stats",
        headers=auth,
        params={"dateRange": "2026-10-03,2026-01-01"},
    )
    assert bad.json()["code"] == 1001


def test_perf_stats_r9_allowed_peer_denied():
    db = SessionLocal()
    try:
        _ensure_cloned_user(
            db,
            username="bi_perf_r9",
            nickname="报表数据分析师",
            mobile="13900000139",
            role_key="bi:r9",
            role_name="数据分析师",
        )
        _ensure_cloned_user(
            db,
            username="bi_perf_peer",
            nickname="报表同事",
            mobile="13900000140",
            role_key="bi:peer",
            role_name="报表同事",
        )
        db.commit()
    finally:
        db.close()

    analyst = client.get("/admin-api/ims/bi/query/perf-stats", headers=headers("bi_perf_r9"))
    assert analyst.json()["code"] == 0

    denied = client.get("/admin-api/ims/bi/query/perf-stats", headers=headers("bi_perf_peer"))
    assert denied.status_code == 403
    assert denied.json()["code"] == 1008
