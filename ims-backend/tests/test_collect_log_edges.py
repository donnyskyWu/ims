import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import utcnow
from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import CollectLog, CollectorAccountBind, Company, IpGroup, PlatformAccount, Realname

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account(*, bound: bool) -> int:
    ops = ops_session()
    try:
        company = Company(company_name="日志边角公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="日志边角组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="日志边角",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011234"),
            phone_enc=encrypt_text("13800001111"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no="ACCT-LOG-EDGE",
            account_name="日志边角号",
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


def test_log_empty_copy_for_cookie_engine_and_inverted_dates():
    auth = headers()
    empty = client.get("/admin-api/ims/collect/log/page", headers=auth)
    assert empty.json()["code"] == 0
    assert empty.json()["data"]["total"] == 0
    assert empty.json()["data"]["emptyTitle"] == "暂无日志"
    assert "本地定时器" in empty.json()["data"]["emptyHint"]
    assert "Cookie" in empty.json()["data"]["emptyHint"]

    cookie = client.get("/admin-api/ims/collect/log/page", headers=auth, params={"status": "COOKIE_EXPIRED"})
    assert cookie.json()["data"]["total"] == 0
    assert cookie.json()["data"]["emptyTitle"] == "没有 Cookie 已失效的日志"
    assert "本地 Collector" in cookie.json()["data"]["emptyHint"]
    assert "账号采集 Tab" in cookie.json()["data"]["emptyHint"]

    engine = client.get("/admin-api/ims/collect/log/page", headers=auth, params={"status": "ENGINE_UNAVAILABLE"})
    assert engine.json()["data"]["emptyTitle"] == "没有浏览器引擎不可用的日志"
    assert "真实浏览器" in engine.json()["data"]["emptyHint"]

    inverted = client.get(
        "/admin-api/ims/collect/log/page",
        headers=auth,
        params={"dateFrom": "2099-02-02", "dateTo": "2099-01-01"},
    )
    assert inverted.json()["data"]["total"] == 0
    assert inverted.json()["data"]["emptyTitle"] == "没有符合筛选的日志"
    assert "开始日期晚于结束日期" in inverted.json()["data"]["emptyHint"]

    summary = client.get("/admin-api/ims/collect/quality/summary", headers=auth)
    body = summary.json()["data"]
    assert body["successRate24h"] is None
    assert "本地调度" in body["healthEmptyNote"]
    assert body["consecutiveFailureAccountCount"] == 0
    assert "Cookie 失效" in body["failureEmptyNote"]
    assert "浏览器引擎不可用" in body["failureEmptyNote"]


def test_cookie_engine_notes_count_as_failures_and_manual_fill_stays_local():
    auth = headers()
    account_id = seed_account(bound=False)
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "日志边角任务",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 4 * * *",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    task_id = int(created.json()["data"]["id"])
    run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    unbound_id = run.json()["data"]["logId"]
    unbound = client.get(f"/admin-api/ims/collect/log/{unbound_id}", headers=auth).json()["data"]
    assert unbound["status"] == "FAILED"
    assert "未绑定" in (unbound["localNote"] or "")
    assert "账号采集 Tab" in unbound["localNote"]
    assert unbound["repairAccountId"] == str(account_id)

    started = utcnow().strftime("%Y-%m-%d %H:%M:%S")
    ops = ops_session()
    try:
        cookie = CollectLog(
            task_id=task_id,
            account_id=account_id,
            status="COOKIE_EXPIRED",
            started_at=started,
            duration_ms=10,
            record_count=0,
            retry_count=0,
            error_summary="Cookie 已失效",
            type_results_json="[]",
            tenant_id=0,
        )
        engine = CollectLog(
            task_id=task_id,
            account_id=account_id,
            status="ENGINE_UNAVAILABLE",
            started_at=started,
            duration_ms=10,
            record_count=0,
            retry_count=0,
            error_summary="浏览器引擎不可用",
            type_results_json="[]",
            tenant_id=0,
        )
        ops.add_all([cookie, engine])
        ops.commit()
        cookie_id = cookie.id
        engine_id = engine.id
    finally:
        ops.close()

    cookie_detail = client.get(f"/admin-api/ims/collect/log/{cookie_id}", headers=auth).json()["data"]
    assert "未连接真实平台" in cookie_detail["localNote"]
    assert cookie_detail["repairAccountId"] == str(account_id)
    assert cookie_detail["retryable"] is True

    engine_detail = client.get(f"/admin-api/ims/collect/log/{engine_id}", headers=auth).json()["data"]
    assert "未启动真实浏览器" in engine_detail["localNote"]
    assert engine_detail["repairAccountId"] == str(account_id)

    listed = client.get(
        "/admin-api/ims/collect/log/page",
        headers=auth,
        params={"status": "COOKIE_EXPIRED", "taskId": task_id},
    )
    assert listed.json()["data"]["total"] == 1
    assert "未连接真实平台" in listed.json()["data"]["list"][0]["localNote"]

    future = client.get(
        "/admin-api/ims/collect/log/page",
        headers=auth,
        params={"status": "ENGINE_UNAVAILABLE", "dateFrom": "2099-01-01"},
    )
    assert future.json()["data"]["total"] == 0
    assert future.json()["data"]["emptyTitle"] == "没有浏览器引擎不可用的日志"

    summary = client.get("/admin-api/ims/collect/quality/summary", headers=auth).json()["data"]
    assert summary["healthEmptyNote"] is None
    assert summary["successRate24h"] == 0.0
    assert summary["consecutiveFailureAccountCount"] >= 1
    assert summary["failureEmptyNote"] is None

    fill = client.post(
        "/admin-api/ims/collect/manual-fill",
        headers=auth,
        json={"taskId": task_id, "recordCount": 2, "remark": "本地补一条"},
    )
    assert fill.json()["code"] == 0
    assert "未调用 Collector" in fill.json()["data"]["localNote"]
    assert "浏览器引擎" in fill.json()["data"]["localNote"]
