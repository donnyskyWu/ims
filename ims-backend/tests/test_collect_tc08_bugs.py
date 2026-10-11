"""TC-08 / TC-09：阈值、cron、竞品账号、低分导出与桩采集投影。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.crypto import encrypt_text
from app.main import app
from app.ops_db import ops_session
from app.ops_models import CollectorAccountBind, Company, InternalContent, IpGroup, PlatformAccount

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_bound_account() -> int:
    ops = ops_session()
    try:
        company = Company(company_name="甲公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="小球 IP", status="ENABLED", tenant_id=0)
        ops.add_all([company, group])
        ops.flush()
        account = PlatformAccount(
            account_no="ACCT-BUG-001",
            account_name="神鱼体育",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
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
        return account.id
    finally:
        ops.close()


def test_cron_rejects_text_and_accepts_quartz():
    auth = headers()
    account_id = seed_bound_account()
    bad = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "非法 cron",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "abc",
            "status": "ENABLED",
        },
    )
    assert bad.json()["code"] == 1001
    assert "cron" in bad.json()["msg"]
    for expr in ("0 2 * * *", "0 */6 * * *", "0 0 */6 * * ?", "0 0 */6 * * ? *"):
        ok = client.post(
            "/admin-api/ims/collect/task",
            headers=auth,
            json={
                "taskName": f"合法 {expr}",
                "platformType": "DOUYIN",
                "accountId": account_id,
                "frequency": "DAILY",
                "cron": expr,
                "status": "ENABLED",
            },
        )
        assert ok.json()["code"] == 0, expr


def test_external_identifier_unique_import_and_credential():
    auth = headers()
    body = {
        "configName": "竞品 A",
        "platformType": "DOUYIN",
        "accountIdentifier": "tb_comp_a",
        "collectEnabled": True,
        "status": "ENABLED",
    }
    first = client.post("/admin-api/ims/collect/external/account", headers=auth, json=body)
    assert first.json()["code"] == 0
    dup = client.post("/admin-api/ims/collect/external/account", headers=auth, json=body)
    assert dup.json()["code"] == 1001
    assert "已存在" in dup.json()["msg"]

    imported = client.post(
        "/admin-api/ims/collect/external/account/import",
        headers=auth,
        json={"csvText": "platform,nick,url,keyword,enabled\nDOUYIN,导入号,https://example.com,词,1\n"},
    )
    assert imported.json()["code"] == 0
    assert imported.json()["data"]["pool"] == "CANDIDATE"
    assert "候选池" in imported.json()["data"]["message"]
    page = client.get(
        "/admin-api/ims/collect/external/account/page",
        headers=auth,
        params={"configName": "导入号"},
    )
    row = page.json()["data"]["list"][0]
    assert row["status"] == "DISABLED"
    assert row["collectEnabled"] is False

    deleted = client.post(
        "/admin-api/ims/collect/external/account/batch-delete",
        headers=auth,
        json={"ids": [int(first.json()["data"]["id"])]},
    )
    assert deleted.json()["code"] == 0
    assert "历史采集数据保留" in deleted.json()["data"]["message"]

    cred = client.post(
        "/admin-api/ims/collect/external/credential",
        headers=auth,
        json={
            "platformType": "DOUYIN",
            "profile": "default",
            "displayName": "租户抖音",
            "secret": "plain-cookie-value",
            "expireAt": "2026-12-31",
            "status": "ENABLED",
        },
    )
    assert cred.json()["code"] == 0
    mask = cred.json()["data"]["secretMask"]
    assert "plain-cookie-value" not in mask
    assert mask.endswith("ue")
    probed = client.post(
        f"/admin-api/ims/collect/external/credential/{cred.json()['data']['id']}/probe",
        headers=auth,
    )
    assert probed.json()["data"]["connStatus"] == "SUCCESS"

    jdbc = client.post(
        "/admin-api/ims/collect/external/source",
        headers=auth,
        json={"sourceName": "库", "baseUrl": "jdbc:mysql://localhost/ims"},
    )
    assert jdbc.json()["code"] == 1243


def test_threshold_rejects_text_and_negative_and_saves_override_fields():
    auth = headers()
    account_id = seed_bound_account()
    text = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "ALERT",
            "platformType": "DOUYIN",
            "ruleName": "失败率",
            "metricName": "fail_rate",
            "compareOperator": "GT",
            "thresholdValue": "abc",
            "notifyMethods": "站内",
            "status": "ENABLED",
        },
    )
    assert text.json()["code"] == 1001
    negative = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "WORK",
            "platformType": "DOUYIN",
            "hotValue": "-1",
            "lowValue": "20",
            "status": "ENABLED",
        },
    )
    assert negative.json()["code"] == 1001
    assert "负数" in negative.json()["msg"]
    missing = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={"thresholdCategory": "OVERRIDE", "platformType": "DOUYIN", "status": "ENABLED"},
    )
    assert missing.json()["code"] == 1001
    saved = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "ALERT",
            "platformType": "DOUYIN",
            "ruleName": "失败率",
            "metricName": "fail_rate",
            "compareOperator": "GT",
            "thresholdValue": "30",
            "notifyMethods": "站内",
            "status": "ENABLED",
        },
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["ruleName"] == "失败率"
    assert saved.json()["data"]["notifyMethods"] == "站内"
    override = client.post(
        "/admin-api/ims/collect/threshold",
        headers=auth,
        json={
            "thresholdCategory": "OVERRIDE",
            "platformType": "DOUYIN",
            "overrideAccountId": account_id,
            "overrideValue": "15",
            "status": "ENABLED",
        },
    )
    assert override.json()["code"] == 0
    assert override.json()["data"]["overrideValue"] == "15"


def test_ensure_unified_reports_existing_task():
    auth = headers()
    first = client.post("/admin-api/ims/collect/task/ensure-unified", headers=auth, json={"platformType": "DOUYIN"})
    assert first.json()["code"] == 0
    assert first.json()["data"]["existed"] is False
    second = client.post("/admin-api/ims/collect/task/ensure-unified", headers=auth, json={"platformType": "DOUYIN"})
    assert second.json()["code"] == 0
    assert second.json()["data"]["existed"] is True
    assert second.json()["data"]["message"] == "任务已存在"


def test_stub_run_writes_internal_low_score_works():
    auth = headers()
    account_id = seed_bound_account()
    created = client.post(
        "/admin-api/ims/collect/task",
        headers=auth,
        json={
            "taskName": "桩投影",
            "platformType": "DOUYIN",
            "accountId": account_id,
            "frequency": "DAILY",
            "cron": "0 2 * * *",
            "status": "ENABLED",
        },
    )
    task_id = created.json()["data"]["id"]
    run = client.post(f"/admin-api/ims/collect/task/{task_id}/run", headers=auth)
    assert run.json()["code"] == 0
    low = client.get(
        "/admin-api/ims/int-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE", "pageNo": 1, "pageSize": 20},
    )
    body = low.json()
    assert body["code"] == 0
    titles = [row["title"] for row in body["data"]["list"]]
    assert "桩采集·低分样例" in titles
    assert "桩采集·爆款样例" not in titles
    assert all(row["completionRate"] < 20 for row in body["data"]["list"])


def test_work_export_matches_low_score_filter_and_boundary():
    auth = headers()
    ops = ops_session()
    try:
        ops.add_all(
            [
                InternalContent(
                    title="刚好两成",
                    account_name="边界号",
                    platform_type="DOUYIN",
                    play_count=1000,
                    completion_rate=20.0,
                    publish_time="2026-10-04 09:00:00",
                    tenant_id=0,
                ),
                InternalContent(
                    title="差一点",
                    account_name="边界号",
                    platform_type="DOUYIN",
                    play_count=1000,
                    completion_rate=19.9,
                    publish_time="2026-10-04 10:00:00",
                    tenant_id=0,
                ),
            ]
        )
        ops.commit()
        work_id = ops.scalar(select(InternalContent.id).where(InternalContent.title == "差一点"))
    finally:
        ops.close()

    low = client.get(
        "/admin-api/ims/int-analysis/work/page",
        headers=auth,
        params={"segment": "LOW_SCORE"},
    )
    assert low.json()["code"] == 0
    assert [row["title"] for row in low.json()["data"]["list"]] == ["差一点"]

    exported = client.post(
        "/admin-api/ims/int-analysis/work/export",
        headers=auth,
        params={"segment": "LOW_SCORE"},
    )
    assert exported.status_code == 200
    assert exported.headers["x-export-rows"] == "1"
    assert "差一点" in exported.text
    assert "刚好两成" not in exported.text

    trend = client.get(f"/admin-api/ims/int-analysis/work/{work_id}/trend", headers=auth)
    points = trend.json()["data"]["points"]
    assert len(points) == 7
    assert points[-1]["value"] == 1000
    assert trend.json()["data"]["dailyDelta"] == points[-1]["value"] - points[-2]["value"]

    accounts = client.post(
        "/admin-api/ims/int-analysis/account/export",
        headers=auth,
        params={"segment": "ALL"},
    )
    assert accounts.status_code == 200
    assert "accountName" in accounts.text.splitlines()[0]
