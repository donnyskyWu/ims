"""FLOW 契约接口。编号均为字符串，由响应层统一转换。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select

from app.core.clock import now_naive
from app.core.context import get_ctx
from app.core.errors import BizError
from app.core.pagination import Page, page_result
from app.core.serialize import parse_api_id
from app.db.repository import assert_dict_values
from app.db.session import get_session
from app.domains.flow.graph import assignee_preview, complete_human, normalize_nodes, open_entry, preview_graph, validate_publish
from app.domains.flow.model import (
    FlowCcRecord,
    FlowInstance,
    FlowTask,
    FlowTemplate,
    FlowTemplateVersion,
    FlowTrace,
)
from app.domains.flow.service import _close_task_todo, _trace, cancel as cancel_instance
from app.domains.message.service import send_notify
from app.domains.system.model import Dept, User, UserDept
from app.domains.todo.service import todo_create

log = logging.getLogger("ims.flow")
DOMAINS = {"ADMIN", "FINANCE", "BUSINESS", "COMMON"}
PRESET_BIZ = {"ACCT_BORROW", "REPORT_REVIEW", "TRAIN_APPROVAL"}
TARGET_RATE = 0.1


def create_template(body: dict) -> dict:
    _need("ims:flow:template:create", "ims:flow:manage")
    name = str(body.get("templateName") or "").strip()
    domain = str(body.get("businessDomain") or "").strip().upper()
    errors = []
    if not name or len(name) > 128:
        errors.append({"field": "templateName", "message": "请填写不超过 128 字的模板名称"})
    if domain not in DOMAINS:
        errors.append({"field": "businessDomain", "message": "请选择业务域"})
    if errors:
        raise BizError(1001, data={"fieldErrors": errors})
    _assert_domain(domain)
    nodes = normalize_nodes(body.get("nodes") or [], strict=False)
    session = get_session()
    code = str(body.get("bizType") or body.get("code") or _next_no("FT", FlowTemplate, "template_no")).strip()
    if session.scalar(select(FlowTemplate).where(FlowTemplate.code == code)):
        code = _next_no("FT", FlowTemplate, "template_no")
    row = FlowTemplate(
        code=code,
        name=name,
        biz_type=str(body.get("bizType") or ""),
        status="DRAFT",
        template_no=_next_no("FT", FlowTemplate, "template_no"),
        business_domain=domain,
        current_version=0,
        start_perm=str(body.get("startPerm") or "") or None,
    )
    session.add(row)
    session.flush()
    version = FlowTemplateVersion(template_id=row.id, version=1, nodes=nodes, status="DRAFT", change_desc=str(body.get("changeDesc") or ""))
    session.add(version)
    session.flush()
    return _template_view(row, version)


def update_template(ident: int, body: dict) -> dict:
    _need("ims:flow:template:create", "ims:flow:manage")
    row = _template(ident)
    _assert_domain(row.business_domain or "")
    draft = _draft_version(row)
    if draft is None:
        raise BizError(1133)
    if body.get("templateName"):
        name = str(body.get("templateName") or "").strip()
        if not name or len(name) > 128:
            raise BizError(1001, data={"fieldErrors": [{"field": "templateName", "message": "请填写不超过 128 字的模板名称"}]})
        row.name = name
    if body.get("businessDomain"):
        domain = str(body["businessDomain"]).upper()
        if domain not in DOMAINS:
            raise BizError(1001, data={"fieldErrors": [{"field": "businessDomain", "message": "请选择业务域"}]})
        _assert_domain(domain)
        row.business_domain = domain
    if body.get("bizType"):
        row.biz_type = str(body.get("bizType") or "")
    if "startPerm" in body:
        row.start_perm = str(body.get("startPerm") or "") or None
    if "nodes" in body:
        draft.nodes = normalize_nodes(body.get("nodes") or [], strict=False)
    if body.get("changeDesc"):
        draft.change_desc = str(body.get("changeDesc") or "")[:512]
    get_session().flush()
    return _template_view(row, draft)


def publish_template(ident: int) -> dict:
    _need("ims:flow:template:publish", "ims:flow:manage")
    row = _template(ident)
    _assert_domain(row.business_domain or "")
    draft = _draft_version(row)
    if draft is None:
        raise BizError(1133)
    nodes = normalize_nodes(draft.nodes or [], strict=True)
    validate_publish(nodes)
    session = get_session()
    previous = list(
        session.scalars(
            select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id, FlowTemplateVersion.status == "PUBLISHED")
        )
    )
    for item in previous:
        item.status = "ARCHIVED"
    draft.nodes = nodes
    draft.status = "PUBLISHED"
    draft.publish_time = now_naive()
    draft.published_by = _actor()
    row.status = "PUBLISHED"
    row.current_version = draft.version
    row.published_at = draft.publish_time
    session.flush()
    return _template_view(row, draft)


def disable_template(ident: int) -> dict:
    _need("ims:flow:template:publish", "ims:flow:manage")
    row = _template(ident)
    _assert_domain(row.business_domain or "")
    if row.status not in {"PUBLISHED", "ENABLED"}:
        raise BizError(1001, data={"fieldErrors": [{"field": "status", "message": "只有已发布的模板可以停用"}]})
    row.status = "DISABLED"
    get_session().flush()
    version = _current_version(row)
    return _template_view(row, version)


def delete_template(ident: int) -> dict:
    _need("ims:flow:template:delete")
    row = _template(ident)
    if row.status != "DRAFT":
        raise BizError(1133)
    row.deleted = row.id
    for version in get_session().scalars(select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id)):
        version.deleted = version.id
    get_session().flush()
    return {"id": row.id}


def revise_template(ident: int) -> dict:
    _need("ims:flow:template:create", "ims:flow:manage")
    row = _template(ident)
    _assert_domain(row.business_domain or "")
    draft = _draft_version(row)
    if draft is not None:
        return _template_view(row, draft)
    current = _current_version(row)
    if current is None:
        raise BizError(1504)
    session = get_session()
    nxt = int(session.scalar(select(func.max(FlowTemplateVersion.version)).where(FlowTemplateVersion.template_id == row.id)) or 0) + 1
    draft = FlowTemplateVersion(
        template_id=row.id,
        version=nxt,
        nodes=list(current.nodes or []),
        status="DRAFT",
        change_desc="",
    )
    session.add(draft)
    session.flush()
    return _template_view(row, draft)


def list_templates(page: Page, name: str | None, domain: str | None, status: str | None) -> dict:
    _need("ims:flow:template:query", "ims:flow:manage")
    session = get_session()
    stmt = select(FlowTemplate)
    if name:
        stmt = stmt.where(FlowTemplate.name.contains(name.strip()))
    if domain:
        stmt = stmt.where(FlowTemplate.business_domain == domain.strip().upper())
    if status:
        stmt = stmt.where(FlowTemplate.status == status.strip().upper())
    allowed = visible_domains()
    if allowed is not None:
        stmt = stmt.where(FlowTemplate.business_domain.in_(allowed))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(
        session.scalars(stmt.order_by(FlowTemplate.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size))
    )
    return page_result([_template_view(row, _current_version(row) or _latest_version(row)) for row in rows], int(total or 0), page)


def preview_template(ident: int, version_no: int | None = None) -> dict:
    _need("ims:flow:template:query", "ims:flow:manage")
    row = _template(ident)
    _assert_domain(row.business_domain or "")
    version = _version_no(row, version_no) if version_no else (_current_version(row) or _latest_version(row))
    if version is None:
        raise BizError(1504)
    graph = preview_graph(normalize_nodes(version.nodes or [], strict=False))
    graph["templateId"] = row.id
    graph["version"] = version.version
    return graph


def start_instance(body: dict) -> dict:
    template_id = parse_api_id(body.get("templateId"))
    if template_id is None:
        raise BizError(1001, data={"fieldErrors": [{"field": "templateId", "message": "请选择模板"}]})
    row = _template(int(template_id))
    _assert_can_start(row)
    if row.status == "DISABLED":
        raise BizError(1134, "模板已停用，不能发起新实例")
    if row.status not in {"PUBLISHED", "ENABLED"}:
        raise BizError(1134)
    version = _current_version(row)
    if version is None or version.status != "PUBLISHED":
        raise BizError(1134)
    latest = _latest_published(row)
    if latest is None or latest.id != version.id:
        raise BizError(1134)
    business_key = str(body.get("businessKey") or "").strip()
    session = get_session()
    if business_key:
        found = session.scalar(
            select(FlowInstance).where(FlowInstance.template_id == row.id, FlowInstance.business_key == business_key)
        )
        if found is not None:
            return _instance_view(found)
    nodes = normalize_nodes(version.nodes or [], strict=False)
    form = dict(body.get("formData") or {})
    _check_form(nodes, form)
    instance = FlowInstance(
        template_version_id=version.id,
        template_id=row.id,
        biz_type=row.biz_type or row.code,
        biz_id=int(body.get("bizId") or 0),
        initiator=_actor(),
        status="RUNNING",
        current_node="",
        instance_no=_next_no("FI", FlowInstance, "instance_no"),
        form_data=form,
        business_key=business_key or None,
        version_no=version.version,
    )
    assert_dict_values(instance)
    session.add(instance)
    session.flush()
    open_entry(instance, nodes)
    session.flush()
    return _instance_view(instance)


def my_todo(page: Page, domain: str | None) -> dict:
    return _task_page(page, mode="todo", domain=domain, task_status=None)


def my_initiated(page: Page, status: str | None) -> dict:
    session = get_session()
    actor = _actor()
    stmt = select(FlowInstance).where(FlowInstance.initiator == actor)
    if status:
        stmt = stmt.where(FlowInstance.status == status.strip().upper())
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(
        session.scalars(
            stmt.order_by(FlowInstance.id.desc()).offset((page.page_no - 1) * page.page_size).limit(page.page_size)
        )
    )
    return page_result([_instance_view(row) for row in rows], int(total or 0), page)


def my_handled(page: Page, task_status: str | None) -> dict:
    return _task_page(page, mode="handled", domain=None, task_status=task_status)


def handle_task(ident: int, body: dict) -> dict:
    action = str(body.get("action") or "").strip().upper()
    if action not in {"APPROVE", "REJECT"}:
        raise BizError(1001, data={"fieldErrors": [{"field": "action", "message": "处理动作不正确"}]})
    task, instance = _own_task(ident)
    if instance.status not in {"RUNNING", "TIMEOUT"}:
        raise BizError(1140)
    if (task.node_type or "") != "START" and int(task.assignee or 0) == int(instance.initiator):
        raise BizError(1008, "不能审核自己提交的单据")
    reject_to = body.get("rejectToNodeOrder")
    if reject_to not in (None, ""):
        reject_to = int(reject_to)
    else:
        reject_to = None
    patch = body.get("formDataPatch") if isinstance(body.get("formDataPatch"), dict) else None
    try:
        result = complete_human(instance, task, action, body.get("comment"), reject_to, patch)
    except BizError:
        raise
    waiting = bool(result.get("waitingParallel"))
    return {
        "taskId": task.id,
        "instanceNo": instance.instance_no,
        "newStatus": instance.status,
        "nextNodes": _pending_brief(instance),
        "isInstanceFinished": instance.status in {"APPROVED", "REJECTED", "CANCELLED"},
        "waitingParallel": waiting,
    }


def transfer_task(ident: int, body: dict) -> None:
    task, instance = _own_task(ident)
    if instance.status not in {"RUNNING", "TIMEOUT"}:
        raise BizError(1140)
    target = parse_api_id(body.get("toUserId"))
    reason = str(body.get("transferReason") or "").strip()
    errors = []
    if target is None or int(target) == int(task.assignee or 0):
        errors.append({"field": "toUserId", "message": "转交目标无效或与当前处理人相同"})
    if not reason or len(reason) > 512:
        errors.append({"field": "transferReason", "message": "请填写不超过 512 字的转交原因"})
    if errors:
        raise BizError(1138 if "toUserId" in {item["field"] for item in errors} and len(errors) == 1 else 1001, data={"fieldErrors": errors})
    user = get_session().get(User, int(target))
    if user is None or user.deleted or user.status != "ACTIVE":
        raise BizError(1138)
    task.status = "TRANSFERRED"
    task.action = "TRANSFER"
    task.comment = reason
    task.handled_at = now_naive()
    _close_task_todo(task, done=False)
    session = get_session()
    created = FlowTask(
        instance_id=instance.id,
        node=task.node,
        assignee=int(target),
        status="PENDING",
        due_time=task.due_time,
        overdue=task.overdue,
        urge_sent=0,
        node_order=task.node_order,
        node_name=task.node_name,
        node_type=task.node_type,
        sla_hours=task.sla_hours,
        remind_count=0,
        reassign_from=int(task.assignee or 0),
        parallel_group=task.parallel_group,
        warn_sent=0,
    )
    session.add(created)
    session.flush()
    todo_create(
        "FLOW_TASK",
        created.id,
        "APPROVAL",
        f"待审批 {created.node_name or created.node}",
        user_ids=[int(target)],
        route=f"/ims/flow/task?taskId={created.id}",
        source_module="FLOW",
        due_time=created.due_time,
    )
    _trace(instance, task, {"nodeKey": task.node, "nodeOrder": task.node_order, "nodeName": task.node_name or ""}, "TRANSFER", reason, actor_id=_actor())
    session.flush()
    return None


def instance_detail(instance_no: str) -> dict:
    instance = _by_no(instance_no)
    if not _can_view(instance):
        raise BizError(1504)
    data = _instance_view(instance)
    data["traceLog"] = _traces(instance)
    data["ccRecords"] = _cc(instance)
    return data


def board(domain: str | None, date_from: str | None, date_to: str | None) -> dict:
    _need("ims:flow:board:query", "ims:flow:manage")
    start, end = _range(date_from, date_to)
    rows = _scoped_instances(domain, start, end)
    running = [row for row in rows if row.status in {"RUNNING", "TIMEOUT"}]
    finished = [row for row in rows if row.status in {"APPROVED", "REJECTED", "CANCELLED"}]
    timeout_tasks = _timeout_tasks([row.id for row in rows])
    timeout_instances = {task.instance_id for task in timeout_tasks}
    by_template: dict[int, dict] = {}
    by_node: dict[str, dict] = {}
    for row in rows:
        bucket = by_template.setdefault(int(row.template_id or 0), {"templateName": _template_name(row), "running": 0, "timeout": 0, "durations": []})
        if row.status in {"RUNNING", "TIMEOUT"}:
            bucket["running"] += 1
        if row.id in timeout_instances:
            bucket["timeout"] += 1
        if row.finished_at and row.create_time:
            bucket["durations"].append((row.finished_at - row.create_time).total_seconds() / 3600)
    for task in timeout_tasks:
        name = task.node_name or task.node
        node = by_node.setdefault(name, {"nodeName": name, "pendingCount": 0, "timeoutCount": 0})
        if task.status == "PENDING":
            node["pendingCount"] += 1
            node["timeoutCount"] += 1
    recent = sorted(timeout_tasks, key=lambda item: item.due_time or item.create_time, reverse=True)[:8]
    return {
        "runningCount": len(running),
        "timeoutCount": len(timeout_instances),
        "finishedCount": len(finished),
        "timeoutRate": _rate(len(timeout_tasks), _executed_count([row.id for row in rows])),
        "byTemplate": [
            {
                "templateName": item["templateName"],
                "runningCount": item["running"],
                "timeoutCount": item["timeout"],
                "avgDurationHours": round(sum(item["durations"]) / len(item["durations"]), 2) if item["durations"] else 0,
            }
            for item in by_template.values()
        ],
        "byNode": list(by_node.values()),
        "recentTimeout": [_task_view(task) for task in recent],
    }


def revoke(instance_no: str) -> None:
    instance = _by_no(instance_no)
    cancel_instance(instance.id)
    return None


def version_list(template_id: int) -> list[dict]:
    _need("ims:flow:template:query", "ims:flow:manage")
    row = _template(template_id)
    _assert_domain(row.business_domain or "")
    rows = list(
        get_session().scalars(
            select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id).order_by(FlowTemplateVersion.version.desc())
        )
    )
    return [_version_brief(row, item) for item in rows]


def version_diff(template_id: int, from_version: int, to_version: int) -> dict:
    _need("ims:flow:template:query", "ims:flow:manage")
    row = _template(template_id)
    _assert_domain(row.business_domain or "")
    left = _must_version(row, from_version)
    right = _must_version(row, to_version)
    return _diff(normalize_nodes(left.nodes or [], strict=False), normalize_nodes(right.nodes or [], strict=False))


def version_snapshot(template_id: int, version_no: int) -> dict:
    _need("ims:flow:template:query", "ims:flow:manage")
    row = _template(template_id)
    _assert_domain(row.business_domain or "")
    version = _must_version(row, version_no)
    return _template_view(row, version)


def rollback(template_id: int, body: dict) -> dict:
    _need("ims:flow:version:rollback")
    row = _template(template_id)
    _assert_domain(row.business_domain or "")
    target_no = body.get("targetVersion")
    desc = str(body.get("changeDesc") or "").strip()
    if target_no in (None, "") or not desc:
        raise BizError(1001, data={"fieldErrors": [{"field": "changeDesc", "message": "请填写变更说明"}]})
    target = _must_version(row, int(target_no))
    if target.status == "DRAFT":
        raise BizError(1134)
    session = get_session()
    previous = list(
        session.scalars(
            select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id, FlowTemplateVersion.status == "PUBLISHED")
        )
    )
    for item in previous:
        item.status = "ARCHIVED"
        if item.version == int(row.current_version or 0):
            item.rolled_back = 1
    nxt = int(session.scalar(select(func.max(FlowTemplateVersion.version)).where(FlowTemplateVersion.template_id == row.id)) or 0) + 1
    created = FlowTemplateVersion(
        template_id=row.id,
        version=nxt,
        nodes=list(target.nodes or []),
        status="PUBLISHED",
        publish_time=now_naive(),
        published_by=_actor(),
        change_desc=desc[:512],
        rolled_back=0,
    )
    session.add(created)
    row.status = "PUBLISHED"
    row.current_version = nxt
    row.published_at = created.publish_time
    session.flush()
    return {"newVersion": nxt, "targetVersion": target.version}


def timeout_list(page: Page, domain: str | None, assignee: int | None, template_name: str | None) -> dict:
    rows = _visible_timeout(domain, assignee, template_name)
    rows.sort(key=lambda item: _timeout_minutes(item), reverse=True)
    total = len(rows)
    start = (page.page_no - 1) * page.page_size
    page_rows = rows[start : start + page.page_size]
    return page_result([_timeout_view(task) for task in page_rows], total, page)


def timeout_rate(stat_month: str | None) -> dict:
    _need("ims:flow:timeout:query", "ims:flow:board:query", "ims:flow:manage")
    month = _month(stat_month)
    start, end = _month_span(month)
    allowed = visible_domains()
    by_domain = []
    for name in ("ADMIN", "FINANCE", "BUSINESS", "COMMON"):
        if allowed is not None and name not in allowed:
            continue
        by_domain.append({"businessDomain": name, "timeoutRate": _month_rate(start, end, name)})
    trend = []
    cursor = month
    for _ in range(6):
        span = _month_span(cursor)
        trend.append({"statMonth": cursor.strftime("%Y-%m"), "timeoutRate": _month_rate(span[0], span[1], None)})
        cursor = (cursor.replace(day=1) - timedelta(days=1)).replace(day=1)
    trend.reverse()
    return {
        "monthlyTimeoutRate": _month_rate(start, end, None),
        "targetRate": TARGET_RATE,
        "byDomain": by_domain,
        "trend": trend,
    }


def timeout_distribution(stat_month: str | None, dimension: str) -> list[dict]:
    _need("ims:flow:timeout:query", "ims:flow:board:query", "ims:flow:manage")
    kind = (dimension or "").strip().upper()
    if kind not in {"TEMPLATE", "NODE", "DEPT", "PERSON"}:
        raise BizError(1001, data={"fieldErrors": [{"field": "dimension", "message": "请选择统计维度"}]})
    start, end = _month_span(_month(stat_month))
    tasks = _tasks_between(start, end)
    groups: dict[str, dict] = {}
    for task in tasks:
        key = _dimension_value(task, kind)
        bucket = groups.setdefault(key, {"dimensionValue": key, "timeoutCount": 0, "totalExecuted": 0, "minutes": []})
        if task.status != "CANCELLED":
            bucket["totalExecuted"] += 1
        if task.overdue:
            bucket["timeoutCount"] += 1
            bucket["minutes"].append(_timeout_minutes(task))
    result = []
    for bucket in groups.values():
        rate = _rate(bucket["timeoutCount"], bucket["totalExecuted"])
        result.append(
            {
                "dimensionValue": bucket["dimensionValue"],
                "timeoutCount": bucket["timeoutCount"],
                "totalExecuted": bucket["totalExecuted"],
                "timeoutRate": rate,
                "avgTimeoutMinutes": round(sum(bucket["minutes"]) / len(bucket["minutes"]), 1) if bucket["minutes"] else 0,
                "overTarget": rate > TARGET_RATE,
            }
        )
    result.sort(key=lambda item: item["timeoutRate"], reverse=True)
    return result


def urge(ident: int, body: dict) -> None:
    _need("ims:flow:timeout:urge", "ims:flow:manage")
    task = get_session().get(FlowTask, int(ident))
    if task is None or task.deleted or not task.overdue:
        raise BizError(1504)
    instance = get_session().get(FlowInstance, task.instance_id)
    if instance is None or not _in_domain(_template_domain(instance)):
        raise BizError(1504)
    text = str(body.get("urgeMessage") or "").strip() or "请尽快处理已超时的审批"
    if task.assignee:
        send_notify(int(task.assignee), "审批督办", text, "FLOW_URGE", f"urge:{task.id}:{int(task.remind_count or 0) + 1}")
    task.remind_count = int(task.remind_count or 0) + 1
    task.urge_sent = int(task.urge_sent or 0) + 1
    get_session().flush()
    return None


def todo_badge() -> dict:
    actor = _actor()
    total = get_session().scalar(
        select(func.count()).select_from(FlowTask).where(FlowTask.assignee == actor, FlowTask.status == "PENDING", FlowTask.node_type != "TIMER")
    )
    return {"count": int(total or 0)}


def visible_domains() -> set[str] | None:
    ctx = get_ctx()
    if ctx is None or ctx.system or ctx.user_id in (None, 0):
        return None
    from app.domains.system.model import Role, UserRole

    session = get_session()
    links = list(session.scalars(select(UserRole).where(UserRole.user_id == ctx.user_id, UserRole.manual_removed == 0)))
    domains: set[str] = set()
    unrestricted = False
    for link in links:
        role = session.get(Role, link.role_id)
        if role is None or role.deleted or role.status != "ENABLED":
            continue
        text = (role.flow_domain or "").strip()
        if text:
            domains.update(part.strip() for part in text.split(",") if part.strip())
        elif (role.data_scope or "") == "ALL":
            unrestricted = True
    if unrestricted or not domains:
        return None
    return domains


def _task_page(page: Page, mode: str, domain: str | None, task_status: str | None) -> dict:
    session = get_session()
    actor = _actor()
    stmt = select(FlowTask).where(FlowTask.assignee == actor)
    if mode == "todo":
        stmt = stmt.where(FlowTask.status == "PENDING", or_(FlowTask.node_type.is_(None), FlowTask.node_type != "TIMER"))
    else:
        stmt = stmt.where(FlowTask.status.in_(["APPROVED", "REJECTED", "TRANSFERRED", "DONE"]))
        if task_status:
            wanted = task_status.strip().upper()
            if wanted == "APPROVED":
                stmt = stmt.where(FlowTask.status.in_(["APPROVED", "DONE"]), or_(FlowTask.action.is_(None), FlowTask.action == "APPROVE"))
            else:
                stmt = stmt.where(or_(FlowTask.status == wanted, FlowTask.action == wanted))
    rows = list(session.scalars(stmt))
    if domain:
        rows = [task for task in rows if _template_domain(_instance_of(task)) == domain.strip().upper()]
    if mode == "todo":
        rows.sort(key=lambda item: (item.due_time is None, item.due_time or item.create_time, item.id))
    else:
        rows.sort(key=lambda item: item.handled_at or item.update_time, reverse=True)
    total = len(rows)
    start = (page.page_no - 1) * page.page_size
    views = []
    for task in rows[start : start + page.page_size]:
        view = _task_view(task)
        if mode == "handled":
            view["durationMinutes"] = _duration_minutes(task)
        views.append(view)
    return page_result(views, total, page)


def _template_view(row: FlowTemplate, version: FlowTemplateVersion | None) -> dict:
    nodes = normalize_nodes(version.nodes or [], strict=False) if version is not None else []
    return {
        "id": row.id,
        "templateNo": row.template_no or row.code,
        "templateName": row.name,
        "businessDomain": row.business_domain or "",
        "bizType": row.biz_type,
        "version": version.version if version is not None else int(row.current_version or 0),
        "status": row.status,
        "publishedAt": _fmt(row.published_at),
        "nodes": nodes,
        "nodeCount": len([node for node in nodes if node["nodeType"] not in {"START", "END"}]),
        "createdBy": row.creator,
        "createdByName": _user_name(row.creator),
        "createdAt": _fmt(row.create_time),
        "assigneePreview": [assignee_preview(node) for node in nodes],
    }


def _instance_view(instance: FlowInstance) -> dict:
    pending = list(
        get_session().scalars(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING"))
    )
    template = get_session().get(FlowTemplate, instance.template_id) if instance.template_id else None
    return {
        "id": instance.id,
        "instanceNo": instance.instance_no or str(instance.id),
        "templateId": instance.template_id,
        "templateName": template.name if template else "",
        "templateVersion": instance.version_no,
        "initiatorUserId": instance.initiator,
        "initiatorName": _user_name(instance.initiator),
        "formData": instance.form_data or {},
        "currentNodes": [_pending_node(task) for task in pending if (task.node_type or "APPROVE") != "TIMER"],
        "instanceStatus": instance.status,
        "status": instance.status,
        "currentNode": instance.current_node,
        "startedAt": _fmt(instance.create_time),
        "finishedAt": _fmt(instance.finished_at),
        "businessDomain": template.business_domain if template else "",
        "bizType": instance.biz_type,
        "canRevoke": instance.status in {"RUNNING", "TIMEOUT", "SUSPENDED"} and _can_revoke(instance),
    }


def _task_view(task: FlowTask) -> dict:
    instance = _instance_of(task)
    template = get_session().get(FlowTemplate, instance.template_id) if instance and instance.template_id else None
    level = _sla_level(task)
    return {
        "id": task.id,
        "instanceNo": instance.instance_no if instance else "",
        "instanceStatus": instance.status if instance else "",
        "templateName": template.name if template else "",
        "nodeOrder": task.node_order,
        "nodeName": task.node_name or task.node,
        "nodeType": task.node_type or "APPROVE",
        "assigneeUserId": task.assignee,
        "assigneeName": _user_name(task.assignee),
        "taskStatus": _task_status(task),
        "initiatorUserId": instance.initiator if instance else None,
        "initiatorName": _user_name(instance.initiator) if instance else "",
        "formData": instance.form_data if instance else {},
        "slaDeadline": _fmt(task.due_time),
        "isTimeout": level == "timeout",
        "slaLevel": level,
        "handledAt": _fmt(task.handled_at),
        "comment": task.comment,
        "startedAt": _fmt(task.create_time),
        "parallelGroup": task.parallel_group or "",
    }


def _timeout_view(task: FlowTask) -> dict:
    data = _task_view(task)
    data.update(
        {
            "slaHours": task.sla_hours or 0,
            "timeoutAt": _fmt(task.due_time),
            "timeoutDurationMinutes": _timeout_minutes(task),
            "remindCount": int(task.remind_count or task.urge_sent or 0),
            "isEscalated": bool(task.escalated) or _timeout_minutes(task) >= 24 * 60,
        }
    )
    return data


def _pending_node(task: FlowTask) -> dict:
    return {
        "nodeOrder": task.node_order,
        "nodeName": task.node_name or task.node,
        "assigneeUserId": task.assignee,
        "assigneeName": _user_name(task.assignee),
        "slaDeadline": _fmt(task.due_time),
        "taskId": task.id,
        "nodeType": task.node_type or "APPROVE",
    }


def _pending_brief(instance: FlowInstance) -> list[dict]:
    rows = list(get_session().scalars(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.status == "PENDING")))
    return [{"nodeOrder": task.node_order, "nodeName": task.node_name or task.node, "assigneeUserId": task.assignee} for task in rows]


def _traces(instance: FlowInstance) -> list[dict]:
    rows = list(get_session().scalars(select(FlowTrace).where(FlowTrace.instance_id == instance.id).order_by(FlowTrace.id.asc())))
    result = []
    for row in rows:
        result.append(
            {
                "nodeOrder": row.node_order,
                "nodeName": row.node_name or "",
                "assigneeUserId": row.actor_id,
                "assigneeName": _user_name(row.actor_id),
                "action": row.action,
                "comment": row.detail or row.comment or "",
                "actedAt": _fmt(row.create_time),
                "isTimeout": False,
            }
        )
    tasks = list(get_session().scalars(select(FlowTask).where(FlowTask.instance_id == instance.id, FlowTask.handled_at.is_not(None))))
    traced = {row.task_id for row in rows if row.task_id}
    for task in tasks:
        if task.id in traced:
            continue
        result.append(
            {
                "nodeOrder": task.node_order,
                "nodeName": task.node_name or task.node,
                "assigneeUserId": task.assignee,
                "assigneeName": _user_name(task.assignee),
                "action": task.action or task.status,
                "comment": task.comment or "",
                "actedAt": _fmt(task.handled_at),
                "isTimeout": bool(task.overdue),
            }
        )
    return result


def _cc(instance: FlowInstance) -> list[dict]:
    rows = list(get_session().scalars(select(FlowCcRecord).where(FlowCcRecord.instance_id == instance.id)))
    return [
        {"nodeOrder": row.node_order, "ccToUserId": row.user_id, "ccToName": _user_name(row.user_id), "notifiedAt": _fmt(row.notified_at)}
        for row in rows
    ]


def _version_brief(template: FlowTemplate, version: FlowTemplateVersion) -> dict:
    if version.rolled_back:
        label = "ROLLED_BACK"
    elif version.status == "PUBLISHED" and version.version == int(template.current_version or 0):
        label = "CURRENT"
    else:
        label = "HISTORICAL"
    return {
        "templateId": template.id,
        "version": version.version,
        "changeDesc": version.change_desc or "",
        "publishedBy": version.published_by,
        "publishedByName": _user_name(version.published_by),
        "publishedAt": _fmt(version.publish_time),
        "status": label,
        "versionStatus": version.status,
    }


def _diff(left: list[dict], right: list[dict]) -> dict:
    old = {node["nodeOrder"]: node for node in left}
    new = {node["nodeOrder"]: node for node in right}
    changes = []
    for order in sorted(set(old) | set(new)):
        if order not in old:
            changes.append({"changeType": "ADDED", "nodeOrder": order, "nodeName": new[order]["nodeName"], "detail": {}})
        elif order not in new:
            changes.append({"changeType": "REMOVED", "nodeOrder": order, "nodeName": old[order]["nodeName"], "detail": {}})
        else:
            detail = {}
            for key in ("nodeName", "nodeType", "slaHours", "parallelGroup", "assigneeRule", "formFields"):
                if old[order].get(key) != new[order].get(key):
                    detail[key] = {"oldValue": old[order].get(key), "newValue": new[order].get(key)}
            if detail:
                changes.append({"changeType": "MODIFIED", "nodeOrder": order, "nodeName": new[order]["nodeName"], "detail": detail})
    return {"nodeChanges": changes, "configChanges": []}


def _check_form(nodes: list[dict], form: dict) -> None:
    fields = []
    for node in nodes:
        if node["nodeType"] == "START":
            fields = list(node.get("formFields") or [])
            break
    if not fields and nodes:
        fields = list(nodes[0].get("formFields") or [])
    errors = []
    for field in fields:
        if field.get("required") and form.get(field.get("fieldKey")) in (None, ""):
            errors.append({"field": field.get("fieldKey") or "formData", "message": f"请填写{field.get('fieldLabel') or '必填项'}"})
    if errors:
        raise BizError(1001, data={"fieldErrors": errors})


def _own_task(ident: int) -> tuple[FlowTask, FlowInstance]:
    task = get_session().get(FlowTask, int(ident))
    if task is None or task.deleted or task.status != "PENDING":
        raise BizError(1135)
    if int(task.assignee or 0) != _actor():
        raise BizError(1135)
    instance = get_session().get(FlowInstance, task.instance_id)
    if instance is None or instance.deleted:
        raise BizError(1504)
    return task, instance


def _can_view(instance: FlowInstance) -> bool:
    actor = _actor()
    if int(instance.initiator) == actor:
        return True
    session = get_session()
    hit = session.scalar(select(FlowTask.id).where(FlowTask.instance_id == instance.id, FlowTask.assignee == actor))
    if hit:
        return True
    ctx = get_ctx()
    perms = set(ctx.perm_codes or []) if ctx else set()
    if not ({"ims:flow:board:query", "ims:flow:instance:manage", "ims:flow:manage"} & perms):
        return False
    return _in_domain(_template_domain(instance))


def _can_revoke(instance: FlowInstance) -> bool:
    ctx = get_ctx()
    perms = set(ctx.perm_codes or []) if ctx else set()
    return int(instance.initiator) == _actor() or bool({"ims:flow:instance:cancel", "ims:flow:cancel", "ims:flow:manage"} & perms)


def _assert_can_start(row: FlowTemplate) -> None:
    ctx = get_ctx()
    if ctx is None:
        raise BizError(1008)
    if ctx.system:
        return
    perms = set(ctx.perm_codes or [])
    if {"ims:flow:instance:start", "ims:flow:start", "ims:flow:manage"} & perms:
        _assert_domain(row.business_domain or "")
        return
    if row.start_perm and row.start_perm in perms:
        _assert_domain(row.business_domain or "")
        return
    raise BizError(1136)


def _assert_domain(domain: str) -> None:
    if not domain:
        return
    allowed = visible_domains()
    if allowed is not None and domain not in allowed:
        raise BizError(1504)


def _in_domain(domain: str) -> bool:
    allowed = visible_domains()
    return allowed is None or not domain or domain in allowed


def _need(*codes: str) -> None:
    ctx = get_ctx()
    if ctx is None:
        raise BizError(1008)
    if ctx.system:
        return
    if not (set(ctx.perm_codes or []) & set(codes)):
        raise BizError(1008)


def _actor() -> int:
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None:
        raise BizError(1008)
    return int(ctx.user_id)


def _template(ident: int) -> FlowTemplate:
    row = get_session().get(FlowTemplate, int(ident))
    if row is None or row.deleted:
        raise BizError(1504)
    return row


def _by_no(instance_no: str) -> FlowInstance:
    row = get_session().scalar(select(FlowInstance).where(FlowInstance.instance_no == instance_no))
    if row is None:
        if str(instance_no).isdigit():
            row = get_session().get(FlowInstance, int(instance_no))
    if row is None or row.deleted:
        raise BizError(1504)
    return row


def _draft_version(row: FlowTemplate) -> FlowTemplateVersion | None:
    return get_session().scalar(
        select(FlowTemplateVersion)
        .where(FlowTemplateVersion.template_id == row.id, FlowTemplateVersion.status == "DRAFT")
        .order_by(FlowTemplateVersion.version.desc())
    )


def _current_version(row: FlowTemplate) -> FlowTemplateVersion | None:
    if row.current_version:
        found = get_session().scalar(
            select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id, FlowTemplateVersion.version == row.current_version)
        )
        if found is not None:
            return found
    return _latest_published(row)


def _latest_published(row: FlowTemplate) -> FlowTemplateVersion | None:
    return get_session().scalar(
        select(FlowTemplateVersion)
        .where(FlowTemplateVersion.template_id == row.id, FlowTemplateVersion.status == "PUBLISHED")
        .order_by(FlowTemplateVersion.version.desc())
    )


def _latest_version(row: FlowTemplate) -> FlowTemplateVersion | None:
    return get_session().scalar(
        select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id).order_by(FlowTemplateVersion.version.desc())
    )


def _version_no(row: FlowTemplate, number: int) -> FlowTemplateVersion | None:
    return get_session().scalar(
        select(FlowTemplateVersion).where(FlowTemplateVersion.template_id == row.id, FlowTemplateVersion.version == int(number))
    )


def _must_version(row: FlowTemplate, number: int) -> FlowTemplateVersion:
    found = _version_no(row, number)
    if found is None:
        raise BizError(1134)
    return found


def _instance_of(task: FlowTask) -> FlowInstance | None:
    return get_session().get(FlowInstance, task.instance_id)


def _template_domain(instance: FlowInstance | None) -> str:
    if instance is None or not instance.template_id:
        return ""
    template = get_session().get(FlowTemplate, int(instance.template_id))
    return (template.business_domain or "") if template else ""


def _template_name(instance: FlowInstance) -> str:
    if not instance.template_id:
        return instance.biz_type or ""
    template = get_session().get(FlowTemplate, int(instance.template_id))
    return template.name if template else ""


def _scoped_instances(domain: str | None, start, end) -> list[FlowInstance]:
    session = get_session()
    stmt = select(FlowInstance).where(FlowInstance.create_time >= start, FlowInstance.create_time < end)
    rows = list(session.scalars(stmt))
    allowed = visible_domains()
    wanted = domain.strip().upper() if domain else ""
    kept = []
    for row in rows:
        item_domain = _template_domain(row)
        if wanted and item_domain != wanted:
            continue
        if allowed is not None and item_domain not in allowed:
            continue
        kept.append(row)
    return kept


def _timeout_tasks(instance_ids: list[int]) -> list[FlowTask]:
    if not instance_ids:
        return []
    return list(
        get_session().scalars(select(FlowTask).where(FlowTask.instance_id.in_(instance_ids), FlowTask.overdue == 1))
    )


def _executed_count(instance_ids: list[int]) -> int:
    if not instance_ids:
        return 0
    total = get_session().scalar(
        select(func.count()).select_from(FlowTask).where(FlowTask.instance_id.in_(instance_ids), FlowTask.status != "CANCELLED")
    )
    return int(total or 0)


def _visible_timeout(domain: str | None, assignee: int | None, template_name: str | None) -> list[FlowTask]:
    ctx = get_ctx()
    perms = set(ctx.perm_codes or []) if ctx else set()
    broad = bool({"ims:flow:timeout:query", "ims:flow:manage", "ims:flow:board:query"} & perms)
    session = get_session()
    stmt = select(FlowTask).where(FlowTask.overdue == 1, FlowTask.status == "PENDING")
    if not broad:
        stmt = stmt.where(FlowTask.assignee == _actor())
    elif assignee:
        stmt = stmt.where(FlowTask.assignee == int(assignee))
    rows = list(session.scalars(stmt))
    kept = []
    for task in rows:
        instance = _instance_of(task)
        item_domain = _template_domain(instance)
        if domain and item_domain != domain.strip().upper():
            continue
        if broad and not _in_domain(item_domain):
            continue
        if template_name and template_name.strip() not in (_template_name(instance) if instance else ""):
            continue
        kept.append(task)
    return kept


def _tasks_between(start, end) -> list[FlowTask]:
    rows = list(get_session().scalars(select(FlowTask).where(FlowTask.create_time >= start, FlowTask.create_time < end)))
    allowed = visible_domains()
    if allowed is None:
        return rows
    return [task for task in rows if _template_domain(_instance_of(task)) in allowed]


def _month_rate(start, end, domain: str | None) -> float:
    tasks = _tasks_between(start, end)
    if domain:
        tasks = [task for task in tasks if _template_domain(_instance_of(task)) == domain]
    executed = [task for task in tasks if task.status != "CANCELLED" and (task.node_type or "APPROVE") not in {"START", "END", "CC"}]
    timed = [task for task in executed if task.overdue]
    return _rate(len(timed), len(executed))


def _dimension_value(task: FlowTask, kind: str) -> str:
    instance = _instance_of(task)
    if kind == "TEMPLATE":
        return _template_name(instance) if instance else "未命名"
    if kind == "NODE":
        return task.node_name or task.node or "节点"
    if kind == "PERSON":
        return _user_name(task.assignee) or "未指定"
    if task.assignee:
        session = get_session()
        user = session.get(User, int(task.assignee))
        if user and user.main_dept_id:
            dept = session.get(Dept, int(user.main_dept_id))
            if dept:
                return dept.name
        link = session.scalar(select(UserDept).where(UserDept.user_id == int(task.assignee)))
        if link:
            dept = session.get(Dept, int(link.dept_id))
            if dept:
                return dept.name
    return "未分配部门"


def _range(date_from: str | None, date_to: str | None):
    end = _day(date_to) or now_naive()
    start = _day(date_from) or (end - timedelta(days=30))
    if start >= end:
        end = start + timedelta(days=1)
    return start, end + timedelta(days=1)


def _day(value: str | None):
    if not value:
        return None
    text = str(value).strip()
    if "," in text:
        text = text.split(",")[0]
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _month(value: str | None) -> datetime:
    if value:
        try:
            return datetime.strptime(str(value)[:7], "%Y-%m")
        except ValueError:
            pass
    current = now_naive()
    return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _month_span(month: datetime):
    start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _rate(part: int, whole: int) -> float:
    if not whole:
        return 0
    return round(part / whole, 4)


def _timeout_minutes(task: FlowTask) -> int:
    if not task.due_time:
        return 0
    end = task.handled_at or now_naive()
    seconds = (end - task.due_time).total_seconds()
    return max(0, int(seconds // 60))


def _duration_minutes(task: FlowTask) -> int:
    if not task.handled_at or not task.create_time:
        return 0
    return max(0, int((task.handled_at - task.create_time).total_seconds() // 60))


def _sla_level(task: FlowTask) -> str:
    if task.overdue or (task.status == "PENDING" and task.due_time and task.due_time < now_naive()):
        return "timeout"
    if task.status == "PENDING" and task.due_time and task.create_time:
        total = (task.due_time - task.create_time).total_seconds()
        if total > 0 and (now_naive() - task.create_time).total_seconds() >= total * 0.8:
            return "warn"
    return "ok"


def _task_status(task: FlowTask) -> str:
    if task.status == "DONE":
        return "REJECTED" if task.action in {"REJECT", "RETURN"} else "APPROVED"
    return task.status


def _user_name(user_id) -> str:
    if not user_id:
        return ""
    user = get_session().get(User, int(user_id))
    if user is None:
        return ""
    return user.nickname or user.username or ""


def _fmt(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _next_no(prefix: str, model, attr: str) -> str:
    day = now_naive().strftime("%Y%m%d")
    head = f"{prefix}{day}"
    column = getattr(model, attr)
    total = get_session().scalar(select(func.count()).select_from(model).where(column.like(f"{head}%")))
    return f"{head}{int(total or 0) + 1:04d}"
