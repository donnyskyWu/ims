"""#240 · 自定义查询空结果/日期与行数边、订阅时刻、分享驳回说明与非整有效期。"""

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


def seed_account_entity(auth: dict) -> None:
    created = client.post(
        "/admin-api/ims/collect/metadata/create",
        headers=auth,
        json={
            "entityCode": "PLATFORM_ACCOUNT",
            "entityName": "平台账号",
            "tableName": "oa_platform_account",
            "status": "ENABLED",
        },
    )
    assert created.json()["code"] == 0
    listed = client.get("/admin-api/ims/collect/metadata/list", headers=auth)
    entity_id = listed.json()["data"]["list"][0]["id"]
    saved = client.put(
        f"/admin-api/ims/collect/metadata/{entity_id}/fields",
        headers=auth,
        json={
            "fields": [
                {
                    "fieldCode": "account_no",
                    "columnName": "account_no",
                    "displayName": "账号编号",
                    "queryConditionType": "EQ",
                },
                {
                    "fieldCode": "created_at",
                    "columnName": "created_at",
                    "displayName": "创建时间",
                    "queryConditionType": "RANGE",
                },
            ]
        },
    )
    assert saved.json()["code"] == 0


def new_report(auth: dict, name: str) -> int:
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": name, "reportType": "REPORT", "category": "内容分析"},
    )
    assert created.json()["code"] == 0
    return created.json()["data"]["id"]


def test_query_limit_date_edges_and_empty_result():
    auth = headers()
    seed_account_entity(auth)

    too_small = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "上限过小",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {"selectFields": ["account_no"], "limit": 0},
        },
    )
    assert too_small.json()["code"] == 1001
    assert too_small.json()["msg"] == "行数上限须为 1~1000"

    too_big = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "上限过大",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {"selectFields": ["account_no"], "limit": 1001},
        },
    )
    assert too_big.json()["code"] == 1001
    assert too_big.json()["msg"] == "行数上限须为 1~1000"

    flipped = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "日期颠倒",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {
                "selectFields": ["created_at"],
                "conditions": [{"fieldCode": "created_at", "operator": "RANGE", "value": "2026-09-20,2026-09-01"}],
                "limit": 20,
            },
        },
    )
    assert flipped.json()["code"] == 0
    flipped_id = flipped.json()["data"]["id"]
    flipped_run = client.post(f"/admin-api/ims/bi/query/{flipped_id}/run", headers=auth)
    assert flipped_run.json()["code"] == 1001
    assert flipped_run.json()["msg"] == "开始日期不能晚于结束日期"

    one_side = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "单侧日期",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {
                "selectFields": ["created_at"],
                "conditions": [{"fieldCode": "created_at", "operator": "RANGE", "value": "2026-09-01,"}],
                "limit": 20,
            },
        },
    )
    one_id = one_side.json()["data"]["id"]
    one_run = client.post(f"/admin-api/ims/bi/query/{one_id}/run", headers=auth)
    assert one_run.json()["code"] == 1001
    assert one_run.json()["msg"] == "请同时填写开始和结束日期"

    missing = client.post(
        "/admin-api/ims/bi/query",
        headers=auth,
        json={
            "queryName": "无命中",
            "entityCode": "PLATFORM_ACCOUNT",
            "config": {
                "selectFields": ["account_no"],
                "conditions": [{"fieldCode": "account_no", "operator": "EQ", "value": "NO-SUCH-240"}],
                "limit": 20,
            },
        },
    )
    assert missing.json()["code"] == 0
    miss_id = missing.json()["data"]["id"]
    ran = client.post(f"/admin-api/ims/bi/query/{miss_id}/run", headers=auth)
    body = ran.json()
    assert body["code"] == 0
    assert body["data"]["rows"] == []
    assert body["data"]["empty"] is True
    assert body["data"]["emptyReason"] == "当前条件下暂无数据"

    filtered = client.get(
        "/admin-api/ims/bi/query/page",
        headers=auth,
        params={"queryName": "no-such-query-240", "pageNo": 1, "pageSize": 10},
    )
    assert filtered.json()["code"] == 0
    assert filtered.json()["data"]["total"] == 0


def test_subscribe_clock_share_reject_note_and_fractional_days():
    auth = headers()
    rid = new_report(auth, "切片240订阅")

    bad_clock = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "坏时刻", "reportId": rid, "period": "DAY", "pushTime": "25:99"},
    )
    assert bad_clock.json()["code"] == 1001
    assert bad_clock.json()["msg"] == "推送时刻应为 HH:mm"

    garbage = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "乱写时刻", "reportId": rid, "period": "WEEK", "pushTime": "abc"},
    )
    assert garbage.json()["code"] == 1001
    assert garbage.json()["msg"] == "推送时刻应为 HH:mm"

    weekly = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "周一时刻", "reportId": rid, "period": "WEEK", "pushTime": "周一 09:00"},
    )
    assert weekly.json()["code"] == 0
    assert weekly.json()["data"]["pushTime"] == "周一 09:00"

    blank = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "默认为空时刻", "reportId": rid, "period": "DAY", "pushTime": ""},
    )
    assert blank.json()["code"] == 0
    assert blank.json()["data"]["pushTime"] == "09:00"

    fraction = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": True, "expireDays": 7.5},
    )
    assert fraction.json()["code"] == 1197
    assert fraction.json()["msg"] == "分享有效期须为 7~30 天"

    pending = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": True, "expireDays": 7},
    )
    assert pending.json()["code"] == 0
    link_id = pending.json()["data"]["id"]
    bare = client.put(
        f"/admin-api/ims/bi/subscribe/share-approval/{link_id}",
        headers=auth,
        json={"approvalStatus": "REJECTED"},
    )
    assert bare.json()["code"] == 1001
    assert bare.json()["msg"] == "驳回说明必填"

    rejected = client.put(
        f"/admin-api/ims/bi/subscribe/share-approval/{link_id}",
        headers=auth,
        json={"approvalStatus": "REJECTED", "note": "成本口径未确认"},
    )
    assert rejected.json()["code"] == 0
    assert rejected.json()["data"]["approvalStatus"] == "REJECTED"
    assert rejected.json()["data"]["approvalNote"] == "成本口径未确认"
