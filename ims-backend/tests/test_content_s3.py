import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import ContentProject, ContentTask, User

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def admin_user() -> tuple[int, int]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin", User.deleted == 0).one()
        return user.id, user.tenant_id or 0
    finally:
        db.close()


def test_partial_update_keeps_document_type_and_scheme():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "保留字段",
            "documentType": "COPY",
            "body": "原文",
            "matchType": 1,
            "matchScheme": [{"matchId": "1", "homeName": "主", "awayName": "客", "matchPlays": []}],
        },
    )
    assert created.json()["code"] == 0
    cid = created.json()["data"]["id"]
    assert created.json()["data"]["documentType"] == "COPY"
    assert created.json()["data"]["matchSummary"] == "主 VS 客"

    updated = client.put(
        f"/admin-api/ims/content/{cid}",
        headers=auth,
        json={"title": "只改标题"},
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"]["documentType"] == "COPY"
    assert updated.json()["data"]["body"] == "原文"
    assert updated.json()["data"]["matchSummary"] == "主 VS 客"


def test_delete_draft_ok_and_pending_blocked():
    auth = headers()
    draft = client.post("/admin-api/ims/content", headers=auth, json={"title": "可删草稿", "body": "x"})
    draft_id = draft.json()["data"]["id"]
    deleted = client.delete(f"/admin-api/ims/content/{draft_id}", headers=auth)
    assert deleted.json()["code"] == 0
    gone = client.get(f"/admin-api/ims/content/{draft_id}", headers=auth)
    assert gone.json()["code"] == 1504

    pending = client.post("/admin-api/ims/content", headers=auth, json={"title": "已提审", "body": "y"})
    pid = pending.json()["data"]["id"]
    submit = client.post(f"/admin-api/ims/content/{pid}/submit-review", headers=auth)
    assert submit.json()["code"] == 0
    blocked = client.delete(f"/admin-api/ims/content/{pid}", headers=auth)
    assert blocked.json()["code"] == 1502


def test_retry_ai_generate_requeues():
    auth = headers()
    created = client.post("/admin-api/ims/content", headers=auth, json={"title": "AI 重试"})
    cid = created.json()["data"]["id"]
    db = SessionLocal()
    try:
        row = db.get(ContentProject, cid)
        row.ai_generate_status = "FAILED"
        row.ai_generate_error = "timeout"
        db.commit()
    finally:
        db.close()

    retry = client.post(f"/admin-api/ims/content/{cid}/retry-ai-generate", headers=auth)
    assert retry.json()["code"] == 0
    assert retry.json()["data"]["aiGenerateStatus"] == "QUEUED"
    detail = client.get(f"/admin-api/ims/content/{cid}", headers=auth)
    assert detail.json()["data"]["aiGenerateStatus"] == "QUEUED"
    assert detail.json()["data"]["aiGenerateError"] in (None, "")


def test_execute_save_keeps_user_attachments():
    auth = headers()
    uid, tid = admin_user()
    db = SessionLocal()
    try:
        task = ContentTask(
            assignment_id=0,
            sop_id=0,
            sop_node_id=0,
            ip_group_id=0,
            author_id=0,
            assignee_user_id=uid,
            node_name="附件节点",
            node_type="NORMAL",
            task_status="IN_PROGRESS",
            user_attachments=[{"fileKey": "k1", "fileName": "brief.pdf"}],
            tenant_id=tid,
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    saved = client.post(
        f"/admin-api/ims/content/task/{task_id}/execute/save",
        headers=auth,
        json={"deliverables": "只保存说明"},
    )
    assert saved.json()["code"] == 0
    execute = client.get(f"/admin-api/ims/content/task/{task_id}/execute", headers=auth)
    body = execute.json()["data"]
    assert body["deliverables"] == "只保存说明"
    atts = body["userAttachments"]
    assert len(atts) == 1
    assert atts[0]["fileKey"] == "k1"
    assert atts[0]["fileName"] == "brief.pdf"


def test_list_complete_gate_and_task_bound_create():
    auth = headers()
    uid, tid = admin_user()
    db = SessionLocal()
    try:
        task = ContentTask(
            assignment_id=0,
            sop_id=0,
            sop_node_id=0,
            ip_group_id=0,
            author_id=0,
            assignee_user_id=uid,
            node_name="生成节点",
            node_type="CONTENT_GENERATION",
            task_status="PENDING",
            tenant_id=tid,
        )
        db.add(task)
        db.commit()
        task_id = task.id
    finally:
        db.close()

    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "任务带入", "taskId": task_id, "body": "草稿", "documentType": "COPY"},
    )
    assert created.json()["code"] == 0
    cid = created.json()["data"]["id"]
    again = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "重复", "taskId": task_id},
    )
    assert again.json()["code"] == 1502

    execute = client.get(f"/admin-api/ims/content/task/{task_id}/execute", headers=auth)
    assert execute.json()["data"]["linkedContent"]["id"] == cid
    assert execute.json()["data"]["status"] == "IN_PROGRESS"

    blocked = client.put(f"/admin-api/ims/content/task/{task_id}/complete", headers=auth, json={})
    assert blocked.json()["code"] == 1500

    db = SessionLocal()
    try:
        row = db.get(ContentProject, cid)
        row.content_status = "PENDING_PUBLISH"
        row.review_passed = 1
        db.commit()
    finally:
        db.close()

    done = client.put(f"/admin-api/ims/content/task/{task_id}/complete", headers=auth, json={})
    assert done.json()["code"] == 0
    assert done.json()["data"]["status"] == "DONE"
