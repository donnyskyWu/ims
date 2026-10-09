"""工作任务确认后自动文案草稿：状态、幂等、失败重试、只写 body。"""

import os
import uuid

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_CONTENT_AI_STUB", None)
os.environ.pop("IMS_CONTENT_AI_BASE_URL", None)

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.main import app
from app.models import ContentReview
from app.settings_runtime import invalidate_param_cache
from tests.test_content import headers, seed_work_task_context

client = TestClient(app)


def _set_param(auth: dict, key: str, value) -> None:
    saved = client.put(
        "/admin-api/ims/system/param",
        headers=auth,
        json={"paramKey": key, "paramValue": value},
    )
    assert saved.json()["code"] == 0, saved.json()
    invalidate_param_cache()


def _confirm_sheet(auth: dict, *, auto_ai: bool) -> dict:
    _set_param(auth, "work.task.confirm.auto-ai-generate", auto_ai)
    ip_group_id, author_id = seed_work_task_context()
    label = uuid.uuid4().hex[:8]
    work_date = f"2026-11-{(uuid.uuid4().int % 27) + 1:02d}"
    node_name = f"写文案-{label}"
    competition = f"选题赛-{label}"
    sop = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": f"自动草稿 SOP {label}",
            "contentType": "SHORT_VIDEO",
            "marketingPlan": "LIVE_PUBLIC",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": node_name,
                    "nodeType": "CONTENT_GENERATION",
                    "documentType": "COPY",
                    "ownerRole": "R6",
                    "standardDesc": "按选题写复盘",
                },
                {"nodeOrder": 2, "nodeName": f"校对-{label}", "nodeType": "NORMAL", "ownerRole": "R6"},
            ],
        },
    )
    assert sop.json()["code"] == 0, sop.json()
    sheet = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": ip_group_id, "workDate": work_date},
    )
    assert sheet.json()["code"] == 0, sheet.json()
    sheet_id = sheet.json()["data"]["id"]
    save = client.post(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        json={
            "ipGroupId": ip_group_id,
            "workDate": work_date,
            "assignments": [
                {
                    "rowNo": 1,
                    "authorId": author_id,
                    "workDate": work_date,
                    "marketingPlan": "LIVE_PUBLIC",
                    "competitions": [
                        {
                            "competitionId": f"C-{label}",
                            "competitionName": competition,
                            "leagueName": "联赛A",
                        }
                    ],
                }
            ],
        },
    )
    assert save.json()["code"] == 0, save.json()
    assignment_id = save.json()["data"]["assignments"][0]["id"]
    confirm = client.post(
        f"/admin-api/ims/content/work-task/{sheet_id}/confirm",
        headers=auth,
        json={"assignmentIds": [assignment_id]},
    )
    assert confirm.json()["code"] == 0, confirm.json()
    again = client.get(
        "/admin-api/ims/content/work-task/sheet",
        headers=auth,
        params={"ipGroupId": ip_group_id, "workDate": work_date},
    )
    task_ids = again.json()["data"]["assignments"][0]["generatedTaskIds"]
    return {
        "auth": auth,
        "sheet_id": sheet_id,
        "assignment_id": assignment_id,
        "task_ids": task_ids,
        "node_name": node_name,
        "competition": competition,
        "confirm": confirm.json()["data"],
    }


def _project(auth: dict, task_id: int) -> dict:
    execute = client.get(f"/admin-api/ims/content/task/{task_id}/execute", headers=auth)
    assert execute.json()["code"] == 0, execute.json()
    linked = execute.json()["data"]["linkedContent"]
    assert linked
    detail = client.get(f"/admin-api/ims/content/{linked['id']}", headers=auth)
    assert detail.json()["code"] == 0, detail.json()
    return detail.json()["data"]


def _review_count(project_id: int) -> int:
    db = SessionLocal()
    try:
        return (
            db.query(ContentReview)
            .filter(ContentReview.content_project_id == project_id, ContentReview.deleted == 0)
            .count()
        )
    finally:
        db.close()


def test_confirm_without_switch_does_not_generate(monkeypatch):
    monkeypatch.delenv("IMS_CONTENT_AI_STUB", raising=False)
    auth = headers()
    ctx = _confirm_sheet(auth, auto_ai=False)
    assert ctx["confirm"]["autoAiGenerate"] is False
    assert ctx["confirm"]["generatedTaskCount"] == 2
    project = _project(auth, ctx["task_ids"][0])
    assert project["aiGenerateStatus"] in (None, "")
    assert project["body"] in (None, "")
    assert project["contentStatus"] == "DRAFT"
    assert project["layoutHtml"] in (None, "")
    normal = client.get(f"/admin-api/ims/content/task/{ctx['task_ids'][1]}/execute", headers=auth)
    assert normal.json()["data"]["nodeType"] == "NORMAL"
    assert normal.json()["data"]["linkedContent"] is None


def test_confirm_writes_draft_once_and_skips_layout_and_review(monkeypatch):
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "success")
    calls = {"n": 0}
    from app.content_ai_draft import generate_copy as real_generate

    def wrapped(**kwargs):
        calls["n"] += 1
        assert "不排版" in kwargs["prompt"] or "不要排版" in kwargs["prompt"]
        return real_generate(**kwargs)

    monkeypatch.setattr("app.content_ai_draft.generate_copy", wrapped)
    auth = headers()
    ctx = _confirm_sheet(auth, auto_ai=True)
    assert ctx["confirm"]["autoAiGenerate"] is True
    assert calls["n"] == 1
    project = _project(auth, ctx["task_ids"][0])
    assert project["aiGenerateStatus"] == "GENERATED"
    assert project["contentStatus"] == "DRAFT"
    assert project["layoutHtml"] in (None, "")
    assert "layoutHtml" not in (project["body"] or "")
    assert ctx["competition"] in project["body"]
    assert ctx["node_name"] in project["body"]
    assert "按选题写复盘" in project["body"]
    assert "不改版式" in project["body"]
    assert project["documentType"] == "COPY"
    assert _review_count(project["id"]) == 0

    again = client.post(
        f"/admin-api/ims/content/work-task/{ctx['sheet_id']}/confirm",
        headers=auth,
        json={"assignmentIds": [ctx["assignment_id"]]},
    )
    assert again.json()["code"] == 0
    assert again.json()["data"]["generatedTaskCount"] == 0
    assert calls["n"] == 1

    retry = client.post(f"/admin-api/ims/content/{project['id']}/retry-ai-generate", headers=auth)
    assert retry.json()["code"] == 0
    assert retry.json()["data"]["aiGenerateStatus"] == "GENERATED"
    assert calls["n"] == 1
    kept = client.get(f"/admin-api/ims/content/{project['id']}", headers=auth).json()["data"]
    assert kept["body"] == project["body"]
    assert kept["contentStatus"] == "DRAFT"
    assert _review_count(project["id"]) == 0


def test_fail_then_retry_rewrites_body_only(monkeypatch):
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "fail")
    auth = headers()
    ctx = _confirm_sheet(auth, auto_ai=True)
    project = _project(auth, ctx["task_ids"][0])
    assert project["aiGenerateStatus"] == "FAILED"
    assert "失败" in (project["aiGenerateError"] or "")
    assert project["body"] in (None, "")
    assert project["contentStatus"] == "DRAFT"
    assert project["layoutHtml"] in (None, "")

    laid = client.put(
        f"/admin-api/ims/content/{project['id']}",
        headers=auth,
        json={"title": project["title"], "layoutHtml": "<section>keep-layout</section>"},
    )
    assert laid.json()["code"] == 0
    assert laid.json()["data"]["layoutHtml"] == "<section>keep-layout</section>"
    assert laid.json()["data"]["body"] in (None, "")

    blocked = client.post(f"/admin-api/ims/content/{project['id']}/retry-ai-generate", headers=auth)
    assert blocked.json()["code"] == 0
    assert blocked.json()["data"]["aiGenerateStatus"] == "FAILED"

    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "success")
    retried = client.post(f"/admin-api/ims/content/{project['id']}/retry-ai-generate", headers=auth)
    assert retried.json()["code"] == 0
    assert retried.json()["data"]["aiGenerateStatus"] == "GENERATED"
    detail = client.get(f"/admin-api/ims/content/{project['id']}", headers=auth).json()["data"]
    assert ctx["competition"] in detail["body"]
    assert detail["layoutHtml"] == "<section>keep-layout</section>"
    assert detail["contentStatus"] == "DRAFT"
    assert _review_count(project["id"]) == 0

    edited = client.put(
        f"/admin-api/ims/content/{project['id']}",
        headers=auth,
        json={"title": project["title"], "body": detail["body"] + "\n人工修订"},
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["body"].endswith("人工修订")
    assert edited.json()["data"]["layoutHtml"] == "<section>keep-layout</section>"
    assert edited.json()["data"]["contentStatus"] == "DRAFT"


def test_stub_mode_param_and_env_precedence(monkeypatch):
    monkeypatch.delenv("IMS_CONTENT_AI_STUB", raising=False)
    auth = headers()
    _set_param(auth, "content.ai.stubMode", "fail")
    ctx = _confirm_sheet(auth, auto_ai=True)
    failed = _project(auth, ctx["task_ids"][0])
    assert failed["aiGenerateStatus"] == "FAILED"

    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "success")
    auth2 = headers()
    ctx2 = _confirm_sheet(auth2, auto_ai=True)
    generated = _project(auth2, ctx2["task_ids"][0])
    assert generated["aiGenerateStatus"] == "GENERATED"
    assert ctx2["competition"] in generated["body"]


def test_retry_without_failure_is_rejected():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "无任务草稿", "body": "手写"},
    )
    assert created.json()["code"] == 0
    content_id = created.json()["data"]["id"]
    rejected = client.post(f"/admin-api/ims/content/{content_id}/retry-ai-generate", headers=auth)
    assert rejected.json()["code"] == 1502
    detail = client.get(f"/admin-api/ims/content/{content_id}", headers=auth).json()["data"]
    assert detail["body"] == "手写"
    assert detail["aiGenerateStatus"] in (None, "")
