"""CONTENT-107 公推模板库（W9-4 首片）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import ContentLayoutTemplate, User

router = APIRouter(prefix="/content/layout-template", tags=["content-layout"])

BJ = timezone(timedelta(hours=8))
STATUSES = frozenset({"DRAFT", "ENABLED", "DISABLED"})
SOURCES = frozenset({"PRESET", "CUSTOM", "IMPORT"})


class LayoutBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateName: str
    previewHtml: str = ""
    source: str = "CUSTOM"


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_template_no(db: Session, tenant_id: int) -> str:
    day = datetime.now(BJ).strftime("%Y%m%d")
    prefix = f"LT{day}"
    count = db.scalar(
        select(func.count())
        .select_from(ContentLayoutTemplate)
        .where(
            ContentLayoutTemplate.deleted == 0,
            ContentLayoutTemplate.tenant_id == tenant_id,
            ContentLayoutTemplate.template_no.like(f"{prefix}%"),
        )
    )
    seq = int(count or 0) + 1
    return f"{prefix}{seq:03d}"


def layout_vo(row: ContentLayoutTemplate) -> dict:
    return {
        "id": row.id,
        "templateNo": row.template_no,
        "templateName": row.template_name,
        "source": row.source,
        "status": row.status,
        "previewHtml": row.preview_html or "",
        "layoutJson": row.layout_json or "",
        "presetCode": row.preset_code or "",
        "usageCount": row.usage_count,
        "createdAt": iso(row.created_at),
    }


@router.get("/list")
def layout_list(
    templateName: str | None = None,
    status: str | None = None,
    source: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(ContentLayoutTemplate).where(
        ContentLayoutTemplate.deleted == 0,
        ContentLayoutTemplate.tenant_id == tenant_id,
    )
    if templateName:
        stmt = stmt.where(ContentLayoutTemplate.template_name.contains(templateName.strip()))
    if status:
        if status not in STATUSES:
            return fail(1001, "status 无效")
        stmt = stmt.where(ContentLayoutTemplate.status == status)
    if source:
        if source not in SOURCES:
            return fail(1001, "source 无效")
        stmt = stmt.where(ContentLayoutTemplate.source == source)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(ContentLayoutTemplate.status.desc(), ContentLayoutTemplate.id.desc())
            .offset((page_no - 1) * size)
            .limit(size)
        ).all()
    )
    return paged([layout_vo(row) for row in rows], total, page_no, size)


@router.post("")
def create_layout(
    body: LayoutBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = body.templateName.strip()
    if not name:
        return fail(1001, "templateName 必填")
    src = body.source if body.source in SOURCES else "CUSTOM"
    tenant_id = tenant_of(actor)
    row = ContentLayoutTemplate(
        template_no=next_template_no(db, tenant_id),
        template_name=name,
        source=src,
        status="DRAFT",
        preview_html=body.previewHtml or "",
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(layout_vo(row))


@router.get("/{template_id}")
def layout_detail(
    template_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(ContentLayoutTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "模板不存在")
    return ok(layout_vo(row))


@router.put("/{template_id}")
def update_layout(
    template_id: int,
    body: LayoutBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(ContentLayoutTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "模板不存在")
    if row.source == "PRESET":
        return fail(1001, "预置模板不可编辑")
    name = body.templateName.strip()
    if not name:
        return fail(1001, "templateName 必填")
    row.template_name = name[:128]
    row.preview_html = body.previewHtml or ""
    row.updated_at = utcnow()
    db.flush()
    return ok(layout_vo(row))


@router.post("/{template_id}/publish")
def publish_layout(
    template_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(ContentLayoutTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "模板不存在")
    if row.source == "PRESET":
        return fail(1001, "预置模板不可直接发布")
    row.status = "ENABLED"
    row.updated_at = utcnow()
    db.flush()
    return ok(layout_vo(row))


@router.put("/{template_id}/enable")
def enable_layout(
    template_id: int,
    enabled: bool = True,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(ContentLayoutTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1500, "模板不存在")
    row.status = "ENABLED" if enabled else "DISABLED"
    row.updated_at = utcnow()
    db.flush()
    return ok(layout_vo(row))
