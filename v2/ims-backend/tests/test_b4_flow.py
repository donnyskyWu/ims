"""B4 工作流：模板、办理、改派、并行、抄送、看板与超时。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.clock import freeze
from app.core.context import system_context, use_context
from app.db.session import session_scope
from app.domains.flow.model import FlowCcRecord, FlowInstance, FlowTask, FlowTemplate, FlowTrace
from app.domains.message.model import Message
from app.domains.system.model import Dept, Menu, Role, RoleMenu
from app.domains.todo.model import Todo, TodoAssignee
from tests.conftest import auth
from tests.stddata import D1, D2, ROOT, U_ADMIN, U_DEPT, U_SELF


def _grant(role_id: int, codes: list[str]) -> None:
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            menus = {menu.perm_code: menu.id for menu in session.scalars(select(Menu)) if menu.perm_code}
            have = set(session.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id == role_id)))
            for code in codes:
                if menus[code] not in have:
                    session.add(RoleMenu(role_id=role_id, menu_id=menus[code], tenant_id=1))


def _nodes(assignee: str = "1", sla: int = 8) -> list[dict]:
    return [
        {
            "nodeOrder": 1,
            "nodeKey": "start",
            "nodeName": "发起",
            "nodeType": "START",
            "formFields": [{"fieldKey": "title", "fieldLabel": "标题", "fieldType": "text", "required": True}],
            "nextOrders": [2],
        },
        {
            "nodeOrder": 2,
            "nodeKey": "approve",
            "nodeName": "审批",
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "USER", "targetUserIds": [assignee]},
            "slaHours": sla,
            "nextOrders": [3],
        },
        {"nodeOrder": 3, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
    ]


def _create(client, headers, name="自定义确认", domain="COMMON", nodes=None, biz="CUSTOM_OK"):
    return client.post(
        "/admin-api/ims/flow/template",
        headers=headers,
        json={"templateName": name, "businessDomain": domain, "bizType": biz, "nodes": nodes if nodes is not None else _nodes()},
    ).json()


def _publish(client, headers, ident):
    return client.post(f"/admin-api/ims/flow/template/{ident}/publish", headers=headers).json()


def _start(client, headers, template_id, form=None, key=""):
    body = {"templateId": str(template_id), "formData": form if form is not None else {"title": "一事"}}
    if key:
        body["businessKey"] = key
    return client.post("/admin-api/ims/flow/instance", headers=headers, json=body).json()


def test_seed_refuses_production():
    from tools.e2e_seed.b4 import assert_allowed

    try:
        assert_allowed("prod")
    except RuntimeError as exc:
        assert "生产环境" in str(exc)
    else:
        raise AssertionError("生产环境应拒绝造数")


def test_presets_and_routes(client):
    headers = auth(client, "u_admin")
    listed = client.get("/admin-api/ims/flow/template/list", headers=headers, params={"pageSize": 50}).json()
    assert listed["code"] == 0, listed
    names = {row["templateName"] for row in listed["data"]["list"]}
    assert {"账号领用审批", "数据上报审核", "培训相关审批"} <= names
    assert not any(word in name for name in names for word in ("请假", "报销", "开播", "内容审核"))
    codes = {row["bizType"] for row in listed["data"]["list"]}
    assert {"ACCT_BORROW", "REPORT_REVIEW", "TRAIN_APPROVAL"} <= codes
    for path in (
        "/admin-api/ims/flow/task/my-todo",
        "/admin-api/ims/flow/task/my-initiated",
        "/admin-api/ims/flow/task/my-handled",
        "/admin-api/ims/flow/task/badge",
        "/admin-api/ims/flow/instance/board",
        "/admin-api/ims/flow/timeout/list",
        "/admin-api/ims/flow/timeout/rate",
        "/admin-api/ims/flow/timeout/distribution",
    ):
        params = {"dimension": "TEMPLATE"} if path.endswith("distribution") else None
        body = client.get(path, headers=headers, params=params).json()
        assert body["code"] == 0, (path, body)


def test_template_publish_start_handle_revoke(client):
    headers = auth(client, "u_admin")
    admin = auth(client, "admin")
    broken = _create(client, headers, name="缺结束", nodes=[{"nodeOrder": 1, "nodeKey": "start", "nodeName": "发起", "nodeType": "START"}])
    assert broken["code"] == 0, broken
    refused = _publish(client, headers, broken["data"]["id"])
    assert refused["code"] == 1131
    created = _create(client, headers)
    assert created["code"] == 0, created
    published = _publish(client, headers, created["data"]["id"])
    assert published["code"] == 0 and published["data"]["status"] == "PUBLISHED"
    preview = client.get(f"/admin-api/ims/flow/template/{created['data']['id']}/preview", headers=headers).json()
    assert preview["code"] == 0 and preview["data"]["nodes"]
    missing = _start(client, headers, created["data"]["id"], form={})
    assert missing["code"] == 1001
    started = _start(client, headers, created["data"]["id"], key="biz-1")
    assert started["code"] == 0 and started["data"]["instanceStatus"] == "RUNNING", started
    again = _start(client, headers, created["data"]["id"], key="biz-1")
    assert again["data"]["instanceNo"] == started["data"]["instanceNo"]
    todo = client.get("/admin-api/ims/flow/task/my-todo", headers=admin).json()
    assert todo["code"] == 0 and todo["data"]["total"] >= 1
    task_id = todo["data"]["list"][0]["id"]
    done = client.put(f"/admin-api/ims/flow/task/{task_id}/handle", headers=admin, json={"action": "APPROVE", "comment": "同意"}).json()
    assert done["code"] == 0 and done["data"]["isInstanceFinished"] is True, done
    detail = client.get(f"/admin-api/ims/flow/instance/{started['data']['instanceNo']}", headers=headers).json()
    assert detail["code"] == 0 and detail["data"]["instanceStatus"] == "APPROVED"
    revoked = client.put(f"/admin-api/ims/flow/instance/{started['data']['instanceNo']}/revoke", headers=headers).json()
    assert revoked["code"] == 1140


def test_return_transfer_and_timeout_still_open(client):
    headers = auth(client, "u_admin")
    admin = auth(client, "admin")
    created = _create(client, headers, name="退回转交", biz="CUSTOM_BACK", nodes=_nodes(sla=1))
    _publish(client, headers, created["data"]["id"])
    started = _start(client, headers, created["data"]["id"])
    task_id = client.get("/admin-api/ims/flow/task/my-todo", headers=admin).json()["data"]["list"][0]["id"]
    same = client.put(
        f"/admin-api/ims/flow/task/{task_id}/transfer",
        headers=admin,
        json={"toUserId": "1", "transferReason": "自己"},
    ).json()
    assert same["code"] == 1138
    moved = client.put(
        f"/admin-api/ims/flow/task/{task_id}/transfer",
        headers=admin,
        json={"toUserId": str(U_DEPT), "transferReason": "请部门同事看一下"},
    ).json()
    assert moved["code"] == 0, moved
    _grant(202, ["ims:flow:task:handle"])
    dept = auth(client, "u_dept")
    returned = client.put(
        f"/admin-api/ims/flow/task/{client.get('/admin-api/ims/flow/task/my-todo', headers=dept).json()['data']['list'][0]['id']}/handle",
        headers=dept,
        json={"action": "REJECT", "comment": "请补充标题"},
    ).json()
    assert returned["code"] == 0, returned
    mine = client.get("/admin-api/ims/flow/task/my-todo", headers=headers).json()
    assert any(row["nodeType"] == "START" for row in mine["data"]["list"])
    start_task = next(row["id"] for row in mine["data"]["list"] if row["nodeType"] == "START")
    resumed = client.put(f"/admin-api/ims/flow/task/{start_task}/handle", headers=headers, json={"action": "APPROVE"}).json()
    assert resumed["code"] == 0, resumed
    anchor = datetime(2026, 10, 1, 9, 0, 0)
    freeze(anchor)
    headers = auth(client, "u_admin")
    late = _create(client, headers, name="超时仍可办", biz="CUSTOM_LATE", nodes=_nodes(sla=1))
    _publish(client, headers, late["data"]["id"])
    running = _start(client, headers, late["data"]["id"])
    freeze(anchor + timedelta(hours=2))
    headers = auth(client, "u_admin")
    admin = auth(client, "admin")
    job = client.post("/admin-api/ims/system/job/run", headers=headers, json={"name": "flow_overdue"}).json()
    assert job["code"] == 0, job
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == running["data"]["instanceNo"]))
        assert instance.status == "TIMEOUT"
        task = session.scalar(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING"))
        assert task.overdue == 1
        task_id = task.id
    handled = client.put(f"/admin-api/ims/flow/task/{task_id}/handle", headers=admin, json={"action": "APPROVE"}).json()
    assert handled["code"] == 0 and handled["data"]["isInstanceFinished"] is True, handled


def test_parallel_cc_timer(client):
    headers = auth(client, "u_admin")
    admin = auth(client, "admin")
    _grant(202, ["ims:flow:instance:start"])
    nodes = [
        {"nodeOrder": 1, "nodeKey": "start", "nodeName": "发起", "nodeType": "START", "nextOrders": [2, 3]},
        {
            "nodeOrder": 2,
            "nodeKey": "a",
            "nodeName": "甲",
            "nodeType": "APPROVE",
            "parallelGroup": "g1",
            "assigneeRule": {"assignType": "USER", "targetUserIds": ["1"]},
            "nextOrders": [4],
        },
        {
            "nodeOrder": 3,
            "nodeKey": "b",
            "nodeName": "乙",
            "nodeType": "APPROVE",
            "parallelGroup": "g1",
            "assigneeRule": {"assignType": "USER", "targetUserIds": [str(U_ADMIN)]},
            "nextOrders": [4],
        },
        {"nodeOrder": 4, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
    ]
    created = _create(client, headers, name="会签", biz="CUSTOM_PAR", nodes=nodes)
    _publish(client, headers, created["data"]["id"])
    started = _start(client, auth(client, "u_dept"), created["data"]["id"], form={})
    assert started["code"] == 0, started
    first_id = client.get("/admin-api/ims/flow/task/my-todo", headers=admin).json()["data"]["list"][0]["id"]
    waiting = client.put(f"/admin-api/ims/flow/task/{first_id}/handle", headers=admin, json={"action": "APPROVE"}).json()
    assert waiting["code"] == 1137, waiting
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == started["data"]["instanceNo"]))
        approved = session.scalar(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "APPROVED"))
        assert approved is not None and instance.status == "RUNNING"
    second = client.get("/admin-api/ims/flow/task/my-todo", headers=headers).json()["data"]["list"][0]
    finished = client.put(f"/admin-api/ims/flow/task/{second['id']}/handle", headers=headers, json={"action": "APPROVE"}).json()
    assert finished["code"] == 0 and finished["data"]["isInstanceFinished"] is True, finished

    cc_nodes = [
        {"nodeOrder": 1, "nodeKey": "start", "nodeName": "发起", "nodeType": "START", "nextOrders": [2]},
        {
            "nodeOrder": 2,
            "nodeKey": "cc",
            "nodeName": "抄送",
            "nodeType": "CC",
            "assigneeRule": {"assignType": "USER", "targetUserIds": [str(U_SELF)]},
            "nextOrders": [3],
        },
        {
            "nodeOrder": 3,
            "nodeKey": "approve",
            "nodeName": "审批",
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "USER", "targetUserIds": ["1"]},
            "nextOrders": [4],
        },
        {"nodeOrder": 4, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
    ]
    copied = _create(client, headers, name="抄送单", biz="CUSTOM_CC", nodes=cc_nodes)
    _publish(client, headers, copied["data"]["id"])
    cc_started = _start(client, headers, copied["data"]["id"])
    assert cc_started["code"] == 0, cc_started
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == cc_started["data"]["instanceNo"]))
        record = session.scalar(select(FlowCcRecord).where(FlowCcRecord.instance_id == instance.id))
        assert record is not None and int(record.user_id) == U_SELF
        mail = session.scalar(select(Message).where(Message.receiver_id == U_SELF, Message.title == "流程抄送"))
        assert mail is not None
        todo_ids = list(session.scalars(select(TodoAssignee.todo_id).where(TodoAssignee.user_id == U_SELF)))
        if todo_ids:
            flow_todo = session.scalar(
                select(Todo).where(Todo.id.in_(todo_ids), Todo.source_type == "FLOW_TASK", Todo.type == "APPROVAL", Todo.status == "PENDING")
            )
            assert flow_todo is None

    timer_nodes = [
        {"nodeOrder": 1, "nodeKey": "start", "nodeName": "发起", "nodeType": "START", "nextOrders": [2]},
        {"nodeOrder": 2, "nodeKey": "wait", "nodeName": "等待", "nodeType": "TIMER", "slaHours": 1, "nextOrders": [3]},
        {
            "nodeOrder": 3,
            "nodeKey": "approve",
            "nodeName": "审批",
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "USER", "targetUserIds": ["1"]},
            "nextOrders": [4],
        },
        {"nodeOrder": 4, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
    ]
    timed = _create(client, headers, name="计时单", biz="CUSTOM_TIMER", nodes=timer_nodes)
    _publish(client, headers, timed["data"]["id"])
    anchor = datetime(2026, 10, 1, 9, 0, 0)
    freeze(anchor)
    headers = auth(client, "u_admin")
    timer_started = _start(client, headers, timed["data"]["id"])
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == timer_started["data"]["instanceNo"]))
        waiting_task = session.scalar(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING"))
        assert waiting_task.node_type == "TIMER" and waiting_task.assignee is None
    freeze(anchor + timedelta(hours=2))
    headers = auth(client, "u_admin")
    admin = auth(client, "admin")
    assert client.post("/admin-api/ims/system/job/run", headers=headers, json={"name": "flow_overdue"}).json()["code"] == 0
    opened = client.get("/admin-api/ims/flow/task/my-todo", headers=admin).json()
    assert any(row["nodeName"] == "审批" and row["instanceNo"] == timer_started["data"]["instanceNo"] for row in opened["data"]["list"])


def test_c078_chain_and_no_merge(client):
    headers = auth(client, "u_admin")
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.get(Dept, D2).leader_user_id = U_ADMIN
            session.get(Dept, D1).leader_user_id = U_DEPT
    self_nodes = _nodes(str(U_SELF))
    created = _create(client, headers, name="改派上级", domain="BUSINESS", biz="CUSTOM_LEAD", nodes=self_nodes)
    _publish(client, headers, created["data"]["id"])
    _grant(204, ["ims:flow:instance:start", "ims:flow:task:handle"])
    started = _start(client, auth(client, "u_self"), created["data"]["id"])
    assert started["code"] == 0 and started["data"]["instanceStatus"] == "RUNNING", started
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == started["data"]["instanceNo"]))
        assignees = set(session.scalars(select(FlowTask.assignee).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING")))
        assert assignees == {U_ADMIN}
        trace = session.scalar(select(FlowTrace).where(FlowTrace.instance_id == instance.id, FlowTrace.action == "REASSIGN"))
        assert trace is not None and trace.detail.startswith("审批人为发起人，已改派给")
        pending_id = session.scalar(select(FlowTask.id).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING"))
    denied = client.put(f"/admin-api/ims/flow/task/{pending_id}/handle", headers=auth(client, "u_self"), json={"action": "APPROVE"}).json()
    assert denied["code"] == 1135

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.get(Dept, D2).leader_user_id = U_SELF
            session.get(Dept, ROOT).leader_user_id = None
            role = session.get(Role, 202)
            role.flow_domain = "BUSINESS"
    _grant(202, ["ims:flow:instance:manage"])
    owned = _create(client, headers, name="改派域主", domain="BUSINESS", biz="CUSTOM_DOM", nodes=_nodes(str(U_SELF)))
    _publish(client, headers, owned["data"]["id"])
    domain_started = _start(client, auth(client, "u_self"), owned["data"]["id"])
    assert domain_started["code"] == 0, domain_started
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == domain_started["data"]["instanceNo"]))
        assignees = set(session.scalars(select(FlowTask.assignee).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING")))
        assert U_DEPT in assignees and U_SELF not in assignees

    merge_nodes = [
        {"nodeOrder": 1, "nodeKey": "start", "nodeName": "发起", "nodeType": "START", "nextOrders": [2]},
        {
            "nodeOrder": 2,
            "nodeKey": "one",
            "nodeName": "第一",
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "USER", "targetUserIds": [str(U_SELF)]},
            "nextOrders": [3],
        },
        {
            "nodeOrder": 3,
            "nodeKey": "two",
            "nodeName": "第二",
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "USER", "targetUserIds": [str(U_ADMIN)]},
            "nextOrders": [4],
        },
        {"nodeOrder": 4, "nodeKey": "end", "nodeName": "结束", "nodeType": "END"},
    ]
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.get(Dept, D2).leader_user_id = U_ADMIN
    merged = _create(client, headers, name="不合并", domain="COMMON", biz="CUSTOM_MERGE", nodes=merge_nodes)
    _publish(client, headers, merged["data"]["id"])
    running = _start(client, auth(client, "u_self"), merged["data"]["id"])
    task = client.get("/admin-api/ims/flow/task/my-todo", headers=headers).json()["data"]["list"]
    current = next(row for row in task if row["instanceNo"] == running["data"]["instanceNo"])
    assert current["nodeName"] == "第一"
    stepped = client.put(f"/admin-api/ims/flow/task/{current['id']}/handle", headers=headers, json={"action": "APPROVE"}).json()
    assert stepped["code"] == 0 and stepped["data"]["isInstanceFinished"] is False, stepped
    with session_scope() as session:
        instance = session.scalar(select(FlowInstance).where(FlowInstance.instance_no == running["data"]["instanceNo"]))
        rows = list(session.scalars(select(FlowTask).where(FlowTask.instance_id == instance.id)))
        assert any(row.node == "one" and row.status == "APPROVED" for row in rows)
        assert any(row.node == "two" and row.status == "PENDING" and row.assignee == U_ADMIN for row in rows)


def test_version_board_timeout_domain(client):
    headers = auth(client, "u_admin")
    created = _create(client, headers, name="版本单", biz="CUSTOM_VER")
    _publish(client, headers, created["data"]["id"])
    revised = client.post(f"/admin-api/ims/flow/template/{created['data']['id']}/revise", headers=headers).json()
    assert revised["code"] == 0, revised
    nodes = revised["data"]["nodes"]
    nodes[1]["nodeName"] = "复核"
    updated = client.put(f"/admin-api/ims/flow/template/{created['data']['id']}", headers=headers, json={"nodes": nodes, "changeDesc": "改名"}).json()
    assert updated["code"] == 0, updated
    _publish(client, headers, created["data"]["id"])
    versions = client.get("/admin-api/ims/flow/version/list", headers=headers, params={"templateId": created["data"]["id"]}).json()
    assert versions["code"] == 0 and len(versions["data"]) >= 2
    diff = client.get(
        "/admin-api/ims/flow/version/diff",
        headers=headers,
        params={"templateId": created["data"]["id"], "fromVersion": 1, "toVersion": 2},
    ).json()
    assert diff["code"] == 0, diff
    rolled = client.post(
        f"/admin-api/ims/flow/version/{created['data']['id']}/rollback",
        headers=headers,
        json={"targetVersion": 1, "changeDesc": "退回第一版"},
    ).json()
    assert rolled["code"] == 0 and rolled["data"]["targetVersion"] == 1, rolled
    snap = client.get(
        "/admin-api/ims/flow/version/snapshot",
        headers=headers,
        params={"templateId": created["data"]["id"], "version": rolled["data"]["newVersion"]},
    ).json()
    assert snap["code"] == 0 and snap["data"]["nodes"][1]["nodeName"] == "审批"

    board = client.get("/admin-api/ims/flow/instance/board", headers=headers).json()
    assert board["code"] == 0 and "runningCount" in board["data"]
    rate = client.get("/admin-api/ims/flow/timeout/rate", headers=headers).json()
    assert rate["code"] == 0 and "monthlyTimeoutRate" in rate["data"]
    dist = client.get("/admin-api/ims/flow/timeout/distribution", headers=headers, params={"dimension": "NODE"}).json()
    assert dist["code"] == 0

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            session.get(Role, 204).flow_domain = "ADMIN"
    _grant(204, ["ims:flow:template:query", "ims:flow:board:query"])
    narrowed = client.get("/admin-api/ims/flow/template/list", headers=auth(client, "u_self"), params={"pageSize": 50}).json()
    assert narrowed["code"] == 0, narrowed
    assert all(row["businessDomain"] == "ADMIN" for row in narrowed["data"]["list"])
    assert "账号领用审批" not in {row["templateName"] for row in narrowed["data"]["list"]}

    draft = _create(client, headers, name="待删草稿", biz="CUSTOM_DEL", nodes=_nodes())
    removed = client.delete(f"/admin-api/ims/flow/template/{draft['data']['id']}", headers=headers).json()
    assert removed["code"] == 0, removed
    disabled = _create(client, headers, name="停用单", biz="CUSTOM_OFF")
    _publish(client, headers, disabled["data"]["id"])
    off = client.post(f"/admin-api/ims/flow/template/{disabled['data']['id']}/disable", headers=headers).json()
    assert off["code"] == 0 and off["data"]["status"] == "DISABLED"
    blocked = _start(client, headers, disabled["data"]["id"])
    assert blocked["code"] == 1134
