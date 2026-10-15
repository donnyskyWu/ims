"""流程模板节点图：DAG、处理人规则、版本差异。不访问数据库。"""

from __future__ import annotations

NODE_TYPES = frozenset({"APPROVE", "TASK", "CC", "TIMER"})
ASSIGN_TYPES = frozenset({"USER", "POSITION", "DEPT", "INITIATOR_SUPERIOR"})
SLA_CHOICES = frozenset({2, 12, 24, 48, 72})

# 种子模板的串行预览。处理人文案在运行时再解析成 assigneeRule。
PREVIEW_NODES: dict[str, list[tuple[int, str, str, str]]] = {
    "FL-LEAVE": [
        (1, "发起申请", "TASK", "发起人"),
        (2, "部门负责人审批", "APPROVE", "岗位·部门负责人"),
        (3, "人事备案", "CC", "抄送·人事"),
        (4, "归档", "TIMER", "定时·归档"),
    ],
    "FL-REIMB": [
        (1, "发起报销", "TASK", "发起人"),
        (2, "部门负责人审批", "APPROVE", "岗位·部门负责人"),
        (3, "财务复核", "APPROVE", "岗位·财务"),
        (4, "出纳付款", "TASK", "岗位·出纳"),
        (5, "归档", "TIMER", "定时·归档"),
    ],
    "FL-CONTENT": [
        (1, "提交内容", "TASK", "发起人"),
        (2, "内容初审", "APPROVE", "岗位·内容审核"),
        (3, "发布确认", "APPROVE", "岗位·内容负责人"),
    ],
    "FL-LIVE": [
        (1, "发起开播", "TASK", "发起人"),
        (2, "直属领导审批", "APPROVE", "发起人直属上级（运行时按组织解析）"),
    ],
}


def rule_from_preview(text: str) -> dict:
    label = text or ""
    if "直属上级" in label:
        return {"assignType": "INITIATOR_SUPERIOR"}
    if "发起人" in label:
        return {"assignType": "USER", "targetIds": []}
    if "财务" in label or "出纳" in label:
        return {"assignType": "POSITION", "targetPositionCodes": ["FINANCE"]}
    if "审核" in label or "内容" in label:
        return {"assignType": "POSITION", "targetPositionCodes": ["CONTENT"]}
    if "部门负责人" in label or "主管" in label or "人事" in label:
        return {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]}
    return {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]}


def nodes_from_preview(rows: list[tuple[int, str, str, str]], sla_hours: int = 24) -> list[dict]:
    nodes: list[dict] = []
    for order, name, node_type, assignee in rows:
        nodes.append(
            {
                "nodeOrder": order,
                "nodeName": name,
                "nodeType": node_type,
                "assigneeRule": rule_from_preview(assignee),
                "assigneePreview": assignee,
                "slaHours": sla_hours,
            }
        )
    return nodes


def nodes_from_chain(names: list[str], sla_hours: int) -> list[dict]:
    """顿号分隔的节点链：首节点发起，中间与末节点为审批，处理人按部门负责人解析。"""
    nodes: list[dict] = []
    total = len(names)
    for index, name in enumerate(names, start=1):
        if index == 1:
            node_type = "TASK"
            rule = {"assignType": "USER", "targetIds": []}
            preview = "发起人"
        else:
            node_type = "APPROVE"
            if "无审批人" in name:
                rule = {"assignType": ""}
                preview = ""
            else:
                rule = {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]}
                preview = "岗位·部门负责人"
        nodes.append(
            {
                "nodeOrder": index,
                "nodeName": name,
                "nodeType": node_type,
                "assigneeRule": rule,
                "assigneePreview": preview,
                "slaHours": sla_hours,
            }
        )
    if total == 1:
        nodes[0]["nodeType"] = "APPROVE"
        if "无审批人" in nodes[0]["nodeName"]:
            nodes[0]["assigneeRule"] = {"assignType": ""}
            nodes[0]["assigneePreview"] = ""
        else:
            nodes[0]["assigneeRule"] = {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]}
            nodes[0]["assigneePreview"] = "岗位·部门负责人"
    return nodes


def normalize_nodes(raw: list | None) -> list[dict]:
    nodes: list[dict] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        rule = item.get("assigneeRule") if isinstance(item.get("assigneeRule"), dict) else {}
        nodes.append(
            {
                "nodeOrder": int(item.get("nodeOrder") or len(nodes) + 1),
                "nodeName": str(item.get("nodeName") or "").strip(),
                "nodeType": str(item.get("nodeType") or "APPROVE").strip().upper(),
                "assigneeRule": {
                    "assignType": str(rule.get("assignType") or "").strip().upper(),
                    "targetIds": [int(i) for i in (rule.get("targetIds") or []) if str(i).isdigit()],
                    "targetPositionCodes": [str(c) for c in (rule.get("targetPositionCodes") or []) if str(c).strip()],
                    "targetDeptId": int(rule["targetDeptId"]) if str(rule.get("targetDeptId") or "").isdigit() else None,
                },
                "assigneePreview": str(item.get("assigneePreview") or ""),
                "slaHours": int(item.get("slaHours") or 24),
                "conditionExpr": item.get("conditionExpr") or [],
                "formFields": item.get("formFields") or [],
                "parallelGroup": item.get("parallelGroup") or "",
            }
        )
    nodes.sort(key=lambda node: node["nodeOrder"])
    return nodes


def chain_text(nodes: list[dict]) -> str:
    ordered = sorted(nodes, key=lambda node: node["nodeOrder"])
    return "、".join(node["nodeName"] for node in ordered if node.get("nodeName"))


def validate_dag(nodes: list[dict]) -> str | None:
    """FLO-T-R1：起止齐全、序号连续、无环。"""
    if len(nodes) < 2:
        return "缺起止节点"
    orders = [int(node["nodeOrder"]) for node in nodes]
    if len(set(orders)) != len(orders):
        return "节点序号重复"
    if sorted(orders) != list(range(1, len(orders) + 1)):
        return "缺起止节点"
    if any(not str(node.get("nodeName") or "").strip() for node in nodes):
        return "节点名称必填"
    names = [str(node.get("nodeName") or "").strip() for node in nodes]
    if len(set(names)) != len(names):
        return "节点名称重复"
    if any(len(name) > 64 for name in names):
        return "节点名称不能超过 64 字"
    order_set = set(orders)
    adj: dict[int, list[int]] = {order: [] for order in orders}
    ordered = sorted(orders)
    for index, order in enumerate(ordered[:-1]):
        adj[order].append(ordered[index + 1])
    for node in nodes:
        for edge in node.get("conditionExpr") or []:
            if not isinstance(edge, dict):
                return "条件分支非法"
            target = int(edge.get("nextNodeOrder") or 0)
            if target not in order_set:
                return "条件分支指向不存在的节点"
            adj[int(node["nodeOrder"])].append(target)
    color = {order: 0 for order in orders}

    def cycle(order: int) -> bool:
        color[order] = 1
        for nxt in adj[order]:
            if color[nxt] == 1 or (color[nxt] == 0 and cycle(nxt)):
                return True
        color[order] = 2
        return False

    if any(cycle(order) for order in orders if color[order] == 0):
        return "存在环路"
    return None


def validate_rules(nodes: list[dict]) -> str | None:
    """审批/任务节点必须有合法处理人规则。抄送和定时可空。"""
    for node in nodes:
        node_type = node.get("nodeType")
        if node_type not in NODE_TYPES:
            return "节点类型非法"
        if node_type in {"CC", "TIMER"}:
            continue
        rule = node.get("assigneeRule") or {}
        kind = rule.get("assignType") or ""
        if kind not in ASSIGN_TYPES:
            return "处理人规则非法"
        if kind == "USER" and node_type == "APPROVE" and not rule.get("targetIds"):
            return "处理人规则非法"
        if kind == "POSITION" and not rule.get("targetPositionCodes"):
            return "处理人规则非法"
        if kind == "DEPT" and not rule.get("targetDeptId"):
            return "处理人规则非法"
    return None


def ends_moved(previous: list[dict], current: list[dict]) -> bool:
    """首尾节点不可移动。中间节点可以调序或插入。"""
    if not previous or not current:
        return False
    old = sorted(previous, key=lambda node: node["nodeOrder"])
    new = sorted(current, key=lambda node: node["nodeOrder"])
    return old[0]["nodeName"] != new[0]["nodeName"] or old[-1]["nodeName"] != new[-1]["nodeName"]


def opening_node(nodes: list[dict]) -> dict:
    """跳过「发起人自己填的」首任务，落到第一个需要别人处理的节点。"""
    ordered = sorted(nodes, key=lambda node: int(node["nodeOrder"]))
    for node in ordered:
        if node.get("nodeType") == "APPROVE":
            return node
        if node.get("nodeType") == "TASK":
            rule = node.get("assigneeRule") or {}
            if rule.get("assignType") == "USER" and not rule.get("targetIds"):
                continue
            return node
    return ordered[0]


def next_human_node(nodes: list[dict], after_order: int) -> dict | None:
    ordered = sorted(nodes, key=lambda node: int(node["nodeOrder"]))
    for node in ordered:
        if int(node["nodeOrder"]) <= after_order:
            continue
        if node.get("nodeType") in {"APPROVE", "TASK"}:
            return node
    return None


def next_chain_node(nodes: list[dict], after_order: int) -> dict | None:
    """绑定版本上的下一待办。抄送也要落任务；定时归档不占待办，链走完才办结。"""
    ordered = sorted(nodes, key=lambda node: int(node["nodeOrder"]))
    for node in ordered:
        if int(node["nodeOrder"]) <= int(after_order):
            continue
        if node.get("nodeType") in {"APPROVE", "TASK", "CC"}:
            return node
    return None


def node_by_order(nodes: list[dict], order: int) -> dict | None:
    for node in nodes:
        if int(node["nodeOrder"]) == int(order):
            return node
    return None


def diff_nodes(old: list[dict], new: list[dict]) -> list[dict]:
    old_by = {int(node["nodeOrder"]): node for node in old}
    new_by = {int(node["nodeOrder"]): node for node in new}
    changes: list[dict] = []
    for order in sorted(set(old_by) | set(new_by)):
        before = old_by.get(order)
        after = new_by.get(order)
        if before is None and after is not None:
            changes.append(
                {"changeType": "ADDED", "nodeOrder": order, "nodeName": after["nodeName"], "detail": {}}
            )
        elif after is None and before is not None:
            changes.append(
                {"changeType": "REMOVED", "nodeOrder": order, "nodeName": before["nodeName"], "detail": {}}
            )
        elif before != after and before is not None and after is not None:
            detail = {}
            for key in ("nodeName", "nodeType", "assigneeRule", "slaHours"):
                if before.get(key) != after.get(key):
                    detail[key] = {"oldValue": before.get(key), "newValue": after.get(key)}
            changes.append(
                {
                    "changeType": "MODIFIED",
                    "nodeOrder": order,
                    "nodeName": after["nodeName"],
                    "detail": detail,
                }
            )
    return changes
