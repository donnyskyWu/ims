import os

os.environ["IMS_DB"] = "ims_test"

from fastapi.testclient import TestClient

from app.audit import publish_notify
from app.core import Base, SessionLocal, engine
from app.main import app, init_db


client = TestClient(app)


def login(username="admin", password="Admin@123") -> str:
    res = client.post("/admin-api/ims/auth/login", json={"username": username, "password": password})
    assert res.json()["code"] == 0
    return res.json()["data"]["accessToken"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_success_and_failure_are_logged():
    bad = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.json()["code"] == 1006
    token = login()
    page = client.get(
        "/admin-api/ims/system/login-log/page",
        headers=auth(token),
        params={"pageNo": 1, "pageSize": 10},
    )
    body = page.json()
    assert body["code"] == 0
    actions = [row["action"] for row in body["data"]["list"]]
    assert "登录失败" in actions
    assert "登录成功" in actions
    assert body["data"]["total"] >= 2
    assert all(row["user"] == "admin" for row in body["data"]["list"])


def test_protected_write_creates_operate_log_and_pages():
    token = login()
    headers = auth(token)
    saved = client.put(
        "/admin-api/ims/system/param",
        headers=headers,
        json={"paramKey": "dingtalk.sso.enabled", "paramValue": True},
    )
    assert saved.json()["code"] == 0
    client.put(
        "/admin-api/ims/system/param",
        headers=headers,
        json={"paramKey": "dingtalk.sso.enabled", "paramValue": False},
    )
    page = client.get(
        "/admin-api/ims/system/operate-log/page",
        headers=headers,
        params={"pageNo": 1, "pageSize": 10, "keyword": "param"},
    )
    data = page.json()["data"]
    assert data["total"] >= 2
    assert data["list"][0]["action"] == "更新参数"
    assert data["list"][0]["path"].startswith("PUT /system/param")
    assert data["list"][0]["module"] == "系统"
    assert data["pageNo"] == 1
    assert data["pageSize"] == 10
    filtered = client.get(
        "/admin-api/ims/system/operate-log/page",
        headers=headers,
        params={"module": "业务"},
    )
    assert filtered.json()["data"]["total"] == 0
    anonymous = client.get("/admin-api/ims/system/operate-log/page")
    assert anonymous.status_code == 401


def test_operate_log_second_page():
    token = login()
    headers = auth(token)
    for index in range(11):
        created = client.post(
            "/admin-api/ims/system/user",
            headers=headers,
            json={
                "username": f"log{index}",
                "nickname": f"日志{index}",
                "mobile": f"1370000{index:04d}",
                "password": "Pass@123",
            },
        )
        assert created.json()["code"] == 0
    first = client.get(
        "/admin-api/ims/system/operate-log/page",
        headers=headers,
        params={"pageNo": 1, "pageSize": 10},
    ).json()["data"]
    second = client.get(
        "/admin-api/ims/system/operate-log/page",
        headers=headers,
        params={"pageNo": 2, "pageSize": 10},
    ).json()["data"]
    assert first["total"] >= 11
    assert len(first["list"]) == 10
    assert len(second["list"]) >= 1
    assert first["list"][0]["id"] != second["list"][0]["id"]


def test_notify_page_dedup_and_filter():
    token = login()
    headers = auth(token)
    db = SessionLocal()
    try:
        first = publish_notify(
            db,
            event_type="TASK_PENDING",
            biz_key="TK-881",
            receiver="孙倩",
            channel="BOTH",
            tenant_id=0,
        )
        again = publish_notify(
            db,
            event_type="TASK_PENDING",
            biz_key="TK-881",
            receiver="孙倩",
            channel="BOTH",
            tenant_id=0,
        )
        publish_notify(
            db,
            event_type="CONTENT_REVIEW_SUBMIT",
            biz_key="8821",
            receiver="李澈",
            channel="IN_APP",
            tenant_id=0,
        )
        db.commit()
    finally:
        db.close()
    assert first["deduped"] is False
    assert again["deduped"] is True
    assert first["id"] == again["id"]
    page = client.get("/admin-api/ims/system/notify/page", headers=headers, params={"pageNo": 1, "pageSize": 10})
    data = page.json()["data"]
    assert data["total"] == 2
    kinds = {row["eventType"] for row in data["list"]}
    assert kinds == {"TASK_PENDING", "CONTENT_REVIEW_SUBMIT"}
    hit = next(row for row in data["list"] if row["eventType"] == "TASK_PENDING")
    assert hit["bizKey"] == "TK-881"
    assert hit["receiver"] == "孙倩"
    assert hit["channel"] == "站内+钉钉"
    assert hit["status"] == "已送达"
    filtered = client.get(
        "/admin-api/ims/system/notify/page",
        headers=headers,
        params={"eventType": "TASK_PENDING", "channel": "站内"},
    ).json()["data"]
    assert filtered["total"] == 0
    kept = client.get(
        "/admin-api/ims/system/notify/page",
        headers=headers,
        params={"eventType": "CONTENT_REVIEW_SUBMIT", "channel": "站内"},
    ).json()["data"]
    assert kept["total"] == 1
