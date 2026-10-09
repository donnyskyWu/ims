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
    assert snap.json()["data"]["rows"]

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


def test_bi_subscribe_daily_period_alias_without_cron():
    """契约 DAILY/WEEKLY/MONTHLY 写入后仍存 DAY/WEEK/MONTH，并给出本地下次推送估算。"""
    auth = headers()
    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "DAILY 订阅测", "reportType": "REPORT", "category": "内容分析"},
    )
    assert created.json()["code"] == 0
    rid = created.json()["data"]["id"]
    sub = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "日报订阅", "reportId": rid, "period": "DAILY", "pushTime": "09:00"},
    )
    body = sub.json()
    assert body["code"] == 0, body
    assert body["data"]["period"] == "DAY"
    assert body["data"]["periodCode"] == "DAILY"
    assert body["data"]["nextPushAt"]
    updated = client.put(
        f"/admin-api/ims/bi/subscribe/{body['data']['id']}",
        headers=auth,
        json={"period": "WEEKLY", "status": "PAUSED"},
    )
    assert updated.json()["code"] == 0
    assert updated.json()["data"]["period"] == "WEEK"
    assert updated.json()["data"]["periodCode"] == "WEEKLY"
    assert updated.json()["data"]["nextPushAt"] == ""
    invalid = client.post(
        "/admin-api/ims/bi/subscribe",
        headers=auth,
        json={"subName": "非法周期", "reportId": rid, "period": "HOURLY"},
    )
    assert invalid.json()["code"] == 1001


def test_bi_share_link_empty_revoke_and_expire_edges():
    auth = headers()
    empty = client.get("/admin-api/ims/bi/subscribe/share-link", headers=auth, params={"token": "  "})
    assert empty.json()["code"] == 1001
    assert "为空" in empty.json()["msg"]

    missing = client.get(
        "/admin-api/ims/bi/subscribe/share-link", headers=auth, params={"token": "no-such-share-token"}
    )
    assert missing.json()["code"] == 1001
    assert "不存在" in missing.json()["msg"]

    created = client.post(
        "/admin-api/ims/bi/report",
        headers=auth,
        json={"reportName": "分享边测", "reportType": "REPORT", "category": "内容分析"},
    )
    rid = created.json()["data"]["id"]

    short = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": False, "expireDays": 3},
    )
    assert short.json()["code"] == 1197
    long = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": False, "expireDays": 31},
    )
    assert long.json()["code"] == 1197

    pending = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": True, "expireDays": 7},
    )
    assert pending.json()["code"] == 0
    pending_token = pending.json()["data"]["linkToken"]
    gated = client.get("/admin-api/ims/bi/subscribe/share-link", headers=auth, params={"token": pending_token})
    assert gated.json()["code"] == 1196
    assert "待审批" in gated.json()["msg"]

    plain = client.post(
        "/admin-api/ims/bi/subscribe/share-link",
        headers=auth,
        json={"reportId": rid, "sensitive": False, "expireDays": 7},
    )
    assert plain.json()["code"] == 0
    assert plain.json()["data"]["approvalStatus"] == "APPROVED"
    token = plain.json()["data"]["linkToken"]
    link_id = plain.json()["data"]["id"]
    opened = client.get("/admin-api/ims/bi/subscribe/share-link", headers=auth, params={"token": token})
    assert opened.json()["code"] == 0
    assert opened.json()["data"]["usable"] is True
    assert "数据权限" in opened.json()["data"]["hint"]

    from app.core import SessionLocal
    from app.models import BiShareLink

    db = SessionLocal()
    row = db.get(BiShareLink, link_id)
    assert row is not None
    row.expire_at = "2020-01-01T00:00:00+08:00"
    db.commit()
    db.close()
    aged = client.get("/admin-api/ims/bi/subscribe/share-link", headers=auth, params={"token": token})
    assert aged.json()["code"] == 1001
    assert "已过期" in aged.json()["msg"]

    revoked = client.put(
        f"/admin-api/ims/bi/subscribe/share-approval/{link_id}",
        headers=auth,
        json={"approvalStatus": "EXPIRED"},
    )
    assert revoked.json()["code"] == 0
    assert revoked.json()["data"]["approvalStatus"] == "EXPIRED"
    after = client.get("/admin-api/ims/bi/subscribe/share-link", headers=auth, params={"token": token})
    assert after.json()["code"] == 1001
    assert "已过期" in after.json()["msg"]


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
