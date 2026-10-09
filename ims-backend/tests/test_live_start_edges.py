"""#168 · 红级同场次整改、开播前取消、黄级待办只记本地不外发。"""

import os

os.environ["IMS_DB"] = "ims_test"
os.environ["IMS_OPS_DB"] = "ims_ops_test"

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import SessionLocal
from app.main import app
from app.models import Todo, WorkMessage
from tests.test_live_risk_pack import headers, payload, register, seed_bundle

client = TestClient(app)


def _session_id(body: dict) -> int:
    return int(body["data"]["id"])


def test_red_reregister_keeps_code_and_yellow_notice_is_local():
    auth = headers()
    ids = seed_bundle()
    red = register(auth, payload(ids["red_account"], ids["red_person"], ids["phone"], "再含违禁词"))
    assert red.json()["code"] == 0, red.json()
    created = red.json()["data"]
    assert created["riskScore"] == 75
    assert created["riskLevel"] == "RED"
    code = created["sessionCode"]
    session_id = _session_id(red.json())

    edited = client.put(
        f"/admin-api/ims/live/register/{code}",
        headers=auth,
        json=payload(ids["red_account"], ids["red_person"], ids["phone"], "整改后专场"),
    )
    assert edited.json()["code"] == 0, edited.json()
    detail = client.get(f"/admin-api/ims/live/register/{code}", headers=auth)
    body = detail.json()["data"]
    assert body["sessionCode"] == code
    assert body["riskScore"] == 50
    assert body["riskLevel"] == "YELLOW"
    assert body["sessionStatus"] == "PENDING_RISK_CHECK"
    assert "钉钉未外发" in (body["yellowNotice"] or "")
    assert "短信未外发" in (body["yellowNotice"] or "")

    blocked = client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth)
    assert blocked.json()["code"] == 1044

    db = SessionLocal()
    try:
        pending = db.scalar(
            select(func.count())
            .select_from(Todo)
            .where(Todo.ref_id == session_id, Todo.task_type == "live_yellow_approve", Todo.status == "PENDING")
        )
        assert pending >= 1
        channels = set(
            db.scalars(
                select(WorkMessage.channel).where(
                    WorkMessage.ref_id == session_id,
                    WorkMessage.ref_type == "live_yellow_approve",
                )
            ).all()
        )
        assert channels == {"IN_APP", "DINGTALK"}
        stub = db.scalars(
            select(WorkMessage).where(WorkMessage.ref_id == session_id, WorkMessage.channel == "DINGTALK")
        ).all()
        assert stub
        assert all("未外发" in (row.content or "") for row in stub)
    finally:
        db.close()

    again = client.post(f"/admin-api/ims/live/register/{code}/risk-check", headers=auth, json={})
    assert again.json()["code"] == 1044
    db = SessionLocal()
    try:
        again_pending = db.scalar(
            select(func.count())
            .select_from(Todo)
            .where(Todo.ref_id == session_id, Todo.task_type == "live_yellow_approve", Todo.status == "PENDING")
        )
        assert again_pending == pending
    finally:
        db.close()


def test_cancel_before_start_and_blocked_after_live():
    auth = headers()
    ids = seed_bundle()
    green = register(auth, payload(ids["green_account"], ids["green_person"], ids["phone"], "可取消专场"))
    assert green.json()["code"] == 0, green.json()
    code = green.json()["data"]["sessionCode"]
    assert green.json()["data"]["sessionStatus"] == "APPROVED"

    blank = client.put(
        f"/admin-api/ims/live/register/{code}/cancel",
        headers=auth,
        json={"cancelReason": "   "},
    )
    assert blank.json()["code"] == 1001
    too_long = client.put(
        f"/admin-api/ims/live/register/{code}/cancel",
        headers=auth,
        json={"cancelReason": "长" * 257},
    )
    assert too_long.json()["code"] == 1001

    cancelled = client.put(
        f"/admin-api/ims/live/register/{code}/cancel",
        headers=auth,
        json={"cancelReason": "计划有变"},
    )
    assert cancelled.json()["code"] == 0, cancelled.json()
    after = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    assert after["sessionStatus"] == "CANCELLED"
    assert after["cancelReason"] == "计划有变"
    start = client.put(f"/admin-api/ims/live/register/{code}/start", headers=auth)
    assert start.json()["code"] == 1042

    live = register(auth, payload(ids["green_account"], ids["green_person"], ids["phone"], "已开播不可取消"))
    assert live.json()["code"] == 0, live.json()
    live_code = live.json()["data"]["sessionCode"]
    started = client.put(f"/admin-api/ims/live/register/{live_code}/start", headers=auth)
    assert started.json()["code"] == 0, started.json()
    denied = client.put(
        f"/admin-api/ims/live/register/{live_code}/cancel",
        headers=auth,
        json={"cancelReason": "来不及了"},
    )
    assert denied.json()["code"] == 1042
    still = client.get(f"/admin-api/ims/live/register/{live_code}", headers=auth).json()["data"]
    assert still["sessionStatus"] == "LIVE"


def test_yellow_reject_writes_local_rectify_notice():
    auth = headers()
    ids = seed_bundle()
    yellow = register(auth, payload(ids["yellow_account"], ids["yellow_person"], ids["phone"], "含违禁词专场"))
    assert yellow.json()["code"] == 0, yellow.json()
    code = yellow.json()["data"]["sessionCode"]
    session_id = _session_id(yellow.json())
    assert "钉钉未外发" in (yellow.json()["data"]["yellowNotice"] or "")

    rejected = client.put(
        f"/admin-api/ims/live/register/{code}/approve",
        headers=auth,
        json={"approve": False, "comment": "请去掉违禁词"},
    )
    assert rejected.json()["code"] == 0, rejected.json()
    detail = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    assert detail["sessionStatus"] == "PENDING_RISK_CHECK"
    assert detail["approveComment"] == "请去掉违禁词"
    assert detail["yellowNotice"]

    db = SessionLocal()
    try:
        rows = db.scalars(
            select(WorkMessage).where(
                WorkMessage.ref_id == session_id,
                WorkMessage.ref_type == "live_yellow_reject",
            )
        ).all()
        channels = {row.channel for row in rows}
        assert channels == {"IN_APP", "DINGTALK"}
        assert all("未外发" in (row.content or "") for row in rows)
        assert any("请去掉违禁词" in (row.content or "") for row in rows)
        pending = db.scalar(
            select(func.count())
            .select_from(Todo)
            .where(Todo.ref_id == session_id, Todo.task_type == "live_yellow_approve", Todo.status == "PENDING")
        )
        assert pending == 1
    finally:
        db.close()

    approved = client.put(
        f"/admin-api/ims/live/register/{code}/approve",
        headers=auth,
        json={"approve": True, "comment": "整改后放行"},
    )
    assert approved.json()["code"] == 0, approved.json()
    released = client.get(f"/admin-api/ims/live/register/{code}", headers=auth).json()["data"]
    assert released["sessionStatus"] == "APPROVED"
    assert released["yellowNotice"] is None
    db = SessionLocal()
    try:
        pending = db.scalar(
            select(func.count())
            .select_from(Todo)
            .where(Todo.ref_id == session_id, Todo.task_type == "live_yellow_approve", Todo.status == "PENDING")
        )
        assert pending == 0
    finally:
        db.close()
