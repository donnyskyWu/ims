"""#156 · 台账日期筛选含当日、更正单空列表、超时督办卡片通道。"""

import os
from datetime import datetime, timedelta, timezone

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core import SessionLocal
from app.live_fin_e2e_seed import E2E_LEDGER_SESSION
from app.main import app
from app.models import LiveSession, User

client = TestClient(app)
BJ = timezone(timedelta(hours=8))
OVERDUE_CODE = "IMS20261009DYS0156"
FRESH_CODE = "IMS20261009DYS0157"


def headers() -> dict:
    token = client.post("/admin-api/ims/auth/login", json={"username": "admin", "password": "Admin@123"}).json()["data"][
        "accessToken"
    ]
    return {"Authorization": f"Bearer {token}"}


def _insert(code: str, hours_ago: int) -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin", User.deleted == 0))
        assert admin is not None
        ended = datetime.now(BJ) - timedelta(hours=hours_ago)
        started = ended - timedelta(hours=2)
        start_iso = started.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        ended_iso = ended.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        row = db.scalar(select(LiveSession).where(LiveSession.session_code == code))
        if row is None:
            row = LiveSession(
                session_code=code,
                account_id=1,
                account_no="AC-PY-0156",
                realname_person_id=1,
                realname_name="台账收尾",
                responsible_user_id=admin.id,
                device_asset_ids="[]",
                platform="DOUYIN",
                topic="督办卡片",
                plan_start_time=start_iso,
                plan_end_time=ended_iso,
                session_status="ENDED",
                actual_start=start_iso,
                actual_end=ended_iso,
                creator=admin.id,
                tenant_id=admin.tenant_id or 0,
                football_sync_status="UNLINKED",
            )
            db.add(row)
        else:
            row.deleted = 0
            row.session_status = "ENDED"
            row.responsible_user_id = admin.id
            row.actual_start = start_iso
            row.actual_end = ended_iso
            row.plan_start_time = start_iso
            row.plan_end_time = ended_iso
        db.commit()
    finally:
        db.close()


def _hide(code: str) -> None:
    db = SessionLocal()
    try:
        row = db.scalar(select(LiveSession).where(LiveSession.session_code == code))
        if row is not None:
            row.deleted = 1
            db.commit()
    finally:
        db.close()


def test_date_only_filters_keep_same_day_and_detail_corrections_empty():
    auth = headers()
    code = E2E_LEDGER_SESSION
    hit = client.get(
        "/admin-api/ims/live/ledger/list",
        headers=auth,
        params={
            "sessionCode": code,
            "platform": "DOUYIN",
            "riskLevel": "GREEN",
            "isSupplement": "false",
            "timeRange": ["2026-10-08", "2026-10-08"],
        },
    )
    body = hit.json()
    assert body["code"] == 0, body
    assert [row["sessionCode"] for row in body["data"]["list"]] == [code]

    same = client.get(
        "/admin-api/ims/live/sessions/list",
        headers=auth,
        params={"sessionCode": code, "timeRange": ["2026-10-08", "2026-10-08"]},
    )
    assert [row["sessionCode"] for row in same.json()["data"]["list"]] == [code]

    other_day = client.get(
        "/admin-api/ims/live/ledger/list",
        headers=auth,
        params={"sessionCode": code, "timeRange": ["2026-10-07", "2026-10-07"]},
    )
    assert other_day.json()["data"]["list"] == []

    other_platform = client.get(
        "/admin-api/ims/live/ledger/list",
        headers=auth,
        params={"sessionCode": code, "platform": "KUAISHOU"},
    )
    assert other_platform.json()["data"]["list"] == []

    red = client.get(
        "/admin-api/ims/live/ledger/list",
        headers=auth,
        params={"sessionCode": code, "riskLevel": "RED"},
    )
    assert red.json()["data"]["list"] == []

    supplement = client.get(
        "/admin-api/ims/live/ledger/list",
        headers=auth,
        params={"sessionCode": code, "isSupplement": "true"},
    )
    assert supplement.json()["data"]["list"] == []

    detail = client.get(f"/admin-api/ims/live/ledger/{code}", headers=auth)
    assert detail.json()["code"] == 0, detail.json()
    assert detail.json()["data"]["corrections"] == []

    exported = client.get(
        "/admin-api/ims/live/ledger/export",
        headers=auth,
        params={"sessionCode": code, "timeRange": ["2026-10-08", "2026-10-08"]},
    )
    payload = exported.json()
    assert payload["code"] == 0, payload
    assert "导出任务已提交" in payload["data"]["message"]
    assert payload["data"]["exportTaskId"]
    downloaded = client.get(payload["data"]["downloadUrl"], headers=auth)
    assert downloaded.status_code == 200


def test_overdue_pending_marks_in_app_supervise_channel():
    auth = headers()
    _insert(OVERDUE_CODE, 48)
    _insert(FRESH_CODE, 2)
    try:
        pending = client.get(
            "/admin-api/ims/live/report/pending",
            headers=auth,
            params={"pageNo": 1, "pageSize": 100},
        )
        body = pending.json()
        assert body["code"] == 1048
        rows = {item["sessionCode"]: item for item in body["data"]["list"]}
        assert rows[OVERDUE_CODE]["overdue"] is True
        assert rows[OVERDUE_CODE]["superviseChannel"] == "IN_APP"
        assert rows[FRESH_CODE]["overdue"] is False
        assert rows[FRESH_CODE]["superviseChannel"] == ""
    finally:
        _hide(OVERDUE_CODE)
        _hide(FRESH_CODE)
