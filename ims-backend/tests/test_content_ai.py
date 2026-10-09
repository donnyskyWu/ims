"""切片 #102：AI 文案 + ComfyUI 视频桩闭环。"""

from __future__ import annotations

import json
import os
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("IMS_DB", "ims_test")
os.environ.setdefault("IMS_OPS_DB", "ims_ops_test")

import pytest
from fastapi.testclient import TestClient

from app.comfyui_client import prompt_status, reset_stub as reset_video_stub
from app.comfyui_client import submit_prompt
from app.content_ai_client import STUB_COPY_V1, copy_status, reset_stub as reset_copy_stub
from app.content_ai_client import submit_copy
from app.content_ai_models import ContentAiJob, ContentWorkflow
from app.core import SessionLocal, utcnow
from app.main import app
from app.settings_runtime import invalidate_param_cache
from tests.test_content import seed_account

client = TestClient(app)
MATCH = [{"matchId": "1001", "homeName": "主队", "awayName": "客队", "matchPlays": []}]


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch):
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "1")
    monkeypatch.setenv("IMS_COMFYUI_STUB", "1")
    monkeypatch.delenv("IMS_CONTENT_GEN_STUB", raising=False)
    reset_copy_stub()
    reset_video_stub()
    invalidate_param_cache()


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def create_draft(auth: dict, title: str = "桩文案草稿") -> dict:
    res = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": title, "contentType": "SHORT_VIDEO", "matchType": 1, "matchScheme": MATCH, "body": "待生成"},
    )
    assert res.json()["code"] == 0, res.text
    return res.json()["data"]


def test_stub_copy_writes_draft_and_retry_hint():
    auth = headers()
    draft = create_draft(auth)
    res = client.post(
        "/admin-api/ims/content/script/generate",
        headers=auth,
        json={
            "topicId": draft["id"],
            "contentRequirement": "今晚这场怎么看",
            "scriptType": "MONOLOGUE",
            "candidateCount": 2,
        },
    )
    body = res.json()
    assert body["code"] == 0, body
    assert body["data"]["candidates"][0]["content"] == STUB_COPY_V1
    assert body["data"]["candidates"][0]["aiGenerated"] is True
    assert body["data"]["promptSnapshot"]
    detail = client.get(f"/admin-api/ims/content/{draft['id']}", headers=auth).json()["data"]
    assert detail["body"] == STUB_COPY_V1
    assert detail["aiGenerateStatus"] == "SUCCESS"
    assert detail["defaultWorkflowId"]
    assert "token" not in json.dumps(detail).lower() or "tokenSecret" not in json.dumps(detail)


def test_copy_fail_then_retry(monkeypatch):
    auth = headers()
    draft = create_draft(auth, "失败重试草稿")
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "fail")
    reset_copy_stub()
    failed = client.post(
        "/admin-api/ims/content/script/generate",
        headers=auth,
        json={
            "topicId": draft["id"],
            "contentRequirement": "失败用例",
            "scriptType": "STORY",
            "candidateCount": 2,
        },
    )
    assert failed.json()["code"] == 1001
    assert "重新发起" in failed.json()["msg"]
    detail = client.get(f"/admin-api/ims/content/{draft['id']}", headers=auth).json()["data"]
    assert detail["aiGenerateStatus"] == "FAILED"
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "1")
    reset_copy_stub()
    retried = client.post(f"/admin-api/ims/content/{draft['id']}/retry-ai-generate", headers=auth)
    assert retried.json()["code"] == 0, retried.text
    assert retried.json()["data"]["aiGenerateStatus"] == "SUCCESS"
    assert retried.json()["data"]["body"] == STUB_COPY_V1


def test_script_finalize_then_video_waiting_to_generating(monkeypatch):
    auth = headers()
    draft = create_draft(auth, "定稿后生产")
    generated = client.post(
        "/admin-api/ims/content/script/generate",
        headers=auth,
        json={
            "topicId": draft["id"],
            "contentRequirement": "定稿链路",
            "scriptType": "SALES_PITCH",
            "candidateCount": 2,
        },
    ).json()
    script_id = generated["data"]["candidates"][0]["id"]
    blocked = client.put(f"/admin-api/ims/content/script/{script_id}/finalize", headers=auth)
    assert blocked.json()["code"] == 1001
    edited = client.put(
        f"/admin-api/ims/content/script/{script_id}",
        headers=auth,
        json={"content": STUB_COPY_V1 + "\n人工润色一句。"},
    )
    assert edited.json()["code"] == 0
    new_id = edited.json()["data"]["id"]
    assert edited.json()["data"]["aiGenerated"] is False
    done = client.put(f"/admin-api/ims/content/script/{new_id}/finalize", headers=auth)
    assert done.json()["code"] == 0
    early = client.post(
        "/admin-api/ims/content/ai-production/task",
        headers=auth,
        json={"topicId": draft["id"], "scriptId": script_id, "requirement": "未定稿脚本", "workflowId": draft["defaultWorkflowId"]},
    )
    assert early.json()["code"] == 1053
    created = client.post(
        "/admin-api/ims/content/ai-production/task",
        headers=auth,
        json={
            "topicId": draft["id"],
            "scriptId": new_id,
            "requirement": "定稿后的成片要求",
            "workflowId": draft["defaultWorkflowId"],
        },
    )
    assert created.json()["code"] == 0, created.text
    assert created.json()["data"]["taskStatus"] == "WAITING"
    task_no = created.json()["data"]["taskNo"]
    submitted = client.post(
        "/admin-api/ims/content/ai-job/submit",
        headers=auth,
        json={
            "taskNo": task_no,
            "workflowId": draft["defaultWorkflowId"],
            "nodeName": "成片",
            "params": {"text": "定稿后的成片要求"},
            "priority": "P2",
        },
    )
    assert submitted.json()["code"] == 0, submitted.text
    assert submitted.json()["data"]["queueStatus"] == "WAITING"
    assert submitted.json()["data"]["gpuNode"] in (None, "")
    assert submitted.json()["data"]["provider"] == "stub"
    assert submitted.json()["data"]["preview"] is None
    assert "plain-token" not in submitted.text
    job_id = submitted.json()["data"]["id"]
    generating = client.get(f"/admin-api/ims/content/ai-job/{job_id}/status", headers=auth)
    assert generating.json()["code"] == 0
    assert generating.json()["data"]["queueStatus"] == "GENERATING"
    task = client.get(f"/admin-api/ims/content/ai-production/task/{task_no}", headers=auth).json()["data"]
    assert task["taskStatus"] == "GENERATING"
    success = client.get(f"/admin-api/ims/content/ai-job/{job_id}/status", headers=auth).json()
    assert success["code"] == 0
    assert success["data"]["queueStatus"] == "SUCCESS"
    assert success["data"]["resultFileKey"] == "stub/comfyui/stable-demo.mp4"
    assert success["data"]["provider"] == "stub"
    assert success["data"]["boundContentId"] == draft["id"]
    assert success["data"]["preview"]["ready"] is True
    assert success["data"]["preview"]["kind"] == "video"
    assert success["data"]["preview"]["fileKey"] == "stub/comfyui/stable-demo.mp4"
    finished = client.get(f"/admin-api/ims/content/ai-production/task/{task_no}", headers=auth).json()["data"]
    assert finished["taskStatus"] == "PENDING_FINAL_REVIEW"
    assert finished["outputFileUrl"] == "stub/comfyui/stable-demo.mp4"
    detail = client.get(f"/admin-api/ims/content/{draft['id']}", headers=auth).json()["data"]
    assert detail["videoJobStatus"] == "PENDING_FINAL_REVIEW"
    assert detail["videoFileKey"] == "stub/comfyui/stable-demo.mp4"


def test_review_reject_blocks_publish_then_pass(monkeypatch):
    auth = headers()
    account_id = seed_account()
    draft = create_draft(auth, "终审发布门禁")
    db = SessionLocal()
    try:
        from app.models import ContentProject

        row = db.get(ContentProject, draft["id"])
        row.review_passed = 1
        row.content_status = "PENDING_PUBLISH"
        db.commit()
    finally:
        db.close()
    created = client.post(
        "/admin-api/ims/content/ai-production/task",
        headers=auth,
        json={"topicId": draft["id"], "requirement": "成片", "workflowId": draft["defaultWorkflowId"]},
    )
    task_no = created.json()["data"]["taskNo"]
    ran = client.post(f"/admin-api/ims/content/ai-production/task/{task_no}/run", headers=auth)
    assert ran.json()["code"] == 0, ran.text
    assert ran.json()["data"]["taskStatus"] == "PENDING_FINAL_REVIEW"
    publish_body = {
        "contentProjectId": draft["id"],
        "accountId": account_id,
        "platform": "DOUYIN",
        "planPublishAt": "2026-10-09T18:00:00+08:00",
        "caption": "桩成片",
    }
    blocked = client.post("/admin-api/ims/content/publish", headers=auth, json=publish_body)
    assert blocked.json()["code"] == 1054
    rejected = client.put(
        f"/admin-api/ims/content/ai-production/task/{task_no}/review",
        headers=auth,
        json={"pass": False, "comment": "终审打回"},
    )
    assert rejected.json()["code"] == 0
    detail = client.get(f"/admin-api/ims/content/{draft['id']}", headers=auth).json()["data"]
    assert detail["videoJobStatus"] == "REVIEW_REJECTED"
    assert "重新发起" in (detail["videoRetryHint"] or "")
    still = client.post("/admin-api/ims/content/publish", headers=auth, json=publish_body)
    assert still.json()["code"] == 1054
    again = client.post(f"/admin-api/ims/content/ai-production/task/{task_no}/run", headers=auth)
    assert again.json()["code"] == 0, again.text
    assert again.json()["data"]["taskStatus"] == "PENDING_FINAL_REVIEW"
    passed = client.put(
        f"/admin-api/ims/content/ai-production/task/{task_no}/review",
        headers=auth,
        json={"pass": True},
    )
    assert passed.json()["code"] == 0
    published = client.post("/admin-api/ims/content/publish", headers=auth, json=publish_body)
    assert published.json()["code"] == 0, published.text
    assert published.json()["data"]["publishStatus"] == "PENDING_PUBLISH"


def test_chain_timeout_1056_then_rerun():
    auth = headers()
    draft = create_draft(auth, "超时重跑")
    created = client.post(
        "/admin-api/ims/content/ai-production/task",
        headers=auth,
        json={"topicId": draft["id"], "requirement": "超时", "workflowId": draft["defaultWorkflowId"]},
    )
    task_no = created.json()["data"]["taskNo"]
    submitted = client.post(
        "/admin-api/ims/content/ai-job/submit",
        headers=auth,
        json={
            "taskNo": task_no,
            "workflowId": draft["defaultWorkflowId"],
            "nodeName": "成片",
            "params": {"text": "超时"},
            "priority": "P1",
        },
    )
    job_id = submitted.json()["data"]["id"]
    db = SessionLocal()
    try:
        job = db.get(ContentAiJob, job_id)
        job.submitted_at = utcnow() - timedelta(minutes=61)
        db.commit()
    finally:
        db.close()
    timed = client.get(f"/admin-api/ims/content/ai-job/{job_id}/status", headers=auth)
    assert timed.json()["code"] == 1056
    assert "重新发起" in timed.json()["msg"]
    assert timed.json()["data"]["queueStatus"] == "FAILED"
    rerun = client.post(f"/admin-api/ims/content/ai-production/task/{task_no}/run", headers=auth)
    assert rerun.json()["code"] == 0, rerun.text
    assert rerun.json()["data"]["taskStatus"] == "PENDING_FINAL_REVIEW"


def test_illegal_node_and_param_schema_and_self_review():
    auth = headers()
    draft = create_draft(auth, "校验草稿")
    missing = client.post(
        "/admin-api/ims/content/ai-production/task",
        headers=auth,
        json={"requirement": "无工作流", "workflowId": 999999},
    )
    assert missing.json()["code"] == 1051
    created = client.post(
        "/admin-api/ims/content/ai-production/task",
        headers=auth,
        json={"topicId": draft["id"], "requirement": "节点", "workflowId": draft["defaultWorkflowId"]},
    )
    task_no = created.json()["data"]["taskNo"]
    bad_node = client.post(
        f"/admin-api/ims/content/ai-production/task/{task_no}/retry-node",
        headers=auth,
        json={"nodeName": "不存在的节点"},
    )
    assert bad_node.json()["code"] == 1055
    db = SessionLocal()
    try:
        wf = db.get(ContentWorkflow, draft["defaultWorkflowId"])
        wf.param_schema = {"required": ["prompt"]}
        db.commit()
        wf_id = wf.id
    finally:
        db.close()
    try:
        bad_params = client.post(
            "/admin-api/ims/content/ai-job/submit",
            headers=auth,
            json={
                "taskNo": task_no,
                "workflowId": wf_id,
                "nodeName": "成片",
                "params": {"text": "缺 prompt"},
                "priority": "P2",
            },
        )
        assert bad_params.json()["code"] == 1001
    finally:
        db = SessionLocal()
        try:
            wf = db.get(ContentWorkflow, draft["defaultWorkflowId"])
            wf.param_schema = {"required": []}
            db.commit()
        finally:
            db.close()
    no_match = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "无比赛", "matchScheme": [], "body": "x"},
    ).json()["data"]
    blocked = client.post(
        "/admin-api/ims/content/script/generate",
        headers=auth,
        json={"topicId": no_match["id"], "contentRequirement": "需要比赛", "scriptType": "MONOLOGUE", "candidateCount": 2},
    )
    assert blocked.json()["code"] == 1500
    project = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "回避审核", "matchScheme": MATCH, "body": "正文"},
    ).json()["data"]
    review = client.post(f"/admin-api/ims/content/{project['id']}/submit-review", headers=auth).json()
    assert review["code"] == 0
    conclusion = client.put(
        f"/admin-api/ims/content/review/{review['data']['reviewNo']}/conclusion",
        headers=auth,
        json={"conclusion": "PASS", "checklistResult": {"COMPLIANCE": True, "QUALITY": True, "BRAND": True}},
    )
    assert conclusion.json()["code"] == 1057


def test_provider_name_follows_stub_and_base_url(monkeypatch):
    from app.comfyui_client import provider_name

    assert provider_name() == "stub"
    monkeypatch.setenv("IMS_COMFYUI_STUB", "0")
    monkeypatch.delenv("IMS_COMFYUI_BASE_URL", raising=False)
    monkeypatch.delenv("IMS_CONTENT_GEN_STUB", raising=False)
    invalidate_param_cache()
    assert provider_name() == "unconfigured"
    monkeypatch.setenv("IMS_COMFYUI_BASE_URL", "http://comfy.example")
    invalidate_param_cache()
    assert provider_name() == "remote"


def test_content_detail_reports_stub_providers():
    auth = headers()
    draft = create_draft(auth, "桩状态草稿")
    assert draft["videoProvider"] == "stub"
    assert draft["aiCopyProvider"] == "stub"
    blob = json.dumps(draft)
    assert "tokenSecret" not in blob
    assert "baseUrl" not in blob
    assert "http://" not in blob


def test_content_detail_video_provider_unconfigured(monkeypatch):
    monkeypatch.setenv("IMS_COMFYUI_STUB", "0")
    monkeypatch.delenv("IMS_COMFYUI_BASE_URL", raising=False)
    monkeypatch.delenv("IMS_CONTENT_GEN_STUB", raising=False)
    invalidate_param_cache()
    auth = headers()
    draft = create_draft(auth, "未配置视频")
    assert draft["videoProvider"] == "unconfigured"
    assert draft["aiCopyProvider"] == "stub"


def test_copy_provider_http_without_url_is_unconfigured(monkeypatch):
    from app.content_ai_client import copy_provider_name

    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "http")
    monkeypatch.delenv("IMS_CONTENT_AI_BASE_URL", raising=False)
    monkeypatch.delenv("IMS_CONTENT_GEN_STUB", raising=False)
    invalidate_param_cache()
    assert copy_provider_name() == "unconfigured"


def test_param_secret_masked():
    auth = headers()
    saved = client.put(
        "/admin-api/ims/system/param",
        headers=auth,
        json={"paramKey": "content.ai.tokenSecret", "paramValue": "plain-token-should-not-leak"},
    )
    assert saved.json()["code"] == 0, saved.text
    assert saved.json()["data"]["paramValue"] == "********"
    assert "plain-token-should-not-leak" not in saved.text
    listing = client.get("/admin-api/ims/system/param", headers=auth)
    assert "plain-token-should-not-leak" not in listing.text
    row = next(item for item in listing.json()["data"] if item["paramKey"] == "content.ai.tokenSecret")
    assert row["secret"] is True
    assert row["paramValue"] == "********"


def test_unified_stub_switch(monkeypatch):
    monkeypatch.delenv("IMS_CONTENT_AI_STUB", raising=False)
    monkeypatch.setenv("IMS_CONTENT_GEN_STUB", "1")
    reset_copy_stub()
    job = submit_copy(requirement="统一开关", script_type="MONOLOGUE", candidate_count=2)
    assert job.ok
    job = copy_status(job.upstream_id)
    job = copy_status(job.upstream_id)
    assert job.status == "SUCCESS"
    assert job.copies[0] == STUB_COPY_V1


def test_real_http_mapping(monkeypatch):
    state = {"hits": 0, "auth": ""}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def _json(self, code: int, payload: dict):
            raw = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            state["auth"] = self.headers.get("Authorization") or ""
            if self.path == "/v1/copy/jobs":
                self._json(200, {"code": 0, "data": {"id": "up-copy", "status": "WAITING"}})
                return
            if self.path == "/prompt":
                self._json(503, {"error": "queue full"})
                return
            self._json(404, {"message": "missing"})

        def do_GET(self):
            if self.path.startswith("/v1/copy/jobs/"):
                state["hits"] += 1
                if state["hits"] == 1:
                    self._json(200, {"code": 0, "data": {"id": "up-copy", "status": "GENERATING"}})
                else:
                    self._json(200, {"code": 0, "data": {"id": "up-copy", "status": "SUCCESS", "copies": ["真实映射文案"]}})
                return
            if self.path.startswith("/history/"):
                self._json(
                    200,
                    {
                        "p-real": {
                            "status": {"status_str": "success", "completed": True},
                            "outputs": {"9": {"videos": [{"filename": "real.mp4", "subfolder": "out", "type": "output"}]}},
                        }
                    },
                )
                return
            self._json(401, {"message": "denied"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        monkeypatch.setenv("IMS_CONTENT_AI_STUB", "0")
        monkeypatch.setenv("IMS_COMFYUI_STUB", "0")
        monkeypatch.setenv("IMS_CONTENT_AI_BASE_URL", f"http://127.0.0.1:{port}")
        monkeypatch.setenv("IMS_COMFYUI_BASE_URL", f"http://127.0.0.1:{port}")
        monkeypatch.setenv("IMS_CONTENT_AI_TOKEN", "plain-token-should-not-leak")
        monkeypatch.setenv("IMS_CONTENT_AI_TIMEOUT", "2")
        invalidate_param_cache()
        submitted = submit_copy(requirement="映射", script_type="MONOLOGUE", candidate_count=2)
        assert submitted.status == "WAITING"
        assert state["auth"] == "Bearer plain-token-should-not-leak"
        mid = copy_status("up-copy")
        assert mid.status == "GENERATING"
        done = copy_status("up-copy")
        assert done.status == "SUCCESS"
        assert done.copies == ["真实映射文案"]
        queued = submit_prompt({"text": "x"})
        assert queued.code == 5004
        assert "plain-token-should-not-leak" not in (queued.message or "")
        monkeypatch.setenv("IMS_COMFYUI_STUB", "0")
        reset_video_stub()
        ok_video = prompt_status("p-real")
        assert ok_video.file_key == "out/real.mp4"
    finally:
        server.shutdown()
        server.server_close()


def test_http_timeout_maps_1056(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_POST(self):
            import time

            time.sleep(1.2)
            self.send_response(200)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        monkeypatch.setenv("IMS_COMFYUI_STUB", "0")
        monkeypatch.setenv("IMS_COMFYUI_BASE_URL", f"http://127.0.0.1:{port}")
        monkeypatch.setenv("IMS_COMFYUI_TIMEOUT", "0.3")
        invalidate_param_cache()
        result = submit_prompt({"text": "slow"})
        assert result.code == 1056
        assert result.retryable
        assert "重新发起" in result.message
    finally:
        server.shutdown()
        server.server_close()
