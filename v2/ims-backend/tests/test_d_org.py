"""组织同步 UT-D07，以及工号差异。"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime

from sqlalchemy import func, select

import app.services.org_sync as org_sync_mod
from app.core.clock import freeze, now_naive
from app.core.context import system_context, use_context
from app.core.events import events
from app.core.fault import faults
from app.core.redis_client import get_redis
from app.db.session import session_scope
from app.domains.auth.model import AuthEventLog, OrgSyncBatch, OrgSyncDiff, OrgSyncEvent, UserMapping
from app.domains.system.model import ChangeLog, Dept, DictData, Menu, Role, RoleMenu, User, UserDept, UserRole
from app.domains.todo.model import Todo, TodoAssignee
from app.integrations.dingtalk.client import ding_state
from app.services.org_sync import drive_retries, replay
from tests.conftest import auth, login
from tests.stddata import D1, D11, D12, D2, DX, PASSWORD, ROOT, U_ADMIN, U_D11, U_OVERLAP

_CALLBACK = "/admin-api/ims/callback/dingtalk/event"
_USER_ADMIN_PERM = "ims:system:user:update"


def _post(client, headers, body):
    response = client.post("/admin-api/ims/system/org-sync/process", headers=headers, json=body)
    return response.json()


def _callback(client, body, signature=None):
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    if signature is None:
        signature = hmac.new(b"test-app-secret", raw, hashlib.sha256).hexdigest()
    response = client.post(
        _CALLBACK,
        content=raw,
        headers={"Content-Type": "application/json", "X-Dingtalk-Signature": signature},
    )
    return response.json()


def _event_count(event_id: str | None = None) -> int:
    with session_scope() as session:
        stmt = select(func.count()).select_from(OrgSyncEvent)
        if event_id is not None:
            stmt = stmt.where(OrgSyncEvent.event_id == event_id)
        return int(session.scalar(stmt) or 0)


def _event_state(event_id: str) -> dict:
    with session_scope() as session:
        row = session.scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == event_id))
        assert row is not None
        return {"status": row.status, "retry": row.retry_count, "next": row.next_retry_at}


def _status_label(code: str) -> str:
    with session_scope() as session:
        row = session.scalar(select(DictData).where(DictData.dict_type == "dict_org_sync_status", DictData.dict_value == code))
    assert row is not None, code
    return row.dict_label


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


def _member_rows(dept_id: int) -> set[tuple]:
    with session_scope() as session:
        rows = session.scalars(select(UserDept).where(UserDept.dept_id == dept_id))
        return {(row.user_id, int(row.is_main), row.source) for row in rows}


def _run_drive():
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            return drive_retries()


def _reconcile(client, headers):
    return client.post("/admin-api/ims/system/org-sync/reconcile", headers=headers).json()


def _ding_tree(extra: list[dict] | None = None, *, drop: set[int] | None = None):
    rows = [
        {"dingtalkDeptId": 100, "parentDingtalkDeptId": None, "name": "市场部"},
        {"dingtalkDeptId": 101, "parentDingtalkDeptId": 100, "name": "市场一组"},
        {"dingtalkDeptId": 200, "parentDingtalkDeptId": None, "name": "技术部"},
    ]
    if drop:
        rows = [row for row in rows if int(row["dingtalkDeptId"]) not in drop]
    if extra:
        rows.extend(extra)
    ding_state.departments = rows
    ding_state.users = []
    ding_state.error = None


def _dept_call(client, headers, method: str, path: str, payload: dict):
    response = getattr(client, method)(f"/admin-api/ims/system{path}", headers=headers, json=payload)
    body = response.json()
    assert body["code"] == 0, body
    return body


def _user_create(client, headers, username: str, nickname: str, dept_ids: list[int], main: int) -> int:
    body = _dept_call(
        client,
        headers,
        "post",
        "/user/create",
        {"username": username, "nickname": nickname, "deptIds": dept_ids, "mainDeptId": main, "password": PASSWORD},
    )
    return int(body["data"]["id"])


def _set_depts(client, headers, user_id: int, dept_ids: list[int], main: int):
    _dept_call(client, headers, "put", "/user/update-depts", {"id": user_id, "deptIds": dept_ids, "mainDeptId": main})


def _prepare_d11_members(client, headers) -> tuple[int, int, int]:
    """D11 只留甲（另属技术部）、乙（没有其他部门）、丙（本地用户，未绑钉钉）。"""
    _set_depts(client, headers, U_D11, [D2], D2)
    _set_depts(client, headers, U_OVERLAP, [D1], D1)
    jia = _user_create(client, headers, "jia", "甲", [D11, D2], D11)
    yi = _user_create(client, headers, "yi", "乙", [D11], D11)
    bing = _user_create(client, headers, "bing", "丙", [D11], D11)
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            for row in session.scalars(select(UserDept).where(UserDept.user_id == jia)):
                row.source = "DINGTALK"
            for row in session.scalars(select(UserDept).where(UserDept.user_id == yi, UserDept.dept_id == D11)):
                row.source = "DINGTALK"
        ids = {row.user_id for row in session.scalars(select(UserDept).where(UserDept.dept_id == D11))}
    assert ids == {jia, yi, bing}
    return jia, yi, bing


def _perm_holders(session) -> set[int]:
    menu_ids = [row.id for row in session.scalars(select(Menu).where(Menu.perm_code == _USER_ADMIN_PERM))]
    role_ids = [row.role_id for row in session.scalars(select(RoleMenu).where(RoleMenu.menu_id.in_(menu_ids), RoleMenu.tenant_id == 1))]
    return {
        row.user_id
        for row in session.scalars(select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.manual_removed == 0, UserRole.tenant_id == 1))
    }


def _assert_d11_removed(jia: int, yi: int, bing: int):
    removed = _dept(D11, deleted=True)
    assert removed["status"] == "DISABLED"
    assert removed["deleted"] == D11
    with session_scope() as session:
        assert session.scalar(select(Dept).where(Dept.id == D11)) is None
        jia_user = session.get(User, jia)
        yi_user = session.get(User, yi)
        bing_user = session.get(User, bing)
        jia_depts = {row.dept_id for row in session.scalars(select(UserDept).where(UserDept.user_id == jia))}
        yi_links = list(session.scalars(select(UserDept).where(UserDept.user_id == yi)))
        bing_links = list(session.scalars(select(UserDept).where(UserDept.user_id == bing)))
        assert jia_depts == {D2}
        assert jia_user.main_dept_id == D2
        assert jia_user.status == "ACTIVE"
        assert {row.dept_id for row in yi_links} == {DX}
        assert yi_user.main_dept_id == DX
        assert any(row.dept_id == DX and int(row.is_main) == 1 for row in yi_links)
        assert {row.dept_id for row in bing_links} == {DX}
        assert bing_user.main_dept_id == DX
        assert any(row.dept_id == DX and int(row.is_main) == 1 for row in bing_links)
        assert yi_user.status == "ACTIVE" and bing_user.status == "ACTIVE"
        mapping = session.scalar(select(UserMapping).where(UserMapping.user_id == bing))
        assert mapping is None
        todos = list(session.scalars(select(Todo).where(Todo.source_type == "DEPT_UNASSIGNED")))
        assert len(todos) == 1
        assert "2" in todos[0].title
        assignees = {row.user_id for row in session.scalars(select(TodoAssignee).where(TodoAssignee.todo_id == todos[0].id))}
        holders = _perm_holders(session)
        assert U_ADMIN in holders
        assert assignees == holders


def _org_snapshot():
    with session_scope() as session:
        depts = tuple(
            sorted(
                (row.id, row.name, row.parent_id, row.status, int(row.deleted or 0), row.source, row.dingtalk_dept_id, int(row.local_orphan or 0))
                for row in session.scalars(select(Dept).execution_options(include_deleted=True))
            )
        )
        users = tuple(
            sorted(
                (row.id, row.username, row.status, row.main_dept_id, row.password_hash, row.position_code, row.nickname)
                for row in session.scalars(select(User).execution_options(include_deleted=True))
            )
        )
        links = tuple(sorted((row.user_id, row.dept_id, int(row.is_main), row.source) for row in session.scalars(select(UserDept))))
        maps = tuple(
            sorted(
                (row.user_id, row.dingtalk_user_id, row.sync_status)
                for row in session.scalars(select(UserMapping).execution_options(include_deleted=True))
            )
        )
    return depts, users, links, maps


def _hire(client, headers, *, event_id: str, ding_id: str = "dt_new", mobile: str = "13700007013", dept_ids: list[int] | None = None, position: str = "POS_HIRE"):
    body = _post(
        client,
        headers,
        {
            "eventId": event_id,
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": ding_id,
            "mobile": mobile,
            "nickname": "新同事",
            "deptIds": [100] if dept_ids is None else dept_ids,
            "positionCode": position,
        },
    )
    assert body["code"] == 0, body
    return body


def test_ut_d07_01(client):
    """UT-D07-01 验签错误：1008，事件不入库。"""
    body = _callback(
        client,
        {"eventId": "evt-d07-01", "eventType": "dept_modify", "eventTime": "2026-10-12T09:00:00+08:00", "dingtalkDeptId": 100, "name": "坏签"},
        signature="0" * 64,
    )
    assert body["code"] == 1008
    assert _event_count() == 0
    assert _event_count("evt-d07-01") == 0


def test_ut_d07_02(client):
    """UT-D07-02 同一 event_id 投递两次，事件表只有 1 条。"""
    payload = {"eventId": "evt-d07-02", "eventType": "dept_modify", "eventTime": "2026-10-12T09:00:00+08:00", "dingtalkDeptId": 100, "name": "重复投递"}
    assert _callback(client, payload)["code"] == 0
    assert _callback(client, payload)["code"] == 0
    assert _event_count() == 1
    assert _event_count("evt-d07-02") == 1


def test_ut_d07_03(client):
    """UT-D07-03 本地把 D11 改成一组后，钉钉改名覆盖为市场 1 组，并留下被覆盖的本地值。"""
    headers = auth(client, "u_admin")
    _dept_call(client, headers, "put", "/dept/update", {"id": D11, "name": "一组"})
    assert _dept(D11)["name"] == "一组"
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-03",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 101,
            "name": "市场 1 组",
        },
    )
    assert body["code"] == 0, body
    assert _dept(D11)["name"] == "市场 1 组"
    with session_scope() as session:
        logs = list(session.scalars(select(ChangeLog).where(ChangeLog.biz_id == D11, ChangeLog.reason == "DINGTALK_OVERRIDE")))
    assert any(row.field == "name" and row.before_value == "一组" for row in logs)


def test_ut_d07_04(client):
    """UT-D07-04 本地把 D11 移到 D2 下，全量对账按钉钉挂回 D1，并记录被覆盖的上级。"""
    headers = auth(client, "u_admin")
    _dept_call(client, headers, "put", "/dept/move", {"id": D11, "parentId": D2})
    assert _dept(D11)["parent_id"] == D2
    _ding_tree()
    body = _reconcile(client, headers)
    assert body["code"] == 0, body
    assert _dept(D11)["parent_id"] == D1
    with session_scope() as session:
        log = session.scalar(
            select(ChangeLog).where(ChangeLog.biz_id == D11, ChangeLog.reason == "DINGTALK_OVERRIDE", ChangeLog.field == "parent_id")
        )
    assert log is not None
    assert log.before_value == "技术部"


def test_ut_d07_05(client):
    """UT-D07-05 钉钉新增部门 102，上级 100，建成 D1 下的 DINGTALK 部门。"""
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-05",
            "eventType": "dept_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 102,
            "parentDingtalkDeptId": 100,
            "name": "新增部门",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        row = session.scalar(select(Dept).where(Dept.dingtalk_dept_id == 102))
        assert row is not None
        assert row.source == "DINGTALK"
        assert row.parent_id == D1


def test_ut_d07_06(client):
    """UT-D07-06 钉钉删除 101：D11 停用并逻辑删除，甲到 D2，乙和丙进 DX，待办 1 条且人数为 2。"""
    headers = auth(client, "u_admin")
    jia, yi, bing = _prepare_d11_members(client, headers)
    body = _post(
        client,
        headers,
        {"eventId": "ev-d07-06", "eventType": "dept_remove", "eventTime": "2026-10-12T09:00:00+08:00", "dingtalkDeptId": 101},
    )
    assert body["code"] == 0, body
    _assert_d11_removed(jia, yi, bing)


def test_ut_d07_07(client):
    """UT-D07-07 本地 D12 及其子部门、两名成员在全量对账后保持不变。"""
    headers = auth(client, "u_admin")
    child_id = int(_dept_call(client, headers, "post", "/dept/create", {"name": "D121", "parentId": D12})["data"]["id"])
    _user_create(client, headers, "m12b", "成员乙", [D12], D12)
    before_name = _dept(D12)["name"]
    before_parent = _dept(D12)["parent_id"]
    child_name = _dept(child_id)["name"]
    child_parent = _dept(child_id)["parent_id"]
    members = _member_rows(D12)
    child_members = _member_rows(child_id)
    assert before_parent == D1
    assert child_parent == D12
    assert len({item[0] for item in members}) == 2
    _ding_tree()
    body = _reconcile(client, headers)
    assert body["code"] == 0, body
    assert _dept(D12)["name"] == before_name
    assert _dept(D12)["parent_id"] == before_parent
    assert _dept(child_id)["name"] == child_name
    assert _dept(child_id)["parent_id"] == child_parent
    assert _member_rows(D12) == members
    assert _member_rows(child_id) == child_members


def test_ut_d07_08(client):
    """UT-D07-08 钉钉删除 100 后，D12 连同 D121 挂到根部门，标记孤儿，成员不变，并有一条请确认待办。"""
    headers = auth(client, "u_admin")
    child_id = int(_dept_call(client, headers, "post", "/dept/create", {"name": "D121", "parentId": D12})["data"]["id"])
    _user_create(client, headers, "m12c", "成员丙", [D12], D12)
    members = _member_rows(D12)
    child_members = _member_rows(child_id)
    assert len({item[0] for item in members}) == 2
    body = _post(
        client,
        headers,
        {"eventId": "ev-d07-08", "eventType": "dept_remove", "eventTime": "2026-10-12T09:00:00+08:00", "dingtalkDeptId": 100},
    )
    assert body["code"] == 0, body
    parent = _dept(D12)
    child = _dept(child_id)
    assert parent["parent_id"] == ROOT
    assert child["parent_id"] == D12
    assert parent["local_orphan"] == 1
    assert parent["name"] == "市场二组"
    assert child["name"] == "D121"
    assert _member_rows(D12) == members
    assert _member_rows(child_id) == child_members
    with session_scope() as session:
        todos = [row for row in session.scalars(select(Todo)) if "请确认" in (row.title or "")]
    assert len(todos) == 1


def test_ut_d07_09(client):
    """UT-D07-09 只删除 D11 时，挂在其下的本地 D12 改挂到最近存活祖先 D1。"""
    headers = auth(client, "u_admin")
    _dept_call(client, headers, "put", "/dept/move", {"id": D12, "parentId": D11})
    assert _dept(D12)["parent_id"] == D11
    body = _post(
        client,
        headers,
        {"eventId": "ev-d07-09", "eventType": "dept_remove", "eventTime": "2026-10-12T09:00:00+08:00", "dingtalkDeptId": 101},
    )
    assert body["code"] == 0, body
    hung = _dept(D12)
    assert hung["parent_id"] == D1
    assert hung["parent_id"] != ROOT
    assert hung["local_orphan"] == 1
    removed = _dept(D11, deleted=True)
    assert removed["status"] == "DISABLED"
    assert removed["deleted"] == D11


def test_ut_d07_10(client):
    """UT-D07-10 钉钉在 D1 下新建与本地同名的市场三组，两个部门都保留，报告写出同名提示。"""
    headers = auth(client, "u_admin")
    local_id = int(_dept_call(client, headers, "post", "/dept/create", {"name": "市场三组", "parentId": D1})["data"]["id"])
    _ding_tree([{"dingtalkDeptId": 102, "parentDingtalkDeptId": 100, "name": "市场三组"}])
    body = _reconcile(client, headers)
    assert body["code"] == 0, body
    notes = body["data"]["sameNameNotes"] or []
    assert any("存在同名本地部门" in str(item) for item in notes)
    with session_scope() as session:
        rows = list(session.scalars(select(Dept).where(Dept.parent_id == D1, Dept.name == "市场三组")))
        assert len(rows) == 2
        assert {row.source for row in rows} == {"LOCAL", "DINGTALK"}
        local = session.get(Dept, local_id)
        assert local is not None and local.source == "LOCAL" and local.dingtalk_dept_id is None


def test_ut_d07_11(client):
    """UT-D07-11 事件时间早于 last_sync_at，名称不变，状态记为已过期。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            dept = session.get(Dept, D11)
            dept.last_sync_at = datetime(2026, 10, 12, 10, 5, 0)
    before = _dept(D11)["name"]
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-11",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T10:00:00+08:00",
            "dingtalkDeptId": 101,
            "name": "过期名",
        },
    )
    assert body["code"] == 0, body
    assert _dept(D11)["name"] == before
    assert body["data"]["status"] == "EXPIRED"
    assert _status_label(body["data"]["status"]) == "已过期"
    assert _event_state("ev-d07-11")["status"] == "EXPIRED"


def test_ut_d07_12(client):
    """UT-D07-12 管理员确认保留孤儿部门后，local_orphan 清零，待办 DONE。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            dept = session.get(Dept, D12)
            dept.local_orphan = 1
            session.add(
                Todo(
                    type="CONFIRM",
                    source_module="org",
                    source_type="DEPT_ORPHAN",
                    source_id=D12,
                    title="请确认保留本地部门",
                    status="PENDING",
                    assignee_perm_code="ims:system:dept:update",
                )
            )
    headers = auth(client, "u_admin")
    body = client.put("/admin-api/ims/system/dept/confirm-orphan", headers=headers, json={"id": D12}).json()
    assert body["code"] == 0, body
    assert _dept(D12)["local_orphan"] == 0
    with session_scope() as session:
        todos = list(session.scalars(select(Todo).where(Todo.source_type == "DEPT_ORPHAN", Todo.source_id == D12)))
    assert len(todos) == 1
    assert todos[0].status == "DONE"


def test_ut_d07_13(client):
    """UT-D07-13 手机号无匹配的新入职人员建成无密码用户，部门跟随钉钉，并触发岗位供给。"""
    headers = auth(client, "u_admin")
    _hire(client, headers, event_id="ev-d07-13")
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_new"))
        assert mapping is not None
        user = session.get(User, mapping.user_id)
        assert user.status == "ACTIVE"
        assert not user.password_hash
        links = {(row.dept_id, row.source) for row in session.scalars(select(UserDept).where(UserDept.user_id == user.id))}
        assert links == {(D1, "DINGTALK")}
        assert user.main_dept_id == D1
        assert user.position_code == "POS_HIRE"
        supplied = session.scalar(select(AuthEventLog).where(AuthEventLog.event_id == "ev-d07-13"))
        role = session.scalar(select(Role).where(Role.position_code == "POS_HIRE", Role.source == "DINGTALK_AUTO"))
        assert supplied is not None
        assert role is not None


def test_ut_d07_14(client):
    """UT-D07-14 未设密码的钉钉新建用户用账号密码登录，返回 1214。"""
    headers = auth(client, "u_admin")
    _hire(client, headers, event_id="ev-d07-14")
    with session_scope() as session:
        mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_new"))
        username = session.get(User, mapping.user_id).username
        assert not session.get(User, mapping.user_id).password_hash
    denied = login(client, username, PASSWORD)
    assert denied.json()["code"] == 1214


def test_ut_d07_15(client):
    """UT-D07-15 钉钉调岗到 D2 时，本地 D12 归属保留。"""
    headers = auth(client, "u_admin")
    added = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-15-add",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_user_a",
            "nickname": "A",
            "deptIds": [101],
        },
    )
    assert added["code"] == 0, added
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            mapping = session.scalar(select(UserMapping).where(UserMapping.dingtalk_user_id == "dt_user_a"))
            session.add(UserDept(user_id=mapping.user_id, dept_id=D12, is_main=0, source="LOCAL"))
            user_id = mapping.user_id
    moved = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-15",
            "eventType": "user_modify",
            "eventTime": "2026-10-12T10:00:00+08:00",
            "dingtalkUserId": "dt_user_a",
            "deptIds": [200],
        },
    )
    assert moved["code"] == 0, moved
    with session_scope() as session:
        links = {(row.dept_id, row.source) for row in session.scalars(select(UserDept).where(UserDept.user_id == user_id))}
    assert links == {(D2, "DINGTALK"), (D12, "LOCAL")}


def test_ut_d07_16(client):
    """UT-D07-16 持有两个会话的用户离职后不可登录，旧令牌失效，离职事件只发一次。"""
    headers = auth(client, "u_admin")
    first = login(client, "u_d11").json()
    second = login(client, "u_d11").json()
    assert first["code"] == 0 and second["code"] == 0
    tokens = [first["data"]["accessToken"], second["data"]["accessToken"]]
    raw = get_redis().get(f"ims:user:sids:{U_D11}")
    assert len(json.loads(raw)) == 2
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(UserMapping(user_id=U_D11, dingtalk_user_id="dt_leave_a", dept_ids=[101], sync_status="SUCCESS"))
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-16",
            "eventType": "user_leave",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_leave_a",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        assert session.get(User, U_D11).status == "RESIGNED"
    assert login(client, "u_d11", PASSWORD).json()["code"] == 1216
    for token in tokens:
        me = client.get("/admin-api/ims/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["code"] == 1002
    resigned = events.of("user.resigned")
    assert len(resigned) == 1
    assert resigned[0]["payload"]["userId"] == U_D11


def test_ut_d07_17(client):
    """UT-D07-17 字典里没有的岗位 NEW_POS2 会按钉钉来源写入 dict_position。"""
    headers = auth(client, "u_admin")
    with session_scope() as session:
        missing = session.scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == "NEW_POS2"))
    assert missing is None
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-17",
            "eventType": "user_add",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkUserId": "dt_pos2",
            "nickname": "新岗位",
            "deptIds": [200],
            "positionCode": "NEW_POS2",
        },
    )
    assert body["code"] == 0, body
    with session_scope() as session:
        row = session.scalar(select(DictData).where(DictData.dict_type == "dict_position", DictData.dict_value == "NEW_POS2"))
    assert row is not None
    assert row.source == "DINGTALK"


def test_ut_d07_18(client):
    """UT-D07-18 对账进行中再次触发，返回 1001，提示同步正在进行中。"""
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.add(OrgSyncBatch(status="RUNNING", started_at=now_naive(), same_name_notes=[]))
    headers = auth(client, "u_admin")
    ding_state.departments = [{"dingtalkDeptId": 100, "name": "被挡住", "parentDingtalkDeptId": None}]
    body = _reconcile(client, headers)
    assert body["code"] == 1001, body
    assert body["msg"] == "同步正在进行中"
    assert _dept(D1)["name"] == "市场部"
    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(OrgSyncBatch)) == 1


def test_ut_d07_19(client):
    """UT-D07-19 钉钉超时：批次记下 5003，部门与人员数据保持原样。"""
    headers = auth(client, "u_admin")
    before = _org_snapshot()
    ding_state.error = "timeout"
    ding_state.departments = [{"dingtalkDeptId": 999, "parentDingtalkDeptId": None, "name": "幽灵部门"}]
    ding_state.users = [{"dingtalkUserId": "dt_ghost", "nickname": "幽灵", "deptIds": [999]}]
    body = _reconcile(client, headers)
    assert body["code"] == 5003, body
    assert _org_snapshot() == before
    with session_scope() as session:
        batch = session.scalar(select(OrgSyncBatch))
        assert batch is not None
        assert batch.status == "FAILED"
        assert batch.error_code == 5003
        assert session.scalar(select(Dept).where(Dept.dingtalk_dept_id == 999)) is None


def test_ut_d07_20(client):
    """UT-D07-20 全量快照缺少钉钉部门 101 时，按删除处理，结果同 UT-D07-06。"""
    headers = auth(client, "u_admin")
    jia, yi, bing = _prepare_d11_members(client, headers)
    _ding_tree(drop={101})
    body = _reconcile(client, headers)
    assert body["code"] == 0, body
    _assert_d11_removed(jia, yi, bing)


def test_ut_d07_21(client):
    """UT-D07-21 持续失败时按可注入时钟重试，前几次为 RETRYING，第 5 次后为 DEAD。"""
    freeze(datetime(2026, 10, 12, 8, 0, 0))
    headers = auth(client, "u_admin")
    event_id = "ev-d07-21"
    seen = []

    def fail_once():
        faults.arm("org.fail", RuntimeError("down"))

    fail_once()
    first = _post(
        client,
        headers,
        {
            "eventId": event_id,
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T08:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "失败不改名",
        },
    )
    assert first["code"] == 0, first
    seen.append(first["data"]["status"])
    for _ in range(4):
        nxt = _event_state(event_id)["next"]
        assert nxt is not None
        freeze(nxt)
        fail_once()
        _run_drive()
        seen.append(_event_state(event_id)["status"])
    assert seen == ["RETRYING", "RETRYING", "RETRYING", "RETRYING", "DEAD"]
    assert _event_state(event_id)["retry"] == 5
    assert _dept(D1)["name"] == "市场部"


def test_ut_d07_22(client):
    """UT-D07-22 死信在故障移除后重放，先回到 PENDING，再处理为 SUCCESS。"""
    headers = auth(client, "u_admin")
    event_id = "ev-d07-22"
    faults.arm("org.fail", RuntimeError("down"))
    failed = _post(
        client,
        headers,
        {
            "eventId": event_id,
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T09:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "重放名称",
        },
    )
    assert failed["code"] == 0, failed
    assert _dept(D1)["name"] == "市场部"
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.scalar(select(OrgSyncEvent).where(OrgSyncEvent.event_id == event_id))
            row.status = "DEAD"
            row.next_retry_at = None
    faults.clear()
    seen = []
    original = org_sync_mod._execute

    def _spy(row):
        seen.append(row.status)
        return original(row)

    org_sync_mod._execute = _spy
    try:
        with session_scope(commit=True) as session:
            with use_context(system_context(1)):
                done = replay(event_id)
    finally:
        org_sync_mod._execute = original
    assert seen == ["PENDING"]
    assert done["status"] == "SUCCESS"
    assert _event_state(event_id)["status"] == "SUCCESS"
    assert _dept(D1)["name"] == "重放名称"


def test_ut_d07_23(client):
    """UT-D07-23 事件时间与处理完成相差 6 分钟时，产生 1 条同步延迟告警。"""
    freeze(datetime(2026, 10, 12, 10, 6, 0))
    headers = auth(client, "u_admin")
    body = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-23",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T10:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "延迟改名",
        },
    )
    assert body["code"] == 0, body
    assert len(events.of("org.delay")) == 1


def test_ut_d07_24(client):
    """UT-D07-24 11:00 的变更先到、10:30 的后到，最终保留 11:00 的值。"""
    headers = auth(client, "u_admin")
    newer = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-24-new",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T11:00:00+08:00",
            "dingtalkDeptId": 100,
            "name": "十一点名称",
        },
    )
    assert newer["code"] == 0, newer
    older = _post(
        client,
        headers,
        {
            "eventId": "ev-d07-24-old",
            "eventType": "dept_modify",
            "eventTime": "2026-10-12T10:30:00+08:00",
            "dingtalkDeptId": 100,
            "name": "十点半名称",
        },
    )
    assert older["code"] == 0, older
    assert _dept(D1)["name"] == "十一点名称"
    assert _status_label(older["data"]["status"]) == "已过期"


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
