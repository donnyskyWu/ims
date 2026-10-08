from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.content import tenant
from app.content_fb_sync import (
    after_content_saved,
    enqueue_outbox,
    execute_outbox_row,
    fb_sync_vo,
    outbox_vo,
    pending_count,
    process_due_outbox,
)
from app.content_production import load_project
from app.corp import ops_db, page_args, paged
from app.models import ContentFbSyncOutbox, ContentProject, User

router = APIRouter(prefix="/content", tags=["content-fb-sync"])


@router.get("/fb-sync/outbox/page")
def outbox_page(
    pageNo: int = 1,
    pageSize: int = 10,
    syncStatus: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    page_no, size = page_args(pageNo, pageSize)
    tid = tenant(actor)
    stmt = select(ContentFbSyncOutbox).where(ContentFbSyncOutbox.tenant_id == tid)
    if syncStatus:
        stmt = stmt.where(ContentFbSyncOutbox.sync_status == syncStatus.strip())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(ContentFbSyncOutbox.id.desc()).offset((page_no - 1) * size).limit(size)
    ).all()
    titles: dict[int, str] = {}
    if rows:
        ids = [r.content_project_id for r in rows]
        for proj in db.scalars(select(ContentProject).where(ContentProject.id.in_(ids))).all():
            titles[proj.id] = proj.title
    return paged([outbox_vo(r, titles.get(r.content_project_id, "")) for r in rows], total, page_no, size)


@router.post("/fb-sync/outbox/{outbox_id}/retry")
def outbox_retry(
    outbox_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = db.get(ContentFbSyncOutbox, outbox_id)
    if row is None or (row.tenant_id or 0) != tenant(actor):
        return fail(1504, "资源不可用")
    if row.dead_letter:
        return fail(1502, "业务规则冲突")
    row.sync_status = "PENDING"
    row.retry_count = 0
    row.next_retry_at = None
    row.dead_letter = 0
    execute_outbox_row(db, ops, row)
    project = db.get(ContentProject, row.content_project_id)
    pending = pending_count(db, tenant(actor), row.content_project_id) if project else 0
    return ok(
        {
            "outbox": outbox_vo(row, project.title if project else ""),
            "fbSync": fb_sync_vo(project, pending) if project else None,
        }
    )


@router.post("/fb-sync/process-due")
def outbox_process_due(
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    count = process_due_outbox(db, ops)
    return ok({"processed": count})


@router.get("/{content_id}/fb-sync")
def content_fb_sync_status(
    content_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    pending = pending_count(db, tenant(actor), row.id)
    return ok(fb_sync_vo(row, pending))


@router.post("/{content_id}/fb-sync")
def content_fb_sync_retry(
    content_id: int,
    db: Session = Depends(db_session),
    ops: Session = Depends(ops_db),
    actor: User = Depends(current_user),
):
    row = load_project(db, content_id, actor)
    if row is None:
        return fail(1504, "资源不可用")
    enqueue_outbox(db, ops, row, "UPSERT", actor.id, try_immediate=True)
    pending = pending_count(db, tenant(actor), row.id)
    return ok(fb_sync_vo(row, pending))
