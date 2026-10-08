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


def test_perf_exam_questions_list():
    auth = headers()
    resp = client.get(
        "/admin-api/ims/perf/exam/questions",
        headers=auth,
        params={"pageNo": 1, "pageSize": 10, "knowledgeDomain": "LIVE_RULE"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 3
    assert all(row["knowledgeDomain"] == "LIVE_RULE" for row in body["data"]["list"])
    assert any(row["questionNo"] == "EQ-001" for row in body["data"]["list"])
