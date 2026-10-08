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


def test_master_overview_blocks():
    auth = headers()
    res = client.get("/admin-api/ims/master/overview", headers=auth)
    assert res.json()["code"] == 0
    blocks = res.json()["data"]["blocks"]
    assert len(blocks) >= 6
    assert any(b["key"] == "company" for b in blocks)
