"""CONTENT-109/110 · Football 方案同步与补偿队列（BR-303）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content import iso
from app.core import utcnow
from app.football_client import sync_article_shelf_off, sync_article_upsert
from app.models import (
    ContentFbSyncOutbox,
    ContentProject,
    ContentTask,
    ContentWorkTaskAssignment,
)
from app.ops_models import AuthorUser

BJ = timezone(timedelta(hours=8))
MAX_FB_RETRIES = 3
BACKOFF_MINUTES = (1, 5, 15)


def resolve_author_id(db: Session, ops: Session, project: ContentProject) -> str:
    if project.task_id:
        task = db.get(ContentTask, project.task_id)
        if task is not None and task.assignment_id:
            assign = db.get(ContentWorkTaskAssignment, task.assignment_id)
            if assign is not None and assign.author_id:
                return str(assign.author_id)
    if project.ip_group_id:
        author = ops.scalar(
            select(AuthorUser).where(
                AuthorUser.ip_group_id == project.ip_group_id,
                AuthorUser.deleted == 0,
                AuthorUser.status == "ENABLED",
            ).order_by(AuthorUser.id.asc())
        )
        if author is not None:
            return str(author.id)
    return str(project.submitter_user_id or project.creator or 0)


def fb_sync_vo(project: ContentProject, pending: int = 0) -> dict:
    status = project.fb_sync_status or "NONE"
    label = {
        "NONE": "未同步",
        "PENDING": "待同步",
        "SYNCED": "成功",
        "COMPENSATING": "补偿中",
        "FAILED": "失败",
    }.get(status, status)
    return {
        "contentProjectId": project.id,
        "authorArticleId": project.author_article_id,
        "fbSyncStatus": status,
        "fbSyncStatusLabel": label,
        "lastSyncAt": project.last_fb_sync_at,
        "lastError": project.last_fb_sync_error,
        "pendingOutboxCount": pending,
        "footballEnrichment": None,
    }


def outbox_vo(row: ContentFbSyncOutbox, title: str = "") -> dict:
    return {
        "id": row.id,
        "contentProjectId": row.content_project_id,
        "contentTitle": title,
        "action": row.action,
        "syncStatus": row.sync_status,
        "retryCount": row.retry_count,
        "lastErrorCode": row.last_error_code,
        "lastErrorMsg": row.last_error_msg,
        "deadLetter": bool(row.dead_letter),
        "nextRetryAt": iso(row.next_retry_at) if row.next_retry_at else "",
        "createdAt": iso(row.created_at),
    }


def pending_count(db: Session, tenant_id: int, content_id: int) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(ContentFbSyncOutbox).where(
                ContentFbSyncOutbox.tenant_id == tenant_id,
                ContentFbSyncOutbox.content_project_id == content_id,
                ContentFbSyncOutbox.sync_status == "PENDING",
                ContentFbSyncOutbox.dead_letter == 0,
            )
        )
        or 0
    )


def build_upsert_payload(db: Session, ops: Session, project: ContentProject) -> dict:
    return {
        "contentId": project.id,
        "authorId": resolve_author_id(db, ops, project),
        "title": project.title,
        "content": project.body or project.layout_html or "",
        "existingArticleId": project.author_article_id,
        "status": -1,
    }


def schedule_next_retry(row: ContentFbSyncOutbox) -> None:
    idx = min(row.retry_count, len(BACKOFF_MINUTES) - 1)
    row.next_retry_at = utcnow() + timedelta(minutes=BACKOFF_MINUTES[idx])


def apply_outbox_success(db: Session, project: ContentProject, row: ContentFbSyncOutbox, article_id: str | None) -> None:
    row.sync_status = "SUCCESS"
    row.last_error_code = None
    row.last_error_msg = None
    row.updated_at = utcnow()
    if row.action == "UPSERT" and article_id:
        project.author_article_id = article_id
    db.flush()
    pending = pending_count(db, project.tenant_id or 0, project.id)
    if pending == 0:
        project.fb_sync_status = "SYNCED"
    project.last_fb_sync_at = datetime.now(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    project.last_fb_sync_error = None


def apply_outbox_failure(
    db: Session,
    project: ContentProject,
    row: ContentFbSyncOutbox,
    err_code: int,
    err_msg: str,
) -> None:
    row.retry_count += 1
    row.last_error_code = err_code
    row.last_error_msg = (err_msg or "")[:512]
    row.updated_at = utcnow()
    project.last_fb_sync_error = row.last_error_msg
    if row.retry_count >= MAX_FB_RETRIES:
        row.sync_status = "FAILED"
        row.dead_letter = 1
        project.fb_sync_status = "FAILED"
        return
    row.sync_status = "PENDING"
    schedule_next_retry(row)
    project.fb_sync_status = "COMPENSATING"


def execute_outbox_row(db: Session, ops: Session, row: ContentFbSyncOutbox) -> None:
    project = db.get(ContentProject, row.content_project_id)
    if project is None or project.deleted and row.action == "UPSERT":
        row.sync_status = "SUCCESS"
        row.updated_at = utcnow()
        return
    payload = row.payload_json or {}
    if row.action == "SHELF_OFF":
        article_id = payload.get("articleId") or project.author_article_id
        if not article_id:
            row.sync_status = "SUCCESS"
            row.updated_at = utcnow()
            return
        ok, err_code, err_msg = sync_article_shelf_off(str(article_id))
    else:
        ok, article_id, err_code, err_msg = sync_article_upsert(payload)
    if ok:
        apply_outbox_success(db, project, row, article_id)
    else:
        apply_outbox_failure(db, project, row, err_code or 1271, err_msg or "同步失败")


def enqueue_outbox(
    db: Session,
    ops: Session,
    project: ContentProject,
    action: str,
    actor_id: int,
    *,
    try_immediate: bool = True,
) -> ContentFbSyncOutbox | None:
    tid = project.tenant_id or 0
    if action == "UPSERT":
        project.fb_sync_version = (project.fb_sync_version or 0) + 1
        idem = f"content:{tid}:{project.id}:upsert:v{project.fb_sync_version}"
        payload = build_upsert_payload(db, ops, project)
    else:
        idem = f"content:{tid}:{project.id}:shelf_off:v{project.fb_sync_version or 0}"
        payload = {"articleId": project.author_article_id, "contentId": project.id}
        if not project.author_article_id:
            return None
    existing = db.scalar(
        select(ContentFbSyncOutbox).where(
            ContentFbSyncOutbox.tenant_id == tid,
            ContentFbSyncOutbox.idempotency_key == idem,
        )
    )
    if existing is not None:
        row = existing
    else:
        row = ContentFbSyncOutbox(
            content_project_id=project.id,
            action=action,
            idempotency_key=idem,
            payload_json=payload,
            sync_status="PENDING",
            creator=actor_id,
            tenant_id=tid,
        )
        db.add(row)
        db.flush()
    if try_immediate and row.sync_status == "PENDING" and row.dead_letter == 0:
        if action == "UPSERT":
            project.fb_sync_status = "PENDING"
        execute_outbox_row(db, ops, row)
    elif row.sync_status == "PENDING":
        project.fb_sync_status = "COMPENSATING" if action == "UPSERT" else project.fb_sync_status
    return row


def after_content_saved(db: Session, ops: Session, project: ContentProject, actor_id: int) -> None:
    enqueue_outbox(db, ops, project, "UPSERT", actor_id, try_immediate=True)


def after_content_deleted(db: Session, ops: Session, project: ContentProject, actor_id: int) -> None:
    if project.author_article_id:
        enqueue_outbox(db, ops, project, "SHELF_OFF", actor_id, try_immediate=True)


def process_due_outbox(db: Session, ops: Session, limit: int = 20) -> int:
    now = utcnow()
    rows = db.scalars(
        select(ContentFbSyncOutbox)
        .where(
            ContentFbSyncOutbox.sync_status == "PENDING",
            ContentFbSyncOutbox.dead_letter == 0,
            ContentFbSyncOutbox.retry_count > 0,
            ContentFbSyncOutbox.next_retry_at.is_not(None),
            ContentFbSyncOutbox.next_retry_at <= now,
        )
        .order_by(ContentFbSyncOutbox.id.asc())
        .limit(limit)
    ).all()
    for row in rows:
        execute_outbox_row(db, ops, row)
    return len(rows)
