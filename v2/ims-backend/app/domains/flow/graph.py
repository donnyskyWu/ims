"""流程图编排：串行、并行会签、条件、抄送与计时。"""
from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.errors import BizError
from app.db.repository import assert_dict_values
from app.db.session import get_session
from app.domains.flow.model import FlowCcRecord, FlowInstance, FlowTask, FlowTemplateVersion
from app.domains.flow.service import (
    Unresolved,
    _alert_unresolved,
    _create_tasks,
    _domain_of_instance,
    _raw_candidates,
    _rule_of,
    _trace,
    on_flow_finished,
    resolve_assignees,
)
from app.domains.message.service import send_notify

_ASSIGN_TYPES = {"USER", "LEADER", "PERM", "DEPT_LEADER"}
_EXPR = re.compile(r"^form\.([A-Za-z0-9_]+)\s*(==|!=)\s*'([^']*)'$")


def normalize_nodes(raw, *, strict: bool = False) -> list[dict]:
    if not isinstance(raw, list):
        raise BizError(1001, data={"fieldErrors": [{"field": "nodes", "message": "请配置流程节点"}]})
    cleaned = []
    errors = []
    for index, node in enumerate(raw):
        if not isinstance(node, dict):
            errors.append({"field": "nodes", "message": "节点格式不正确"})
            continue
        order = node.get("nodeOrder", index + 1)
        try:
            order = int(order)
        except (TypeError, ValueError):
            errors.append({"field": "nodeOrder", "message": "节点顺序不正确"})
            continue
        name = str(node.get("nodeName") or node.get("name") or "").strip()
        if strict and not name:
            errors.append({"field": "nodeName", "message": "请填写节点名称"})
        if len(name) > 64:
            errors.append({"field": "nodeName", "message": "节点名称不能超过 64 字"})
        kind = str(node.get("nodeType") or "APPROVE").upper()
        if kind not in {"START", "END", "APPROVE", "TASK", "CC", "TIMER"}:
            errors.append({"field": "nodeType", "message": "节点类型不正确"})
        key = str(node.get("nodeKey") or node.get("key") or f"n{order}").strip()
        sla = node.get("slaHours", node.get("dueHours"))
        if sla not in (None, ""):
            try:
                sla = int(sla)
            except (TypeError, ValueError):
                errors.append({"field": "slaHours", "message": "时限须为正整数"})
                sla = None
            if isinstance(sla, int) and sla <= 0:
                errors.append({"field": "slaHours", "message": "时限须为正整数"})
        item = {
            "nodeOrder": order,
            "nodeKey": key,
            "key": key,
            "nodeName": name or key,
            "nodeType": kind,
            "assigneeRule": _clean_rule(node),
            "slaHours": sla if isinstance(sla, int) and sla > 0 else None,
            "formFields": list(node.get("formFields") or []),
            "conditionExpr": list(node.get("conditionExpr") or []),
            "parallelGroup": str(node.get("parallelGroup") or "").strip(),
            "nextOrders": [int(value) for value in (node.get("nextOrders") or []) if str(value).isdigit() or isinstance(value, int)],
        }
        if item["slaHours"]:
            item["dueHours"] = item["slaHours"]
        cleaned.append(item)
    if errors and strict:
        raise BizError(1001, data={"fieldErrors": errors})
    if not cleaned and strict:
        raise BizError(1001, data={"fieldErrors": [{"field": "nodes", "message": "请配置流程节点"}]})
    cleaned.sort(key=lambda item: item["nodeOrder"])
    return cleaned


def _clean_rule(node: dict) -> dict:
    rule = _rule_of(node)
    if not rule.get("assignType"):
        return {}
    saved = {"assignType": rule["assignType"]}
    if rule["assignType"] == "USER":
        saved["targetUserIds"] = [str(item) for item in rule.get("targetUserIds") or []]
    if rule["assignType"] == "PERM":
        saved["permCode"] = str(rule.get("permCode") or "")
    if rule["assignType"] == "DEPT_LEADER" and rule.get("targetDeptId") not in (None, ""):
        saved["targetDeptId"] = str(rule.get("targetDeptId"))
    return saved


def validate_publish(nodes: list[dict]) -> None:
    if not nodes:
        raise BizError(1131, data={"nodeKeys": []})
    kinds = {node["nodeType"] for node in nodes}
    if "START" not in kinds or "END" not in kinds:
        raise BizError(1131, data={"nodeKeys": [node["nodeKey"] for node in nodes if node["nodeType"] not in {"START", "END"}]})
    errors = []
    for node in nodes:
        if node["nodeType"] in {"APPROVE", "TASK"}:
            rule = node.get("assigneeRule") or {}
            if rule.get("assignType") not in _ASSIGN_TYPES:
                errors.append(node["nodeKey"])
            elif rule["assignType"] == "PERM" and not str(rule.get("permCode") or "").strip():
                errors.append(node["nodeKey"])
            elif rule["assignType"] == "USER" and not rule.get("targetUserIds"):
                errors.append(node["nodeKey"])
            elif rule["assignType"] == "DEPT_LEADER" and not rule.get("targetDeptId"):
                errors.append(node["nodeKey"])
    if errors:
        raise BizError(1132, data={"nodeKeys": errors})
    cycle = _cycle_keys(nodes)
    if cycle:
        raise BizError(1131, data={"nodeKeys": cycle})


def preview_graph(nodes: list[dict]) -> dict:
    edges = []
    for node in nodes:
        for target in _successors(node, nodes, None):
            label = ""
            for cond in node.get("conditionExpr") or []:
                if int(cond.get("nextNodeOrder") or 0) == target:
                    label = str(cond.get("expression") or "")
            edges.append({"fromNodeOrder": node["nodeOrder"], "toNodeOrder": target, "conditionLabel": label})
    graph = "SERIAL"
    if any(node.get("conditionExpr") for node in nodes):
        graph = "CONDITIONAL"
    elif any(node.get("parallelGroup") for node in nodes):
        graph = "PARALLEL"
    return {
        "nodes": [
            {
                "nodeOrder": node["nodeOrder"],
                "nodeKey": node["nodeKey"],
                "nodeName": node["nodeName"],
                "nodeType": node["nodeType"],
                "slaHours": node.get("slaHours"),
                "assigneePreview": assignee_preview(node),
                "parallelGroup": node.get("parallelGroup") or "",
            }
            for node in nodes
        ],
        "edges": edges,
        "graphType": graph,
    }


def assignee_preview(node: dict) -> str:
    rule = node.get("assigneeRule") or {}
    kind = rule.get("assignType")
    if node.get("nodeType") in {"START", "END"}:
        return "系统"
    if node.get("nodeType") == "TIMER":
        return "到点自动流转"
    if kind == "USER":
        return "指定人"
    if kind == "LEADER":
        return "发起人直属上级（运行时按发起人组织解析）"
    if kind == "PERM":
        return f"持有权限码 {rule.get('permCode') or ''}".strip()
    if kind == "DEPT_LEADER":
        return "指定部门负责人"
    if node.get("nodeType") == "CC":
        return "抄送"
    return "未配置"


def open_entry(instance: FlowInstance, nodes: list[dict]) -> list[FlowTask]:
    if not nodes:
        raise BizError(1132)
    return open_orders(instance, nodes, [nodes[0]["nodeOrder"]])


def open_orders(instance: FlowInstance, nodes: list[dict], orders: list[int], seen: set | None = None, hold_start: bool = False) -> list[FlowTask]:
    by_order = {node["nodeOrder"]: node for node in nodes}
    seen = seen or set()
    created: list[FlowTask] = []
    for order in orders:
        if order in seen or order not in by_order:
            continue
        node = by_order[order]
        group = node.get("parallelGroup") or ""
        if group:
            members = [item for item in nodes if item.get("parallelGroup") == group]
            for member in members:
                if member["nodeOrder"] in seen:
                    continue
                seen.add(member["nodeOrder"])
                created.extend(_open_one(instance, nodes, member, hold_start=hold_start))
            continue
        seen.add(order)
        created.extend(_open_one(instance, nodes, node, hold_start=hold_start))
    _refresh_current(instance)
    return created


def complete_human(instance: FlowInstance, task: FlowTask, action: str, comment: str | None, reject_to: int | None, form_patch: dict | None) -> dict:
    nodes = _nodes(instance)
    node = _node_of(task, nodes)
    if form_patch:
        merged = dict(instance.form_data or {})
        merged.update(form_patch)
        instance.form_data = merged
    task.status = "REJECTED" if action == "REJECT" else "APPROVED"
    task.action = action
    task.comment = comment
    task.handled_at = now_naive()
    from app.domains.flow.service import _cancel_siblings, _close_task_todo

    _cancel_siblings(instance, task.id)
    _close_task_todo(task, done=True)
    _trace(instance, task, node, action, comment or "", actor_id=int(task.assignee or 0), comment=comment)
    if action == "REJECT":
        target = reject_to if reject_to is not None else _default_return(nodes)
        _clear_pending(instance)
        open_orders(instance, nodes, [target], hold_start=True)
        get_session().flush()
        return {"waitingParallel": False}
    group = node.get("parallelGroup") or ""
    if group and _group_pending(instance, group):
        get_session().commit()
        raise BizError(1137)
    if group:
        _leave_group(instance, nodes, group)
    else:
        nxt = _successors(node, nodes, instance.form_data or {})
        if not nxt:
            _finish(instance, "APPROVED")
        else:
            open_orders(instance, nodes, nxt)
    get_session().flush()
    return {"waitingParallel": False}


def require_parallel_ready(instance: FlowInstance, group: str) -> None:
    if group and _group_pending(instance, group):
        raise BizError(1137)


def advance_timers() -> int:
    session = get_session()
    now = now_naive()
    rows = list(
        session.scalars(
            select(FlowTask).where(FlowTask.status == "PENDING", FlowTask.node_type == "TIMER", FlowTask.due_time.is_not(None), FlowTask.due_time <= now)
        )
    )
    moved = 0
    for task in rows:
        instance = session.get(FlowInstance, task.instance_id)
        if instance is None or instance.status not in {"RUNNING", "TIMEOUT"}:
            continue
        nodes = _nodes(instance)
        node = _node_of(task, nodes)
        task.status = "APPROVED"
        task.action = "AUTO"
        task.handled_at = now
        nxt = _successors(node, nodes, instance.form_data or {})
        if nxt:
            open_orders(instance, nodes, nxt)
        else:
            _finish(instance, "APPROVED")
        moved += 1
    if moved:
        session.flush()
    return moved


def _open_one(instance: FlowInstance, nodes: list[dict], node: dict, hold_start: bool = False) -> list[FlowTask]:
    kind = node["nodeType"]
    if kind == "END":
        _finish(instance, "APPROVED")
        return []
    if kind == "START":
        if hold_start:
            return _resubmit(instance, node)
        return open_orders(instance, nodes, _successors(node, nodes, instance.form_data or {}))
    if kind == "CC":
        _copy(instance, node)
        return open_orders(instance, nodes, _successors(node, nodes, instance.form_data or {}))
    if kind == "TIMER":
        return [_timer_task(instance, node)]
    return _assign_human(instance, node)


def _resubmit(instance: FlowInstance, node: dict) -> list[FlowTask]:
    """退回到发起节点时交给发起人补件，不走「不能审自己」改派。"""
    hours = node.get("slaHours")
    due = now_naive() + timedelta(hours=float(hours)) if hours else None
    if instance.status != "TIMEOUT":
        instance.status = "RUNNING"
    return _create_tasks(instance, node, [int(instance.initiator)], due, None)


def _assign_human(instance: FlowInstance, node: dict) -> list[FlowTask]:
    domain = _domain_of_instance(instance)
    try:
        assignees, note = resolve_assignees(node, int(instance.initiator), domain)
    except Unresolved:
        instance.status = "RUNNING"
        assert_dict_values(instance)
        get_session().flush()
        _alert_unresolved(instance)
        get_session().commit()
        raise BizError(1132)
    if note:
        _trace(instance, None, node, "REASSIGN", note, actor_id=int(instance.initiator))
    hours = node.get("slaHours")
    due = now_naive() + timedelta(hours=float(hours)) if hours else None
    if instance.status != "TIMEOUT":
        instance.status = "RUNNING"
    return _create_tasks(instance, node, assignees, due, note)


def _copy(instance: FlowInstance, node: dict) -> None:
    rule = node.get("assigneeRule") or {}
    if rule:
        users = _raw_candidates(rule, int(instance.initiator))
    else:
        users = []
    session = get_session()
    now = now_naive()
    for user_id in users:
        session.add(
            FlowCcRecord(
                instance_id=instance.id,
                node_order=int(node["nodeOrder"]),
                node_name=node.get("nodeName") or "",
                user_id=int(user_id),
                notified_at=now,
            )
        )
        send_notify(int(user_id), "流程抄送", f"{node.get('nodeName') or '抄送'}：请知悉", "FLOW_CC", f"cc:{instance.id}:{node['nodeOrder']}:{user_id}")
    session.flush()


def _timer_task(instance: FlowInstance, node: dict) -> FlowTask:
    hours = node.get("slaHours") or 0
    due = now_naive() + timedelta(hours=float(hours or 0))
    task = FlowTask(
        instance_id=instance.id,
        node=node["nodeKey"],
        assignee=None,
        status="PENDING",
        due_time=due,
        overdue=0,
        urge_sent=0,
        node_order=int(node["nodeOrder"]),
        node_name=node.get("nodeName") or "",
        node_type="TIMER",
        sla_hours=int(hours) if hours else None,
        remind_count=0,
        warn_sent=0,
    )
    get_session().add(task)
    get_session().flush()
    return task


def _leave_group(instance: FlowInstance, nodes: list[dict], group: str) -> None:
    require_parallel_ready(instance, group)
    by_order = {node["nodeOrder"]: node for node in nodes}
    dest = []
    for node in nodes:
        if node.get("parallelGroup") != group:
            continue
        for order in _successors(node, nodes, instance.form_data or {}):
            target = by_order.get(order)
            if target is None or target.get("parallelGroup") == group:
                continue
            if order not in dest:
                dest.append(order)
    if dest:
        open_orders(instance, nodes, dest)
    else:
        _finish(instance, "APPROVED")


def _finish(instance: FlowInstance, status: str) -> None:
    instance.status = status
    instance.finished_at = now_naive()
    instance.current_node = ""
    assert_dict_values(instance)
    get_session().flush()
    if status == "REJECTED":
        from app.domains.flow.service import _reject_side_effects

        _reject_side_effects(instance)
    else:
        on_flow_finished(instance.biz_type, int(instance.biz_id or 0), status, instance)


def _group_pending(instance: FlowInstance, group: str) -> bool:
    rows = list(
        get_session().scalars(
            select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.parallel_group == group, FlowTask.status == "PENDING")
        )
    )
    return bool(rows)


def _clear_pending(instance: FlowInstance) -> None:
    from app.domains.flow.service import _close_task_todo

    rows = list(get_session().scalars(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING")))
    for task in rows:
        task.status = "CANCELLED"
        _close_task_todo(task, done=False)


def _default_return(nodes: list[dict]) -> int:
    for node in nodes:
        if node["nodeType"] == "START":
            return int(node["nodeOrder"])
    return int(nodes[0]["nodeOrder"])


def _successors(node: dict, nodes: list[dict], form: dict | None) -> list[int]:
    by_order = {item["nodeOrder"]: item for item in nodes}
    matched = _match_condition(node, form or {})
    if matched:
        return [item for item in matched if item in by_order]
    explicit = [int(item) for item in node.get("nextOrders") or [] if int(item) in by_order]
    if explicit:
        return explicit
    nxt = int(node["nodeOrder"]) + 1
    if nxt in by_order:
        return [nxt]
    return []


def _structural_next(node: dict, by_order: dict) -> list[int]:
    found = []
    for cond in node.get("conditionExpr") or []:
        order = int(cond.get("nextNodeOrder") or 0)
        if order in by_order and order not in found:
            found.append(order)
    for item in node.get("nextOrders") or []:
        order = int(item)
        if order in by_order and order not in found:
            found.append(order)
    if found:
        return found
    nxt = int(node["nodeOrder"]) + 1
    if nxt in by_order:
        return [nxt]
    return []


def _match_condition(node: dict, form: dict) -> list[int] | None:
    conds = node.get("conditionExpr") or []
    if not conds:
        return None
    for cond in conds:
        expr = str(cond.get("expression") or "").strip()
        if expr in {"", "*", "true"} or _expr_ok(expr, form):
            return [int(cond.get("nextNodeOrder") or 0)]
    return None


def _expr_ok(expr: str, form: dict) -> bool:
    found = _EXPR.match(expr.replace('"', "'"))
    if not found:
        return False
    key, op, expected = found.group(1), found.group(2), found.group(3)
    actual = "" if form.get(key) is None else str(form.get(key))
    if op == "==":
        return actual == expected
    return actual != expected


def _cycle_keys(nodes: list[dict]) -> list[str]:
    by_order = {node["nodeOrder"]: node for node in nodes}
    visiting = set()
    visited = set()
    cycle = []

    def walk(order: int) -> bool:
        if order in visiting:
            cycle.append(by_order[order]["nodeKey"])
            return True
        if order in visited or order not in by_order:
            return False
        visiting.add(order)
        for nxt in _structural_next(by_order[order], by_order):
            if walk(nxt):
                cycle.append(by_order[order]["nodeKey"])
                return True
        visiting.remove(order)
        visited.add(order)
        return False

    for node in nodes:
        if walk(node["nodeOrder"]):
            return list(dict.fromkeys(reversed(cycle)))
    return []


def _nodes(instance: FlowInstance) -> list[dict]:
    version = get_session().get(FlowTemplateVersion, instance.template_version_id)
    if version is None:
        raise BizError(1504)
    return list(version.nodes or [])


def _node_of(task: FlowTask, nodes: list[dict]) -> dict:
    for node in nodes:
        if node.get("nodeKey") == task.node or node.get("key") == task.node:
            return node
    return {"nodeOrder": task.node_order or 0, "nodeKey": task.node, "key": task.node, "nodeName": task.node_name or task.node, "nodeType": task.node_type or "APPROVE"}


def _refresh_current(instance: FlowInstance) -> None:
    pending = list(
        get_session().scalars(select(FlowTask.node).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING"))
    )
    if pending:
        instance.current_node = str(pending[0])[:64]
