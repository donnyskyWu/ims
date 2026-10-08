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


def test_bi_screen_list_and_detail():
    auth = headers()
    listed = client.get("/admin-api/ims/bi/screen/list", headers=auth, params={"pageNo": 1, "pageSize": 10})
    body = listed.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 2
    assert all(row["reportType"] == "DASHBOARD" for row in body["data"]["list"])
    screen_id = body["data"]["list"][0]["id"]

    detail = client.get(f"/admin-api/ims/bi/screen/{screen_id}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["widgets"]
    preview = client.get(f"/admin-api/ims/bi/screen/{screen_id}/preview", headers=auth)
    assert preview.json()["code"] == 0
    assert preview.json()["data"]["reportName"]
