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
