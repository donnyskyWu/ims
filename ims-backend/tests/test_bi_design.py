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


def test_bi_design_bind_metric_and_reject_illegal_field():
    auth = headers()
    ds = client.get("/admin-api/ims/bi/report/datasets", headers=auth).json()["data"]
    metric_codes = {
        field.get("metricCode")
        for dataset in ds["datasets"]
        if dataset["code"] == "METRIC_LIB"
        for field in dataset["fields"]
    }
    assert "GMV_DAILY" in metric_codes
    types = {item["type"] for item in ds["compLib"]}
    for required in ("LINE", "BAR", "PIE", "AREA", "RADAR", "FUNNEL", "TABLE", "KPI", "DATE_RANGE", "CASCADE", "TAB", "GROUP", "BUTTON", "LINK", "JUMP"):
        assert required in types

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "绑定 GMV", "reportType": "REPORT", "category": "内容"},
    )
    rid = created.json()["data"]["id"]
    bound = {
        "id": "k1",
        "type": "KPI",
        "title": "GMV",
        "x": 40,
        "y": 40,
        "w": 240,
        "h": 120,
        "dataset": "METRIC_LIB",
        "metricKey": "gmv",
        "metricCode": "GMV_DAILY",
        "dimensionKey": "statDate",
        "agg": "SUM",
    }
    queried = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "k1", "components": [bound]},
    )
    body = queried.json()
    assert body["code"] == 0
    assert body["data"]["rows"]
    assert body["data"]["metricTotal"] > 0
    assert any(row.get("gmv") for row in body["data"]["rows"])

    unknown = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "k1", "components": [{**bound, "customField": "not_registered"}]},
    )
    assert unknown.json()["code"] == 1191

    dim_as_value = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "k1", "components": [{**bound, "metricKey": "platform", "metricCode": ""}]},
    )
    assert dim_as_value.json()["code"] == 1191

    bad_expr = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "k1", "components": [{**bound, "calcExpression": "CONCAT(gmv)"}]},
    )
    assert bad_expr.json()["code"] == 1192

    good_expr = client.post(
        "/admin-api/ims/bi/report/query",
        headers=auth,
        json={"reportId": rid, "compId": "k1", "components": [{**bound, "calcExpression": "(SUM(gmv) - SUM(cost)) / SUM(gmv)"}]},
    )
    assert good_expr.json()["code"] == 0
