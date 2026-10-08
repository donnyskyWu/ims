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


def test_dc_trace_entry_and_query():
    auth = headers()
    entry = client.get(
        "/admin-api/ims/dc/trace/entry",
        headers=auth,
        params={"entryType": "ACCOUNT", "keyword": "", "limit": 5},
    )
    assert entry.json()["code"] == 0
    assert isinstance(entry.json()["data"], list)

    items = entry.json()["data"]
    entry_id = items[0]["entryId"] if items else "1"
    entry_type = items[0]["entryType"] if items else "ACCOUNT"
    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={
            "entryType": entry_type,
            "entryId": entry_id,
            "mode": "GRAPH",
            "pageNo": 1,
            "pageSize": 5,
        },
    )
    body = queried.json()
    assert body["code"] == 0
    assert "queryCostMs" in body["data"]
    assert "nodes" in body["data"]


def test_dc_trace_account_keyword_detail_mode():
    """#52 · E2E 种子账号 AC-E2E-FIN 入口 + DETAIL 模式（无种子时跳过断言入口命中）"""
    auth = headers()
    entry = client.get(
        "/admin-api/ims/dc/trace/entry",
        headers=auth,
        params={"entryType": "ACCOUNT", "keyword": "AC-E2E-FIN", "limit": 5},
    )
    assert entry.json()["code"] == 0
    items = entry.json()["data"]
    fin_hit = next((i for i in items if "AC-E2E-FIN" in (i.get("entryLabel") or "")), None)
    if not fin_hit:
        return
    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={
            "entryType": fin_hit["entryType"],
            "entryId": fin_hit["entryId"],
            "mode": "DETAIL",
            "pageNo": 1,
            "pageSize": 10,
        },
    )
    body = queried.json()
    assert body["code"] == 0
    data = body["data"]
    assert "detailList" in data
    assert isinstance(data["detailList"].get("list"), list)
    assert data["detailList"]["total"] >= 1
    assert "code" not in data["detailList"]
    node_types = {n["nodeType"] for n in data["nodes"]}
    assert "ACCOUNT" in node_types
    assert "SESSION" in node_types


def test_dc_trace_session_detail_export_and_timeout():
    """#53 · 场次明细下钻 + XLSX/PDF 导出 + 1181 宽日期降级 + 1504"""
    from tests.test_fin import approved_session, confirm_cost_for_session

    auth = headers()
    code = approved_session(auth)
    confirm_cost_for_session(auth, code)
    detail_live = client.get(f"/admin-api/ims/live/register/{code}", headers=auth)
    assert detail_live.json()["code"] == 0
    account_id = str(detail_live.json()["data"]["accountId"])

    queried = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={"entryType": "ACCOUNT", "entryId": account_id, "mode": "DETAIL", "pageNo": 1, "pageSize": 10},
    )
    body = queried.json()
    assert body["code"] == 0
    listed = [row["sessionCode"] for row in body["data"]["detailList"]["list"]]
    assert code in listed

    detail = client.get(f"/admin-api/ims/dc/trace/detail/{code}", headers=auth)
    detail_body = detail.json()
    assert detail_body["code"] == 0
    assert detail_body["data"]["sessionCode"] == code
    assert detail_body["data"]["liveData"]["gmv"] == 100000.0
    assert detail_body["data"]["profit"]["netProfit"] == 81400.0
    amounts = {row["costItem"]: row["amount"] for row in detail_body["data"]["costDetail"]}
    assert amounts["ad"] == 5000.0
    assert detail_body["data"]["dataAsOf"]

    missing = client.get("/admin-api/ims/dc/trace/detail/NO-SUCH-SESSION", headers=auth)
    assert missing.json()["code"] == 1504

    exported = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id, "format": "XLSX"},
    )
    export_body = exported.json()
    assert export_body["code"] == 0
    assert export_body["data"]["expiresIn"] == 300
    download_url = export_body["data"]["downloadUrl"]
    assert download_url.startswith("/admin-api/ims/dc/trace/export/file?token=")
    file_resp = client.get(download_url, headers=auth)
    assert file_resp.status_code == 200
    assert code.encode() in file_resp.content
    assert b"queryCostMs" in file_resp.content

    pdf = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "SESSION", "entryId": code, "format": "PDF"},
    )
    assert pdf.json()["code"] == 0
    pdf_file = client.get(pdf.json()["data"]["downloadUrl"], headers=auth)
    assert pdf_file.status_code == 200
    assert pdf_file.content.startswith(b"%PDF")
    assert code.encode() in pdf_file.content

    bad_format = client.get(
        "/admin-api/ims/dc/trace/export",
        headers=auth,
        params={"entryType": "ACCOUNT", "entryId": account_id, "format": "CSV"},
    )
    assert bad_format.json()["code"] == 1001

    slow = client.post(
        "/admin-api/ims/dc/trace/query",
        headers=auth,
        json={
            "entryType": "ACCOUNT",
            "entryId": account_id,
            "mode": "DETAIL",
            "dateRange": ["2020-01-01", "2026-12-31"],
        },
    )
    slow_body = slow.json()
    assert slow_body["code"] == 1181
    assert "缩小" in slow_body["msg"]
    assert isinstance(slow_body["data"]["queryCostMs"], (int, float))
