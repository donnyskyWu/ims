import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.crypto import encrypt_text
from app.main import app, init_db
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import CollectConfig, CollectorAccountBind, Company, IpGroup, PlatformAccount, Realname

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account(*, bound: bool = True) -> int:
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
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no="ACCT-CL-001",
            account_name="神鱼体育",
            platform_type="DOUYIN",
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
                    collector_account_id=f"acc_douyin_{account.id}",
                    bind_status="BOUND",
                    conn_status="SUCCESS",
                    tenant_id=0,
                )
            )
        ops.commit()
        return account.id
    finally:
        ops.close()


def seed_external_config() -> int:
    ops = ops_session()
    try:
        cfg = CollectConfig(
            config_name="快手竞品 A",
            platform_type="KUAISHOU",
            scope="EXTERNAL",
            account_identifier="ks_user_1",
            status="ENABLED",
            tenant_id=0,
        )
        ops.add(cfg)
        ops.commit()
        return cfg.id
    finally:
        ops.close()


def test_create_single_account_task_run_and_log():
    auth = headers()
    account_id = seed_account(bound=True)
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "神鱼体育 · 作品",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "HOURLY",
            "cron": "0 */6 * * *",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    task_id = created.json()["data"]["id"]
    page = client.get(
        "/admin-api/ims/collect/task/page",
        headers=auth,
        params={"taskName": "神鱼", "platformType": "DOUYIN", "frequency": "HOURLY"},
    )
    assert page.json()["data"]["total"] == 1
    run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert run.json()["code"] == 0
    log_id = run.json()["data"]["logId"]
    detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=auth)
    body = detail.json()["data"]
    assert isinstance(body["typeResults"], list)
    assert len(body["typeResults"]) >= 1
    logs = client.get("/admin-api/ims/collect/log/page", headers=auth, params={"taskId": task_id})
    assert logs.json()["data"]["total"] >= 1


def test_unbound_account_warning_and_failed_run():
    auth = headers()
    account_id = seed_account(bound=False)
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "未绑定任务",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 2 * * *",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    assert "bindWarning" in created.json()["data"]
    task_id = created.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    log_id = run.json()["data"]["logId"]
    detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=auth).json()["data"]
    assert detail["status"] == "FAILED"
    assert detail["repairAccountId"] == str(account_id)
    assert "未绑定" in (detail["errorSummary"] or "")


def test_channel_d_external_task():
    auth = headers()
    config_id = seed_external_config()
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "竞品采集",
            "platformType": "KUAISHOU",
            "collectConfigId": config_id,
            "method": "EXTERNAL",
            "frequency": "DAILY",
            "cron": "0 3 * * *",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    data = created.json()["data"]
    assert data["accountId"] is None
    assert data["collectConfigId"] == str(config_id)


def test_ensure_unified_members():
    auth = headers()
    seed_account(bound=True)
    resp = client.post("/admin-api/ims/collect/task/ensure-unified", headers=auth, json={"platformType": "DOUYIN"})
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["isUnified"] is True
    assert (resp.json()["data"]["memberCount"] or 0) >= 1


def test_quality_summary_and_manual_fill():
    auth = headers()
    account_id = seed_account(bound=True)
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "质量补录任务",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 4 * * *",
            "status": "ENABLED",
        },
    )
    task_id = created.json()["data"]["id"]
    client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)

    summary = client.get("/admin-api/ims/collect/quality/summary", headers=auth)
    assert summary.json()["code"] == 0
    assert "successRate24h" in summary.json()["data"]
    assert isinstance(summary.json()["data"]["consecutiveFailureTop"], list)

    fill = client.post(
        "/admin-api/ims/collect/manual-fill",
        headers=auth,
        json={"taskId": int(task_id), "recordCount": 3, "remark": "补录昨日缺失"},
    )
    assert fill.json()["code"] == 0
    log_id = fill.json()["data"]["logId"]
    detail = client.get(f"/admin-api/ims/collect/log/{log_id}", headers=auth).json()["data"]
    assert detail["status"] == "SUCCESS"
    assert detail["typeResults"][0]["source"] == "MANUAL_FILL"
    assert detail["recordCount"] == 3
