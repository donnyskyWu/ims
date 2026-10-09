"""#162 · 冲话费列表沿用既有查询参数，空月份导出标明零笔。"""

import os
import uuid
from decimal import Decimal

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)

MONTH = "2025-07"
OTHER = "2025-08"
EMPTY = "2099-12"


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


def recharge(auth: dict, account_id: int, amount: float, day: str, channel: str) -> None:
    res = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "amount": amount,
            "channel": channel,
            "rechargeDate": day,
        },
    )
    assert res.json()["code"] == 0, res.json()


def listing(auth: dict, **params) -> list:
    res = client.get("/admin-api/ims/account/recharge/list", headers=auth, params={"pageNo": 1, "pageSize": 50, **params})
    body = res.json()
    assert body["code"] == 0, body
    return body["data"]["list"]


def test_recharge_list_filters_by_account_status_month_and_channel():
    auth = headers()
    left = make_account(f"FLT-A-{uuid.uuid4().hex[:8]}")
    right = make_account(f"FLT-B-{uuid.uuid4().hex[:8]}")
    recharge(auth, left, 11.11, f"{MONTH}-03", "ALIPAY")
    recharge(auth, left, 33.33, f"{OTHER}-09", "BANK")
    recharge(auth, right, 22.22, f"{OTHER}-04", "WECHAT")

    july = listing(auth, accountId=left, month=MONTH)
    assert len(july) == 1
    assert july[0]["channel"] == "ALIPAY"
    assert Decimal(str(july[0]["amount"])) == Decimal("11.11")
    assert july[0]["verifyStatus"] == "UNVERIFIED"

    august_bank = listing(auth, accountId=left, month=OTHER, channel="BANK")
    assert len(august_bank) == 1
    assert Decimal(str(august_bank[0]["amount"])) == Decimal("33.33")

    wechat = listing(auth, accountId=right, channel="WECHAT", month=OTHER)
    assert len(wechat) == 1
    assert wechat[0]["accountId"] == right

    matched = listing(auth, accountId=left, verifyStatus="MATCHED", month=MONTH)
    assert matched == []

    unverified = listing(auth, accountId=left, verifyStatus="UNVERIFIED", month=MONTH)
    assert len(unverified) == 1

    other_account = listing(auth, accountId=right, month=MONTH)
    assert other_account == []


def test_recharge_summary_export_empty_month_reports_zero():
    auth = headers()
    exported = client.get(
        "/admin-api/ims/account/recharge/summary/export",
        headers=auth,
        params={"month": EMPTY, "groupBy": "ACCOUNT", "format": "CSV"},
    )
    body = exported.json()
    assert body["code"] == 0, body
    assert body["data"]["recordCount"] == 0
    assert Decimal(str(body["data"]["totalAmount"])) == Decimal("0.00")
    assert body["data"]["fileName"] == f"recharge_summary_{EMPTY}_ACCOUNT.csv"
    file_res = client.get(body["data"]["downloadUrl"], headers=auth)
    assert file_res.status_code == 200
    text = file_res.content.decode("utf-8-sig")
    assert "合计" in text
    assert "0.00" in text
    assert "11.11" not in text
