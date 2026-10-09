"""工作流 FLOW-001/002 · 模板/实例列表 + 发起实例（P0 桩）。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import FlowInstance, FlowTask, FlowTemplate, User

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
# 本地预览桩：不落设计器，按种子模板给出串行节点与处理人预览文案。
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


class FlowTimeoutUrgeBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    urgeMessage: str | None = None


STATUS_LABELS = {
    "DRAFT": "草稿",
    "PUBLISHED": "已发布",
    "DISABLED": "已停用",
    "RUNNING": "进行中",
    "APPROVED": "已通过",
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
    return {
        "id": row.id,
        "templateCode": row.template_code,
        "templateName": row.template_name,
        "businessDomain": row.business_domain,
        "businessDomainLabel": DOMAIN_LABELS.get(row.business_domain, row.business_domain),
        "status": row.status,
        "statusLabel": STATUS_LABELS.get(row.status, row.status),
        "versionLabel": row.version_label,
        "nodeCount": row.node_count,
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


def instance_start_vo(row: FlowInstance, tpl: FlowTemplate, actor: User, names: dict[int, str]) -> dict:
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
                "nodeOrder": 1,
                "nodeName": row.current_node_name,
                "assigneeUserId": actor.id,
                "assigneeName": names.get(actor.id, ""),
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
        node_order=1,
        node_name=node_name or inst.current_node_name or "审批节点",
        node_type="APPROVE",
        assignee_user_id=assignee_user_id,
        task_status="PENDING",
        tenant_id=tenant_id,
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.flush()
    return task


def sync_seed_tasks(db: Session, tenant_id: int, default_assignee_id: int) -> None:
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
        ensure_pending_task(db, inst, tenant_id, default_assignee_id, inst.current_node_name)


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


def instance_vo(row: FlowInstance, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "instanceNo": row.instance_no,
        "templateId": row.template_id,
        "templateName": row.template_name,
        "title": row.title,
        "instanceStatus": row.instance_status,
        "instanceStatusLabel": STATUS_LABELS.get(row.instance_status, row.instance_status),
        "currentNodeName": row.current_node_name,
        "initiatorName": names.get(row.initiator_user_id, ""),
        "startedAt": iso(row.started_at),
        "finishedAt": iso(row.finished_at),
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
    names = user_names(db, [r.initiator_user_id for r in rows])
    return paged([instance_vo(r, names) for r in rows], total, page_no, size)


@router.post("/instance")
def flow_instance_start(
    body: FlowInstanceStartBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """发起流程实例（本地桩：首节点处理人=发起人，无 Flowable）。"""
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
            ensure_pending_task(db, existing, tenant_id, actor.id, existing.current_node_name)
            names = user_names(db, [existing.initiator_user_id, actor.id])
            replay = instance_start_vo(existing, tpl, actor, names)
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

    first_node = FIRST_NODE_BY_CODE.get(tpl.template_code, "审批节点")
    now = utcnow()
    row = FlowInstance(
        instance_no=next_instance_no(db, tenant_id),
        template_id=tpl.id,
        template_name=tpl.template_name,
        title=title,
        business_key=biz_key,
        form_data=form,
        instance_status="RUNNING",
        current_node_name=first_node,
        initiator_user_id=actor.id,
        tenant_id=tenant_id,
        started_at=now,
        finished_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    ensure_pending_task(db, row, tenant_id, actor.id, first_node)
    names = user_names(db, [actor.id])
    return ok(instance_start_vo(row, tpl, actor, names))


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
            FlowTask.assignee_user_id == actor.id,
            FlowTask.task_status == "PENDING",
            FlowInstance.deleted == 0,
        )
    )
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
    max_order = 1
    if tpl is not None and not tpl.deleted:
        orders = [order for order, *_rest in preview_nodes_for(tpl)]
        if orders:
            max_order = max(orders)
    reject_order: int | None = None
    if action == "REJECT":
        if body.rejectToNodeOrder is None:
            reject_order = 1
        elif body.rejectToNodeOrder < 1 or body.rejectToNodeOrder > max_order:
            return fail(1001, "退回目标节点无效")
        else:
            reject_order = body.rejectToNodeOrder

    if body.formDataPatch:
        merged = dict(inst.form_data or {})
        merged.update(body.formDataPatch)
        inst.form_data = merged

    now = utcnow()
    comment = (body.comment or "").strip()
    if len(comment) > 512:
        return fail(1001, "审批意见不能超过 512 字")
    task.comment = comment
    task.handled_at = now
    task.updated_at = now

    if action == "APPROVE":
        task.task_status = "APPROVED"
        inst.instance_status = "APPROVED"
        inst.current_node_name = "—"
        inst.finished_at = now
        inst.updated_at = now
        new_status = "APPROVED"
        is_finished = True
        next_nodes: list[dict] = []
    else:
        task.task_status = "REJECTED"
        inst.instance_status = "REJECTED"
        inst.current_node_name = "—"
        inst.finished_at = now
        inst.updated_at = now
        new_status = "REJECTED"
        is_finished = True
        next_nodes = []

    db.flush()
    comment_hint = "退回建议填写意见" if action == "REJECT" and not comment else ""
    return ok(
        {
            "taskId": task.id,
            "instanceNo": inst.instance_no,
            "newStatus": new_status,
            "nextNodes": next_nodes,
            "isInstanceFinished": is_finished,
            "rejectToNodeOrder": reject_order,
            "commentHint": comment_hint,
        }
    )


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
    templateName: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_flow(db, tenant_id, actor.id)
    now = utcnow()
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
    if templateName:
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
    page_no, size = page_args(pageNo, pageSize)
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
    if now.replace(tzinfo=None) < started + timedelta(hours=DEFAULT_SLA_HOURS):
        return fail(1001, "任务未超时，不可督办")
    raw = body.urgeMessage or ""
    if len(raw) > 256:
        return fail(1001, "督办说明不能超过 256 字")
    message = raw.strip()
    task.remind_count = (task.remind_count or 0) + 1
    task.updated_at = now
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
