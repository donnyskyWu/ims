"""#150 · BI/DC 本地收尾：预览空态、导出边界。不覆盖看板总览/布局/查询性能。"""

import io
import os
import time
import zipfile

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app import bi_drill, dc_trace

client = TestClient(app)


def login(username: str = "admin", password: str = "Admin@123") -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": password},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_preview_outside_window_is_empty_and_inverted_dates_fail():
    auth = login()
    outside = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"dateFrom": "2020-01-01", "dateTo": "2020-01-02", "platform": "抖音"},
    )
    body = outside.json()
    assert body["code"] == 0, body
    assert body["data"]["empty"] is True
    assert body["data"]["kpis"] == []
    assert body["data"]["rows"] == []
    assert body["data"]["emptyReason"] == "当前筛选下暂无指标"

    edge = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"dateFrom": "2026-10-03", "dateTo": "2026-10-03"},
    )
    edge_body = edge.json()
    assert edge_body["code"] == 0, edge_body
    assert edge_body["data"]["empty"] is False
    assert edge_body["data"]["kpis"]

    inverted = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"dateFrom": "2026-10-03", "dateTo": "2026-09-01"},
    )
    assert inverted.json()["code"] == 1001
    assert "晚于" in inverted.json()["msg"]

    bad = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"dateFrom": "2026-13-01", "dateTo": "2026-10-03"},
    )
    assert bad.json()["code"] == 1001

    open_range = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"platform": "抖音"},
    )
    assert open_range.json()["code"] == 0
    assert open_range.json()["data"]["rows"]


def test_bi_export_edges_expired_other_user_and_bad_context():
    auth = login()
    spaced = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={"drillPath": " PLATFORM , ACCOUNT ", "format": "csv", "filterContext": "{}"},
    )
    spaced_body = spaced.json()
    assert spaced_body["code"] == 0, spaced_body
    assert spaced_body["data"]["fileName"] == "bi_drill.csv"
    csv_file = client.get(spaced_body["data"]["downloadUrl"], headers=auth)
    text = csv_file.content.decode("utf-8-sig")
    assert "账号" in text
    assert "神鱼官方" in text

    array_ctx = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={"drillPath": "PLATFORM", "filterContext": "[]", "format": "XLSX"},
    )
    assert array_ctx.json()["code"] == 1001

    exported = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={"drillPath": "PLATFORM", "format": "XLSX"},
    )
    payload = exported.json()["data"]
    token = payload["downloadUrl"].split("token=", 1)[1]
    item = bi_drill._EXPORTS[token]
    bi_drill._EXPORTS[token] = (time.time() - 5, item[1], item[2], item[3], item[4])
    expired = client.get(payload["downloadUrl"], headers=auth)
    assert expired.status_code == 401
    assert expired.json()["code"] == 1002
    assert "过期" in expired.json()["msg"]

    fresh = client.get(
        "/admin-api/ims/bi/query/export",
        headers=auth,
        params={"drillPath": "PLATFORM", "format": "XLSX"},
    )
    fresh_url = fresh.json()["data"]["downloadUrl"]
    other = login("e2e_author")
    denied = client.get(fresh_url, headers=other)
    assert denied.status_code == 403
    assert denied.json()["code"] == 1008


def test_dc_export_case_blank_entry_and_header_only():
    auth = login()
    blank = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": "  ", "format": "XLSX"},
    )
    assert blank.json()["code"] == 1001
    assert "entryId" in blank.json()["msg"]

    exported = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": "999999999", "format": "xlsx"},
    )
    body = exported.json()
    assert body["code"] == 0, body
    assert body["data"]["sessionCount"] == 0
    assert body["data"]["fileName"] == "dc_trace_report.xlsx"
    assert body["data"]["expiresIn"] == 300
    file_resp = client.get(body["data"]["downloadUrl"], headers=auth)
    assert file_resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(file_resp.content)) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "sessionTitle" in xml
    assert "999999999" not in xml

    pdf = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "SESSION", "entryId": "NO-SUCH-SESSION", "format": " pdf "},
    )
    pdf_body = pdf.json()
    assert pdf_body["code"] == 0, pdf_body
    assert pdf_body["data"]["sessionCount"] == 0
    pdf_file = client.get(pdf_body["data"]["downloadUrl"], headers=auth)
    assert pdf_file.content.startswith(b"%PDF")

    token = body["data"]["downloadUrl"].split("token=", 1)[1]
    item = dc_trace._EXPORTS[token]
    dc_trace._EXPORTS[token] = (time.time() - 5, item[1], item[2], item[3], item[4])
    expired = client.get(body["data"]["downloadUrl"], headers=auth)
    assert expired.json()["code"] == 1002
