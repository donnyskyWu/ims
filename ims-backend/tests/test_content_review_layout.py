import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.layout_html import sanitize_layout_html
from app.main import app

client = TestClient(app)

PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAgCAIAAADbtmxLAAAAMUlEQVR42u3OMQ0AAAgDsEmafy2IwQXhaFIB"
    "zbSvREhISEhISEhISEhISEhISEjo0gKJWmhqLudyPwAAAABJRU5ErkJggg=="
)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def _layout() -> str:
    return (
        f'<p onclick="evil()">版式段落</p>'
        f'<img src="{PNG}" alt="插图" data-w="160">'
        "<script>alert(1)</script>"
        '<img src="javascript:alert(1)" alt="bad">'
        '<a href="javascript:alert(1)">链接</a>'
    )


def test_sanitize_layout_html_keeps_image_and_is_idempotent():
    out = sanitize_layout_html(_layout())
    assert "<script" not in out.lower()
    assert "onclick" not in out.lower()
    assert "javascript:" not in out.lower()
    assert 'alt="插图"' in out
    assert "width:160px" in out
    assert "版式段落" in out
    assert "链接" in out
    assert out.count("<img") == 1
    assert sanitize_layout_html(out) == out
    assert sanitize_layout_html("") == ""
    assert sanitize_layout_html(None) == ""


def test_review_detail_returns_sanitized_layout_html():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "审核版式预览", "body": "纯文本摘要", "layoutHtml": _layout()},
    )
    assert created.json()["code"] == 0
    stored = created.json()["data"]["layoutHtml"]
    assert "<script" not in stored.lower()
    assert 'alt="插图"' in stored
    content_id = created.json()["data"]["id"]

    updated = client.put(
        f"/admin-api/ims/content/{content_id}",
        headers=auth,
        json={"title": "审核版式预览", "body": "纯文本摘要"},
    )
    assert updated.json()["code"] == 0
    assert 'alt="插图"' in updated.json()["data"]["layoutHtml"]

    submit = client.post(f"/admin-api/ims/content/{content_id}/submit-review", headers=auth)
    assert submit.json()["code"] == 0
    review_no = submit.json()["data"]["reviewNo"]

    detail = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth)
    assert detail.json()["code"] == 0
    data = detail.json()["data"]
    assert data["body"] == "纯文本摘要"
    assert "<script" not in data["layoutHtml"].lower()
    assert "onclick" not in data["layoutHtml"].lower()
    assert 'alt="插图"' in data["layoutHtml"]
    assert "width:160px" in data["layoutHtml"]
    assert data["checklist"]


def test_review_detail_body_when_layout_empty():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "审核纯文本", "body": "仅纯文本正文"},
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["layoutHtml"] == ""
    content_id = created.json()["data"]["id"]
    submit = client.post(f"/admin-api/ims/content/{content_id}/submit-review", headers=auth)
    review_no = submit.json()["data"]["reviewNo"]
    detail = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth)
    data = detail.json()["data"]
    assert data["layoutHtml"] == ""
    assert data["body"] == "仅纯文本正文"
