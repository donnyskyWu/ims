import json
import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ["IMS_COLLECT_SCHEDULER"] = "0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.collector_stub import DOUYIN_FOLLOWER_COUNT, CollectorStub
from app.crypto import decrypt_text, encrypt_text
from app.douyin_collect import tick_due
from app.main import app
from app.ops_db import ops_session
from app.ops_models import (
    CollectLog,
    CollectTask,
    CollectorAccountBind,
    Company,
    DouyinFollower,
    DouyinFollowerDaily,
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
    assert first.json()["data"]["recordCount"] == 5
    assert first.json()["data"]["errorSummary"] in (None, "")
    listed = client.get(
        "/admin-api/ims/collect/douyin/account/page", headers=auth, params={"pageNo": 1, "pageSize": 50}
    )
    row = next(item for item in listed.json()["data"]["list"] if item["id"] == account_id)
    by_video = {item["videoId"]: item for item in row["videoSnapshots"]}
    assert by_video["dyv-2001"]["playCount"] == 2100
    assert by_video["dyv-2001"]["likeCount"] == 40
    assert by_video["dyv-2001"]["commentCount"] == 6
    assert by_video["dyv-2001"]["shareCount"] == 2
    assert by_video["dyv-2001"]["statDate"]
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
        snap = ops.scalar(
            select(DouyinVideoSnapshot).where(
                DouyinVideoSnapshot.account_id == account_id,
                DouyinVideoSnapshot.video_id == "dyv-2001",
                DouyinVideoSnapshot.deleted == 0,
            )
        )
        assert snap.play_count == 2100
        assert snap.like_count == 40
        assert snap.comment_count == 6
        assert snap.share_count == 2
        fans = ops.scalar(select(func.count()).select_from(DouyinFollower).where(DouyinFollower.account_id == account_id))
        daily = ops.scalars(select(DouyinFollowerDaily).where(DouyinFollowerDaily.account_id == account_id)).all()
        assert fans == 2
        assert len(daily) == 1
        assert daily[0].follower_count == DOUYIN_FOLLOWER_COUNT
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
        daily = ops.scalar(
            select(func.count()).select_from(DouyinFollowerDaily).where(DouyinFollowerDaily.account_id == account_id)
        )
        assert videos == 2
        assert daily == 1
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
    ops = ops_session()
    try:
        daily = ops.scalar(
            select(func.count()).select_from(DouyinFollowerDaily).where(DouyinFollowerDaily.account_id == cookie_acc)
        )
        videos = ops.scalar(select(func.count()).select_from(DouyinVideo).where(DouyinVideo.account_id == cookie_acc))
        assert daily == 0
        assert videos == 0
    finally:
        ops.close()
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


def test_follower_fail_keeps_videos_and_skips_daily():
    auth = headers()
    company_id, group_id = seed_master()
    account_id = create_account(auth, company_id, group_id, "DY_FOLLOWER_FAIL", "粉丝失败号")["account"]["id"]
    bound = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/bind", headers=auth)
    assert bound.json()["code"] == 0
    run = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/run", headers=auth)
    assert run.status_code == 200
    body = run.json()["data"]
    assert body["status"] == "PARTIAL"
    assert body["statusLabel"] == "部分成功"
    assert body["recordCount"] == 2
    assert "粉丝统计失败" in (body["errorSummary"] or "")
    ops = ops_session()
    try:
        videos = ops.scalar(select(func.count()).select_from(DouyinVideo).where(DouyinVideo.account_id == account_id))
        daily = ops.scalar(
            select(func.count()).select_from(DouyinFollowerDaily).where(DouyinFollowerDaily.account_id == account_id)
        )
        fans = ops.scalar(select(func.count()).select_from(DouyinFollower).where(DouyinFollower.account_id == account_id))
        assert videos == 2
        assert daily == 0
        assert fans == 0
        log = ops.scalar(select(CollectLog).where(CollectLog.account_id == account_id))
        types = {item["dataType"]: item["status"] for item in json.loads(log.type_results_json)}
        assert types["FOLLOWER_STATS"] == "FAILED"
        assert types["DOUYIN_FOLLOWER_LIST"] == "FAILED"
        assert types["DOUYIN_VIDEO_LIST"] == "SUCCESS"
    finally:
        ops.close()
    page = client.get("/admin-api/ims/collect/douyin/account/page", headers=auth)
    row = next(item for item in page.json()["data"]["list"] if item["id"] == account_id)
    assert row["followerCount"] is None


def test_stub_serves_real_douyin_paths(collector_stub):
    import httpx

    account = "acc_douyin_DY_OK"
    headers_ = {"Authorization": "Bearer pytest-collector-token"}
    videos = httpx.get(
        f"{collector_stub.base_url}/api/v1/internal/douyin/accounts/{account}/videos",
        headers=headers_,
    )
    assert videos.status_code == 200
    assert len(videos.json()["data"]["videos"]) == 2
    fans = httpx.get(
        f"{collector_stub.base_url}/api/v1/internal/douyin/accounts/{account}/followers",
        headers=headers_,
    )
    assert len(fans.json()["data"]["followers"]) == 2
    stats = httpx.get(
        f"{collector_stub.base_url}/api/v1/internal/douyin/follower-stats",
        headers=headers_,
        params={"account_id": account},
    )
    assert stats.json()["data"]["follower_count"] == DOUYIN_FOLLOWER_COUNT
    old = httpx.post(
        f"{collector_stub.base_url}/api/v1/internal/douyin/videos",
        headers=headers_,
        json={"user_id": account, "cookie": "x"},
    )
    assert old.status_code == 404


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


def test_douyin_probe_empty_and_credential_clear_stay_stub_safe():
    auth = headers()
    company_id, group_id = seed_master()
    account_id = create_account(auth, company_id, group_id, "DY_PROBE_EMPTY", "探活空态")["account"]["id"]
    rotated = "dy-cookie-rotated-should-not-leak"

    probe = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/probe", headers=auth)
    assert probe.status_code == 200
    body = probe.json()
    assert body["code"] == 0
    assert body["data"]["healthLabel"] == "未绑定"
    assert body["data"]["lastProbeAt"] == ""
    assert "请先导入" in body["data"]["notice"]
    assert SECRET not in probe.text

    tab = client.post(f"/admin-api/ims/corp/account/{account_id}/collector-bind/test-connection", headers=auth)
    assert tab.status_code == 200
    assert tab.json()["code"] == 0
    assert tab.json()["data"]["healthLabel"] == "未绑定"
    assert "请先导入" in tab.json()["data"]["notice"]

    bound = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/bind", headers=auth)
    assert bound.json()["code"] == 0
    assert bound.json()["data"]["healthLabel"] == "连接正常"
    assert bound.json()["data"]["lastProbeAt"]

    updated = client.put(
        f"/admin-api/ims/collect/douyin/account/{account_id}",
        headers=auth,
        json={"cookie": rotated},
    )
    assert updated.json()["code"] == 0
    account = updated.json()["data"]["account"]
    assert account["healthLabel"] == "未探活"
    assert account["lastProbeAt"] == ""
    assert account["credentialMask"].startswith("****")
    assert rotated not in updated.text

    reprobe = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/probe", headers=auth)
    assert reprobe.json()["data"]["healthLabel"] == "连接正常"
    assert reprobe.json()["data"]["lastProbeAt"]

    cleared = client.put(
        f"/admin-api/ims/collect/douyin/account/{account_id}",
        headers=auth,
        json={"clearCredential": True},
    )
    assert cleared.json()["code"] == 0
    cleared_account = cleared.json()["data"]["account"]
    assert cleared_account["healthLabel"] == "未探活"
    assert cleared_account["hasCredential"] is False
    assert cleared_account["credentialMask"] == ""
    assert cleared_account["credentialRef"].startswith("cred_dy_")
    assert SECRET not in cleared.text
    assert rotated not in cleared.text

    empty_probe = client.post(f"/admin-api/ims/collect/douyin/account/{account_id}/probe", headers=auth)
    assert empty_probe.json()["code"] == 0
    assert empty_probe.json()["data"]["healthLabel"] == "未探活"
    assert "凭证未配置" in empty_probe.json()["data"]["notice"]

    ops = ops_session()
    try:
        row = ops.get(PlatformAccount, account_id)
        assert row is not None
        assert not row.cookie_enc
        bind = ops.scalar(
            select(CollectorAccountBind).where(
                CollectorAccountBind.oa_account_id == account_id,
                CollectorAccountBind.deleted == 0,
            )
        )
        assert bind is not None
        assert bind.bind_status == "BOUND"
        assert bind.conn_status == ""
        assert bind.last_probe_at == ""
    finally:
        ops.close()
