"""#191 · 冲话费边界：未来日期、金额、超长备注、空白凭证与已注销账号。"""

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


def make_account(account_no: str, status: str = "IN_POOL") -> int:
    ops = ops_session()
    try:
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type="DOUYIN",
            status=status,
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        ops.refresh(row)
        return int(row.id)
    finally:
        ops.close()


def post_recharge(auth: dict, account_id: int, **overrides) -> dict:
    payload = {
        "accountId": account_id,
        "amount": 10,
        "channel": "ALIPAY",
        "rechargeDate": "2026-04-02",
    }
    payload.update(overrides)
    res = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=payload,
    )
    return res.json()


def test_recharge_edges_future_amount_remark_voucher_and_cancelled():
    auth = headers()
    account_id = make_account("AC-EDGE-191")

    future = post_recharge(auth, account_id, rechargeDate="2099-01-01")
    assert future["code"] == 1001
    assert "不得晚于" in future["msg"]

    zero = post_recharge(auth, account_id, amount=0)
    assert zero["code"] == 1001
    assert "金额" in zero["msg"]

    negative = post_recharge(auth, account_id, amount=-1)
    assert negative["code"] == 1001

    long_remark = post_recharge(auth, account_id, remark="备" * 257)
    assert long_remark["code"] == 1001
    assert "备注" in long_remark["msg"]

    blank_voucher = post_recharge(auth, account_id, amount=6000, voucherUrl="   ")
    assert blank_voucher["code"] == 1025

    boundary = post_recharge(auth, account_id, amount=5000)
    assert boundary["code"] == 0, boundary
    assert boundary["data"]["voucherUrl"] in (None, "")

    kept = post_recharge(auth, account_id, amount=12.5, remark="边缘备注")
    assert kept["code"] == 0, kept
    assert kept["data"]["remark"] == "边缘备注"
    assert kept["data"]["operatorName"]

    listed = client.get(
        "/admin-api/ims/account/recharge/list",
        headers=auth,
        params={"accountId": account_id, "pageNo": 1, "pageSize": 20},
    ).json()
    assert listed["code"] == 0
    match = next(row for row in listed["data"]["list"] if row["id"] == kept["data"]["id"])
    assert match["remark"] == "边缘备注"
    assert match["operatorName"]

    cancelled_id = make_account("AC-EDGE-191-X", status="CANCELLED")
    blocked = post_recharge(auth, cancelled_id, amount=8)
    assert blocked["code"] == 1001
    assert "注销" in blocked["msg"]
