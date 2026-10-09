"""#185 · 单账号时间线按类型和时间筛选。缺省仍返回全部事件。"""

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


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
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


def checkout(auth: dict, account_id: int) -> None:
    apply = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "pytest 时间线筛选",
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


def types_of(payload: dict) -> list[str]:
    return [item["eventType"] for item in payload["data"]["list"]]


def test_account_timeline_filters_type_and_time():
    auth = headers()
    account_id = make_account(f"AC-PY-TL-{uuid.uuid4().hex[:8]}")
    checkout(auth, account_id)
    returned = client.post(
        "/admin-api/ims/account/return/submit",
        headers=auth,
        json={"accountId": account_id, "remark": "筛选前归还"},
    )
    assert returned.json()["code"] == 0

    all_events = client.get(f"/admin-api/ims/account/timeline/{account_id}", headers=auth)
    assert all_events.json()["code"] == 0
    assert set(types_of(all_events.json())) >= {"APPLY", "RETURN"}

    only_return = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("eventTypes", "RETURN")],
    )
    assert only_return.json()["code"] == 0
    assert types_of(only_return.json()) == ["RETURN"]

    both = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("eventTypes", "APPLY"), ("eventTypes", "RETURN")],
    )
    assert both.json()["code"] == 0
    assert set(types_of(both.json())) == {"APPLY", "RETURN"}

    none = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("eventTypes", "RECYCLE")],
    )
    assert none.json()["code"] == 0
    assert none.json()["data"]["list"] == []
    assert none.json()["data"]["total"] == 0

    illegal = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("eventTypes", "NOT_A_TYPE")],
    )
    assert illegal.json()["code"] == 1001

    partial = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("timeRange", "2026-10-01")],
    )
    assert partial.json()["code"] == 1001

    backwards = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("timeRange", "2026-12-01"), ("timeRange", "2026-01-01")],
    )
    assert backwards.json()["code"] == 1001

    outside = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[("timeRange", "2000-01-01 00:00:00"), ("timeRange", "2000-01-02 23:59:59")],
    )
    assert outside.json()["code"] == 0
    assert outside.json()["data"]["list"] == []

    inside = client.get(
        f"/admin-api/ims/account/timeline/{account_id}",
        headers=auth,
        params=[
            ("eventTypes", "APPLY"),
            ("timeRange", "2020-01-01"),
            ("timeRange", "2099-12-31"),
        ],
    )
    assert inside.json()["code"] == 0
    assert types_of(inside.json()) == ["APPLY"]
