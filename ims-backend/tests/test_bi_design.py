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


def test_bi_design_datasets_save_publish():
    auth = headers()
    ds = client.get("/admin-api/ims/bi/report/datasets", headers=auth)
    assert ds.json()["code"] == 0
    assert ds.json()["data"]["compLib"]

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "W9 设计器", "reportType": "REPORT", "category": "内容分析"},
    )
    rid = created.json()["data"]["id"]

    layout = {
        "layoutMode": "FREE",
        "comps": [{"id": "c1", "type": "KPI", "title": "粉丝", "x": 40, "y": 40, "w": 240, "h": 120}],
    }
    saved = client.put(f"/admin-api/ims/bi/report/{rid}", headers=auth, json={"layoutJson": layout})
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["comps"][0]["title"] == "粉丝"

    preview = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "c1", "components": layout["comps"]},
    )
    assert preview.json()["code"] == 0

    pub = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert pub.json()["code"] == 0
    assert pub.json()["data"]["status"] == "PUBLISHED"


def test_bi_design_bind_metric_rejects_illegal_field():
    auth = headers()
    ds = client.get("/admin-api/ims/bi/report/datasets", headers=auth).json()["data"]
    types = {item["type"] for item in ds["compLib"]}
    grouped = {
        "CHART": ["KPI", "BAR", "LINE", "PIE", "DONUT", "RADAR", "FUNNEL", "SCATTER", "TABLE", "DETAIL_TABLE", "RICH_TEXT"],
        "FILTER": ["DATE_RANGE", "SELECT_SINGLE", "SELECT_MULTI", "TEXT_INPUT", "NUMBER_RANGE"],
        "CONTAINER": ["GROUP", "CARD", "TAB"],
        "ACTION": ["BUTTON", "LINK", "TRIGGER"],
    }
    actual = {group: [item["type"] for item in ds["compLib"] if item["group"] == group] for group in grouped}
    assert actual == grouped
    assert types == {code for codes in grouped.values() for code in codes}
    assert "AREA" not in types and "CASCADE" not in types
    names = {item["type"]: item["name"] for item in ds["compLib"]}
    assert names["RICH_TEXT"] == "富文本"
    assert names["TABLE"] == "数据表"
    assert names["DATE_RANGE"] == "日期范围"
    assert names["TRIGGER"] == "联动触发件"
    assert len(ds["compLib"]) == 22
    metric = next(item for item in ds["datasets"] if item["code"] == "METRIC_LIB")
    keys = {field["fieldKey"] for field in metric["fields"]}
    assert {"statDate", "gmv"} <= keys
    assert any(field["fieldKey"] == "gmv" and field["metricCode"] == "GMV_DAILY" for field in metric["fields"])

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "W9 绑定", "reportType": "REPORT", "category": "内容分析"},
    )
    rid = created.json()["data"]["id"]
    bound = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={
            "reportId": rid,
            "compId": "c1",
            "components": [
                {"id": "c1", "type": "KPI", "dataset": "METRIC_LIB", "metric": "gmv", "agg": "SUM"},
            ],
        },
    )
    assert bound.json()["code"] == 0
    assert bound.json()["data"]["rows"][0]["value"] == 696000

    series = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={
            "reportId": rid,
            "compId": "c2",
            "components": [
                {
                    "id": "c2",
                    "type": "LINE",
                    "dataset": "METRIC_LIB",
                    "dimension": "statDate",
                    "metric": "gmv",
                    "agg": "SUM",
                }
            ],
        },
    )
    assert series.json()["code"] == 0
    assert len(series.json()["data"]["rows"]) == 3

    illegal = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={
            "reportId": rid,
            "compId": "c1",
            "components": [{"id": "c1", "type": "KPI", "dataset": "METRIC_LIB", "metric": "not_registered"}],
        },
    )
    assert illegal.json()["code"] == 1191

    dim_as_value = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={
            "reportId": rid,
            "compId": "c1",
            "components": [{"id": "c1", "type": "KPI", "dataset": "METRIC_LIB", "metric": "statDate"}],
        },
    )
    assert dim_as_value.json()["code"] == 1191

    bad_expr = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={
            "reportId": rid,
            "compId": "c1",
            "components": [{"id": "c1", "type": "KPI", "dataset": "METRIC_LIB", "calcExpression": "DROP(gmv)"}],
        },
    )
    assert bad_expr.json()["code"] == 1192


def test_bi_publish_keeps_v1_then_bumps():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "版本报表", "reportType": "REPORT", "category": "日报"},
    )
    body = created.json()["data"]
    rid = body["id"]
    assert body["version"] == 1
    assert body["status"] == "DRAFT"
    first = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert first.json()["code"] == 0
    assert first.json()["data"]["status"] == "PUBLISHED"
    assert first.json()["data"]["version"] == 1
    second = client.post(f"/admin-api/ims/bi/report/{rid}/publish", headers=auth)
    assert second.json()["data"]["version"] == 2
    saved = client.put(
        f"/admin-api/ims/bi/report/{rid}",
        headers=auth,
        json={"layoutJson": {"layoutMode": "FREE", "comps": []}},
    )
    assert saved.json()["data"]["version"] == 3
