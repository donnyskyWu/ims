from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import iso, tenant
from app.core import utcnow
from app.corp import ops_db
from app.models import (
    ContentProject,
    ContentSop,
    ContentSopNode,
    ContentTask,
    ContentWorkTaskAssignment,
    ContentWorkTaskAssignmentTask,
    ContentWorkTaskSheet,
    SysParam,
    User,
)
from app.ops_models import AuthorUser, IpGroup, IpGroupAnchorRel

router = APIRouter(prefix="/content/work-task", tags=["content-work-task"])

BJ = timezone(timedelta(hours=8))
MARKETING_PLANS = {"LIVE_PUBLIC", "PAID_SALES", "LIVE", "VIDEO"}
SALES_PLATFORMS = {"PRIVATE", "KUAISHOU", "DOUYIN", "NONE"}
DEFAULT_ROW_COUNT = 10


class CompetitionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    competitionId: str
    competitionName: str = ""
    leagueName: str = ""
    matchTime: str = ""


class AssignmentSaveItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    rowNo: int
    authorId: int
    assigneeId: int | None = None
    publishAccountId: int | None = None
    workDate: str
    marketingPlan: str
    isLive: int = 0
    liveTime: str = ""
    salesPlatform: str = "NONE"
    winPrediction: str = "UNKNOWN"
    sopId: int | None = None
    competitions: list[CompetitionItem] = Field(default_factory=list)


class SheetSaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ipGroupId: int
    workDate: str
    assignments: list[AssignmentSaveItem]


class ConfirmBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    assignmentIds: list[int]


def param_bool(db: Session, key: str) -> bool:
    row = db.scalar(select(SysParam).where(SysParam.param_key == key))
    if row is None:
        return False
    return str(row.param_value).lower() in ("true", "1", "yes")


def author_in_group(ops: Session, ip_group_id: int, author_id: int, tenant_id: int) -> bool:
    author = ops.get(AuthorUser, author_id)
    if author is None or author.deleted or (author.tenant_id or 0) != tenant_id:
        return False
    if author.status != "ENABLED":
        return False
    rel = ops.scalar(
        select(IpGroupAnchorRel.id).where(
            IpGroupAnchorRel.ip_group_id == ip_group_id,
            IpGroupAnchorRel.anchor_user_id == author_id,
            IpGroupAnchorRel.deleted == 0,
            IpGroupAnchorRel.tenant_id == tenant_id,
        )
    )
    return rel is not None


def assignment_vo(db: Session, ops: Session, row: ContentWorkTaskAssignment) -> dict:
    author = ops.get(AuthorUser, row.author_id)
    task_ids = db.scalars(
        select(ContentWorkTaskAssignmentTask.task_id).where(
            ContentWorkTaskAssignmentTask.assignment_id == row.id,
            ContentWorkTaskAssignmentTask.tenant_id == row.tenant_id,
        )
    ).all()
    return {
        "id": row.id,
        "rowNo": row.row_no,
        "authorId": row.author_id,
        "authorName": author.author_name if author else "",
        "assigneeId": row.assignee_id,
        "publishAccountId": row.publish_account_id,
        "workDate": row.work_date,
        "marketingPlan": row.marketing_plan,
        "isLive": row.is_live,
        "liveTime": row.live_time,
        "salesPlatform": row.sales_platform,
        "winPrediction": row.win_prediction,
        "sopId": int(row.sop_id or 0),
        "competitions": row.competitions or [],
        "rowStatus": row.row_status,
        "generatedTaskIds": list(task_ids),
    }


def sheet_vo(db: Session, ops: Session, sheet: ContentWorkTaskSheet) -> dict:
    group = ops.get(IpGroup, sheet.ip_group_id)
    leader_name = ""
    if group and group.leader_user_id:
        leader = db.get(User, int(group.leader_user_id))
        if leader:
            leader_name = leader.nickname or leader.username or ""
    rows = db.scalars(
        select(ContentWorkTaskAssignment)
        .where(
            ContentWorkTaskAssignment.sheet_id == sheet.id,
            ContentWorkTaskAssignment.deleted == 0,
            ContentWorkTaskAssignment.tenant_id == sheet.tenant_id,
        )
        .order_by(ContentWorkTaskAssignment.row_no.asc())
    ).all()
    return {
        "id": sheet.id,
        "ipGroupId": sheet.ip_group_id,
        "ipGroupName": group.group_name if group else "",
        "ipGroupLeaderName": leader_name,
        "workDate": sheet.work_date,
        "status": sheet.status,
        "confirmedAt": sheet.confirmed_at,
        "assignments": [assignment_vo(db, ops, item) for item in rows],
    }


def empty_rows(work_date: str, start: int = 1) -> list[AssignmentSaveItem]:
    return [
        AssignmentSaveItem(
            rowNo=i,
            authorId=0,
            workDate=work_date,
            marketingPlan="LIVE_PUBLIC",
            isLive=0,
            salesPlatform="NONE",
            competitions=[],
        )
        for i in range(start, start + DEFAULT_ROW_COUNT)
    ]


def load_sheet(db: Session, sheet_id: int, actor: User) -> ContentWorkTaskSheet | None:
    row = db.get(ContentWorkTaskSheet, sheet_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return None
    return row


def enabled_sops_for_plan(db: Session, marketing_plan: str, tenant_id: int) -> list[ContentSop]:
    stmt = (
        select(ContentSop)
        .where(
            ContentSop.deleted == 0,
            ContentSop.tenant_id == tenant_id,
            ContentSop.status == "ENABLED",
            ContentSop.marketing_plan == marketing_plan,
        )
        .order_by(ContentSop.version.desc(), ContentSop.id.desc())
    )
    return list(db.scalars(stmt).all())


def resolve_confirm_sop(
    db: Session, marketing_plan: str, tenant_id: int, sop_id: int | None
) -> ContentSop | None:
    """出任务模板。指定 sopId 时只用该启用 SOP，避免并行用例抢同一条公推模板。

    未指定且同营销计划启用 SOP 不止一条时返回 None（1502），不按最新 id 抢绑。
    """
    if sop_id:
        sop = db.get(ContentSop, int(sop_id))
        if (
            sop is None
            or sop.deleted
            or (sop.tenant_id or 0) != tenant_id
            or sop.status != "ENABLED"
            or (sop.marketing_plan or "") != (marketing_plan or "")
        ):
            return None
        return sop
    matches = enabled_sops_for_plan(db, marketing_plan, tenant_id)
    if len(matches) == 1:
        return matches[0]
    return None


def validate_assignment(
    ops: Session, ip_group_id: int, item: AssignmentSaveItem, tenant_id: int, sheet_id: int, db: Session
) -> str | None:
    if not item.competitions:
        return "competitions"
    if item.marketingPlan not in MARKETING_PLANS:
        return "marketingPlan"
    if item.salesPlatform not in SALES_PLATFORMS:
        return "salesPlatform"
    if item.isLive and not item.liveTime:
        return "liveTime"
    if not item.authorId or not author_in_group(ops, ip_group_id, item.authorId, tenant_id):
        return "author"
    seen: set[str] = set()
    for other in db.scalars(
        select(ContentWorkTaskAssignment).where(
            ContentWorkTaskAssignment.sheet_id == sheet_id,
            ContentWorkTaskAssignment.deleted == 0,
            ContentWorkTaskAssignment.work_date == item.workDate[:10],
            ContentWorkTaskAssignment.author_id == item.authorId,
            ContentWorkTaskAssignment.row_no != item.rowNo,
        )
    ).all():
        for comp in other.competitions or []:
            cid = comp.get("competitionId") if isinstance(comp, dict) else None
            if cid:
                seen.add(str(cid))
    for comp in item.competitions:
        cid = comp.competitionId
        if cid in seen:
            return "duplicateCompetition"
        seen.add(cid)
    return None


@router.get("/sheet")
def sheet_get_or_create(
    ipGroupId: int,
    workDate: str,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tid = tenant(actor)
    group = ops.get(IpGroup, ipGroupId)
    if group is None or group.deleted or (group.tenant_id or 0) != tid:
        return fail(1500, "参数校验失败")
    if group.status != "ENABLED":
        return fail(1501, "关联资源不可用或已停用")
    date = workDate[:10]
    sheet = db.scalar(
        select(ContentWorkTaskSheet).where(
            ContentWorkTaskSheet.ip_group_id == ipGroupId,
            ContentWorkTaskSheet.work_date == date,
            ContentWorkTaskSheet.deleted == 0,
            ContentWorkTaskSheet.tenant_id == tid,
        )
    )
    if sheet is None:
        sheet = ContentWorkTaskSheet(
            ip_group_id=ipGroupId,
            work_date=date,
            status="DRAFT",
            creator=actor.id,
            tenant_id=tid,
        )
        db.add(sheet)
        db.flush()
        for item in empty_rows(date):
            db.add(
                ContentWorkTaskAssignment(
                    sheet_id=sheet.id,
                    row_no=item.rowNo,
                    author_id=0,
                    work_date=date,
                    marketing_plan=item.marketingPlan,
                    tenant_id=tid,
                )
            )
        db.flush()
    return ok(sheet_vo(db, ops, sheet))


@router.post("/sheet")
def sheet_save(
    body: SheetSaveBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    tid = tenant(actor)
    group = ops.get(IpGroup, body.ipGroupId)
    if group is None or group.deleted or (group.tenant_id or 0) != tid:
        return fail(1500, "参数校验失败")
    date = body.workDate[:10]
    sheet = db.scalar(
        select(ContentWorkTaskSheet).where(
            ContentWorkTaskSheet.ip_group_id == body.ipGroupId,
            ContentWorkTaskSheet.work_date == date,
            ContentWorkTaskSheet.deleted == 0,
            ContentWorkTaskSheet.tenant_id == tid,
        )
    )
    if sheet is None:
        sheet = ContentWorkTaskSheet(
            ip_group_id=body.ipGroupId,
            work_date=date,
            status="DRAFT",
            creator=actor.id,
            tenant_id=tid,
        )
        db.add(sheet)
        db.flush()
    for item in body.assignments:
        if item.authorId <= 0 and not item.competitions:
            continue
        err = validate_assignment(ops, body.ipGroupId, item, tid, sheet.id, db)
        if err:
            if err == "author":
                return fail(1501, "关联资源不可用或已停用")
            if err == "duplicateCompetition":
                return fail(1502, "业务规则冲突")
            return fail(1500, "参数校验失败")
    existing = {
        row.row_no: row
        for row in db.scalars(
            select(ContentWorkTaskAssignment).where(
                ContentWorkTaskAssignment.sheet_id == sheet.id,
                ContentWorkTaskAssignment.deleted == 0,
            )
        ).all()
    }
    touched: set[int] = set()
    for item in body.assignments:
        if item.authorId <= 0 and not item.competitions:
            continue
        row = existing.get(item.rowNo)
        if row is None:
            row = ContentWorkTaskAssignment(sheet_id=sheet.id, row_no=item.rowNo, tenant_id=tid)
            db.add(row)
        if row.row_status == "CONFIRMED":
            continue
        row.author_id = item.authorId
        row.assignee_id = item.assigneeId
        row.publish_account_id = item.publishAccountId
        row.work_date = item.workDate[:10]
        row.marketing_plan = item.marketingPlan
        row.is_live = 1 if item.isLive else 0
        row.live_time = (item.liveTime or "")[:8]
        row.sales_platform = item.salesPlatform
        row.win_prediction = (item.winPrediction or "UNKNOWN")[:16]
        row.sop_id = int(item.sopId or 0)
        row.competitions = [c.model_dump() for c in item.competitions]
        touched.add(item.rowNo)
    for row_no, row in existing.items():
        if row_no not in touched and row.row_status != "CONFIRMED":
            row.deleted = 1
    db.flush()
    return ok(sheet_vo(db, ops, sheet))


def resolve_assignee(group: IpGroup, node: ContentSopNode) -> int:
    if group.leader_user_id:
        return int(group.leader_user_id)
    return 1


@router.post("/{sheet_id}/confirm")
def sheet_confirm(
    sheet_id: int,
    body: ConfirmBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    sheet = load_sheet(db, sheet_id, actor)
    if sheet is None:
        return fail(1504, "资源不可用")
    if not body.assignmentIds:
        return fail(1500, "参数校验失败")
    group = ops.get(IpGroup, sheet.ip_group_id)
    if group is None:
        return fail(1500, "参数校验失败")
    auto_ai = param_bool(db, "work.task.confirm.auto-ai-generate")
    generated = 0
    tid = tenant(actor)
    for aid in body.assignmentIds:
        row = db.get(ContentWorkTaskAssignment, aid)
        if row is None or row.deleted or row.sheet_id != sheet.id or (row.tenant_id or 0) != tid:
            return fail(1504, "资源不可用")
        if row.row_status == "CONFIRMED":
            continue
        item = AssignmentSaveItem(
            rowNo=row.row_no,
            authorId=row.author_id,
            assigneeId=row.assignee_id,
            publishAccountId=row.publish_account_id,
            workDate=row.work_date,
            marketingPlan=row.marketing_plan,
            isLive=row.is_live,
            liveTime=row.live_time,
            salesPlatform=row.sales_platform,
            winPrediction=row.win_prediction,
            competitions=[CompetitionItem(**c) for c in (row.competitions or [])],
        )
        err = validate_assignment(ops, sheet.ip_group_id, item, tid, sheet.id, db)
        if err:
            if err == "duplicateCompetition":
                return fail(1502, "业务规则冲突")
            return fail(1500, "参数校验失败")
        sop = resolve_confirm_sop(db, row.marketing_plan, tid, row.sop_id or None)
        if sop is None:
            return fail(1502, "业务规则冲突")
        nodes = db.scalars(
            select(ContentSopNode)
            .where(ContentSopNode.sop_id == sop.id, ContentSopNode.deleted == 0)
            .order_by(ContentSopNode.node_order.asc())
        ).all()
        if not nodes:
            return fail(1502, "业务规则冲突")
        for node in nodes:
            assignee = resolve_assignee(group, node)
            task = ContentTask(
                assignment_id=row.id,
                sop_id=sop.id,
                sop_node_id=node.id,
                ip_group_id=sheet.ip_group_id,
                author_id=row.author_id,
                assignee_user_id=assignee,
                node_name=node.node_name,
                node_type=node.node_type or "NORMAL",
                task_status="PENDING",
                visible_in_list=1,
                marketing_plan=row.marketing_plan,
                work_date=row.work_date,
                plan_name=f"{row.work_date} 工作任务",
                competitions=row.competitions or [],
                tenant_id=tid,
            )
            db.add(task)
            db.flush()
            db.add(
                ContentWorkTaskAssignmentTask(
                    assignment_id=row.id,
                    task_id=task.id,
                    tenant_id=tid,
                )
            )
            generated += 1
            if (node.node_type or "NORMAL") == "CONTENT_GENERATION":
                project = ContentProject(
                    title=f"{row.marketing_plan}-{row.work_date}",
                    content_status="DRAFT",
                    document_type=node.document_type or "COPY",
                    task_id=task.id,
                    ai_generate_status=None,
                    submitter_user_id=assignee,
                    creator=actor.id,
                    tenant_id=tid,
                )
                db.add(project)
                db.flush()
                if auto_ai:
                    from app.content_ai_draft import generate_draft_for_project

                    try:
                        generate_draft_for_project(db, project, task, node, row, retry=False)
                    except Exception:
                        project.ai_generate_status = "FAILED"
                        project.ai_generate_error = "AI 文案生成失败"
        row.row_status = "CONFIRMED"
    sheet.status = "CONFIRMED"
    sheet.confirmed_at = iso(datetime.now(BJ))
    db.flush()
    return ok(
        {
            "sheetId": sheet.id,
            "generatedTaskCount": generated,
            "confirmedAt": sheet.confirmed_at,
            "autoAiGenerate": auto_ai,
        }
    )


@router.post("/{sheet_id}/withdraw")
def sheet_withdraw(
    sheet_id: int,
    body: ConfirmBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    sheet = load_sheet(db, sheet_id, actor)
    if sheet is None:
        return fail(1504, "资源不可用")
    if not body.assignmentIds:
        return fail(1500, "参数校验失败")
    tid = tenant(actor)
    for aid in body.assignmentIds:
        row = db.get(ContentWorkTaskAssignment, aid)
        if row is None or row.deleted or row.sheet_id != sheet.id:
            return fail(1504, "资源不可用")
        if row.row_status != "CONFIRMED":
            continue
        links = db.scalars(
            select(ContentWorkTaskAssignmentTask).where(
                ContentWorkTaskAssignmentTask.assignment_id == row.id,
                ContentWorkTaskAssignmentTask.tenant_id == tid,
            )
        ).all()
        for link in links:
            task = db.get(ContentTask, link.task_id)
            if task is None or task.deleted:
                continue
            if task.task_status in ("IN_PROGRESS", "COMPLETED"):
                return fail(1502, "业务规则冲突")
            task.task_status = "CANCELLED"
            task.visible_in_list = 0
            if task.id:
                projects = db.scalars(
                    select(ContentProject).where(
                        ContentProject.task_id == task.id,
                        ContentProject.deleted == 0,
                        ContentProject.tenant_id == tid,
                    )
                ).all()
                for project in projects:
                    if project.content_status == "DRAFT":
                        project.deleted = 1
            db.delete(link)
        row.row_status = "DRAFT"
    any_confirmed = db.scalar(
        select(ContentWorkTaskAssignment.id).where(
            ContentWorkTaskAssignment.sheet_id == sheet.id,
            ContentWorkTaskAssignment.deleted == 0,
            ContentWorkTaskAssignment.row_status == "CONFIRMED",
        )
    )
    if any_confirmed is None:
        sheet.status = "DRAFT"
        sheet.confirmed_at = None
    db.flush()
    return ok(sheet_vo(db, ops, sheet))
