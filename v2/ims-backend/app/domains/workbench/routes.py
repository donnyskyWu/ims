"""待办跳转登记。本批目标页都未交付，只返回占位路径。

告警的存库值沿用 B0a 的 ALERT（中文「告警」）。材料里的 ALARM 只作查询别名，不入库。
"""
from __future__ import annotations

# 单据已不存在。去处理时返回 1297，由前端再调用 complete。
MISSING_SOURCE = "DOC_GONE"

# source_type → 占位路径。delivered 留待后续批次改为 True。
ROUTE_TABLE = (
    {"source_type": "ACCT_APPLY", "type": "APPROVAL", "path": "/ims/account/apply", "delivered": False, "label": "账号领用审批"},
    {"source_type": "ACCT_RETURN", "type": "RETURN", "path": "/ims/account/return", "delivered": False, "label": "账号归还"},
    {"source_type": "CONTENT_REVIEW", "type": "REVIEW", "path": "/ims/content/review", "delivered": False, "label": "内容审核"},
    {"source_type": "WORK_TASK_CONFIRM", "type": "CONFIRM", "path": "/ims/content/task", "delivered": False, "label": "工作任务确认"},
    {"source_type": "CERT_EXPIRE", "type": "WARNING", "path": "/ims/cert/expire", "delivered": False, "label": "证件到期"},
    {"source_type": "LIVE_ALARM", "type": "ALERT", "path": "/ims/live/alarm", "delivered": False, "label": "直播告警"},
    {"source_type": "COLLECT_FAIL", "type": "ALERT", "path": "/ims/alert/realtime", "delivered": False, "label": "采集失败"},
    {"source_type": "LEARN_TASK", "type": "LEARN", "path": "/ims/train/learn", "delivered": False, "label": "学习任务"},
    {"source_type": "FLOW_TASK", "type": "APPROVAL", "path": "/ims/flow/mine", "delivered": False, "label": "流程任务"},
)

DEFAULT_BY_TYPE = {
    "APPROVAL": "/ims/account/apply",
    "RETURN": "/ims/account/return",
    "REVIEW": "/ims/content/review",
    "CONFIRM": "/ims/content/task",
    "WARNING": "/ims/cert/expire",
    "ALERT": "/ims/live/alarm",
    "LEARN": "/ims/train/learn",
}

MODULE_LABELS = {
    "account": "账号",
    "acct": "账号",
    "content": "内容",
    "cert": "证件",
    "live": "直播",
    "alert": "告警",
    "train": "培训",
    "flow": "流程",
    "system": "系统",
    "manual": "手工",
    "doc": "单据",
    "order": "订单",
}

_BY_SOURCE = {item["source_type"]: item for item in ROUTE_TABLE}


def normalize_type(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text in {"", "ALL"}:
        return None
    if text == "ALARM":
        return "ALERT"
    return text


def module_label(source_module: str | None) -> str:
    text = (source_module or "").strip()
    if not text:
        return "系统"
    if text in MODULE_LABELS:
        return MODULE_LABELS[text]
    lowered = text.lower()
    if lowered in MODULE_LABELS:
        return MODULE_LABELS[lowered]
    if all(ch.isascii() and (ch.isalnum() or ch in "_-") for ch in text):
        return "业务"
    return text


def path_for(source_type: str | None, todo_type: str | None) -> str:
    found = _BY_SOURCE.get(source_type or "")
    if found:
        return found["path"]
    if (source_type or "").startswith("FLOW"):
        return "/ims/flow/mine"
    return DEFAULT_BY_TYPE.get(todo_type or "", "/ims/workbench/soon")


def resolve_jump(source_type: str | None, todo_type: str | None, route: str | None) -> dict:
    if (source_type or "") == MISSING_SOURCE:
        return {"state": "missing", "path": "", "delivered": False, "message": "跳转目标单据不存在或已删除"}
    path = (route or "").strip() or path_for(source_type, todo_type)
    found = _BY_SOURCE.get(source_type or "")
    delivered = bool(found and found["delivered"])
    if delivered:
        return {"state": "navigate", "path": path, "delivered": True, "message": ""}
    return {"state": "placeholder", "path": path, "delivered": False, "message": "功能将在后续批次交付"}
