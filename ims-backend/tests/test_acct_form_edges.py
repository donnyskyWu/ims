"""#236 · 领用计划日、冲话费北京时间、交接/解冻/回收说明长度。"""

import os
import uuid
from datetime import timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app
from app.acct_flow import shanghai_today
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


def test_apply_rejects_blank_long_purpose_and_bad_plan_range():
    auth = headers()
    account_id = make_account(f"AC-PY-EDGE-{uuid.uuid4().hex[:8]}")
    blank = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={"accountId": account_id, "purpose": "  ", "planStart": "2026-10-08", "planEnd": "2026-11-08"},
    )
    assert blank.json()["code"] == 1001
    assert blank.json()["msg"] == "用途说明必填"

    long_purpose = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "用" * 257,
            "planStart": "2026-10-08",
            "planEnd": "2026-11-08",
        },
    )
    assert long_purpose.json()["code"] == 1001
    assert long_purpose.json()["msg"] == "用途说明不超过 256 字"

    missing = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={"accountId": account_id, "purpose": "领用", "planStart": "2026-10-08", "planEnd": ""},
    )
    assert missing.json()["code"] == 1001
    assert missing.json()["msg"] == "计划起止必填"

    same_day = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={"accountId": account_id, "purpose": "领用", "planStart": "2026-10-08", "planEnd": "2026-10-08"},
    )
    assert same_day.json()["code"] == 1001
    assert same_day.json()["msg"] == "计划结束须晚于计划开始"

    backwards = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={"accountId": account_id, "purpose": "领用", "planStart": "2026-11-08", "planEnd": "2026-10-08"},
    )
    assert backwards.json()["code"] == 1001
    assert backwards.json()["msg"] == "计划结束须晚于计划开始"

    ok = client.post(
        "/admin-api/ims/account/apply",
        headers=auth,
        json={
            "accountId": account_id,
            "purpose": "用" * 256,
            "planStart": "2026-10-08",
            "planEnd": "2026-10-09",
        },
    )
    assert ok.json()["code"] == 0, ok.json()


def test_recharge_date_uses_shanghai_today():
    auth = headers()
    account_id = make_account(f"AC-PY-RC-{uuid.uuid4().hex[:8]}")
    today = shanghai_today().isoformat()
    tomorrow = (shanghai_today() + timedelta(days=1)).isoformat()
    future = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"accountId": account_id, "amount": 12.5, "channel": "ALIPAY", "rechargeDate": tomorrow},
    )
    assert future.json()["code"] == 1001
    assert future.json()["msg"] == "充值日期不得晚于今日"

    current = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={"accountId": account_id, "amount": 12.5, "channel": "ALIPAY", "rechargeDate": today},
    )
    assert current.json()["code"] == 0, current.json()
    assert current.json()["data"]["rechargeDate"] == today


def test_remark_length_is_distinct_from_required():
    auth = headers()
    long_transfer = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": 1,
            "transferType": "TRANSFER",
            "toUserId": 1,
            "reasonType": "BUSINESS_ADJUST",
            "remark": "交接" * 300,
        },
    )
    assert long_transfer.json()["code"] == 1001
    assert long_transfer.json()["msg"] == "交接说明不超过 512 字"

    empty_transfer = client.post(
        "/admin-api/ims/account/transfer",
        headers=auth,
        json={
            "accountId": 1,
            "transferType": "RECALL",
            "reasonType": "BUSINESS_ADJUST",
            "remark": "   ",
        },
    )
    assert empty_transfer.json()["code"] == 1001
    assert empty_transfer.json()["msg"] == "交接说明必填"

    long_unfreeze = client.post(
        "/admin-api/ims/account/1/unfreeze",
        headers=auth,
        json={"remark": "解" * 513},
    )
    assert long_unfreeze.json()["code"] == 1001
    assert long_unfreeze.json()["msg"] == "解冻说明不超过 512 字"

    long_recycle = client.post(
        "/admin-api/ims/account/1/recycle",
        headers=auth,
        json={"remark": "回" * 513},
    )
    assert long_recycle.json()["code"] == 1001
    assert long_recycle.json()["msg"] == "回收说明不超过 512 字"
