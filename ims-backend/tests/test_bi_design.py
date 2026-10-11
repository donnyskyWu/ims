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
    assert {"KPI", "LINE", "BAR", "PIE", "AREA", "RADAR", "FUNNEL", "TABLE", "DATE_RANGE", "CASCADE", "BUTTON", "LINK"} <= types
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
