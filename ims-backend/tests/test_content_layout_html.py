import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.content_layout_html import sanitize_layout_html
from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_sanitize_layout_html_strips_script_and_javascript_urls():
    raw = (
        '<p>版式甲</p><script>alert(1)</script>'
        '<img src="javascript:alert(1)" onerror="alert(1)" alt="bad">'
        '<a href="javascript:alert(1)">x</a>'
        '<a href="https://example.com/a">链接</a>'
    )
    html = sanitize_layout_html(raw)
    assert "版式甲" in html
    assert "<script" not in html.lower()
    assert "javascript:" not in html.lower()
    assert "onerror" not in html.lower()
    assert "https://example.com/a" in html
    assert sanitize_layout_html("<script>alert(1)</script>") == ""
    assert sanitize_layout_html("") == ""


def test_content_detail_returns_sanitized_layout_html_and_body_fallback_source():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "查看版式",
            "body": "纯文本乙",
            "layoutHtml": '<p class="lead">版式甲</p><script>alert(1)</script>',
        },
    )
    body = created.json()
    assert body["code"] == 0
    assert "版式甲" in body["data"]["layoutHtml"]
    assert "<script" not in body["data"]["layoutHtml"].lower()
    assert body["data"]["body"] == "纯文本乙"
    content_id = body["data"]["id"]

    detail = client.get(f"/admin-api/ims/content/{content_id}", headers=auth)
    assert detail.json()["code"] == 0
    assert detail.json()["data"]["layoutHtml"] == body["data"]["layoutHtml"]

    listed = client.get("/admin-api/ims/content", headers=auth, params={"title": "查看版式", "pageNo": 1, "pageSize": 10})
    row = next(item for item in listed.json()["data"]["list"] if item["id"] == content_id)
    assert row["layoutHtml"] == body["data"]["layoutHtml"]
    assert row["body"] == "纯文本乙"


def test_content_without_layout_html_keeps_plain_body():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "仅正文", "body": "只有正文丙", "layoutHtml": "<script>alert(1)</script>"},
    )
    body = created.json()
    assert body["code"] == 0
    assert body["data"]["layoutHtml"] == ""
    assert body["data"]["body"] == "只有正文丙"
