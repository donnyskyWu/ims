"""#155 · 账号列表责任人筛选 + 证件到期催办列表筛选。"""

import os
import uuid
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, PlatformAccount


client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _seed_douyin(account_no: str, holder_user_id: int, status: str) -> None:
    ops = ops_session()
    try:
        company = Company(company_name=f"甲公司{account_no}", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name=f"IP{account_no}", status="ENABLED", tenant_id=0)
        ops.add_all([company, group])
        ops.flush()
        ops.add(
            PlatformAccount(
                account_no=account_no,
                account_name=f"昵称{account_no}",
                platform_type="DOUYIN",
                ip_group_id=group.id,
                company_id=company.id,
                holder_user_id=holder_user_id,
                status=status,
                tenant_id=0,
            )
        )
        ops.commit()
    finally:
        ops.close()


def test_account_page_filters_holder_and_rejects_bad_status():
    auth = headers()
    created = client.post(
        "/admin-api/ims/system/user",
        headers=auth,
        json={"username": f"holder155{uuid.uuid4().hex[:8]}", "password": "Admin@123", "nickname": "筛选责任人"},
    )
    assert created.json()["code"] == 0, created.json()
    holder_id = int(created.json()["data"]["id"])
    mine = f"AC-155-{uuid.uuid4().hex[:6]}"
    other = f"AC-155B-{uuid.uuid4().hex[:6]}"
    _seed_douyin(mine, holder_id, "IN_POOL")
    _seed_douyin(other, 1, "IN_USE")

    page = client.get(
        "/admin-api/ims/corp/account/page",
        headers=auth,
        params={"platformType": "DOUYIN", "holderUserId": holder_id, "status": "IN_POOL", "keyword": mine},
    )
    body = page.json()
    assert body["code"] == 0, body
    assert body["data"]["total"] == 1
    assert body["data"]["list"][0]["accountNo"] == mine
    assert body["data"]["list"][0]["holderUserName"] == "筛选责任人"
    assert body["data"]["list"][0]["status"] == "IN_POOL"

    missed = client.get(
        "/admin-api/ims/corp/account/page",
        headers=auth,
        params={"platformType": "DOUYIN", "holderUserId": holder_id, "status": "FROZEN", "keyword": mine},
    )
    assert missed.json()["data"]["total"] == 0

    bad_status = client.get(
        "/admin-api/ims/corp/account/page",
        headers=auth,
        params={"platformType": "DOUYIN", "status": "NOPE"},
    )
    assert bad_status.json()["code"] == 1001

    missing = client.get(
        "/admin-api/ims/corp/account/page",
        headers=auth,
        params={"platformType": "DOUYIN", "holderUserId": 999999},
    )
    assert missing.json()["code"] == 1001
    assert missing.json()["msg"] == "责任人不存在"


def _upload(auth: dict, holder: str, days: int, number: str):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": number,
            "fileKey": "local/cert/upload",
            "issueDate": "2020-01-01",
            "expireDate": (today + timedelta(days=days)).isoformat(),
        },
    )


def test_cert_expire_list_filters_level_and_remind_summary():
    auth = headers()
    holder = f"E2E155{uuid.uuid4().hex[:6]}"
    created = _upload(auth, holder, 30, f"110101{uuid.uuid4().hex[:10]}"[:18].ljust(18, "0"))
    body = created.json()
    assert body["code"] == 0, body
    reviewed = client.put(
        f"/admin-api/ims/cert/archive/{body['data']['id']}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert reviewed.json()["code"] == 0
    scan = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    assert scan.json()["code"] == 0

    listed = client.get(
        "/admin-api/ims/cert/expire/list",
        headers=auth,
        params={"holderName": holder, "level": "YELLOW", "status": "WARNING"},
    )
    data = listed.json()["data"]
    assert data["total"] == 1
    row = data["list"][0]
    assert row["level"] == "YELLOW"
    assert row["notifiedSummary"].startswith("已通知：")
    assert "管理员" in row["notifiedSummary"]
    assert row["remindCount"] == 0
    assert row["lastRemindedAt"] == ""

    reminded = client.put(
        f"/admin-api/ims/cert/expire/{row['id']}/remind",
        headers=auth,
        json={"remindChannel": "APP"},
    )
    assert reminded.json()["code"] == 0, reminded.json()
    again = client.get(
        "/admin-api/ims/cert/expire/list",
        headers=auth,
        params={"holderName": holder, "level": "YELLOW"},
    )
    refreshed = again.json()["data"]["list"][0]
    assert refreshed["remindCount"] == 1
    assert refreshed["lastRemindedAt"]

    empty = client.get(
        "/admin-api/ims/cert/expire/list",
        headers=auth,
        params={"holderName": holder, "level": "LOCKED"},
    )
    assert empty.json()["data"]["total"] == 0

    bad = client.get("/admin-api/ims/cert/expire/list", headers=auth, params={"level": "GREEN"})
    assert bad.json()["code"] == 1001
    assert bad.json()["msg"] == "预警级别无效"
