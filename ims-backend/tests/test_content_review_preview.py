import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.content_review_preview import split_paid_free
from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_split_layout_zone_and_paywall_marker():
    zoned = split_paid_free(
        "付费原文\n---FREE---\n免费原文",
        '<section data-zone="paid"><p>付费版式</p></section><section data-zone="free"><p>免费版式</p></section>',
        "COPY",
    )
    assert zoned["columnSplit"] == "layout-zone"
    assert zoned["paidBody"] == "付费版式"
    assert zoned["freeBody"] == "免费版式"
    assert zoned["paywall"] is True

    wall = split_paid_free(
        "",
        '<div data-paywall="true">付费墙</div><div data-paywall="false">免费墙</div>',
        "COPY",
    )
    assert wall["columnSplit"] == "layout-zone"
    assert wall["paidBody"] == "付费墙"
    assert wall["freeBody"] == "免费墙"


def test_split_body_marker_beats_official_plan():
    marked = split_paid_free("付费推荐：主胜\n---FREE---\n免费导读：赛前看点", "", "OFFICIAL_PLAN")
    assert marked["columnSplit"] == "body-marker"
    assert marked["paidBody"] == "付费推荐：主胜"
    assert marked["freeBody"] == "免费导读：赛前看点"
    assert marked["paywall"] is True


def test_split_official_plan_and_default_free_and_script_stripped():
    paid = split_paid_free("方案正文", "", "OFFICIAL_PLAN")
    assert paid["columnSplit"] == "paywall-doc"
    assert paid["paidBody"] == "方案正文"
    assert paid["freeBody"] == ""
    assert paid["paywall"] is True

    free = split_paid_free("导读", "", "COPY")
    assert free["columnSplit"] == "default-free"
    assert free["paidBody"] == ""
    assert free["freeBody"] == "导读"
    assert free["paywall"] is False

    from_layout = split_paid_free("", "<script>alert(1)</script><p>仅版式</p>", "COPY")
    assert from_layout["columnSplit"] == "default-free"
    assert from_layout["freeBody"] == "仅版式"
    assert "alert" not in from_layout["freeBody"]


def test_review_detail_preview_sessions_and_columns():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={
            "title": "双栏审核预览",
            "contentType": "ARTICLE",
            "documentType": "COPY",
            "body": "付费原文\n---FREE---\n免费原文",
            "layoutHtml": (
                '<section data-zone="body_paid"><p>付费版式</p></section>'
                '<section data-zone="free_body"><p>免费版式</p></section>'
            ),
            "matchType": 1,
            "matchScheme": [
                {
                    "matchId": "m119",
                    "homeName": "曼联",
                    "awayName": "切尔西",
                    "matchTime": "2026-10-09 20:00",
                    "mainPlayMethod": "胜平负",
                }
            ],
        },
    )
    assert created.json()["code"] == 0
    content_id = created.json()["data"]["id"]
    submitted = client.post(f"/admin-api/ims/content/{content_id}/submit-review", headers=auth)
    assert submitted.json()["code"] == 0
    review_no = submitted.json()["data"]["reviewNo"]

    detail = client.get(f"/admin-api/ims/content/review/{review_no}", headers=auth)
    body = detail.json()
    assert body["code"] == 0
    preview = body["data"]["contentPreview"]
    assert preview["columnSplit"] == "layout-zone"
    assert preview["paidBody"] == "付费版式"
    assert preview["freeBody"] == "免费版式"
    assert preview["paywall"] is True
    assert preview["matchType"] == 1
    assert preview["matchScheme"][0]["homeName"] == "曼联"
    assert preview["matchScheme"][0]["awayName"] == "切尔西"
    assert "layoutHtml" in preview and "data-zone" in preview["layoutHtml"]
    assert "checklist" in body["data"]
