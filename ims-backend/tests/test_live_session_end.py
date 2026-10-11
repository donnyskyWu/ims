"""BUG-036 · 确认下播：仅直播中可结束，R5/R7 限本人，R1/R4 可操作全部。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.acct_seed import _ensure_cloned_user
from app.core import SessionLocal
from app.crypto import encrypt_text
from app.main import app
from app.models import Todo, User
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, LiveRoom, Phone, PlatformAccount, Realname

BJ = timezone(timedelta(hours=8))
client = TestClient(app)


def headers(username: str = "admin") -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": username, "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def user_id(username: str) -> int:
    db = SessionLocal()
    try:
        row = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        assert row is not None
        return row.id
    finally:
        db.close()


def ensure_roles() -> None:
    db = SessionLocal()
    try:
        _ensure_cloned_user(
            db,
            username="live_r5",
            nickname="直播运营甲",
            mobile="13900003605",
            role_key="live:r5",
            role_name="直播运营",
        )
        _ensure_cloned_user(
            db,
            username="live_r7",
            nickname="主播甲",
            mobile="13900003607",
            role_key="live:r7",
            role_name="主播",
        )
        _ensure_cloned_user(
            db,
            username="live_r4",
            nickname="运营总监甲",
            mobile="13900003604",
            role_key="live:r4",
            role_name="运营总监",
        )
        db.commit()
    finally:
        db.close()


def seed() -> dict[str, int]:
    ops = ops_session()
    try:
        company = Company(company_name="下播公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="下播组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="下播实名人",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001013600"),
            phone_enc=encrypt_text("13800003600"),
            status="ENABLED",
            tenant_id=0,
        )
        phone = Phone(
            phone_enc=encrypt_text("13600003600"),
            phone_sha256=uuid.uuid4().hex,
            phone_code="PY-END",
            status="IN_USE",
            keeper_id=1,
            tenant_id=0,
        )
        ops.add_all([company, group, person, phone])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-END",
            account_name="下播场次号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        now = datetime.now(BJ)
        room = LiveRoom(
            tenant_id=0,
            author_id="end-1",
            nickname="下播主播",
            live_name="只读房间",
            live_id="live-end",
            status=3,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(minutes=5),
            viewer_count=10,
            deleted=0,
        )
        ops.add_all([account, room])
        ops.commit()
        return {"account": account.id, "person": person.id, "phone": phone.id, "room": room.id}
    finally:
        ops.close()


def register(auth: dict, ids: dict[str, int], owner: int, topic: str = "确认下播专场") -> str:
    body = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": ids["account"],
            "realnamePersonId": ids["person"],
            "responsibleUserId": owner,
            "deviceAssetIds": [ids["phone"]],
            "platform": "DOUYIN",
            "topic": topic,
            "planStartTime": "2026-10-20T20:00:00+08:00",
            "planEndTime": "2026-10-20T22:00:00+08:00",
            "footballRoomId": str(ids["room"]),
        },
    )
    assert body.json()["code"] == 0, body.json()
    return body.json()["data"]["sessionCode"]


def test_end_only_from_live_sets_clock_and_todo():
    auth = headers()
    ids = seed()
    code = register(auth, ids, 1)
    blocked = client.put(f"/admin-api/ims/live/register/{code}/end", headers=auth)
    assert blocked.json()["code"] == 1042

    started = client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth)
    assert started.json()["code"] == 0, started.json()
    live = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    assert live["sessionStatus"] == "LIVE"
    assert live["actualStart"]
    assert live["endAllowed"] is True

    synced = client.post(f"/admin-api/ims/live/sessions/{code}/football-sync", headers=auth, json={})
    assert synced.json()["code"] == 0, synced.json()
    assert synced.json()["data"]["footballRoomBasic"]["endTime"]
    still = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    assert still["sessionStatus"] == "LIVE"

    ended = client.put(f"/admin-api/ims/live/register/{code}/end", headers=auth)
    assert ended.json()["code"] == 0, ended.json()
    data = ended.json()["data"]
    assert data["sessionStatus"] == "ENDED"
    assert data["actualEnd"]
    assert data["durationMinutes"] is not None
    assert data["durationMinutes"] >= 0
    assert data["endAllowed"] is False

    again = client.put(f"/admin-api/ims/live/register/{code}/end", headers=auth)
    assert again.json()["code"] == 1042

    db = SessionLocal()
    try:
        todo = db.scalar(
            select(Todo).where(
                Todo.task_type == "live_report_entry",
                Todo.assignee_user_id == 1,
                Todo.status == "PENDING",
            )
        )
        assert todo is not None
        assert code in (todo.title or "")
        assert todo.deadline is not None
    finally:
        db.close()


def test_r5_and_r7_only_end_own_sessions_r4_ends_any():
    ensure_roles()
    auth = headers()
    ids = seed()
    admin_code = register(auth, ids, 1, "管理员场次")
    client.put(f"/admin-api/ims/live/register/{admin_code}/start", headers=auth)

    r5 = headers("live_r5")
    listing = client.get("/admin-api/ims/live/sessions/list", headers=r5, params={"sessionCode": admin_code})
    assert listing.json()["code"] == 0, listing.json()
    row = listing.json()["data"]["list"][0]
    assert row["sessionCode"] == admin_code
    assert row["endAllowed"] is False
    denied = client.put(f"/admin-api/ims/live/register/{admin_code}/end", headers=r5)
    assert denied.json()["code"] == 1008
    denied_start = client.put(f"/admin-api/ims/live/register/{admin_code}/start", headers=r5)
    assert denied_start.json()["code"] == 1008

    own = register(auth, ids, user_id("live_r5"), "运营本人场次")
    assert client.put(f"/admin-api/ims/live/register/{own}/start", headers=r5).json()["code"] == 0
    own_end = client.put(f"/admin-api/ims/live/register/{own}/end", headers=r5)
    assert own_end.json()["code"] == 0, own_end.json()
    assert own_end.json()["data"]["sessionStatus"] == "ENDED"

    host = register(auth, ids, user_id("live_r7"), "主播本人场次")
    r7 = headers("live_r7")
    assert client.put(f"/admin-api/ims/live/register/{host}/start", headers=r7).json()["code"] == 0
    assert client.put(f"/admin-api/ims/live/register/{admin_code}/end", headers=r7).json()["code"] == 1008
    assert client.put(f"/admin-api/ims/live/register/{host}/end", headers=r7).json()["code"] == 0

    r4 = headers("live_r4")
    fresh = register(auth, ids, 1, "总监代下播")
    assert client.put(f"/admin-api/ims/live/register/{fresh}/start", headers=auth).json()["code"] == 0
    director = client.put(f"/admin-api/ims/live/register/{fresh}/end", headers=r4)
    assert director.json()["code"] == 0, director.json()
    assert director.json()["data"]["sessionStatus"] == "ENDED"


def test_bind_room_on_sync_keeps_session_status():
    auth = headers()
    ids = seed()
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": ids["account"],
            "realnamePersonId": ids["person"],
            "responsibleUserId": 1,
            "deviceAssetIds": [ids["phone"]],
            "platform": "DOUYIN",
            "topic": "未绑定房间",
            "planStartTime": "2026-10-20T20:00:00+08:00",
            "planEndTime": "",
        },
    )
    assert created.json()["code"] == 0, created.json()
    code = created.json()["data"]["sessionCode"]
    missing = client.post(f"/admin-api/ims/live/sessions/{code}/football-sync", headers=auth, json={})
    assert missing.json()["code"] == 1041
    ghost = client.post(
        f"/admin-api/ims/live/sessions/{code}/football-sync",
        headers=auth,
        json={"footballRoomId": "RG2-ROOM-001"},
    )
    assert ghost.json()["code"] == 1051
    before = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    assert not before["footballRoomId"]
    assert before["footballSyncStatus"] in (None, "", "UNLINKED")
    bound = client.post(
        f"/admin-api/ims/live/sessions/{code}/football-sync",
        headers=auth,
        json={"footballRoomId": str(ids["room"])},
    )
    assert bound.json()["code"] == 0, bound.json()
    basic = bound.json()["data"]["footballRoomBasic"]
    assert basic["status"] == 3
    assert basic["endTime"]
    still = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    assert still["sessionStatus"] == "APPROVED"
    assert still["footballRoomId"] == str(ids["room"])


def test_r5_cannot_approve_supplement():
    ensure_roles()
    auth = headers()
    ids = seed()
    created = client.post(
        "/admin-api/ims/live/ledger/supplement",
        headers=auth,
        json={
            "sessionCreate": {
                "accountId": ids["account"],
                "realnamePersonId": ids["person"],
                "responsibleUserId": 1,
                "deviceAssetIds": [ids["phone"]],
                "platform": "DOUYIN",
                "topic": "补录待审批",
                "planStartTime": "2020-01-15T20:00:00+08:00",
                "planEndTime": "",
            },
            "sessionReport": {
                "actualStart": "2020-01-15T20:00:00+08:00",
                "actualEnd": "2020-01-15T22:00:00+08:00",
                "gmv": 20,
                "refundAmount": 0,
                "orderCount": 1,
                "viewerCount": 10,
                "peakOnline": 4,
                "newFans": 1,
                "adCost": 0,
            },
            "supplementReason": "历史漏登",
        },
    )
    assert created.json()["code"] == 0, created.json()
    supplement_id = created.json()["data"]["supplementId"]
    code = created.json()["data"]["sessionCode"]
    pending = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    assert pending["isSupplement"] is True
    assert pending["approverUserId"] is None
    denied = client.put(
        f"/admin-api/ims/live/ledger/supplement/{supplement_id}/approve",
        headers=headers("live_r5"),
        json={"approve": True, "comment": "运营不能批"},
    )
    assert denied.json()["code"] == 1008
    approved = client.put(
        f"/admin-api/ims/live/ledger/supplement/{supplement_id}/approve",
        headers=auth,
        json={"approve": True, "comment": "总监入库"},
    )
    assert approved.json()["code"] == 0, approved.json()
    landed = client.get(f"/admin-api/ims/live/sessions/{code}", headers=auth).json()["data"]
    assert landed["sessionStatus"] == "ENDED"
    assert landed["approverUserId"]


def _open_session(auth: dict, ids: dict[str, int], topic: str) -> str:
    created = client.post(
        "/admin-api/ims/live/register",
        headers={**auth, "clientToken": uuid.uuid4().hex},
        json={
            "accountId": ids["account"],
            "realnamePersonId": ids["person"],
            "responsibleUserId": 1,
            "deviceAssetIds": [ids["phone"]],
            "platform": "DOUYIN",
            "topic": topic,
            "planStartTime": "2026-10-20T20:00:00+08:00",
            "planEndTime": "",
        },
    )
    assert created.json()["code"] == 0, created.json()
    return created.json()["data"]["sessionCode"]


def test_stub_room_syncs_by_code_and_numeric_id():
    from app.live_fin_e2e_seed import STUB_ROOM_CODE, STUB_ROOM_ID, ensure_stub_live_room

    ensure_stub_live_room()
    auth = headers()
    ids = seed()
    by_code = _open_session(auth, ids, "桩房间号同步")
    synced = client.post(
        f"/admin-api/ims/live/sessions/{by_code}/football-sync",
        headers=auth,
        json={"footballRoomId": STUB_ROOM_CODE},
    )
    assert synced.json()["code"] == 0, synced.json()
    basic = synced.json()["data"]["footballRoomBasic"]
    assert basic["liveId"] == STUB_ROOM_CODE
    assert basic["roomId"] == str(STUB_ROOM_ID)
    assert basic["status"] == 2
    assert basic["liveName"] == "桩直播间"
    still = client.get(f"/admin-api/ims/live/sessions/{by_code}", headers=auth).json()["data"]
    assert still["sessionStatus"] == "APPROVED"
    assert still["footballRoomId"] == STUB_ROOM_CODE
    assert still["footballSyncStatus"] == "SYNCED"

    by_id = _open_session(auth, ids, "桩主键同步")
    synced_id = client.post(
        f"/admin-api/ims/live/sessions/{by_id}/football-sync",
        headers=auth,
        json={"footballRoomId": str(STUB_ROOM_ID)},
    )
    assert synced_id.json()["code"] == 0, synced_id.json()
    assert synced_id.json()["data"]["footballRoomBasic"]["roomId"] == str(STUB_ROOM_ID)
    kept = client.get(f"/admin-api/ims/live/sessions/{by_id}", headers=auth).json()["data"]
    assert kept["footballRoomId"] == str(STUB_ROOM_ID)
    assert kept["footballSyncStatus"] == "SYNCED"
    assert kept["sessionStatus"] == "APPROVED"
