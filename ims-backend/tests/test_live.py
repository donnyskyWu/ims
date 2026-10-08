import os
import re
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.crypto import encrypt_text
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import Company, IpGroup, LiveRoom, Phone, PlatformAccount, Realname

BJ = timezone(timedelta(hours=8))



client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_live_deps() -> tuple[int, int, int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="甲公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="小球 IP", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="张三",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800001111"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600004444"),
            phone_sha256="x",
            phone_type="iPhone",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no="ACCT-2026-0001",
            account_name="神鱼体育",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.flush()
        now = datetime.now(BJ)
        room = LiveRoom(
            tenant_id=0,
            author_id="1001",
            nickname="主播甲",
            live_name="测试直播间",
            live_id="live-001",
            status=3,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            viewer_count=8800,
            like_count=1200,
            reservation_count=300,
            deleted=0,
        )
        ops.add(room)
        ops.commit()
        return account.id, person.id, phone.id, room.id
    finally:
        ops.close()


def register_payload(account_id: int, person_id: int, phone_id: int, room_id: int | None = None) -> dict:
    body = {
        "accountId": account_id,
        "realnamePersonId": person_id,
        "responsibleUserId": 1,
        "deviceAssetIds": [phone_id],
        "platform": "DOUYIN",
        "topic": "pytest 直播专场",
        "planStartTime": "2026-10-06T20:00:00+08:00",
        "planEndTime": "2026-10-06T22:00:00+08:00",
    }
    if room_id is not None:
        body["footballRoomId"] = str(room_id)
    return body


def test_register_session_id_and_metrics_from_live_room():
    auth = headers()
    account_id, person_id, phone_id, room_id = seed_live_deps()
    token = uuid.uuid4().hex
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": token},
        json=register_payload(account_id, person_id, phone_id, room_id),
    )
    assert reg.json()["code"] == 0
    code = reg.json()["data"]["sessionCode"]
    assert re.match(r"^IMS\d{8}DYS\d{4}$", code)

    dup = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": token},
        json=register_payload(account_id, person_id, phone_id, room_id),
    )
    assert dup.json()["data"]["sessionCode"] == code

    metrics = client.get(f"/admin-api/ims/live/sessions/{code}/metrics", headers=auth)
    assert metrics.json()["code"] == 0
    data = metrics.json()["data"]
    assert data["syncStatus"] in ("PENDING", "UNLINKED", "SYNCED")
    basic = data.get("footballRoomBasic")
    assert basic is not None
    assert basic["sourceTable"] == "live_room"
    assert basic["viewerCount"] == 8800
    assert data["metricsByManualEntry"]["gmv"] is True

    sync = client.post(f"/admin-api/ims/live/sessions/{code}/football-sync", headers=auth, json={})
    assert sync.json()["code"] == 0
    assert sync.json()["data"]["syncStatus"] == "SYNCED"
    assert sync.json()["data"]["footballRoomBasic"]["liveName"] == "测试直播间"

    listing = client.get("/admin-api/ims/live/sessions/list", headers=auth)
    assert listing.json()["data"]["total"] >= 1
    assert listing.json()["data"]["list"][0]["sessionCode"] == code


def test_metrics_unlinked_without_room():
    auth = headers()
    account_id, person_id, phone_id, _room_id = seed_live_deps()
    reg = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json=register_payload(account_id, person_id, phone_id, None),
    )
    code = reg.json()["data"]["sessionCode"]
    metrics = client.get(f"/admin-api/ims/live/sessions/{code}/metrics", headers=auth)
    assert metrics.json()["data"]["syncStatus"] == "UNLINKED"
    assert metrics.json()["data"]["footballRoomBasic"] is None
