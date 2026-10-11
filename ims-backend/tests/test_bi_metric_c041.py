"""BUG-C041：被引用指标删除返回 1502；导出带表头。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import BiMetric

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "tc_r9", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_tc_r9_referenced_metric_delete_is_1502_and_export_lists_it():
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/metric",
        headers=auth,
        json={"metricName": "C041被引用", "metricCode": "C041_REF", "metricType": "BASIC"},
    )
    assert created.json()["code"] == 0
    mid = created.json()["data"]["id"]

    db = SessionLocal()
    try:
        row = db.get(BiMetric, mid)
        assert row is not None
        row.ref_count = 2
        db.commit()
    finally:
        db.close()

    blocked = client.delete(f"/admin-api/ims/bi/metric/{mid}", headers=auth)
    assert blocked.json()["code"] == 1502
    assert blocked.json()["msg"] == "指标已被引用，不可删除"

    listed = client.get(
        "/admin-api/ims/bi/metric/list",
        headers=auth,
        params={"keyword": "C041_REF", "pageNo": 1, "pageSize": 5},
    )
    assert any(item["id"] == mid for item in listed.json()["data"]["list"])

    exported = client.get(
        "/admin-api/ims/bi/metric/export",
        headers=auth,
        params={"keyword": "C041_REF"},
    )
    body = exported.json()
    assert body["code"] == 0
    assert "指标编码" in body["data"]["csv"]
    assert "C041_REF" in body["data"]["csv"]
    assert body["data"]["count"] >= 1
