"""#70 · ACCT-004 成本汇总：按账号 / 部门 / 平台聚合，期间为月份。"""

import os
import uuid
from decimal import Decimal

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core import SessionLocal
from app.main import app
from app.models import AccountRecharge, Role, User, UserDept, UserRole
from app.ops_db import ops_session
from app.ops_models import PlatformAccount
from app.security import hash_password

client = TestClient(app)

MONTH = "2026-01"
OTHER = "2025-12"


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def make_user(dept_id: int | None) -> tuple[int, str]:
    username = f"sum_{uuid.uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        user = User(
            username=username,
            nickname=username,
            mobile=f"138{uuid.uuid4().int % 10**8:08d}",
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        db.add(user)
        db.flush()
        if dept_id:
            db.add(UserDept(user_id=user.id, dept_id=dept_id, tenant_id=0))
        role = db.scalar(select(Role).where(Role.role_key == "sys:admin", Role.deleted == 0))
        assert role is not None
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.commit()
        return int(user.id), username
    finally:
        db.close()


def make_account(account_no: str, platform: str, holder_id: int | None) -> int:
    ops = ops_session()
    try:
        row = PlatformAccount(
            account_no=account_no,
            account_name=account_no,
            platform_type=platform,
            holder_user_id=holder_id,
            status="IN_POOL",
            tenant_id=0,
        )
        ops.add(row)
        ops.commit()
        ops.refresh(row)
        return int(row.id)
    finally:
        ops.close()


def recharge(auth: dict, account_id: int, amount: float, day: str) -> int:
    token = uuid.uuid4().hex
    res = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": token},
        json={"accountId": account_id, "amount": amount, "channel": "ALIPAY", "rechargeDate": day},
    )
    body = res.json()
    assert body["code"] == 0, body
    return int(body["data"]["id"])


def set_diff(recharge_id: int, diff: float) -> None:
    db = SessionLocal()
    try:
        row = db.get(AccountRecharge, recharge_id)
        assert row is not None
        row.verify_diff = diff
        row.verify_status = "DIFF"
        db.commit()
    finally:
        db.close()


def summary(auth: dict, month: str, group_by: str):
    return client.get(
        "/admin-api/ims/account/recharge/summary",
        headers=auth,
        params={"month": month, "groupBy": group_by},
    ).json()


def by_key(body: dict) -> dict[str, dict]:
    return {row["dimKey"]: row for row in body["data"]["rows"]}


def test_recharge_summary_groups_account_dept_platform_for_the_month():
    db = SessionLocal()
    try:
        db.execute(delete(AccountRecharge).where(AccountRecharge.recharge_date.like(f"{MONTH}%")))
        db.execute(delete(AccountRecharge).where(AccountRecharge.recharge_date.like(f"{OTHER}%")))
        db.commit()
    finally:
        db.close()

    suffix = uuid.uuid4().hex[:8]
    dept_a, dept_b = 70101, 70102
    user_a, name_a = make_user(dept_a)
    user_b, name_b = make_user(dept_b)
    user_none, name_none = make_user(None)
    auth_a = headers(name_a)
    auth_b = headers(name_b)
    auth_none = headers(name_none)

    account_a = make_account(f"SUM-A-{suffix}", "DOUYIN", user_a)
    account_b = make_account(f"SUM-B-{suffix}", "KUAISHOU", user_b)
    account_c = make_account(f"SUM-C-{suffix}", "XIAOHONGSHU", None)
    account_d = make_account(f"SUM-D-{suffix}", "DOUYIN", None)

    first = recharge(auth_a, account_a, 100.10, f"{MONTH}-02")
    second = recharge(auth_a, account_a, 50.40, f"{MONTH}-18")
    set_diff(second, 1.50)
    third = recharge(auth_b, account_b, 20, f"{MONTH}-03")
    set_diff(third, 0.25)
    recharge(auth_none, account_c, 3, f"{MONTH}-04")
    recharge(auth_b, account_d, 1, f"{MONTH}-05")
    recharge(auth_a, account_a, 9.99, f"{OTHER}-20")
    assert first > 0

    admin = headers()
    account_body = summary(admin, MONTH, "ACCOUNT")
    assert account_body["code"] == 0, account_body
    assert account_body["data"]["groupBy"] == "ACCOUNT"
    assert account_body["data"]["month"] == MONTH
    account_rows = by_key(account_body)
    assert money(account_rows[str(account_a)]["totalAmount"]) == money("150.50")
    assert account_rows[str(account_a)]["recordCount"] == 2
    assert money(account_rows[str(account_a)]["diffAmount"]) == money("1.50")
    assert f"SUM-A-{suffix}" in account_rows[str(account_a)]["dimLabel"]
    assert money(account_rows[str(account_b)]["totalAmount"]) == money("20.00")
    assert account_rows[str(account_b)]["recordCount"] == 1
    assert money(account_rows[str(account_c)]["totalAmount"]) == money("3.00")
    assert money(account_rows[str(account_d)]["totalAmount"]) == money("1.00")
    totals = account_body["data"]["totals"]
    assert money(totals["totalAmount"]) == money("174.50")
    assert totals["recordCount"] == 5
    assert money(totals["diffAmount"]) == money("1.75")
    assert money(sum(Decimal(str(row["totalAmount"])) for row in account_body["data"]["rows"])) == money(totals["totalAmount"])

    dept_body = summary(admin, MONTH, "DEPT")
    assert dept_body["code"] == 0, dept_body
    dept_rows = by_key(dept_body)
    assert dept_rows[str(dept_a)]["dimLabel"] == f"部门#{dept_a}"
    assert money(dept_rows[str(dept_a)]["totalAmount"]) == money("150.50")
    assert dept_rows[str(dept_a)]["recordCount"] == 2
    assert dept_rows[str(dept_b)]["dimLabel"] == f"部门#{dept_b}"
    assert money(dept_rows[str(dept_b)]["totalAmount"]) == money("21.00")
    assert dept_rows[str(dept_b)]["recordCount"] == 2
    assert dept_rows["0"]["dimLabel"] == "未分配"
    assert money(dept_rows["0"]["totalAmount"]) == money("3.00")
    assert money(dept_body["data"]["totals"]["totalAmount"]) == money("174.50")
    assert dept_body["data"]["totals"]["recordCount"] == 5

    platform_body = summary(admin, MONTH, "PLATFORM")
    assert platform_body["code"] == 0, platform_body
    platform_rows = by_key(platform_body)
    assert platform_rows["DOUYIN"]["dimLabel"] == "抖音"
    assert money(platform_rows["DOUYIN"]["totalAmount"]) == money("151.50")
    assert platform_rows["DOUYIN"]["recordCount"] == 3
    assert platform_rows["KUAISHOU"]["dimLabel"] == "快手"
    assert money(platform_rows["KUAISHOU"]["totalAmount"]) == money("20.00")
    assert platform_rows["XIAOHONGSHU"]["dimLabel"] == "小红书"
    assert money(platform_rows["XIAOHONGSHU"]["totalAmount"]) == money("3.00")
    assert money(platform_body["data"]["totals"]["totalAmount"]) == money("174.50")

    other = summary(admin, OTHER, "ACCOUNT")
    assert other["code"] == 0, other
    assert len(other["data"]["rows"]) == 1
    assert money(other["data"]["rows"][0]["totalAmount"]) == money("9.99")
    assert other["data"]["totals"]["recordCount"] == 1
    assert str(account_b) not in by_key(other)

    stored = SessionLocal()
    try:
        rows = list(
            stored.scalars(select(AccountRecharge).where(AccountRecharge.recharge_date.like(f"{MONTH}%"))).all()
        )
        assert len(rows) == 5
        assert money(sum(Decimal(str(row.amount)) for row in rows)) == money(totals["totalAmount"])
        diff = sum((Decimal(str(row.verify_diff)) if row.verify_diff is not None else Decimal("0")) for row in rows)
        assert money(diff) == money(totals["diffAmount"])
    finally:
        stored.close()


def test_recharge_summary_rejects_bad_month_and_group():
    auth = headers()
    missing = summary(auth, "", "ACCOUNT")
    assert missing["code"] == 1001
    bad_month = summary(auth, "2026-1", "ACCOUNT")
    assert bad_month["code"] == 1001
    bad_group = summary(auth, MONTH, "YEAR")
    assert bad_group["code"] == 1001
    empty = summary(auth, "2024-02", "ACCOUNT")
    assert empty["code"] == 0, empty
    assert empty["data"]["rows"] == []
    assert empty["data"]["totals"]["recordCount"] == 0
    assert money(empty["data"]["totals"]["totalAmount"]) == money("0")
