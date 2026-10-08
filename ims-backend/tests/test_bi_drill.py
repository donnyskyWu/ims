import io
import os
import zipfile

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CHAIN = ["PLATFORM", "ACCOUNT", "SESSION", "PERSON", "DATE", "SUBJECT"]
FIRST_VALUE = {
    "PLATFORM": "抖音",
    "ACCOUNT": "神鱼官方",
    "SESSION": "LS-20260928-01",
    "PERSON": "主播-林晓",
    "DATE": "2026-09-28",
    "SUBJECT": "神鱼文化",
}


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_dimension_tree_six_and_query_page_still_works():
    auth = headers()
    tree = client.get("/admin-api/ims/bi/query/dimension-tree", headers=auth)
    body = tree.json()
    assert body["code"] == 0
    six = next(item for item in body["data"]["trees"] if item["treeName"] == "自助六维")
    assert [level["dimensionKey"] for level in six["levels"]] == CHAIN
    prefix = next(item for item in body["data"]["trees"] if item["treeName"] == "平台→账号→场次")
    assert [level["dimensionKey"] for level in prefix["levels"]] == CHAIN[:3]

    page = client.get("/admin-api/ims/bi/query/page", headers=auth)
    assert page.json()["code"] == 0


def test_drill_six_dimensions_then_1195():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "六维下钻", "reportType": "REPORT", "category": "内容分析"},
    )
    report_id = created.json()["data"]["id"]
    path: list[str] = []
    for key in CHAIN:
        path.append(key)
        res = client.post(
            "/admin-api/ims/bi/query/drill",
            headers=auth,
            json={
                "reportId": report_id,
                "drillPath": path,
                "direction": "DOWN",
                "filterContext": {},
            },
        )
        body = res.json()
        assert body["code"] == 0, body
        assert body["data"]["dimensionKey"] == key
        assert body["data"]["rows"][0]["dimensionValue"] == FIRST_VALUE[key]
        assert body["data"]["queryMode"] == "SYNC"
        assert body["data"]["dataset"] == "METRIC_LIB"

    illegal = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={"reportId": report_id, "drillPath": path + ["PLATFORM"], "direction": "DOWN", "filterContext": {}},
    )
    assert illegal.json()["code"] == 1195

    skipped = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={"drillPath": ["PLATFORM", "SUBJECT"], "direction": "DOWN", "filterContext": {}},
    )
    assert skipped.json()["code"] == 1195

    empty = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={"drillPath": [], "direction": "DOWN", "filterContext": {}},
    )
    assert empty.json()["code"] == 1001

    missing = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={"reportId": 99999999, "drillPath": ["PLATFORM"], "direction": "DOWN", "filterContext": {}},
    )
    assert missing.status_code == 403
    assert missing.json()["code"] == 1008


def test_drill_up_returns_requested_level():
    auth = headers()
    res = client.post(
        "/admin-api/ims/bi/query/drill",
        headers=auth,
        json={"drillPath": ["PLATFORM", "ACCOUNT"], "direction": "UP", "filterContext": {"PLATFORM": "抖音"}},
    )
    body = res.json()
    assert body["code"] == 0
    assert body["data"]["direction"] == "UP"
    assert body["data"]["dimensionKey"] == "ACCOUNT"
    assert body["data"]["rows"][0]["dimensionValue"] == "神鱼官方"


def test_export_xlsx_and_csv_match_current_level():
    auth = headers()
    path = ",".join(CHAIN)
    exported = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={"drillPath": path, "filterContext": "{}", "format": "XLSX"},
    )
    body = exported.json()
    assert body["code"] == 0
    assert body["data"]["expiresIn"] == 60
    assert body["data"]["fileName"] == "bi_drill.xlsx"
    file_res = client.get(body["data"]["downloadUrl"], headers=auth)
    assert file_res.status_code == 200
    assert "spreadsheetml" in file_res.headers["content-type"]
    with zipfile.ZipFile(io.BytesIO(file_res.content)) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "主体" in xml
    assert "神鱼文化" in xml

    csv_res = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={"drillPath": "PLATFORM", "format": "CSV"},
    )
    csv_body = csv_res.json()
    assert csv_body["code"] == 0
    csv_file = client.get(csv_body["data"]["downloadUrl"], headers=auth)
    text = csv_file.content.decode("utf-8-sig")
    assert "平台" in text
    assert "抖音" in text

    bad_fmt = client.get("/admin-api/ims/bi/query/export", headers=auth, params={"format": "PDF"})
    assert bad_fmt.json()["code"] == 1001


def test_cell_drill_module_detail_and_dc_trace():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "穿透", "reportType": "REPORT", "category": "内容分析"},
    )
    report_id = created.json()["data"]["id"]
    detail = client.post(
        "/admin-api/ims/bi/query/cell-drill",
        headers=auth,
        json={
            "reportId": report_id,
            "cellDimensions": {"PLATFORM": "抖音", "SESSION": "LS-20260928-01", "SUBJECT": "神鱼文化"},
            "drillToDetail": True,
        },
    )
    detail_body = detail.json()
    assert detail_body["code"] == 0
    assert detail_body["data"]["jumpType"] == "MODULE_DETAIL"
    assert "LS-20260928-01" in detail_body["data"]["jumpUrl"]
    assert detail_body["data"]["jumpUrl"].startswith("/ims/live/sessions")

    trace = client.post(
        "/admin-api/ims/bi/query/cell-drill",
        headers=auth,
        json={
            "reportId": report_id,
            "cellDimensions": {"PLATFORM": "抖音"},
            "drillToDetail": True,
        },
    )
    trace_body = trace.json()
    assert trace_body["code"] == 0
    assert trace_body["data"]["jumpType"] == "DC_TRACE"
    assert trace_body["data"]["jumpParams"]["entryType"] == "PLATFORM"
    assert trace_body["data"]["jumpParams"]["keyword"] == "抖音"

    hidden = client.post(
        "/admin-api/ims/bi/query/cell-drill",
        headers=auth,
        json={"reportId": 99999999, "cellDimensions": {"PLATFORM": "抖音"}, "drillToDetail": False},
    )
    assert hidden.json()["code"] == 1008
