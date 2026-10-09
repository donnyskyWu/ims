"""#227 · 账实核对边角：未来月份、两位小数、方向与刚好 2.00%。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.core import SessionLocal
from app.main import app
from app.models import AccountRecharge, AccountRechargeVerify
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)

EQUAL_MONTH = "2022-01"
HIGHER_PLATFORM = "2022-02"
EXACT_MONTH = "2022-03"


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


def clear_month(account_id: int, month: str) -> None:
    db = SessionLocal()
    try:
        db.execute(
            delete(AccountRecharge).where(
                AccountRecharge.account_id == account_id,
                AccountRecharge.recharge_date.like(f"{month}%"),
            )
        )
        db.execute(
            delete(AccountRechargeVerify).where(
                AccountRechargeVerify.account_id == account_id,
                AccountRechargeVerify.month == month,
            )
        )
        db.commit()
    finally:
        db.close()


def verify_count(account_id: int, month: str) -> int:
    db = SessionLocal()
    try:
        return int(
            db.scalar(
                select(func.count())
                .select_from(AccountRechargeVerify)
                .where(
                    AccountRechargeVerify.account_id == account_id,
                    AccountRechargeVerify.month == month,
                )
            )
            or 0
        )
    finally:
        db.close()


def post_recharge(auth: dict, account_id: int, amount: float, day: str) -> None:
    res = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "amount": amount,
            "channel": "ALIPAY",
            "rechargeDate": day,
        },
    )
    assert res.json()["code"] == 0, res.json()


def post_verify(auth: dict, account_id: int, month: str, platform: float | None) -> dict:
    body: dict = {"month": month, "accountIds": [account_id]}
    if platform is not None:
        body["platformConsumed"] = platform
    return client.post("/admin-api/ims/account/recharge/verify", headers=auth, json=body).json()


def test_verify_rejects_future_month_extra_cents_and_bad_month():
    auth = headers()
    account_id = make_account("AC-EDGE-227")
    clear_month(account_id, "2022-06")
    before = verify_count(account_id, "2022-06")

    future = post_verify(auth, account_id, "2099-12", 100)
    assert future["code"] == 1001
    assert future["msg"] == "不能核对未来月份"
    assert verify_count(account_id, "2099-12") == 0

    bad_month = post_verify(auth, account_id, "2026-13", 100)
    assert bad_month["code"] == 1001
    assert bad_month["msg"] == "核对月份格式不合法"

    cents = post_verify(auth, account_id, "2022-06", 100.009)
    assert cents["code"] == 1001
    assert "两位小数" in cents["msg"]
    assert verify_count(account_id, "2022-06") == before

    zero = post_verify(auth, account_id, "2022-06", 0)
    assert zero["code"] == 1001
    assert "大于 0" in zero["msg"]

    negative = post_verify(auth, account_id, "2022-06", -1)
    assert negative["code"] == 1001
    assert "大于 0" in negative["msg"]

    one_decimal = post_verify(auth, account_id, "2022-06", 100.1)
    assert one_decimal["code"] == 1001
    assert "无冲话费" in one_decimal["msg"]


def test_verify_side_amounts_and_exact_threshold_items():
    auth = headers()
    account_id = make_account("AC-EDGE-227-SIDE")
    for month in (EQUAL_MONTH, HIGHER_PLATFORM, EXACT_MONTH):
        clear_month(account_id, month)

    post_recharge(auth, account_id, 80, f"{EQUAL_MONTH}-15")
    equal = post_verify(auth, account_id, EQUAL_MONTH, 80)
    assert equal["code"] == 0, equal
    assert equal["data"]["diffRateText"] == "0.00%"
    assert equal["data"]["verifyStatus"] == "MATCHED"
    assert equal["data"]["diffAmount"] == 0
    assert equal["data"]["totalRecharge"] == equal["data"]["platformConsumed"]
    items = equal["data"]["diffItems"]
    assert len(items) == 1
    assert items[0]["accountNo"] == "AC-EDGE-227-SIDE"
    assert items[0]["rechargeAmount"] == 80
    assert items[0]["platformAmount"] == 80
    assert items[0]["diff"] == 0

    post_recharge(auth, account_id, 100, f"{HIGHER_PLATFORM}-15")
    higher = post_verify(auth, account_id, HIGHER_PLATFORM, 100.5)
    assert higher["code"] == 0, higher
    assert higher["data"]["verifyStatus"] == "MATCHED"
    assert higher["data"]["totalRecharge"] < higher["data"]["platformConsumed"]
    assert higher["data"]["overThreshold"] is False
    assert higher["data"]["diffItems"][0]["platformAmount"] == 100.5

    post_recharge(auth, account_id, 102, f"{EXACT_MONTH}-15")
    exact = post_verify(auth, account_id, EXACT_MONTH, 100)
    assert exact["code"] == 1026
    assert exact["data"]["diffRateText"] == "2.00%"
    assert exact["data"]["overThreshold"] is True
    assert exact["data"]["totalRecharge"] > exact["data"]["platformConsumed"]
    assert exact["data"]["diffItems"][0]["diff"] == 2
    assert exact["data"]["workOrderId"]
