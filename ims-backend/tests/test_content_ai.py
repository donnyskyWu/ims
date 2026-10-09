"""内容文案生成：桩预览、失败重试、续写、HTTP 基址、不改版式。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"
os.environ.pop("IMS_CONTENT_AI_STUB", None)
os.environ.pop("IMS_CONTENT_AI_BASE_URL", None)

from fastapi.testclient import TestClient

from app.main import app
from app.settings_runtime import invalidate_param_cache

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_models_and_preview_leave_body_and_layout(monkeypatch):
    monkeypatch.delenv("IMS_CONTENT_AI_STUB", raising=False)
    monkeypatch.delenv("IMS_CONTENT_AI_BASE_URL", raising=False)
    invalidate_param_cache()
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "文案桩", "body": "原稿", "layoutHtml": "<p>keep-layout</p>"},
    )
    assert created.json()["code"] == 0
    content_id = created.json()["data"]["id"]

    models = client.get("/admin-api/ims/content/ai-content/models", headers=auth)
    assert models.json()["code"] == 0
    ids = {row["id"] for row in models.json()["data"]}
    assert "stub-qwen" in ids
    assert "stub-gpt" in ids

    generated = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={"modelId": "stub-qwen", "prompt": "MARKER-ALPHA 赛后复盘", "contentId": content_id},
    )
    body = generated.json()
    assert body["code"] == 0
    assert body["data"]["mock"] is True
    assert body["data"]["targetField"] == "body"
    assert body["data"]["layoutApplied"] is False
    assert "layoutHtml" not in body["data"]
    assert "MARKER-ALPHA" in body["data"]["markdown"]
    assert "不改版式" in body["data"]["markdown"]

    detail = client.get(f"/admin-api/ims/content/{content_id}", headers=auth).json()["data"]
    assert detail["body"] == "原稿"
    assert detail["layoutHtml"] == "<p>keep-layout</p>"

    missing = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={"modelId": "missing-model", "prompt": "x"},
    )
    assert missing.json()["code"] == 1500
    gone = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={"modelId": "stub-qwen", "prompt": "x", "contentId": 999999},
    )
    assert gone.json()["code"] == 1504


def test_fail_retry_and_polish_round(monkeypatch):
    auth = headers()
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "fail")
    failed = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={"modelId": "stub-qwen", "prompt": "首稿"},
    )
    assert failed.json()["code"] == 1500
    assert "失败" in failed.json()["msg"]

    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "success")
    first = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={"modelId": "stub-gpt", "prompt": "首稿要点 ALPHA"},
    )
    assert first.json()["code"] == 0
    draft = first.json()["data"]["markdown"]
    assert "ALPHA" in draft

    second = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={
            "modelId": "stub-gpt",
            "prompt": "加强结尾 BETA",
            "roundCount": 2,
            "currentBody": draft,
            "history": [
                {"role": "user", "content": "首稿要点 ALPHA"},
                {"role": "assistant", "content": draft},
            ],
        },
    )
    polished = second.json()
    assert polished["code"] == 0
    assert polished["data"]["roundCount"] == 2
    text = polished["data"]["markdown"]
    assert "ALPHA" in text
    assert "BETA" in text
    assert "续写" in text
    assert polished["data"]["layoutApplied"] is False


def test_http_mode_uses_configured_base(monkeypatch):
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "http")
    monkeypatch.setenv("IMS_CONTENT_AI_BASE_URL", "https://llm.example.test/gateway")
    invalidate_param_cache()
    seen: dict = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            seen["timeout"] = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json):
            seen["url"] = url
            seen["json"] = json

            class Response:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {"choices": [{"message": {"content": "# HTTP稿\n\n远端正文"}}]}

            return Response()

    monkeypatch.setattr("app.content_ai_client.httpx.Client", FakeClient)
    auth = headers()
    res = client.post(
        "/admin-api/ims/content/ai-content/generate",
        headers=auth,
        json={"modelId": "stub-qwen", "prompt": "写复盘"},
    )
    body = res.json()
    assert body["code"] == 0
    assert body["data"]["mock"] is False
    assert body["data"]["markdown"].startswith("# HTTP稿")
    assert seen["url"] == "https://llm.example.test/gateway/v1/chat/completions"
    assert "jingcai" not in seen["url"]
    assert seen["json"]["model"] == "qwen-plus"


def test_save_body_does_not_wipe_layout():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "排版保留", "body": "旧正文", "layoutHtml": "<section>typeset</section>"},
    )
    assert created.json()["code"] == 0
    content_id = created.json()["data"]["id"]
    updated = client.put(
        f"/admin-api/ims/content/{content_id}",
        headers=auth,
        json={"title": "排版保留", "body": "采纳后的正文"},
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"]["body"] == "采纳后的正文"
    assert updated.json()["data"]["layoutHtml"] == "<section>typeset</section>"
