"""#131 · VERIFY-R1 定时全量/增量，VERIFY-R2 逾期升级部门负责人。"""

import os
from datetime import datetime, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.main import app
from app.asset_verify import add_business_days, escalate_overdue, run_scheduled_verify, scheduled_scope
from app.core import SessionLocal, utcnow
from app.models import AssetLedger, AssetVerifyBatch, AssetVerifyError, Todo, User, UserDept, WorkMessage
from app.ops_db import ops_session
from app.ops_models import IpGroup
from app.security import hash_password

client = TestClient(app)

STALE = "AS-SCH-STALE"
FRESH = "AS-SCH-FRESH"
OWNED = "AS-R2-OWNED"
# 2026-10-12 00:30 上海 = 周一；2026-10-13 00:30 上海 = 周二
MONDAY = datetime(2026, 10, 11, 16, 30, 0)
TUESDAY = datetime(2026, 10, 12, 16, 30, 0)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _create(auth: dict, code: str) -> dict:
    return client.post(
        "/admin-api/ims/asset/ledger",
        headers=auth,
        json={"assetCode": code, "assetName": code, "assetType": "OFFICE"},
    ).json()


def _user(username: str, nickname: str) -> int:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        if user is None:
            user = User(
                username=username,
                nickname=nickname,
                mobile="13900013101" if username.endswith("owner") else "13900013102",
                password_hash=hash_password("Admin@123"),
                status="ENABLED",
                tenant_id=0,
                deleted=0,
            )
            db.add(user)
            db.flush()
        else:
            user.nickname = nickname
            user.status = "ENABLED"
        db.commit()
        return int(user.id)
    finally:
        db.close()


def test_monday_is_full_tuesday_is_increment_and_the_same_day_runs_once():
    assert scheduled_scope(MONDAY) == "FULL"
    assert scheduled_scope(TUESDAY) == "INCREMENT"
    assert add_business_days(datetime(2026, 10, 9, 2, 0, 0), 3) == datetime(2026, 10, 14, 15, 59, 59)
    assert add_business_days(datetime(2026, 10, 5, 1, 0, 0), 3) == datetime(2026, 10, 8, 15, 59, 59)

    auth = headers()
    stale = _create(auth, STALE)
    fresh = _create(auth, FRESH)
    assert stale["code"] == 0, stale
    assert fresh["code"] == 0, fresh
    db = SessionLocal()
    try:
        db.get(AssetLedger, stale["data"]["id"]).updated_at = datetime(2026, 9, 1, 0, 0, 0)
        db.get(AssetLedger, fresh["data"]["id"]).updated_at = TUESDAY
        db.commit()

        first = run_scheduled_verify(db, TUESDAY)
        db.commit()
        assert first == ["AVS20261013I0"]
        rows = list(db.scalars(select(AssetVerifyBatch).where(AssetVerifyBatch.schedule_date == "2026-10-13")).all())
        assert len(rows) == 3
        assert {row.scope for row in rows} == {"INCREMENT"}
        assert {row.trigger_mode for row in rows} == {"SCHEDULE"}
        person = next(row for row in rows if row.verify_type == "asset_person")
        codes = set(db.scalars(select(AssetVerifyError.asset_code).where(AssetVerifyError.batch_id == person.id)).all())
        assert FRESH in codes
        assert STALE not in codes

        again = run_scheduled_verify(db, TUESDAY)
        db.commit()
        assert again == first
        kept = db.scalar(
            select(func.count()).select_from(AssetVerifyBatch).where(AssetVerifyBatch.schedule_date == "2026-10-13")
        )
        assert kept == 3

        monday = run_scheduled_verify(db, MONDAY)
        db.commit()
        assert monday == ["AVS20261012F0"]
        full_rows = list(db.scalars(select(AssetVerifyBatch).where(AssetVerifyBatch.schedule_date == "2026-10-12")).all())
        assert {row.scope for row in full_rows} == {"FULL"}
        full_person = next(row for row in full_rows if row.verify_type == "asset_person")
        full_codes = set(
            db.scalars(select(AssetVerifyError.asset_code).where(AssetVerifyError.batch_id == full_person.id)).all()
        )
        assert STALE in full_codes
        assert FRESH in full_codes
        assert full_person.deadline_at == add_business_days(MONDAY, 3)
        assert full_person.task_status == "PENDING_DISPATCH"
    finally:
        db.close()


def test_overdue_verify_escalates_to_dept_leader_once_and_skips_closed():
    auth = headers()
    owner_id = _user("asset_r2_owner", "资产使用人")
    leader_id = _user("asset_r2_leader", "校验负责人")
    db = SessionLocal()
    try:
        db.execute(delete(UserDept).where(UserDept.user_id == owner_id))
        db.add(UserDept(user_id=owner_id, dept_id=73131, tenant_id=0))
        db.commit()
    finally:
        db.close()
    ops = ops_session()
    try:
        group = ops.scalar(select(IpGroup).where(IpGroup.group_name == "校验升级组", IpGroup.deleted == 0))
        if group is None:
            ops.add(
                IpGroup(
                    group_name="校验升级组",
                    status="ENABLED",
                    ding_dept_id=73131,
                    leader_user_id=leader_id,
                    tenant_id=0,
                )
            )
        else:
            group.ding_dept_id = 73131
            group.leader_user_id = leader_id
            group.status = "ENABLED"
        ops.commit()
    finally:
        ops.close()

    created = _create(auth, OWNED)
    assert created["code"] == 0, created
    checked = client.post(
        f"/admin-api/ims/asset/ledger/{created['data']['id']}/checkout",
        headers=auth,
        json={"ownerUserId": owner_id, "purpose": "办公领用"},
    ).json()
    assert checked["code"] == 0, checked
    ran = client.post(
        "/admin-api/ims/asset/verify/run",
        headers=auth,
        json={"verifyTypes": ["asset_person", "asset_account", "asset_session"], "scope": "FULL"},
    ).json()
    assert ran["code"] == 0, ran
    person = next(item for item in ran["data"]["batches"] if item["verifyType"] == "asset_person")
    account = next(item for item in ran["data"]["batches"] if item["verifyType"] == "asset_account")
    session = next(item for item in ran["data"]["batches"] if item["verifyType"] == "asset_session")
    assert person["taskStatus"] == "PENDING_DISPATCH"
    assert person["deadlineAt"]
    assert person["overdue"] is False

    db = SessionLocal()
    try:
        db.execute(
            delete(AssetVerifyError).where(
                AssetVerifyError.batch_id == person["id"],
                AssetVerifyError.asset_code != OWNED,
            )
        )
        row = db.get(AssetVerifyBatch, person["id"])
        row.deadline_at = utcnow() - timedelta(hours=1)
        closed = db.get(AssetVerifyBatch, session["id"])
        closed.task_status = "CLOSED"
        closed.deadline_at = utcnow() - timedelta(hours=2)
        db.commit()

        assert escalate_overdue(db) == 1
        db.commit()
        todos = list(
            db.scalars(
                select(Todo).where(Todo.task_type == "asset_verify_overdue", Todo.ref_id == person["id"])
            ).all()
        )
        assert len(todos) == 1
        assert todos[0].assignee_user_id == leader_id
        assert "资产校验逾期" in todos[0].title
        messages = list(
            db.scalars(
                select(WorkMessage).where(WorkMessage.source_module == "ASSET", WorkMessage.ref_id == person["id"])
            ).all()
        )
        assert {item.channel for item in messages} == {"IN_APP", "DINGTALK"}
        assert {item.user_id for item in messages} == {leader_id}
        stub = next(item for item in messages if item.channel == "DINGTALK")
        assert "钉钉未外发" in (stub.content or "")
        assert db.get(AssetVerifyBatch, person["id"]).escalate_user_id == leader_id
        assert db.get(AssetVerifyBatch, account["id"]).escalated_at is None
        assert db.get(AssetVerifyBatch, session["id"]).escalated_at is None

        assert escalate_overdue(db) == 0
        db.commit()
        again = db.scalar(
            select(func.count()).select_from(Todo).where(Todo.task_type == "asset_verify_overdue", Todo.ref_id == person["id"])
        )
        assert again == 1
    finally:
        db.close()

    listed = client.get(
        "/admin-api/ims/asset/verify/batches",
        headers=auth,
        params={"batchNo": person["batchNo"]},
    ).json()
    assert listed["code"] == 0, listed
    found = listed["data"]["list"][0]
    assert found["overdue"] is True
    assert found["escalateUserName"] == "校验负责人"
    assert "已升级" not in (found.get("remark") or "")
