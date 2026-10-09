"""UT-CONTENT-002 · 选题立项 TOP-R1（缺 SOP 或计划发布日 → 1052）。"""

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


def create_sop(auth: dict, name: str = "立项 SOP") -> int:
    res = client.post(
        "/admin-api/ims/content/sop",
        headers=auth,
        json={
            "sopName": name,
            "contentType": "SHORT_VIDEO",
            "sopLevel": "STANDARD",
            "nodes": [
                {
                    "nodeOrder": 1,
                    "nodeName": "脚本",
                    "standardDesc": "脚本标准",
                    "qualityChecklist": [{"itemCode": "OK", "itemDesc": "合格", "required": True}],
                    "ownerRole": "R6",
                    "slaHours": 24,
                }
            ],
        },
    )
    body = res.json()
    assert body["code"] == 0
    return body["data"]["id"]


def create_topic(auth: dict, title: str = "周末热点口播") -> dict:
    res = client.post(
        "/admin-api/ims/content/topic",
        headers=auth,
        json={
            "title": title,
            "description": "内容要求：30 秒口播，突出赛程",
            "sourceType": "HOTSPOT",
        },
    )
    body = res.json()
    assert body["code"] == 0
    return body["data"]


def test_topic_create_list_and_approve_gate():
    auth = headers()
    empty = client.get("/admin-api/ims/content/topic/list", headers=auth)
    assert empty.json()["code"] == 0
    assert empty.json()["data"]["total"] == 0

    bad = client.post(
        "/admin-api/ims/content/topic",
        headers=auth,
        json={"title": "", "description": "要求", "sourceType": "HOTSPOT"},
    )
    assert bad.json()["code"] == 1500

    created = create_topic(auth)
    assert created["topicNo"].startswith("TP")
    assert created["topicStatus"] == "PENDING_REVIEW"
    assert created["canCreateTask"] is False
    assert created["contentProjectId"] is None

    listed = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"keyword": "周末热点", "topicStatus": "PENDING_REVIEW", "sourceType": "HOTSPOT"},
    )
    assert listed.json()["code"] == 0
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["list"][0]["id"] == created["id"]

    sop_id = create_sop(auth)
    missing = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "APPROVE_PROJECT"},
    )
    assert missing.json()["code"] == 1052
    assert missing.json()["msg"] == "选题立项缺少 SOP 或计划发布日"

    no_sop = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "APPROVE_PROJECT", "planPublishDate": "2026-12-01"},
    )
    assert no_sop.json()["code"] == 1052

    no_date = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "APPROVE_PROJECT", "sopId": sop_id},
    )
    assert no_date.json()["code"] == 1052

    unknown_sop = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "APPROVE_PROJECT", "planPublishDate": "2026-12-01", "sopId": 999999},
    )
    assert unknown_sop.json()["code"] == 1051

    still = client.get("/admin-api/ims/content/topic/list", headers=auth, params={"keyword": "周末热点"})
    assert still.json()["data"]["list"][0]["topicStatus"] == "PENDING_REVIEW"
    assert still.json()["data"]["list"][0]["canCreateTask"] is False

    approved = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={
            "action": "APPROVE_PROJECT",
            "planPublishDate": "2026-12-01",
            "sopId": sop_id,
            "reviewOpinion": "按内容要求立项",
        },
    )
    assert approved.json()["code"] == 0
    assert approved.json()["data"] is None

    again = client.get("/admin-api/ims/content/topic/list", headers=auth, params={"topicNo": created["topicNo"]})
    row = again.json()["data"]["list"][0]
    assert row["topicStatus"] == "APPROVED_PROJECT"
    assert row["canCreateTask"] is True
    assert row["sopId"] == sop_id
    assert row["sopName"] == "立项 SOP"
    assert row["planPublishDate"] == "2026-12-01"
    assert row["contentProjectId"]

    project = client.get("/admin-api/ims/content", headers=auth, params={"title": "周末热点口播"})
    assert project.json()["code"] == 0
    assert project.json()["data"]["list"][0]["id"] == row["contentProjectId"]

    locked = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "REJECT", "reviewOpinion": "已立项不可再驳回"},
    )
    assert locked.json()["code"] == 1504


def test_topic_reject_blocks_task():
    auth = headers()
    created = create_topic(auth, "落选选题")
    empty_opinion = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "REJECT"},
    )
    assert empty_opinion.json()["code"] == 1500

    rejected = client.put(
        f"/admin-api/ims/content/topic/{created['id']}/review",
        headers=auth,
        json={"action": "REJECT", "reviewOpinion": "与内容要求不符"},
    )
    assert rejected.json()["code"] == 0

    listed = client.get("/admin-api/ims/content/topic/list", headers=auth, params={"topicStatus": "REJECTED"})
    row = listed.json()["data"]["list"][0]
    assert row["id"] == created["id"]
    assert row["topicStatus"] == "REJECTED"
    assert row["canCreateTask"] is False
    assert row["reviewOpinion"] == "与内容要求不符"
    assert row["contentProjectId"] is None


def approve(auth: dict, topic_id: int, sop_id: int, plan_date: str) -> None:
    res = client.put(
        f"/admin-api/ims/content/topic/{topic_id}/review",
        headers=auth,
        json={"action": "APPROVE_PROJECT", "planPublishDate": plan_date, "sopId": sop_id, "reviewOpinion": "排期"},
    )
    assert res.json()["code"] == 0


def gantt(auth: dict, start: str, end: str, account_id: int | None = None):
    params: list[tuple[str, str]] = [("timeRange", start), ("timeRange", end)]
    if account_id is not None:
        params.append(("accountId", str(account_id)))
    return client.get("/admin-api/ims/content/topic/gantt", headers=auth, params=params)


def test_topic_gantt_range_and_same_account_conflict():
    from app.core import SessionLocal
    from app.models import ContentPublish
    from app.ops_db import ops_session
    from app.ops_models import PlatformAccount

    auth = headers()
    sop_id = create_sop(auth, "甘特 SOP")
    first = create_topic(auth, "甘特甲")
    second = create_topic(auth, "甘特乙")
    third = create_topic(auth, "甘特丙")
    other_day = create_topic(auth, "甘特丁")
    pending = client.post(
        "/admin-api/ims/content/topic",
        headers=auth,
        json={
            "title": "甘特待评审",
            "description": "内容要求：尚未立项",
            "sourceType": "ORIGINAL",
            "planPublishDate": "2026-12-02",
        },
    )
    assert pending.json()["code"] == 0

    approve(auth, first["id"], sop_id, "2026-12-01")
    approve(auth, second["id"], sop_id, "2026-12-01")
    approve(auth, third["id"], sop_id, "2026-12-01")
    approve(auth, other_day["id"], sop_id, "2026-12-20")

    missing = client.get("/admin-api/ims/content/topic/gantt", headers=auth)
    assert missing.json()["code"] == 1500
    reversed_range = gantt(auth, "2026-12-07", "2026-12-01")
    assert reversed_range.json()["code"] == 1500
    bad_day = gantt(auth, "2026-13-01", "2026-12-07")
    assert bad_day.json()["code"] == 1500

    window = gantt(auth, "2026-12-01", "2026-12-07")
    assert window.json()["code"] == 0
    items = window.json()["data"]["items"]
    assert [row["title"] for row in items] == ["甘特甲", "甘特乙", "甘特丙", "甘特待评审"]
    assert all(row["conflictHint"] is None for row in items)
    assert items[0]["planPublishDate"] == "2026-12-01"
    assert items[0]["topicStatus"] == "APPROVED_PROJECT"
    assert items[0]["sopName"] == "甘特 SOP"
    assert items[0]["topicNo"].startswith("TP")
    assert items[-1]["topicStatus"] == "PENDING_REVIEW"
    assert items[-1]["sopName"] is None

    listed = client.get("/admin-api/ims/content/topic/list", headers=auth, params={"keyword": "甘特甲"})
    project_first = listed.json()["data"]["list"][0]["contentProjectId"]
    project_second = client.get("/admin-api/ims/content/topic/list", headers=auth, params={"keyword": "甘特乙"}).json()["data"]["list"][0][
        "contentProjectId"
    ]
    project_third = client.get("/admin-api/ims/content/topic/list", headers=auth, params={"keyword": "甘特丙"}).json()["data"]["list"][0][
        "contentProjectId"
    ]

    ops = ops_session()
    try:
        shared = PlatformAccount(
            account_no="AC-GANTT-140",
            account_name="甘特共享号",
            platform_type="DOUYIN",
            status="IN_USE",
            tenant_id=0,
        )
        alone = PlatformAccount(
            account_no="AC-GANTT-140B",
            account_name="甘特独享号",
            platform_type="DOUYIN",
            status="IN_USE",
            tenant_id=0,
        )
        ops.add(shared)
        ops.add(alone)
        ops.commit()
        shared_id = int(shared.id)
        alone_id = int(alone.id)
    finally:
        ops.close()

    db = SessionLocal()
    try:
        db.add_all(
            [
                ContentPublish(
                    publish_no="PB-GANTT-140A",
                    content_project_id=project_first,
                    account_id=shared_id,
                    account_no="AC-GANTT-140",
                    platform="DOUYIN",
                    plan_publish_at="2026-12-01T10:00:00+08:00",
                    caption="甲",
                    tenant_id=0,
                ),
                ContentPublish(
                    publish_no="PB-GANTT-140B",
                    content_project_id=project_second,
                    account_id=shared_id,
                    account_no="AC-GANTT-140",
                    platform="DOUYIN",
                    plan_publish_at="2026-12-01T11:00:00+08:00",
                    caption="乙",
                    tenant_id=0,
                ),
                ContentPublish(
                    publish_no="PB-GANTT-140C",
                    content_project_id=project_third,
                    account_id=alone_id,
                    account_no="AC-GANTT-140B",
                    platform="DOUYIN",
                    plan_publish_at="2026-12-01T12:00:00+08:00",
                    caption="丙",
                    tenant_id=0,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    conflicted = gantt(auth, "2026-12-01", "2026-12-07")
    by_title = {row["title"]: row for row in conflicted.json()["data"]["items"]}
    assert by_title["甘特甲"]["conflictHint"] == "同账号同日超量"
    assert by_title["甘特乙"]["conflictHint"] == "同账号同日超量"
    assert by_title["甘特丙"]["conflictHint"] is None
    assert by_title["甘特待评审"]["conflictHint"] is None

    shared_only = gantt(auth, "2026-12-01", "2026-12-07", shared_id)
    assert [row["title"] for row in shared_only.json()["data"]["items"]] == ["甘特甲", "甘特乙"]
    assert all(row["conflictHint"] == "同账号同日超量" for row in shared_only.json()["data"]["items"])

    alone_only = gantt(auth, "2026-12-01", "2026-12-07", alone_id)
    assert [row["title"] for row in alone_only.json()["data"]["items"]] == ["甘特丙"]
    assert alone_only.json()["data"]["items"][0]["conflictHint"] is None

    later = gantt(auth, "2026-12-20", "2026-12-20")
    assert [row["title"] for row in later.json()["data"]["items"]] == ["甘特丁"]
    assert later.json()["data"]["items"][0]["conflictHint"] is None
