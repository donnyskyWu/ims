import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ["IMS_COLLECT_SCHEDULER"] = "0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.collector_stub import CollectorStub
from app.crypto import decrypt_text, encrypt_text
from app.douyin_collect import tick_due
from app.main import app
from app.ops_db import ops_session
from app.ops_models import (
    CollectTask,
    CollectorAccountBind,
    Company,
    DouyinVideo,
    DouyinVideoSnapshot,
    IpGroup,
    PlatformAccount,
)

client = TestClient(app)
SECRET = "dy-cookie-plain-should-not-leak"


@pytest.fixture(autouse=True)
def collector_stub():
    stub = CollectorStub()
    stub.start()
    os.environ["IMS_COLLECTOR_BASE_URL"] = stub.base_url
    os.environ["IMS_COLLECTOR_TOKEN"] = "pytest-collector-token"
    yield stub
    stub.stop()


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_master() -> tuple[int, int]:
    ops = ops_session()
    try:
        company = Company(company_name="抖音采集公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="抖音采集组", status="ENABLED", tenant_id=0)
        ops.add_all([company, group])
        ops.commit()
        return company.id, group.id
    finally:
        ops.close()


def create_account(auth: dict, company_id: int, group_id: int, platform_id: str, name: str) -> dict:
    resp = client.post(
        "/admin-api/ims/collect/douyin/account",
        headers=auth,
        json={
            "accountName": name,
            "companyId": company_id,
            "ipGroupId": group_id,
            "platformAccountId": platform_id,
            "cookie": SECRET,
            "frequency": "DAILY",
            "cron": "0 2 * * *",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    return body["data"]


def test_credential_masked_and_not_stored_plain():
    auth = headers()
    company_id, group_id = seed_master()
    data = create_account(auth, company_id, group_id, "DY_OK_UNIT", "掩码号")
    account = data["account"]
    dumped = str(data)
    assert SECRET not in dumped
    assert account["credentialMask"].startswith("****")
    assert account["credentialRef"].startswith("cred_dy_")
    assert account["platformAccountId"] == "DY_OK_UNIT"
    assert data["task"]["nextRunAt"]
    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account["id"])
        assert row.cookie_enc
        assert SECRET not in row.cookie_enc
        plain = decrypt_text(row.cookie_enc)
        assert SECRET in plain
        task = ops.scalar(select(CollectTask).where(CollectTask.account_id == account["id"], CollectTask.deleted == 0))
        assert task.source == "DOUYIN_OPEN_API"
        assert task.data_type == "DOUYIN_VIDEO_LIST"
    finally:
        ops.close()
    detail = client.get(f"/admin-api/ims/corp/account/{account['id']}", headers=auth)
    assert SECRET not in detail.text
    assert detail.json()["data"]["credentialMask"] == account["credentialMask"]


def test_collect_idempotent_and_scheduler():
    auth = headers()
    company_id, group_id = seed_master()
    data = create_account(auth, company_id, group_id, "DY_OK_RUN", "采集号")
    account_id = data["account"]["id"]
    bound = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/bind", headers=auth)
    assert bound.status_code == 200
    assert bound.json()["code"] == 0
    assert bound.json()["data"]["healthLabel"] == "连接正常"
    assert bound.json()["data"]["collectorAccountId"].startswith("acc_douyin_")
    first = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/run", headers=auth)
    assert first.status_code == 200
    assert first.json()["code"] == 0
    assert first.json()["data"]["status"] == "SUCCESS"
    assert first.json()["data"]["statusLabel"] == "成功"
    assert first.json()["data"]["recordCount"] == 2
    second = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/run", headers=auth)
    assert second.json()["data"]["status"] == "SUCCESS"
    ops = ops_session()
    try:
        videos = ops.scalar(select(func.count()).select_from(DouyinVideo).where(DouyinVideo.account_id == account_id))
        snaps = ops.scalar(
            select(func.count()).select_from(DouyinVideoSnapshot).where(DouyinVideoSnapshot.account_id == account_id)
        )
        assert videos == 2
        assert snaps == 2
        titles = ops.scalars(select(DouyinVideo.title).where(DouyinVideo.account_id == account_id)).all()
        assert "抖音内部作品甲" in titles
        task = ops.scalar(
            select(CollectTask).where(
                CollectTask.account_id == account_id,
                CollectTask.deleted == 0,
                CollectTask.source == "DOUYIN_OPEN_API",
            )
        )
        task.next_run_at = "2000-01-01 00:00:00"
        ops.commit()
        task_id = task.id
    finally:
        ops.close()
    assert tick_due() >= 1
    ops = ops_session()
    try:
        videos = ops.scalar(select(func.count()).select_from(DouyinVideo).where(DouyinVideo.account_id == account_id))
        assert videos == 2
        task = ops.get(CollectTask, task_id)
        assert task.next_run_at > "2000-01-01 00:00:00"
        assert task.success_count >= 3
    finally:
        ops.close()


def test_cookie_expired_and_engine_unavailable_are_not_http_500():
    auth = headers()
    company_id, group_id = seed_master()
    cookie_acc = create_account(auth, company_id, group_id, "DY_COOKIE_EXPIRED", "失效号")["account"]["id"]
    engine_acc = create_account(auth, company_id, group_id, "DY_ENGINE_DOWN", "引擎号")["account"]["id"]
    for account_id in (cookie_acc, engine_acc):
        bound = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/bind", headers=auth)
        assert bound.status_code == 200
        assert bound.json()["code"] == 0
    cookie_run = client.post(f"/admin-api/ims/collect/douyin/account/{cookie_acc}/run", headers=auth)
    assert cookie_run.status_code == 200
    assert cookie_run.json()["code"] == 0
    assert cookie_run.json()["data"]["status"] == "COOKIE_EXPIRED"
    assert cookie_run.json()["data"]["statusLabel"] == "Cookie 已失效"
    assert cookie_run.json()["data"]["recordCount"] == 0
    engine_run = client.post(f"/admin-api/ims/collect/douyin/account/{engine_acc}/run", headers=auth)
    assert engine_run.status_code == 200
    assert engine_run.json()["data"]["status"] == "ENGINE_UNAVAILABLE"
    assert engine_run.json()["data"]["statusLabel"] == "浏览器引擎不可用"
    probe = client.post(f"/admin-api/ims/collect/douyin/account/{cookie_acc}/probe", headers=auth)
    assert probe.status_code == 200
    assert probe.json()["data"]["healthLabel"] == "Cookie 已失效"
    logs = client.get("/admin-api/ims/collect/douyin/log/page", headers=auth, params={"accountId": cookie_acc})
    labels = [item["statusLabel"] for item in logs.json()["data"]["list"]]
    assert labels == ["Cookie 已失效"]


def test_legacy_douyin_task_run_stays_simulated():
    """任务页创建的抖音任务、外部统一任务仍走模拟运行，不打 Collector。"""
    auth = headers()
    ops = ops_session()
    try:
        company = Company(company_name="模拟公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="模拟组", status="ENABLED", tenant_id=0)
        ops.add_all([company, group])
        ops.flush()
        account = PlatformAccount(
            account_name="模拟抖音号",
            platform_type="DOUYIN",
            platform_account_id="DY_LEGACY",
            company_id=company.id,
            ip_group_id=group.id,
            cookie_enc=encrypt_text("cookie-demo"),
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.flush()
        ops.add(
            CollectorAccountBind(
                oa_account_id=account.id,
                collector_account_id=f"acc_douyin_{account.id}",
                bind_status="BOUND",
                conn_status="SUCCESS",
                tenant_id=0,
            )
        )
        ops.commit()
        account_id = account.id
    finally:
        ops.close()
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "模拟抖音作品",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 2 * * *",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    task_id = created.json()["data"]["id"]
    ops = ops_session()
    try:
        stored = ops.get(CollectTask, int(task_id))
        assert stored.source == "API"
        assert stored.data_type in (None, "")
    finally:
        ops.close()
    run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert run.status_code == 200
    assert run.json()["code"] == 0
    assert run.json()["data"]["status"] == "SUCCESS"
    log_id = run.json()["data"]["logId"]
    detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=auth).json()["data"]
    assert detail["recordCount"] == 6
    types = {item["dataType"] for item in detail["typeResults"]}
    assert "VIDEO" in types
    assert "FAN" in types
    ops = ops_session()
    try:
        videos = ops.scalar(select(func.count()).select_from(DouyinVideo).where(DouyinVideo.account_id == account_id))
        assert videos in (None, 0)
    finally:
        ops.close()
