"""CONTENT-107 公推模板库（W9-4 首片）。"""

from __future__ import annotations

import html
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of
from app.models import ContentLayoutImportJob, ContentLayoutTemplate, User

router = APIRouter(prefix="/content/layout-template", tags=["content-layout"])

BJ = timezone(timedelta(hours=8))
STATUSES = frozenset({"DRAFT", "ENABLED", "DISABLED"})
SOURCES = frozenset({"PRESET", "CUSTOM", "IMPORT"})


class LayoutBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateName: str
    previewHtml: str = ""
    source: str = "CUSTOM"
    documentType: str | None = None
    tags: str | None = None


class ImportUrlBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    url: str = ""
    templateName: str = ""


class ImportPasteBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    templateName: str = ""
    html: str = ""


def new_job_id() -> str:
    return f"IMP{secrets.token_hex(4)}"


def record_job(
    db: Session,
    actor: User,
    *,
    channel: str,
    status: str,
    template_id: int = 0,
    template_name: str = "",
    message: str = "",
) -> str:
    job_no = new_job_id()
    db.add(
        ContentLayoutImportJob(
            job_no=job_no,
            channel=channel,
            status=status,
            template_id=template_id or 0,
            template_name=(template_name or "")[:128],
            message=(message or "")[:256],
            created_by=actor.id,
            tenant_id=tenant_of(actor),
        )
    )
    db.flush()
    return job_no


def job_vo(row: ContentLayoutImportJob) -> dict:
    return {
        "jobId": row.job_no,
        "channel": row.channel,
        "status": row.status,
        "templateId": row.template_id or None,
        "templateName": row.template_name,
        "message": row.message,
        "createdAt": iso(row.created_at),
    }


def load_layout(db: Session, template_id: int, tenant_id: int) -> ContentLayoutTemplate | None:
    row = db.get(ContentLayoutTemplate, template_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    return row


def new_import_template(
    db: Session,
    actor: User,
    *,
    name: str,
    preview_html: str,
) -> ContentLayoutTemplate:
    tenant_id = tenant_of(actor)
    row = ContentLayoutTemplate(
        template_no=next_template_no(db, tenant_id),
        template_name=name[:128],
        source="IMPORT",
        status="DRAFT",
        preview_html=preview_html,
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return row


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


def creator_name(db: Session, user_id: int) -> str:
    if not user_id:
        return ""
    user = db.get(User, int(user_id))
    if user is None:
        return ""
    return (user.nickname or user.username or "").strip()


def creator_names(db: Session, user_ids: set[int]) -> dict[int, str]:
    wanted = {int(item) for item in user_ids if int(item) > 0}
    if not wanted:
        return {}
    rows = db.scalars(select(User).where(User.id.in_(wanted))).all()
    return {row.id: (row.nickname or row.username or "").strip() for row in rows}


def layout_vo(row: ContentLayoutTemplate, creator: str = "") -> dict:
    return {
        "id": row.id,
        "templateNo": row.template_no,
        "templateName": row.template_name,
        "source": row.source,
        "status": row.status,
        "documentType": row.document_type or "",
        "tags": row.tags or "",
        "previewHtml": row.preview_html or "",
        "layoutJson": row.layout_json or "",
        "presetCode": row.preset_code or "",
        "usageCount": row.usage_count,
        "creatorName": creator,
        "createdAt": iso(row.created_at),
        "updatedAt": iso(row.updated_at),
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
    names = creator_names(db, {row.created_by for row in rows})
    return paged([layout_vo(row, names.get(row.created_by, "")) for row in rows], total, page_no, size)


@router.post("")
def create_layout(
    body: LayoutBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = body.templateName.strip()
    if not name:
        return fail(1001, "必填项，请填写")
    src = body.source if body.source in SOURCES else "CUSTOM"
    tenant_id = tenant_of(actor)
    row = ContentLayoutTemplate(
        template_no=next_template_no(db, tenant_id),
        template_name=name,
        source=src,
        status="DRAFT",
        preview_html=body.previewHtml or "",
        document_type=(body.documentType or "").strip()[:32],
        tags=(body.tags or "").strip()[:256],
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(layout_vo(row, creator_name(db, actor.id)))


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
    return ok(layout_vo(row, creator_name(db, row.created_by)))


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
        return fail(1001, "必填项，请填写")
    row.template_name = name[:128]
    row.preview_html = body.previewHtml or ""
    if body.documentType is not None:
        row.document_type = body.documentType.strip()[:32]
    if body.tags is not None:
        row.tags = body.tags.strip()[:256]
    row.updated_at = utcnow()
    db.flush()
    return ok(layout_vo(row, creator_name(db, row.created_by)))


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
    return ok(layout_vo(row, creator_name(db, row.created_by)))


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
    return ok(layout_vo(row, creator_name(db, row.created_by)))


@router.get("/import-job/list")
def import_job_list(
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    rows = db.scalars(
        select(ContentLayoutImportJob)
        .where(ContentLayoutImportJob.deleted == 0, ContentLayoutImportJob.tenant_id == tenant_id)
        .order_by(ContentLayoutImportJob.id.desc())
        .limit(50)
    ).all()
    return ok({"list": [job_vo(row) for row in rows]})


@router.post("/import-url")
def import_layout_url(
    body: ImportUrlBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    """公众号链接抓取桩：不生成模板，失败任务仍可在列表查看。"""
    url = (body.url or "").strip()
    if not url:
        return fail(1001, "必填项，请填写")
    message = "公众号链接抓取失败，请改用 MHTML 或粘贴 HTML"
    job_no = record_job(
        db,
        actor,
        channel="url",
        status="FAILED",
        template_name=(body.templateName or "").strip(),
        message=message,
    )
    return fail(1500, message, {"jobId": job_no, "status": "FAILED"})


@router.post("/import-paste")
def import_layout_paste(
    body: ImportPasteBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = (body.templateName or "").strip()
    raw = (body.html or "").strip()
    if not name or not raw:
        return fail(1001, "必填项，请填写")
    row = new_import_template(db, actor, name=name, preview_html=raw)
    job_no = record_job(
        db,
        actor,
        channel="html",
        status="SUCCESS",
        template_id=row.id,
        template_name=row.template_name,
        message="导入成功",
    )
    return ok({"jobId": job_no, "template": layout_vo(row, creator_name(db, row.created_by))})


@router.post("/import-mhtml")
async def import_layout_mhtml(
    file: UploadFile | None = File(default=None),
    templateName: str = Form(default=""),
    overrideId: int | None = Form(default=None),
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    if file is None or not (file.filename or "").strip():
        return fail(1001, "必填项，请填写")
    filename = file.filename or ""
    if not filename.lower().endswith((".mhtml", ".mht")):
        return fail(1001, "请上传 .mhtml 文件")
    raw = await file.read()
    if not raw:
        return fail(1001, "必填项，请填写")
    text = raw.decode("utf-8", errors="ignore")
    preview = f"<pre>{html.escape(text[:4000])}</pre>"
    tenant_id = tenant_of(actor)
    name = (templateName or "").strip() or filename.rsplit(".", 1)[0]
    if overrideId:
        row = load_layout(db, int(overrideId), tenant_id)
        if row is None:
            return fail(1500, "模板不存在")
        if row.source == "PRESET":
            return fail(1001, "预置模板不可覆盖")
        row.preview_html = preview
        if (templateName or "").strip():
            row.template_name = name[:128]
        row.updated_at = utcnow()
        db.flush()
    else:
        row = new_import_template(db, actor, name=name, preview_html=preview)
    job_no = record_job(
        db,
        actor,
        channel="mhtml",
        status="SUCCESS",
        template_id=row.id,
        template_name=row.template_name,
        message="导入成功",
    )
    return ok({"jobId": job_no, "template": layout_vo(row, creator_name(db, row.created_by))})


@router.post("/{template_id}/copy")
def copy_layout(
    template_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    src = load_layout(db, template_id, tenant_id)
    if src is None:
        return fail(1500, "模板不存在")
    name = f"{src.template_name}（副本）"[:128]
    row = ContentLayoutTemplate(
        template_no=next_template_no(db, tenant_id),
        template_name=name,
        source="CUSTOM",
        status="DRAFT",
        preview_html=src.preview_html or "",
        layout_json=src.layout_json or "",
        preset_code="",
        document_type=src.document_type or "",
        tags=src.tags or "",
        created_by=actor.id,
        tenant_id=tenant_id,
    )
    db.add(row)
    db.flush()
    return ok(layout_vo(row, creator_name(db, actor.id)))


@router.delete("/{template_id}")
def delete_layout(
    template_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = load_layout(db, template_id, tenant_id)
    if row is None:
        return fail(1500, "模板不存在")
    if row.source == "PRESET":
        return fail(1001, "预置模板不可删除")
    row.deleted = 1
    row.updated_at = utcnow()
    return ok(None)
