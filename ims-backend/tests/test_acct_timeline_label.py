"""#204 · 单账号时间线带回中文类型和操作人，不改筛选参数。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def make_account(account_no: str) -> int:
    ops = ops_session()
    try:
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type="DOUYIN",
            status="IN_POOL",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        ops.refresh(row)
        return int(row.id)
    finally:
        ops.close()


def test_timeline_includes_chinese_label_and_operator():
    auth = headers()
    account_id = make_account(f"AC-PY-TL-{uuid.uuid4().hex[:8]}")
    apply = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "pytest 时间线标签",
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    body = apply.json()
    assert body["code"] == 0, body
    apply_id = body["data"]["id"]
    approved = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/approve",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approved.json()["code"] == 0
    confirmed = client.put(
        f"/admin-api/ims/account/apply/{apply_id}/confirm",
        headers=auth,
        json={"passwordReset": True},
    )
    assert confirmed.json()["code"] == 0, confirmed.json()

    timeline = client.get(f"/admin-api/ims/account/timeline/{account_id}", headers=auth)
    payload = timeline.json()
    assert payload["code"] == 0, payload
    events = payload["data"]["list"]
    apply_event = next(item for item in events if item["eventType"] == "APPLY")
    assert apply_event["eventLabel"] == "领用"
    assert apply_event["operatorName"] == "管理员"
    assert "APPLY" == apply_event["eventType"]
