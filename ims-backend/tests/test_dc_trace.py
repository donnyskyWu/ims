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
