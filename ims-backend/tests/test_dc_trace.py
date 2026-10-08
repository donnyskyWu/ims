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
