"""工作流 FLOW-001/002 · 模板/实例列表 + 发起实例（P0 桩）。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.flow_graph import (
    PREVIEW_NODES,
    SLA_CHOICES,
    chain_text,
    diff_nodes,
    ends_moved,
    next_human_node,
    node_by_order,
    nodes_from_chain,
    nodes_from_preview,
    normalize_nodes,
    opening_node,
    validate_dag,
    validate_rules,
)
from app.models import (
    FlowInstance,
    FlowTask,
    FlowTemplate,
    FlowTemplateVersion,
    Role,
    User,
    UserRole,
    WorkMessage,
)
from app.scope import dept_ids_of, enabled_roles

router = APIRouter(prefix="/flow", tags=["flow"])

BJ = timezone(timedelta(hours=8))
DOMAINS = frozenset({"ADMIN", "FINANCE", "BUSINESS", "COMMON"})
TEMPLATE_STATUSES = frozenset({"DRAFT", "PUBLISHED", "DISABLED"})
INSTANCE_STATUSES = frozenset({"RUNNING", "APPROVED", "REJECTED", "CANCELLED", "TIMEOUT"})
TASK_STATUSES = frozenset({"PENDING", "APPROVED", "REJECTED", "TRANSFERRED"})
HANDLE_ACTIONS = frozenset({"APPROVE", "REJECT"})
DEFAULT_SLA_HOURS = 24
ESCALATION_HOURS = 24
BR115_TARGET_RATE = 0.1
STAT_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

DOMAIN_LABELS = {
    "ADMIN": "行政域",
    "FINANCE": "财务域",
    "BUSINESS": "业务域",
    "COMMON": "通用",
}
FIRST_NODE_BY_CODE = {
    "FL-LEAVE": "部门负责人审批",
    "FL-REIMB": "财务复核",
    "FL-CONTENT": "内容初审",
    "FL-LIVE": "直属领导审批",
}
DINGTALK_TIMEOUT_MARK = "__DINGTALK_TIMEOUT__"
WARN_SLA_RATIO = 0.8


class FlowInstanceStartBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    templateId: int = Field(..., gt=0)
    formData: dict[str, str | int | float | None] = Field(default_factory=dict)
    businessKey: str | None = None


class FlowTaskHandleBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: str
    comment: str = ""
    rejectToNodeOrder: int | None = None
    formDataPatch: dict[str, str | int | float | None] | None = None
    advance: bool = False


class FlowTaskTransferBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    toUserId: int | None = None
    transferReason: str = ""


class FlowTimeoutUrgeBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    urgeMessage: str | None = None
    fromInstance: bool = False


class FlowTemplateWriteBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    templateName: str = ""
    businessDomain: str = "COMMON"
    slaHours: int | None = None
    nodeChain: str | None = None
    nodes: list[dict] = Field(default_factory=list)
    status: str | None = None
    changeDesc: str = ""


class FlowTemplatePublishBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    templateName: str | None = None
    slaHours: int | None = None
    nodeChain: str | None = None
    nodes: list[dict] | None = None
    changeDesc: str = ""


class FlowVersionRollbackBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    targetVersion: int
    changeDesc: str = ""


STATUS_LABELS = {
    "DRAFT": "草稿",
    "PUBLISHED": "已发布",
    "DISABLED": "已停用",
    "RUNNING": "进行中",
    "APPROVED": "已完成",
    "REJECTED": "已驳回",
    "CANCELLED": "已撤销",
    "TIMEOUT": "已超时",
}


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def template_vo(row: FlowTemplate, names: dict[int, str]) -> dict:
    stored = normalize_nodes(row.nodes) if row.nodes else []
    return {
        "id": row.id,
        "templateCode": row.template_code,
        "templateName": row.template_name,
        "businessDomain": row.business_domain,
        "businessDomainLabel": DOMAIN_LABELS.get(row.business_domain, row.business_domain),
        "status": row.status,
        "statusLabel": STATUS_LABELS.get(row.status, row.status),
        "versionLabel": row.version_label,
        "version": int(row.version_no or template_version_no(row)),
        "nodeCount": row.node_count,
        "slaHours": int(row.sla_hours or DEFAULT_SLA_HOURS),
        "nodeChain": chain_text(stored) if stored else "",
        "startCount": int(row.start_count or 0),
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }


def template_version_no(row: FlowTemplate) -> int:
    m = re.search(r"(\d+)", row.version_label or "")
    return int(m.group(1)) if m else 1


def next_instance_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"FI{day}"
    taken = set(
        db.scalars(
            select(FlowInstance.instance_no).where(
                FlowInstance.tenant_id == tenant_id,
                FlowInstance.instance_no.like(f"{prefix}%"),
            )
        ).all()
    )
    n = 1
    while f"{prefix}{n:03d}" in taken and n < 10000:
        n += 1
    return f"{prefix}{n:03d}"


def instance_start_vo(
    row: FlowInstance,
    tpl: FlowTemplate,
    names: dict[int, str],
    *,
    assignee_user_id: int,
    node_order: int = 1,
) -> dict:
    title = row.title or str((row.form_data or {}).get("title") or "")
    return {
        "id": row.id,
        "instanceNo": row.instance_no,
        "templateId": row.template_id,
        "templateVersion": template_version_no(tpl),
        "initiatorUserId": row.initiator_user_id,
        "initiatorName": names.get(row.initiator_user_id, ""),
        "formData": row.form_data or {},
        "title": title,
        "currentNodes": [
            {
                "nodeOrder": node_order,
                "nodeName": row.current_node_name,
                "assigneeUserId": assignee_user_id,
                "assigneeName": names.get(assignee_user_id, ""),
            }
        ],
        "instanceStatus": row.instance_status,
        "startedAt": iso(row.started_at),
        "finishedAt": iso(row.finished_at),
    }


def sla_view(task: FlowTask, *, now: datetime | None = None) -> dict:
    """待办 SLA：80% 时限临期、超过截止为超时。时点与超时清单同一套 naive UTC。"""
    ref = _naive_dt(now or utcnow())
    started = _task_effective_start(task)
    deadline = started + timedelta(hours=DEFAULT_SLA_HOURS)
    elapsed = (ref - started).total_seconds()
    sla_seconds = DEFAULT_SLA_HOURS * 3600
    is_timeout = ref >= deadline
    if is_timeout:
        tone = "timeout"
    elif sla_seconds > 0 and elapsed >= sla_seconds * WARN_SLA_RATIO:
        tone = "warn"
    else:
        tone = "normal"
    return {
        "slaDeadline": iso(deadline),
        "isTimeout": is_timeout,
        "slaTone": tone,
    }


def task_vo(task: FlowTask, inst: FlowInstance, names: dict[int, str], *, now: datetime | None = None) -> dict:
    return {
        "id": task.id,
        "instanceNo": inst.instance_no,
        "instanceStatus": inst.instance_status,
        "templateName": inst.template_name,
        "nodeOrder": task.node_order,
        "nodeName": task.node_name,
        "nodeType": task.node_type,
        "assigneeUserId": task.assignee_user_id,
        "assigneeName": names.get(task.assignee_user_id, ""),
        "taskStatus": task.task_status,
        "initiatorUserId": inst.initiator_user_id,
        "initiatorName": names.get(inst.initiator_user_id, ""),
        "formData": inst.form_data or {},
        "handledAt": iso(task.handled_at),
        "comment": task.comment or "",
        "allowTransfer": bool(task.allow_transfer),
        "startedAt": iso(task.started_at),
        **sla_view(task, now=now),
    }


def timeout_task_vo(
    task: FlowTask,
    inst: FlowInstance,
    names: dict[int, str],
    *,
    sla_hours: int = DEFAULT_SLA_HOURS,
    now: datetime | None = None,
) -> dict:
    ref = now or utcnow()
    started = task.started_at or ref
    if started.tzinfo is not None:
        started = started.replace(tzinfo=None)
    deadline = started + timedelta(hours=sla_hours)
    timeout_minutes = max(0, int((ref - deadline).total_seconds() // 60))
    is_escalated = timeout_minutes >= ESCALATION_HOURS * 60
    base = task_vo(task, inst, names, now=ref)
    base.update(
        {
            "slaHours": sla_hours,
            "timeoutAt": iso(deadline),
            "timeoutDurationMinutes": timeout_minutes,
            "remindCount": task.remind_count or 0,
            "isEscalated": is_escalated,
        }
    )
    return base


def _naive_dt(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _task_effective_start(task: FlowTask) -> datetime:
    return _naive_dt(task.started_at or task.created_at or utcnow())


def _task_timeout_overflow_hours(task: FlowTask, *, eval_at: datetime) -> float:
    eval_at = _naive_dt(eval_at)
    deadline = _task_effective_start(task) + timedelta(hours=DEFAULT_SLA_HOURS)
    if eval_at <= deadline:
        return 0.0
    return (eval_at - deadline).total_seconds() / 3600.0


def _duration_bucket_for_overflow(overflow_hours: float) -> tuple[str, str]:
    if overflow_hours < 24:
        return "0_24H", "0-24h"
    if overflow_hours < 48:
        return "24_48H", "24-48h"
    return "48H_PLUS", "48h+"


def _task_is_timeout(task: FlowTask, *, eval_at: datetime) -> bool:
    eval_at = _naive_dt(eval_at)
    deadline = _task_effective_start(task) + timedelta(hours=DEFAULT_SLA_HOURS)
    if task.task_status == "PENDING":
        return eval_at >= deadline
    if task.handled_at is not None:
        return _naive_dt(task.handled_at) >= deadline
    return eval_at >= deadline


def _current_stat_month() -> str:
    return datetime.now(BJ).strftime("%Y-%m")


def _parse_stat_month(raw: str | None) -> str:
    if raw and STAT_MONTH_RE.fullmatch(raw.strip()):
        return raw.strip()
    return _current_stat_month()


def _month_range(stat_month: str) -> tuple[datetime, datetime]:
    year_s, month_s = stat_month.split("-", 1)
    year, month = int(year_s), int(month_s)
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _eval_at_for_month(stat_month: str, *, current_month: str) -> datetime:
    _, end = _month_range(stat_month)
    if stat_month == current_month:
        return _naive_dt(utcnow())
    return end - timedelta(seconds=1)


def _iter_trend_months(anchor_month: str, count: int = 6) -> list[str]:
    start, _ = _month_range(anchor_month)
    months: list[str] = []
    y, m = start.year, start.month
    for _ in range(count):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def _load_task_domain_rows(db: Session, tenant_id: int) -> list[tuple[FlowTask, str]]:
    rows = db.execute(
        select(FlowTask, FlowTemplate.business_domain)
        .join(FlowInstance, FlowInstance.id == FlowTask.instance_id)
        .join(FlowTemplate, FlowTemplate.id == FlowInstance.template_id)
        .where(
            FlowTask.deleted == 0,
            FlowTask.tenant_id == tenant_id,
            FlowInstance.deleted == 0,
            FlowTemplate.deleted == 0,
        )
    ).all()
    out: list[tuple[FlowTask, str]] = []
    for task, domain in rows:
        dom = (domain or "COMMON").strip().upper()
        if dom not in DOMAINS:
            dom = "COMMON"
        out.append((task, dom))
    return out


def _month_timeout_stats(
    rows: list[tuple[FlowTask, str]],
    stat_month: str,
    *,
    eval_at: datetime,
) -> tuple[int, int, int, dict[str, tuple[int, int]]]:
    month_start, month_end = _month_range(stat_month)
    in_month = [
        (task, dom)
        for task, dom in rows
        if month_start <= _task_effective_start(task) < month_end
    ]
    total = len(in_month)
    timeout_count = sum(1 for task, _ in in_month if _task_is_timeout(task, eval_at=eval_at))
    urge_count = sum((task.remind_count or 0) for task, _ in in_month if _task_is_timeout(task, eval_at=eval_at))
    by_dom: dict[str, tuple[int, int]] = {}
    for task, dom in in_month:
        t_out, t_all = by_dom.get(dom, (0, 0))
        t_all += 1
        if _task_is_timeout(task, eval_at=eval_at):
            t_out += 1
        by_dom[dom] = (t_out, t_all)
    return timeout_count, total, urge_count, by_dom


def ensure_pending_task(
    db: Session,
    inst: FlowInstance,
    tenant_id: int,
    assignee_user_id: int,
    node_name: str,
    *,
    node_order: int = 1,
    node_type: str = "APPROVE",
    sla_hours: int = DEFAULT_SLA_HOURS,
    allow_transfer: int = 1,
) -> FlowTask | None:
    if inst.instance_status != "RUNNING":
        return None
    existing = db.scalar(
        select(FlowTask).where(
            FlowTask.deleted == 0,
            FlowTask.tenant_id == tenant_id,
            FlowTask.instance_id == inst.id,
            FlowTask.task_status == "PENDING",
        )
    )
    if existing is not None:
        return existing
    now = utcnow()
    task = FlowTask(
        instance_id=inst.id,
        node_order=node_order,
        node_name=node_name or inst.current_node_name or "审批节点",
        node_type=node_type or "APPROVE",
        assignee_user_id=assignee_user_id,
        task_status="PENDING",
        sla_hours=sla_hours or DEFAULT_SLA_HOURS,
        allow_transfer=allow_transfer,
        tenant_id=tenant_id,
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()
    return task


def sync_seed_tasks(db: Session, tenant_id: int, default_assignee_id: int) -> None:
    """给还没有待办的运行中实例补一条。处理人按节点规则解析，解析不到再用发起人。

    default_assignee_id 只在发起人也为空时兜底，避免谁打开待办就把单子领走。
    """
    running = list(
        db.scalars(
            select(FlowInstance).where(
                FlowInstance.deleted == 0,
                FlowInstance.tenant_id == tenant_id,
                FlowInstance.instance_status == "RUNNING",
            )
        ).all()
    )
    for inst in running:
        assignee_id, node = _assignee_for_instance(db, inst)
        if assignee_id <= 0:
            assignee_id = inst.initiator_user_id or default_assignee_id
        node_name = (node or {}).get("nodeName") or inst.current_node_name
        node_order = int((node or {}).get("nodeOrder") or inst.current_node_order or 1)
        node_type = str((node or {}).get("nodeType") or "APPROVE")
        sla_hours = int((node or {}).get("slaHours") or DEFAULT_SLA_HOURS)
        ensure_pending_task(
            db,
            inst,
            tenant_id,
            assignee_id,
            node_name,
            node_order=node_order,
            node_type=node_type,
            sla_hours=sla_hours,
        )


def _backdate_demo_timeout_task(db: Session, tenant_id: int) -> None:
    """种子：首条 RUNNING 待办 started_at 回拨至 SLA 外，便于超时督办联调。"""
    row = db.execute(
        select(FlowTask, FlowInstance)
        .join(FlowInstance, FlowInstance.id == FlowTask.instance_id)
        .where(
            FlowTask.deleted == 0,
            FlowTask.tenant_id == tenant_id,
            FlowTask.task_status == "PENDING",
            FlowInstance.deleted == 0,
            FlowInstance.instance_status == "RUNNING",
        )
        .order_by(FlowTask.id.asc())
        .limit(1)
    ).first()
    if row is None:
        return
    task, inst = row
    stale = utcnow() - timedelta(hours=DEFAULT_SLA_HOURS + 2)
    if task.started_at and task.started_at.replace(tzinfo=None) <= stale:
        return
    task.started_at = stale
    task.updated_at = utcnow()
    inst.started_at = stale
    inst.updated_at = utcnow()
    db.flush()


def _mark_demo_warn_task(db: Session, tenant_id: int) -> None:
    """种子实例里未超时的那条拨到 SLA 80% 之后，待办可看到临期黄标。不改账号流转单。"""
    warn_at = utcnow() - timedelta(hours=int(DEFAULT_SLA_HOURS * WARN_SLA_RATIO) + 1)
    timeout_line = utcnow() - timedelta(hours=DEFAULT_SLA_HOURS)
    for title in ("差旅报销 · 上海出差", "张三 · 年假 3 天"):
        row = db.execute(
            select(FlowTask, FlowInstance)
            .join(FlowInstance, FlowInstance.id == FlowTask.instance_id)
            .where(
                FlowTask.deleted == 0,
                FlowTask.tenant_id == tenant_id,
                FlowTask.task_status == "PENDING",
                FlowInstance.deleted == 0,
                FlowInstance.instance_status == "RUNNING",
                FlowInstance.title == title,
            )
            .limit(1)
        ).first()
        if row is None:
            continue
        task, inst = row
        started = _naive_dt(task.started_at or utcnow())
        if started <= timeout_line:
            continue
        if started <= _naive_dt(warn_at):
            return
        task.started_at = warn_at
        task.updated_at = utcnow()
        inst.started_at = warn_at
        inst.updated_at = utcnow()
        db.flush()
        return


def _pending_by_instance(db: Session, tenant_id: int, instance_ids: list[int]) -> dict[int, FlowTask]:
    if not instance_ids:
        return {}
    tasks = list(
        db.scalars(
            select(FlowTask).where(
                FlowTask.deleted == 0,
                FlowTask.tenant_id == tenant_id,
                FlowTask.instance_id.in_(instance_ids),
                FlowTask.task_status == "PENDING",
            )
        ).all()
    )
    found: dict[int, FlowTask] = {}
    for task in tasks:
        found.setdefault(task.instance_id, task)
    return found


def instance_vo(row: FlowInstance, names: dict[int, str], pending: FlowTask | None = None) -> dict:
    assignee_id = pending.assignee_user_id if pending is not None else 0
    return {
        "id": row.id,
        "instanceNo": row.instance_no,
        "templateId": row.template_id,
        "templateName": row.template_name,
        "title": row.title,
        "instanceStatus": row.instance_status,
        "instanceStatusLabel": STATUS_LABELS.get(row.instance_status, row.instance_status),
        "currentNodeName": row.current_node_name,
        "currentNodeOrder": row.current_node_order or (pending.node_order if pending is not None else 0),
        "currentAssigneeUserId": assignee_id,
        "currentAssigneeName": names.get(assignee_id, "") if assignee_id else "",
        "pendingTaskId": pending.id if pending is not None else 0,
        "initiatorName": names.get(row.initiator_user_id, ""),
        "startedAt": iso(row.started_at),
        "finishedAt": iso(row.finished_at),
    }


def _actor_is_r1(db: Session, actor: User) -> bool:
    if actor.username == "admin":
        return True
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == actor.id)).all())
    if not role_ids:
        return False
    roles = db.scalars(
        select(Role).where(Role.id.in_(role_ids), Role.deleted == 0, Role.status == "ENABLED")
    ).all()
    return any(role.role_key == "sys:admin" for role in roles)


def _role_is_leader(role: Role) -> bool:
    key = (role.role_key or "").lower()
    name = role.role_name or ""
    return key in {"r4", "dept_leader", "dept:leader"} or key.endswith(":r4") or "部门负责人" in name or "运营总监" in name


def _role_matches_position(role: Role, codes: list[str]) -> bool:
    key = (role.role_key or "").lower()
    name = role.role_name or ""
    folded = {code.upper() for code in codes}
    if folded & {"DEPT_LEADER", "R4", "部门负责人"} and _role_is_leader(role):
        return True
    if folded & {"FINANCE", "R3", "财务"} and (key in {"r3", "acct:r3"} or key.endswith(":r3") or "财务" in name):
        return True
    if folded & {"CONTENT", "R8", "内容审核"} and (key.endswith(":r8") or key == "r8" or "审核" in name):
        return True
    return False


def _users_in_tenant(db: Session, tenant_id: int) -> list[User]:
    return list(
        db.scalars(
            select(User).where(User.deleted == 0, User.status == "ENABLED", User.tenant_id == tenant_id)
        ).all()
    )


def _share_dept(db: Session, left: User, right: User) -> bool:
    return bool(set(dept_ids_of(db, left)) & set(dept_ids_of(db, right)))


def _pick_among(db: Session, initiator: User, candidates: list[User]) -> User | None:
    others = [user for user in candidates if user.id != initiator.id]
    if not others:
        return None
    same = [user for user in others if _share_dept(db, initiator, user)]
    return (same or others)[0]


def _leaders(db: Session, tenant_id: int) -> list[User]:
    found: list[User] = []
    for user in _users_in_tenant(db, tenant_id):
        if any(_role_is_leader(role) for role in enabled_roles(db, user)):
            found.append(user)
    return found


def graph_nodes(db: Session, tpl: FlowTemplate | None, *, version_no: int | None = None) -> list[dict]:
    if tpl is None:
        return []
    if version_no is not None:
        snap = db.scalar(
            select(FlowTemplateVersion).where(
                FlowTemplateVersion.deleted == 0,
                FlowTemplateVersion.tenant_id == tpl.tenant_id,
                FlowTemplateVersion.template_id == tpl.id,
                FlowTemplateVersion.version_no == version_no,
            )
        )
        if snap is not None and snap.nodes:
            return normalize_nodes(snap.nodes)
    if tpl.nodes:
        return normalize_nodes(tpl.nodes)
    preset = PREVIEW_NODES.get(tpl.template_code)
    if preset:
        return nodes_from_preview(preset, int(tpl.sla_hours or DEFAULT_SLA_HOURS))
    return []


def resolve_assignee(db: Session, initiator: User, node: dict) -> tuple[int | None, str | None]:
    """按节点规则解析处理人。

    R1 发起时仍落到 R1，避免单管理员环境里锁后审批和闭环待办被转走。
    其他发起人：能解析到部门负责人/指定人时不把审批待办派回自己。
    INITIATOR_SUPERIOR 解析失败返回 1132，不静默派给发起人。
    """
    rule = node.get("assigneeRule") or {}
    kind = str(rule.get("assignType") or "")
    node_type = str(node.get("nodeType") or "APPROVE")
    if _actor_is_r1(db, initiator) and kind != "USER":
        return initiator.id, None
    if kind == "USER":
        ids = [int(item) for item in (rule.get("targetIds") or [])]
        if not ids:
            return initiator.id, None
        target = db.get(User, ids[0])
        if target is None or target.deleted or target.status != "ENABLED":
            return None, "处理人规则非法"
        if node_type == "APPROVE" and target.id == initiator.id:
            return None, "发起人不能审批自己的单据"
        return target.id, None
    if kind == "INITIATOR_SUPERIOR":
        picked = _pick_among(db, initiator, _leaders(db, initiator.tenant_id or 0))
        if picked is None:
            return None, "处理人规则非法"
        return picked.id, None
    if kind == "DEPT":
        dept_id = rule.get("targetDeptId")
        if not dept_id:
            return None, "处理人规则非法"
        members = [
            user
            for user in _users_in_tenant(db, initiator.tenant_id or 0)
            if dept_id in dept_ids_of(db, user) and user.id != initiator.id
        ]
        leaders = [user for user in members if any(_role_is_leader(role) for role in enabled_roles(db, user))]
        picked = (leaders or members)[:1]
        if not picked:
            return None, "处理人规则非法"
        return picked[0].id, None
    codes = [str(code) for code in (rule.get("targetPositionCodes") or [])]
    pool = [
        user
        for user in _users_in_tenant(db, initiator.tenant_id or 0)
        if any(_role_matches_position(role, codes) for role in enabled_roles(db, user))
    ]
    if not pool and (not codes or "DEPT_LEADER" in {code.upper() for code in codes}):
        pool = _leaders(db, initiator.tenant_id or 0)
    picked = _pick_among(db, initiator, pool)
    if picked is not None:
        return picked.id, None
    if node_type == "APPROVE":
        return initiator.id, None
    return initiator.id, None


def _assignee_for_instance(db: Session, inst: FlowInstance) -> tuple[int, dict | None]:
    initiator = db.get(User, inst.initiator_user_id)
    tpl = db.get(FlowTemplate, inst.template_id)
    nodes = graph_nodes(db, tpl, version_no=inst.template_version or None)
    node = None
    if nodes:
        if inst.current_node_name:
            node = next((item for item in nodes if item["nodeName"] == inst.current_node_name), None)
        if node is None and inst.current_node_order:
            node = node_by_order(nodes, inst.current_node_order)
        if node is None:
            node = opening_node(nodes)
    if initiator is None or node is None:
        return inst.initiator_user_id or 0, node
    assignee_id, _err = resolve_assignee(db, initiator, node)
    return assignee_id or inst.initiator_user_id or 0, node


def _form_empty(form: dict | None) -> bool:
    if not form:
        return True
    return not any(value is not None and str(value).strip() for value in form.values())


def _edge_copy(db: Session, actor: User, inst: FlowInstance) -> str:
    status = inst.instance_status
    if status == "RUNNING":
        if actor.id == inst.initiator_user_id or _actor_is_r1(db, actor):
            return "进行中。撤销后已完成节点留痕，实例进入已撤销。"
        return "进行中。仅发起人或管理员可撤销。"
    if status == "CANCELLED":
        return "已撤销，已完成节点留痕，不可再次撤销。"
    if status == "REJECTED":
        return "实例已驳回结束，不可撤销。"
    if status == "TIMEOUT":
        return "实例已超时结束，不可撤销。"
    return "实例已结束不可撤销。"


def _can_revoke(db: Session, actor: User, inst: FlowInstance) -> bool:
    return inst.instance_status == "RUNNING" and (
        actor.id == inst.initiator_user_id or _actor_is_r1(db, actor)
    )


def _load_instance(db: Session, tenant_id: int, instance_no: str) -> FlowInstance | None:
    no = (instance_no or "").strip()
    if not no:
        return None
    return db.scalar(
        select(FlowInstance).where(
            FlowInstance.deleted == 0,
            FlowInstance.tenant_id == tenant_id,
            FlowInstance.instance_no == no,
        )
    )


def instance_detail_vo(db: Session, inst: FlowInstance, actor: User, names: dict[int, str]) -> dict:
    tpl = db.get(FlowTemplate, inst.template_id)
    tasks = list(
        db.scalars(
            select(FlowTask)
            .where(
                FlowTask.deleted == 0,
                FlowTask.tenant_id == inst.tenant_id,
                FlowTask.instance_id == inst.id,
            )
            .order_by(FlowTask.id.asc())
        ).all()
    )
    extra_ids = [task.assignee_user_id for task in tasks]
    extra_ids.append(inst.initiator_user_id)
    if any(uid not in names for uid in extra_ids):
        names = {**names, **user_names(db, extra_ids)}
    trace: list[dict] = []
    for task in tasks:
        trace.append(
            {
                "nodeOrder": task.node_order,
                "nodeName": task.node_name,
                "assigneeUserId": task.assignee_user_id,
                "assigneeName": names.get(task.assignee_user_id, ""),
                "action": task.task_status,
                "comment": task.comment or "",
                "actedAt": iso(task.handled_at or task.started_at),
                "isTimeout": False,
            }
        )
    if inst.instance_status == "CANCELLED":
        trace.append(
            {
                "nodeOrder": 0,
                "nodeName": inst.current_node_name or "撤销",
                "assigneeUserId": inst.initiator_user_id,
                "assigneeName": names.get(inst.initiator_user_id, ""),
                "action": "CANCELLED",
                "comment": "已完成节点留痕，实例进入已撤销",
                "actedAt": iso(inst.finished_at),
                "isTimeout": False,
            }
        )
    pending = next((task for task in tasks if task.task_status == "PENDING"), None)
    if inst.instance_status == "RUNNING" and pending is not None:
        current_nodes = [
            {
                "nodeOrder": pending.node_order,
                "nodeName": pending.node_name,
                "assigneeUserId": pending.assignee_user_id,
                "assigneeName": names.get(pending.assignee_user_id, ""),
            }
        ]
    else:
        current_nodes = []
    return {
        **instance_vo(inst, names, pending),
        "templateVersion": template_version_no(tpl) if tpl is not None and not tpl.deleted else 1,
        "initiatorUserId": inst.initiator_user_id,
        "formData": inst.form_data or {},
        "formEmpty": _form_empty(inst.form_data),
        "currentNodes": current_nodes,
        "canRevoke": _can_revoke(db, actor, inst),
        "edgeCopy": _edge_copy(db, actor, inst),
        "traceLog": trace,
        "ccRecords": [],
    }


def seed_flow(db: Session, tenant_id: int, creator_id: int) -> None:
    """补齐默认模板和示例实例。已有账号流转等业务实例时仍要补，不能因表非空整段跳过。"""
    now = utcnow()
    templates = [
        ("FL-LEAVE", "请假审批", "ADMIN", "PUBLISHED", "v1.2", 4),
        ("FL-REIMB", "费用报销", "FINANCE", "PUBLISHED", "v2.0", 5),
        ("FL-CONTENT", "内容审核", "BUSINESS", "PUBLISHED", "v1.0", 3),
        ("FL-LIVE", "开播审批", "BUSINESS", "DRAFT", "v0.9", 2),
    ]
    existing_codes = set(
        db.scalars(
            select(FlowTemplate.template_code).where(
                FlowTemplate.deleted == 0, FlowTemplate.tenant_id == tenant_id
            )
        ).all()
    )
    missing = [item for item in templates if item[0] not in existing_codes]
    if missing:
        db.add_all(
            [
                FlowTemplate(
                    template_code=code,
                    template_name=name,
                    business_domain=domain,
                    status=status,
                    version_label=ver,
                    node_count=nodes,
                    creator_id=creator_id,
                    tenant_id=tenant_id,
                    created_at=now,
                    updated_at=now,
                )
                for code, name, domain, status, ver, nodes in missing
            ]
        )
        db.flush()

    tpls = list(
        db.scalars(
            select(FlowTemplate).where(FlowTemplate.deleted == 0, FlowTemplate.tenant_id == tenant_id)
        ).all()
    )
    by_code = {t.template_code: t for t in tpls}
    day = datetime.now(BJ).strftime("%Y%m%d")
    seeds = [
        (f"FI{day}001", "FL-LEAVE", "张三 · 年假 3 天", "RUNNING", "部门负责人审批", 26),
        (f"FI{day}002", "FL-REIMB", "差旅报销 · 上海出差", "RUNNING", "财务复核", 2),
        (f"FI{day}003", "FL-CONTENT", "短视频《赛事集锦》发布", "APPROVED", "—", 0),
    ]
    existing_titles = set(
        db.scalars(
            select(FlowInstance.title).where(FlowInstance.deleted == 0, FlowInstance.tenant_id == tenant_id)
        ).all()
    )
    # 含软删：uk_flow_instance_no 不区分 deleted，固定 001/002/003 可能已被闭环实例占用。
    taken_nos = set(
        db.scalars(
            select(FlowInstance.instance_no).where(
                FlowInstance.tenant_id == tenant_id,
                FlowInstance.instance_no.like(f"FI{day}%"),
            )
        ).all()
    )
    added = False
    for preferred, code, title, st, node, age_hours in seeds:
        if title in existing_titles:
            continue
        tpl = by_code.get(code)
        if tpl is None:
            continue
        no = preferred
        if no in taken_nos:
            n = 1
            while f"FI{day}{n:03d}" in taken_nos and n < 10000:
                n += 1
            no = f"FI{day}{n:03d}"
        taken_nos.add(no)
        finished = now if st == "APPROVED" else None
        started = now - timedelta(hours=age_hours) if age_hours else now
        db.add(
            FlowInstance(
                instance_no=no,
                template_id=tpl.id,
                template_name=tpl.template_name,
                title=title,
                instance_status=st,
                current_node_name=node,
                initiator_user_id=creator_id,
                tenant_id=tenant_id,
                started_at=started,
                finished_at=finished,
                created_at=now,
                updated_at=now,
            )
        )
        added = True
    if added:
        db.flush()
    sync_seed_tasks(db, tenant_id, creator_id)
    _backdate_demo_timeout_task(db, tenant_id)
    _mark_demo_warn_task(db, tenant_id)


@router.get("/template/list")
def flow_template_list(
    templateName: str | None = None,
    businessDomain: str | None = None,
    status: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    q = select(FlowTemplate).where(FlowTemplate.deleted == 0, FlowTemplate.tenant_id == tenant_id)
    if templateName:
        kw = f"%{templateName.strip()}%"
        q = q.where((FlowTemplate.template_name.like(kw)) | (FlowTemplate.template_code.like(kw)))
    if businessDomain and businessDomain.strip().upper() in DOMAINS:
        q = q.where(FlowTemplate.business_domain == businessDomain.strip().upper())
    if status and status.strip().upper() in TEMPLATE_STATUSES:
        q = q.where(FlowTemplate.status == status.strip().upper())
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(FlowTemplate.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([template_vo(r, names) for r in rows], total, page_no, size)


def preview_nodes_for(tpl: FlowTemplate) -> list[tuple[int, str, str, str]]:
    preset = PREVIEW_NODES.get(tpl.template_code)
    if preset:
        return preset
    count = max(int(tpl.node_count or 1), 1)
    first = FIRST_NODE_BY_CODE.get(tpl.template_code, "审批节点")
    nodes: list[tuple[int, str, str, str]] = []
    for order in range(1, count + 1):
        if order == 1 and count > 1:
            nodes.append((order, "发起", "TASK", "发起人"))
        elif order == count:
            nodes.append((order, first, "APPROVE", "本地桩·处理人"))
        else:
            nodes.append((order, f"节点{order}", "APPROVE", "本地桩·处理人"))
    return nodes


def template_preview_vo(tpl: FlowTemplate) -> dict:
    if tpl.nodes:
        stored = normalize_nodes(tpl.nodes)
        nodes = [
            (
                int(node["nodeOrder"]),
                str(node["nodeName"]),
                str(node["nodeType"]),
                str(node.get("assigneePreview") or "处理人"),
            )
            for node in stored
        ]
    else:
        nodes = preview_nodes_for(tpl)
    return {
        "templateId": tpl.id,
        "templateCode": tpl.template_code,
        "templateName": tpl.template_name,
        "status": tpl.status,
        "statusLabel": STATUS_LABELS.get(tpl.status, tpl.status),
        "canStart": tpl.status == "PUBLISHED",
        "graphType": "SERIAL",
        "nodes": [
            {
                "nodeOrder": order,
                "nodeName": name,
                "nodeType": node_type,
                "assigneePreview": assignee,
            }
            for order, name, node_type, assignee in nodes
        ],
        "edges": [
            {"fromNodeOrder": nodes[i][0], "toNodeOrder": nodes[i + 1][0]}
            for i in range(len(nodes) - 1)
        ],
    }


@router.get("/template/{template_id}/preview")
def flow_template_preview(
    template_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """流程图预览桩：草稿与已发布都可看，不启动设计器。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = db.get(FlowTemplate, template_id)
    if tpl is None or tpl.deleted or tpl.tenant_id != tenant_id:
        return fail(1001, "模板不存在")
    return ok(template_preview_vo(tpl))


@router.get("/instance/list")
def flow_instance_list(
    keyword: str | None = None,
    instanceStatus: str | None = None,
    templateId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    q = select(FlowInstance).where(FlowInstance.deleted == 0, FlowInstance.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where(
            (FlowInstance.title.like(kw))
            | (FlowInstance.instance_no.like(kw))
            | (FlowInstance.template_name.like(kw))
        )
    if instanceStatus and instanceStatus.strip().upper() in INSTANCE_STATUSES:
        q = q.where(FlowInstance.instance_status == instanceStatus.strip().upper())
    if templateId:
        q = q.where(FlowInstance.template_id == templateId)
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(FlowInstance.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    pending_by_inst = _pending_by_instance(db, tenant_id, [row.id for row in rows])
    user_ids = [row.initiator_user_id for row in rows]
    user_ids.extend(task.assignee_user_id for task in pending_by_inst.values())
    names = user_names(db, user_ids)
    return paged(
        [instance_vo(row, names, pending_by_inst.get(row.id)) for row in rows],
        total,
        page_no,
        size,
    )


@router.get("/instance/board")
def flow_instance_board(
    businessDomain: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """看板：按当前节点分列进行中实例，供流转/完成。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    q = select(FlowInstance).where(FlowInstance.deleted == 0, FlowInstance.tenant_id == tenant_id)
    if businessDomain and businessDomain.strip().upper() in DOMAINS:
        q = q.join(FlowTemplate, FlowTemplate.id == FlowInstance.template_id).where(
            FlowTemplate.business_domain == businessDomain.strip().upper()
        )
    rows = list(db.scalars(q.order_by(FlowInstance.id.desc())).all())
    now = utcnow()
    running = [row for row in rows if row.instance_status == "RUNNING"]
    finished = [row for row in rows if row.instance_status == "APPROVED"]
    pending = _pending_by_instance(db, tenant_id, [row.id for row in running])
    timeout_count = 0
    for task in pending.values():
        started = task.started_at or now
        if started.tzinfo is not None:
            started = started.replace(tzinfo=None)
        if now.replace(tzinfo=None) >= started + timedelta(hours=task.sla_hours or DEFAULT_SLA_HOURS):
            timeout_count += 1
    names = user_names(
        db,
        [row.initiator_user_id for row in running] + [task.assignee_user_id for task in pending.values()],
    )
    columns: dict[str, list[dict]] = {}
    by_node: dict[str, dict] = {}
    for row in running:
        task = pending.get(row.id)
        name = row.current_node_name or "未分派"
        card = instance_vo(row, names, task)
        card["canAdvance"] = bool(task is not None and next_human_node(graph_nodes(db, db.get(FlowTemplate, row.template_id), version_no=row.template_version or None), task.node_order))
        columns.setdefault(name, []).append(card)
        bucket = by_node.setdefault(name, {"nodeName": name, "pendingCount": 0, "timeoutCount": 0})
        bucket["pendingCount"] += 1
        if task is not None:
            started = task.started_at or now
            if started.tzinfo is not None:
                started = started.replace(tzinfo=None)
            if now.replace(tzinfo=None) >= started + timedelta(hours=task.sla_hours or DEFAULT_SLA_HOURS):
                bucket["timeoutCount"] += 1
    by_template: dict[str, dict] = {}
    for row in rows:
        item = by_template.setdefault(
            row.template_name,
            {"templateName": row.template_name, "runningCount": 0, "timeoutCount": 0, "avgDurationHours": 0},
        )
        if row.instance_status == "RUNNING":
            item["runningCount"] += 1
    return ok(
        {
            "runningCount": len(running),
            "timeoutCount": timeout_count,
            "finishedCount": len(finished),
            "byTemplate": list(by_template.values()),
            "byNode": list(by_node.values()),
            "columns": [{"nodeName": name, "cards": cards} for name, cards in columns.items()],
            "recentTimeout": [],
        }
    )


@router.get("/instance/{instance_no}")
def flow_instance_detail(
    instance_no: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """实例详情：表单、轨迹、抄送空态，以及撤销边界文案。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    inst = _load_instance(db, tenant_id, instance_no)
    if inst is None:
        return fail(1001, "流程实例不存在")
    names = user_names(db, [inst.initiator_user_id, actor.id])
    return ok(instance_detail_vo(db, inst, actor, names))


@router.put("/instance/{instance_no}/revoke")
def flow_instance_revoke(
    instance_no: str,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """撤销进行中实例。已完成节点留痕，待办不再出现在我的待办。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    inst = _load_instance(db, tenant_id, instance_no)
    if inst is None:
        return fail(1001, "流程实例不存在")
    if inst.instance_status != "RUNNING":
        return fail(1140, "实例已结束不可撤销")
    if actor.id != inst.initiator_user_id and not _actor_is_r1(db, actor):
        return fail(1139, "非发起人不可撤销")
    now = utcnow()
    inst.instance_status = "CANCELLED"
    inst.finished_at = now
    inst.updated_at = now
    pending = list(
        db.scalars(
            select(FlowTask).where(
                FlowTask.deleted == 0,
                FlowTask.tenant_id == tenant_id,
                FlowTask.instance_id == inst.id,
                FlowTask.task_status == "PENDING",
            )
        ).all()
    )
    for task in pending:
        if not (task.comment or "").strip():
            task.comment = "未办结，随实例撤销关闭"
        task.updated_at = now
    db.flush()
    return ok(None)


@router.post("/instance")
def flow_instance_start(
    body: FlowInstanceStartBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """发起流程实例。审批节点按模板规则解析处理人，不把待办派回非管理员发起人。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    biz_key = (body.businessKey or "").strip() or None
    if biz_key and len(biz_key) > 64:
        return fail(1001, "businessKey 不能超过 64 字")
    if biz_key:
        existing = db.scalar(
            select(FlowInstance).where(
                FlowInstance.deleted == 0,
                FlowInstance.tenant_id == tenant_id,
                FlowInstance.business_key == biz_key,
            )
        )
        if existing is not None:
            tpl = db.get(FlowTemplate, existing.template_id)
            if tpl is None:
                return fail(1001, "模板不存在")
            assignee_id, node = _assignee_for_instance(db, existing)
            task = ensure_pending_task(
                db,
                existing,
                tenant_id,
                assignee_id or existing.initiator_user_id,
                (node or {}).get("nodeName") or existing.current_node_name,
                node_order=int((node or {}).get("nodeOrder") or existing.current_node_order or 1),
                node_type=str((node or {}).get("nodeType") or "APPROVE"),
            )
            holder = task.assignee_user_id if task is not None else assignee_id or actor.id
            names = user_names(db, [existing.initiator_user_id, holder])
            replay = instance_start_vo(
                existing,
                tpl,
                names,
                assignee_user_id=holder,
                node_order=task.node_order if task is not None else 1,
            )
            replay["idempotent"] = True
            return ok(replay)

    tpl = db.get(FlowTemplate, body.templateId)
    if tpl is None or tpl.deleted or tpl.tenant_id != tenant_id:
        return fail(1001, "模板不存在")
    if tpl.status != "PUBLISHED":
        return fail(1134, "仅已发布模板可发起新实例")

    form = dict(body.formData or {})
    title = str(form.get("title") or form.get("subject") or "").strip()
    if not title:
        return fail(1001, "formData.title 必填")
    if len(title) > 256:
        return fail(1001, "标题不能超过 256 字")

    nodes = graph_nodes(db, tpl)
    node = opening_node(nodes) if nodes else None
    if node is None:
        first_name = FIRST_NODE_BY_CODE.get(tpl.template_code, "审批节点")
        node = {
            "nodeOrder": 1,
            "nodeName": first_name,
            "nodeType": "APPROVE",
            "assigneeRule": {"assignType": "POSITION", "targetPositionCodes": ["DEPT_LEADER"]},
            "slaHours": DEFAULT_SLA_HOURS,
        }
    assignee_id, rule_err = resolve_assignee(db, actor, node)
    if rule_err and str((node.get("assigneeRule") or {}).get("assignType")) == "INITIATOR_SUPERIOR":
        return fail(1132, "处理人规则非法，发起人上级无法解析")
    if assignee_id is None:
        return fail(1132, rule_err or "处理人规则非法")
    if node.get("nodeType") == "APPROVE" and assignee_id == actor.id and not _actor_is_r1(db, actor):
        leaders = _leaders(db, tenant_id)
        if any(user.id != actor.id for user in leaders):
            return fail(1132, "审批节点不能派给发起人")
    now = utcnow()
    row = FlowInstance(
        instance_no=next_instance_no(db, tenant_id),
        template_id=tpl.id,
        template_name=tpl.template_name,
        title=title,
        business_key=biz_key,
        form_data=form,
        instance_status="RUNNING",
        current_node_name=str(node.get("nodeName") or "审批节点"),
        current_node_order=int(node.get("nodeOrder") or 1),
        template_version=template_version_no(tpl),
        initiator_user_id=actor.id,
        tenant_id=tenant_id,
        started_at=now,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    tpl.start_count = int(tpl.start_count or 0) + 1
    task = ensure_pending_task(
        db,
        row,
        tenant_id,
        assignee_id,
        row.current_node_name,
        node_order=row.current_node_order,
        node_type=str(node.get("nodeType") or "APPROVE"),
        sla_hours=int(node.get("slaHours") or DEFAULT_SLA_HOURS),
    )
    holder = task.assignee_user_id if task is not None else assignee_id
    names = user_names(db, [actor.id, holder])
    return ok(instance_start_vo(row, tpl, names, assignee_user_id=holder, node_order=row.current_node_order))


@router.get("/task/my-todo")
def flow_task_my_todo(
    businessDomain: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    sync_seed_tasks(db, tenant_id, actor.id)
    q = (
        select(FlowTask, FlowInstance)
        .join(FlowInstance, FlowInstance.id == FlowTask.instance_id)
        .where(
            FlowTask.deleted == 0,
            FlowTask.tenant_id == tenant_id,
            FlowTask.task_status == "PENDING",
            FlowInstance.deleted == 0,
            FlowInstance.instance_status == "RUNNING",
        )
    )
    # 我的待办只列派给自己的。管理员在实例列表和详情看当前处理人，避免把别人的确认单领进自己的待办。
    q = q.where(FlowTask.assignee_user_id == actor.id)
    if businessDomain and businessDomain.strip().upper() in DOMAINS:
        q = q.join(FlowTemplate, FlowTemplate.id == FlowInstance.template_id).where(
            FlowTemplate.business_domain == businessDomain.strip().upper()
        )
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(FlowTask.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.execute(stmt.offset((page_no - 1) * size).limit(size)).all())
    user_ids: list[int] = []
    for task, inst in rows:
        user_ids.extend([task.assignee_user_id, inst.initiator_user_id])
    names = user_names(db, user_ids)
    return paged([task_vo(task, inst, names) for task, inst in rows], total, page_no, size)


@router.put("/task/{task_id}/handle")
def flow_task_handle(
    task_id: int,
    body: FlowTaskHandleBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    action = (body.action or "").strip().upper()
    if action not in HANDLE_ACTIONS:
        return fail(1001, "action 须为 APPROVE 或 REJECT")
    task = db.get(FlowTask, task_id)
    if task is None or task.deleted or task.tenant_id != tenant_id:
        return fail(1001, "任务不存在")
    if task.task_status != "PENDING":
        return fail(1001, "任务已处理")
    if task.assignee_user_id != actor.id:
        return fail(1135, "非该任务处理人")
    inst = db.get(FlowInstance, task.instance_id)
    if inst is None or inst.deleted or inst.tenant_id != tenant_id:
        return fail(1001, "流程实例不存在")
    if inst.instance_status != "RUNNING":
        return fail(1001, "实例已终态，不可处理")

    tpl = db.get(FlowTemplate, inst.template_id)
    nodes = graph_nodes(db, tpl, version_no=inst.template_version or None) if tpl is not None else []
    max_order = max((int(node["nodeOrder"]) for node in nodes), default=1)
    if not nodes and tpl is not None and not tpl.deleted:
        preview_orders = [order for order, *_rest in preview_nodes_for(tpl)]
        if preview_orders:
            max_order = max(preview_orders)
    reject_order: int | None = None
    if action == "REJECT":
        if body.rejectToNodeOrder is None:
            reject_order = 1
        elif body.rejectToNodeOrder < 1 or body.rejectToNodeOrder > max_order:
            return fail(1001, "退回目标节点无效")
        else:
            reject_order = body.rejectToNodeOrder

    now = utcnow()
    comment = (body.comment or "").strip()
    if len(comment) > 512:
        return fail(1001, "审批意见不能超过 512 字")
    if action == "REJECT" and not comment:
        return fail(1001, "退回意见必填")

    if body.formDataPatch:
        merged = dict(inst.form_data or {})
        merged.update(body.formDataPatch)
        inst.form_data = merged

    task.comment = comment
    task.handled_at = now
    task.updated_at = now
    next_nodes: list[dict] = []

    if action == "APPROVE" and body.advance:
        nxt = next_human_node(nodes, task.node_order) if nodes else None
        if nxt is not None:
            initiator = db.get(User, inst.initiator_user_id) or actor
            assignee_id, rule_err = resolve_assignee(db, initiator, nxt)
            if assignee_id is None:
                return fail(1132, rule_err or "处理人规则非法")
            task.task_status = "APPROVED"
            db.flush()
            inst.current_node_name = str(nxt.get("nodeName") or "审批节点")
            inst.current_node_order = int(nxt.get("nodeOrder") or task.node_order + 1)
            inst.updated_at = now
            ensure_pending_task(
                db,
                inst,
                tenant_id,
                assignee_id,
                inst.current_node_name,
                node_order=inst.current_node_order,
                node_type=str(nxt.get("nodeType") or "APPROVE"),
                sla_hours=int(nxt.get("slaHours") or DEFAULT_SLA_HOURS),
            )
            new_status = "RUNNING"
            is_finished = False
            next_nodes = [
                {
                    "nodeOrder": inst.current_node_order,
                    "nodeName": inst.current_node_name,
                    "assigneeUserId": assignee_id,
                }
            ]
        else:
            task.task_status = "APPROVED"
            inst.instance_status = "APPROVED"
            inst.current_node_name = "—"
            inst.finished_at = now
            inst.updated_at = now
            new_status = "APPROVED"
            is_finished = True
    elif action == "APPROVE":
        task.task_status = "APPROVED"
        inst.instance_status = "APPROVED"
        inst.current_node_name = "—"
        inst.finished_at = now
        inst.updated_at = now
        new_status = "APPROVED"
        is_finished = True
    else:
        target = node_by_order(nodes, reject_order or 1) if nodes else None
        node_name = str((target or {}).get("nodeName") or "发起申请")
        task.task_status = "REJECTED"
        inst.instance_status = "RUNNING"
        inst.current_node_name = node_name
        inst.current_node_order = reject_order or 1
        inst.finished_at = None
        inst.updated_at = now
        db.flush()
        ensure_pending_task(
            db,
            inst,
            tenant_id,
            inst.initiator_user_id,
            node_name,
            node_order=inst.current_node_order,
            node_type="TASK",
            sla_hours=int((target or {}).get("slaHours") or DEFAULT_SLA_HOURS),
        )
        _notify(
            db,
            user_id=inst.initiator_user_id,
            tenant_id=tenant_id,
            title="流程已退回",
            content=f"{inst.instance_no} 已退回：{comment}"[:512],
            ref_id=inst.id,
        )
        new_status = "REJECTED"
        is_finished = False
        next_nodes = [
            {
                "nodeOrder": inst.current_node_order,
                "nodeName": node_name,
                "assigneeUserId": inst.initiator_user_id,
            }
        ]

    db.flush()
    return ok(
        {
            "taskId": task.id,
            "instanceNo": inst.instance_no,
            "newStatus": new_status,
            "nextNodes": next_nodes,
            "isInstanceFinished": is_finished,
            "rejectToNodeOrder": reject_order,
            "commentHint": "",
        }
    )


@router.put("/task/{task_id}/transfer")
def flow_task_transfer(
    task_id: int,
    body: FlowTaskTransferBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """转交一次一跳。目标不能是自己，同一节点不可再次转交。"""
    tenant_id = tenant_of(actor)
    task = db.get(FlowTask, task_id)
    if task is None or task.deleted or task.tenant_id != tenant_id:
        return fail(1001, "任务不存在")
    if task.task_status != "PENDING":
        return fail(1001, "任务已处理")
    if task.assignee_user_id != actor.id:
        return fail(1135, "非该任务处理人")
    inst = db.get(FlowInstance, task.instance_id)
    if inst is None or inst.deleted or inst.tenant_id != tenant_id:
        return fail(1001, "流程实例不存在")
    if inst.instance_status != "RUNNING":
        return fail(1001, "实例已终态，不可转交")
    if not task.allow_transfer:
        return fail(1138, "同一节点只能转交一次")
    reason = (body.transferReason or "").strip()
    if not reason:
        return fail(1001, "转交原因必填")
    if len(reason) > 512:
        return fail(1001, "转交原因不能超过 512 字")
    target_id = int(body.toUserId or 0)
    if target_id <= 0 or target_id == actor.id:
        return fail(1138, "转交目标人无效或与当前处理人相同")
    target = db.get(User, target_id)
    if (
        target is None
        or target.deleted
        or target.status != "ENABLED"
        or (target.tenant_id or 0) != tenant_id
    ):
        return fail(1138, "转交目标人无效或与当前处理人相同")
    now = utcnow()
    task.task_status = "TRANSFERRED"
    task.comment = reason
    task.handled_at = now
    task.updated_at = now
    db.flush()
    ensure_pending_task(
        db,
        inst,
        tenant_id,
        target.id,
        task.node_name,
        node_order=task.node_order,
        node_type=task.node_type,
        sla_hours=task.sla_hours or DEFAULT_SLA_HOURS,
        allow_transfer=0,
    )
    _notify(
        db,
        user_id=target.id,
        tenant_id=tenant_id,
        title="流程已转交",
        content=f"{inst.instance_no} 转交给你：{reason}"[:512],
        ref_id=inst.id,
    )
    db.flush()
    return ok(None)


@router.get("/timeout/rate")
def flow_timeout_rate(
    statMonth: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """BR-115 月度超时率桩：超时节点数 / 当月执行节点总数。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    stat_month = _parse_stat_month(statMonth)
    current_month = _current_stat_month()
    rows = _load_task_domain_rows(db, tenant_id)
    eval_at = _eval_at_for_month(stat_month, current_month=current_month)
    timeout_count, total_executed, urge_count, by_dom = _month_timeout_stats(
        rows, stat_month, eval_at=eval_at
    )
    monthly_rate = round(timeout_count / total_executed, 4) if total_executed else 0.0
    by_domain = [
        {
            "businessDomain": dom,
            "timeoutRate": round(out / tot, 4) if tot else 0.0,
        }
        for dom, (out, tot) in sorted(by_dom.items(), key=lambda x: x[0])
    ]
    trend: list[dict] = []
    for m in _iter_trend_months(stat_month, 6):
        m_eval = _eval_at_for_month(m, current_month=current_month)
        out, tot, _, _ = _month_timeout_stats(rows, m, eval_at=m_eval)
        trend.append(
            {
                "statMonth": m,
                "timeoutRate": round(out / tot, 4) if tot else 0.0,
            }
        )
    return ok(
        {
            "monthlyTimeoutRate": monthly_rate,
            "targetRate": BR115_TARGET_RATE,
            "byDomain": by_domain,
            "trend": trend,
            "timeoutCount": timeout_count,
            "totalExecuted": total_executed,
            "urgeCount": urge_count,
            "statMonth": stat_month,
        }
    )


@router.get("/timeout/distribution")
def flow_timeout_distribution(
    statMonth: str | None = None,
    groupBy: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """FLOW-004 / BR-115 超时分布桩：当月超时节点按时长分桶，或按 domain/template 聚合。"""
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    stat_month = _parse_stat_month(statMonth)
    current_month = _current_stat_month()
    eval_at = _eval_at_for_month(stat_month, current_month=current_month)
    rows = _load_task_domain_rows(db, tenant_id)
    month_start, month_end = _month_range(stat_month)
    in_month = [
        (task, dom)
        for task, dom in rows
        if month_start <= _task_effective_start(task) < month_end
    ]
    timed_out = [(task, dom) for task, dom in in_month if _task_is_timeout(task, eval_at=eval_at)]

    bucket_defs = [
        ("0_24H", "0-24h"),
        ("24_48H", "24-48h"),
        ("48H_PLUS", "48h+"),
    ]
    bucket_counts = {k: 0 for k, _ in bucket_defs}
    for task, _ in timed_out:
        key, _ = _duration_bucket_for_overflow(_task_timeout_overflow_hours(task, eval_at=eval_at))
        bucket_counts[key] = bucket_counts.get(key, 0) + 1
    duration_buckets = [
        {"bucketKey": k, "bucketLabel": label, "count": bucket_counts.get(k, 0)}
        for k, label in bucket_defs
    ]

    by_domain_map: dict[str, int] = {}
    for task, dom in timed_out:
        by_domain_map[dom] = by_domain_map.get(dom, 0) + 1
    by_domain = [
        {
            "businessDomain": dom,
            "businessDomainLabel": DOMAIN_LABELS.get(dom, dom),
            "timeoutCount": cnt,
        }
        for dom, cnt in sorted(by_domain_map.items(), key=lambda x: x[0])
    ]

    inst_ids = {task.instance_id for task, _ in timed_out}
    inst_by_id: dict[int, FlowInstance] = {}
    if inst_ids:
        for inst in db.scalars(
            select(FlowInstance).where(
                FlowInstance.id.in_(inst_ids),
                FlowInstance.deleted == 0,
            )
        ).all():
            inst_by_id[inst.id] = inst
    by_template_map: dict[str, int] = {}
    for task, _ in timed_out:
        inst = inst_by_id.get(task.instance_id)
        name = (inst.template_name if inst else "") or "—"
        by_template_map[name] = by_template_map.get(name, 0) + 1
    by_template = [
        {"templateName": name, "timeoutCount": cnt}
        for name, cnt in sorted(by_template_map.items(), key=lambda x: (-x[1], x[0]))
    ]

    mode = (groupBy or "duration").strip().lower()
    if mode not in ("duration", "domain", "template"):
        mode = "duration"

    return ok(
        {
            "statMonth": stat_month,
            "groupBy": mode,
            "slaHours": DEFAULT_SLA_HOURS,
            "timeoutTotal": len(timed_out),
            "durationBuckets": duration_buckets,
            "byDomain": by_domain,
            "byTemplate": by_template,
        }
    )


@router.get("/timeout/list")
def flow_timeout_list(
    businessDomain: str | None = None,
    assigneeUserId: int | None = None,
    assigneeName: str | None = None,
    templateName: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    now = utcnow()
    page_no, size = page_args(pageNo, pageSize)
    assignee_text = (assigneeName or "").strip()
    assignee_ids: list[int] | None = None
    if assignee_text:
        like = f"%{assignee_text}%"
        assignee_ids = list(
            db.scalars(
                select(User.id).where(
                    User.deleted == 0,
                    User.tenant_id == tenant_id,
                    or_(User.nickname.like(like), User.username.like(like)),
                )
            ).all()
        )
        if not assignee_ids:
            return paged([], 0, page_no, size)
    q = (
        select(FlowTask, FlowInstance)
        .join(FlowInstance, FlowInstance.id == FlowTask.instance_id)
        .where(
            FlowTask.deleted == 0,
            FlowTask.tenant_id == tenant_id,
            FlowTask.task_status == "PENDING",
            FlowInstance.deleted == 0,
            FlowInstance.instance_status == "RUNNING",
        )
    )
    if businessDomain and businessDomain.strip().upper() in DOMAINS:
        q = q.join(FlowTemplate, FlowTemplate.id == FlowInstance.template_id).where(
            FlowTemplate.business_domain == businessDomain.strip().upper()
        )
    if assigneeUserId is not None and assigneeUserId > 0:
        q = q.where(FlowTask.assignee_user_id == assigneeUserId)
    if assignee_ids is not None:
        q = q.where(FlowTask.assignee_user_id.in_(assignee_ids))
    if templateName and templateName.strip():
        kw = f"%{templateName.strip()}%"
        q = q.where(FlowInstance.template_name.like(kw))
    rows = list(db.execute(q.order_by(FlowTask.started_at.asc())).all())
    timed_out: list[tuple[FlowTask, FlowInstance]] = []
    for task, inst in rows:
        started = task.started_at or now
        if started.tzinfo is not None:
            started = started.replace(tzinfo=None)
        if now.replace(tzinfo=None) >= started + timedelta(hours=DEFAULT_SLA_HOURS):
            timed_out.append((task, inst))
    total = len(timed_out)
    page_rows = timed_out[(page_no - 1) * size : page_no * size]
    user_ids: list[int] = []
    for task, inst in page_rows:
        user_ids.extend([task.assignee_user_id, inst.initiator_user_id])
    names = user_names(db, user_ids)
    return paged(
        [timeout_task_vo(task, inst, names, now=now) for task, inst in page_rows],
        total,
        page_no,
        size,
    )


@router.put("/timeout/{task_id}/urge")
def flow_timeout_urge(
    task_id: int,
    body: FlowTimeoutUrgeBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    task = db.get(FlowTask, task_id)
    if task is None or task.deleted or task.tenant_id != tenant_id:
        return fail(1001, "任务不存在")
    if task.task_status != "PENDING":
        return fail(1001, "任务已处理，不可督办")
    inst = db.get(FlowInstance, task.instance_id)
    if inst is None or inst.deleted or inst.tenant_id != tenant_id:
        return fail(1001, "流程实例不存在")
    if inst.instance_status != "RUNNING":
        return fail(1001, "实例已终态，不可督办")
    now = utcnow()
    started = task.started_at or now
    if started.tzinfo is not None:
        started = started.replace(tzinfo=None)
    if not body.fromInstance and now.replace(tzinfo=None) < started + timedelta(hours=DEFAULT_SLA_HOURS):
        return fail(1001, "任务未超时，不可督办")
    raw = body.urgeMessage or ""
    if len(raw) > 256:
        return fail(1001, "督办说明不能超过 256 字")
    message = raw.strip()
    task.remind_count = (task.remind_count or 0) + 1
    task.updated_at = now
    note = message or "请尽快处理该审批待办"
    _notify(
        db,
        user_id=task.assignee_user_id,
        tenant_id=tenant_id,
        title="流程催办",
        content=f"{inst.instance_no} {note}"[:512],
        ref_id=inst.id,
    )
    db.flush()
    timed_out = message == DINGTALK_TIMEOUT_MARK
    payload = {
        "remindCount": task.remind_count,
        "notifyChannel": "DINGTALK_STUB",
        "delivery": "QUEUED" if timed_out else "STUB_OK",
        "queued": timed_out,
        "urgeMessage": message,
    }
    if timed_out:
        return fail(5003, "钉钉推送失败已入补发队列", payload)
    return ok(payload)


def _notify(
    db: Session,
    *,
    user_id: int,
    tenant_id: int,
    title: str,
    content: str,
    ref_id: int,
) -> None:
    if user_id <= 0:
        return
    db.add(
        WorkMessage(
            user_id=user_id,
            title=title[:128],
            content=content[:512],
            channel="IN_APP",
            source_module="FLOW",
            ref_type="FLOW_INSTANCE",
            ref_id=ref_id,
            tenant_id=tenant_id,
            created_at=utcnow(),
        )
    )


def _resolve_write_nodes(body_nodes: list[dict] | None, node_chain: str | None, sla_hours: int) -> list[dict]:
    if body_nodes:
        return normalize_nodes(body_nodes)
    names = [part.strip() for part in (node_chain or "").replace("，", "、").split("、") if part.strip()]
    if names:
        return nodes_from_chain(names, sla_hours)
    return []


def _check_graph(nodes: list[dict]) -> tuple[int, str] | None:
    dag_err = validate_dag(nodes)
    if dag_err:
        return 1131, dag_err if "环路" in dag_err or "起止" in dag_err else f"DAG 校验失败：{dag_err}"
    rule_err = validate_rules(nodes)
    if rule_err:
        return 1132, rule_err
    return None


def next_template_code(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"FT{day}"
    taken = set(
        db.scalars(
            select(FlowTemplate.template_code).where(
                FlowTemplate.tenant_id == tenant_id,
                FlowTemplate.template_code.like(f"{prefix}%"),
            )
        ).all()
    )
    n = 1
    while f"{prefix}{n:03d}" in taken and n < 10000:
        n += 1
    return f"{prefix}{n:03d}"


def template_detail_vo(row: FlowTemplate, names: dict[int, str]) -> dict:
    base = template_vo(row, names)
    base.update(
        {
            "templateNo": row.template_code,
            "version": int(row.version_no or template_version_no(row)),
            "slaHours": int(row.sla_hours or DEFAULT_SLA_HOURS),
            "startCount": int(row.start_count or 0),
            "nodes": normalize_nodes(row.nodes) if row.nodes else nodes_from_preview(
                preview_nodes_for(row), int(row.sla_hours or DEFAULT_SLA_HOURS)
            ),
            "nodeChain": chain_text(normalize_nodes(row.nodes)) if row.nodes else chain_text(
                nodes_from_preview(preview_nodes_for(row))
            ),
            "createdBy": row.creator_id,
            "createdAt": iso(row.created_at),
        }
    )
    return base


def _load_template(db: Session, tenant_id: int, template_id: int) -> FlowTemplate | None:
    tpl = db.get(FlowTemplate, template_id)
    if tpl is None or tpl.deleted or tpl.tenant_id != tenant_id:
        return None
    return tpl


def _write_snapshot(db: Session, tpl: FlowTemplate, actor: User, change_desc: str) -> None:
    current = list(
        db.scalars(
            select(FlowTemplateVersion).where(
                FlowTemplateVersion.deleted == 0,
                FlowTemplateVersion.tenant_id == tpl.tenant_id,
                FlowTemplateVersion.template_id == tpl.id,
                FlowTemplateVersion.version_status == "CURRENT",
            )
        ).all()
    )
    for row in current:
        row.version_status = "HISTORICAL"
    now = utcnow()
    db.add(
        FlowTemplateVersion(
            template_id=tpl.id,
            version_no=int(tpl.version_no or 1),
            nodes=tpl.nodes,
            template_name=tpl.template_name,
            sla_hours=int(tpl.sla_hours or DEFAULT_SLA_HOURS),
            change_desc=(change_desc or "")[:256],
            version_status="CURRENT",
            published_by=actor.id,
            tenant_id=tpl.tenant_id,
            published_at=now,
            created_at=now,
        )
    )


def _apply_nodes(tpl: FlowTemplate, nodes: list[dict], sla_hours: int) -> None:
    tpl.nodes = nodes
    tpl.node_count = len(nodes)
    tpl.sla_hours = sla_hours
    tpl.version_label = f"v{int(tpl.version_no or 1)}.0"
    tpl.updated_at = utcnow()


@router.post("/template")
def flow_template_create(
    body: FlowTemplateWriteBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    name = (body.templateName or "").strip()
    if not name:
        return fail(1001, "模板名称必填")
    if len(name) > 128:
        return fail(1001, "模板名称不能超过 128 字")
    domain = (body.businessDomain or "COMMON").strip().upper()
    if domain not in DOMAINS:
        return fail(1001, "业务域非法")
    sla = int(body.slaHours or DEFAULT_SLA_HOURS)
    if sla not in SLA_CHOICES:
        return fail(1001, "节点超时须为 2/12/24/48/72 小时")
    nodes = _resolve_write_nodes(body.nodes, body.nodeChain, sla)
    if not nodes:
        return fail(1001, "节点链必填")
    checked = _check_graph(nodes)
    if checked:
        return fail(checked[0], checked[1])
    now = utcnow()
    row = FlowTemplate(
        template_code=next_template_code(db, tenant_id),
        template_name=name,
        business_domain=domain,
        status="DRAFT",
        version_label="v1.0",
        version_no=1,
        node_count=len(nodes),
        nodes=nodes,
        sla_hours=sla,
        start_count=0,
        creator_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return ok(template_detail_vo(row, user_names(db, [actor.id])))


@router.put("/template/{template_id}")
def flow_template_update(
    template_id: int,
    body: FlowTemplateWriteBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = _load_template(db, tenant_id, template_id)
    if tpl is None:
        return fail(1001, "模板不存在")
    status_only = (
        body.status
        and not (body.templateName or "").strip()
        and not body.nodes
        and not (body.nodeChain or "").strip()
        and body.slaHours is None
    )
    if status_only:
        target = (body.status or "").strip().upper()
        if target not in {"PUBLISHED", "DISABLED"}:
            return fail(1001, "状态非法")
        if tpl.status == "DRAFT" and target == "DISABLED":
            tpl.status = "DISABLED"
        elif tpl.status == "PUBLISHED" and target == "DISABLED":
            tpl.status = "DISABLED"
        elif tpl.status == "DISABLED" and target == "PUBLISHED":
            tpl.status = "PUBLISHED"
        else:
            return fail(1133, "已发布模板不可直接编辑，须升版本")
        tpl.updated_at = utcnow()
        db.flush()
        return ok(template_detail_vo(tpl, user_names(db, [tpl.creator_id])))
    if tpl.status != "DRAFT":
        return fail(1133, "已发布模板不可直接编辑，须升版本")
    name = (body.templateName or tpl.template_name).strip()
    if not name:
        return fail(1001, "模板名称必填")
    sla = int(body.slaHours or tpl.sla_hours or DEFAULT_SLA_HOURS)
    if sla not in SLA_CHOICES:
        return fail(1001, "节点超时须为 2/12/24/48/72 小时")
    nodes = _resolve_write_nodes(body.nodes or None, body.nodeChain, sla)
    if nodes:
        previous = normalize_nodes(tpl.nodes) if tpl.nodes else []
        if previous and ends_moved(previous, nodes):
            return fail(1001, "首 / 尾节点不可移动")
        checked = _check_graph(nodes)
        if checked:
            return fail(checked[0], checked[1])
        _apply_nodes(tpl, nodes, sla)
    tpl.template_name = name
    tpl.updated_at = utcnow()
    db.flush()
    return ok(template_detail_vo(tpl, user_names(db, [tpl.creator_id])))


@router.post("/template/{template_id}/publish")
def flow_template_publish(
    template_id: int,
    body: FlowTemplatePublishBody | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = _load_template(db, tenant_id, template_id)
    if tpl is None:
        return fail(1001, "模板不存在")
    payload = body or FlowTemplatePublishBody()
    sla = int(payload.slaHours or tpl.sla_hours or DEFAULT_SLA_HOURS)
    if sla not in SLA_CHOICES:
        return fail(1001, "节点超时须为 2/12/24/48/72 小时")
    incoming = _resolve_write_nodes(payload.nodes, payload.nodeChain, sla)
    previous = normalize_nodes(tpl.nodes) if tpl.nodes else graph_nodes(db, tpl)
    nodes = incoming or previous
    if not nodes:
        return fail(1131, "DAG 校验失败：缺起止节点")
    if previous and incoming and ends_moved(previous, incoming):
        return fail(1001, "首 / 尾节点不可移动")
    checked = _check_graph(nodes)
    if checked:
        return fail(checked[0], checked[1])
    if (payload.templateName or "").strip():
        tpl.template_name = payload.templateName.strip()
    if tpl.status == "PUBLISHED" and not incoming:
        return ok(template_detail_vo(tpl, user_names(db, [tpl.creator_id, actor.id])))
    if tpl.status == "PUBLISHED" and incoming:
        already = db.scalar(
            select(FlowTemplateVersion.id).where(
                FlowTemplateVersion.deleted == 0,
                FlowTemplateVersion.tenant_id == tenant_id,
                FlowTemplateVersion.template_id == tpl.id,
                FlowTemplateVersion.version_no == int(tpl.version_no or 1),
            )
        )
        if already is None:
            _write_snapshot(db, tpl, actor, "升版本前快照")
            db.flush()
        tpl.version_no = int(tpl.version_no or 1) + 1
    _apply_nodes(tpl, nodes, sla)
    tpl.status = "PUBLISHED"
    if not tpl.version_no:
        tpl.version_no = 1
    _write_snapshot(db, tpl, actor, payload.changeDesc or "发布")
    db.flush()
    return ok(template_detail_vo(tpl, user_names(db, [tpl.creator_id, actor.id])))


def _version_nodes(db: Session, tpl: FlowTemplate, version_no: int) -> list[dict] | None:
    snap = db.scalar(
        select(FlowTemplateVersion).where(
            FlowTemplateVersion.deleted == 0,
            FlowTemplateVersion.tenant_id == tpl.tenant_id,
            FlowTemplateVersion.template_id == tpl.id,
            FlowTemplateVersion.version_no == version_no,
        )
    )
    if snap is None or not snap.nodes:
        if version_no == int(tpl.version_no or 1) and tpl.nodes:
            return normalize_nodes(tpl.nodes)
        return None
    return normalize_nodes(snap.nodes)


@router.get("/version/list")
def flow_version_list(
    templateId: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = _load_template(db, tenant_id, templateId)
    if tpl is None:
        return fail(1001, "模板不存在")
    rows = list(
        db.scalars(
            select(FlowTemplateVersion)
            .where(
                FlowTemplateVersion.deleted == 0,
                FlowTemplateVersion.tenant_id == tenant_id,
                FlowTemplateVersion.template_id == tpl.id,
            )
            .order_by(FlowTemplateVersion.version_no.desc())
        ).all()
    )
    names = user_names(db, [row.published_by for row in rows])
    return ok(
        [
            {
                "templateId": tpl.id,
                "version": row.version_no,
                "changeDesc": row.change_desc or "",
                "publishedBy": row.published_by,
                "publishedByName": names.get(row.published_by, ""),
                "publishedAt": iso(row.published_at),
                "status": row.version_status,
            }
            for row in rows
        ]
    )


@router.get("/version/diff")
def flow_version_diff(
    templateId: int,
    fromVersion: int,
    toVersion: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = _load_template(db, tenant_id, templateId)
    if tpl is None:
        return fail(1001, "模板不存在")
    old = _version_nodes(db, tpl, fromVersion)
    new = _version_nodes(db, tpl, toVersion)
    if old is None or new is None:
        return fail(1134, "回滚目标版本非法")
    return ok({"nodeChanges": diff_nodes(old, new), "configChanges": []})


@router.get("/version/snapshot")
def flow_version_snapshot(
    templateId: int,
    version: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = _load_template(db, tenant_id, templateId)
    if tpl is None:
        return fail(1001, "模板不存在")
    nodes = _version_nodes(db, tpl, version)
    if nodes is None:
        return fail(1134, "回滚目标版本非法")
    data = template_detail_vo(tpl, user_names(db, [tpl.creator_id]))
    data["version"] = version
    data["nodes"] = nodes
    data["nodeChain"] = chain_text(nodes)
    data["readonly"] = True
    return ok(data)


@router.post("/version/{template_id}/rollback")
def flow_version_rollback(
    template_id: int,
    body: FlowVersionRollbackBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    tpl = _load_template(db, tenant_id, template_id)
    if tpl is None:
        return fail(1001, "模板不存在")
    nodes = _version_nodes(db, tpl, body.targetVersion)
    if nodes is None or body.targetVersion < 1:
        return fail(1134, "回滚目标版本非法")
    if tpl.status == "DRAFT":
        return fail(1134, "回滚目标版本非法")
    tpl.version_no = int(tpl.version_no or 1) + 1
    _apply_nodes(tpl, nodes, int(tpl.sla_hours or DEFAULT_SLA_HOURS))
    tpl.status = "PUBLISHED"
    _write_snapshot(db, tpl, actor, body.changeDesc or f"回滚到 v{body.targetVersion}")
    db.flush()
    return ok({"newVersion": tpl.version_no, "targetVersion": body.targetVersion})
