import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import ContentProject, ContentReview
from app.ops_db import ops_session
from app.ops_models import Company, IpGroup, PlatformAccount, Realname
from app.crypto import encrypt_text

client = TestClient(app)

CHECKLIST_PASS = {"COMPLIANCE": True, "QUALITY": True, "BRAND": True}


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def seed_account() -> int:
    ops = ops_session()
    try:
        company = Company(company_name="清单公司", status="ENABLED", tenant_id=0)
        group = IpGroup(group_name="清单组", status="ENABLED", tenant_id=0)
        person = Realname(
            real_name="王五",
            id_type="ID_CARD",
            id_card_enc=encrypt_text("330101199001011240"),
            phone_enc=encrypt_text("13800003333"),
            status="ENABLED",
            tenant_id=0,
        )
        ops.add_all([company, group, person])
        ops.flush()
        account = PlatformAccount(
            account_no="AC-TAIL-01",
            account_name="清单号",
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


def seed_pending_review(title: str = "清单短视频") -> tuple[int, str]:
    db = SessionLocal()
    try:
        project = ContentProject(
            title=title,
            content_type="SHORT_VIDEO",
            platform_type="DOUYIN",
            document_type="COPY",
            review_passed=0,
            submitter_user_id=9001,
            creator=9001,
            tenant_id=0,
        )
        db.add(project)
        db.flush()
        review = ContentReview(
            review_no=f"RVTAIL{project.id}",
            content_project_id=project.id,
            content_title=project.title,
            submitter_user_id=9001,
            review_round=1,
            creator=1,
            tenant_id=0,
        )
        db.add(review)
        db.commit()
        return project.id, review.review_no
    finally:
        db.close()


def pass_review(auth: dict, review_no: str, checklist: dict | None = None) -> dict:
    res = client.put(
        f"/admin-api/ims/content/review/{review_no}/conclusion",
        headers=auth,
        json={"conclusion": "PASS", "checklistResult": checklist or CHECKLIST_PASS},
    )
    return res.json()


def pending_review_no(auth: dict, project_id: int) -> str | None:
    queue = client.get("/admin-api/ims/content/review/queue", headers=auth)
    assert queue.json()["code"] == 0
    for row in queue.json()["data"]["list"]:
        if row.get("contentProjectId") == project_id:
            return row["reviewNo"]
    return None


def test_content_list_filters_type_platform_and_document():
    auth = headers()
    video = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "筛选短视频",
            "contentType": "SHORT_VIDEO",
            "platformType": "DOUYIN",
            "documentType": "COPY",
            "body": "短视频正文",
        },
    )
    article = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "筛选图文",
            "contentType": "ARTICLE",
            "platformType": "KUAISHOU",
            "documentType": "SCRIPT",
            "body": "图文正文",
        },
    )
    assert video.json()["code"] == 0
    assert article.json()["code"] == 0

    by_type = client.get("/admin-api/ims/content", headers=auth, params={"contentType": "ARTICLE"})
    titles = [row["title"] for row in by_type.json()["data"]["list"]]
    assert "筛选图文" in titles
    assert "筛选短视频" not in titles

    by_platform = client.get("/admin-api/ims/content", headers=auth, params={"platformType": "DOUYIN"})
    platform_titles = [row["title"] for row in by_platform.json()["data"]["list"]]
    assert "筛选短视频" in platform_titles
    assert "筛选图文" not in platform_titles

    by_doc = client.get("/admin-api/ims/content", headers=auth, params={"documentType": "SCRIPT", "title": "筛选"})
    doc_titles = [row["title"] for row in by_doc.json()["data"]["list"]]
    assert doc_titles == ["筛选图文"]


def test_publish_checklist_blocks_partial_pass_and_empty_caption_then_overdue_todo():
    auth = headers()
    account_id = seed_account()
    project_id, review_no = seed_pending_review()

    partial = pass_review(auth, review_no, {"COMPLIANCE": True, "QUALITY": True, "BRAND": False})
    assert partial["code"] == 1500
    assert "质量清单" in partial["msg"]

    detail = client.get(f"/admin-api/ims/content/{project_id}", headers=auth)
    assert detail.json()["code"] == 0
    codes = {item["itemCode"]: item["passed"] for item in detail.json()["data"]["publishChecklist"]}
    assert codes["REVIEW_PASSED"] is False
    assert codes["BRAND"] is False

    assert pass_review(auth, review_no)["code"] == 0
    review_l2 = pending_review_no(auth, project_id)
    assert review_l2 is not None
    assert pass_review(auth, review_l2)["code"] == 0

    ready = client.get(f"/admin-api/ims/content/{project_id}", headers=auth).json()["data"]["publishChecklist"]
    ready_codes = {item["itemCode"]: item["passed"] for item in ready}
    assert ready_codes["REVIEW_PASSED"] is True
    assert ready_codes["COMPLIANCE"] is True
    assert ready_codes["CAPTION"] is False

    missing_caption = client.post(
        "/admin-api/ims/content/publish",
        headers=auth,
        json={
            "contentProjectId": project_id,
            "accountId": account_id,
            "platform": "DOUYIN",
            "planPublishAt": "2026-10-01T18:00:00+08:00",
            "caption": "",
        },
    )
    assert missing_caption.json()["code"] == 1054
    assert "文案或正文" in missing_caption.json()["msg"]

    publish = client.post(
        "/admin-api/ims/content/publish",
        headers=auth,
        json={
            "contentProjectId": project_id,
            "accountId": account_id,
            "platform": "DOUYIN",
            "planPublishAt": "2026-10-01T18:00:00+08:00",
            "caption": "清单文案",
        },
    )
    body = publish.json()
    assert body["code"] == 0
    assert body["data"]["receiptOverdue"] is True
    publish_id = body["data"]["id"]
    publish_no = body["data"]["publishNo"]

    logs = client.get(
        "/admin-api/ims/system/operate-log/page",
        headers=auth,
        params={"module": "内容", "keyword": "publish", "pageSize": 20},
    )
    actions = [row["action"] for row in logs.json()["data"]["list"]]
    assert "新增发布单" in actions
    assert all(row["module"] == "内容" for row in logs.json()["data"]["list"])

    pending = client.get("/admin-api/ims/content/publish/pending", headers=auth, params={"overdueOnly": True})
    assert any(row["publishNo"] == publish_no for row in pending.json()["data"]["list"])
    again = client.get("/admin-api/ims/content/publish/pending", headers=auth, params={"overdueOnly": True})
    assert again.json()["code"] == 0

    todos = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"status": "PENDING", "pageSize": 50},
    )
    matched = [row for row in todos.json()["data"]["list"] if row["title"] == f"发布督办：{publish_no}"]
    assert len(matched) == 1
    assert matched[0]["taskType"] == "content_publish"
    assert matched[0]["overdue"] is True

    messages = client.get("/admin-api/ims/auth/workbench/messages", headers=auth, params={"pageSize": 50})
    assert any(row["title"] == f"发布督办：{publish_no}" for row in messages.json()["data"]["list"])

    receipt = client.put(
        f"/admin-api/ims/content/publish/{publish_id}/receipt",
        headers=auth,
        json={"publishUrl": "https://example.com/tail", "publishedAt": "2026-10-08T20:00:00+08:00"},
    )
    assert receipt.json()["code"] == 0
    left = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"status": "PENDING", "pageSize": 50},
    )
    assert all(row["title"] != f"发布督办：{publish_no}" for row in left.json()["data"]["list"])
