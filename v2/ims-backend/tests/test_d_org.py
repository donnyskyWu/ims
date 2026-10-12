"""组织同步：事件、对账、工号差异。"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.clock import advance, freeze, now_naive
from app.core.context import system_context, use_context
from app.core.events import events
from app.core.fault import faults
from app.db.session import session_scope
from app.domains.auth.model import OrgSyncBatch, OrgSyncDiff, OrgSyncEvent, UserMapping
from app.domains.system.model import ChangeLog, Dept, DictData, User, UserDept
from app.domains.todo.model import Todo, TodoAssignee
from app.integrations.dingtalk.client import ding_state
from app.services.org_sync import drive_retries, replay
from tests.conftest import auth, login
from tests.stddata import D1, D11, D12, D2, DX, ROOT, U_ADMIN, U_DEPT

import app.domains.system.org_router  # noqa: F401  挂到 create_app 的 MOUNTS


@pytest.fixture
def client(app):
    from app.domains.system.org_router import router

    if not any(getattr(route, "path", "").endswith("/org-sync/process") for route in app.routes):
        app.include_router(router, prefix="/admin-api/ims/system")
    return TestClient(app)


def _post(client, headers, body):
    response = client.post("/admin-api/ims/system/org-sync/process", headers=headers, json=body)
    return response.json()


def _event_state(event_id: str) -> dict:
    with session_scope() as session:
        row = session.scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == event_id))
        assert row is not None
        return {"status": row.status, "retry": row.retry_count, "next": row.next_retry_at, "count": 1}


def _dept(ident: int, *, deleted: bool = False) -> dict:
    with session_scope() as session:
        stmt = select(Dept).where(Dept.id == ident)
        if deleted:
            stmt = stmt.execution_options(include_deleted=True)
        row = session.scalar(stmt)
        assert row is not None
        return {
            "name": row.name,
            "parent_id": row.parent_id,
            "source": row.source,
            "status": row.status,
            "deleted": row.deleted,
            "local_orphan": row.local_orphan,
            "ding": row.dingtalk_dept_id,
            "path": row.path,
        }


def _run_drive():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            return drive_retries()


def test_ut_d07_01(client):
    """回调验签：坏签不入库，好签入库，重复事件仍一行。"""
    body = {"eventId": "cb-d07-01", "eventType": "dept_modify", "eventTime": "2026-10-12T09:00:00+08:00", "dingtalkDeptId": 100, "name": "签名部门"}
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    bad = client.post(
        "/admin-api/ims/callback/dingtalk/event",
        content=raw,
        headers={"Content-Type": "application/json", "X-Dingtalk-Signature": "0" * 64},
    )
    assert bad.json()["code"] == 1008
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(OrgSyncEvent)) == 0
    sig = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Dingtalk-Signature": sig}
    ok = client.post("/admin-api/ims/callback/dingtalk/event", content=raw, headers=headers)
    assert ok.json()["code"] == 0, ok.text
    assert ok.json()["data"]["accepted"] is True
    again = client.post("/admin-api/ims/callback/dingtalk/event", content=raw, headers=headers)
    assert again.json()["code"] == 0
    with session_scope() as session:
        rows = list(session.scalars(select(OrgSyncEvent)))
    assert len(rows) == 1
    assert rows[0].event_id == "cb-d07-01"


def test_ut_d07_02_duplicate_event(client):
    headers = auth(client, "u_admin")
    body = {
        "eventId": "ev-dup",
        "eventType": "dept_modify",
        "eventTime": "2026-10-12T09:00:00+08:00",
        "dingtalkDeptId": 100,
        "name": "市场改名",
    }
    first = _post(client, headers, body)
    assert first["code"] == 0, first
    assert first["data"]["duplicated"] is False
    second = _post(client, headers, {**body, "name": "不应再生效"})
    assert second["code"] == 0, second
    assert second["data"]["duplicated"] is True
    assert _dept(D1)["name"] == "市场改名"
    with session_scope() as session:
        count = session.scalar(select(func.count()).select_from(OrgSyncEvent).where(OrgSyncEvent.event_id == "ev-dup"))
        logs = list(session.scalars(select(ChangeLog).where(ChangeLog.reason == "DINGTALK_OVERRIDE")))
    assert count == 1
    assert len(logs) == 1


def test_ut_d07_03_modify_expired(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            dept = session.get(Dept, D1)
            dept.name = "本地改名"
            dept.last_sync_at = datetime(2026, 10, 12, 12, 0, 0)
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-expired",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T10:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "过期名",
        },
    )
    assert body["code"] == 0, body
    assert body["data"]["status"] == "EXPIRED"
    assert _dept(D1)["name"] == "本地改名"
    assert _event_state("ev-expired")["status"] == "EXPIRED"


def test_ut_d07_04_modify_override(client):
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-override",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T09:30:00+08:00",
            "dingtalkDeptId": 100,
            "name": "市场总部",
        },
    )
    assert body["code"] == 0, body
    assert _dept(D1)["name"] == "市场总部"
    with session_scope() as session:
        log = session.scalar(select(ChangeLog).where(ChangeLog.reason == "DINGTALK_OVERRIDE", ChangeLog.biz_id == D1))
    assert log is not None
    assert log.before_value == "市场部"
    assert log.after_value == "市场总部"


def test_ut_d07_05_dept_add(client):
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-add-dept",
            "eventType": "dept_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 300,
            "parentDingtalkDeptId": 100,
            "name": "市场三组",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        row = session.scalar(select(Dept).where(Dept.dingtalk_dept_id == 300))
        assert row is not None
        assert row.source == "DINGTALK"
        assert row.parent_id == D1
        assert row.name == "市场三组"
        assert row.path.startswith(f"/{ROOT}/{D1}/")


def test_ut_d07_06_dept_remove_unassigned(client):
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-rm-d1",
            "eventType": "dept_remove",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 100,
        },
    )
    assert body["code"] == 0, body
    removed = _dept(D1, deleted=True)
    assert removed["status"] == "DISABLED"
    assert removed["deleted"] == D1
    with session_scope() as session:
        assert session.get(Dept, D1) is None
        admin_links = list(session.scalars(select(UserDept).where(UserDept.user_id == U_ADMIN)))
        admin = session.get(User, U_ADMIN)
        dept_user = session.get(User, U_DEPT)
        dept_links = {row.dept_id for row in session.scalars(select(UserDept).where(UserDept.user_id == U_DEPT))}
        pending = session.get(Dept, DX)
        todos = list(session.scalars(select(Todo).where(Todo.type == "CONFIRM", Todo.source_type == "DEPT_UNASSIGNED")))
        assert pending.name == "待分配" and pending.source == "SYSTEM"
        assert admin.main_dept_id == DX
        assert {(row.dept_id, row.is_main) for row in admin_links} == {(DX, 1)}
        assert D1 not in dept_links and D2 in dept_links
        assert dept_user.main_dept_id == D2
        assert len(todos) == 1
        assert "1" in todos[0].title
        assignees = {row.user_id for row in session.scalars(select(TodoAssignee).where(TodoAssignee.todo_id == todos[0].id))}
        assert U_ADMIN in assignees
        orphan = session.scalar(select(Todo).where(Todo.source_type == "DEPT_ORPHAN"))
        local = session.get(Dept, D12)
        assert local.parent_id == ROOT
        assert local.local_orphan == 1
        assert local.source == "LOCAL"
        assert orphan is not None and "请确认" in orphan.title


def test_ut_d07_07_local_orphan_nearest_ancestor(client):
    headers = auth(client, "u_admin")
    created = _post(
        client,
        headers,
        {
            "eventId": "ev-mid",
            "eventType": "dept_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 301,
            "parentDingtalkDeptId": 100,
            "name": "中层",
        },
    )
    assert created["code"] == 0, created
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            parent = session.scalar(select(Dept).where(Dept.dingtalk_dept_id == 301))
            row = Dept(
                parent_id=parent.id,
                name="本地小组",
                source="LOCAL",
                status="ENABLED",
                path="/",
                tenant_id=1,
            )
            session.add(row)
            session.flush()
            row.path = f"{parent.path}{row.id}/"
            local_id = row.id
    removed = _post(
        client,
        headers,
        {
            "eventId": "ev-rm-mid",
            "eventType": "dept_remove",
            "eventTime": "2026-10-12T09:10:00+08:00",
            "dingtalkDeptId": 301,
        },
    )
    assert removed["code"] == 0, removed
    with session_scope() as session:
        local = session.get(Dept, local_id)
        assert local.parent_id == D1
        assert local.parent_id != ROOT
        assert local.local_orphan == 1
        todo = session.scalar(select(Todo).where(Todo.source_type == "DEPT_ORPHAN", Todo.source_id == local_id))
        assert todo is not None and "请确认" in todo.title
        assert _dept_gone(session, 301)


def _dept_gone(session, ding_id: int) -> bool:
    row = session.scalar(select(Dept).where(Dept.dingtalk_dept_id == ding_id).execution_options(include_deleted=True))
    return row is not None and row.deleted == row.id and row.status == "DISABLED"


def test_ut_d07_08_reconcile_timeout(client):
    headers = auth(client, "u_admin")
    ding_state.departments = [{"dingtalkDeptId": 999, "parentDingtalkDeptId": None, "name": "不应出现"}]
    ding_state.error = "timeout"
    response = client.post("/admin-api/ims/system/org-sync/reconcile", headers=headers)
    body = response.json()
    assert body["code"] == 5003, body
    assert _dept(D1)["name"] == "市场部"
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(OrgSyncBatch)) == 0
        assert session.scalar(select(Dept).where(Dept.dingtalk_dept_id == 999)) is None


def test_ut_d07_09_reconcile_running(client):
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(OrgSyncBatch(status="RUNNING", started_at=now_naive(), same_name_notes=[]))
    headers = auth(client, "u_admin")
    ding_state.departments = [{"dingtalkDeptId": 100, "name": "被挡住", "parentDingtalkDeptId": None}]
    body = client.post("/admin-api/ims/system/org-sync/reconcile", headers=headers).json()
    assert body["code"] == 1001, body
    assert body["msg"] == "同步正在进行中"
    assert _dept(D1)["name"] == "市场部"
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(OrgSyncBatch)) == 1


def test_ut_d07_10_same_name_and_local_kept(client):
    headers = auth(client, "u_admin")
    before = _dept(D12)
    ding_state.departments = [
        {"dingtalkDeptId": 100, "parentDingtalkDeptId": None, "name": "市场部同步"},
        {"dingtalkDeptId": 101, "parentDingtalkDeptId": 100, "name": "市场一组"},
        {"dingtalkDeptId": 200, "parentDingtalkDeptId": None, "name": "技术部"},
        {"dingtalkDeptId": 102, "parentDingtalkDeptId": 100, "name": "市场二组"},
    ]
    ding_state.users = []
    body = client.post("/admin-api/ims/system/org-sync/reconcile", headers=headers).json()
    assert body["code"] == 0, body
    notes = body["data"]["sameNameNotes"]
    assert any("存在同名本地部门" in str(item) for item in notes)
    latest = client.get("/admin-api/ims/system/org-sync/latest-batch", headers=headers).json()
    assert latest["code"] == 0, latest
    assert any("存在同名本地部门" in str(item) for item in latest["data"]["sameNameNotes"])
    with session_scope() as session:
        twins = list(session.scalars(select(Dept).where(Dept.parent_id == D1, Dept.name == "市场二组")))
        assert {row.source for row in twins} == {"LOCAL", "DINGTALK"}
        local = session.get(Dept, D12)
        assert local.name == before["name"]
        assert local.parent_id == before["parent_id"]
        assert local.source == "LOCAL"
        assert local.dingtalk_dept_id is None
        assert local.deleted == 0
        renamed = session.get(Dept, D1)
        assert renamed.name == "市场部同步"
        assert renamed.source == "DINGTALK"


def test_ut_d07_11_user_add_position(client):
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-user-add",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_new_pos",
            "mobile": "13800002222",
            "nickname": "新同事",
            "deptIds": [100, 200],
            "positionCode": "NEW_POS",
            "empNo": "E900",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_new_pos"))
        user = session.get(User, mapping.user_id)
        assert user.status == "ACTIVE"
        assert user.password_hash is None
        assert user.nickname == "新同事"
        assert user.position_code == "NEW_POS"
        assert user.emp_no == "E900"
        links = list(session.scalars(select(UserDept).where(UserDept.user_id == user.id)))
        assert {(row.dept_id, row.source) for row in links} == {(D1, "DINGTALK"), (D2, "DINGTALK")}
        assert user.main_dept_id == D1
        dict_row = session.scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == "NEW_POS"))
        assert dict_row is not None and dict_row.source == "DINGTALK"
        username = user.username
    denied = login(client, username, "Abc12345")
    assert denied.json()["code"] == 1214


def test_ut_d07_12_user_modify_keeps_local(client):
    headers = auth(client, "u_admin")
    added = _post(
        client,
        headers,
        {
            "eventId": "ev-user-mod-base",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_mod",
            "nickname": "改部门",
            "deptIds": [100],
        },
    )
    assert added["code"] == 0, added
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_mod"))
            session.add(UserDept(user_id=mapping.user_id, dept_id=D12, is_main=0, source="LOCAL", tenant_id=1))
    modified = _post(
        client,
        headers,
        {
            "eventId": "ev-user-mod",
            "eventType": "user_modify",
            "eventTime": "2026-10-12T10:00:00+08:00",
            "dingtalkUserId": "dt_mod",
            "deptIds": [200],
            "nickname": "已改",
        },
    )
    assert modified["code"] == 0, modified
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_mod"))
        user = session.get(User, mapping.user_id)
        links = {(row.dept_id, row.source) for row in session.scalars(select(UserDept).where(UserDept.user_id == user.id))}
        assert links == {(D2, "DINGTALK"), (D12, "LOCAL")}
        assert user.main_dept_id == D2
        assert user.nickname == "已改"


def test_ut_d07_13_user_leave_once(client):
    token = auth(client, "u_d12")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(UserMapping(user_id=1103, dingtalk_user_id="dt_d12", dept_ids=[101], sync_status="SUCCESS", tenant_id=1))
    headers = auth(client, "u_admin")
    first = _post(
        client,
        headers,
        {
            "eventId": "ev-leave-1",
            "eventType": "user_leave",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_d12",
        },
    )
    assert first["code"] == 0, first
    second = _post(
        client,
        headers,
        {
            "eventId": "ev-leave-2",
            "eventType": "user_leave",
            "eventTime": "2026-10-12T09:05:00+08:00",
            "dingtalkUserId": "dt_d12",
        },
    )
    assert second["code"] == 0, second
    assert len(events.of("user.resigned")) == 1
    with session_scope() as session:
        user = session.get(User, 1103)
        assert user.status == "RESIGNED"
    me = client.get("/admin-api/ims/auth/me", headers=token)
    assert me.json()["code"] == 1002


def test_ut_d07_14_retry_dead_replay(client):
    freeze(datetime(2026, 10, 12, 8, 0, 0))
    headers = auth(client, "u_admin")
    body = {
        "eventId": "ev-retry",
        "eventType": "dept_modify",
        "eventTime": "2026-10-12T08:00:00+08:00",
        "dingtalkDeptId": 100,
        "name": "重试后的名字",
    }
    faults.arm("org.fail", RuntimeError("down"))
    first = _post(client, headers, body)
    assert first["code"] == 0, first
    assert first["data"]["status"] == "RETRYING"
    assert _dept(D1)["name"] == "市场部"
    state = _event_state("ev-retry")
    assert state["retry"] == 1
    assert state["next"] == datetime(2026, 10, 12, 8, 1, 0)
    _run_drive()
    assert _event_state("ev-retry")["retry"] == 1
    assert _dept(D1)["name"] == "市场部"
    gaps = (5, 15, 60)
    for index, minutes in enumerate(gaps, start=2):
        advance(timedelta(minutes=1 if index == 2 else gaps[index - 3]))
        faults.arm("org.fail", RuntimeError("down"))
        _run_drive()
        state = _event_state("ev-retry")
        assert state["status"] == "RETRYING"
        assert state["retry"] == index
        assert state["next"] == now_naive() + timedelta(minutes=minutes)
    advance(timedelta(minutes=60))
    faults.arm("org.fail", RuntimeError("down"))
    _run_drive()
    state = _event_state("ev-retry")
    assert state["status"] == "DEAD"
    assert state["retry"] == 5
    assert _dept(D1)["name"] == "市场部"
    advance(timedelta(minutes=120))
    _run_drive()
    assert _event_state("ev-retry")["status"] == "DEAD"
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            done = replay("ev-retry")
    assert done["status"] == "SUCCESS"
    assert _dept(D1)["name"] == "重试后的名字"
    assert _event_state("ev-retry")["status"] == "SUCCESS"


def test_ut_d07_15_delay_event(client):
    freeze(datetime(2026, 10, 12, 10, 0, 0))
    headers = auth(client, "u_admin")
    late = _post(
        client,
        headers,
        {
            "eventId": "ev-delay",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "延迟改名",
        },
    )
    assert late["code"] == 0, late
    assert len(events.of("org.delay")) == 1
    near = _post(
        client,
        headers,
        {
            "eventId": "ev-nodelay",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T09:56:00+08:00",
            "dingtalkDeptId": 200,
            "name": "技术及时",
        },
    )
    assert near["code"] == 0, near
    assert len(events.of("org.delay")) == 1


def test_ut_d07_16_out_of_order(client):
    headers = auth(client, "u_admin")
    newer = _post(
        client,
        headers,
        {
            "eventId": "ev-new",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T15:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "较新名称",
        },
    )
    assert newer["code"] == 0, newer
    older = _post(
        client,
        headers,
        {
            "eventId": "ev-old",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T14:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "较旧名称",
        },
    )
    assert older["code"] == 0, older
    assert older["data"]["status"] == "EXPIRED"
    assert _dept(D1)["name"] == "较新名称"


def test_ut_b1pre_06_emp_roundtrip(client):
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-emp-fill",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_emp_fill",
            "nickname": "有工号",
            "deptIds": [200],
            "empNo": "E100",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_emp_fill"))
        user = session.get(User, mapping.user_id)
        assert user.emp_no == "E100"
        diffs = list(session.scalars(select(OrgSyncDiff).where(OrgSyncDiff.dingtalk_user_id == "dt_emp_fill")))
    assert diffs == []
    page = client.get("/admin-api/ims/system/user/page?keyword=E100", headers=headers).json()
    assert page["code"] == 0, page
    assert any(item["empNo"] == "E100" for item in page["data"]["list"])


def test_ut_b1pre_07_emp_mismatch(client):
    headers = auth(client, "u_admin")
    created = _post(
        client,
        headers,
        {
            "eventId": "ev-emp-base",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_emp_mis",
            "nickname": "工号冲突",
            "deptIds": [200],
            "empNo": "E1",
        },
    )
    assert created["code"] == 0, created
    changed = _post(
        client,
        headers,
        {
            "eventId": "ev-emp-mis",
            "eventType": "user_modify",
            "eventTime": "2026-10-12T10:00:00+08:00",
            "dingtalkUserId": "dt_emp_mis",
            "empNo": "E2",
        },
    )
    assert changed["code"] == 0, changed
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_emp_mis"))
        user = session.get(User, mapping.user_id)
        assert user.emp_no == "E1"
        diff = session.scalar(select(OrgSyncDiff).where(OrgSyncDiff.dingtalk_user_id == "dt_emp_mis"))
        assert diff.diff_type == "EMP_NO_MISMATCH"
        assert diff.diff_label == "工号不一致"
        assert diff.ims_value == "E1"
        assert diff.remote_value == "E2"


def test_ut_b1pre_08_emp_missing(client):
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-emp-miss",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_emp_miss",
            "nickname": "缺工号",
            "deptIds": [200],
            "empNo": "",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_emp_miss"))
        user = session.get(User, mapping.user_id)
        assert user.emp_no in (None, "")
        diff = session.scalar(select(OrgSyncDiff).where(OrgSyncDiff.dingtalk_user_id == "dt_emp_miss"))
        assert diff.diff_type == "EMP_NO_MISSING"
        assert diff.diff_label == "工号缺失"
