import os
os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine, utcnow
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_home_dashboard_kpis_and_shortcuts():
    auth = headers()
    resp = client.get("/admin-api/ims/home/dashboard", headers=auth)
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert len(data["kpis"]) == 4
    keys = {k["key"] for k in data["kpis"]}
    assert keys == {"accounts", "worksToday", "pendingTodos", "collectAlert"}
    assert data["kpis"][1]["value"] == "数据延迟"
    assert "Football" in data["kpis"][1]["wow"]
    assert "不随日期" in data["kpis"][1]["wow"]
    assert data["kpis"][0]["wow"] == "随 IP 组变化"
    assert "近 7 天" in data["kpis"][3]["wow"]
    assert "不按 IP 组或日期缩小" in data["kpis"][2]["wow"]
    note = data["filterNote"]
    assert "账号数随 IP 组" in note
    assert "不请求 Football" in note
    assert "近 7 天" in note
    assert "不按 IP 组或日期缩小" in note
    assert len(data["shortcuts"]) >= 4
    assert any(s["route"] == "/ims/collect/task" for s in data["shortcuts"])


def test_home_date_span_1202():
    auth = headers()
    resp = client.get(
        "/admin-api/ims/home/dashboard",
        headers=auth,
        params={"dateFrom": "2025-01-01", "dateTo": "2025-06-01"},
    )
    assert resp.json()["code"] == 1202


def test_home_todos_page():
    auth = headers()
    resp = client.get("/admin-api/ims/home/todos", headers=auth, params={"pageNo": 1, "pageSize": 10})
    assert resp.json()["code"] == 0
    assert "list" in resp.json()["data"]
