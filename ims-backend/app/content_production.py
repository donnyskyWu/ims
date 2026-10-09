from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import iso, next_seq, tenant
from app.content_fb_sync import after_content_deleted, after_content_saved, fb_sync_vo
from app.content_task import APPROVED_CONTENT_STATUSES
from app.corp import ops_db, page_args, paged
from app.models import ContentProject, ContentReview, ContentReviewSeq, ContentTask, User

router = APIRouter(prefix="/content", tags=["content-production"])


class ContentSaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    contentType: str = "SHORT_VIDEO"
    platformType: str = ""
    body: str = ""
    layoutHtml: str = ""
    documentType: str = ""
    taskId: int | None = None
    ipGroupId: int | None = None
    matchType: int | None = None
    matchScheme: list[dict] = Field(default_factory=list)
    competitionId: str | None = None
    competitionName: str | None = None


def match_summary(scheme: list) -> str:
    if not scheme:
        return ""
    if len(scheme) == 1:
        item = scheme[0]
        home = item.get("homeName") or ""
        away = item.get("awayName") or ""
        if home or away:
            return f"{home} VS {away}".strip()
    return f"{len(scheme)}场"


def apply_match_fields(project: ContentProject, body: ContentSaveBody) -> None:
    scheme = body.matchScheme or []
    project.match_type = body.matchType
    project.match_scheme = scheme
    project.match_summary = match_summary(scheme)
    if scheme:
        first = scheme[0]
        project.competition_id = str(first.get("matchId") or first.get("scheduleId") or body.competitionId or "")
        if not project.competition_name:
            project.competition_name = match_summary(scheme)
    elif body.competitionId:
        project.competition_id = body.competitionId[:64]
    if body.competitionName:
        project.competition_name = body.competitionName[:256]


def project_vo(row: ContentProject) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "contentType": row.content_type,
        "platformType": row.platform_type,
        "documentType": row.document_type,
        "contentStatus": row.content_status,
        "taskId": row.task_id,
        "ipGroupId": row.ip_group_id,
        "body": row.body,
        "layoutHtml": row.layout_html,
        "matchType": row.match_type,
        "matchScheme": row.match_scheme or [],
        "matchSummary": row.match_summary or row.competition_name,
        "competitionId": row.competition_id,
        "competitionName": row.competition_name,
        "aiGenerateStatus": row.ai_generate_status,
        "aiGenerateError": row.ai_generate_error,
        "reviewPassed": bool(row.review_passed),
        "authorArticleId": row.author_article_id,
        "fbSyncStatus": row.fb_sync_status or "NONE",
        "fbSyncStatusLabel": fb_sync_vo(row, 0)["fbSyncStatusLabel"],
        "lastFbSyncAt": row.last_fb_sync_at,
        "createdAt": iso(row.created_at),
    }


def load_project(db: Session, content_id: int, actor: User) -> ContentProject | None:
    row = db.get(ContentProject, content_id)
    if row is None or row.deleted or (row.tenant_id or 0) != tenant(actor):
        return None
    return row


@router.get("")
def content_list(
    pageNo: int = 1,
    pageSize: int = 10,
    title: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentProject).where(ContentProject.deleted == 0, ContentProject.tenant_id == tenant(actor))
    if title:
        stmt = stmt.where(ContentProject.title.contains(title.strip()))
    if status:
        stmt = stmt.where(ContentProject.content_status == status.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(ContentProject.id.desc()).offset((page_no - 1) * size).limit(size)
    ).all()
    return paged([project_vo(row) for row in rows], total, page_no, size)


@router.get("/{content_id}")
def content_detail(content_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    return ok(project_vo(row))


@router.post("")
def content_create(
    body: ContentSaveBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    title = (body.title or "").strip()
    if not title or len(title) > 200:
        return fail(1500, "参数校验失败")
    tid = tenant(actor)
    if body.taskId is not None:
        task = db.get(ContentTask, body.taskId)
        if task is None or task.deleted or (task.tenant_id or 0) != tid:
            return fail(1500, "参数校验失败")
        existing = db.scalar(
            select(ContentProject).where(
                ContentProject.task_id == body.taskId,
                ContentProject.deleted == 0,
                ContentProject.tenant_id == tid,
            )
        )
        if existing is not None:
            return fail(1502, "业务规则冲突")
    row = ContentProject(
        title=title,
        content_type=(body.contentType or "SHORT_VIDEO")[:32],
        platform_type=(body.platformType or "")[:32],
        document_type=(body.documentType or "")[:32],
        body=body.body or "",
        layout_html=body.layoutHtml or "",
        task_id=body.taskId,
        ip_group_id=body.ipGroupId,
        content_status="DRAFT",
        submitter_user_id=actor.id,
        creator=actor.id,
        tenant_id=tid,
    )
    apply_match_fields(row, body)
    db.add(row)
    db.flush()
    after_content_saved(db, ops, row, actor.id)
    return ok(project_vo(row))


@router.put("/{content_id}")
def content_update(
    content_id: int,
    body: ContentSaveBody,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.content_status not in ("DRAFT", "REJECTED"):
        return fail(1502, "业务规则冲突")
    title = (body.title or row.title).strip()
    if not title:
        return fail(1500, "参数校验失败")
    row.title = title[:256]
    if body.contentType:
        row.content_type = body.contentType[:32]
    if body.platformType is not None:
        row.platform_type = body.platformType[:32]
    if "documentType" in body.model_fields_set and body.documentType is not None:
        row.document_type = body.documentType[:32]
    # 未显式提交 body / layoutHtml 时保留已有正文与版式。文案采纳只写 body，不顺带清空排版。
    if "body" in body.model_fields_set and body.body is not None:
        row.body = body.body
    if "layoutHtml" in body.model_fields_set:
        row.layout_html = body.layoutHtml
    if body.ipGroupId is not None:
        row.ip_group_id = body.ipGroupId
    apply_match_fields(row, body)
    db.flush()
    after_content_saved(db, ops, row, actor.id)
    return ok(project_vo(row))


@router.delete("/{content_id}")
def content_delete(
    content_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.content_status not in ("DRAFT", "REJECTED"):
        return fail(1502, "业务规则冲突")
    after_content_deleted(db, ops, row, actor.id)
    row.deleted = 1
    return ok(None)


@router.post("/{content_id}/submit-review")
def content_submit_review(content_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    if row.content_status not in ("DRAFT", "REJECTED"):
        return fail(1502, "业务规则冲突")
    pending = db.scalar(
        select(ContentReview.id).where(
            ContentReview.content_project_id == row.id,
            ContentReview.deleted == 0,
            ContentReview.conclusion.is_(None),
        )
    )
    if pending is not None:
        return fail(1502, "业务规则冲突")
    review_no = next_seq(db, ContentReviewSeq, tenant(actor), "RV")
    db.add(
        ContentReview(
            review_no=review_no,
            content_project_id=row.id,
            content_title=row.title,
            submitter_user_id=row.submitter_user_id,
            review_round=1,
            creator=actor.id,
            tenant_id=tenant(actor),
        )
    )
    row.content_status = "PENDING_REVIEW"
    row.review_passed = 0
    return ok({"reviewNo": review_no, "contentStatus": row.content_status})


@router.post("/{content_id}/retry-ai-generate")
def content_retry_ai(content_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    status = row.ai_generate_status
    if status in ("GENERATED", "GENERATING"):
        return ok({"aiGenerateStatus": status, "aiGenerateError": row.ai_generate_error})
    if status not in ("FAILED", "QUEUED"):
        return fail(1502, "业务规则冲突")
    from app.content_ai_draft import retry_project_draft

    try:
        retry_project_draft(db, row)
    except Exception:
        row.ai_generate_status = "FAILED"
        row.ai_generate_error = "AI 文案生成失败"
    return ok({"aiGenerateStatus": row.ai_generate_status, "aiGenerateError": row.ai_generate_error})
