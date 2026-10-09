"""PERF-001 覆盖率 / 试取数，PERF-004 预警处置与连续两月辅导名单。"""

import os
from decimal import Decimal

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import app
from app.models import PerfCalcResult, User, WorkMessage
from app.perf_calc import write_ranks

client = TestClient(app)

LINEAR = {
    "ruleType": "LINEAR",
    "linear": {"minMetric": 0, "maxMetric": 100, "minScore": 0, "maxScore": 100},
}


def headers(username: str = "admin") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def create_metric(auth: dict, code: str, name: str, source: str, expression: str | None = None) -> int:
    payload: dict = {
        "metricCode": code,
        "metricName": name,
        "dataSource": source,
        "weight": 10,
        "scoreRule": LINEAR,
        "status": "ENABLED",
    }
    if source == "AUTO":
        payload["sourceConfig"] = {
            "module": "TRAIN",
            "metricExpression": expression or "finish_rate",
            "periodType": "MONTHLY",
        }
    created = client.post("/admin-api/ims/perf/metric", headers=auth, json=payload)
    assert created.json()["code"] == 0, created.json()
    return created.json()["data"]["id"]


def test_auto_coverage_and_local_test_fetch():
    auth = headers()
    staff = headers("e2e_perf_staff")
    denied = client.get("/admin-api/ims/perf/metric/auto-coverage", headers=staff)
    assert denied.status_code == 403
    assert denied.json()["code"] == 403

    before = client.get("/admin-api/ims/perf/metric/auto-coverage", headers=auth).json()["data"]
    manual_id = create_metric(auth, "E2E_COV_MANUAL", "手工覆盖", "MANUAL")
    after_manual = client.get("/admin-api/ims/perf/metric/auto-coverage", headers=auth).json()["data"]
    assert after_manual["enabledMetricCount"] == before["enabledMetricCount"] + 1
    assert after_manual["autoMetricCount"] == before["autoMetricCount"]
    assert any(item["metricCode"] == "E2E_COV_MANUAL" for item in after_manual["manualMetrics"])

    create_metric(auth, "E2E_COV_AUTO", "自动覆盖", "AUTO", "finish_rate")
    create_metric(auth, "E2E_COV_EXAM", "考试覆盖", "EXAM")
    after_auto = client.get("/admin-api/ims/perf/metric/auto-coverage", headers=auth).json()["data"]
    assert after_auto["autoMetricCount"] == before["autoMetricCount"] + 2
    assert after_auto["enabledMetricCount"] == before["enabledMetricCount"] + 3
    assert after_auto["autoCoverageRate"] == round(after_auto["autoMetricCount"] * 100 / after_auto["enabledMetricCount"], 2)

    disabled = client.delete(f"/admin-api/ims/perf/metric/{manual_id}", headers=auth)
    assert disabled.json()["code"] == 0
    after_off = client.get("/admin-api/ims/perf/metric/auto-coverage", headers=auth).json()["data"]
    assert after_off["enabledMetricCount"] == after_auto["enabledMetricCount"] - 1
    assert all(item["metricCode"] != "E2E_COV_MANUAL" for item in after_off["manualMetrics"])

    auto_id = client.get(
        "/admin-api/ims/perf/metric/list",
        headers=auth,
        params={"metricName": "自动覆盖", "pageNo": 1, "pageSize": 10},
    ).json()["data"]["list"][0]["id"]
    fetched = client.post(
        "/admin-api/ims/perf/metric/test-fetch",
        headers=auth,
        json={"metricId": auto_id, "testPeriod": "2026-09"},
    ).json()
    assert fetched["code"] == 0
    assert fetched["data"]["fetchable"] is True
    assert fetched["data"]["elapsedMs"] >= 0
    assert "取数通道可用" in fetched["data"].get("errorReason", "") or "sampleValue" in fetched["data"]

    manual_fetch = client.post(
        "/admin-api/ims/perf/metric/test-fetch",
        headers=auth,
        json={"metricId": manual_id, "testPeriod": "2026-09"},
    ).json()
    assert manual_fetch["data"]["fetchable"] is False
    assert "禁用" in manual_fetch["data"]["errorReason"] or "手工" in manual_fetch["data"]["errorReason"]

    unknown_id = create_metric(auth, "E2E_COV_UNKNOWN", "未知表达式", "AUTO", "not_a_metric")
    unknown = client.post(
        "/admin-api/ims/perf/metric/test-fetch",
        headers=auth,
        json={"metricId": unknown_id, "testPeriod": "2026-09"},
    ).json()
    assert unknown["data"]["fetchable"] is False
    assert "无法取数" in unknown["data"]["errorReason"]

    bad_period = client.post(
        "/admin-api/ims/perf/metric/test-fetch",
        headers=auth,
        json={"metricId": auto_id, "testPeriod": "202609"},
    ).json()
    assert bad_period["code"] == 1001

    missing = client.post(
        "/admin-api/ims/perf/metric/test-fetch",
        headers=auth,
        json={"metricId": 99999999, "testPeriod": "2026-09"},
    ).json()
    assert missing["code"] == 1500

    staff_fetch = client.post(
        "/admin-api/ims/perf/metric/test-fetch",
        headers=staff,
        json={"metricId": auto_id, "testPeriod": "2026-09"},
    )
    assert staff_fetch.status_code == 403
    assert staff_fetch.json()["code"] == 403


def test_rank_alerts_handle_and_two_month_coaching():
    auth = headers()
    staff_auth = headers("e2e_perf_staff")
    denied = client.get("/admin-api/ims/perf/rank/alerts", headers=staff_auth)
    assert denied.status_code == 403
    assert denied.json()["code"] == 403
    denied_coach = client.get("/admin-api/ims/perf/rank/coaching-list", headers=staff_auth)
    assert denied_coach.json()["code"] == 403

    db = SessionLocal()
    user = db.scalar(select(User).where(User.username == "e2e_perf_staff", User.deleted == 0))
    assert user is not None
    tenant_id = user.tenant_id or 0
    for period, score in (("2026-07", "50.00"), ("2026-08", "48.00")):
        db.add(
            PerfCalcResult(
                period_month=period,
                user_id=user.id,
                user_name=user.nickname,
                position_code="R5",
                dept_id=9501,
                dept_name="直播部",
                total_score=Decimal(score),
                rank_in_dept=1,
                result_status="PUBLISHED",
                calc_snapshot={},
                version=1,
                is_current=1,
                tenant_id=tenant_id,
            )
        )
    db.commit()
    write_ranks(db, tenant_id, "2026-07")
    db.commit()
    write_ranks(db, tenant_id, "2026-08")
    db.commit()
    user_id = user.id
    messages = db.scalar(
        select(func.count())
        .select_from(WorkMessage)
        .where(
            WorkMessage.user_id == user_id,
            WorkMessage.title == "绩效预警",
            WorkMessage.content.like("%2026-08%"),
        )
    )
    assert int(messages or 0) == 1
    db.close()

    listed = client.get(
        "/admin-api/ims/perf/rank/alerts",
        headers=auth,
        params={"periodMonth": "2026-08", "pageNo": 1, "pageSize": 20},
    ).json()
    assert listed["code"] == 0
    row = next(item for item in listed["data"]["list"] if item["userName"] == "绩效员工甲")
    assert row["handleStatus"] == "PENDING"
    assert row["pushTargets"] == ["SELF", "SUPERIOR", "HR"]
    assert row["totalScore"] == 48.0
    alert_id = row["id"]

    empty = client.put(
        f"/admin-api/ims/perf/rank/alert/{alert_id}/handle",
        headers=auth,
        json={"handleRemark": "  "},
    ).json()
    assert empty["code"] == 1001

    done = client.put(
        f"/admin-api/ims/perf/rank/alert/{alert_id}/handle",
        headers=auth,
        json={"handleRemark": "安排辅导", "followUpPlan": "每周复盘"},
    ).json()
    assert done["code"] == 0

    again = client.put(
        f"/admin-api/ims/perf/rank/alert/{alert_id}/handle",
        headers=auth,
        json={"handleRemark": "再登记"},
    ).json()
    assert again["code"] == 1001

    done_list = client.get(
        "/admin-api/ims/perf/rank/alerts",
        headers=auth,
        params={"periodMonth": "2026-08", "handleStatus": "DONE", "pageSize": 20},
    ).json()
    assert any(item["id"] == alert_id and item["handleRemark"] == "安排辅导" for item in done_list["data"]["list"])
    pending = client.get(
        "/admin-api/ims/perf/rank/alerts",
        headers=auth,
        params={"periodMonth": "2026-08", "handleStatus": "PENDING", "pageSize": 20},
    ).json()
    assert all(item["id"] != alert_id for item in pending["data"]["list"])

    coach = client.get("/admin-api/ims/perf/rank/coaching-list", headers=auth).json()
    assert coach["code"] == 0
    person = next(item for item in coach["data"] if item["userName"] == "绩效员工甲")
    assert person["consecutiveMonths"] == 2
    assert [item["periodMonth"] for item in person["lastTwoPeriods"]] == ["2026-07", "2026-08"]
    assert person["lastTwoPeriods"][1]["gradeLevel"] == "IMPROVE"

    listed_again = client.get(
        "/admin-api/ims/perf/rank/alerts",
        headers=auth,
        params={"periodMonth": "2026-08", "pageSize": 50},
    ).json()
    assert sum(1 for item in listed_again["data"]["list"] if item["userId"] == user_id) == 1
