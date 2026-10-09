"""#152 · SOP/计划列表筛选与计划任务进度；公推模板来源筛选。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.main import app
from app.models import ContentTask
from app.ops_db import ops_session
from app.ops_models import IpGroup

client = TestClient(app)


def headers() -> dict:
    token = client.post(
        "/admin-api/ims/auth/login",
        json={"username": "admin", "password": "Admin@123"},
    ).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def sop_nodes(name: str = "脚本") -> list[dict]:
    return [
        {
            "nodeOrder": 1,
            "nodeName": name,
            "standardDesc": "脚本标准",
            "ownerRole": "R6",
            "slaHours": 24,
        },
        {
            "nodeOrder": 2,
            "nodeName": "发布",
            "standardDesc": "发布标准",
            "ownerRole": "R6",
            "nodeType": "CONTENT_PUBLISH",
            "slaHours": 12,
        },
    ]


def create_sop(auth: dict, name: str, content_type: str) -> int:
    created = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": name,
            "contentType": content_type,
            "sopLevel": "STANDARD",
            "nodes": sop_nodes(),
        },
    )
    body = created.json()
    assert body["code"] == 0, body
    return body["data"]["id"]


def seed_ip_group() -> int:
    ops = ops_session()
    try:
        group = IpGroup(group_name="筛选IP", status="ENABLED", tenant_id=0)
        ops.add(group)
        ops.commit()
        return group.id
    finally:
        ops.close()


def listed(path: str, auth: dict, **params) -> list[dict]:
    res = client.get(path, headers=auth, params={"pageNo": 1, "pageSize": 20, **params})
    body = res.json()
    assert body["code"] == 0, body
    return body["data"]["list"]


def test_sop_list_filters_by_type_and_status():
    auth = headers()
    video_id = create_sop(auth, "筛选短视频 SOP", "SHORT_VIDEO")
    article_id = create_sop(auth, "筛选文章 SOP", "ARTICLE")

    articles = listed("/admin-api/ims/content/sop/list", auth, contentType="ARTICLE", keyword="筛选")
    assert [row["id"] for row in articles] == [article_id]

    videos = listed("/admin-api/ims/content/sop/list", auth, contentType="SHORT_VIDEO", keyword="筛选短视频")
    assert [row["id"] for row in videos] == [video_id]

    both = listed("/admin-api/ims/content/sop/list", auth, status="ENABLED", keyword="筛选")
    assert {row["id"] for row in both} == {video_id, article_id}

    updated = client.put(
        f"/admin-api/ims/content/sop/{video_id}",
        headers=auth,
        json={
            "sopName": "筛选短视频 SOP",
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": sop_nodes(name="脚本v2"),
        },
    )
    assert updated.json()["code"] == 0
    new_id = updated.json()["data"]["id"]

    disabled = listed("/admin-api/ims/content/sop/list", auth, status="DISABLED", keyword="筛选短视频")
    assert [row["id"] for row in disabled] == [video_id]
    assert disabled[0]["version"] == 1

    enabled = listed("/admin-api/ims/content/sop/list", auth, status="ENABLED", keyword="筛选短视频")
    assert [row["id"] for row in enabled] == [new_id]
    assert enabled[0]["version"] == 2

    none = listed("/admin-api/ims/content/sop/list", auth, contentType="AUDIO", keyword="筛选")
    assert none == []


def test_plan_filters_and_task_progress():
    auth = headers()
    sop_id = create_sop(auth, "进度 SOP", "SHORT_VIDEO")
    ip_group_id = seed_ip_group()

    def create_plan(name: str) -> int:
        created = client.post(
            "/admin-api/ims/content/plan",
            headers=auth,
            json={
                "planName": name,
                "sopId": sop_id,
                "ipGroupIds": [ip_group_id],
                "startDate": "2026-10-01",
                "endDate": "2026-10-31",
            },
        )
        body = created.json()
        assert body["code"] == 0, body
        assert body["data"]["taskTotal"] == 0
        assert body["data"]["progressPercent"] is None
        return body["data"]["id"]

    plan_a = create_plan("进度甲计划")
    create_plan("进度乙计划")

    named = listed("/admin-api/ims/content/plan", auth, planName="进度甲")
    assert [row["id"] for row in named] == [plan_a]
    assert named[0]["status"] == "DRAFT"
    assert named[0]["taskTotal"] == 0

    running = listed("/admin-api/ims/content/plan", auth, status="IN_PROGRESS", planName="进度")
    assert running == []

    started = client.post(f"/admin-api/ims/content/plan/{plan_a}/start", headers=auth)
    assert started.json()["code"] == 0
    assert started.json()["data"]["taskTotal"] == 2
    assert started.json()["data"]["taskDone"] == 0
    assert started.json()["data"]["progressPercent"] == 0

    db = SessionLocal()
    try:
        task = db.scalar(select(ContentTask).where(ContentTask.plan_name == "进度甲计划"))
        assert task is not None
        task.task_status = "DONE"
        db.commit()
    finally:
        db.close()

    progressed = listed("/admin-api/ims/content/plan", auth, status="IN_PROGRESS", planName="进度甲")
    assert len(progressed) == 1
    assert progressed[0]["taskTotal"] == 2
    assert progressed[0]["taskDone"] == 1
    assert progressed[0]["progressPercent"] == 50

    drafts = listed("/admin-api/ims/content/plan", auth, status="DRAFT", planName="进度")
    assert len(drafts) == 1
    assert drafts[0]["planName"] == "进度乙计划"


def test_layout_source_filter_miss_is_empty():
    auth = headers()
    created = client.post(
        "/admin-api/ims/content/layout-template",
        headers=auth,
        json={"templateName": "来源筛选模板", "previewHtml": "", "source": "CUSTOM"},
    )
    assert created.json()["code"] == 0
    tpl_id = created.json()["data"]["id"]

    missed = listed(
        "/admin-api/ims/content/layout-template/list",
        auth,
        templateName="来源筛选",
        source="IMPORT",
    )
    assert missed == []

    hit = listed(
        "/admin-api/ims/content/layout-template/list",
        auth,
        templateName="来源筛选",
        source="CUSTOM",
        status="DRAFT",
    )
    assert [row["id"] for row in hit] == [tpl_id]
    assert hit[0]["previewHtml"] == ""
