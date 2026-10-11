"""TC-15：指标口径版本（C001）、方案指标权重 1154（C002）、方案停用（C003）、三档分档（C011）。"""

import os
from datetime import datetime

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import PerfMetric, PerfMetricRevision
from app.perf import adjustment_limit_message
from app.perf_calc import metric_rule_for_period, score_of
from app.settings_runtime import invalidate_param_cache

client = TestClient(app)

LINEAR = {
    "ruleType": "LINEAR",
    "linear": {"minMetric": 0, "maxMetric": 100, "minScore": 0, "maxScore": 100},
}


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_metric_edit_keeps_historical_rule():
    auth = headers()
    created = client.post(
        "/admin-api/ims/perf/metric",
        headers=auth,
        json={
            "metricCode": "TC15_RULE",
            "metricName": "口径指标",
            "dataSource": "MANUAL",
            "weight": 10,
            "scoreRule": LINEAR,
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    metric_id = created.json()["data"]["id"]
    assert created.json()["data"]["version"] == 1

    edited = client.put(
        f"/admin-api/ims/perf/metric/{metric_id}",
        headers=auth,
        json={
            "metricCode": "TC15_RULE",
            "metricName": "口径指标",
            "dataSource": "MANUAL",
            "weight": 10,
            "scoreRule": {
                "ruleType": "LINEAR",
                "linear": {"minMetric": 0, "maxMetric": 100, "minScore": 0, "maxScore": 40},
            },
            "status": "ENABLED",
        },
    )
    body = edited.json()
    assert body["code"] == 0
    assert body["data"]["version"] == 2
    assert body["data"]["scoreRule"]["linear"]["maxScore"] == 40

    db = SessionLocal()
    try:
        metric = db.get(PerfMetric, metric_id)
        revisions = db.query(PerfMetricRevision).filter(PerfMetricRevision.metric_id == metric_id).all()
        by_version = {row.version: row for row in revisions}
        by_version[1].effective_at = datetime(2026, 1, 1)
        by_version[2].effective_at = datetime(2026, 8, 1)
        db.commit()
        db.refresh(metric)
        old_rule, old_version = metric_rule_for_period(db, metric, "2026-06")
        new_rule, new_version = metric_rule_for_period(db, metric, "2026-08")
    finally:
        db.close()
    assert old_version == 1
    assert new_version == 2
    assert float(score_of(old_rule, 100)) == 100
    assert float(score_of(new_rule, 100)) == 40


def _metric(auth: dict, code: str) -> int:
    created = client.post(
        "/admin-api/ims/perf/metric",
        headers=auth,
        json={
            "metricCode": code,
            "metricName": code,
            "dataSource": "MANUAL",
            "weight": 10,
            "scoreRule": LINEAR,
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    return created.json()["data"]["id"]


def _scheme(auth: dict) -> int:
    created = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "TC15方案",
            "positionCode": "R6",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [
                {"metricName": "占位A", "weight": 50, "calcRule": "AUTO"},
                {"metricName": "占位B", "weight": 50, "calcRule": "AUTO"},
            ],
        },
    )
    assert created.json()["code"] == 0
    return created.json()["data"]["id"]


def test_scheme_items_require_100_and_toggle():
    auth = headers()
    left = _metric(auth, "TC15_LEFT")
    right = _metric(auth, "TC15_RIGHT")
    scheme_id = _scheme(auth)

    low = client.put(
        f"/admin-api/ims/perf/scheme/{scheme_id}",
        headers=auth,
        json={
            "items": [
                {"metricId": left, "metricName": "TC15_LEFT", "weight": 40, "calcRule": "AUTO"},
                {"metricId": right, "metricName": "TC15_RIGHT", "weight": 40, "calcRule": "AUTO"},
            ]
        },
    )
    assert low.json()["code"] == 1154
    assert low.json()["data"]["totalWeight"] == 80

    saved = client.put(
        f"/admin-api/ims/perf/scheme/{scheme_id}",
        headers=auth,
        json={
            "items": [
                {"metricId": left, "metricName": "TC15_LEFT", "weight": 40, "calcRule": "AUTO"},
                {"metricId": right, "metricName": "TC15_RIGHT", "weight": 60, "calcRule": "AUTO"},
            ]
        },
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["weightTotal"] == 100
    assert "TC15_LEFT 40%" in saved.json()["data"]["metricSummary"]

    stopped = client.post(f"/admin-api/ims/perf/scheme/{scheme_id}/deactivate", headers=auth)
    assert stopped.json()["code"] == 0
    assert stopped.json()["data"]["status"] == "INACTIVE"
    blocked = client.post(
        "/admin-api/ims/perf/execution",
        headers=auth,
        json={
            "schemeId": scheme_id,
            "targetUserId": 1,
            "periodType": "MONTHLY",
            "periodStart": "2026-09-01",
            "periodEnd": "2026-09-30",
        },
    )
    assert blocked.json()["code"] == 1001

    started = client.post(f"/admin-api/ims/perf/scheme/{scheme_id}/activate", headers=auth)
    assert started.json()["code"] == 0
    assert started.json()["data"]["status"] == "ACTIVE"


def test_grade_line_is_configurable_three_bands():
    auth = headers()
    invalidate_param_cache()
    try:
        updated = client.put(
            "/admin-api/ims/system/param",
            headers=auth,
            json={"paramKey": "perf.grade.qualified", "paramValue": "70"},
        )
        assert updated.json()["code"] == 0
        scheme = client.post(
            "/admin-api/ims/perf/scheme",
            headers=auth,
            json={
                "templateName": "分档方案",
                "positionCode": "R5",
                "periodType": "MONTHLY",
                "activate": True,
                "items": [{"metricName": "A", "weight": 100, "calcRule": "AUTO"}],
            },
        )
        scheme_id = scheme.json()["data"]["id"]
        created = client.post(
            "/admin-api/ims/perf/execution",
            headers=auth,
            json={
                "schemeId": scheme_id,
                "targetUserId": 1,
                "periodType": "MONTHLY",
                "periodStart": "2026-05-01",
                "periodEnd": "2026-05-31",
            },
        )
        record_id = created.json()["data"]["id"]
        from app.models import PerfRecord

        db = SessionLocal()
        try:
            row = db.get(PerfRecord, record_id)
            row.status = "ISSUED"
            row.total_score = 65
            db.commit()
        finally:
            db.close()
        detail = client.get(f"/admin-api/ims/perf/result/{record_id}", headers=auth)
        body = detail.json()
        assert body["code"] == 0
        assert body["data"]["grade"] == "IMPROVE"
        assert body["data"]["gradeEdge"] == "待改进 <70"
        assert body["data"]["alerted"] is True
        assert body["data"]["grade"] not in {"S", "A", "B", "C", "D"}
    finally:
        invalidate_param_cache()


def test_same_user_same_period_is_blocked():
    auth = headers()
    scheme = _scheme(auth)
    payload = {
        "schemeId": scheme,
        "targetUserId": 1,
        "periodType": "MONTHLY",
        "periodStart": "2026-10-01",
        "periodEnd": "2026-10-31",
    }
    first = client.post("/admin-api/ims/perf/execution", headers=auth, json=payload)
    assert first.json()["code"] == 0
    again = client.post("/admin-api/ims/perf/execution", headers=auth, json=payload)
    assert again.json()["code"] == 1001
    assert again.json()["msg"] == "该周期已有进行中的考核记录（BR-031）"
    other = client.post(
        "/admin-api/ims/perf/execution",
        headers=auth,
        json={**payload, "periodStart": "2026-11-01", "periodEnd": "2026-11-30"},
    )
    assert other.json()["code"] == 0


def test_adjust_by_metric_rejects_over_20_percent():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "逐项调整",
            "positionCode": "R5",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [
                {"metricName": "开播", "weight": 40, "calcRule": "AUTO"},
                {"metricName": "GMV", "weight": 60, "calcRule": "AUTO"},
            ],
        },
    )
    scheme_id = scheme.json()["data"]["id"]
    created = client.post(
        "/admin-api/ims/perf/execution",
        headers=auth,
        json={
            "schemeId": scheme_id,
            "targetUserId": 1,
            "periodType": "MONTHLY",
            "periodStart": "2026-04-01",
            "periodEnd": "2026-04-30",
        },
    )
    record_id = created.json()["data"]["id"]
    calc = client.post(f"/admin-api/ims/perf/execution/{record_id}/calculate", headers=auth)
    body = calc.json()["data"]
    assert len(body["lines"]) == 2
    base = body["calcBaseScore"]
    names = [line["metricName"] for line in body["lines"]]
    assert names == ["开播", "GMV"]
    blocked = client.put(
        f"/admin-api/ims/perf/execution/{record_id}/adjust",
        headers=auth,
        json={
            "lines": [
                {"metricName": "开播", "manualAdjustment": 50},
                {"metricName": "GMV", "manualAdjustment": 50},
            ]
        },
    )
    assert blocked.json()["code"] == 1001
    assert blocked.json()["msg"] == adjustment_limit_message(base)
    saved = client.put(
        f"/admin-api/ims/perf/execution/{record_id}/adjust",
        headers=auth,
        json={
            "lines": [
                {"metricName": "开播", "manualAdjustment": 2},
                {"metricName": "GMV", "manualAdjustment": 0},
            ],
            "remark": "补一场",
        },
    )
    saved_body = saved.json()
    assert saved_body["code"] == 0
    lines = {line["metricName"]: line for line in saved_body["data"]["lines"]}
    assert lines["开播"]["finalScore"] == lines["开播"]["autoScore"] + 2
    assert saved_body["data"]["totalScore"] == round(base + 2 * 0.4, 1)
