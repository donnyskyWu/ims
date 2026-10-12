"""流程模板、发起、办理、撤销与超时催办。"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import and_, func, or_, select

from app.core.clock import now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.events import events
from app.db.repository import assert_dict_values
from app.db.session import get_session
from app.domains.flow.model import FlowInstance, FlowTask, FlowTemplate, FlowTemplateVersion, FlowTrace
from app.domains.message.service import send_notify
from app.domains.system.model import Dept, Role, User, UserRole
from app.domains.todo.model import Todo
from app.domains.todo.service import todo_create, users_with_perm

log = logging.getLogger("ims.flow")

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
        raise BizError(1008, "不能审核自己提交的单据")
    if instance.status not in {"RUNNING", "TIMEOUT"}:
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
    if task.assignee is not None and int(task.assignee) == int(instance.initiator):
        raise BizError(1008, "不能审核自己提交的单据")
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
    has_perm = bool(ctx and ({"ims:flow:cancel", "ims:flow:instance:cancel"} & set(ctx.perm_codes or set())))
    if instance.status not in {"RUNNING", "SUSPENDED", "TIMEOUT"}:
        raise BizError(1140)
    if actor != int(instance.initiator) and not has_perm:
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
    _warn_approaching(now)
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
        task.remind_count = int(task.remind_count or 0) + 1
        instance = session.get(FlowInstance, task.instance_id)
        if instance is not None and instance.status == "RUNNING":
            instance.status = "TIMEOUT"
            assert_dict_values(instance)
        if not task.assignee:
            continue
        send_notify(int(task.assignee), "审批已超时", "督办：有一条审批已超时，请尽快处理", "FLOW_OVERDUE", f"task:{task.id}")
        todo_create(
            "FLOW_TASK",
            task.id,
            "WARNING",
            "督办",
            user_ids=[int(task.assignee)],
            route=f"/ims/flow/task?taskId={task.id}",
            source_module="FLOW",
        )
    if rows:
        session.flush()
    _escalate_overdue(now)
    try:
        from app.domains.flow.graph import advance_timers

        advance_timers()
    except Exception:
        log.exception("计时节点自动流转失败")
    return len(rows)


def _warn_approaching(now) -> None:
    session = get_session()
    rows = list(
        session.scalars(
            select(FlowTask).where(
                FlowTask.status == "PENDING",
                FlowTask.due_time.is_not(None),
                FlowTask.overdue == 0,
                FlowTask.warn_sent == 0,
                FlowTask.assignee.is_not(None),
            )
        )
    )
    for task in rows:
        start = task.create_time or now
        total = (task.due_time - start).total_seconds()
        if total <= 0:
            continue
        if (now - start).total_seconds() < total * 0.8:
            continue
        if task.due_time <= now:
            continue
        task.warn_sent = 1
        send_notify(int(task.assignee), "审批即将超时", "有一条审批即将到达时限，请尽快处理", "FLOW_WARN", f"warn:{task.id}")
    session.flush()


def _escalate_overdue(now) -> None:
    session = get_session()
    deadline = now - timedelta(hours=24)
    rows = list(
        session.scalars(
            select(FlowTask).where(
                FlowTask.status == "PENDING",
                FlowTask.overdue == 1,
                FlowTask.escalated == 0,
                FlowTask.due_time.is_not(None),
                FlowTask.due_time < deadline,
            )
        )
    )
    for task in rows:
        task.escalated = 1
        targets = set()
        if task.assignee:
            leader = _leader_of(int(task.assignee))
            if leader:
                targets.add(int(leader))
        instance = session.get(FlowInstance, task.instance_id)
        domain = ""
        if instance is not None and instance.template_id:
            template = session.get(FlowTemplate, int(instance.template_id))
            domain = (template.business_domain or "") if template else ""
        for user_id in domain_owner_ids(domain, 0):
            targets.add(int(user_id))
        for user_id in targets:
            send_notify(user_id, "审批超时已升级", "有一条审批超时超过一天，请督办处理", "FLOW_ESCALATE", f"esc:{task.id}:{user_id}")
    if rows:
        session.flush()


class Unresolved(Exception):
    """处理人经过改派链后仍无人可派。"""


def _open_node(instance: FlowInstance, nodes: list, index: int) -> list[FlowTask]:
    node = nodes[index]
    domain = _domain_of_instance(instance)
    try:
        assignees, note = resolve_assignees(node, int(instance.initiator), domain)
    except Unresolved:
        instance.status = "RUNNING"
        instance.current_node = str(node.get("key") or node.get("nodeKey") or "")
        assert_dict_values(instance)
        get_session().flush()
        _alert_unresolved(instance)
        get_session().commit()
        raise BizError(1132)
    instance.current_node = str(node.get("key") or node.get("nodeKey") or "")
    if instance.status == "SUSPENDED":
        instance.status = "RUNNING"
    due = None
    hours = node.get("dueHours", node.get("slaHours"))
    if hours not in (None, ""):
        due = now_naive() + timedelta(hours=float(hours))
    if note:
        _trace(instance, None, node, "REASSIGN", note, actor_id=int(instance.initiator))
    return _create_tasks(instance, node, assignees, due, note)


def resolve_assignees(node: dict, initiator_id: int, domain: str | None = None) -> tuple[list[int], str | None]:
    """按 C078 解析处理人。返回（候选人，改派留痕或空）。无人可派时抛 Unresolved。"""
    rule = _rule_of(node)
    raw = _raw_candidates(rule, initiator_id)
    self_case = initiator_id in raw or (not raw and rule.get("assignType") == "LEADER")
    if raw and initiator_id not in raw:
        return raw, None
    if raw and initiator_id in raw:
        others = [user_id for user_id in raw if user_id != initiator_id]
        if others:
            return others, _reassign_sentence(others)
    if not self_case:
        raise Unresolved()
    leader = _leader_of(initiator_id)
    if leader and leader != initiator_id:
        return [leader], _reassign_sentence([leader])
    owners = domain_owner_ids(domain or "", initiator_id)
    if owners:
        return owners, _reassign_sentence(owners)
    others = other_managers(initiator_id)
    if others:
        return others, _reassign_sentence(others)
    raise Unresolved()


def _rule_of(node: dict) -> dict:
    rule = node.get("assigneeRule") if isinstance(node.get("assigneeRule"), dict) else {}
    assign_type = str(rule.get("assignType") or "").upper()
    if not assign_type:
        if node.get("assigneeUserId") not in (None, "") or node.get("targetUserIds"):
            assign_type = "USER"
        elif node.get("permCode"):
            assign_type = "PERM"
        elif node.get("rule") == "LEADER":
            assign_type = "LEADER"
        elif node.get("targetDeptId") not in (None, ""):
            assign_type = "DEPT_LEADER"
    alias = {"POSITION": "PERM", "INITIATOR_SUPERIOR": "LEADER", "DEPT": "DEPT_LEADER"}
    assign_type = alias.get(assign_type, assign_type)
    user_ids = list(rule.get("targetUserIds") or node.get("targetUserIds") or [])
    if node.get("assigneeUserId") not in (None, "") and not user_ids:
        user_ids = [node.get("assigneeUserId")]
    return {
        "assignType": assign_type,
        "targetUserIds": user_ids,
        "permCode": rule.get("permCode") or node.get("permCode") or "",
        "targetDeptId": rule.get("targetDeptId") if rule.get("targetDeptId") not in (None, "") else node.get("targetDeptId"),
    }


def _raw_candidates(rule: dict, initiator_id: int) -> list[int]:
    assign_type = rule.get("assignType")
    if assign_type == "USER":
        found = []
        for item in rule.get("targetUserIds") or []:
            if item in (None, ""):
                continue
            found.append(int(item))
        return _unique(found)
    if assign_type == "PERM":
        code = str(rule.get("permCode") or "").strip()
        if not code:
            return []
        return _unique(users_with_perm(code))
    if assign_type == "LEADER":
        leader = _leader_of(initiator_id)
        return [leader] if leader else []
    if assign_type == "DEPT_LEADER":
        dept_id = rule.get("targetDeptId")
        if dept_id in (None, ""):
            return []
        dept = get_session().get(Dept, int(dept_id))
        if dept is None or not dept.leader_user_id:
            return []
        return [int(dept.leader_user_id)]
    return []


def domain_owner_ids(domain: str, exclude: int) -> list[int]:
    if not domain:
        return []
    session = get_session()
    roles = list(session.scalars(select(Role).where(Role.status == "ENABLED")))
    role_ids = []
    for role in roles:
        parts = [part.strip() for part in (role.flow_domain or "").split(",") if part.strip()]
        if domain in parts:
            role_ids.append(role.id)
    if not role_ids:
        return []
    holders = set(users_with_perm("ims:flow:instance:manage")) or set(users_with_perm("ims:flow:manage"))
    found = []
    links = list(session.scalars(select(UserRole).where(UserRole.role_id.in_(role_ids), UserRole.manual_removed == 0)))
    for link in links:
        user_id = int(link.user_id)
        if user_id == int(exclude) or user_id not in holders:
            continue
        user = session.get(User, user_id)
        if user is None or user.deleted or user.status != "ACTIVE":
            continue
        found.append(user_id)
    return _unique(found)


def other_managers(exclude: int) -> list[int]:
    holders = users_with_perm("ims:flow:instance:manage") or users_with_perm("ims:flow:manage")
    session = get_session()
    platform = []
    rest = []
    for user_id in holders:
        if int(user_id) == int(exclude):
            continue
        links = list(session.scalars(select(UserRole).where(UserRole.user_id == int(user_id), UserRole.manual_removed == 0)))
        roles = [session.get(Role, link.role_id) for link in links]
        if any(role and not (role.flow_domain or "").strip() and (role.data_scope or "") == "ALL" and role.status == "ENABLED" for role in roles):
            platform.append(int(user_id))
        else:
            rest.append(int(user_id))
    return _unique(platform + rest)


def _reassign_sentence(user_ids: list[int]) -> str:
    return f"审批人为发起人，已改派给 {_display_names(user_ids)}"


def _display_names(user_ids: list[int]) -> str:
    session = get_session()
    parts = []
    for user_id in user_ids:
        user = session.get(User, int(user_id))
        if user is None:
            continue
        label = user.nickname or user.username or str(user.id)
        if user.emp_no:
            label = f"{label}（{user.emp_no}）"
        parts.append(label)
    return "、".join(parts) or "其他处理人"


def _create_tasks(instance: FlowInstance, node: dict, assignees: list[int], due, note: str | None) -> list[FlowTask]:
    session = get_session()
    if instance.status not in {"TIMEOUT"}:
        instance.status = "RUNNING"
    tasks = []
    hours = node.get("slaHours", node.get("dueHours"))
    for user_id in assignees:
        task = FlowTask(
            instance_id=instance.id,
            node=str(node.get("key") or node.get("nodeKey") or instance.current_node or ""),
            assignee=int(user_id),
            status="PENDING",
            due_time=due,
            overdue=0,
            urge_sent=0,
            node_order=int(node.get("nodeOrder") or 0),
            node_name=str(node.get("nodeName") or node.get("key") or ""),
            node_type=str(node.get("nodeType") or "APPROVE"),
            sla_hours=int(hours) if hours not in (None, "") else None,
            remind_count=0,
            reassign_from=int(instance.initiator) if note else None,
            parallel_group=str(node.get("parallelGroup") or "") or None,
            warn_sent=0,
        )
        session.add(task)
        session.flush()
        todo_create(
            "FLOW_TASK",
            task.id,
            "APPROVAL",
            f"待审批 {task.node_name or task.node}",
            user_ids=[int(user_id)],
            route=f"/ims/flow/task?taskId={task.id}",
            source_module="FLOW",
            due_time=due,
            summary=task.node_name or "",
        )
        tasks.append(task)
    return tasks


def _alert_unresolved(instance: FlowInstance) -> None:
    targets = other_managers(0) or [1]
    for user_id in targets:
        send_notify(int(user_id), "流程缺少处理人", "有一条流程无法解析处理人，请管理员处理", "FLOW_UNRESOLVED", f"inst:{instance.id}")


def _domain_of_instance(instance: FlowInstance) -> str:
    if not instance.template_id:
        return ""
    template = get_session().get(FlowTemplate, int(instance.template_id))
    return (template.business_domain or "") if template else ""


def _trace(instance: FlowInstance, task: FlowTask | None, node: dict, action: str, detail: str, actor_id: int | None = None, comment: str | None = None) -> None:
    row = FlowTrace(
        instance_id=instance.id,
        task_id=task.id if task is not None else None,
        node_key=str(node.get("key") or node.get("nodeKey") or ""),
        node_order=int(node.get("nodeOrder") or 0),
        node_name=str(node.get("nodeName") or node.get("key") or ""),
        actor_id=actor_id,
        action=action,
        comment=comment,
        detail=detail[:512],
    )
    get_session().add(row)
    get_session().flush()


def _unique(values: list[int]) -> list[int]:
    found = []
    seen = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        found.append(int(item))
    return found


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


def on_flow_finished(biz_type: str, biz_id: int, result: str, instance: FlowInstance | None = None) -> None:
    """业务模块注册回调。本批只记日志并通知发起人，领用/上报/培训后续挂接。"""
    log.info("flow finished biz_type=%s biz_id=%s result=%s", biz_type, biz_id, result)
    payload = {
        "instanceId": instance.id if instance is not None else None,
        "action": "REJECT" if result == "REJECTED" else "APPROVE",
        "result": result,
        "bizType": biz_type,
        "bizId": biz_id,
        "initiator": instance.initiator if instance is not None else None,
    }
    for callback in list(callbacks):
        callback(dict(payload))
    if instance is not None and result == "APPROVED":
        send_notify(int(instance.initiator), "流程已通过", "您发起的流程已通过", "FLOW_APPROVE", str(instance.id))


def _finish_callback(instance: FlowInstance, result: str) -> None:
    on_flow_finished(instance.biz_type, instance.biz_id, result, instance)


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
    keep = session.get(FlowTask, keep_id)
    stmt = select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING", FlowTask.id != keep_id)
    if keep is not None:
        stmt = stmt.where(FlowTask.node == keep.node)
    rows = list(session.scalars(stmt))
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
