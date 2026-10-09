"""#199 · 查看审计时间范围开始晚于结束。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_view_logs_reject_inverted_time_range():
    bad = client.get(
        "/admin-api/ims/cert/security/view-logs",
        headers=headers(),
        params=[
            ("timeRange", "2026-10-09 00:00:00"),
            ("timeRange", "2026-10-01 00:00:00"),
        ],
    )
    body = bad.json()
    assert body["code"] == 1001
    assert "开始时间不能晚于结束时间" in body["msg"]

    same = client.get(
        "/admin-api/ims/cert/security/view-logs",
        headers=headers(),
        params=[
            ("timeRange", "2026-10-01 00:00:00"),
            ("timeRange", "2026-10-01 00:00:00"),
        ],
    )
    assert same.json()["code"] == 0
