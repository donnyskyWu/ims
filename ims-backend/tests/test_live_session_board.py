"""BUG-030 · 场次列表统计卡随开播、下播变化，分页固定 20。"""

import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, Phone, PlatformAccount, Realname

BJ = timezone(timedelta(hours=8))
client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed() -> dict[str, int]:
    ops = ops_session()
    try:
        company = Company(company_name="统计卡公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="统计卡组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="统计卡实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001013601"),
            phone_enc=encrypt_text("13800003001"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600003001"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-BOARD",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no=f"AC-BOARD-{uuid.uuid4().hex[:6]}",
            account_name="统计卡场次号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        return {"account": account.id, "person": person.id, "phone": phone.id}
    finally:
        ops.close()


def stats(auth: dict) -> dict:
    res = client.get(
        "/admin-api/ims/live/sessions/list",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    body = res.json()
    assert body["code"] == 0, body
    assert body["data"]["pageSize"] == 20
    return body["data"]["stats"]


def test_board_follows_start_end_and_confirm():
    auth = headers()
    ids = seed()
    before = stats(auth)
    plan = (datetime.now(BJ) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": ids["account"],
            "realnamePersonId": ids["person"],
            "responsibleUserId": 1,
            "deviceAssetIds": [ids["phone"]],
            "platform": "DOUYIN",
            "topic": "统计卡专场",
            "planStartTime": plan,
            "planEndTime": "",
        },
    )
    assert created.json()["code"] == 0, created.json()
    code = created.json()["data"]["sessionCode"]
    opened = stats(auth)
    assert opened["todayPendingStart"] == before["todayPendingStart"] + 1

    started = client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth)
    assert started.json()["code"] == 0, started.json()
    living = stats(auth)
    assert living["liveCount"] == before["liveCount"] + 1
    assert living["todayPendingStart"] == before["todayPendingStart"]

    ended = client.put(f"/admin-api/ims/live/register/{code}/end", headers=auth)
    assert ended.json()["code"] == 0, ended.json()
    waiting = stats(auth)
    assert waiting["liveCount"] == before["liveCount"]
    assert waiting["entryDue24h"] == before["entryDue24h"] + 1

    actual_start = datetime.now(BJ).strftime("%Y-%m-%dT%H:00:00+08:00")
    actual_end = (datetime.now(BJ) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:00:00+08:00")
    submitted = client.post(
        f"/admin-api/ims/live/report/{code}",
        headers=auth,
        json={
            "actualStart": actual_start,
            "actualEnd": actual_end,
            "gmv": 80,
            "refundAmount": 0,
            "orderCount": 2,
            "viewerCount": 10,
            "peakOnline": 4,
            "newFans": 1,
            "adCost": 5,
        },
    )
    assert submitted.json()["code"] == 0, submitted.json()
    confirmed = client.put(f"/admin-api/ims/live/report/{code}/confirm", headers=auth)
    assert confirmed.json()["code"] == 0, confirmed.json()
    booked = stats(auth)
    assert booked["entryDue24h"] == before["entryDue24h"]
    assert booked["monthConfirmedGmv"] == round(before["monthConfirmedGmv"] + 80, 2)
