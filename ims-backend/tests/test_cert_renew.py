"""#69 · CERT-002 换证：新有效期、旧证归档为历史、黄/红/锁定解除、工作台待办完成。"""

import os
from datetime import date, timedelta

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def _upload(auth: dict, holder: str, days: int, number: str, cert_type: str = "IDCARD"):
    today = date.today()
    return client.post(
        "/admin-api/ims/cert/archive/upload",
        headers=auth,
        json={
            "holderName": holder,
            "certType": cert_type,
            "certNoPlain": number,
            "fileKey": "local/cert/renew",
            "issueDate": "2020-01-01",
            "expireDate": (today + timedelta(days=days)).isoformat(),
        },
    )


def _approve(auth: dict, cert_id: int):
    return client.put(
        f"/admin-api/ims/cert/archive/{cert_id}/review",
        headers=auth,
        json={"action": "APPROVE"},
    )


def test_cert_renew_archives_old_and_clears_warnings_and_todos():
    auth = headers()
    today = date.today()
    samples = [
        ("RN黄", 30, "YELLOW", "WARNING", "110101199002020031"),
        ("RN红", 7, "RED", "WARNING", "110101199002020007"),
        ("RN锁", 0, "LOCKED", "EXPIRED_LOCKED", "110101199002020000"),
    ]
    created_ids: dict[str, int] = {}
    for holder, days, _level, _status, number in samples:
        created = _upload(auth, holder, days, number)
        body = created.json()
        assert body["code"] == 0, body
        assert number not in created.text
        approved = _approve(auth, body["data"]["id"])
        assert approved.json()["code"] == 0
        created_ids[holder] = body["data"]["id"]

    control = _upload(auth, "RN对照", 7, "110101199002020077")
    assert control.json()["code"] == 0
    assert _approve(auth, control.json()["data"]["id"]).json()["code"] == 0

    blocked = _upload(auth, "RN黄", 400, "110101199002029999")
    assert blocked.json()["code"] == 1032

    passport = _upload(auth, "RN黄", 400, "P12345678", cert_type="PASSPORT")
    assert passport.json()["code"] == 0, passport.json()
    passport_id = passport.json()["data"]["id"]
    assert _approve(auth, passport_id).json()["code"] == 0

    scan = client.post("/admin-api/ims/cert/expire/scan", headers=auth)
    assert scan.json()["code"] == 0, scan.json()
    assert scan.json()["data"]["created"] == 4

    listed = client.get("/admin-api/ims/cert/expire/list", headers=auth, params={"pageNo": 1, "pageSize": 20})
    logs = {row["holderName"]: row for row in listed.json()["data"]["list"] if row["certType"] == "IDCARD"}
    for holder, _days, level, status, number in samples:
        assert logs[holder]["level"] == level
        assert logs[holder]["status"] == status
        assert logs[holder]["certId"] == created_ids[holder]
        assert number not in listed.text
    assert logs["RN对照"]["status"] == "WARNING"
    assert "RN黄" in logs

    yellow_log = logs["RN黄"]["id"]
    wrong = client.put(
        f"/admin-api/ims/cert/expire/{yellow_log}/renew",
        headers=auth,
        json={"newCertId": passport_id, "remark": "类型不同"},
    )
    assert wrong.json()["code"] == 1001

    short = _upload(auth, "RN黄", 10, "110101199002020010")
    assert short.json()["code"] == 1001
    assert "超出 30 天" in short.json()["msg"]

    pending = _upload(auth, "RN黄", 400, "110101199002020410")
    pending_body = pending.json()
    assert pending_body["code"] == 0, pending_body
    assert pending_body["data"]["status"] == "PENDING_REVIEW"
    again = _upload(auth, "RN黄", 400, "110101199002020411")
    assert again.json()["code"] == 1032
    early = client.put(
        f"/admin-api/ims/cert/expire/{yellow_log}/renew",
        headers=auth,
        json={"newCertId": pending_body["data"]["id"]},
    )
    assert early.json()["code"] == 1033

    new_ids: dict[str, int] = {"RN黄": pending_body["data"]["id"]}
    for holder, number in (("RN红", "110101199002020407"), ("RN锁", "110101199002020400")):
        uploaded = _upload(auth, holder, 400, number)
        assert uploaded.json()["code"] == 0, uploaded.json()
        new_ids[holder] = uploaded.json()["data"]["id"]

    for holder, _days, _level, _status, _number in samples:
        assert _approve(auth, new_ids[holder]).json()["code"] == 0
        renewed = client.put(
            f"/admin-api/ims/cert/expire/{logs[holder]['id']}/renew",
            headers=auth,
            json={"newCertId": new_ids[holder], "remark": "换证"},
        )
        assert renewed.json()["code"] == 0, renewed.json()
        assert renewed.json()["data"] is None
        repeat = client.put(
            f"/admin-api/ims/cert/expire/{logs[holder]['id']}/renew",
            headers=auth,
            json={"newCertId": new_ids[holder]},
        )
        assert repeat.json()["code"] == 1033

    missing = client.put(
        "/admin-api/ims/cert/expire/999999/renew",
        headers=auth,
        json={"newCertId": new_ids["RN黄"]},
    )
    assert missing.json()["code"] == 1504

    new_date = (today + timedelta(days=400)).isoformat()
    for holder, days, _level, _status, number in samples:
        page = client.get(
            "/admin-api/ims/corp/resource/certificate/page",
            headers=auth,
            params={"holderName": holder, "pageNo": 1, "pageSize": 20},
        )
        rows = page.json()["data"]["list"]
        assert number not in page.text
        old_row = next(row for row in rows if row["id"] == created_ids[holder])
        new_row = next(row for row in rows if row["id"] == new_ids[holder])
        assert old_row["status"] == "RECYCLED"
        assert old_row["expireDate"] == (today + timedelta(days=days)).isoformat()
        assert new_row["status"] == "EFFECTIVE"
        assert new_row["expireDate"] == new_date
        alert = client.get(
            "/admin-api/ims/cert/expire/list",
            headers=auth,
            params={"holderName": holder, "pageNo": 1, "pageSize": 20},
        )
        alert_rows = [row for row in alert.json()["data"]["list"] if row["certId"] == created_ids[holder]]
        assert len(alert_rows) == 1
        assert alert_rows[0]["status"] == "RENEW_RESOLVED"
        assert number not in alert.text

    control_alert = client.get(
        "/admin-api/ims/cert/expire/list",
        headers=auth,
        params={"holderName": "RN对照", "pageNo": 1, "pageSize": 10},
    )
    assert control_alert.json()["data"]["list"][0]["status"] == "WARNING"
    assert control_alert.json()["data"]["list"][0]["level"] == "RED"

    stats = client.get("/admin-api/ims/cert/expire/stats", headers=auth).json()["data"]
    assert stats["byLevel"]["YELLOW"] == 0
    assert stats["byLevel"]["RED"] == 1
    assert stats["byLevel"]["LOCKED"] == 0
    assert stats["renewedThisMonth"] == 3

    pending_todos = client.get(
        "/admin-api/ims/auth/workbench/todos",
        headers=auth,
        params={"pageNo": 1, "pageSize": 50, "status": "PENDING"},
    ).json()["data"]["list"]
    pending_titles = [row["title"] for row in pending_todos]
    done_titles = [
        row["title"]
        for row in client.get(
            "/admin-api/ims/auth/workbench/todos",
            headers=auth,
            params={"pageNo": 1, "pageSize": 50, "status": "DONE"},
        ).json()["data"]["list"]
    ]
    labels = {"YELLOW": "黄色", "RED": "红色", "LOCKED": "锁定"}
    for holder, _days, level, _status, _number in samples:
        title = f"证件{labels[level]}预警：{holder}"
        assert title not in pending_titles
        assert title in done_titles
    assert "证件红色预警：RN对照" in pending_titles

    second = client.post("/admin-api/ims/cert/expire/scan", headers=auth).json()
    assert second["code"] == 0
    assert second["data"]["created"] == 0
    assert second["data"]["skipped"] >= 1
    yellow_again = client.get(
        "/admin-api/ims/cert/expire/list",
        headers=auth,
        params={"holderName": "RN黄", "pageNo": 1, "pageSize": 20},
    ).json()["data"]["list"]
    assert [row["status"] for row in yellow_again if row["certType"] == "IDCARD"] == ["RENEW_RESOLVED"]
