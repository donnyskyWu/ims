from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import iso, tenant
from app.corp import ops_db, page_args, paged
from app.models import (
    ContentProject,
    ContentTask,
    ContentWorkTaskAssignment,
    ContentWorkTaskAssignmentTask,
    User,
)
from app.ops_models import AuthorUser, IpGroup

router = APIRouter(prefix="/content/task", tags=["content-task"])

APPROVED_CONTENT_STATUSES = frozenset(
    {
        "PENDING_PUBLISH",
        "PUBLISHED_DRAFT",
        "FORMALLY_PUBLISHED",
        "PUBLISHED",
        "UNPUBLISHED",
    }
)
ACTIVE_TASK_STATUSES = frozenset({"PENDING", "IN_PROGRESS", "PENDING_REVIEW"})


class ExecuteSaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    deliverables: str | None = None
    userAttachments: list[dict] = Field(default_factory=list)


class CompleteBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    deliverables: str | None = None


def load_task(db: Session, task_id: int, actor: User) -> ContentTask | None:
    row = db.get(ContentTask, task_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return None
    return row


def competition_summary(competitions: list) -> tuple[str, str]:
    if not competitions:
        return "", ""
    first = competitions[0] if isinstance(competitions[0], dict) else {}
    cid = str(first.get("competitionId") or "")
    cname = str(first.get("competitionName") or first.get("leagueName") or "")
    return cid, cname


def work_task_remark(row: ContentWorkTaskAssignment | None) -> str:
    if row is None:
        return ""
    parts: list[str] = []
    for comp in row.competitions or []:
        if not isinstance(comp, dict):
            continue
        name = comp.get("competitionName") or comp.get("leagueName") or comp.get("competitionId") or ""
        live = "是" if row.is_live else "否"
        live_part = f"（{row.live_time}）" if row.is_live and row.live_time else ""
        parts.append(f"{name}-{row.marketing_plan}-{live}{live_part}-{row.sales_platform}；")
    return "".join(parts)


def linked_content_vo(project: ContentProject | None) -> dict | None:
    if project is None or project.deleted:
        return None
    return {
        "id": project.id,
        "title": project.title,
        "status": project.content_status,
        "documentType": project.document_type or "",
        "aiGenerateStatus": project.ai_generate_status,
        "aiGenerateError": project.ai_generate_error,
    }


def task_list_vo(db: Session, ops: Session, row: ContentTask) -> dict:
    group = ops.get(IpGroup, row.ip_group_id)
    assignee = db.get(User, row.assignee_user_id)
    author = ops.get(AuthorUser, row.author_id) if row.author_id else None
    assignment = db.get(ContentWorkTaskAssignment, row.assignment_id) if row.assignment_id else None
    project = db.scalar(
        select(ContentProject).where(
            ContentProject.task_id == row.id,
            ContentProject.deleted == 0,
            ContentProject.tenant_id == row.tenant_id,
        )
    )
    _, cname = competition_summary(row.competitions or [])
    return {
        "id": row.id,
        "planName": row.plan_name or "",
        "nodeName": row.node_name,
        "nodeType": row.node_type or "NORMAL",
        "ipGroupId": row.ip_group_id,
        "ipGroupName": group.group_name if group else "",
        "assigneeUserId": row.assignee_user_id,
        "assigneeName": (assignee.nickname or assignee.username) if assignee else "",
        "status": row.task_status,
        "competitionName": cname,
        "marketingPlan": row.marketing_plan,
        "workDate": row.work_date,
        "authorId": row.author_id,
        "authorName": author.author_name if author else "",
        "isLive": assignment.is_live if assignment else 0,
        "liveTime": assignment.live_time if assignment else "",
        "linkedContent": linked_content_vo(project),
        "createdAt": iso(row.created_at),
    }


def ensure_in_progress(task: ContentTask, actor: User) -> str | None:
    if task.assignee_user_id != actor.id:
        return "assignee"
    if task.task_status == "PENDING":
        task.task_status = "IN_PROGRESS"
    if task.task_status not in ("IN_PROGRESS", "PENDING_REVIEW"):
        return "status"
    return None


def content_passes_gate(project: ContentProject | None) -> bool:
    if project is None or project.deleted:
        return False
    if project.review_passed:
        return True
    return project.content_status in APPROVED_CONTENT_STATUSES


def complete_task(db: Session, task: ContentTask, actor: User, deliverables: str | None) -> tuple[int, str]:
    err = ensure_in_progress(task, actor)
    if err == "assignee":
        return 1504, "资源不可用"
    if err == "status":
        return 1500, "参数校验失败"
    node_type = task.node_type or "NORMAL"
    if node_type == "CONTENT_GENERATION":
        project = db.scalar(
            select(ContentProject).where(
                ContentProject.task_id == task.id,
                ContentProject.deleted == 0,
                ContentProject.tenant_id == task.tenant_id,
            )
        )
        if not content_passes_gate(project):
            return 1500, "内容须审核通过后方可完成任务"
    else:
        text = (deliverables or task.deliverables or "").strip()
        if not text:
            return 1500, "请填写工作说明"
        task.deliverables = text
    task.task_status = "DONE"
    return 0, "ok"


@router.get("/page")
def task_page(
    pageNo: int = 1,
    pageSize: int = 10,
    onlyMine: bool = True,
    ipGroupId: int | None = None,
    workDate: str | None = None,
    planName: str | None = None,
    status: str | None = None,
    assigneeUserId: int | None = None,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tid = tenant(actor)
    stmt = select(ContentTask).where(
        ContentTask.deleted == 0,
        ContentTask.tenant_id == tid,
        ContentTask.visible_in_list == 1,
        ContentTask.task_status != "CANCELLED",
    )
    if onlyMine:
        stmt = stmt.where(ContentTask.assignee_user_id == actor.id)
    elif assigneeUserId is not None:
        stmt = stmt.where(ContentTask.assignee_user_id == assigneeUserId)
    if ipGroupId is not None:
        stmt = stmt.where(ContentTask.ip_group_id == ipGroupId)
    if workDate:
        stmt = stmt.where(ContentTask.work_date == workDate.strip()[:10])
    if planName:
        stmt = stmt.where(ContentTask.plan_name.contains(planName.strip()))
    if status:
        stmt = stmt.where(ContentTask.task_status == status.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(ContentTask.id.desc()).offset((page_no - 1) * size).limit(size)
    ).all()
    return paged([task_list_vo(db, ops, row) for row in rows], total, page_no, size)


@router.get("/{task_id}/execute")
def task_execute(
    task_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    task = load_task(db, task_id, actor)
    if task is None:
        return fail(1504, "资源不可用")
    if task.assignee_user_id != actor.id:
        return fail(1504, "资源不可用")
    if task.task_status == "PENDING":
        task.task_status = "IN_PROGRESS"
    from app.models import ContentSopNode

    node = db.get(ContentSopNode, task.sop_node_id)
    instruction = (node.instruction_text if node else "") or (node.node_name if node else task.node_name)
    attachments = list(node.attachment_urls or []) if node else []
    assignment = db.get(ContentWorkTaskAssignment, task.assignment_id)
    cid, cname = competition_summary(task.competitions or [])
    group = ops.get(IpGroup, task.ip_group_id)
    project = db.scalar(
        select(ContentProject).where(
            ContentProject.task_id == task.id,
            ContentProject.deleted == 0,
            ContentProject.tenant_id == task.tenant_id,
        )
    )
    siblings: list[ContentTask] = []
    if assignment is not None:
        link_ids = db.scalars(
            select(ContentWorkTaskAssignmentTask.task_id).where(
                ContentWorkTaskAssignmentTask.assignment_id == assignment.id,
                ContentWorkTaskAssignmentTask.tenant_id == task.tenant_id,
            )
        ).all()
        if link_ids:
            siblings = list(
                db.scalars(
                    select(ContentTask).where(
                        ContentTask.id.in_(link_ids),
                        ContentTask.deleted == 0,
                        ContentTask.sop_node_id == task.sop_node_id,
                    )
                ).all()
            )
    ip_tabs: list[dict] = []
    if len(siblings) > 1:
        for sib in siblings:
            g = ops.get(IpGroup, sib.ip_group_id)
            proj = db.scalar(
                select(ContentProject).where(
                    ContentProject.task_id == sib.id,
                    ContentProject.deleted == 0,
                    ContentProject.tenant_id == sib.tenant_id,
                )
            )
            ip_tabs.append(
                {
                    "taskId": sib.id,
                    "ipGroupId": sib.ip_group_id,
                    "ipGroupName": g.group_name if g else "",
                    "status": sib.task_status,
                    "linkedContent": linked_content_vo(proj),
                }
            )
    author = ops.get(AuthorUser, task.author_id) if task.author_id else None
    return ok(
        {
            "id": task.id,
            "nodeName": task.node_name,
            "nodeType": task.node_type or "NORMAL",
            "planName": task.plan_name or "",
            "ipGroupId": task.ip_group_id,
            "ipGroupName": group.group_name if group else "",
            "authorName": author.author_name if author else "",
            "competitionId": cid,
            "competitionName": cname,
            "marketingPlan": task.marketing_plan,
            "isLive": assignment.is_live if assignment else 0,
            "liveTime": assignment.live_time if assignment else "",
            "salesPlatform": assignment.sales_platform if assignment else "",
            "workTaskRemark": work_task_remark(assignment),
            "executionInstruction": instruction,
            "attachments": attachments,
            "userAttachments": list(task.user_attachments or []),
            "deliverables": task.deliverables or "",
            "status": task.task_status,
            "linkedContent": linked_content_vo(project),
            "ipGroupTabs": ip_tabs,
        }
    )


@router.post("/{task_id}/execute/save")
def task_execute_save(
    task_id: int,
    body: ExecuteSaveBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    task = load_task(db, task_id, actor)
    if task is None:
        return fail(1504, "资源不可用")
    if task.assignee_user_id != actor.id:
        return fail(1504, "资源不可用")
    if body.deliverables is not None:
        task.deliverables = body.deliverables[:4000]
    if body.userAttachments is not None:
        task.user_attachments = body.userAttachments
    return ok(None)


@router.post("/{task_id}/execute/complete")
def task_execute_complete(
    task_id: int,
    body: CompleteBody | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    task = load_task(db, task_id, actor)
    if task is None:
        return fail(1504, "资源不可用")
    code, msg = complete_task(db, task, actor, body.deliverables if body else None)
    if code:
        return fail(code, msg)
    return ok({"status": task.task_status})


@router.put("/{task_id}/complete")
def task_complete(
    task_id: int,
    body: CompleteBody | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    task = load_task(db, task_id, actor)
    if task is None:
        return fail(1504, "资源不可用")
    code, msg = complete_task(db, task, actor, body.deliverables if body else None)
    if code:
        return fail(code, msg)
    return ok({"status": task.task_status})
