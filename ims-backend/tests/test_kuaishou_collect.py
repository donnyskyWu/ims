import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ["IMS_COLLECT_SCHEDULER"] = "0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.collector_stub import KUAISHOU_FOLLOWER_COUNT, CollectorStub
from app.crypto import decrypt_text
from app.kuaishou_collect import tick_due
from app.main import app
from app.ops_db import ops_session
from app.ops_models import (
    CollectTask,
    Company,
    IpGroup,
    KuaishouFollowerDaily,
    KuaishouVideo,
    KuaishouVideoSnapshot,
    PlatformAccount,
)

client = TestClient(app)
SECRET = "ks-cookie-plain-should-not-leak"


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
        company = Company(company_name="快手采集公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="快手采集组", status="ENABLED", tenant_id=0)
        ops.add_all([company, group])
        ops.commit()
        return company.id, group.id
    finally:
        ops.close()


def create_account(auth: dict, company_id: int, group_id: int, platform_id: str, name: str) -> dict:
    resp = client.post(
        "/admin-api/ims/collect/kuaishou/account",
        headers=auth,
        json={
            "accountName": name,
            "companyId": company_id,
            "ipGroupId": group_id,
            "platformAccountId": platform_id,
            "cookie": SECRET,
            "authToken": "auth-secret",
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
    data = create_account(auth, company_id, group_id, "KS_OK_UNIT", "掩码号")
    account = data["account"]
    dumped = str(data)
    assert SECRET not in dumped
    assert "auth-secret" not in dumped
    assert account["credentialMask"].startswith("****")
    assert account["credentialRef"].startswith("cred_ks_")
    assert account["platformAccountId"] == "KS_OK_UNIT"
    assert data["task"]["nextRunAt"]
    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account["id"])
        assert row.cookie_enc
        assert SECRET not in row.cookie_enc
        plain = decrypt_text(row.cookie_enc)
        assert SECRET in plain
        assert row.credential_ref == account["credentialRef"]
    finally:
        ops.close()
    detail = client.get(f"/admin-api/ims/corp/account/{account['id']}", headers=auth)
    assert SECRET not in detail.text
    assert detail.json()["data"]["credentialMask"] == account["credentialMask"]


def test_collect_idempotent_and_scheduler():
    auth = headers()
    company_id, group_id = seed_master()
    data = create_account(auth, company_id, group_id, "KS_OK_RUN", "采集号")
    account_id = data["account"]["id"]
    bound = client.post(f"/admin-api/ims/collect/kuaishou/account/{account_id}/bind", headers=auth)
    assert bound.status_code == 200
    assert bound.json()["code"] == 0
    assert bound.json()["data"]["healthLabel"] == "连接正常"
    first = client.post(f"/admin-api/ims/collect/kuaishou/account/{account_id}/run", headers=auth)
    assert first.status_code == 200
    assert first.json()["code"] == 0
    assert first.json()["data"]["status"] == "SUCCESS"
    assert first.json()["data"]["statusLabel"] == "成功"
    assert first.json()["data"]["recordCount"] == 3
    assert first.json()["data"]["durationMs"] >= 0
    listed = client.get(
        "/admin-api/ims/collect/kuaishou/account/page", headers=auth, params={"pageNo": 1, "pageSize": 50}
    )
    row = next(item for item in listed.json()["data"]["list"] if item["id"] == account_id)
    by_video = {item["videoId"]: item for item in row["videoSnapshots"]}
    assert by_video["ksv-1001"]["playCount"] == 1200
    assert by_video["ksv-1001"]["likeCount"] == 30
    assert by_video["ksv-1001"]["commentCount"] == 4
    assert by_video["ksv-1001"]["shareCount"] == 1
    assert by_video["ksv-1001"]["statDate"]
    second = client.post(f"/admin-api/ims/collect/kuaishou/account/{account_id}/run", headers=auth)
    assert second.json()["data"]["status"] == "SUCCESS"
    ops = ops_session()
    try:
        videos = ops.scalar(select(func.count()).select_from(KuaishouVideo).where(KuaishouVideo.account_id == account_id))
        snaps = ops.scalar(
            select(func.count()).select_from(KuaishouVideoSnapshot).where(KuaishouVideoSnapshot.account_id == account_id)
        )
        assert videos == 2
        assert snaps == 2
        snap = ops.scalar(
            select(KuaishouVideoSnapshot).where(
                KuaishouVideoSnapshot.account_id == account_id,
                KuaishouVideoSnapshot.video_id == "ksv-1001",
                KuaishouVideoSnapshot.deleted == 0,
            )
        )
        assert snap.play_count == 1200
        assert snap.like_count == 30
        assert snap.comment_count == 4
        assert snap.share_count == 1
        daily = ops.scalars(select(KuaishouFollowerDaily).where(KuaishouFollowerDaily.account_id == account_id)).all()
        assert len(daily) == 1
        assert daily[0].follower_count == KUAISHOU_FOLLOWER_COUNT
        task = ops.scalar(select(CollectTask).where(CollectTask.account_id == account_id, CollectTask.deleted == 0))
        task.next_run_at = "2000-01-01 00:00:00"
        ops.commit()
        task_id = task.id
    finally:
        ops.close()
    assert tick_due() >= 1
    ops = ops_session()
    try:
        videos = ops.scalar(select(func.count()).select_from(KuaishouVideo).where(KuaishouVideo.account_id == account_id))
        assert videos == 2
        task = ops.get(CollectTask, task_id)
        assert task.next_run_at > "2000-01-01 00:00:00"
        assert task.success_count >= 3
    finally:
        ops.close()


def test_cookie_expired_and_engine_unavailable_are_not_http_500():
    auth = headers()
    company_id, group_id = seed_master()
    cookie_acc = create_account(auth, company_id, group_id, "KS_COOKIE_EXPIRED", "失效号")["account"]["id"]
    engine_acc = create_account(auth, company_id, group_id, "KS_ENGINE_DOWN", "引擎号")["account"]["id"]
    for account_id in (cookie_acc, engine_acc):
        bound = client.post(f"/admin-api/ims/collect/kuaishou/account/{account_id}/bind", headers=auth)
        assert bound.status_code == 200
        assert bound.json()["code"] == 0
    cookie_run = client.post(f"/admin-api/ims/collect/kuaishou/account/{cookie_acc}/run", headers=auth)
    assert cookie_run.status_code == 200
    assert cookie_run.json()["code"] == 0
    assert cookie_run.json()["data"]["status"] == "COOKIE_EXPIRED"
    assert cookie_run.json()["data"]["statusLabel"] == "Cookie 已失效"
    assert cookie_run.json()["data"]["recordCount"] == 0
    engine_run = client.post(f"/admin-api/ims/collect/kuaishou/account/{engine_acc}/run", headers=auth)
    assert engine_run.status_code == 200
    assert engine_run.json()["data"]["status"] == "ENGINE_UNAVAILABLE"
    assert engine_run.json()["data"]["statusLabel"] == "浏览器引擎不可用"
    probe = client.post(f"/admin-api/ims/collect/kuaishou/account/{cookie_acc}/probe", headers=auth)
    assert probe.status_code == 200
    assert probe.json()["data"]["healthLabel"] == "Cookie 已失效"
    logs = client.get("/admin-api/ims/collect/kuaishou/log/page", headers=auth)
    labels = [item["statusLabel"] for item in logs.json()["data"]["list"]]
    assert "Cookie 已失效" in labels
    assert "浏览器引擎不可用" in labels


def test_missing_collector_url_is_failed_not_500(monkeypatch):
    auth = headers()
    company_id, group_id = seed_master()
    account_id = create_account(auth, company_id, group_id, "KS_OK_OFFLINE", "离线号")["account"]["id"]
    client.post(f"/admin-api/ims/collect/kuaishou/account/{account_id}/bind", headers=auth)
    monkeypatch.delenv("IMS_COLLECTOR_BASE_URL", raising=False)
    run = client.post(f"/admin-api/ims/collect/kuaishou/account/{account_id}/run", headers=auth)
    assert run.status_code == 200
    assert run.json()["code"] == 0
    assert run.json()["data"]["status"] == "FAILED"
    assert "未配置 Collector" in (run.json()["data"]["errorSummary"] or "")
