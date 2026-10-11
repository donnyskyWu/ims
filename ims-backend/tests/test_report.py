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


def report_user_ids(count: int) -> list[int]:
    from app.core import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin", User.deleted == 0).one()
        ids = [admin.id]
        tenant_id = admin.tenant_id or 0
        for index in range(1, count):
            username = f"rpt_expect_{index}"
            row = db.query(User).filter(User.username == username).one_or_none()
            if row is None:
                row = User(
                    username=username,
                    nickname=f"应报人{index}",
                    status="ENABLED",
                    tenant_id=tenant_id,
                    deleted=0,
                )
                db.add(row)
                db.flush()
            row.status = "ENABLED"
            row.deleted = 0
            row.tenant_id = tenant_id
            ids.append(row.id)
        db.commit()
        return ids
    finally:
        db.close()


def put_user_assignees(auth: dict, template_id: int, user_ids: list[int], name: str = "填报测试模板") -> None:
    updated = client.put(
        f"/admin-api/ims/report/template/{template_id}",
        headers=auth,
        json={
            "templateName": name,
            "periodType": "DAILY",
            "fieldsSchema": [
                {"fieldKey": "metric_value", "fieldLabel": "指标", "fieldType": "NUMBER", "required": True},
            ],
            "status": "ENABLED",
            "businessLine": "BUSINESS",
            "assignees": [{"assignType": "USER", "targetIds": user_ids}],
        },
    )
    assert updated.json()["code"] == 0


def test_report_stat_complete_rate_after_approve():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    admin_id = report_user_ids(1)[0]
    put_user_assignees(auth, template_id, [admin_id])
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
        params={"statPeriod": period, "templateId": template_id},
    )
    body = stat.json()
    assert body["code"] == 0
    assert body["data"]["shouldCount"] == 1
    assert body["data"]["completeApprovedCount"] == 1
    assert body["data"]["totalCompleteRate"] == 100.0
    assert any(row["templateId"] == template_id for row in body["data"]["byTemplate"])

    trend = client.get(
        "/admin-api/ims/report/stat/trend",
        headers=auth,
        params={"dateRange": "2026-10-01,2026-10-31", "templateId": template_id},
    )
    assert trend.json()["code"] == 0
    assert any(row["statPeriod"] == period for row in trend.json()["data"])


def test_report_stat_pass_rate_excludes_reject_from_completion():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    approved = submit_one(auth, template_id, author_id, account_id, "2026-11-01")
    rejected = submit_one(auth, template_id, author_id, account_id, "2026-11-02")
    assert (
        client.put(
            f"/admin-api/ims/report/audit/{approved['id']}",
            headers=auth,
            json={"conclusion": "APPROVED"},
        ).json()["code"]
        == 0
    )
    assert (
        client.put(
            f"/admin-api/ims/report/audit/{rejected['id']}",
            headers=auth,
            json={"conclusion": "REJECTED", "rejectReason": "勾稽不平"},
        ).json()["code"]
        == 0
    )
    draft = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": "2026-11-03",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"metric_value": 1},
            "asDraft": True,
        },
    )
    assert draft.json()["code"] == 0
    stat = client.get(
        "/admin-api/ims/report/stat/complete-rate",
        headers=auth,
        params={"templateId": template_id},
    )
    body = stat.json()
    assert body["code"] == 0
    assert body["data"]["shouldCount"] == 0
    assert body["data"]["completeApprovedCount"] == 0
    assert body["data"]["submittedCount"] == 2
    assert body["data"]["approvedCount"] == 1
    assert body["data"]["totalCompleteRate"] == 0.0
    assert body["data"]["passRate"] == 50.0
    assert body["data"]["totalCompleteRate"] != body["data"]["passRate"]
    assert body["data"]["rejectCount"] == 1
    assert body["data"]["todayCount"] == 2
    assert body["data"]["fieldCheckHitRate"] == 100.0
    assert body["data"]["avgAuditHours"] >= 0


def test_report_stat_expected_count_includes_people_who_did_not_file():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    author2, account2, _ = seed_author_accounts()
    user_ids = report_user_ids(3)
    template_id = create_enabled_template(auth)
    put_user_assignees(auth, template_id, user_ids)
    period = "2026-12-01"
    first = submit_one(auth, template_id, author_id, account_id, period)
    second = submit_one(auth, template_id, author2, account2, period)
    for submission in (first, second):
        assert (
            client.put(
                f"/admin-api/ims/report/audit/{submission['id']}",
                headers=auth,
                json={"conclusion": "APPROVED"},
            ).json()["code"]
            == 0
        )
    stat = client.get(
        "/admin-api/ims/report/stat/complete-rate",
        headers=auth,
        params={"templateId": template_id, "statPeriod": period},
    )
    data = stat.json()["data"]
    assert stat.json()["code"] == 0
    assert data["shouldCount"] == 3
    assert data["completeApprovedCount"] == 1
    assert data["approvedCount"] == 2
    assert data["submittedCount"] == 2
    assert data["totalCompleteRate"] == 33.33
    assert data["totalCompleteRate"] <= 33.33
    assert data["passRate"] == 100.0
    missed = client.get(
        "/admin-api/ims/report/stat/missed",
        headers=auth,
        params={"templateId": template_id, "statPeriod": period, "pageNo": 1, "pageSize": 20},
    )
    missed_body = missed.json()
    assert missed_body["code"] == 0
    rows = missed_body["data"]["list"]
    missed_ids = {row["userId"] for row in rows if row["status"] == "MISSED"}
    assert set(user_ids[1:]) <= missed_ids
    assert user_ids[0] not in {row["userId"] for row in rows}
    assert all(row["status"] == "MISSED" for row in rows if row["userId"] in user_ids[1:])


def test_report_stat_rotation_counts_one_duty_user():
    from datetime import date

    auth = headers()
    user_ids = report_user_ids(3)
    day = date(2026, 12, 2)
    period = day.isoformat()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "轮值应报",
            "periodType": "DAILY",
            "fieldsSchema": [
                {"fieldKey": "metric_value", "fieldLabel": "指标", "fieldType": "NUMBER", "required": True},
            ],
            "assignees": [
                {
                    "assignType": "DEPT_ROTATION",
                    "rotationList": [
                        {"userId": uid, "order": index + 1} for index, uid in enumerate(user_ids)
                    ],
                }
            ],
        },
    )
    assert created.json()["code"] == 0
    template_id = created.json()["data"]["id"]
    duty = user_ids[day.toordinal() % len(user_ids)]
    stat = client.get(
        "/admin-api/ims/report/stat/complete-rate",
        headers=auth,
        params={"templateId": template_id, "statPeriod": period},
    )
    data = stat.json()["data"]
    assert data["shouldCount"] == 1
    assert data["completeApprovedCount"] == 0
    assert data["totalCompleteRate"] == 0.0
    missed = client.get(
        "/admin-api/ims/report/stat/missed",
        headers=auth,
        params={"templateId": template_id, "statPeriod": period, "pageNo": 1, "pageSize": 20},
    )
    rows = missed.json()["data"]["list"]
    assert [row["userId"] for row in rows] == [duty]
    assert rows[0]["status"] == "MISSED"


def test_report_stat_position_expands_to_enabled_users():
    from app.core import SessionLocal
    from app.models import Role, User, UserRole

    auth = headers()
    user_ids = report_user_ids(3)
    holders = user_ids[1:]
    role_key = "rpt_pos_b047"
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.id == user_ids[0]).one()
        tenant_id = admin.tenant_id or 0
        role = db.query(Role).filter(Role.role_key == role_key).one_or_none()
        if role is None:
            role = Role(
                role_name="上报岗位",
                role_key=role_key,
                dingtalk_position=role_key,
                status="ENABLED",
                tenant_id=tenant_id,
                deleted=0,
            )
            db.add(role)
            db.flush()
        role.status = "ENABLED"
        role.deleted = 0
        role.tenant_id = tenant_id
        role.dingtalk_position = role_key
        for uid in holders:
            link = db.query(UserRole).filter(UserRole.user_id == uid, UserRole.role_id == role.id).one_or_none()
            if link is None:
                db.add(UserRole(user_id=uid, role_id=role.id, tenant_id=tenant_id))
        db.commit()
    finally:
        db.close()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "岗位应报",
            "periodType": "DAILY",
            "fieldsSchema": [
                {"fieldKey": "metric_value", "fieldLabel": "指标", "fieldType": "NUMBER", "required": True},
            ],
            "assignees": [{"assignType": "POSITION", "targetCodes": [role_key]}],
        },
    )
    assert created.json()["code"] == 0
    template_id = created.json()["data"]["id"]
    period = "2026-12-03"
    stat = client.get(
        "/admin-api/ims/report/stat/complete-rate",
        headers=auth,
        params={"templateId": template_id, "statPeriod": period},
    )
    data = stat.json()["data"]
    assert data["shouldCount"] == 2
    assert data["completeApprovedCount"] == 0
    missed = client.get(
        "/admin-api/ims/report/stat/missed",
        headers=auth,
        params={"templateId": template_id, "statPeriod": period, "pageNo": 1, "pageSize": 20},
    )
    missed_ids = {row["userId"] for row in missed.json()["data"]["list"]}
    assert missed_ids == set(holders)


def test_report_template_expr_rejects_delete_and_drop():
    auth = headers()
    base = {
        "templateName": "表达式拦截",
        "fieldsSchema": [
            {"fieldKey": "gmv", "fieldLabel": "GMV", "fieldType": "NUMBER", "required": True},
            {"fieldKey": "orders", "fieldLabel": "订单数", "fieldType": "INTEGER", "required": False},
        ],
    }
    deleted = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            **base,
            "templateName": "DELETE 拦截",
            "fieldsSchema": base["fieldsSchema"]
            + [
                {
                    "fieldKey": "rule_del",
                    "fieldLabel": "非法勾稽",
                    "fieldType": "CROSS_RULE",
                    "crossCheck": {"expression": "DELETE FROM tb_x", "errorMsg": "不平"},
                }
            ],
        },
    )
    assert deleted.json()["code"] == 1192
    assert "非法表达式" in deleted.json()["msg"]

    dropped = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            **base,
            "templateName": "DROP 拦截",
            "fieldsSchema": [
                {
                    "fieldKey": "gmv",
                    "fieldLabel": "GMV",
                    "fieldType": "NUMBER",
                    "required": True,
                    "validateExpr": "DROP TABLE tb_x",
                }
            ],
        },
    )
    assert dropped.json()["code"] == 1192

    missing = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            **base,
            "templateName": "未知字段",
            "fieldsSchema": base["fieldsSchema"]
            + [
                {
                    "fieldKey": "rule_miss",
                    "fieldLabel": "未知字段",
                    "fieldType": "CROSS_RULE",
                    "crossCheck": {"expression": "detail_sum == summary", "errorMsg": "不平"},
                }
            ],
        },
    )
    assert missing.json()["code"] == 1121

    ok_res = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            **base,
            "templateName": "合法勾稽",
            "fieldsSchema": base["fieldsSchema"]
            + [
                {
                    "fieldKey": "rule_ok",
                    "fieldLabel": "明细合计",
                    "fieldType": "CROSS_RULE",
                    "crossCheck": {"expression": "gmv == orders", "errorMsg": "明细合计不平"},
                }
            ],
        },
    )
    body = ok_res.json()
    assert body["code"] == 0
    assert body["data"]["fieldCount"] == 2
    template_id = body["data"]["id"]

    preview_bad = client.post(
        f"/admin-api/ims/report/template/{template_id}/preview",
        headers=auth,
        json={"sampleData": {"gmv": 10, "orders": 3}},
    )
    assert preview_bad.json()["code"] == 0
    assert preview_bad.json()["data"]["validationResult"]["passed"] is False

    preview_ok = client.post(
        f"/admin-api/ims/report/template/{template_id}/preview",
        headers=auth,
        json={"sampleData": {"gmv": 4, "orders": 4}},
    )
    assert preview_ok.json()["data"]["validationResult"]["passed"] is True


def test_report_submit_rejects_stored_illegal_expression():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    from app.core import SessionLocal
    from app.models import ReportTemplate

    db = SessionLocal()
    try:
        row = db.get(ReportTemplate, template_id)
        fields = list(row.fields_schema or [])
        fields.append(
            {
                "fieldKey": "rule_stored",
                "fieldLabel": "库存非法式",
                "fieldType": "CROSS_RULE",
                "crossCheck": {"expression": "DROP TABLE tb_x", "errorMsg": "拒绝"},
            }
        )
        row.fields_schema = fields
        db.commit()
    finally:
        db.close()

    blocked = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": "2026-10-12",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"metric_value": 1},
            "asDraft": False,
        },
    )
    assert blocked.json()["code"] == 1192

    preview = client.post(
        f"/admin-api/ims/report/template/{template_id}/preview",
        headers=auth,
        json={"sampleData": {"metric_value": 1}},
    )
    assert preview.json()["code"] == 1192


def test_report_assignees_create_fill_todos_only_for_selected_users():
    auth = headers()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "填报人待办",
            "fieldsSchema": [
                {"fieldKey": "gmv", "fieldLabel": "GMV", "fieldType": "MONEY", "required": True, "range": {"min": 0}},
            ],
            "assignees": [],
        },
    )
    assert created.json()["code"] == 0
    template_id = created.json()["data"]["id"]
    admin_id = created.json()["data"]["createdBy"]
    updated = client.put(
        f"/admin-api/ims/report/template/{template_id}",
        headers=auth,
        json={
            "templateName": "填报人待办",
            "fieldsSchema": [
                {"fieldKey": "gmv", "fieldLabel": "GMV", "fieldType": "MONEY", "required": True, "range": {"min": 0}},
            ],
            "assignees": [{"assignType": "USER", "targetIds": [admin_id]}],
            "status": "ENABLED",
            "periodType": "DAILY",
            "deadlineRule": "18:00",
            "businessLine": "BUSINESS",
        },
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"]["version"] >= 2

    from app.core import SessionLocal
    from app.models import Todo

    db = SessionLocal()
    try:
        rows = list(
            db.query(Todo)
            .filter(Todo.ref_type == "report_template", Todo.ref_id == template_id, Todo.task_type == "report_fill")
            .all()
        )
    finally:
        db.close()
    pending = [row for row in rows if row.status == "PENDING"]
    assert [row.assignee_user_id for row in pending] == [admin_id]
    assert any("填报待办" in row.title for row in pending)


def test_report_submit_context_cascades_enabled_templates_and_author_pool():
    auth = headers()
    author_id, account_id, bad_account_id = seed_author_accounts()
    template_id = create_enabled_template(auth)
    disabled = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "已停用模板",
            "status": "DISABLED",
            "fieldsSchema": [
                {"fieldKey": "gmv", "fieldLabel": "GMV", "fieldType": "NUMBER", "required": True},
            ],
        },
    )
    assert disabled.json()["code"] == 0
    disabled_id = disabled.json()["data"]["id"]

    bare = client.get("/admin-api/ims/report/submit/context", headers=auth)
    assert bare.json()["code"] == 0
    template_ids = [row["id"] for row in bare.json()["data"]["templates"]]
    assert template_id in template_ids
    assert disabled_id not in template_ids
    assert bare.json()["data"]["authors"] == []
    assert bare.json()["data"]["accounts"] == []

    by_template = client.get(
        "/admin-api/ims/report/submit/context",
        headers=auth,
        params={"templateId": template_id},
    )
    assert by_template.json()["code"] == 0
    assert any(row["id"] == author_id and row["authorName"] == "上报作者" for row in by_template.json()["data"]["authors"])
    assert by_template.json()["data"]["accounts"] == []

    pooled = client.get(
        "/admin-api/ims/report/submit/context",
        headers=auth,
        params={"templateId": template_id, "authorId": author_id},
    )
    assert pooled.json()["code"] == 0
    account_ids = [row["id"] for row in pooled.json()["data"]["accounts"]]
    assert account_id in account_ids
    assert bad_account_id not in account_ids

    stopped = client.get(
        "/admin-api/ims/report/submit/context",
        headers=auth,
        params={"templateId": disabled_id},
    )
    assert stopped.json()["code"] == 1501


def test_report_submit_1122_rejects_value_below_min():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "非负金额",
            "fieldsSchema": [
                {
                    "fieldKey": "gmv",
                    "fieldLabel": "当日GMV",
                    "fieldType": "MONEY",
                    "required": True,
                    "range": {"min": 0},
                }
            ],
        },
    )
    assert created.json()["code"] == 0
    bad = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": created.json()["data"]["id"],
            "period": "2026-10-11",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"gmv": -1},
            "asDraft": False,
        },
    )
    body = bad.json()
    assert body["code"] == 1122
    assert body["data"]["errors"][0]["fieldKey"] == "gmv"


def test_report_submit_list_author_filter_and_data_volume():
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    template_id = create_enabled_template(auth)
    submit = client.post(
        "/admin-api/ims/report/submit",
        headers=auth,
        json={
            "templateId": template_id,
            "period": "2026-10-13",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"metric_value": 9, "_rowCount": 3},
            "asDraft": False,
        },
    )
    assert submit.json()["code"] == 0
    assert submit.json()["data"]["dataVolume"] == 3

    listed = client.get(
        "/admin-api/ims/report/submit/list",
        headers=auth,
        params={"authorId": author_id, "accountId": account_id, "pageNo": 1, "pageSize": 20},
    )
    assert listed.json()["code"] == 0
    matched = [row for row in listed.json()["data"]["list"] if row["templateId"] == template_id]
    assert matched
    assert matched[0]["dataVolume"] == 3

    empty = client.get(
        "/admin-api/ims/report/submit/list",
        headers=auth,
        params={"authorId": 999999, "pageNo": 1, "pageSize": 10},
    )
    assert empty.json()["data"]["total"] == 0


def test_report_template_frequency_dept_and_reenable():
    auth = headers()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "周五经营模板",
            "periodType": "WEEKLY",
            "deadlineRule": "周五 18:00",
            "deptName": "直播运营",
            "businessLine": "FINANCE",
            "fieldsSchema": [],
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["periodType"] == "WEEKLY"
    assert body["data"]["deadlineRule"] == "周五 18:00"
    assert body["data"]["deptName"] == "直播运营"
    assert body["data"]["businessLine"] == "FINANCE"
    template_id = body["data"]["id"]

    stopped = client.delete(f"/admin-api/ims/report/template/{template_id}", headers=auth)
    assert stopped.json()["code"] == 0
    assert stopped.json()["data"]["status"] == "DISABLED"

    enabled = client.put(
        f"/admin-api/ims/report/template/{template_id}",
        headers=auth,
        json={
            "templateName": "周五经营模板",
            "periodType": "WEEKLY",
            "deadlineRule": "周五 18:00",
            "deptName": "直播运营",
            "businessLine": "FINANCE",
            "status": "ENABLED",
            "fieldsSchema": [],
            "assignees": [],
        },
    )
    assert enabled.json()["code"] == 0
    assert enabled.json()["data"]["status"] == "ENABLED"


def _dept_user(username: str, mobile: str) -> int:
    from app.core import SessionLocal
    from app.models import Role, RolePerm, User, UserDept, UserRole
    from app.security import hash_password

    db = SessionLocal()
    try:
        user = User(
            username=username,
            nickname=username,
            mobile=mobile,
            password_hash=hash_password("Admin@123"),
            status="ENABLED",
            tenant_id=0,
        )
        role = Role(
            role_name=username,
            role_key=f"rpt:{username}",
            data_scope="DEPT",
            status="ENABLED",
            source="MANUAL",
            tenant_id=0,
        )
        db.add_all([user, role])
        db.flush()
        db.add(
            RolePerm(
                role_id=role.id,
                module_code="auth",
                perm_code="auth:workbench:query",
                perm_level="R",
                tenant_id=0,
            )
        )
        db.add(UserRole(user_id=user.id, role_id=role.id, tenant_id=0))
        db.add(UserDept(user_id=user.id, dept_id=8301, tenant_id=0))
        db.commit()
        return int(user.id)
    finally:
        db.close()


def _login(username: str) -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": username, "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_assigned_dept_filler_can_submit_without_report_menu_perm():
    filler_id = _dept_user("rpt_fill_b083", "13900008301")
    outsider_id = _dept_user("rpt_outsider_b083", "13900008302")
    assert outsider_id != filler_id
    auth = headers()
    author_id, account_id, _ = seed_author_accounts()
    created = client.post(
        "/admin-api/ims/report/template",
        headers=auth,
        json={
            "templateName": "TB上报模板3",
            "periodType": "DAILY",
            "deadlineRule": "18:00",
            "status": "ENABLED",
            "businessLine": "BUSINESS",
            "fieldsSchema": [
                {"fieldKey": "gmv", "fieldLabel": "GMV", "fieldType": "NUMBER", "required": True},
            ],
            "assignees": [{"assignType": "USER", "targetIds": [filler_id]}],
        },
    )
    assert created.json()["code"] == 0, created.json()
    template_id = created.json()["data"]["id"]

    filler = _login("rpt_fill_b083")
    context = client.get(
        "/admin-api/ims/report/submit/context",
        headers=filler,
        params={"templateId": template_id},
    )
    body = context.json()
    assert body["code"] == 0, body
    assert any(row["id"] == template_id for row in body["data"]["templates"])

    submitted = client.post(
        "/admin-api/ims/report/submit",
        headers=filler,
        json={
            "templateId": template_id,
            "period": "2026-10-11",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"gmv": 12},
            "asDraft": False,
        },
    )
    assert submitted.json()["code"] == 0, submitted.json()

    outsider = _login("rpt_outsider_b083")
    denied = client.get(
        "/admin-api/ims/report/submit/context",
        headers=outsider,
        params={"templateId": template_id},
    )
    assert denied.json()["code"] == 1008
    blocked = client.post(
        "/admin-api/ims/report/submit",
        headers=outsider,
        json={
            "templateId": template_id,
            "period": "2026-10-11",
            "authorId": author_id,
            "accountId": account_id,
            "dataContent": {"gmv": 1},
            "asDraft": False,
        },
    )
    assert blocked.json()["code"] == 1008
