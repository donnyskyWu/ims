import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ["IMS_COLLECT_SCHEDULER"] = "0"

from fastapi.testclient import TestClient

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import CollectTask, CollectorAccountBind, Company, IpGroup, PlatformAccount, Realname

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account(*, platform: str = "DOUYIN", bound: bool = True, conn: str = "SUCCESS") -> int:
    ops = ops_session()
    try:
        company = Company(company_name="调度公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="调度组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="调度员",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800001111"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no=f"ACCT-SCH-{platform}",
            account_name="调度账号",
            platform_type=platform,
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            cookie_enc=encrypt_text("cookie-demo") if bound else "",
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.flush()
        if bound:
            ops.add(
                CollectorAccountBind(
                    oa_account_id=account.id,
                    collector_account_id=f"acc_{platform.lower()}_{account.id}",
                    bind_status="BOUND",
                    conn_status=conn,
                    tenant_id=0,
                )
            )
        ops.commit()
        return account.id
    finally:
        ops.close()


def create_task(auth: dict, account_id: int, *, platform: str = "DOUYIN", name: str = "调度桩任务") -> dict:
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": name,
            "platformType": platform,
            "accountId": account_id,
            "frequency": "HOURLY",
            "cron": "0 * * * *",
            "status": "ENABLED",
        },
    )
    assert created.status_code == 200
    assert created.json()["code"] == 0
    return created.json()["data"]


def test_task_page_shows_next_run_and_health():
    auth = headers()
    account_id = seed_account(bound=True)
    data = create_task(auth, account_id)
    assert data["nextRunAt"]
    assert data["healthLabel"] == "连接正常"
    assert data["status"] == "ENABLED"
    assert data["statusLabel"] == "启用"
    page = client.get("/admin-api/ims/collect/task/page", headers=auth, params={"taskName": "调度桩"})
    row = page.json()["data"]["list"][0]
    assert row["nextRunAt"] == data["nextRunAt"]
    assert row["healthLabel"] == "连接正常"


def test_stop_blocks_run_and_start_reschedules():
    auth = headers()
    account_id = seed_account(bound=True)
    task_id = create_task(auth, account_id)["id"]
    stopped = client.post(f"/admin-api/ims/collect/task/{task_id}/stop", headers=auth)
    assert stopped.json()["code"] == 0
    assert stopped.json()["data"]["status"] == "DISABLED"
    assert stopped.json()["data"]["statusLabel"] == "停用"
    assert not stopped.json()["data"]["nextRunAt"]
    assert stopped.json()["data"]["scheduleLabel"] == "已停止，暂无下次执行"
    blocked = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert blocked.json()["code"] == 1001
    started = client.post(f"/admin-api/ims/collect/task/{task_id}/start", headers=auth)
    assert started.json()["code"] == 0
    assert started.json()["data"]["status"] == "ENABLED"
    assert started.json()["data"]["nextRunAt"]
    assert started.json()["data"]["scheduleLabel"] == started.json()["data"]["nextRunAt"]
    again = client.post(f"/admin-api/ims/collect/task/{task_id}/start", headers=auth)
    assert again.json()["data"]["nextRunAt"] == started.json()["data"]["nextRunAt"]


def test_failed_run_retry_increments():
    auth = headers()
    account_id = seed_account(bound=False)
    data = create_task(auth, account_id, name="未绑定调度")
    assert data["healthLabel"] == "未绑定"
    task_id = data["id"]
    first = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert first.json()["code"] == 0
    assert first.json()["data"]["status"] == "FAILED"
    assert first.json()["data"]["retryCount"] == 0
    second = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert second.json()["data"]["status"] == "FAILED"
    assert second.json()["data"]["retryCount"] == 1
    log_id = second.json()["data"]["logId"]
    detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=auth).json()["data"]
    assert detail["retryCount"] == 1
    assert detail["retryable"] is True
    logs = client.get("/admin-api/ims/collect/log/page", headers=auth, params={"taskId": task_id}).json()["data"]["list"]
    assert logs[0]["retryCount"] == 1
    assert logs[1]["retryCount"] == 0


def test_platform_source_retry_uses_collect_log():
    auth = headers()
    account_id = seed_account(bound=False)
    data = create_task(auth, account_id, name="抖音源失败重试")
    ops = ops_session()
    try:
        task = ops.get(CollectTask, int(data["id"]))
        task.source = "DOUYIN_OPEN_API"
        ops.commit()
    finally:
        ops.close()
    first = client.post(f"/admin-api/ims/collect/task/{data['id']}/run", headers=auth)
    assert first.json()["code"] == 0
    assert first.json()["data"]["status"] == "FAILED"
    assert first.json()["data"]["retryCount"] == 0
    second = client.post(f"/admin-api/ims/collect/task/{data['id']}/run", headers=auth)
    assert second.json()["data"]["retryCount"] == 1


def test_local_tick_runs_due_stub_and_skips_platform_source():
    auth = headers()
    douyin_id = seed_account(platform="DOUYIN", bound=True)
    kuaishou_id = seed_account(platform="KUAISHOU", bound=False)
    stub = create_task(auth, douyin_id, platform="DOUYIN", name="本地桩到期")
    owned = create_task(auth, kuaishou_id, platform="KUAISHOU", name="快手平台源")
    ops = ops_session()
    try:
        for task_id in (int(stub["id"]), int(owned["id"])):
            task = ops.get(CollectTask, task_id)
            task.next_run_at = "2000-01-01 00:00:00"
        ops.commit()
        assert ops.get(CollectTask, int(owned["id"])).source == "KUAISHOU_OPEN_API"
    finally:
        ops.close()
    from app.collect import tick_local_tasks

    assert tick_local_tasks() == 1
    ops = ops_session()
    try:
        stub_row = ops.get(CollectTask, int(stub["id"]))
        owned_row = ops.get(CollectTask, int(owned["id"]))
        assert stub_row.next_run_at > "2000-01-01 00:00:00"
        assert stub_row.success_count >= 1
        assert owned_row.next_run_at == "2000-01-01 00:00:00"
        assert owned_row.success_count == 0
    finally:
        ops.close()
