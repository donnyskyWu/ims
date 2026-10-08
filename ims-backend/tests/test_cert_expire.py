"""#61 · CERT-002 到期预警：T−30 黄 / T−7 红 / T−0 锁定 + 工作台提醒。"""

import os
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app
from app.cert_expire import warn_level


client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_warn_level_boundaries():
    assert warn_level(31) is None
    assert warn_level(30) == "YELLOW"
    assert warn_level(8) == "YELLOW"
    assert warn_level(7) == "RED"
    assert warn_level(1) == "RED"
    assert warn_level(0) == "LOCKED"
    assert warn_level(-2) == "LOCKED"


def _upload(auth: dict, holder: str, days: int, number: str):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": "IDCARD",
            "certNoPlain": number,
            "fileKey": "local/cert/upload",
            "issueDate": "2020-01-01",
            "expireDate": (today + timedelta(days=days)).isoformat(),
        },
    )


def test_cert_expire_scan_three_levels_workbench_and_no_repeat():
    auth = headers()
    samples = [
        ("E2E黄证", 30, "YELLOW", "EXPIRING", "110101199001010031"),
        ("E2E红证", 7, "RED", "EXPIRING", "110101199001010007"),
        ("E2E锁证", 0, "LOCKED", "EXPIRED", "110101199001010000"),
    ]
    for holder, days, _level, _status, number in samples:
        created = _upload(auth, holder, days, number)
        body = created.json()
        assert body["code"] == 0, body
        assert body["data"]["status"] == "PENDING_REVIEW"
        assert number not in created.text
        assert "certNoEncrypted" not in created.text
        reviewed = client.put(
            f"/admin-api/ims/cert/archive/{body['data']['id']}/review",
            headers=auth,
            json={"action": "APPROVE"},
        )
        assert reviewed.json()["code"] == 0
        again = client.put(
            f"/admin-api/ims/cert/archive/{body['data']['id']}/review",
            headers=auth,
            json={"action": "APPROVE"},
        )
        assert again.json()["code"] == 1033

    dup = _upload(auth, "E2E黄证", 30, "110101199001019999")
    assert dup.json()["code"] == 1032

    quiet = _upload(auth, "E2E远证", 40, "110101199001010040")
    assert quiet.json()["code"] == 0
    approved = client.put(
        f"/admin-api/ims/cert/archive/{quiet.json()['data']['id']}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )
    assert approved.json()["code"] == 0

    scan = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    payload = scan.json()
    assert payload["code"] == 0, payload
    assert payload["data"]["created"] == 3
    assert payload["data"]["scanTaskId"].startswith("SCAN-")

    listed = client.get("/admin-api/ims/cert/expire/list", headers=auth, params={"pageNo": 1, "pageSize": 20})
    rows = {row["holderName"]: row for row in listed.json()["data"]["list"]}
    assert "E2E远证" not in rows
    for holder, _days, level, _status, number in samples:
        assert rows[holder]["level"] == level
        assert number not in listed.text
    assert rows["E2E锁证"]["status"] == "EXPIRED_LOCKED"
    assert rows["E2E黄证"]["status"] == "WARNING"
    assert rows["E2E黄证"]["remainDays"] == 30
    assert rows["E2E红证"]["remainDays"] == 7
    assert rows["E2E锁证"]["remainDays"] == 0

    stats = client.get("/admin-api/ims/cert/expire/stats", headers=auth)
    by_level = stats.json()["data"]["byLevel"]
    assert by_level["YELLOW"] == 1
    assert by_level["RED"] == 1
    assert by_level["LOCKED"] == 1

    page = client.get("/admin-api/ims/corp/resource/certificate/page", headers=auth, params={"holderName": "E2E锁证"})
    assert page.json()["data"]["list"][0]["status"] == "EXPIRED"
    yellow = client.get("/admin-api/ims/corp/resource/certificate/page", headers=auth, params={"holderName": "E2E黄证"})
    assert yellow.json()["data"]["list"][0]["status"] == "EXPIRING"

    messages = client.get("/admin-api/ims/auth/workbench/messages", headers=auth, params={"pageNo": 1, "pageSize": 20})
    titles = [row["title"] for row in messages.json()["data"]["list"]]
    assert "证件黄色预警：E2E黄证" in titles
    assert "证件红色预警：E2E红证" in titles
    assert "证件锁定预警：E2E锁证" in titles
    todos = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"pageNo": 1, "pageSize": 20, "status": "PENDING"},
    )
    todo_titles = [row["title"] for row in todos.json()["data"]["list"]]
    assert "证件黄色预警：E2E黄证" in todo_titles

    second = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    assert second.json()["data"]["created"] == 0
    assert second.json()["data"]["skipped"] == 3
    messages_again = client.get("/admin-api/ims/auth/workbench/messages", headers=auth, params={"pageNo": 1, "pageSize": 50})
    again_titles = [row["title"] for row in messages_again.json()["data"]["list"]]
    assert again_titles.count("证件黄色预警：E2E黄证") == 1
