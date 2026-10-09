import json
import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
import app.content_layout_ai as layout_ai

client = TestClient(app)

BODY = "周日焦点战\n主队状态稳定，客队防守一般。"


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def create_content(auth: dict, *, body: str = BODY, content_type: str = "ARTICLE", title: str = "语义排版稿") -> dict:
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": title, "contentType": content_type, "body": body},
    )
    payload = created.json()
    assert payload["code"] == 0
    return payload["data"]


def test_stub_preview_apply_keeps_plain_text(monkeypatch):
    monkeypatch.setenv("IMS_LAYOUT_AI_STUB", "success")

    def _forbid_llm(*args, **kwargs):
        raise AssertionError("stub 不应调用 LLM")

    monkeypatch.setattr(layout_ai.httpx, "Client", _forbid_llm)
    auth = headers()
    row = create_content(auth, body="A & B <C>")
    preview = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/preview",
        headers=auth,
        json={"mode": "AUTO", "body": "A & B <C>"},
    )
    preview_body = preview.json()
    assert preview_body["code"] == 0
    assert preview_body["data"]["fidelityCheck"]["passed"] is True
    assert preview_body["data"]["fidelityCheck"]["plainTextBefore"] == "A & B <C>"
    assert preview_body["data"]["fidelityCheck"]["plainTextAfter"] == "A & B <C>"
    assert preview_body["data"]["selectedFootballTemplate"] == "decision-scan"
    assert "<script" not in preview_body["data"]["layoutHtml"]

    applied = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "AUTO", "body": "A & B <C>", "overwrite": False},
    )
    applied_body = applied.json()
    assert applied_body["code"] == 0
    assert applied_body["data"]["body"] == "A & B <C>"
    assert applied_body["data"]["bodyFormat"] == "LAYOUT"
    assert applied_body["data"]["layoutHtml"]
    assert layout_ai.normalize_plain(layout_ai.extract_plain_text(applied_body["data"]["layoutHtml"])) == "A & B <C>"

    detail = client.get(f"/admin-api/ims/content/{row['id']}", headers=auth).json()
    assert detail["data"]["body"] == "A & B <C>"
    assert detail["data"]["bodyFormat"] == "LAYOUT"

    saved = client.put(
        f"/admin-api/ims/content/{row['id']}",
        headers=auth,
        json={"title": "语义排版稿-改标题", "contentType": "ARTICLE", "body": "A & B <C>"},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["layoutHtml"] == applied_body["data"]["layoutHtml"]
    assert saved.json()["data"]["body"] == "A & B <C>"


def test_empty_body_2036_fidelity_2037_overwrite_2031(monkeypatch):
    monkeypatch.setenv("IMS_LAYOUT_AI_STUB", "success")
    auth = headers()
    empty = create_content(auth, body="", title="空正文")
    empty_preview = client.post(
        f"/admin-api/ims/content/{empty['id']}/typeset/preview",
        headers=auth,
        json={"mode": "AUTO"},
    )
    assert empty_preview.json()["code"] == 2036

    row = create_content(auth, title="保真与覆盖")
    monkeypatch.setenv("IMS_LAYOUT_AI_STUB", "fidelity")
    mutated = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "AUTO", "overwrite": True},
    )
    assert mutated.json()["code"] == 2037
    unchanged = client.get(f"/admin-api/ims/content/{row['id']}", headers=auth).json()["data"]
    assert unchanged["body"] == BODY
    assert unchanged["bodyFormat"] == "PLAIN"
    assert unchanged["layoutHtml"] == ""

    monkeypatch.setenv("IMS_LAYOUT_AI_STUB", "success")
    first = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "AUTO", "overwrite": False},
    )
    assert first.json()["code"] == 0
    second = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "AUTO", "overwrite": False},
    )
    assert second.json()["code"] == 2031
    still = client.get(f"/admin-api/ims/content/{row['id']}", headers=auth).json()["data"]
    assert still["body"] == BODY
    assert still["layoutHtml"] == first.json()["data"]["layoutHtml"]

    replaced = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "AUTO", "overwrite": True},
    )
    assert replaced.json()["code"] == 0
    assert replaced.json()["data"]["body"] == BODY


def test_content_stub_fallback_and_copywriting_does_not_layout(monkeypatch):
    monkeypatch.delenv("IMS_LAYOUT_AI_STUB", raising=False)
    monkeypatch.setenv("IMS_CONTENT_AI_STUB", "success")
    auth = headers()
    row = create_content(auth, title="文案不排版")
    preview = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/preview",
        headers=auth,
        json={"mode": "AUTO"},
    )
    assert preview.json()["code"] == 0
    retry = client.post(f"/admin-api/ims/content/{row['id']}/retry-ai-generate", headers=auth)
    assert retry.json()["code"] == 0
    detail = client.get(f"/admin-api/ims/content/{row['id']}", headers=auth).json()["data"]
    assert detail["aiGenerateStatus"] == "QUEUED"
    assert detail["layoutHtml"] == ""
    assert detail["body"] == BODY
    assert detail["bodyFormat"] == "PLAIN"


def test_non_article_and_review_readonly_same_layout(monkeypatch):
    monkeypatch.setenv("IMS_LAYOUT_AI_STUB", "success")
    auth = headers()
    video = create_content(auth, content_type="SHORT_VIDEO", title="短视频", body=BODY)
    denied = client.post(
        f"/admin-api/ims/content/{video['id']}/typeset/preview",
        headers=auth,
        json={"mode": "AUTO"},
    )
    assert denied.json()["code"] == 1500

    row = create_content(auth, title="审核只读版式")
    applied = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "AUTO", "overwrite": False},
    ).json()
    assert applied["code"] == 0
    submitted = client.post(f"/admin-api/ims/content/{row['id']}/submit-review", headers=auth).json()
    assert submitted["code"] == 0
    review = client.get(f"/admin-api/ims/content/review/{submitted['data']['reviewNo']}", headers=auth).json()
    assert review["code"] == 0
    assert review["data"]["layoutHtml"] == applied["data"]["layoutHtml"]
    assert review["data"]["body"] == BODY
    assert review["data"]["bodyFormat"] == "LAYOUT"
    assert review["data"]["layoutJson"]["bodyFormat"] == "LAYOUT"


def test_llm_client_and_missing_key(monkeypatch):
    monkeypatch.delenv("IMS_LAYOUT_AI_STUB", raising=False)
    monkeypatch.delenv("IMS_CONTENT_AI_STUB", raising=False)
    monkeypatch.delenv("IMS_LAYOUT_AI_API_KEY", raising=False)
    monkeypatch.delenv("IMS_CONTENT_AI_API_KEY", raising=False)
    auth = headers()
    row = create_content(auth, title="未配置密钥", body="原文")
    missing = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/preview",
        headers=auth,
        json={"mode": "AUTO"},
    )
    assert missing.json()["code"] == 2039

    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"segments": [{"segmentType": "PLAIN_PARAGRAPH", "text": "原文"}]},
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, timeout=0):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setenv("IMS_LAYOUT_AI_ENDPOINT", "https://llm.example/v1")
    monkeypatch.setenv("IMS_LAYOUT_AI_MODEL", "layout-test")
    monkeypatch.setenv("IMS_LAYOUT_AI_API_KEY", "test-key")
    monkeypatch.setattr(layout_ai.httpx, "Client", FakeClient)
    preview = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/preview",
        headers=auth,
        json={"mode": "AUTO", "body": "原文"},
    )
    assert preview.json()["code"] == 0
    assert preview.json()["data"]["fidelityCheck"]["plainTextAfter"] == "原文"
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "layout-test"
    assert "不得增删改原文" in captured["json"]["messages"][0]["content"]


def test_layout_module_does_not_call_copywriting():
    source = open(layout_ai.__file__, encoding="utf-8").read()
    assert "import football_client" not in source
    assert "jingcai." not in source.lower()
    assert "retry-ai-generate" not in source
    assert "retry_ai" not in source
