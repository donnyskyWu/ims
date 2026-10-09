"""#170 · 考核结果等级边界、名单筛选，以及空筛选导出。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import PerfRecord

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _scheme(auth: dict, name: str) -> int:
    created = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": name,
            "positionCode": "R5",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [{"metricName": "指标 A", "weight": 100, "calcRule": "AUTO"}],
        },
    )
    assert created.json()["code"] == 0
    return created.json()["data"]["id"]


def _record(auth: dict, scheme_id: int, start: str, score: float | None, status: str = "ISSUED") -> dict:
    created = client.post(
        "/admin-api/ims/perf/execution",
        headers=auth,
        json={
            "schemeId": scheme_id,
            "targetUserId": 1,
            "periodType": "MONTHLY",
            "periodStart": start,
            "periodEnd": start[:8] + "28",
        },
    )
    body = created.json()
    assert body["code"] == 0
    record_id = body["data"]["id"]
    db = SessionLocal()
    try:
        row = db.get(PerfRecord, record_id)
        row.status = status
        row.total_score = score
        db.commit()
    finally:
        db.close()
    return body["data"]


def test_grade_edges_at_90_80_70_60():
    auth = headers()
    scheme_id = _scheme(auth, "等级边界方案")
    samples = [
        (90.0, "S", "S ≥90", "2024-01-01"),
        (89.9, "A", "A 80-89", "2024-02-01"),
        (80.0, "A", "A 80-89", "2024-03-01"),
        (79.9, "B", "B 70-79", "2024-04-01"),
        (70.0, "B", "B 70-79", "2024-05-01"),
        (69.9, "C", "C 60-69", "2024-06-01"),
        (60.0, "C", "C 60-69", "2024-07-01"),
        (59.9, "D", "D <60", "2024-08-01"),
    ]
    for score, letter, edge, start in samples:
        made = _record(auth, scheme_id, start, score)
        detail = client.get(f"/admin-api/ims/perf/result/{made['id']}", headers=auth)
        body = detail.json()
        assert body["code"] == 0
        assert body["data"]["grade"] == letter
        assert body["data"]["gradeEdge"] == edge
        assert body["data"]["totalScore"] == score


def test_result_filters_by_grade_and_unknown_name():
    auth = headers()
    scheme_id = _scheme(auth, "结果筛选方案")
    low = _record(auth, scheme_id, "2023-03-01", 59.9)
    high = _record(auth, scheme_id, "2023-04-01", 90)

    graded = client.get(
        "/admin-api/ims/perf/result/list",
        headers=auth,
        params={"grade": "D", "evaluateeName": low["evaluateeName"], "pageNo": 1, "pageSize": 50},
    )
    assert graded.json()["code"] == 0
    ids = [row["id"] for row in graded.json()["data"]["list"]]
    assert low["id"] in ids
    assert high["id"] not in ids
    counts = graded.json()["data"]["gradeCounts"]
    assert counts["S"] >= 1
    assert counts["D"] >= 1

    by_no = client.get(
        "/admin-api/ims/perf/result/list",
        headers=auth,
        params={"recordNo": low["recordNo"], "pageNo": 1, "pageSize": 10},
    )
    assert by_no.json()["code"] == 0
    assert [row["id"] for row in by_no.json()["data"]["list"]] == [low["id"]]

    empty = client.get(
        "/admin-api/ims/perf/result/list",
        headers=auth,
        params={"evaluateeName": "NO-SUCH-PERF-170", "pageNo": 1, "pageSize": 20},
    )
    assert empty.json()["code"] == 0
    assert empty.json()["data"]["list"] == []
    assert empty.json()["data"]["gradeCounts"] == {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}

    bad = client.get("/admin-api/ims/perf/result/list", headers=auth, params={"grade": "EXCELLENT"})
    assert bad.json()["code"] == 1001


def test_export_empty_filter_is_header_only():
    auth = headers()
    resp = client.get(
        "/admin-api/ims/perf/result/export",
        headers=auth,
        params={"evaluateeName": "NO-SUCH-PERF-170", "status": "ISSUED"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert resp.headers.get("x-export-rows") == "0"
    text = resp.content.decode("utf-8-sig").strip()
    assert text == "recordNo,evaluateeName,position,cycleDisplay,totalScore,grade,status"
