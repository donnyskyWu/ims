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
    assert row["contentProjectStatus"] == ""
    assert row["contentStatusChain"] == []


def test_topic_filter_edit_revive_and_cancel():
    auth = headers()
    hotspot = create_topic(auth, "热点口播甲")
    talent = client.post(
        "/admin-api/ims/content/topic",
        headers=auth,
        json={"title": "达人探店乙", "description": "内容要求：探店", "sourceType": "TALENT"},
    ).json()["data"]

    by_source = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"sourceType": "TALENT", "keyword": "探店"},
    )
    assert by_source.json()["data"]["total"] == 1
    assert by_source.json()["data"]["list"][0]["id"] == talent["id"]

    by_no = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": hotspot["topicNo"]},
    )
    assert by_no.json()["data"]["total"] == 1
    assert by_no.json()["data"]["list"][0]["title"] == "热点口播甲"

    by_owner = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"submitterUserId": hotspot["submitterUserId"]},
    )
    assert by_owner.json()["data"]["total"] == 2
    other = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"submitterUserId": 999999},
    )
    assert other.json()["data"]["total"] == 0

    locked_edit = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}",
        headers=auth,
        json={"title": "", "description": "要求", "sourceType": "HOTSPOT"},
    )
    assert locked_edit.json()["code"] == 1500

    edited = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}",
        headers=auth,
        json={
            "title": "热点口播甲-改",
            "description": "内容要求：改后口播",
            "sourceType": "BRAND",
            "planPublishDate": "2026-12-20",
        },
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"] is None
    changed = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": hotspot["topicNo"]},
    ).json()["data"]["list"][0]
    assert changed["title"] == "热点口播甲-改"
    assert changed["sourceType"] == "BRAND"
    assert changed["description"] == "内容要求：改后口播"
    assert changed["planPublishDate"] == "2026-12-20"
    assert changed["topicStatus"] == "PENDING_REVIEW"
    assert changed["topicNo"] == hotspot["topicNo"]

    bad_sop = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}",
        headers=auth,
        json={"title": "不应写入", "description": "内容要求", "sourceType": "HOTSPOT", "sopId": 999999},
    )
    assert bad_sop.json()["code"] == 1051
    still = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": hotspot["topicNo"]},
    ).json()["data"]["list"][0]
    assert still["title"] == "热点口播甲-改"

    rejected = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}/review",
        headers=auth,
        json={"action": "REJECT", "reviewOpinion": "先归档"},
    )
    assert rejected.json()["code"] == 0
    edit_rejected = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}",
        headers=auth,
        json={"title": "落选不可改", "description": "内容要求", "sourceType": "TALENT"},
    )
    assert edit_rejected.json()["code"] == 1504

    revive_pending = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}/review",
        headers=auth,
        json={"action": "REVIVE"},
    )
    assert revive_pending.json()["code"] == 1504

    revived = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}/review",
        headers=auth,
        json={"action": "REVIVE"},
    )
    assert revived.json()["code"] == 0
    back = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": talent["topicNo"]},
    ).json()["data"]["list"][0]
    assert back["topicStatus"] == "PENDING_REVIEW"
    assert back["reviewOpinion"] == "先归档"
    assert back["canCreateTask"] is False
    assert back["contentProjectId"] is None

    again = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}",
        headers=auth,
        json={"title": "达人探店乙-复活后", "description": "内容要求：再评", "sourceType": "TALENT"},
    )
    assert again.json()["code"] == 0

    empty_cancel = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}/review",
        headers=auth,
        json={"action": "CANCEL"},
    )
    assert empty_cancel.json()["code"] == 1500
    cancelled = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}/review",
        headers=auth,
        json={"action": "CANCEL", "reviewOpinion": "本期不做"},
    )
    assert cancelled.json()["code"] == 0
    cancelled_row = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicStatus": "CANCELLED", "topicNo": hotspot["topicNo"]},
    ).json()["data"]["list"][0]
    assert cancelled_row["topicStatus"] == "CANCELLED"
    assert cancelled_row["reviewOpinion"] == "本期不做"
    assert cancelled_row["canCreateTask"] is False
    revive_cancelled = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}/review",
        headers=auth,
        json={"action": "REVIVE"},
    )
    assert revive_cancelled.json()["code"] == 1504
    edit_cancelled = client.put(
        f"/admin-api/ims/content/topic/{hotspot['id']}",
        headers=auth,
        json={"title": "取消不可改", "description": "内容要求", "sourceType": "BRAND"},
    )
    assert edit_cancelled.json()["code"] == 1504

    sop_id = create_sop(auth, "详情 SOP")
    approved = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}/review",
        headers=auth,
        json={
            "action": "APPROVE_PROJECT",
            "planPublishDate": "2026-12-02",
            "sopId": sop_id,
            "reviewOpinion": "复活后立项",
        },
    )
    assert approved.json()["code"] == 0
    project_row = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": talent["topicNo"]},
    ).json()["data"]["list"][0]
    assert project_row["topicStatus"] == "APPROVED_PROJECT"
    assert project_row["contentProjectStatus"] == "DRAFT"
    assert project_row["contentStatusChain"][0]["status"] == "DRAFT"
    assert project_row["contentStatusChain"][0]["current"] is True
    assert project_row["contentStatusChain"][0]["label"] == "草稿"
    cancel_approved = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}/review",
        headers=auth,
        json={"action": "CANCEL", "reviewOpinion": "已立项不可取消"},
    )
    assert cancel_approved.json()["code"] == 1504
    edit_approved = client.put(
        f"/admin-api/ims/content/topic/{talent['id']}",
        headers=auth,
        json={"title": "已立项不可改", "description": "内容要求", "sourceType": "TALENT"},
    )
    assert edit_approved.json()["code"] == 1504


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


def test_topic_gantt_single_day_pending_and_unknown_account():
    """未立项但已填计划发布日的选题落在单日区间内；不存在的账号返回空列表。"""
    auth = headers()
    pending = client.post(
        "/admin-api/ims/content/topic",
        headers=auth,
        json={
            "title": "单日待评审",
            "description": "内容要求：甘特边界",
            "sourceType": "ORIGINAL",
            "planPublishDate": "2026-11-18",
        },
    )
    assert pending.json()["code"] == 0
    assert pending.json()["data"]["topicStatus"] == "PENDING_REVIEW"
    assert pending.json()["data"]["planPublishDate"] == "2026-11-18"

    bare = client.post(
        "/admin-api/ims/content/topic",
        headers=auth,
        json={
            "title": "无发布日",
            "description": "内容要求：不进甘特",
            "sourceType": "ORIGINAL",
        },
    )
    assert bare.json()["code"] == 0

    one = gantt(auth, "2026-11-18", "2026-11-18")
    assert one.json()["code"] == 0
    items = one.json()["data"]["items"]
    assert [row["title"] for row in items] == ["单日待评审"]
    assert items[0]["topicStatus"] == "PENDING_REVIEW"
    assert items[0]["planPublishDate"] == "2026-11-18"
    assert items[0]["conflictHint"] is None

    missing_account = gantt(auth, "2026-11-18", "2026-11-18", 999_999)
    assert missing_account.json()["code"] == 0
    assert missing_account.json()["data"]["items"] == []

    other_day = gantt(auth, "2026-11-19", "2026-11-19")
    assert other_day.json()["code"] == 0
    assert other_day.json()["data"]["items"] == []


def test_topic_list_filter_miss_edges():
    """编号需完整匹配；空白编号仍命中；来源非法 1500；关键词与来源同时无命中为空页。"""
    auth = headers()
    created = create_topic(auth, "筛选边角口播")

    missing_no = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": "TP-NO-SUCH"},
    )
    assert missing_no.json()["code"] == 0
    assert missing_no.json()["data"]["total"] == 0
    assert missing_no.json()["data"]["list"] == []

    padded = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": f"  {created['topicNo']}  "},
    )
    assert padded.json()["code"] == 0
    assert padded.json()["data"]["total"] == 1
    assert padded.json()["data"]["list"][0]["id"] == created["id"]

    partial = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"topicNo": created["topicNo"][:-2]},
    )
    assert partial.json()["code"] == 0
    assert partial.json()["data"]["total"] == 0

    bad_source = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"sourceType": "UNKNOWN"},
    )
    assert bad_source.json()["code"] == 1500

    missed = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"sourceType": "BRAND", "keyword": "不存在的筛选边角"},
    )
    assert missed.json()["code"] == 0
    assert missed.json()["data"]["total"] == 0

    keyword_hit = client.get(
        "/admin-api/ims/content/topic/list",
        headers=auth,
        params={"keyword": "  筛选边角  "},
    )
    assert keyword_hit.json()["code"] == 0
    assert keyword_hit.json()["data"]["total"] == 1
    assert keyword_hit.json()["data"]["list"][0]["title"] == "筛选边角口播"
