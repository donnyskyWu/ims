"""AIR 知识库文件管理（KNOW-002/005 · 无检索）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirKb, AirKbCategory, AirKbDoc

router = APIRouter(prefix="/air", tags=["air"])

BJ = timezone(timedelta(hours=8))


class KbUploadBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str
    fileKey: str
    contentType: str = "application/octet-stream"
    fileSize: int = 0
    kbId: int = 0
    cateId: int = 0


class KbCategoryBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbId: int
    parentId: int | None = None
    categoryName: str
    sortNo: int | None = None


class KbAuditBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    docId: int
    approve: bool
    auditNote: str = ""


def kb_doc_vo(row: AirKbDoc, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "kbId": row.kb_id,
        "title": row.title,
        "fileKey": row.file_key,
        "contentType": row.content_type,
        "fileSize": int(row.file_size or 0),
        "cateId": row.cate_id,
        "auditStatus": row.audit_status,
        "uploaderUserId": row.uploader_user_id,
        "uploaderName": names.get(row.uploader_user_id, ""),
        "createdAt": row.created_at.strftime("%Y-%m-%dT%H:%M:%S+08:00") if row.created_at else "",
    }


def ensure_default_kb(db: Session, tenant_id: int, owner_user_id: int) -> AirKb:
    row = db.scalar(
        select(AirKb).where(AirKb.deleted == 0, AirKb.tenant_id == tenant_id).order_by(AirKb.id.asc())
    )
    if row is not None:
        return row
    now = utcnow()
    row = AirKb(
        kb_name="默认知识库",
        secret_level="INTERNAL",
        owner_user_id=owner_user_id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def ensure_default_categories(db: Session, kb_id: int, tenant_id: int) -> None:
    count = db.scalar(
        select(func.count())
        .select_from(AirKbCategory)
        .where(AirKbCategory.deleted == 0, AirKbCategory.tenant_id == tenant_id, AirKbCategory.kb_id == kb_id)
    )
    if count:
        return
    now = utcnow()
    seeds = [
        ("制度规范", ["人事制度", "财务制度"]),
        ("业务资料", ["SOP", "案例库"]),
    ]
    sort = 0
    for parent_name, children in seeds:
        sort += 1
        parent = AirKbCategory(
            kb_id=kb_id,
            category_name=parent_name,
            parent_id=None,
            sort_no=sort,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(parent)
        db.flush()
        for idx, child_name in enumerate(children, start=1):
            db.add(
                AirKbCategory(
                    kb_id=kb_id,
                    category_name=child_name,
                    parent_id=parent.id,
                    sort_no=idx,
                    tenant_id=tenant_id,
                    created_at=now,
                    updated_at=now,
                )
            )
    db.flush()


def cate_doc_count(db: Session, cate_id: int, tenant_id: int, kb_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AirKbDoc)
            .where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.kb_id == kb_id,
                AirKbDoc.cate_id == cate_id,
                AirKbDoc.audit_status == "PUBLISHED",
            )
        )
        or 0
    )


def build_category_nodes(db: Session, kb_id: int, tenant_id: int) -> list[dict]:
    rows = list(
        db.scalars(
            select(AirKbCategory)
            .where(
                AirKbCategory.deleted == 0,
                AirKbCategory.tenant_id == tenant_id,
                AirKbCategory.kb_id == kb_id,
            )
            .order_by(AirKbCategory.sort_no.asc(), AirKbCategory.id.asc())
        ).all()
    )
    by_parent: dict[int | None, list[AirKbCategory]] = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def build(node: AirKbCategory) -> dict:
        children = [build(item) for item in by_parent.get(node.id, [])]
        doc_count = cate_doc_count(db, node.id, tenant_id, kb_id)
        for child in children:
            doc_count += child.get("docCount", 0)
        return {
            "id": node.id,
            "categoryName": node.category_name,
            "parentId": node.parent_id,
            "sortNo": node.sort_no,
            "docCount": doc_count,
            "children": children,
        }

    return [build(item) for item in by_parent.get(None, [])]


@router.get("/kb/tree")
def kb_tree(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    kb = ensure_default_kb(db, tenant_id, actor.id)
    ensure_default_categories(db, kb.id, tenant_id)
    children = build_category_nodes(db, kb.id, tenant_id)
    doc_total = int(
        db.scalar(
            select(func.count())
            .select_from(AirKbDoc)
            .where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.kb_id == kb.id,
                AirKbDoc.audit_status == "PUBLISHED",
            )
        )
        or 0
    )
    return ok(
        [
            {
                "id": kb.id,
                "kbName": kb.kb_name,
                "secretLevel": kb.secret_level,
                "docCount": doc_total,
                "children": children,
            }
        ]
    )


@router.get("/kb/category/tree")
def kb_category_tree(
    kbId: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    kb = db.get(AirKb, kbId)
    if kb is None or kb.deleted or kb.tenant_id != tenant_id:
        kb = ensure_default_kb(db, tenant_id, actor.id)
    ensure_default_categories(db, kb.id, tenant_id)
    return ok(build_category_nodes(db, kb.id, tenant_id))


@router.post("/kb/category")
def kb_category_create(
    body: KbCategoryBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = (body.categoryName or "").strip()
    if not name:
        return fail(1001, "categoryName 必填")
    tenant_id = tenant_of(actor)
    kb = db.get(AirKb, body.kbId)
    if kb is None or kb.deleted or kb.tenant_id != tenant_id:
        return fail(1004, "知识库不存在")
    parent_id = body.parentId or None
    if parent_id:
        parent = db.get(AirKbCategory, parent_id)
        if parent is None or parent.deleted or parent.kb_id != kb.id or parent.tenant_id != tenant_id:
            return fail(1004, "父分类不存在")
        if parent.parent_id is not None:
            return fail(1001, "仅支持两级分类")
    dup = db.scalar(
        select(AirKbCategory.id).where(
            AirKbCategory.deleted == 0,
            AirKbCategory.tenant_id == tenant_id,
            AirKbCategory.kb_id == kb.id,
            AirKbCategory.parent_id == parent_id,
            AirKbCategory.category_name == name,
        )
    )
    if dup:
        return fail(1001, "同级分类名称重复")
    sort_no = body.sortNo
    if sort_no is None:
        sort_no = int(
            db.scalar(
                select(func.count())
                .select_from(AirKbCategory)
                .where(
                    AirKbCategory.deleted == 0,
                    AirKbCategory.kb_id == kb.id,
                    AirKbCategory.parent_id == parent_id,
                )
            )
            or 0
        ) + 1
    now = utcnow()
    row = AirKbCategory(
        kb_id=kb.id,
        category_name=name,
        parent_id=parent_id,
        sort_no=sort_no,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return ok({"categoryId": row.id, "sortNo": row.sort_no})


@router.get("/kb/page")
def kb_page(
    pageNo: int = 1,
    pageSize: int = 10,
    title: str = "",
    kbId: int | None = None,
    categoryId: int | None = None,
    docStatus: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    stmt = select(AirKbDoc).where(AirKbDoc.deleted == 0, AirKbDoc.tenant_id == tenant_id)
    if kbId:
        stmt = stmt.where(AirKbDoc.kb_id == kbId)
    if categoryId:
        stmt = stmt.where(AirKbDoc.cate_id == categoryId)
    if title.strip():
        stmt = stmt.where(AirKbDoc.title.like(f"%{title.strip()}%"))
    if docStatus:
        stmt = stmt.where(AirKbDoc.audit_status == docStatus)
    page_no, size = page_args(pageNo, pageSize)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(AirKbDoc.id.desc()).offset((page_no - 1) * size).limit(size)
        ).all()
    )
    names = user_names(db, {r.uploader_user_id for r in rows})
    return paged([kb_doc_vo(r, names) for r in rows], total, page_no, size)


@router.post("/kb/doc/upload")
def kb_doc_upload(
    body: KbUploadBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    title = (body.title or "").strip()
    file_key = (body.fileKey or "").strip()
    if not title:
        return fail(1001, "title 必填")
    if not file_key:
        return fail(1001, "fileKey 必填")
    now = utcnow()
    tenant_id = tenant_of(actor)
    kb = ensure_default_kb(db, tenant_id, actor.id)
    kb_id = int(body.kbId or kb.id)
    if kb_id != kb.id:
        other = db.get(AirKb, kb_id)
        if other is None or other.deleted or other.tenant_id != tenant_id:
            return fail(1004, "知识库不存在")
    cate_id = int(body.cateId or 0)
    if cate_id:
        cate = db.get(AirKbCategory, cate_id)
        if cate is None or cate.deleted or cate.kb_id != kb_id or cate.tenant_id != tenant_id:
            return fail(1004, "分类不存在")
    row = AirKbDoc(
        kb_id=kb_id,
        title=title,
        file_key=file_key,
        content_type=(body.contentType or "application/octet-stream").strip(),
        file_size=max(0, int(body.fileSize or 0)),
        cate_id=cate_id,
        audit_status="PENDING",
        uploader_user_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, {actor.id})
    return ok({"docIds": [row.id], "auditStatus": [row.audit_status], "doc": kb_doc_vo(row, names)})


@router.post("/kb/doc/audit")
def kb_doc_audit(
    body: KbAuditBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(AirKbDoc).where(
            AirKbDoc.deleted == 0,
            AirKbDoc.tenant_id == tenant_id,
            AirKbDoc.id == body.docId,
        )
    )
    if row is None:
        return fail(1004, "文档不存在")
    if row.audit_status != "PENDING":
        return fail(1001, "仅待审批文档可审批")
    if not body.approve and not (body.auditNote or "").strip():
        return fail(1001, "驳回须填写 auditNote")
    row.audit_status = "PUBLISHED" if body.approve else "DRAFT"
    row.updated_at = utcnow()
    db.flush()
    doc_status = "PUBLISHED" if body.approve else "DRAFT"
    return ok({"docId": row.id, "auditStatus": row.audit_status, "docStatus": doc_status})


@router.get("/kb/doc/{doc_id}/download")
def kb_doc_download(
    doc_id: int,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.scalar(
        select(AirKbDoc).where(
            AirKbDoc.deleted == 0,
            AirKbDoc.tenant_id == tenant_id,
            AirKbDoc.id == doc_id,
        )
    )
    if row is None:
        return fail(1004, "文档不存在")
    if row.audit_status != "PUBLISHED":
        return fail(1001, "未发布文档不可下载")
    return ok(
        {
            "docId": row.id,
            "fileKey": row.file_key,
            "contentType": row.content_type,
            "downloadUrl": f"/admin-api/ims/air/kb/files/{row.file_key.lstrip('/')}",
            "stub": True,
        }
    )
