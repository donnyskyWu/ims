import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import PerfRecord

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_perf_scheme_create_list_and_activate():
    auth = headers()
    created = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "直播运营考核-2026Q1",
            "positionCode": "R5",
            "periodType": "QUARTERLY",
            "metricSummary": "场次 · GMV · 风控",
            "evaluateeCount": 18,
            "activate": True,
            "items": [
                {"metricName": "开播场次", "weight": 40, "calcRule": "AUTO"},
                {"metricName": "直播 GMV", "weight": 60, "calcRule": "AUTO"},
            ],
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["schemeNo"].startswith("PS")
    assert body["data"]["status"] == "ACTIVE"
    assert body["data"]["weightTotal"] == 100
    scheme_id = body["data"]["id"]

    listed = client.get(
        "/admin-api/ims/perf/scheme/list",
        headers=auth,
        params={"templateName": "直播运营", "positionCode": "R5", "status": "ACTIVE", "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1
    assert any(row["id"] == scheme_id for row in listed.json()["data"]["list"])

    second = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "直播运营考核-B",
            "positionCode": "R5",
            "periodType": "QUARTERLY",
            "activate": False,
            "items": [
                {"metricName": "指标 A", "weight": 50, "calcRule": "AUTO"},
                {"metricName": "指标 B", "weight": 50, "calcRule": "AUTO"},
            ],
        },
    )
    second_id = second.json()["data"]["id"]
    activated = client.post(f"/admin-api/ims/perf/scheme/{second_id}/activate", headers=auth)
    assert activated.json()["code"] == 0
    assert activated.json()["data"]["status"] == "ACTIVE"

    first = client.get(
        "/admin-api/ims/perf/scheme/list",
        headers=auth,
        params={"positionCode": "R5", "status": "INACTIVE", "pageNo": 1, "pageSize": 20},
    )
    assert any(row["id"] == scheme_id for row in first.json()["data"]["list"])


def test_perf_scheme_rejects_invalid_weight():
    auth = headers()
    bad = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "权重错误方案",
            "positionCode": "R6",
            "periodType": "MONTHLY",
            "items": [
                {"metricName": "作品数", "weight": 30, "calcRule": "AUTO"},
                {"metricName": "互动率", "weight": 30, "calcRule": "AUTO"},
            ],
        },
    )
    assert bad.json()["code"] == 1001


def test_perf_execution_create_and_list():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "执行考核用方案",
            "positionCode": "R5",
            "periodType": "QUARTERLY",
            "activate": True,
            "items": [
                {"metricName": "A", "weight": 50, "calcRule": "AUTO"},
                {"metricName": "B", "weight": 50, "calcRule": "AUTO"},
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
            "periodType": "QUARTERLY",
            "periodStart": "2026-07-01",
            "periodEnd": "2026-09-30",
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["recordNo"].startswith("PR")
    assert body["data"]["status"] == "DRAFT"
    record_id = body["data"]["id"]

    listed = client.get(
        "/admin-api/ims/perf/execution/list",
        headers=auth,
        params={"schemeId": scheme_id, "status": "DRAFT", "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert any(row["id"] == record_id for row in listed.json()["data"]["list"])


def test_perf_execution_rejects_inactive_scheme():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "未启用方案",
            "positionCode": "R6",
            "periodType": "MONTHLY",
            "activate": False,
            "items": [
                {"metricName": "X", "weight": 100, "calcRule": "AUTO"},
            ],
        },
    )
    scheme_id = scheme.json()["data"]["id"]
    bad = client.post(
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
    assert bad.json()["code"] == 1001


def test_perf_result_list_after_confirmed():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "结果读屏方案",
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
            "periodStart": "2026-09-01",
            "periodEnd": "2026-09-30",
        },
    )
    record_id = created.json()["data"]["id"]
    db = SessionLocal()
    try:
        row = db.get(PerfRecord, record_id)
        row.status = "CONFIRMED"
        row.total_score = 88.0
        db.commit()
    finally:
        db.close()

    listed = client.get(
        "/admin-api/ims/perf/result/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    hit = [r for r in listed.json()["data"]["list"] if r["id"] == record_id]
    assert hit and hit[0]["grade"] == "S"

    detail = client.get(f"/admin-api/ims/perf/result/{record_id}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["published"] is True

    draft = client.post(
        "/admin-api/ims/perf/execution",
        headers=auth,
        json={
            "schemeId": scheme_id,
            "targetUserId": 1,
            "periodType": "MONTHLY",
            "periodStart": "2026-08-01",
            "periodEnd": "2026-08-31",
        },
    )
    draft_id = draft.json()["data"]["id"]
    blocked = client.get(f"/admin-api/ims/perf/result/{draft_id}", headers=auth)
    assert blocked.json()["code"] == 1157


def test_perf_calculate_and_confirm():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "算分确认方案",
            "positionCode": "R5",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [
                {"metricName": "开播场次", "weight": 40, "calcRule": "AUTO"},
                {"metricName": "直播 GMV", "weight": 60, "calcRule": "AUTO"},
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
            "periodStart": "2026-10-01",
            "periodEnd": "2026-10-31",
        },
    )
    record_id = created.json()["data"]["id"]

    calc = client.post(f"/admin-api/ims/perf/execution/{record_id}/calculate", headers=auth)
    assert calc.json()["code"] == 0
    assert calc.json()["data"]["status"] == "CALCULATED"
    assert calc.json()["data"]["totalScore"] is not None

    confirm = client.post(f"/admin-api/ims/perf/execution/{record_id}/confirm", headers=auth)
    assert confirm.json()["code"] == 0
    assert confirm.json()["data"]["status"] == "CONFIRMED"

    result = client.get(f"/admin-api/ims/perf/result/{record_id}", headers=auth)
    assert result.json()["code"] == 0


def test_perf_adjust_and_locked_1155():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "人工调整方案",
            "positionCode": "R5",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [{"metricName": "指标 A", "weight": 100, "calcRule": "AUTO"}],
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
            "periodStart": "2026-10-01",
            "periodEnd": "2026-10-31",
        },
    )
    record_id = created.json()["data"]["id"]

    calc = client.post(f"/admin-api/ims/perf/execution/{record_id}/calculate", headers=auth)
    base = calc.json()["data"]["totalScore"]
    assert calc.json()["data"]["status"] == "CALCULATED"

    adj = client.put(
        f"/admin-api/ims/perf/execution/{record_id}/adjust",
        headers=auth,
        json={"manualAdjustment": 3, "remark": "场次补录"},
    )
    assert adj.json()["code"] == 0
    assert adj.json()["data"]["status"] == "REVIEWED"
    assert adj.json()["data"]["totalScore"] == round(base + 3, 1)

    confirm = client.post(f"/admin-api/ims/perf/execution/{record_id}/confirm", headers=auth)
    assert confirm.json()["code"] == 0

    locked = client.put(
        f"/admin-api/ims/perf/execution/{record_id}/adjust",
        headers=auth,
        json={"manualAdjustment": 1},
    )
    assert locked.json()["code"] == 1155


def test_perf_issue_from_confirmed_and_locked_1155():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "下发方案",
            "positionCode": "R5",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [{"metricName": "指标 A", "weight": 100, "calcRule": "AUTO"}],
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
            "periodStart": "2026-11-01",
            "periodEnd": "2026-11-30",
        },
    )
    record_id = created.json()["data"]["id"]
    client.post(f"/admin-api/ims/perf/execution/{record_id}/calculate", headers=auth)
    client.post(f"/admin-api/ims/perf/execution/{record_id}/confirm", headers=auth)

    issued = client.put(f"/admin-api/ims/perf/execution/{record_id}/issue", headers=auth)
    assert issued.json()["code"] == 0
    assert issued.json()["data"]["status"] == "ISSUED"

    again = client.put(f"/admin-api/ims/perf/execution/{record_id}/issue", headers=auth)
    assert again.json()["code"] == 1155


def test_perf_result_export_csv():
    auth = headers()
    scheme = client.post(
        "/admin-api/ims/perf/scheme",
        headers=auth,
        json={
            "templateName": "导出方案",
            "positionCode": "R5",
            "periodType": "MONTHLY",
            "activate": True,
            "items": [{"metricName": "指标 A", "weight": 100, "calcRule": "AUTO"}],
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
            "periodStart": "2026-12-01",
            "periodEnd": "2026-12-31",
        },
    )
    record_id = created.json()["data"]["id"]
    client.post(f"/admin-api/ims/perf/execution/{record_id}/calculate", headers=auth)
    client.post(f"/admin-api/ims/perf/execution/{record_id}/confirm", headers=auth)
    client.put(f"/admin-api/ims/perf/execution/{record_id}/issue", headers=auth)

    resp = client.get("/admin-api/ims/perf/result/export", headers=auth)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    text = resp.content.decode("utf-8-sig")
    lines = [line for line in text.strip().splitlines() if line]
    assert lines[0].startswith("recordNo,")
    assert any("ISSUED" in line for line in lines[1:])
    assert any(created.json()["data"]["recordNo"] in line for line in lines[1:])
