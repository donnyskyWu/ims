import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.content_typeset import extract_plain, fidelity_ok, normalize_plain

client = TestClient(app)

BODY = "主队近期状态回升，客队防守不稳。\n\n焦点在中场控制。"


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def create_content(auth: dict, body: str = BODY, title: str = "排版稿") -> dict:
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": title, "body": body, "contentType": "ARTICLE"},
    )
    payload = created.json()
    assert payload["code"] == 0
    return payload["data"]


def test_rule_presets_preview_apply_keeps_body():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/content/layout-template/list",
        headers=auth,
        params={"status": "ENABLED", "pageNo": 1, "pageSize": 20},
    )
    names = {row["templateName"] for row in listed.json()["data"]["list"]}
    assert {"清爽阅读", "营销引流", "决策扫读", "分析报告"} <= names

    row = create_content(auth)
    content_id = row["id"]
    for preset, marker in (
        ("clean-read", "ims-layout-clean"),
        ("marketing", "ims-lead"),
        ("decision-scan", "ims-scan-line"),
        ("analysis-report", "ims-analysis"),
    ):
        preview = client.post(
            f"/admin-api/ims/content/{content_id}/typeset/preview",
            headers=auth,
            json={"mode": "RULE", "preset": preset},
        )
        body = preview.json()
        assert body["code"] == 0, body
        assert body["data"]["fidelityCheck"]["passed"] is True
        assert body["data"]["plainTextBefore"] == body["data"]["plainTextAfter"]
        assert marker in body["data"]["layoutHtml"]
        assert "主队近期状态回升" in body["data"]["layoutHtml"]
        assert body["data"]["body"] == BODY

    detail = client.get(f"/admin-api/ims/content/{content_id}", headers=auth).json()["data"]
    assert detail["bodyFormat"] == "PLAIN"
    assert detail["body"] == BODY

    applied = client.post(
        f"/admin-api/ims/content/{content_id}/typeset/apply",
        headers=auth,
        json={"mode": "RULE", "preset": "marketing"},
    )
    applied_body = applied.json()
    assert applied_body["code"] == 0, applied_body
    assert applied_body["data"]["body"] == BODY
    assert applied_body["data"]["bodyFormat"] == "LAYOUT"
    assert "data-preset=\"marketing\"" in applied_body["data"]["layoutHtml"]
    assert fidelity_ok(BODY, applied_body["data"]["layoutHtml"])

    again = client.post(
        f"/admin-api/ims/content/{content_id}/typeset/apply",
        headers=auth,
        json={"mode": "RULE", "preset": "clean-read", "overwrite": False},
    )
    assert again.json()["code"] == 2031

    overwritten = client.post(
        f"/admin-api/ims/content/{content_id}/typeset/apply",
        headers=auth,
        json={"mode": "RULE", "preset": "clean-read", "overwrite": True, "body": "另一段不应写回正文"},
    )
    overwritten_body = overwritten.json()
    assert overwritten_body["code"] == 0, overwritten_body
    assert overwritten_body["data"]["body"] == BODY
    assert "另一段不应写回正文" in overwritten_body["data"]["layoutHtml"]
    assert "主队近期状态回升" not in overwritten_body["data"]["layoutHtml"]


def test_typeset_empty_body_and_fidelity_gate(monkeypatch):
    auth = headers()
    empty = create_content(auth, body="", title="空正文")
    denied = client.post(
        f"/admin-api/ims/content/{empty['id']}/typeset/preview",
        headers=auth,
        json={"mode": "RULE", "preset": "clean-read"},
    )
    assert denied.json()["code"] == 2036

    row = create_content(auth, title="保真失败")

    def bad_render(preset, body, template_name=""):
        return "<p>被改写的正文</p>", {"version": 1, "preset": preset}

    monkeypatch.setattr("app.content_typeset.render_layout", bad_render)
    failed = client.post(
        f"/admin-api/ims/content/{row['id']}/typeset/apply",
        headers=auth,
        json={"mode": "RULE", "preset": "clean-read"},
    )
    assert failed.json()["code"] == 2037
    kept = client.get(f"/admin-api/ims/content/{row['id']}", headers=auth).json()["data"]
    assert kept["body"] == BODY
    assert kept["bodyFormat"] == "PLAIN"
    assert normalize_plain(extract_plain("<p>甲&amp;乙</p>")) == "甲&乙"


def test_apply_template_review_and_preserve_on_save():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/content/layout-template/list",
        headers=auth,
        params={"templateName": "清爽阅读", "status": "ENABLED", "pageSize": 5},
    ).json()["data"]["list"]
    assert listed
    template_id = listed[0]["id"]

    missing = client.post(
        "/admin-api/ims/content/1/typeset/apply",
        headers=auth,
        json={"mode": "TEMPLATE", "templateId": 999999},
    )
    assert missing.json()["code"] in (1501, 1504)

    row = create_content(auth, title="套用模板稿")
    content_id = row["id"]
    applied = client.post(
        f"/admin-api/ims/content/{content_id}/typeset/apply",
        headers=auth,
        json={"mode": "TEMPLATE", "templateId": template_id},
    )
    applied_body = applied.json()
    assert applied_body["code"] == 0, applied_body
    assert applied_body["data"]["body"] == BODY
    assert applied_body["data"]["bodyFormat"] == "LAYOUT"
    assert applied_body["data"]["layoutTemplateId"] == template_id
    assert fidelity_ok(BODY, applied_body["data"]["layoutHtml"])

    saved = client.put(
        f"/admin-api/ims/content/{content_id}",
        headers=auth,
        json={"title": "套用模板稿", "body": BODY},
    )
    assert saved.json()["code"] == 0
    assert saved.json()["data"]["layoutHtml"] == applied_body["data"]["layoutHtml"]
    assert saved.json()["data"]["bodyFormat"] == "LAYOUT"

    draft = client.post(
        "/admin-api/ims/content/layout-template",
        headers=auth,
        json={"templateName": "未发布模板", "previewHtml": "<p>x</p>"},
    ).json()["data"]["id"]
    blocked = client.post(
        f"/admin-api/ims/content/{content_id}/typeset/apply",
        headers=auth,
        json={"mode": "TEMPLATE", "templateId": draft, "overwrite": True},
    )
    assert blocked.json()["code"] == 1501

    submitted = client.post(f"/admin-api/ims/content/{content_id}/submit-review", headers=auth)
    assert submitted.json()["code"] == 0
    review_no = submitted.json()["data"]["reviewNo"]
    detail = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth).json()
    assert detail["code"] == 0
    assert detail["data"]["body"] == BODY
    assert detail["data"]["bodyFormat"] == "LAYOUT"
    assert "主队近期状态回升" in detail["data"]["layoutHtml"]

    locked = client.post(
        f"/admin-api/ims/content/{content_id}/typeset/apply",
        headers=auth,
        json={"mode": "RULE", "preset": "marketing", "overwrite": True},
    )
    assert locked.json()["code"] == 1502
