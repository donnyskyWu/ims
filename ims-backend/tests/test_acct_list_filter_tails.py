"""#217 · 账号列表按 IP 组 id 过滤，归还单按离职人与生效日区间过滤。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_USE_CLOUD_DB", None)
os.environ.pop("IMS_DATABASE_URL", None)
os.environ["IMS_MYSQL_HOST"] = "127.0.0.1"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import User
from app.ops_db import ops_session
from app.ops_models import IpGroup, PlatformAccount
from app.security import hash_password

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _user(username: str) -> int:
    db = SessionLocal()
    try:
        row = db.scalar(select(User).where(User.username == username, User.deleted == 0))
        if row is None:
            row = User(
                username=username,
                nickname=username,
                mobile="1390000" + str(abs(hash(username)) % 10000).zfill(4),
                password_hash=hash_password("Admin@123"),
                status="ENABLED",
                tenant_id=0,
                deleted=0,
            )
            db.add(row)
            db.commit()
        return int(row.id)
    finally:
        db.close()


def test_account_page_filters_whole_list_by_ip_group():
    auth = headers()
    stamp = uuid.uuid4().hex[:8]
    ops = ops_session()
    try:
        group_a = IpGroup(group_name=f"G217-A-{stamp}", status="ENABLED", tenant_id=0)
        group_b = IpGroup(group_name=f"G217-B-{stamp}", status="ENABLED", tenant_id=0)
        ops.add_all([group_a, group_b])
        ops.flush()
        kept = PlatformAccount(
            account_no=f"AC-217-A-{stamp}",
            account_name="组A",
            platform_type="DOUYIN",
            ip_group_id=group_a.id,
            status="IN_POOL",
            tenant_id=0,
        )
        other = PlatformAccount(
            account_no=f"AC-217-B-{stamp}",
            account_name="组B",
            platform_type="DOUYIN",
            ip_group_id=group_b.id,
            status="IN_POOL",
            tenant_id=0,
        )
        ops.add_all([kept, other])
        ops.commit()
        group_a_id = int(group_a.id)
    finally:
        ops.close()

    listed = client.get(
        "/admin-api/ims/corp/account/page",
        headers=auth,
        params={"platformType": "DOUYIN", "ipGroupId": group_a_id, "pageNo": 1, "pageSize": 50},
    ).json()
    assert listed["code"] == 0, listed
    nos = [row["accountNo"] for row in listed["data"]["list"]]
    assert f"AC-217-A-{stamp}" in nos
    assert f"AC-217-B-{stamp}" not in nos
    assert listed["data"]["total"] == len(nos)


def test_return_list_filters_by_user_and_resign_range():
    auth = headers()
    stamp = uuid.uuid4().hex[:8]
    early_id = _user(f"resign_early_{stamp}")
    late_id = _user(f"resign_late_{stamp}")
    early = client.post(
        "/admin-api/ims/account/return/generate",
        headers=auth,
        json={"userId": early_id, "dingtalkResignDate": "2024-03-01", "manual": True},
    ).json()
    late = client.post(
        "/admin-api/ims/account/return/generate",
        headers=auth,
        json={"userId": late_id, "dingtalkResignDate": "2024-06-15", "manual": True},
    ).json()
    assert early["code"] == 0, early
    assert late["code"] == 0, late

    by_user = client.get("/admin-api/ims/account/return/list", headers=auth, params={"userId": early_id}).json()
    assert by_user["code"] == 0, by_user
    assert by_user["data"]["total"] == 1
    assert by_user["data"]["list"][0]["returnNo"] == early["data"]["returnNo"]
    assert by_user["data"]["list"][0]["resignDate"] == "2024-03-01"

    june = client.get(
        "/admin-api/ims/account/return/list",
        headers=auth,
        params={"timeFrom": "2024-06-01", "timeTo": "2024-06-30", "userId": late_id},
    ).json()
    assert june["code"] == 0, june
    assert [row["returnNo"] for row in june["data"]["list"]] == [late["data"]["returnNo"]]

    missed = client.get(
        "/admin-api/ims/account/return/list",
        headers=auth,
        params={"timeFrom": "2024-06-01", "timeTo": "2024-06-30", "userId": early_id},
    ).json()
    assert missed["code"] == 0, missed
    assert missed["data"]["total"] == 0
    assert missed["data"]["list"] == []
