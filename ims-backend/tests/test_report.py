import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.ops_db import ops_session
from app.ops_models import AuthorUser, IpGroup, IpGroupAnchorRel, PlatformAccount

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_report_template_create_and_list():
    auth = headers()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "抖音电商日度经营数据",
            "periodType": "DAILY",
            "deadlineRule": "18:00",
            "deptName": "运营中心",
            "businessLine": "BUSINESS",
            "status": "ENABLED",
            "fieldsSchema": [
                {"fieldKey": "gmv", "fieldLabel": "GMV", "fieldType": "NUMBER", "required": True},
                {"fieldKey": "orders", "fieldLabel": "订单数", "fieldType": "NUMBER", "required": True},
            ],
            "assignees": [],
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["fieldCount"] == 2
    assert body["data"]["templateNo"].startswith("RT")

    listed = client.get(
        "/admin-api/ims/report/template/list",
        headers=auth,
        params={"templateName": "抖音电商", "pageNo": 1, "pageSize": 10},
    )
    list_body = listed.json()
    assert list_body["code"] == 0
    assert list_body["data"]["total"] >= 1
    assert any(row["templateName"] == "抖音电商日度经营数据" for row in list_body["data"]["list"])


def test_report_template_1121_invalid_cross_check():
    auth = headers()
    bad = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "勾稽错误样例",
            "fieldsSchema": [
                {
                    "fieldKey": "summary",
                    "fieldLabel": "汇总",
                    "fieldType": "NUMBER",
                    "required": True,
                    "crossCheck": {
                        "targetFieldKey": "missing_detail",
                        "operator": "EQ",
                        "errorMsg": "明细合计须等于汇总",
                    },
                }
            ],
        },
    )
    assert bad.json()["code"] == 1121


def seed_author_accounts() -> tuple[int, int, int]:
    """Returns (template_id from caller, author_id, account_id)."""
    ops = ops_session()
    try:
        group = IpGroup(group_name="上报组", group_type="SMALL", status="ENABLED", leader_user_id=1, tenant_id=0)
        ops.add(group)
        ops.flush()
        author = AuthorUser(author_name="上报作者", ip_group_id=group.id, status="ENABLED", tenant_id=0)
        ops.add(author)
        ops.flush()
        ops.add(
            IpGroupAnchorRel(
                ip_group_id=group.id,
                anchor_user_id=author.id,
                is_primary=1,
                tenant_id=0,
            )
        )
        good_account = PlatformAccount(
            account_no="88001",
            account_name="共池账号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            status="IN_USE",
            tenant_id=0,
        )
        bad_account = PlatformAccount(
            account_no="88099",
            account_name="跨组账号",
            platform_type="DOUYIN",
            ip_group_id=0,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(good_account)
        ops.add(bad_account)
        ops.commit()
        return author.id, good_account.id, bad_account.id
    finally:
        ops.close()


def create_enabled_template(auth: dict) -> int:
    res = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "填报测试模板",
            "periodType": "DAILY",
            "fieldsSchema": [
                {"fieldKey": "metric_value", "fieldLabel": "指标", "fieldType": "NUMBER", "required": True},
            ],
        },
    )
    assert res.json()["code"] == 0
    return res.json()["data"]["id"]


def test_report_submit_list_and_dedup():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    submit = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": "2026-10-07",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"metric_value": 100},
            "asDraft": False,
        },
    )
    body = submit.json()
    assert body["code"] == 0
    assert body["data"]["submissionNo"].startswith("RS")
    assert body["data"]["submitStatus"] == "SUBMITTED"

    listed = client.get(
        "/admin-api/ims/report/submit/list",
        headers=auth,
        params={"templateId": template_id, "pageNo": 1, "pageSize": 10},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] >= 1

    dup = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": "2026-10-07",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"metric_value": 200},
            "asDraft": False,
        },
    )
    assert dup.json()["code"] == 1123


def test_report_submit_1127_pool_mismatch():
    auth = headers()
    author_id, _, bad_account_id = seed_author_accounts()
    template_id = create_enabled_template(auth)
    bad = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": "2026-10-08",
            "authorId": author_id,
            "accountId": bad_account_id,
            "dataContent": {"metric_value": 1},
            "asDraft": False,
        },
    )
    assert bad.json()["code"] == 1127


def submit_one(auth: dict, template_id: int, author_id: int, account_id: int, period: str) -> dict:
    res = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": period,
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"metric_value": 88},
            "asDraft": False,
        },
    )
    assert res.json()["code"] == 0
    return res.json()["data"]


def test_report_audit_queue_approve():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    sub = submit_one(auth, template_id, author_id, account_id, "2026-10-09")
    queued = client.get(
        "/admin-api/ims/report/audit/queue",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20},
    )
    body = queued.json()
    assert body["code"] == 0
    assert any(row["id"] == sub["id"] for row in body["data"]["list"])
    audited = client.put(
        f"/admin-api/ims/report/audit/{sub['id']}",
        headers=auth,
        json={"conclusion": "APPROVED"},
    )
    assert audited.json()["code"] == 0
    assert audited.json()["data"]["newStatus"] == "APPROVED"
    assert audited.json()["data"]["nextAction"] == "COMPLETED"


def test_report_audit_1124_reject_reason_required():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    sub = submit_one(auth, template_id, author_id, account_id, "2026-10-10")
    bad = client.put(
        f"/admin-api/ims/report/audit/{sub['id']}",
        headers=auth,
        json={"conclusion": "REJECTED", "rejectReason": ""},
    )
    assert bad.json()["code"] == 1124


def test_report_stat_complete_rate_after_approve():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    period = "2026-10-11"
    sub = submit_one(auth, template_id, author_id, account_id, period)
    client.put(
        f"/admin-api/ims/report/audit/{sub['id']}",
        headers=auth,
        json={"conclusion": "APPROVED"},
    )
    stat = client.get(
        "/admin-api/ims/report/stat/complete-rate",
        headers=auth,
        params={"statPeriod": period},
    )
    body = stat.json()
    assert body["code"] == 0
    assert body["data"]["totalCompleteRate"] == 100.0
    assert any(row["templateId"] == template_id for row in body["data"]["byTemplate"])

    trend = client.get(
        "/admin-api/ims/report/stat/trend",
        headers=auth,
        params={"dateRange": "2026-10-01,2026-10-31", "templateId": template_id},
    )
    assert trend.json()["code"] == 0
    assert any(row["statPeriod"] == period for row in trend.json()["data"])
