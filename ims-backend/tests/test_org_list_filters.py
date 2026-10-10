"""组织人员、同步事件、岗位供给规则的已有列表筛选。"""

import json
import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.core import SessionLocal
from app.dingtalk_crypto import pack
from app.main import app
from app.org_sync import process_due


client = TestClient(app)


def login() -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def post_event(payload: dict, nonce: str):
    body, headers = pack(json.dumps(payload, ensure_ascii=False), "1700000000000", nonce)
    return client.post("/admin-api/ims/auth/org/event", json=body, headers=headers)


def consume() -> None:
    db = SessionLocal()
    try:
        process_due(db)
        db.commit()
    finally:
        db.close()


def enabled_role_id(token: str) -> int:
    rows = client.get("/admin-api/ims/system/role/list", headers=auth(token)).json()["data"]
    for row in rows:
        if row["status"] == "ENABLED":
            return row["id"]
    raise AssertionError("no enabled role")


def test_org_user_and_event_filters():
    payload = {
        "eventType": "hire",
        "dingtalkEventId": "evt-filter-212",
        "unionId": "union-filter-212",
        "payloadJson": {
            "dingtalkUserId": "dt-filter-212",
            "nickname": "筛选新人",
            "mobile": "13700002122",
            "deptIds": [212],
            "deptNames": ["筛选部"],
            "afterDept": "筛选部",
        },
    }
    assert post_event(payload, "nonce-org-212").json()["code"] == 0
    consume()
    token = login()
    headers = auth(token)

    matched = client.get(
        "/admin-api/ims/auth/org/users",
        headers=headers,
        params={"keyword": "筛选新人", "deptId": 212, "syncStatus": "SUCCESS", "pageNo": 1, "pageSize": 10},
    )
    assert matched.json()["code"] == 0
    rows = matched.json()["data"]["list"]
    assert matched.json()["data"]["total"] == 1
    assert rows[0]["nickname"] == "筛选新人"
    assert rows[0]["syncStatus"] == "SUCCESS"

    pending = client.get(
        "/admin-api/ims/auth/org/users",
        headers=headers,
        params={"keyword": "筛选新人", "syncStatus": "PENDING"},
    )
    assert pending.json()["data"]["total"] == 0

    other_dept = client.get(
        "/admin-api/ims/auth/org/users",
        headers=headers,
        params={"keyword": "筛选新人", "deptId": 9},
    )
    assert other_dept.json()["data"]["total"] == 0

    hired = client.get(
        "/admin-api/ims/auth/org/events",
        headers=headers,
        params={"eventType": "hire", "syncStatus": "SUCCESS"},
    )
    assert any(row["dingtalkEventId"] == "evt-filter-212" for row in hired.json()["data"]["list"])

    resigned = client.get(
        "/admin-api/ims/auth/org/events",
        headers=headers,
        params={"eventType": "resign"},
    )
    assert all(row["dingtalkEventId"] != "evt-filter-212" for row in resigned.json()["data"]["list"])

    future = client.get(
        "/admin-api/ims/auth/org/events",
        headers=headers,
        params=[
            ("eventType", "hire"),
            ("timeRange", "2099-01-01 00:00:00"),
            ("timeRange", "2099-01-02 23:59:59"),
        ],
    )
    assert future.json()["code"] == 0
    assert future.json()["data"]["total"] == 0


def test_position_rule_list_filters():
    token = login()
    headers = auth(token)
    role_id = enabled_role_id(token)
    created = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "筛选供给甲", "dingtalkPosition": "筛选岗甲", "grantRoleIds": [role_id]},
    )
    assert created.json()["code"] == 0
    rule_id = created.json()["data"]["id"]
    other = client.post(
        "/admin-api/ims/auth/position/rule",
        headers=headers,
        json={"ruleName": "筛选供给乙", "dingtalkPosition": "筛选岗乙", "grantRoleIds": [role_id]},
    )
    assert other.json()["code"] == 0
    edited = client.put(
        f"/admin-api/ims/auth/position/rule/{rule_id}",
        headers=headers,
        json={"ruleName": "筛选供给甲", "dingtalkPosition": "筛选岗甲", "grantRoleIds": [role_id]},
    )
    assert edited.json()["code"] == 0
    assert edited.json()["data"]["version"] == 2

    by_name = client.get(
        "/admin-api/ims/auth/position/rules",
        headers=headers,
        params={"keyword": "供给甲", "pageNo": 1, "pageSize": 10},
    )
    assert by_name.json()["data"]["total"] == 2
    assert {row["status"] for row in by_name.json()["data"]["list"]} == {"ENABLED", "DISABLED"}

    by_position = client.get(
        "/admin-api/ims/auth/position/rules",
        headers=headers,
        params={"dingtalkPosition": "筛选岗乙"},
    )
    assert by_position.json()["data"]["total"] == 1
    assert by_position.json()["data"]["list"][0]["ruleName"] == "筛选供给乙"

    by_role = client.get(
        "/admin-api/ims/auth/position/rules",
        headers=headers,
        params={"grantRoleId": role_id, "keyword": "筛选供给"},
    )
    assert by_role.json()["data"]["total"] == 3

    missing_role = client.get(
        "/admin-api/ims/auth/position/rules",
        headers=headers,
        params={"grantRoleId": 99999, "keyword": "筛选供给"},
    )
    assert missing_role.json()["data"]["total"] == 0

    disabled = client.get(
        "/admin-api/ims/auth/position/rules",
        headers=headers,
        params={"keyword": "筛选供给甲", "status": "DISABLED"},
    )
    assert disabled.json()["data"]["total"] == 1
    assert disabled.json()["data"]["list"][0]["version"] == 1
