import os
from unittest.mock import MagicMock, patch

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


def test_bi_subscribe_list_and_share_link():
    auth = headers()
    listed = client.get("/admin-api/ims/bi/subscribe/list", headers=auth, params={"pageNo": 1, "pageSize": 10})
    body = listed.json()
    assert body["code"] == 0
    assert body["data"]["total"] >= 2

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "W9 订阅测", "reportType": "REPORT", "category": "内容分析"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]

    sub = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "测试订阅", "reportId": rid, "period": "DAY", "pushTime": "09:00"},
    )
    assert sub.json()["code"] == 0
    sid = sub.json()["data"]["id"]

    paused = client.put(f"/admin-api/ims/bi/subscribe/{sid}", headers=auth, json={"status": "PAUSED"})
    assert paused.json()["code"] == 0

    snap = client.get(f"/admin-api/ims/bi/subscribe/snapshot/{sid}", headers=auth)
    assert snap.json()["code"] == 0
    assert snap.json()["data"]["empty"] is True
    assert snap.json()["data"]["rows"] == []
    assert snap.json()["data"]["emptyReason"] == "尚未推送，暂无快照"

    link = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": True, "expireDays": 7},
    )
    assert link.json()["code"] == 0
    assert link.json()["data"]["approvalStatus"] == "PENDING"
    lid = link.json()["data"]["id"]

    approved = client.put(
        f"/admin-api/ims/bi/subscribe/share-approval/{lid}",
        headers=auth,
        json={"approvalStatus": "APPROVED"},
    )
    assert approved.json()["code"] == 0

    link2 = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": True, "expireDays": 14},
    )
    assert link2.json()["code"] == 0
    lid2 = link2.json()["data"]["id"]
    rejected = client.put(
        f"/admin-api/ims/bi/subscribe/share-approval/{lid2}",
        headers=auth,
        json={"approvalStatus": "REJECTED"},
    )
    assert rejected.json()["code"] == 0
    assert rejected.json()["data"]["approvalStatus"] == "REJECTED"

    expired = client.put(
        f"/admin-api/ims/bi/subscribe/share-approval/{lid}",
        headers=auth,
        json={"approvalStatus": "EXPIRED"},
    )
    assert expired.json()["code"] == 0
    assert expired.json()["data"]["approvalStatus"] == "EXPIRED"

    resumed = client.put(f"/admin-api/ims/bi/subscribe/{sid}", headers=auth, json={"status": "ACTIVE"})
    assert resumed.json()["code"] == 0

    push = client.post(f"/admin-api/ims/bi/subscribe/{sid}/push-now", headers=auth)
    assert push.json()["code"] == 0
    assert push.json()["data"]["lastPushStatus"] in ("DING_OK", "SITE_OK")
    assert push.json()["data"]["snapshot"]["rows"]
    if "DING" in (sub.json()["data"].get("channels") or "").upper():
        assert push.json()["data"]["dingTalk"]["msgId"]


def test_bi_subscribe_push_now_dingtalk_webhook():
    auth = headers()
    cfg = client.put(
        "/admin-api/ims/system/param",
        headers=auth,
        json={"paramKey": "bi.dingtalk.webhook.url", "paramValue": "https://example.test/ding-hook"},
    )
    assert cfg.json()["code"] == 0

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "Webhook 测", "reportType": "REPORT", "category": "内容分析"},
    )
    rid = created.json()["data"]["id"]
    sub = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "Webhook 订阅", "reportId": rid, "period": "DAY", "pushTime": "09:00", "channels": "SITE+DING"},
    )
    sid = sub.json()["data"]["id"]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp

    with patch("app.bi_subscribe.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = mock_http
        push = client.post(f"/admin-api/ims/bi/subscribe/{sid}/push-now", headers=auth)

    body = push.json()
    assert body["code"] == 0
    assert body["data"]["lastPushStatus"] == "DING_OK"
    ding = body["data"]["dingTalk"]
    assert ding["status"] == "WEBHOOK_SENT"
    assert ding["webhookConfigured"] is True
    mock_http.post.assert_called_once()
    assert mock_http.post.call_args[0][0] == "https://example.test/ding-hook"
    assert mock_http.post.call_args[1]["json"]["msgtype"] == "markdown"


def test_bi_report_preview_run_and_drill():
    auth = headers()
    run = client.post(
        "/admin-api/ims/bi/report/preview/run",
        headers=auth,
        json={"platform": "抖音", "dateFrom": "2026-09-01", "dateTo": "2026-10-03"},
    )
    assert run.json()["code"] == 0
    assert run.json()["data"]["kpis"]
    assert run.json()["data"]["rows"]

    drill = client.post(
        "/admin-api/ims/bi/report/preview/drill",
        headers=auth,
        json={"drillPath": ["抖音"], "dimension": "platform"},
    )
    assert drill.json()["code"] == 0
    assert drill.json()["data"]["rows"][0].get("account")
