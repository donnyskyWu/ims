"""#120 · 已核对冲话费解锁后再编辑，以及成本汇总导出 xlsx/csv。"""

import io
import os
import uuid
import zipfile
from decimal import Decimal

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.acct_seed import ensure_acct_finance_user, ensure_acct_peer_user
from app.core import SessionLocal
from app.main import app
from app.models import AccountRecharge, AccountRechargeVerify, AccountTimelineEvent, User
from app.ops_db import ops_session
from app.ops_models import PlatformAccount

client = TestClient(app)

MONTH = "2024-11"


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


def recharge(auth: dict, account_id: int, amount: float, day: str, voucher: str | None = None) -> dict:
    res = client.post(
        "/admin-api/ims/account/recharge",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": account_id,
            "amount": amount,
            "channel": "ALIPAY",
            "rechargeDate": day,
            "voucherUrl": voucher,
        },
    )
    body = res.json()
    assert body["code"] == 0, body
    return body["data"]


def verify(auth: dict, account_id: int, platform: float) -> dict:
    res = client.post(
        "/admin-api/ims/account/recharge/verify",
        headers=auth,
        json={"month": MONTH, "accountIds": [account_id], "platformConsumed": platform},
    )
    return res.json()


def edit(auth: dict, recharge_id: int, account_id: int, amount: float, day: str, voucher: str | None = None):
    return client.put(
        f"/admin-api/ims/account/recharge/{recharge_id}",
        headers=auth,
        json={
            "accountId": account_id,
            "amount": amount,
            "channel": "WECHAT",
            "rechargeDate": day,
            "voucherUrl": voucher,
        },
    )


def unlock(auth: dict, recharge_id: int):
    return client.post(f"/admin-api/ims/account/recharge/{recharge_id}/unlock", headers=auth)


def listed(auth: dict, account_id: int) -> dict:
    res = client.get(
        "/admin-api/ims/account/recharge/list",
        headers=auth,
        params={"accountId": account_id, "month": MONTH},
    )
    return res.json()["data"]["list"][0]


def prepare_roles() -> None:
    db = SessionLocal()
    try:
        ensure_acct_finance_user(db)
        ensure_acct_peer_user(db)
        db.commit()
    finally:
        db.close()


def clear_month() -> None:
    db = SessionLocal()
    try:
        ids = list(
            db.scalars(select(AccountRecharge.id).where(AccountRecharge.recharge_date.like(f"{MONTH}%"))).all()
        )
        if ids:
            db.execute(delete(AccountTimelineEvent).where(AccountTimelineEvent.ref_id.in_(ids), AccountTimelineEvent.event_type == "RECHARGE"))
        db.execute(delete(AccountRecharge).where(AccountRecharge.recharge_date.like(f"{MONTH}%")))
        db.execute(delete(AccountRechargeVerify).where(AccountRechargeVerify.month == MONTH))
        db.commit()
    finally:
        db.close()


def test_verified_recharge_stays_locked_until_admin_unlocks():
    prepare_roles()
    clear_month()
    admin = headers()
    finance = headers("e2e_acct_r3")
    peer = headers("e2e_acct_peer")
    suffix = uuid.uuid4().hex[:8]
    matched_account = make_account(f"UNL-M-{suffix}")
    diff_account = make_account(f"UNL-D-{suffix}")

    open_row = recharge(admin, matched_account, 40, f"{MONTH}-02")
    changed = edit(admin, open_row["id"], matched_account, 41.5, f"{MONTH}-03")
    assert changed.status_code == 200
    assert changed.json()["code"] == 0
    assert changed.json()["data"] is None
    assert listed(admin, matched_account)["amount"] == 41.5
    assert listed(admin, matched_account)["channel"] == "WECHAT"
    assert listed(admin, matched_account)["verifyStatus"] == "UNVERIFIED"

    blocked_peer = edit(peer, open_row["id"], matched_account, 10, f"{MONTH}-03")
    assert blocked_peer.status_code == 403
    assert blocked_peer.json()["code"] == 1008

    finance_edit = edit(finance, open_row["id"], matched_account, 42, f"{MONTH}-04")
    assert finance_edit.json()["code"] == 0, finance_edit.json()
    need_voucher = edit(finance, open_row["id"], matched_account, 6000, f"{MONTH}-04")
    assert need_voucher.json()["code"] == 1025

    passed = verify(admin, matched_account, 42)
    assert passed["code"] == 0, passed
    assert passed["data"]["verifyStatus"] == "MATCHED"
    locked = edit(admin, open_row["id"], matched_account, 43, f"{MONTH}-04")
    assert locked.json()["code"] == 1001
    assert "请先解锁" in locked.json()["msg"]
    finance_unlock = unlock(finance, open_row["id"])
    assert finance_unlock.status_code == 403
    assert finance_unlock.json()["code"] == 1008
    peer_unlock = unlock(peer, open_row["id"])
    assert peer_unlock.json()["code"] == 1008

    opened = unlock(admin, open_row["id"])
    assert opened.json()["code"] == 0, opened.json()
    assert opened.json()["data"]["previousStatus"] == "MATCHED"
    assert opened.json()["data"]["verifyStatus"] == "UNVERIFIED"
    again = unlock(admin, open_row["id"])
    assert again.json()["code"] == 1001
    assert "无需解锁" in again.json()["msg"]
    corrected = edit(admin, open_row["id"], matched_account, 44, f"{MONTH}-05")
    assert corrected.json()["code"] == 0, corrected.json()
    assert listed(admin, matched_account)["amount"] == 44
    assert listed(admin, matched_account)["verifyStatus"] == "UNVERIFIED"
    assert listed(admin, matched_account)["verifyDiff"] is None

    diff_row = recharge(admin, diff_account, 102, f"{MONTH}-08")
    over = verify(admin, diff_account, 100)
    assert over["code"] == 1026
    assert over["data"]["verifyStatus"] == "DIFF"
    assert over["data"]["workOrderId"]
    bare = SessionLocal()
    try:
        bare_row = bare.get(AccountRecharge, diff_row["id"])
        assert bare_row is not None
        bare_row.verify_status = "DIFF"
        bare_row.verify_diff = 2
        bare.execute(delete(AccountRechargeVerify).where(AccountRechargeVerify.month == MONTH, AccountRechargeVerify.account_id == diff_account))
        bare.commit()
    finally:
        bare.close()
    missing_ticket = unlock(admin, diff_row["id"])
    assert missing_ticket.json()["code"] == 1001
    assert "财务核查工单" in missing_ticket.json()["msg"]

    verify(admin, diff_account, 100)
    unlocked_diff = unlock(admin, diff_row["id"])
    assert unlocked_diff.json()["code"] == 0, unlocked_diff.json()
    assert unlocked_diff.json()["data"]["previousStatus"] == "DIFF"
    fixed = edit(admin, diff_row["id"], diff_account, 100, f"{MONTH}-08", voucher="RC-DIFF")
    assert fixed.json()["code"] == 0, fixed.json()
    assert listed(admin, diff_account)["amount"] == 100
    assert listed(admin, diff_account)["verifyStatus"] == "UNVERIFIED"

    moved = edit(admin, diff_row["id"], matched_account, 100, f"{MONTH}-08", voucher="RC-DIFF")
    assert moved.json()["code"] == 1001
    assert "不可变更账号" in moved.json()["msg"]

    db = SessionLocal()
    try:
        notes = list(
            db.scalars(
                select(AccountTimelineEvent.snapshot_summary).where(
                    AccountTimelineEvent.account_id == matched_account,
                    AccountTimelineEvent.event_type == "RECHARGE",
                )
            ).all()
        )
        assert any("解锁已核对记录" in text and "MATCHED" in text for text in notes)
        assert any(text.startswith("冲话费更正") for text in notes)
    finally:
        db.close()


def test_recharge_summary_export_xlsx_and_csv_match_query():
    clear_month()
    admin = headers()
    finance = headers("e2e_acct_r3")
    account_id = make_account(f"EXP-{uuid.uuid4().hex[:8]}")
    recharge(admin, account_id, 30.25, f"{MONTH}-01")
    recharge(admin, account_id, 19.75, f"{MONTH}-12")

    summary = client.get(
        "/admin-api/ims/account/recharge/summary",
        headers=admin,
        params={"month": MONTH, "groupBy": "ACCOUNT"},
    ).json()
    assert summary["code"] == 0
    row = summary["data"]["rows"][0]
    assert Decimal(str(row["totalAmount"])) == Decimal("50.00")
    assert row["recordCount"] == 2

    exported = client.get(
        "/admin-api/ims/account/recharge/summary/export",
        headers=admin,
        params={"month": MONTH, "groupBy": "ACCOUNT", "format": "xlsx"},
    )
    body = exported.json()
    assert body["code"] == 0, body
    assert body["data"]["fileName"] == f"recharge_summary_{MONTH}_ACCOUNT.xlsx"
    assert body["data"]["format"] == "XLSX"
    file_res = client.get(body["data"]["downloadUrl"], headers=admin)
    assert file_res.status_code == 200
    assert "spreadsheetml" in file_res.headers["content-type"]
    with zipfile.ZipFile(io.BytesIO(file_res.content)) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "50.00" in xml
    assert row["dimLabel"] in xml
    assert "合计" in xml

    stolen = client.get(body["data"]["downloadUrl"], headers=finance)
    assert stolen.status_code == 403
    assert stolen.json()["code"] == 1008

    csv_res = client.get(
        "/admin-api/ims/account/recharge/summary/export",
        headers=admin,
        params={"month": MONTH, "groupBy": "PLATFORM", "format": "CSV"},
    )
    csv_body = csv_res.json()
    assert csv_body["code"] == 0, csv_body
    csv_file = client.get(csv_body["data"]["downloadUrl"], headers=admin)
    text = csv_file.content.decode("utf-8-sig")
    assert "抖音" in text
    assert "50.00" in text
    assert "合计" in text

    bad_fmt = client.get(
        "/admin-api/ims/account/recharge/summary/export",
        headers=admin,
        params={"month": MONTH, "groupBy": "ACCOUNT", "format": "PDF"},
    )
    assert bad_fmt.json()["code"] == 1001
    bad_month = client.get(
        "/admin-api/ims/account/recharge/summary/export",
        headers=admin,
        params={"month": "202411", "groupBy": "ACCOUNT", "format": "CSV"},
    )
    assert bad_month.json()["code"] == 1001
