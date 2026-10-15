"""TC-07 P1：SOP 平台/启停、公推导入与复制删除、内容导出与批量。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def _node(**extra) -> dict:
    base = {
        "nodeOrder": 1,
        "nodeName": "脚本",
        "ownerRole": "R6",
        "nodeType": "NORMAL",
        "slaHours": 24,
    }
    base.update(extra)
    return base


def test_b001_sop_platform_and_generation_doc_type():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "TC07 平台 SOP",
            "contentType": "ARTICLE",
            "platform": "DOUYIN",
            "sopLevel": "STANDARD",
            "nodes": [_node(nodeType="CONTENT_GENERATION", documentType="COPY", nodeName="成稿")],
        },
    )
    assert created.json()["code"] == 0
    assert created.json()["data"]["platform"] == "DOUYIN"

    missing = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "TC07 缺文档类型",
            "contentType": "ARTICLE",
            "platform": "ALL",
            "nodes": [_node(nodeType="CONTENT_GENERATION", documentType="", nodeName="成稿")],
        },
    )
    assert missing.json()["code"] == 1500
    assert "文档类型" in missing.json()["msg"]

    bad_platform = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "TC07 坏平台",
            "contentType": "ARTICLE",
            "platform": "XHS",
            "nodes": [_node()],
        },
    )
    assert bad_platform.json()["code"] == 1500

    empty_type = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={"sopName": "TC07 缺内容类型", "contentType": "", "nodes": [_node()]},
    )
    assert empty_type.json()["code"] == 1001
    assert "必填" in empty_type.json()["msg"]

    out_of_dict = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={"sopName": "TC07 越界类型", "contentType": "LIVE_CLIP", "nodes": [_node()]},
    )
    assert out_of_dict.json()["code"] == 1503

    video = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={"sopName": "TC07 视频 SOP", "contentType": "VIDEO", "nodes": [_node()]},
    )
    assert video.json()["code"] == 0
    assert video.json()["data"]["contentType"] == "VIDEO"

    echoed = client.get(
        "/admin-api/ims/content/sop/list",
        headers=auth,
        params={"keyword": "TC07 平台 SOP", "pageSize": 20},
    )
    assert echoed.json()["data"]["list"][0]["contentType"] == "ARTICLE"

    options = client.get(
        "/admin-api/ims/system/dict-data/list",
        headers=auth,
        params={"dictType": "dict_content_type"},
    )
    enabled = [row for row in options.json()["data"] if row["status"] == "ENABLED"]
    assert [(row["dictValue"], row["dictLabel"]) for row in enabled] == [
        ("ARTICLE", "文章"),
        ("SHORT_VIDEO", "短视频"),
        ("VIDEO", "视频"),
    ]


def test_b002_sop_status_hides_from_enabled_list():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": "TC07 启停 SOP",
            "contentType": "SHORT_VIDEO",
            "platform": "KUAISHOU",
            "nodes": [_node()],
        },
    )
    sop_id = created.json()["data"]["id"]
    assert created.json()["data"]["status"] == "ENABLED"

    disabled = client.put(
        f"/admin-api/ims/content/sop/{sop_id}/status",
        headers=auth,
        json={"status": "DISABLED"},
    )
    assert disabled.json()["code"] == 0
    assert disabled.json()["data"]["status"] == "DISABLED"

    enabled_only = client.get(
        "/admin-api/ims/content/sop/list",
        headers=auth,
        params={"status": "ENABLED", "keyword": "TC07 启停 SOP", "pageSize": 20},
    )
    assert enabled_only.json()["code"] == 0
    assert all(row["id"] != sop_id for row in enabled_only.json()["data"]["list"])

    again = client.put(
        f"/admin-api/ims/content/sop/{sop_id}/status",
        headers=auth,
        json={"status": "ENABLED"},
    )
    assert again.json()["data"]["status"] == "ENABLED"
    listed = client.get(
        "/admin-api/ims/content/sop/list",
        headers=auth,
        params={"status": "ENABLED", "keyword": "TC07 启停 SOP", "pageSize": 20},
    )
    assert any(row["id"] == sop_id for row in listed.json()["data"]["list"])


def test_b004_layout_import_wizard():
    auth = headers()
    empty_url = client.post("/admin-api/ims/content/layout-template/import-url", headers=auth, json={"url": "  "})
    assert empty_url.json()["code"] == 1001

    blocked = client.post(
        "/admin-api/ims/content/layout-template/import-url",
        headers=auth,
        json={"url": "https://mp.weixin.qq.com/s/demo", "templateName": "不应落库"},
    )
    assert blocked.json()["code"] == 1500
    assert "MHTML" in blocked.json()["msg"]
    assert "HTML" in blocked.json()["msg"]
    leaked = client.get(
        "/admin-api/ims/content/layout-template/list",
        headers=auth,
        params={"templateName": "不应落库"},
    )
    assert leaked.json()["data"]["list"] == []

    empty_paste = client.post(
        "/admin-api/ims/content/layout-template/import-paste",
        headers=auth,
        json={"templateName": "", "html": ""},
    )
    assert empty_paste.json()["code"] == 1001

    pasted = client.post(
        "/admin-api/ims/content/layout-template/import-paste",
        headers=auth,
        json={"templateName": "TC07 粘贴模板", "html": "<p>示例正文</p>"},
    )
    body = pasted.json()
    assert body["code"] == 0
    assert body["data"]["jobId"]
    assert body["data"]["template"]["status"] == "DRAFT"
    assert body["data"]["template"]["source"] == "IMPORT"

    mhtml = client.post(
        "/admin-api/ims/content/layout-template/import-mhtml",
        headers=auth,
        files={"file": ("demo.mhtml", b"<html><body>mhtml</body></html>", "multipart/related")},
        data={"templateName": "TC07 MHTML"},
    )
    assert mhtml.json()["code"] == 0
    assert mhtml.json()["data"]["template"]["status"] == "DRAFT"
    assert mhtml.json()["data"]["template"]["source"] == "IMPORT"


def test_b005_preset_copy_and_draft_delete():
    auth = headers()
    listed = client.get(
        "/admin-api/ims/content/layout-template/list",
        headers=auth,
        params={"source": "PRESET", "pageSize": 20},
    )
    presets = listed.json()["data"]["list"]
    assert presets
    src = presets[0]
    copied = client.post(f"/admin-api/ims/content/layout-template/{src['id']}/copy", headers=auth)
    copy_body = copied.json()
    assert copy_body["code"] == 0
    assert copy_body["data"]["templateName"].endswith("（副本）")
    assert copy_body["data"]["status"] == "DRAFT"
    assert copy_body["data"]["source"] == "CUSTOM"

    blocked = client.delete(f"/admin-api/ims/content/layout-template/{src['id']}", headers=auth)
    assert blocked.json()["code"] == 1001

    removed = client.delete(
        f"/admin-api/ims/content/layout-template/{copy_body['data']['id']}",
        headers=auth,
    )
    assert removed.json()["code"] == 0
    gone = client.get(f"/admin-api/ims/content/layout-template/{copy_body['data']['id']}", headers=auth)
    assert gone.json()["code"] != 0


def test_b007_export_and_batch():
    auth = headers()
    title = "TC07 批量内容"
    created = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": title, "contentType": "ARTICLE", "documentType": "COPY", "body": "正文"},
    )
    content_id = created.json()["data"]["id"]

    empty_del = client.post("/admin-api/ims/content/batch-delete", headers=auth, json={"ids": []})
    assert empty_del.json()["msg"] == "请先勾选要删除的内容"
    empty_sub = client.post("/admin-api/ims/content/batch-submit", headers=auth, json={"ids": []})
    assert empty_sub.json()["msg"] == "请先勾选要提交的内容"
    empty_kb = client.post("/admin-api/ims/content/batch-transfer-kb", headers=auth, json={"ids": []})
    assert empty_kb.json()["msg"] == "请先勾选要转入知识库的内容"

    exported = client.get("/admin-api/ims/content/export", headers=auth, params={"title": title})
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert title.encode("utf-8") in exported.content

    transferred = client.post(
        "/admin-api/ims/content/batch-transfer-kb",
        headers=auth,
        json={"ids": [content_id]},
    )
    assert transferred.json()["code"] == 0
    assert transferred.json()["data"]["transferred"] == 1
    kb = client.get("/admin-api/ims/air/kb/page", headers=auth, params={"title": title})
    assert any(row["title"] == title for row in kb.json()["data"]["list"])

    submitted = client.post("/admin-api/ims/content/batch-submit", headers=auth, json={"ids": [content_id]})
    assert submitted.json()["code"] == 0
    assert submitted.json()["data"]["submitted"] == 1

    draft = client.post(
        "/admin-api/ims/content",
        headers=auth,
        json={"title": "TC07 待删", "contentType": "ARTICLE", "body": "删"},
    )
    draft_id = draft.json()["data"]["id"]
    deleted = client.post("/admin-api/ims/content/batch-delete", headers=auth, json={"ids": [draft_id]})
    assert deleted.json()["code"] == 0
    assert deleted.json()["data"]["deleted"] == 1
    missing = client.get(f"/admin-api/ims/content/{draft_id}", headers=auth)
    assert missing.json()["code"] != 0
