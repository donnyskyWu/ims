"""#71 · LIVE-R2 / CERT-E-R3：过期、锁定或未生效证件拦截开播（1045），换证后恢复。"""

import os
import uuid
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

client = TestClient(app)
HOLDER = "直播锁定人"
FREE = "直播自由人"


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_people() -> tuple[int, int, int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="锁定公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="锁定组", status="ENABLED", tenant_id=0)
        locked = Realname(
            real_name=HOLDER,
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199003031045"),
            phone_enc=encrypt_text("13800001045"),
            status="ENABLED",
            tenant_id=0,
        )
        free = Realname(
            real_name=FREE,
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199003031046"),
            phone_enc=encrypt_text("13800001046"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600001045"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-1045",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, locked, free, phone])
        ops.flush()
        locked_account = PlatformAccount(
            account_no="AC-PY-1045",
            account_name="锁定场次",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=locked.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        free_account = PlatformAccount(
            account_no="AC-PY-1045-FREE",
            account_name="自由场次",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=free.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add_all([locked_account, free_account])
        ops.commit()
        return locked_account.id, locked.id, free_account.id, free.id, phone.id
    finally:
        ops.close()


def payload(account_id: int, person_id: int, phone_id: int, topic: str) -> dict:
    return {
        "accountId": account_id,
        "realnamePersonId": person_id,
        "responsibleUserId": 1,
        "deviceAssetIds": [phone_id],
        "platform": "DOUYIN",
        "topic": topic,
        "planStartTime": "2026-10-08T20:00:00+08:00",
        "planEndTime": "2026-10-08T22:00:00+08:00",
    }


def register(auth: dict, body: dict):
    return client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=body,
    )


def upload(auth: dict, holder: str, days: int, number: str):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": number,
            "fileKey": "local/cert/live1045",
            "issueDate": "2020-01-01",
            "expireDate": (today + timedelta(days=days)).isoformat(),
        },
    )


def test_locked_cert_blocks_live_until_renewed():
    auth = headers()
    locked_account, locked_person, free_account, free_person, phone_id = seed_people()
    opened = register(auth, payload(locked_account, locked_person, phone_id, "先登记"))
    assert opened.json()["code"] == 0, opened.json()
    session_code = opened.json()["data"]["sessionCode"]
    assert opened.json()["data"]["sessionStatus"] == "APPROVED"

    pending = upload(auth, HOLDER, 0, "110101199003031045")
    assert pending.json()["code"] == 0, pending.json()
    pending_id = pending.json()["data"]["id"]
    blocked_pending = register(auth, payload(locked_account, locked_person, phone_id, "待审拦截"))
    assert blocked_pending.json()["code"] == 1045
    assert "未生效" in blocked_pending.json()["msg"]
    start_pending = client.put(f"/admin-api/ims/live/register/{session_code}/start", headers=auth)
    assert start_pending.json()["code"] == 1045

    approved = client.put(
        f"/admin-api/ims/cert/archive/{pending_id}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approved.json()["code"] == 0
    while_effective = register(auth, payload(locked_account, locked_person, phone_id, "生效可登记"))
    assert while_effective.json()["code"] == 0, while_effective.json()
    second_code = while_effective.json()["data"]["sessionCode"]

    scan = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    assert scan.json()["code"] == 0, scan.json()
    locked_start = client.put(f"/admin-api/ims/live/register/{session_code}/start", headers=auth)
    assert locked_start.json()["code"] == 1045
    assert "过期或锁定" in locked_start.json()["msg"]
    still = client.get(f"/admin-api/ims/live/register/{session_code}", headers=auth)
    assert still.json()["data"]["sessionStatus"] == "APPROVED"
    risk = client.post(f"/admin-api/ims/live/register/{session_code}/risk-check", headers=auth, json={})
    assert risk.json()["code"] == 1045
    blocked_register = register(auth, payload(locked_account, locked_person, phone_id, "锁定拦截"))
    assert blocked_register.json()["code"] == 1045

    free_ok = register(auth, payload(free_account, free_person, phone_id, "他人不受影响"))
    assert free_ok.json()["code"] == 0, free_ok.json()

    listed = client.get(
        "/admin-api/ims/cert/expire/list",
        headers=auth,
        params={"holderName": HOLDER, "pageNo": 1, "pageSize": 10},
    )
    logs = [row for row in listed.json()["data"]["list"] if row["holderName"] == HOLDER]
    assert logs and logs[0]["status"] == "EXPIRED_LOCKED"
    renewed = upload(auth, HOLDER, 400, "110101199003031400")
    assert renewed.json()["code"] == 0, renewed.json()
    new_id = renewed.json()["data"]["id"]
    assert client.put(
        f"/admin-api/ims/cert/archive/{new_id}/review",
        headers=auth,
        json={"action": "APPROVE"},
    ).json()["code"] == 0
    still_locked = client.put(f"/admin-api/ims/live/register/{second_code}/start", headers=auth)
    assert still_locked.json()["code"] == 1045
    done = client.put(
        f"/admin-api/ims/cert/expire/{logs[0]['id']}/renew",
        headers=auth,
        json={"newCertId": new_id, "remark": "换证"},
    )
    assert done.json()["code"] == 0, done.json()

    started = client.put(f"/admin-api/ims/live/register/{session_code}/start", headers=auth)
    assert started.json()["code"] == 0, started.json()
    after = client.get(f"/admin-api/ims/live/register/{session_code}", headers=auth)
    assert after.json()["data"]["sessionStatus"] == "LIVE"
    again = register(auth, payload(locked_account, locked_person, phone_id, "换证后可登记"))
    assert again.json()["code"] == 0, again.json()
