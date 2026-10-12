"""流程模板、办理、撤销与超时催办。"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.clock import freeze, now_naive
from app.core.context import RequestContext, use_context
from app.core.errors import BizError
from app.core.events import events
from app.db.session import session_scope
from app.domains.flow.model import FlowInstance, FlowTask, FlowTemplateVersion
from app.domains.flow.router import router as flow_router
from app.domains.flow.service import act, callbacks, cancel, edit_nodes, publish_template, scan_overdue, start
from app.domains.message.model import Message
from app.domains.system.model import Dept, UserRole
from app.domains.todo.model import Todo
from tests.stddata import D1, D11, U_ADMIN, U_DEPT, U_D11, U_SELF


def _ctx(user_id, perms=None, scopes=None, depts=None):
    return RequestContext(
        user_id=user_id,
        tenant_id=1,
        perm_codes=set(perms or []),
        data_scopes=set(scopes or ["ALL"]),
        dept_ids=list(depts or []),
        username="tester",
        nickname="tester",
    )


@pytest.fixture(autouse=True)
def _clear_callbacks():
    callbacks.clear()
    yield
    callbacks.clear()


def _route(path):
    for route in flow_router.routes:
        if getattr(route, "path", None) == path:
            return route
    raise AssertionError(path)


def test_router_perms():
    assert _route("/template").endpoint.__ims_meta__["perm"] == "ims:flow:manage"
    assert _route("/template").summary == "发布流程模板"
    assert _route("/start").endpoint.__ims_meta__["perm"] == "ims:flow:start"
    assert _route("/act").endpoint.__ims_meta__["perm"] == "ims:flow:act"
    assert _route("/cancel").endpoint.__ims_meta__["perm"] == "ims:flow:cancel"
    assert _route("/cancel").summary == "撤销流程"


def test_publish_is_immutable_and_running_instance_keeps_version():
    first_nodes = [
        {"key": "n1", "assigneeUserId": U_DEPT},
        {"key": "n2", "assigneeUserId": U_ADMIN},
    ]
    with session_scope(commit=True) as session:
        with use_context(_ctx(U_SELF, ["ims:flow:start", "ims:flow:manage"])):
            first = publish_template("LEAVE", "请假", first_nodes, "leave")
            assert first["version"] == 1
            assert first["status"] == "PUBLISHED"
            with pytest.raises(BizError) as locked:
                edit_nodes(first["versionId"], [{"key": "changed", "assigneeUserId": U_DEPT}])
            assert locked.value.code == 1001
            started = start("LEAVE", "leave", 7)
            assert started["status"] == "RUNNING"
            assert started["currentNode"] == "n1"
            assert started["templateVersionId"] == first["versionId"]
            second = publish_template("LEAVE", "请假修订", [{"key": "z9", "assigneeUserId": U_ADMIN}])
            assert second["version"] == 2
        instance = session.get(FlowInstance, started["id"])
        assert instance.template_version_id == first["versionId"]
        with use_context(_ctx(U_DEPT, ["ims:flow:act"])):
            moved = act(started["id"], "APPROVE")
        assert moved["currentNode"] == "n2"
        assert moved["status"] == "RUNNING"
        assert moved["templateVersionId"] == first["versionId"]
        with use_context(_ctx(U_ADMIN, ["ims:flow:act"])):
            done = act(started["id"], "APPROVE")
        assert done["status"] == "APPROVED"
        with use_context(_ctx(U_SELF, ["ims:flow:start"])):
            latest = start("LEAVE", "leave", 8)
        assert latest["templateVersionId"] == second["versionId"]
        assert latest["currentNode"] == "z9"
        stored = session.get(FlowTemplateVersion, first["versionId"])
        assert stored.nodes[0]["key"] == "n1"
        assert stored.nodes[1]["key"] == "n2"


def test_return_reject_and_cancel():
    seen = []
    callbacks.append(lambda payload: seen.append(payload["action"]))
    nodes = [
        {"key": "n1", "assigneeUserId": U_DEPT},
        {"key": "n2", "assigneeUserId": U_ADMIN},
    ]
    with session_scope(commit=True) as session:
        with use_context(_ctx(U_SELF, ["ims:flow:start"])):
            publish_template("BACK", "退回", nodes)
            started = start("BACK", "leave", 1)
        with use_context(_ctx(U_DEPT, ["ims:flow:act"])):
            act(started["id"], "APPROVE")
        with use_context(_ctx(U_ADMIN, ["ims:flow:act"])):
            returned = act(started["id"], "RETURN", "请补充")
        assert returned["status"] == "RUNNING"
        assert returned["currentNode"] == "n1"
        pending = list(session.scalars(select(FlowTask).where(FlowTask.instance_id == started["id"], FlowTask.status == "PENDING")))
        assert len(pending) == 1 and pending[0].node == "n1" and pending[0].assignee == U_DEPT
        with use_context(_ctx(U_DEPT, ["ims:flow:act"])):
            rejected = act(started["id"], "REJECT", "不同意")
        assert rejected["status"] == "REJECTED"
        assert seen == ["REJECT"]
        assert events.of("flow.rejected")
        mail = session.scalar(select(Message).where(Message.receiver_id == U_SELF, Message.title == "流程已驳回"))
        assert mail is not None
        with use_context(_ctx(U_SELF, ["ims:flow:start"])):
            publish_template("STOP", "撤销", [{"key": "only", "assigneeUserId": U_ADMIN}])
            running = start("STOP", "leave", 2)
        with use_context(_ctx(U_DEPT)):
            with pytest.raises(BizError) as blocked:
                cancel(running["id"])
            assert blocked.value.code == 1139
        still = session.get(FlowInstance, running["id"])
        assert still.status == "RUNNING"
        with use_context(_ctx(U_SELF)):
            stopped = cancel(running["id"])
        assert stopped["status"] == "CANCELLED"
        todos = list(session.scalars(select(Todo).where(Todo.source_type == "FLOW_TASK", Todo.status == "PENDING")))
        assert todos == []
        voided = session.scalar(select(func.count()).select_from(Todo).where(Todo.source_type == "FLOW_TASK", Todo.status == "CANCELLED"))
        assert int(voided or 0) >= 1


def test_leader_perm_and_self_suspension():
    with session_scope(commit=True) as session:
        dept = session.get(Dept, D11)
        parent = session.get(Dept, D1)
        dept.leader_user_id = U_D11
        parent.leader_user_id = U_ADMIN
        session.flush()
        with use_context(_ctx(U_D11, ["ims:flow:start"], depts=[D11])):
            publish_template("LEAD", "上级", [{"key": "lead", "rule": "LEADER", "dueHours": 4}])
            led = start("LEAD", "leave", 1)
        assert led["status"] == "RUNNING"
        task = session.scalar(select(FlowTask).where(FlowTask.instance_id == led["id"], FlowTask.status == "PENDING"))
        assert task.assignee == U_ADMIN
        assert task.due_time is not None
        with use_context(_ctx(U_ADMIN, ["ims:flow:start"])):
            publish_template("PERM", "权限", [{"key": "check", "permCode": "ims:flow:act"}])
            expanded = start("PERM", "leave", 2)
        names = list(session.scalars(select(FlowTask.assignee).where(FlowTask.instance_id == expanded["id"], FlowTask.status == "PENDING")))
        assert U_ADMIN not in names
        assert 1 in names
        with use_context(_ctx(U_SELF, ["ims:flow:start"])):
            publish_template("SELF", "自己", [{"key": "me", "assigneeUserId": U_SELF}])
            suspended = start("SELF", "leave", 3)
        assert suspended["status"] == "SUSPENDED"
        manage = session.scalar(select(Todo).where(Todo.source_type == "FLOW_INSTANCE", Todo.source_id == suspended["id"]))
        assert manage is not None and manage.assignee_perm_code == "ims:flow:manage"
        with use_context(_ctx(U_SELF, ["ims:flow:act"])):
            with pytest.raises(BizError) as denied:
                act(suspended["id"], "APPROVE")
            assert denied.value.code == 1008
        link = session.scalar(select(UserRole).where(UserRole.user_id == 1, UserRole.role_id == 101))
        session.delete(link)
        session.flush()
        with use_context(_ctx(U_ADMIN, ["ims:flow:start"])):
            publish_template("ONLY", "仅自己", [{"key": "solo", "permCode": "ims:flow:manage"}])
            alone = start("ONLY", "leave", 4)
        assert alone["status"] == "SUSPENDED"
        with use_context(_ctx(U_ADMIN, ["ims:flow:act"])):
            with pytest.raises(BizError) as only:
                act(alone["id"], "APPROVE")
            assert only.value.code == 1008


def test_overdue_scan_once():
    with session_scope(commit=True) as session:
        with use_context(_ctx(U_SELF, ["ims:flow:start"])):
            publish_template("LATE", "超时", [{"key": "n1", "assigneeUserId": U_ADMIN, "dueHours": 1}])
            started = start("LATE", "leave", 1)
        freeze(now_naive() + timedelta(hours=2))
        assert scan_overdue() == 1
        assert scan_overdue() == 0
        task = session.scalar(select(FlowTask).where(FlowTask.instance_id == started["id"]))
        assert task.overdue == 1 and task.urge_sent == 1
        mails = list(session.scalars(select(Message).where(Message.receiver_id == U_ADMIN, Message.title == "审批已超时")))
        todos = list(session.scalars(select(Todo).where(Todo.source_type == "FLOW_TASK", Todo.source_id == task.id, Todo.type == "WARNING")))
        assert len(mails) == 1
        assert len(todos) == 1
        assert todos[0].status == "PENDING"
