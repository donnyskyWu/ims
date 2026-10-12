"""流程模板、发起、办理、撤销与超时催办。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import and_, func, or_, select

from app.core.clock import now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.events import events
from app.db.repository import assert_dict_values
from app.db.session import get_session
from app.domains.flow.model import FlowInstance, FlowTask, FlowTemplate, FlowTemplateVersion
from app.domains.message.service import send_notify
from app.domains.system.model import Dept, User
from app.domains.todo.model import Todo
from app.domains.todo.service import todo_create, users_with_perm

callbacks: list = []


def publish_template(code: str, name: str, nodes: list, biz_type: str = "") -> dict:
    if not code or not str(code).strip():
        raise BizError(1001, data={"fieldErrors": [{"field": "code", "message": "请填写编码"}]})
    if not name or not str(name).strip():
        raise BizError(1001, data={"fieldErrors": [{"field": "name", "message": "请填写名称"}]})
    cleaned = _normalize_nodes(nodes)
    session = get_session()
    template = session.scalar(select(FlowTemplate).where(FlowTemplate.code == code))
    if template is None:
        template = FlowTemplate(code=code, name=name, biz_type=biz_type or "", status="ENABLED")
        session.add(template)
        session.flush()
    else:
        template.name = name
        if biz_type:
            template.biz_type = biz_type
    current = session.scalar(select(func.max(FlowTemplateVersion.version)).where(FlowTemplateVersion.template_id == template.id))
    version = int(current or 0) + 1
    row = FlowTemplateVersion(
        template_id=template.id,
        version=version,
        nodes=cleaned,
        status="PUBLISHED",
        publish_time=now_naive(),
    )
    session.add(row)
    session.flush()
    return _version_view(template, row)


def edit_nodes(version_id: int, nodes: list) -> dict:
    session = get_session()
    row = session.get(FlowTemplateVersion, int(version_id))
    if row is None or row.deleted:
        raise BizError(1504)
    if row.status == "PUBLISHED":
        raise BizError(1001, "已发布的版本不能修改")
    row.nodes = _normalize_nodes(nodes)
    session.flush()
    template = session.get(FlowTemplate, row.template_id)
    return _version_view(template, row)


def start(code: str, biz_type: str, biz_id: int, initiator_id: int | None = None) -> dict:
    session = get_session()
    template = session.scalar(select(FlowTemplate).where(FlowTemplate.code == code))
    if template is None:
        raise BizError(1504)
    version = session.scalar(
        select(FlowTemplateVersion)
        .where(FlowTemplateVersion.template_id == template.id, FlowTemplateVersion.status == "PUBLISHED")
        .order_by(FlowTemplateVersion.version.desc())
    )
    if version is None:
        raise BizError(1504)
    nodes = list(version.nodes or [])
    if not nodes:
        raise BizError(1001, "流程没有节点")
    initiator = _actor(initiator_id)
    instance = FlowInstance(
        template_version_id=version.id,
        biz_type=biz_type or template.biz_type or "",
        biz_id=int(biz_id or 0),
        initiator=initiator,
        status="RUNNING",
        current_node=str(nodes[0].get("key") or ""),
    )
    assert_dict_values(instance)
    session.add(instance)
    session.flush()
    tasks = _open_node(instance, nodes, 0)
    session.flush()
    return _instance_view(instance, tasks)


def act(instance_id: int, action: str, comment: str | None = None, user_id: int | None = None) -> dict:
    action_name = (action or "").strip().upper()
    if action_name not in {"APPROVE", "REJECT", "RETURN"}:
        raise BizError(1001, data={"fieldErrors": [{"field": "action", "message": "处理动作不正确"}]})
    session = get_session()
    instance = _load_instance(int(instance_id))
    actor = _actor(user_id)
    if instance.status == "SUSPENDED" and actor == int(instance.initiator):
        raise BizError(1008)
    if instance.status != "RUNNING":
        raise BizError(1008)
    task = session.scalar(
        select(FlowTask).where(
            FlowTask.instance_id == instance.id,
            FlowTask.status == "PENDING",
            FlowTask.assignee == actor,
            FlowTask.node == instance.current_node,
        )
    )
    if task is None:
        raise BizError(1008)
    nodes = _nodes_of(instance)
    index = _node_index(nodes, instance.current_node)
    if action_name == "RETURN":
        if index <= 0:
            raise BizError(1001, "已经是第一个节点")
        _finish_task(task, "RETURN", comment)
        _cancel_siblings(instance, task.id)
        _open_node(instance, nodes, index - 1)
        session.flush()
        return _instance_view(instance)
    if action_name == "REJECT":
        _finish_task(task, "REJECT", comment)
        _cancel_siblings(instance, task.id)
        instance.status = "REJECTED"
        session.flush()
        _reject_side_effects(instance)
        return _instance_view(instance)
    _finish_task(task, "APPROVE", comment)
    _cancel_siblings(instance, task.id)
    if index + 1 >= len(nodes):
        instance.status = "APPROVED"
        session.flush()
        _finish_callback(instance, "APPROVED")
        return _instance_view(instance)
    _open_node(instance, nodes, index + 1)
    session.flush()
    return _instance_view(instance)


def cancel(instance_id: int, user_id: int | None = None) -> dict:
    instance = _load_instance(int(instance_id))
    actor = _actor(user_id)
    ctx = get_ctx()
    has_perm = bool(ctx and "ims:flow:cancel" in (ctx.perm_codes or set()))
    if actor != int(instance.initiator) and not has_perm:
        raise BizError(1139)
    if instance.status not in {"RUNNING", "SUSPENDED"}:
        raise BizError(1139)
    session = get_session()
    task_ids = list(session.scalars(select(FlowTask.id).where(FlowTask.instance_id == instance.id)))
    pending = list(session.scalars(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING")))
    for task in pending:
        task.status = "CANCELLED"
    filters = [and_(Todo.source_type == "FLOW_INSTANCE", Todo.source_id == instance.id)]
    if task_ids:
        filters.append(and_(Todo.source_type == "FLOW_TASK", Todo.source_id.in_(task_ids)))
    todos = list(session.scalars(select(Todo).where(Todo.status == "PENDING", or_(*filters))))
    for todo in todos:
        todo.status = "CANCELLED"
    instance.status = "CANCELLED"
    session.flush()
    return _instance_view(instance)


def scan_overdue() -> int:
    session = get_session()
    now = now_naive()
    rows = list(
        session.scalars(
            select(FlowTask).where(
                FlowTask.status == "PENDING",
                FlowTask.due_time.is_not(None),
                FlowTask.due_time < now,
                FlowTask.overdue == 0,
                FlowTask.urge_sent == 0,
            )
        )
    )
    for task in rows:
        task.overdue = 1
        task.urge_sent = 1
        if not task.assignee:
            continue
        send_notify(int(task.assignee), "审批已超时", "督办：有一条审批已超时，请尽快处理", "FLOW_OVERDUE", f"task:{task.id}")
        todo_create("FLOW_TASK", task.id, "WARNING", "督办", user_ids=[int(task.assignee)])
    if rows:
        session.flush()
    return len(rows)


def _open_node(instance: FlowInstance, nodes: list, index: int) -> list[FlowTask]:
    node = nodes[index]
    assignees, suspend = _resolve_assignees(node, int(instance.initiator))
    instance.current_node = str(node.get("key") or "")
    if suspend or not assignees:
        instance.status = "SUSPENDED"
        assert_dict_values(instance)
        todo_create("FLOW_INSTANCE", instance.id, "APPROVAL", "流程缺少处理人", perm_code="ims:flow:manage")
        return []
    instance.status = "RUNNING"
    due = None
    if node.get("dueHours") not in (None, ""):
        due = now_naive() + timedelta(hours=float(node["dueHours"]))
    session = get_session()
    tasks = []
    for user_id in assignees:
        task = FlowTask(
            instance_id=instance.id,
            node=instance.current_node,
            assignee=int(user_id),
            status="PENDING",
            due_time=due,
            overdue=0,
            urge_sent=0,
        )
        session.add(task)
        session.flush()
        todo_create("FLOW_TASK", task.id, "APPROVAL", f"待审批 {instance.current_node}", user_ids=[int(user_id)])
        tasks.append(task)
    return tasks


def _resolve_assignees(node: dict, initiator_id: int) -> tuple[list[int], bool]:
    if node.get("assigneeUserId") not in (None, ""):
        user_id = int(node["assigneeUserId"])
        if user_id == initiator_id:
            return [], True
        return [user_id], False
    if node.get("permCode"):
        found = users_with_perm(str(node["permCode"]))
        if not found or set(found) <= {initiator_id}:
            return [], True
        return [user_id for user_id in found if user_id != initiator_id], False
    if node.get("rule") == "LEADER":
        leader = _leader_of(initiator_id)
        if leader is None or leader == initiator_id:
            return [], True
        return [leader], False
    raise BizError(1001, data={"fieldErrors": [{"field": "nodes", "message": "节点未指定处理人"}]})


def _leader_of(user_id: int) -> int | None:
    session = get_session()
    user = session.get(User, int(user_id))
    if user is None or not user.main_dept_id:
        return None
    dept = session.get(Dept, int(user.main_dept_id))
    if dept is None:
        return None
    leader = dept.leader_user_id
    if leader is not None and int(leader) != int(user_id):
        return int(leader)
    if not dept.parent_id:
        return None
    parent = session.get(Dept, int(dept.parent_id))
    if parent is None or not parent.leader_user_id:
        return None
    if int(parent.leader_user_id) == int(user_id):
        return None
    return int(parent.leader_user_id)


def _finish_callback(instance: FlowInstance, result: str) -> None:
    action = "REJECT" if result == "REJECTED" else "APPROVE"
    payload = {
        "instanceId": instance.id,
        "action": action,
        "result": result,
        "bizType": instance.biz_type,
        "bizId": instance.biz_id,
        "initiator": instance.initiator,
    }
    for callback in list(callbacks):
        callback(dict(payload))


def _reject_side_effects(instance: FlowInstance) -> None:
    payload = {
        "instanceId": instance.id,
        "action": "REJECT",
        "result": "REJECTED",
        "bizType": instance.biz_type,
        "bizId": instance.biz_id,
        "initiator": instance.initiator,
    }
    events.publish("flow.rejected", payload)
    for callback in list(callbacks):
        callback(dict(payload))
    send_notify(int(instance.initiator), "流程已驳回", "您发起的流程已被驳回", "FLOW_REJECT", str(instance.id))


def _finish_task(task: FlowTask, action: str, comment: str | None) -> None:
    task.status = "DONE"
    task.action = action
    task.comment = comment
    _close_task_todo(task, done=True)


def _cancel_siblings(instance: FlowInstance, keep_id: int) -> None:
    session = get_session()
    rows = list(
        session.scalars(
            select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING", FlowTask.id != keep_id)
        )
    )
    for task in rows:
        task.status = "CANCELLED"
        _close_task_todo(task, done=False)


def _close_task_todo(task: FlowTask, done: bool) -> None:
    row = get_session().scalar(
        select(Todo).where(Todo.source_type == "FLOW_TASK", Todo.source_id == task.id, Todo.type == "APPROVAL", Todo.status == "PENDING")
    )
    if row is None:
        return
    if done:
        row.status = "DONE"
        row.done_by = task.assignee
    else:
        row.status = "CANCELLED"


def _nodes_of(instance: FlowInstance) -> list:
    version = get_session().get(FlowTemplateVersion, instance.template_version_id)
    if version is None:
        raise BizError(1504)
    return list(version.nodes or [])


def _node_index(nodes: list, key: str | None) -> int:
    for index, node in enumerate(nodes):
        if node.get("key") == key:
            return index
    return 0


def _load_instance(instance_id: int) -> FlowInstance:
    row = get_session().get(FlowInstance, instance_id)
    if row is None or row.deleted:
        raise BizError(1504)
    return row


def _actor(user_id: int | None) -> int:
    if user_id is not None:
        return int(user_id)
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None:
        raise BizError(1008)
    return int(ctx.user_id)


def _normalize_nodes(nodes: list) -> list:
    if not isinstance(nodes, list) or not nodes:
        raise BizError(1001, data={"fieldErrors": [{"field": "nodes", "message": "请配置流程节点"}]})
    cleaned = []
    for node in nodes:
        if not isinstance(node, dict) or not str(node.get("key") or "").strip():
            raise BizError(1001, data={"fieldErrors": [{"field": "nodes", "message": "节点缺少标识"}]})
        cleaned.append(dict(node))
    return cleaned


def _version_view(template: FlowTemplate | None, row: FlowTemplateVersion) -> dict:
    return {
        "templateId": row.template_id,
        "versionId": row.id,
        "version": row.version,
        "status": row.status,
        "code": template.code if template else None,
        "name": template.name if template else None,
    }


def _instance_view(instance: FlowInstance, tasks: list | None = None) -> dict:
    if tasks is None:
        tasks = list(
            get_session().scalars(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING"))
        )
    return {
        "id": instance.id,
        "status": instance.status,
        "currentNode": instance.current_node,
        "templateVersionId": instance.template_version_id,
        "initiator": instance.initiator,
        "taskIds": [task.id for task in tasks],
    }
