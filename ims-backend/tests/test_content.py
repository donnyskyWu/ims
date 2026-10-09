import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import Base, engine
from app.main import app, init_db
from app.models import ContentProject, ContentReview
from app.ops_db import OpsBase, ops_engine, ops_session
from app.ops_models import AuthorUser, Company, IpGroup, IpGroupAnchorRel, PlatformAccount, Realname
from app.crypto import encrypt_text

client = TestClient(app)



def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_ip_group() -> int:
    ops = ops_session()
    try:
        group = IpGroup(group_name="内容IP-A", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.commit()
        return group.id
    finally:
        ops.close()


def seed_account() -> int:
    ops = ops_session()
    try:
        company = Company(company_name="内容公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="发布组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="李四",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011239"),
            phone_enc=encrypt_text("13800002222"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-PUB-01",
            account_name="发布号",
            platform_type="DOUYIN",
            ip_group_id=group.id,
            company_id=company.id,
            realname_id=person.id,
            holder_user_id=1,
            author_user_id=1,
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(account)
        ops.commit()
        return account.id
    finally:
        ops.close()


CHECKLIST_PASS = {"COMPLIANCE": True, "QUALITY": True, "BRAND": True}


def pass_review_conclusion(auth: dict, review_no: str) -> None:
    res = client.put(
        f"/admin-api/ims/content/review/{review_no}/conclusion",
        headers=auth,
        json={"conclusion": "PASS", "checklistResult": CHECKLIST_PASS},
    )
    assert res.json()["code"] == 0


def pending_review_no_for_project(auth: dict, project_id: int) -> str | None:
    queue = client.get("/admin-api/ims/content/review/queue", headers=auth)
    assert queue.json()["code"] == 0
    for row in queue.json()["data"]["list"]:
        if row.get("contentProjectId") == project_id:
            return row["reviewNo"]
    return None


def pass_all_pending_reviews(auth: dict, project_id: int) -> None:
    for _ in range(4):
        review_no = pending_review_no_for_project(auth, project_id)
        if not review_no:
            break
        pass_review_conclusion(auth, review_no)


def seed_pending_review(db=None) -> tuple[int, str]:
    from app.core import SessionLocal

    local = db or SessionLocal()
    try:
        project = ContentProject(
            title="待审短视频",
            review_passed=0,
            submitter_user_id=9001,
            creator=9001,
            tenant_id=0,
        )
        local.add(project)
        local.flush()
        review = ContentReview(
            review_no="RV202610060001",
            content_project_id=project.id,
            content_title=project.title,
            submitter_user_id=9001,
            review_round=1,
            creator=1,
            tenant_id=0,
        )
        local.add(review)
        local.commit()
        return project.id, review.review_no
    finally:
        if db is None:
            local.close()


def test_sop_list_and_plan_create():
    auth = headers()
    empty = client.get("/admin-api/ims/content/sop/list", headers=auth)
    assert empty.json()["code"] == 0
    assert empty.json()["data"]["total"] == 0

    create = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "带货短视频标准 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "脚本",
                    "standardDesc": "脚本标准",
                    "qualityChecklist": [{"itemCode": "SCRIPT_OK", "itemDesc": "脚本完整", "required": True}],
                    "ownerRole": "R6",
                    "slaHours": 24,
                }
            ],
        },
    )
    assert create.json()["code"] == 0
    sop_id = create.json()["data"]["id"]
    assert create.json()["data"]["version"] == 1

    nodes = client.get(f"/admin-api/ims/content/sop/{sop_id}/nodes", headers=auth)
    assert nodes.json()["code"] == 0
    assert len(nodes.json()["data"]) == 1

    ip_group_id = seed_ip_group()
    plan = client.post(
        "/admin-api/ims/content/plan",
        headers=auth,
        json={
            "planName": "10月内容计划",
            "sopId": sop_id,
            "ipGroupIds": [ip_group_id],
            "startDate": "2026-10-01",
            "endDate": "2026-10-31",
        },
    )
    assert plan.json()["code"] == 0
    assert plan.json()["data"]["status"] == "DRAFT"
    assert plan.json()["data"]["sopId"] == sop_id

    plans = client.get("/admin-api/ims/content/plan", headers=auth)
    assert plans.json()["code"] == 0
    assert plans.json()["data"]["total"] == 1

    plan_id = plan.json()["data"]["id"]
    started = client.post(f"/admin-api/ims/content/plan/{plan_id}/start", headers=auth)
    assert started.json()["code"] == 0
    assert started.json()["data"]["status"] == "IN_PROGRESS"
    assert started.json()["data"]["tasksGenerated"] == 1

    tasks = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "onlyMine": False},
    )
    assert tasks.json()["code"] == 0
    assert tasks.json()["data"]["total"] >= 1
    assert any(t["planName"] == "10月内容计划" for t in tasks.json()["data"]["list"])

    blocked = client.post(f"/admin-api/ims/content/plan/{plan_id}/start", headers=auth)
    assert blocked.json()["code"] == 1502


def test_plan_terminate_approve_flow():
    """#36 · 计划终止：申请 → 批准 → TERMINATED + 关联任务 TERMINATED"""
    auth = headers()
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "计划终止 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "终止节点",
                    "nodeType": "NORMAL",
                    "ownerRole": "R6",
                    "slaHours": 24,
                }
            ],
        },
    )
    assert sop.json()["code"] == 0
    sop_id = sop.json()["data"]["id"]
    ip_group_id = seed_ip_group()
    plan = client.post(
        "/admin-api/ims/content/plan",
        headers=auth,
        json={
            "planName": "计划终止验收",
            "sopId": sop_id,
            "ipGroupIds": [ip_group_id],
            "startDate": "2026-10-01",
            "endDate": "2026-10-31",
        },
    )
    assert plan.json()["code"] == 0
    plan_id = plan.json()["data"]["id"]
    started = client.post(f"/admin-api/ims/content/plan/{plan_id}/start", headers=auth)
    assert started.json()["code"] == 0

    pending = client.post(
        f"/admin-api/ims/content/plan/{plan_id}/terminate",
        headers=auth,
        json={"reason": "E2E 终止原因"},
    )
    assert pending.json()["code"] == 0
    assert pending.json()["data"]["status"] == "TERMINATE_PENDING"
    assert pending.json()["data"]["terminateReason"] == "E2E 终止原因"

    approved = client.post(f"/admin-api/ims/content/plan/{plan_id}/terminate/approve", headers=auth)
    assert approved.json()["code"] == 0
    assert approved.json()["data"]["status"] == "TERMINATED"
    assert approved.json()["data"]["tasksTerminated"] == 1

    tasks = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "onlyMine": False, "planName": "计划终止验收"},
    )
    assert tasks.json()["code"] == 0
    assert tasks.json()["data"]["total"] == 1
    assert tasks.json()["data"]["list"][0]["status"] == "TERMINATED"

    reject_blocked = client.post(f"/admin-api/ims/content/plan/{plan_id}/terminate/reject", headers=auth)
    assert reject_blocked.json()["code"] == 1502


def test_plan_start_normal_task_execute_complete():
    """#33 · 计划启动 → 执行页完成（NORMAL 节点 · ADR-079 工作说明）"""
    auth = headers()
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "计划任务完成 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "校对",
                    "nodeType": "NORMAL",
                    "ownerRole": "R6",
                    "slaHours": 24,
                }
            ],
        },
    )
    assert sop.json()["code"] == 0
    sop_id = sop.json()["data"]["id"]

    ops = ops_session()
    try:
        group = IpGroup(group_name="计划任务组", status="ENABLED", leader_user_id=1, tenant_id=0)
        ops.add(group)
        ops.commit()
        ip_group_id = group.id
    finally:
        ops.close()

    plan = client.post(
        "/admin-api/ims/content/plan",
        headers=auth,
        json={
            "planName": "计划任务完成验收",
            "sopId": sop_id,
            "ipGroupIds": [ip_group_id],
            "startDate": "2026-10-01",
            "endDate": "2026-10-31",
        },
    )
    assert plan.json()["code"] == 0
    plan_id = plan.json()["data"]["id"]

    started = client.post(f"/admin-api/ims/content/plan/{plan_id}/start", headers=auth)
    assert started.json()["code"] == 0

    mine = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={"onlyMine": True, "pageSize": 20, "planName": "计划任务完成验收"},
    )
    assert mine.json()["code"] == 0
    assert mine.json()["data"]["total"] >= 1
    task_id = mine.json()["data"]["list"][0]["id"]

    execute = client.get(f"/admin-api/ims/content/task/{task_id}/execute", headers=auth)
    assert execute.json()["code"] == 0
    assert execute.json()["data"]["nodeType"] == "NORMAL"

    blocked = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/complete",
        headers=auth,
        json={},
    )
    assert blocked.json()["code"] == 1500

    done = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/complete",
        headers=auth,
        json={"deliverables": "校对完成（pytest）"},
    )
    assert done.json()["code"] == 0
    assert done.json()["data"]["status"] == "DONE"


def test_review_gate_and_publish():
    auth = headers()
    account_id = seed_account()
    project_id, review_no = seed_pending_review()

    blocked = client.post(
        "/admin-api/ims/content/publish",
        headers=auth,
        json={
            "contentProjectId": project_id,
            "accountId": account_id,
            "platform": "DOUYIN",
            "planPublishAt": "2026-10-08T18:00:00+08:00",
            "caption": "测试文案",
        },
    )
    assert blocked.json()["code"] == 1054

    queue = client.get("/admin-api/ims/content/review/queue", headers=auth)
    assert queue.json()["code"] == 0
    assert queue.json()["data"]["total"] >= 1

    reject_missing = client.put(
        f"/admin-api/ims/content/review/{review_no}/conclusion",
        headers=auth,
        json={"conclusion": "REJECT_BACK", "checklistResult": {"COMPLIANCE": False}},
    )
    assert reject_missing.json()["code"] == 1058

    pass_review_conclusion(auth, review_no)

    blocked_after_l1 = client.post(
        "/admin-api/ims/content/publish",
        headers=auth,
        json={
            "contentProjectId": project_id,
            "accountId": account_id,
            "platform": "DOUYIN",
            "planPublishAt": "2026-10-08T18:00:00+08:00",
            "caption": "测试文案",
        },
    )
    assert blocked_after_l1.json()["code"] == 1054

    review_no_l2 = pending_review_no_for_project(auth, project_id)
    assert review_no_l2 is not None
    queue_l2 = client.get("/admin-api/ims/content/review/queue", headers=auth)
    l2_row = next(r for r in queue_l2.json()["data"]["list"] if r["reviewNo"] == review_no_l2)
    assert l2_row["reviewRound"] == 2

    pass_review_conclusion(auth, review_no_l2)

    publish = client.post(
        "/admin-api/ims/content/publish",
        headers=auth,
        json={
            "contentProjectId": project_id,
            "accountId": account_id,
            "platform": "DOUYIN",
            "planPublishAt": "2026-10-08T18:00:00+08:00",
            "caption": "测试文案",
        },
    )
    assert publish.json()["code"] == 0
    assert publish.json()["data"]["publishStatus"] == "PENDING_PUBLISH"
    publish_id = publish.json()["data"]["id"]

    listing = client.get("/admin-api/ims/content/publish/list", headers=auth)
    assert listing.json()["code"] == 0
    assert listing.json()["data"]["total"] >= 1
    publish_no = publish.json()["data"]["publishNo"]
    scoped = client.get(
        "/admin-api/ims/content/publish/list",
        headers=auth,
        params={
            "accountId": account_id,
            "platform": "DOUYIN",
            "publishStatus": "PENDING_PUBLISH",
            "timeFrom": "2026-10-08T00:00:00+08:00",
            "timeTo": "2026-10-08T23:59:59+08:00",
            "pageSize": 50,
        },
    )
    assert scoped.json()["code"] == 0
    assert any(row["publishNo"] == publish_no for row in scoped.json()["data"]["list"])
    missed = client.get(
        "/admin-api/ims/content/publish/list",
        headers=auth,
        params={"platform": "KUAISHOU", "accountId": account_id, "pageSize": 50},
    )
    assert missed.json()["code"] == 0
    assert all(row["publishNo"] != publish_no for row in missed.json()["data"]["list"])

    pending = client.get("/admin-api/ims/content/publish/pending", headers=auth)
    assert pending.json()["code"] == 0
    assert any(row["publishNo"] == publish.json()["data"]["publishNo"] for row in pending.json()["data"]["list"])

    receipt = client.put(
        f"/admin-api/ims/content/publish/{publish_id}/receipt",
        headers=auth,
        json={"publishUrl": "https://example.com/p/1", "publishedAt": "2026-10-08T20:00:00+08:00"},
    )
    assert receipt.json()["code"] == 0

    archive = client.get(f"/admin-api/ims/content/publish/{publish_id}/archive", headers=auth)
    assert archive.json()["code"] == 0
    assert archive.json()["data"]["archiveNo"].startswith("AR")
    assert len(archive.json()["data"]["fileList"]) >= 3


def seed_work_task_context() -> tuple[int, int]:
    """Returns (ip_group_id, author_id)."""
    ops = ops_session()
    try:
        group = IpGroup(group_name="工作任务组", status="ENABLED", leader_user_id=1, tenant_id=0)
        ops.add(group)
        ops.flush()
        author = AuthorUser(author_name="作者甲", ip_group_id=group.id, status="ENABLED", tenant_id=0)
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
        ops.commit()
        return group.id, author.id
    finally:
        ops.close()


def test_work_task_confirm_and_withdraw():
    auth = headers()
    ip_group_id, author_id = seed_work_task_context()
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "公推 SOP",
            "contentType": "SHORT_VIDEO",
            "marketingPlan": "LIVE_PUBLIC",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "撰写",
                    "nodeType": "CONTENT_GENERATION",
                    "documentType": "COPY",
                    "ownerRole": "R6",
                },
                {"nodeOrder": 2, "nodeName": "审核准备", "nodeType": "NORMAL", "ownerRole": "R6"},
            ],
        },
    )
    assert sop.json()["code"] == 0

    sheet = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": ip_group_id, "workDate": "2026-10-06"},
    )
    assert sheet.json()["code"] == 0
    sheet_id = sheet.json()["data"]["id"]
    assert len(sheet.json()["data"]["assignments"]) == 10

    save = client.post(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        json={
            "ipGroupId": ip_group_id,
            "workDate": "2026-10-06",
            "assignments": [
                {
                    "rowNo": 1,
                    "authorId": author_id,
                    "workDate": "2026-10-06",
                    "marketingPlan": "LIVE_PUBLIC",
                    "isLive": 0,
                    "salesPlatform": "DOUYIN",
                    "competitions": [
                        {
                            "competitionId": "M001",
                            "competitionName": "测试赛",
                            "leagueName": "联赛A",
                            "matchTime": "2026-10-06T20:00:00",
                        }
                    ],
                }
            ],
        },
    )
    assert save.json()["code"] == 0
    assignment_id = save.json()["data"]["assignments"][0]["id"]

    confirm = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/confirm",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert confirm.json()["code"] == 0
    assert confirm.json()["data"]["generatedTaskCount"] == 2
    assert confirm.json()["data"]["autoAiGenerate"] is False

    again = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": ip_group_id, "workDate": "2026-10-06"},
    )
    row = again.json()["data"]["assignments"][0]
    assert row["rowStatus"] == "CONFIRMED"
    assert len(row["generatedTaskIds"]) == 2
    assert "ipGroupLeaderName" in again.json()["data"]

    page_wt = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={
            "onlyMine": False,
            "ipGroupId": ip_group_id,
            "workDate": "2026-10-06",
            "pageSize": 50,
        },
    )
    assert page_wt.json()["code"] == 0
    assert page_wt.json()["data"]["total"] >= 2
    task_row = page_wt.json()["data"]["list"][0]
    assert task_row["workDate"] == "2026-10-06"
    assert task_row.get("authorName")

    withdraw = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/withdraw",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert withdraw.json()["code"] == 0
    assert withdraw.json()["data"]["assignments"][0]["rowStatus"] == "DRAFT"
    assert withdraw.json()["data"]["assignments"][0]["generatedTaskIds"] == []


def _post_public_sop(auth: dict, name: str, node_name: str) -> int:
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": name,
            "contentType": "SHORT_VIDEO",
            "marketingPlan": "LIVE_PUBLIC",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": node_name,
                    "nodeType": "CONTENT_GENERATION",
                    "documentType": "COPY",
                    "ownerRole": "R6",
                }
            ],
        },
    )
    assert sop.json()["code"] == 0
    return int(sop.json()["data"]["id"])


def test_work_task_confirm_pins_sop_when_several_public_enabled():
    """多条启用公推 SOP 时，未指定不抢最新一条；指定 sopId 只出该模板的节点。"""
    auth = headers()
    ip_group_id, author_id = seed_work_task_context()
    older_id = _post_public_sop(auth, "公推甲", "节点甲")
    newer_id = _post_public_sop(auth, "公推乙", "节点乙")
    assert newer_id > older_id

    sheet = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": ip_group_id, "workDate": "2026-10-09"},
    )
    assert sheet.json()["code"] == 0
    sheet_id = sheet.json()["data"]["id"]
    payload = {
        "ipGroupId": ip_group_id,
        "workDate": "2026-10-09",
        "assignments": [
            {
                "rowNo": 1,
                "authorId": author_id,
                "workDate": "2026-10-09",
                "marketingPlan": "LIVE_PUBLIC",
                "competitions": [{"competitionId": "M-PIN", "competitionName": "隔离赛"}],
            }
        ],
    }
    saved = client.post("/admin-api/ims/content/work-task/sheet", headers=auth, json=payload)
    assert saved.json()["code"] == 0
    assignment_id = saved.json()["data"]["assignments"][0]["id"]
    ambiguous = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/confirm",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert ambiguous.json()["code"] == 1502

    payload["assignments"][0]["sopId"] = older_id
    pinned = client.post("/admin-api/ims/content/work-task/sheet", headers=auth, json=payload)
    assert pinned.json()["code"] == 0
    assert pinned.json()["data"]["assignments"][0]["sopId"] == older_id
    confirm = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/confirm",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert confirm.json()["code"] == 0
    assert confirm.json()["data"]["generatedTaskCount"] == 1
    assert confirm.json()["data"]["sheetId"] == sheet_id
    assert confirm.json()["data"]["confirmedAt"]

    tasks = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={"onlyMine": False, "ipGroupId": ip_group_id, "workDate": "2026-10-09", "pageSize": 20},
    )
    names = [row["nodeName"] for row in tasks.json()["data"]["list"]]
    assert names == ["节点甲"]

    withdraw = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/withdraw",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert withdraw.json()["code"] == 0
    assert withdraw.json()["data"]["assignments"][0]["rowStatus"] == "DRAFT"
    assert withdraw.json()["data"]["assignments"][0]["generatedTaskIds"] == []


def test_task_execute_content_gate_and_crud():
    """#35 · 工作任务确认 → CONTENT_GENERATION 执行/提审/审过 → 任务 DONE"""
    auth = headers()
    ip_group_id, author_id = seed_work_task_context()
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "任务流 SOP",
            "contentType": "SHORT_VIDEO",
            "marketingPlan": "LIVE_PUBLIC",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "写文案",
                    "nodeType": "CONTENT_GENERATION",
                    "documentType": "COPY",
                    "ownerRole": "R6",
                },
                {"nodeOrder": 2, "nodeName": "校对", "nodeType": "NORMAL", "ownerRole": "R6"},
            ],
        },
    )
    assert sop.json()["code"] == 0

    sheet = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": ip_group_id, "workDate": "2026-10-07"},
    )
    sheet_id = sheet.json()["data"]["id"]
    save = client.post(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        json={
            "ipGroupId": ip_group_id,
            "workDate": "2026-10-07",
            "assignments": [
                {
                    "rowNo": 1,
                    "authorId": author_id,
                    "workDate": "2026-10-07",
                    "marketingPlan": "LIVE_PUBLIC",
                    "competitions": [{"competitionId": "M100", "competitionName": "周末赛"}],
                }
            ],
        },
    )
    assignment_id = save.json()["data"]["assignments"][0]["id"]
    confirm = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/confirm",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert confirm.json()["code"] == 0
    task_ids = save.json()["data"]["assignments"][0].get("generatedTaskIds") or []
    if not task_ids:
        again = client.get(
            "/admin-api/ims/content/work-task/sheet",
            headers=auth,
            params={"ipGroupId": ip_group_id, "workDate": "2026-10-07"},
        )
        task_ids = again.json()["data"]["assignments"][0]["generatedTaskIds"]
    cg_task_id = task_ids[0]

    mine = client.get(
        "/admin-api/ims/content/task/page",
        headers=auth,
        params={"onlyMine": True, "pageSize": 20},
    )
    assert mine.json()["code"] == 0
    assert mine.json()["data"]["total"] >= 2

    blocked = client.post(
        f"/admin-api/ims/content/task/{cg_task_id}/execute/complete",
        headers=auth,
        json={},
    )
    assert blocked.json()["code"] == 1500

    execute = client.get(f"/admin-api/ims/content/task/{cg_task_id}/execute", headers=auth)
    assert execute.json()["code"] == 0
    assert execute.json()["data"]["nodeType"] == "CONTENT_GENERATION"
    project_id = execute.json()["data"]["linkedContent"]["id"]

    update = client.put(
        f"/admin-api/ims/content/{project_id}",
        headers=auth,
        json={
            "title": "周末赛文案",
            "matchType": 1,
            "matchScheme": [
                {
                    "matchId": "1001",
                    "homeName": "主队",
                    "awayName": "客队",
                    "matchPlays": [],
                }
            ],
        },
    )
    assert update.json()["code"] == 0
    assert update.json()["data"]["matchSummary"]

    from app.core import SessionLocal

    db_fix = SessionLocal()
    try:
        proj = db_fix.get(ContentProject, project_id)
        proj.submitter_user_id = 9001
        db_fix.commit()
    finally:
        db_fix.close()

    submit = client.post(f"/admin-api/ims/content/{project_id}/submit-review", headers=auth)
    assert submit.json()["code"] == 0
    review_no = submit.json()["data"]["reviewNo"]

    pass_all_pending_reviews(auth, project_id)

    done = client.post(
        f"/admin-api/ims/content/task/{cg_task_id}/execute/complete",
        headers=auth,
        json={},
    )
    assert done.json()["code"] == 0
    assert done.json()["data"]["status"] == "DONE"

    normal_task_id = task_ids[1]
    need_note = client.put(
        f"/admin-api/ims/content/task/{normal_task_id}/complete",
        headers=auth,
        json={"deliverables": ""},
    )
    assert need_note.json()["code"] == 1500

    normal_done = client.put(
        f"/admin-api/ims/content/task/{normal_task_id}/complete",
        headers=auth,
        json={"deliverables": "校对完成"},
    )
    assert normal_done.json()["code"] == 0

    listing = client.get("/admin-api/ims/content", headers=auth, params={"pageSize": 5})
    assert listing.json()["code"] == 0
    assert listing.json()["data"]["total"] >= 1


def _sop_nodes(name_a: str = "脚本", name_b: str = "发布", preds_b: list[int] | None = None, preds_a: list[int] | None = None):
    return [
        {
            "nodeOrder": 1,
            "nodeName": name_a,
            "standardDesc": "脚本标准",
            "ownerRole": "R6",
            "slaHours": 24,
            "nodeType": "NORMAL",
            "predecessors": preds_a or [],
        },
        {
            "nodeOrder": 2,
            "nodeName": name_b,
            "standardDesc": "发布标准",
            "ownerRole": "R8",
            "slaHours": 8,
            "nodeType": "CONTENT_PUBLISH",
            "predecessors": [1] if preds_b is None else preds_b,
            "parallelGroup": "PUSH",
        },
    ]


def test_sop_version_delete_and_dag():
    """#101 · SOP 新版本 / 逻辑删除 / DAG 环与执行岗位"""
    auth = headers()
    created = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "DAG 标准 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": _sop_nodes(),
        },
    )
    assert created.json()["code"] == 0
    sop_id = created.json()["data"]["id"]
    assert created.json()["data"]["version"] == 1
    assert created.json()["data"]["status"] == "ENABLED"
    assert created.json()["data"]["nodeCount"] == 2

    nodes = client.get(f"/admin-api/ims/content/sop/{sop_id}/nodes", headers=auth)
    assert nodes.json()["code"] == 0
    body = nodes.json()["data"]
    assert body[1]["predecessors"] == [1]
    assert body[1]["parallelGroup"] == "PUSH"
    assert body[1]["nodeType"] == "CONTENT_PUBLISH"

    cycle = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "成环 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": _sop_nodes(preds_a=[2], preds_b=[1]),
        },
    )
    assert cycle.json()["code"] == 1500
    assert "环" in cycle.json()["msg"]

    missing_role = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "缺岗位 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "脚本",
                    "ownerRole": "",
                    "nodeType": "NORMAL",
                    "slaHours": 24,
                }
            ],
        },
    )
    assert missing_role.json()["code"] == 1500
    assert "执行岗位" in missing_role.json()["msg"]

    missing_doc = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "缺文档类型 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "成稿",
                    "ownerRole": "R6",
                    "nodeType": "CONTENT_GENERATION",
                    "documentType": "",
                    "slaHours": 24,
                }
            ],
        },
    )
    assert missing_doc.json()["code"] == 1500

    updated = client.put(
        f"/admin-api/ims/content/sop/{sop_id}",
        headers=auth,
        json={
            "sopName": "DAG 标准 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": _sop_nodes(name_b="发布v2"),
        },
    )
    assert updated.json()["code"] == 0
    new_id = updated.json()["data"]["id"]
    assert new_id != sop_id
    assert updated.json()["data"]["version"] == 2
    assert updated.json()["data"]["status"] == "ENABLED"

    listed = client.get("/admin-api/ims/content/sop/list", headers=auth, params={"keyword": "DAG 标准 SOP"})
    assert listed.json()["code"] == 0
    by_id = {row["id"]: row for row in listed.json()["data"]["list"]}
    assert by_id[sop_id]["status"] == "DISABLED"
    assert by_id[sop_id]["version"] == 1
    assert by_id[new_id]["version"] == 2

    new_nodes = client.get(f"/admin-api/ims/content/sop/{new_id}/nodes", headers=auth)
    assert new_nodes.json()["data"][1]["nodeName"] == "发布v2"
    old_nodes = client.get(f"/admin-api/ims/content/sop/{sop_id}/nodes", headers=auth)
    assert old_nodes.json()["data"][1]["nodeName"] == "发布"

    no_confirm = client.delete(f"/admin-api/ims/content/sop/{new_id}", headers=auth)
    assert no_confirm.json()["code"] == 1500
    removed = client.delete(
        f"/admin-api/ims/content/sop/{new_id}",
        headers=auth,
        params={"confirmText": "DELETE"},
    )
    assert removed.json()["code"] == 0
    gone = client.get(f"/admin-api/ims/content/sop/{new_id}/nodes", headers=auth)
    assert gone.json()["code"] == 1504
    still = client.get(f"/admin-api/ims/content/sop/{sop_id}/nodes", headers=auth)
    assert still.json()["code"] == 0
    assert len(still.json()["data"]) == 2


def test_review_drawer_preview_steps_and_reject_remark():
    auth = headers()
    from app.core import SessionLocal

    db = SessionLocal()
    try:
        project = ContentProject(
            title="版式待审",
            body="纯文本兜底不应盖过版式",
            layout_html="<section><p>版式正文先看</p><script>alert(1)</script></section>",
            document_type="ARTICLE",
            content_type="ARTICLE",
            match_summary="英超 · 阿森纳 VS 切尔西",
            review_passed=0,
            submitter_user_id=9001,
            creator=9001,
            tenant_id=0,
            content_status="PENDING_REVIEW",
        )
        db.add(project)
        db.flush()
        review = ContentReview(
            review_no="RV202610090116",
            content_project_id=project.id,
            content_title=project.title,
            submitter_user_id=9001,
            review_round=1,
            creator=1,
            tenant_id=0,
        )
        db.add(review)
        db.commit()
        review_no = review.review_no
    finally:
        db.close()

    detail = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth)
    payload = detail.json()
    assert payload["code"] == 0
    preview = payload["data"]["preview"]
    assert "版式正文先看" in preview["layoutHtml"]
    assert preview["body"] == "纯文本兜底不应盖过版式"
    assert preview["documentType"] == "ARTICLE"
    assert preview["contentType"] == "ARTICLE"
    assert preview["matchSummary"] == "英超 · 阿森纳 VS 切尔西"
    steps = payload["data"]["reviewSteps"]
    assert [step["round"] for step in steps] == [1, 2]
    assert steps[0]["label"].startswith("运营组长：")
    assert steps[0]["status"] == "CURRENT"
    assert steps[1]["label"].startswith("运营总监：")
    assert steps[1]["status"] == "PENDING"

    missing_items = client.put(
        f"/admin-api/ims/content/review/{review_no}/conclusion",
        headers=auth,
        json={"conclusion": "REJECT_BACK", "checklistResult": {"COMPLIANCE": False}, "remark": "缺结构化项"},
    )
    assert missing_items.json()["code"] == 1058

    missing_remark = client.put(
        f"/admin-api/ims/content/review/{review_no}/conclusion",
        headers=auth,
        json={
            "conclusion": "REJECT_BACK",
            "checklistResult": {"COMPLIANCE": False, "QUALITY": True, "BRAND": True},
            "rejectItems": [{"itemCode": "COMPLIANCE", "reason": ""}],
        },
    )
    assert missing_remark.json()["code"] == 1500

    rejected = client.put(
        f"/admin-api/ims/content/review/{review_no}/conclusion",
        headers=auth,
        json={
            "conclusion": "REJECT_BACK",
            "checklistResult": {"COMPLIANCE": False, "QUALITY": True, "BRAND": True},
            "rejectItems": [{"itemCode": "COMPLIANCE", "reason": ""}],
            "remark": "标题与正文不符，请先改正文",
        },
    )
    assert rejected.json()["code"] == 0

    again = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth)
    data = again.json()["data"]
    assert data["conclusion"] == "REJECT_BACK"
    assert data["remark"] == "标题与正文不符，请先改正文"
    assert data["rejectItems"][0]["reason"] == "标题与正文不符，请先改正文"
    assert data["reviewSteps"][0]["status"] == "DONE"
    assert data["reviewSteps"][0]["remark"] == "标题与正文不符，请先改正文"


def test_review_detail_exposes_readonly_match_sessions():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "审核场次只读",
            "matchType": 2,
            "matchScheme": [
                {
                    "matchId": "88001",
                    "className": "英超",
                    "homeName": "曼联",
                    "awayName": "切尔西",
                    "matchTime": "2026-10-09 20:00",
                    "mainPlayMethod": "胜平负",
                    "matchPlays": [{"result": "胜"}],
                },
                {
                    "matchId": "88002",
                    "className": "西甲",
                    "homeName": "皇马",
                    "awayName": "巴萨",
                    "mainPlayMethod": "让球",
                    "matchPlays": [],
                },
            ],
        },
    )
    assert created.json()["code"] == 0
    project_id = created.json()["data"]["id"]
    submit = client.post(f"/admin-api/ims/content/{project_id}/submit-review", headers=auth)
    assert submit.json()["code"] == 0
    review_no = submit.json()["data"]["reviewNo"]

    detail = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth)
    body = detail.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["matchType"] == 2
    assert data["matchSummary"] == "2场"
    assert len(data["matchScheme"]) == 2
    assert data["matchScheme"][0]["homeName"] == "曼联"
    assert data["matchScheme"][0]["awayName"] == "切尔西"
    assert data["matchScheme"][0]["mainPlayMethod"] == "胜平负"
    assert data["checklist"]

    queue = client.get("/admin-api/ims/content/review/queue", headers=auth, params={"pageSize": 50})
    row = next(item for item in queue.json()["data"]["list"] if item["reviewNo"] == review_no)
    assert row["matchSummary"] == "2场"
    assert "matchScheme" not in row

    legacy = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "旧赛事名",
            "matchScheme": [],
            "competitionName": "英超 · 阿森纳 vs 切尔西",
        },
    )
    assert legacy.json()["code"] == 0
    legacy_id = legacy.json()["data"]["id"]
    legacy_submit = client.post(f"/admin-api/ims/content/{legacy_id}/submit-review", headers=auth)
    assert legacy_submit.json()["code"] == 0
    legacy_no = legacy_submit.json()["data"]["reviewNo"]
    legacy_detail = client.get(f"/admin-api/ims/content/review/{legacy_no}", headers=auth).json()["data"]
    assert legacy_detail["matchScheme"] == []
    assert legacy_detail["competitionName"] == "英超 · 阿森纳 vs 切尔西"
    assert legacy_detail["matchSummary"] == "英超 · 阿森纳 vs 切尔西"
