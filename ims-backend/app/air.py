"""AIR 知识库文件管理（KNOW-001/002/004/005/006 · 无检索）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.air_skill import dept_ids_of, parse_expire, resolve_grant_target, role_ids_of, write_event
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import (
    AirKb,
    AirKbCategory,
    AirKbDoc,
    AirKbGrant,
    ContentProject,
    PerfScheme,
    Role,
    TrainMaterial,
    User,
    UserRole,
)

router = APIRouter(prefix="/air", tags=["air"])

BJ = timezone(timedelta(hours=8))


class KbUploadBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str = ""
    fileKey: str = ""
    fileName: str = ""
    content: str = ""
    contentType: str = "application/octet-stream"
    fileSize: int = 0
    kbId: int = 0
    cateId: int = 0
    categoryId: int = 0
    secretLevel: str = ""


class KbImportUrlBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbId: int = 0
    categoryId: int = 0
    urls: list[str] = Field(default_factory=list)
    secretLevel: str = ""


class KbImportTextBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbId: int = 0
    categoryId: int = 0
    title: str = ""
    content: str = ""
    secretLevel: str = ""


FILE_EXTS = frozenset({"pdf", "doc", "docx", "md", "html", "htm", "xls", "xlsx", "txt", "csv"})


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


class KbCreateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbName: str = ""
    desc: str = ""
    secretLevel: str = ""
    ownerUserId: int = 0


class KbLibAuditBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbId: int
    approve: bool
    auditNote: str = ""


class KbCategoryRenameBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbId: int
    categoryName: str = ""


class KbGrantBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    kbId: int
    grantType: str = ""
    grantId: int = 0
    expireAt: str = ""


class KbTransferBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    sourceType: str = ""
    sourceIds: list[int] = Field(default_factory=list)
    targetKbId: int = 0
    targetCategoryId: int = 0
    secretLevel: str = ""
    clientToken: str = ""


SECRET_LEVELS = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "TOP_SECRET")
SECRET_RANK = {name: index for index, name in enumerate(SECRET_LEVELS)}
SECRET_LABEL = {
    "PUBLIC": "公开",
    "INTERNAL": "内部",
    "CONFIDENTIAL": "机密",
    "TOP_SECRET": "绝密",
}
KB_STATUS_LABEL = {"DRAFT": "草稿", "PENDING": "入库审批中", "PUBLISHED": "已发布"}
SOURCE_LABEL = {
    "FILE": "文件",
    "URL": "URL",
    "TEXT": "文本",
    "TRAIN": "培训资料",
    "PERF": "绩效考核模板",
    "CONTENT": "内容记录",
}


def as_utc(dt: datetime) -> datetime:
    """库内 DateTime 不带时区，写入值为 UTC。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_shanghai(dt: datetime | None, *, clock: bool = False) -> str:
    """naive UTC → Asia/Shanghai。clock 为表格 yyyy-MM-dd HH:mm，否则带 +08:00。"""
    if dt is None:
        return ""
    local = as_utc(dt).astimezone(BJ)
    if clock:
        return local.strftime("%Y-%m-%d %H:%M")
    return local.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def iso_min(dt: datetime | None) -> str:
    """授权到期等日历钟面，按录入时刻格式化，不当作 UTC。"""
    if dt is None:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(BJ).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M")


def format_size(size: int) -> str:
    value = max(0, int(size or 0))
    if value < 1024:
        return f"{value} B"
    units = ["KB", "MB", "GB"]
    number = float(value)
    unit = "B"
    for unit in units:
        number /= 1024
        if number < 1024:
            break
    return f"{number:.1f} {unit}"


def normalize_secret(value: str) -> str:
    text = (value or "").strip().upper()
    alias = {
        "公开": "PUBLIC",
        "内部": "INTERNAL",
        "机密": "CONFIDENTIAL",
        "绝密": "TOP_SECRET",
        "PUBLIC": "PUBLIC",
        "INTERNAL": "INTERNAL",
        "CONFIDENTIAL": "CONFIDENTIAL",
        "TOP_SECRET": "TOP_SECRET",
    }
    return alias.get(text, alias.get((value or "").strip(), ""))


def grants_limit_text(secret: str) -> str:
    if secret == "CONFIDENTIAL":
        return "仅 R1/R3/R4 可授权"
    if secret == "TOP_SECRET":
        return "仅 R1 可授权"
    return ""


def role_tags_of(db: Session, user: User) -> set[str]:
    tags: set[str] = set()
    role_ids = list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)).all())
    if not role_ids:
        return tags
    roles = db.scalars(select(Role).where(Role.id.in_(role_ids), Role.deleted == 0)).all()
    for role in roles:
        key = (role.role_key or "").strip().lower()
        name = role.role_name or ""
        if key:
            tags.add(key)
        if key == "sys:admin" or "系统管理员" in name:
            tags.add("r1")
        if key == "r3" or key.endswith(":r3") or "财务" in name:
            tags.add("r3")
        if key == "r4" or key.endswith(":r4") or "运营总监" in name:
            tags.add("r4")
    return tags


def target_allowed(secret: str, tags: set[str]) -> bool:
    if secret == "TOP_SECRET":
        return bool(tags & {"r1", "sys:admin"})
    if secret == "CONFIDENTIAL":
        return bool(tags & {"r1", "r3", "r4", "sys:admin"})
    return True


def kb_doc_vo(row: AirKbDoc, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "kbId": row.kb_id,
        "title": row.title,
        "fileKey": row.file_key,
        "contentType": row.content_type,
        "fileSize": int(row.file_size or 0),
        "cateId": row.cate_id,
        "categoryId": row.cate_id,
        "secretLevel": row.secret_level or "",
        "secretLabel": SECRET_LABEL.get(row.secret_level or "", row.secret_level or ""),
        "sourceType": row.source_type or "FILE",
        "sourceLabel": SOURCE_LABEL.get(row.source_type or "FILE", row.source_type or ""),
        "sourceRef": row.source_ref or "",
        "body": row.body or "",
        "auditNote": row.audit_note or "",
        "auditStatus": row.audit_status,
        "uploaderUserId": row.uploader_user_id,
        "uploaderName": names.get(row.uploader_user_id, ""),
        "createdAt": iso_shanghai(row.created_at),
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


def kb_doc_total(db: Session, kb_id: int, tenant_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AirKbDoc)
            .where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.kb_id == kb_id,
            )
        )
        or 0
    )


def kb_size_total(db: Session, kb_id: int, tenant_id: int) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(AirKbDoc.file_size), 0)).where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.kb_id == kb_id,
            )
        )
        or 0
    )


def grant_count_of(db: Session, kb_id: int, tenant_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AirKbGrant)
            .where(
                AirKbGrant.deleted == 0,
                AirKbGrant.tenant_id == tenant_id,
                AirKbGrant.kb_id == kb_id,
                AirKbGrant.status == "ACTIVE",
            )
        )
        or 0
    )


def ensure_kb_no(db: Session, row: AirKb) -> None:
    if (row.kb_no or "").strip():
        return
    row.kb_no = f"KB-{row.id:04d}"
    row.updated_at = utcnow()


def next_kb_no(db: Session, tenant_id: int) -> str:
    rows = db.scalars(
        select(AirKb.kb_no).where(AirKb.deleted == 0, AirKb.tenant_id == tenant_id)
    ).all()
    highest = 0
    for item in rows:
        text = (item or "").strip()
        if not text.startswith("KB-"):
            continue
        tail = text.split("-", 1)[1]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"KB-{highest + 1:04d}"


def load_kb(db: Session, kb_id: int, tenant_id: int) -> AirKb | None:
    row = db.get(AirKb, kb_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    ensure_kb_no(db, row)
    return row


def list_kbs(db: Session, tenant_id: int, owner_user_id: int) -> list[AirKb]:
    ensure_default_kb(db, tenant_id, owner_user_id)
    rows = list(
        db.scalars(
            select(AirKb)
            .where(AirKb.deleted == 0, AirKb.tenant_id == tenant_id)
            .order_by(AirKb.id.asc())
        ).all()
    )
    if len(rows) == 1:
        ensure_default_categories(db, rows[0].id, tenant_id)
    for row in rows:
        ensure_kb_no(db, row)
        if not (row.status or "").strip():
            row.status = "PUBLISHED"
        if not (row.provider or "").strip():
            row.provider = "LOCAL"
    return rows


def kb_vo(db: Session, row: AirKb, names: dict[int, str]) -> dict:
    secret = row.secret_level or "INTERNAL"
    size = kb_size_total(db, row.id, row.tenant_id)
    return {
        "id": row.id,
        "kbCode": row.kb_no,
        "kbNo": row.kb_no,
        "kbName": row.kb_name,
        "desc": row.description or "",
        "secretLevel": secret,
        "secretLabel": SECRET_LABEL.get(secret, secret),
        "grantsLimit": grants_limit_text(secret),
        "docCount": kb_doc_total(db, row.id, row.tenant_id),
        "totalSize": size,
        "sizeLabel": format_size(size),
        "status": row.status or "PUBLISHED",
        "statusLabel": KB_STATUS_LABEL.get(row.status or "PUBLISHED", row.status or ""),
        "provider": row.provider or "LOCAL",
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id, ""),
        "grantCount": grant_count_of(db, row.id, row.tenant_id),
        "updatedAt": iso_shanghai(row.updated_at, clock=True),
    }


def tree_node(db: Session, row: AirKb, tenant_id: int) -> dict:
    secret = row.secret_level or "INTERNAL"
    return {
        "id": row.id,
        "kbNo": row.kb_no,
        "kbName": row.kb_name,
        "secretLevel": secret,
        "secretLabel": SECRET_LABEL.get(secret, secret),
        "status": row.status or "PUBLISHED",
        "docCount": kb_doc_total(db, row.id, tenant_id),
        "children": build_category_nodes(db, row.id, tenant_id),
    }


@router.get("/kb/tree")
def kb_tree(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    rows = list_kbs(db, tenant_id, actor.id)
    return ok([tree_node(db, row, tenant_id) for row in rows])


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


@router.put("/kb/category/{category_id}")
def kb_category_rename(
    category_id: int,
    body: KbCategoryRenameBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    name = (body.categoryName or "").strip()
    if not name:
        return fail(1001, "分类名称必填")
    if len(name) > 64:
        return fail(1001, "分类名称不超过 64 字")
    tenant_id = tenant_of(actor)
    row = db.get(AirKbCategory, category_id)
    if row is None or row.deleted or row.tenant_id != tenant_id or row.kb_id != body.kbId:
        return fail(1004, "分类不存在")
    dup = db.scalar(
        select(AirKbCategory.id).where(
            AirKbCategory.deleted == 0,
            AirKbCategory.tenant_id == tenant_id,
            AirKbCategory.kb_id == row.kb_id,
            AirKbCategory.parent_id == row.parent_id,
            AirKbCategory.category_name == name,
            AirKbCategory.id != row.id,
        )
    )
    if dup:
        return fail(1001, "同级分类名称重复")
    row.category_name = name
    row.updated_at = utcnow()
    return ok({"categoryId": row.id, "categoryName": row.category_name})


@router.delete("/kb/category/{category_id}")
def kb_category_delete(
    category_id: int,
    kbId: int,
    moveToRoot: bool = False,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(AirKbCategory, category_id)
    if row is None or row.deleted or row.tenant_id != tenant_id or row.kb_id != kbId:
        return fail(1004, "分类不存在")
    child_ids = [
        row.id,
        *list(
            db.scalars(
                select(AirKbCategory.id).where(
                    AirKbCategory.deleted == 0,
                    AirKbCategory.tenant_id == tenant_id,
                    AirKbCategory.parent_id == row.id,
                )
            ).all()
        ),
    ]
    doc_count = int(
        db.scalar(
            select(func.count())
            .select_from(AirKbDoc)
            .where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.cate_id.in_(child_ids),
            )
        )
        or 0
    )
    if doc_count and not moveToRoot:
        return fail(1001, "该分类下有知识条目，删除后条目将改挂根分类")
    moved = 0
    if doc_count:
        docs = db.scalars(
            select(AirKbDoc).where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.cate_id.in_(child_ids),
            )
        ).all()
        now = utcnow()
        for doc in docs:
            doc.cate_id = 0
            doc.updated_at = now
            moved += 1
    now = utcnow()
    nodes = db.scalars(
        select(AirKbCategory).where(
            AirKbCategory.deleted == 0,
            AirKbCategory.tenant_id == tenant_id,
            AirKbCategory.id.in_(child_ids),
        )
    ).all()
    for node in nodes:
        node.deleted = 1
        node.updated_at = now
    return ok({"categoryId": row.id, "movedDocCount": moved})


def role_tags_for_role(role: Role) -> set[str]:
    tags: set[str] = set()
    key = (role.role_key or "").strip().lower()
    name = role.role_name or ""
    if key:
        tags.add(key)
    if key == "sys:admin" or "系统管理员" in name:
        tags.add("r1")
    if key == "r3" or key.endswith(":r3") or "财务" in name:
        tags.add("r3")
    if key == "r4" or key.endswith(":r4") or "运营总监" in name:
        tags.add("r4")
    return tags


@router.post("/kb/grant")
def kb_grant(body: KbGrantBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = load_kb(db, body.kbId, tenant_id)
    if row is None:
        return fail(1004, "知识库不存在")
    if row.status != "PUBLISHED":
        return fail(1001, "知识库未发布不可授权")
    grant_type = (body.grantType or "").strip().upper()
    if grant_type not in {"DEPT", "ROLE", "PERSON"}:
        return fail(1001, "授权类型仅支持 DEPT、ROLE、PERSON")
    expire_at = None
    if (body.expireAt or "").strip():
        expire_at = parse_expire(body.expireAt)
        if expire_at is None:
            return fail(1001, "有效期格式应为 YYYY-MM-DD")
    secret = row.secret_level or "INTERNAL"
    limit = grants_limit_text(secret)
    if secret in {"CONFIDENTIAL", "TOP_SECRET"}:
        if grant_type == "PERSON":
            user = db.get(User, body.grantId)
            tags = role_tags_of(db, user) if user is not None else set()
            if not target_allowed(secret, tags):
                return fail(1001, limit)
        elif grant_type == "ROLE":
            role = db.get(Role, body.grantId)
            tags = role_tags_for_role(role) if role is not None else set()
            if not target_allowed(secret, tags):
                return fail(1001, limit)
        else:
            return fail(1001, limit)
    grant_name, error = resolve_grant_target(db, tenant_id, grant_type, body.grantId)
    if error:
        return fail(1001, error)
    now = utcnow()
    grant = AirKbGrant(
        kb_id=row.id,
        grant_type=grant_type,
        grant_id_ref=body.grantId,
        grant_name=grant_name or "",
        status="ACTIVE",
        expire_at=expire_at,
        granted_by=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(grant)
    db.flush()
    sync_id = write_event(
        db,
        tenant_id,
        "KB_GRANT",
        {"kbId": row.id, "grantId": grant.id, "grantType": grant_type, "grantIdRef": body.grantId},
    )
    return ok({"grantId": grant.id, "status": grant.status, "syncEventId": sync_id, "grantName": grant.grant_name})


def transfer_rows(db: Session, tenant_id: int, source_type: str, keyword: str) -> list[dict]:
    text = keyword.strip()
    items: list[dict] = []
    if source_type == "TRAIN":
        stmt = select(TrainMaterial).where(TrainMaterial.deleted == 0, TrainMaterial.tenant_id == tenant_id)
        if text:
            stmt = stmt.where(TrainMaterial.title.like(f"%{text}%"))
        for row in db.scalars(stmt.order_by(TrainMaterial.id.desc()).limit(50)).all():
            items.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "category": row.material_type or "",
                    "secretLevel": "INTERNAL",
                    "updatedAt": iso_shanghai(row.updated_at, clock=True),
                }
            )
    elif source_type == "PERF":
        stmt = select(PerfScheme).where(PerfScheme.deleted == 0, PerfScheme.tenant_id == tenant_id)
        if text:
            stmt = stmt.where(PerfScheme.template_name.like(f"%{text}%"))
        for row in db.scalars(stmt.order_by(PerfScheme.id.desc()).limit(50)).all():
            items.append(
                {
                    "id": row.id,
                    "title": row.template_name,
                    "category": row.position_code or "",
                    "secretLevel": "INTERNAL",
                    "updatedAt": iso_shanghai(row.updated_at, clock=True),
                }
            )
    elif source_type == "CONTENT":
        stmt = select(ContentProject).where(ContentProject.deleted == 0, ContentProject.tenant_id == tenant_id)
        if text:
            stmt = stmt.where(ContentProject.title.like(f"%{text}%"))
        for row in db.scalars(stmt.order_by(ContentProject.id.desc()).limit(50)).all():
            items.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "category": row.content_type or "",
                    "secretLevel": "INTERNAL",
                    "updatedAt": iso_shanghai(row.created_at, clock=True),
                }
            )
    imported = set(
        db.scalars(
            select(AirKbDoc.source_ref).where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.source_type == source_type,
            )
        ).all()
    )
    for item in items:
        item["imported"] = str(item["id"]) in {str(value) for value in imported}
        item["secretLabel"] = SECRET_LABEL.get(item["secretLevel"], item["secretLevel"])
    return items


@router.get("/kb/transfer-source")
def kb_transfer_source(
    sourceType: str = "",
    keyword: str = "",
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    kind = (sourceType or "").strip().upper()
    if kind not in {"TRAIN", "PERF", "CONTENT"}:
        return fail(1001, "请先选择来源模块")
    tenant_id = tenant_of(actor)
    items = transfer_rows(db, tenant_id, kind, keyword or "")
    page_no, size = page_args(pageNo, pageSize)
    total = len(items)
    return paged(items[(page_no - 1) * size : page_no * size], total, page_no, size)


@router.post("/kb/doc/import-from")
def kb_import_from(body: KbTransferBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    kind = (body.sourceType or "").strip().upper()
    if kind not in {"TRAIN", "PERF", "CONTENT"}:
        return fail(1001, "请先选择来源模块")
    if not body.sourceIds:
        return fail(1001, "请至少勾选 1 条来源条目")
    tenant_id = tenant_of(actor)
    kb = load_kb(db, body.targetKbId, tenant_id)
    if kb is None:
        return fail(1001, "目标知识库必填")
    if body.targetCategoryId:
        cate = db.get(AirKbCategory, body.targetCategoryId)
        if cate is None or cate.deleted or cate.kb_id != kb.id or cate.tenant_id != tenant_id:
            return fail(1004, "分类不存在")
    secret = normalize_secret(body.secretLevel) if (body.secretLevel or "").strip() else ""
    if secret and secret not in SECRET_LEVELS:
        return fail(1001, "密级非法")
    if secret and SECRET_RANK[secret] < SECRET_RANK.get(kb.secret_level or "INTERNAL", 1):
        return fail(1001, "密级不得低于库密级")
    sources = {item["id"]: item for item in transfer_rows(db, tenant_id, kind, "")}
    now = utcnow()
    doc_ids: list[int] = []
    statuses: list[str] = []
    for source_id in body.sourceIds:
        item = sources.get(int(source_id))
        if item is None:
            return fail(1001, "来源条目不存在")
        existed = db.scalar(
            select(AirKbDoc).where(
                AirKbDoc.deleted == 0,
                AirKbDoc.tenant_id == tenant_id,
                AirKbDoc.source_type == kind,
                AirKbDoc.source_ref == str(source_id),
                AirKbDoc.kb_id == kb.id,
            )
        )
        if existed is not None:
            doc_ids.append(existed.id)
            statuses.append(existed.audit_status)
            continue
        doc_secret = secret or item["secretLevel"]
        if SECRET_RANK.get(doc_secret, 0) < SECRET_RANK.get(kb.secret_level or "INTERNAL", 1):
            doc_secret = kb.secret_level or "INTERNAL"
        row = AirKbDoc(
            kb_id=kb.id,
            title=item["title"][:256],
            file_key=f"kb/transfer/{kind.lower()}/{source_id}",
            content_type="text/plain",
            file_size=len(item["title"].encode("utf-8")),
            cate_id=int(body.targetCategoryId or 0),
            secret_level=doc_secret,
            source_type=kind,
            source_ref=str(source_id),
            body=item["title"],
            audit_status="PENDING",
            uploader_user_id=actor.id,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        doc_ids.append(row.id)
        statuses.append(row.audit_status)
    kb.updated_at = now
    return ok({"docIds": doc_ids, "auditStatus": statuses})


@router.get("/kb/page")
def kb_page(
    pageNo: int = 1,
    pageSize: int = 10,
    keyword: str = "",
    kbId: int | None = None,
    secretLevel: str = "",
    status: str = "",
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    rows = list_kbs(db, tenant_id, actor.id)
    secret = normalize_secret(secretLevel)
    wanted = (status or "").strip().upper()
    text = (keyword or "").strip().lower()
    filtered: list[AirKb] = []
    for row in rows:
        if kbId and row.id != kbId:
            continue
        if secret and (row.secret_level or "") != secret:
            continue
        if wanted and (row.status or "") != wanted:
            continue
        if text and text not in f"{row.kb_no} {row.kb_name}".lower():
            continue
        filtered.append(row)
    page_no, size = page_args(pageNo, pageSize)
    total = len(filtered)
    page_rows = list(reversed(filtered))[(page_no - 1) * size : page_no * size]
    names = user_names(db, {row.owner_user_id for row in page_rows})
    return paged([kb_vo(db, row, names) for row in page_rows], total, page_no, size)


@router.get("/kb/doc/page")
def kb_doc_page(
    pageNo: int = 1,
    pageSize: int = 10,
    title: str = "",
    keyword: str = "",
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
    text = (title or keyword or "").strip()
    if text:
        stmt = stmt.where(AirKbDoc.title.like(f"%{text}%"))
    if docStatus:
        stmt = stmt.where(AirKbDoc.audit_status == docStatus)
    page_no, size = page_args(pageNo, pageSize)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(
        db.scalars(stmt.order_by(AirKbDoc.id.desc()).offset((page_no - 1) * size).limit(size)).all()
    )
    names = user_names(db, {r.uploader_user_id for r in rows})
    return paged([kb_doc_vo(r, names) for r in rows], total, page_no, size)


@router.post("/kb")
def kb_create(body: KbCreateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    name = (body.kbName or "").strip()
    if not name:
        return fail(1001, "知识库名称必填")
    if len(name) > 128:
        return fail(1001, "知识库名称不超过 128 字")
    secret = normalize_secret(body.secretLevel)
    if secret not in SECRET_LEVELS:
        return fail(1001, "密级必填")
    if body.ownerUserId <= 0:
        return fail(1001, "责任人必填")
    tenant_id = tenant_of(actor)
    owner = db.get(User, body.ownerUserId)
    if owner is None or owner.deleted or (owner.tenant_id or 0) != tenant_id:
        return fail(1001, "责任人不存在")
    now = utcnow()
    status = "PENDING" if secret in {"CONFIDENTIAL", "TOP_SECRET"} else "PUBLISHED"
    row = AirKb(
        kb_no=next_kb_no(db, tenant_id),
        kb_name=name,
        description=(body.desc or "").strip()[:512],
        secret_level=secret,
        status=status,
        provider="LOCAL",
        owner_user_id=owner.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, {owner.id})
    return ok(kb_vo(db, row, names))


@router.post("/kb/audit")
def kb_lib_audit(body: KbLibAuditBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = load_kb(db, body.kbId, tenant_id)
    if row is None:
        return fail(1004, "知识库不存在")
    if row.status != "PENDING":
        return fail(1001, "仅入库审批中的知识库可审批")
    if not body.approve and not (body.auditNote or "").strip():
        return fail(1001, "驳回须填写意见")
    row.status = "PUBLISHED" if body.approve else "DRAFT"
    row.updated_at = utcnow()
    names = user_names(db, {row.owner_user_id})
    data = kb_vo(db, row, names)
    data["auditNote"] = (body.auditNote or "").strip()
    return ok(data)


@router.get("/kb/owner-candidates")
def kb_owner_candidates(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    """在职人员姓名，供新建知识库选责任人。走知识库数据范围，不依赖系统用户目录。"""
    tenant_id = tenant_of(actor)
    rows = db.scalars(
        select(User)
        .where(User.deleted == 0, User.tenant_id == tenant_id, User.status == "ENABLED")
        .order_by(User.id.asc())
    ).all()
    data = []
    for row in rows:
        name = (row.nickname or "").strip() or (row.username or "").strip()
        if not name:
            continue
        data.append({"userId": row.id, "name": name})
    return ok(data)


@router.get("/kb/{kb_id}")
def kb_detail(kb_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = load_kb(db, kb_id, tenant_id)
    if row is None:
        return fail(1004, "知识库不存在")
    names = user_names(db, {row.owner_user_id})
    data = kb_vo(db, row, names)
    docs = list(
        db.scalars(
            select(AirKbDoc)
            .where(AirKbDoc.deleted == 0, AirKbDoc.tenant_id == tenant_id, AirKbDoc.kb_id == row.id)
            .order_by(AirKbDoc.id.desc())
        ).all()
    )
    uploaders = user_names(db, {item.uploader_user_id for item in docs})
    data["docs"] = [kb_doc_vo(item, uploaders) for item in docs]
    data["fileOnly"] = True
    grants = db.scalars(
        select(AirKbGrant)
        .where(AirKbGrant.deleted == 0, AirKbGrant.tenant_id == tenant_id, AirKbGrant.kb_id == row.id)
        .order_by(AirKbGrant.id.desc())
    ).all()
    data["grants"] = [
        {
            "grantId": item.id,
            "grantType": item.grant_type,
            "grantName": item.grant_name,
            "status": item.status,
            "expireAt": iso_min(item.expire_at) if item.expire_at else "",
        }
        for item in grants
    ]
    return ok(data)


def extension_of(name: str) -> str:
    text = (name or "").rsplit("/", 1)[-1]
    if "." not in text:
        return ""
    return text.rsplit(".", 1)[-1].lower()


def resolve_upload_kb(
    db: Session,
    actor: User,
    kb_id: int,
    category_id: int,
    secret_level: str,
):
    tenant_id = tenant_of(actor)
    if kb_id:
        kb = load_kb(db, kb_id, tenant_id)
        if kb is None:
            return None, None, None, fail(1004, "知识库不存在")
    else:
        kb = ensure_default_kb(db, tenant_id, actor.id)
        ensure_kb_no(db, kb)
    if category_id:
        cate = db.get(AirKbCategory, category_id)
        if cate is None or cate.deleted or cate.kb_id != kb.id or cate.tenant_id != tenant_id:
            return None, None, None, fail(1004, "分类不存在")
    secret = normalize_secret(secret_level) if (secret_level or "").strip() else (kb.secret_level or "INTERNAL")
    if secret not in SECRET_LEVELS:
        return None, None, None, fail(1001, "密级非法")
    if SECRET_RANK[secret] < SECRET_RANK.get(kb.secret_level or "INTERNAL", 1):
        return None, None, None, fail(1001, "密级不得低于库密级")
    return kb, secret, tenant_id, None


def insert_pending_doc(
    db: Session,
    *,
    kb: AirKb,
    tenant_id: int,
    actor_id: int,
    title: str,
    file_key: str,
    content_type: str,
    file_size: int,
    cate_id: int,
    secret: str,
    source_type: str,
    body: str = "",
) -> AirKbDoc:
    now = utcnow()
    row = AirKbDoc(
        kb_id=kb.id,
        title=title[:256],
        file_key=file_key[:512],
        content_type=content_type or "application/octet-stream",
        file_size=max(0, int(file_size or 0)),
        cate_id=cate_id,
        secret_level=secret,
        source_type=source_type,
        body=body or "",
        audit_status="PENDING",
        uploader_user_id=actor_id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    kb.updated_at = now
    db.flush()
    return row


@router.post("/kb/doc/upload")
def kb_doc_upload(
    body: KbUploadBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    file_name = (body.fileName or "").strip()
    file_key = (body.fileKey or "").strip()
    title = (body.title or "").strip() or file_name
    if not file_key and not file_name:
        return fail(1001, "请选择文件")
    if file_name:
        ext = extension_of(file_name)
        if ext not in FILE_EXTS:
            return fail(1001, "不支持的文件类型")
    if not title:
        return fail(1001, "标题必填")
    if not file_key:
        safe = file_name.replace("\\", "/").rsplit("/", 1)[-1].replace(" ", "_")
        file_key = f"kb/{utcnow().astimezone(BJ).year}/{safe}"
    cate_id = int(body.categoryId or body.cateId or 0)
    kb, secret, tenant_id, error = resolve_upload_kb(db, actor, int(body.kbId or 0), cate_id, body.secretLevel)
    if error is not None:
        return error
    row = insert_pending_doc(
        db,
        kb=kb,
        tenant_id=tenant_id,
        actor_id=actor.id,
        title=title,
        file_key=file_key,
        content_type=(body.contentType or "application/octet-stream").strip(),
        file_size=body.fileSize or len((body.content or "").encode("utf-8")),
        cate_id=cate_id,
        secret=secret,
        source_type="FILE",
        body=body.content or "",
    )
    names = user_names(db, {actor.id})
    return ok({"docIds": [row.id], "auditStatus": [row.audit_status], "doc": kb_doc_vo(row, names)})


@router.post("/kb/doc/import-url")
def kb_doc_import_url(
    body: KbImportUrlBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    urls = [item.strip() for item in body.urls if (item or "").strip()]
    if not urls:
        return fail(1001, "URL 地址必填")
    if any(not (item.startswith("http://") or item.startswith("https://")) for item in urls):
        return fail(1001, "URL 须以 http:// 或 https:// 开头")
    kb, secret, tenant_id, error = resolve_upload_kb(db, actor, int(body.kbId or 0), int(body.categoryId or 0), body.secretLevel)
    if error is not None:
        return error
    ids: list[int] = []
    statuses: list[str] = []
    for url in urls:
        row = insert_pending_doc(
            db,
            kb=kb,
            tenant_id=tenant_id,
            actor_id=actor.id,
            title=url[:128],
            file_key=url[:512],
            content_type="text/uri-list",
            file_size=len(url.encode("utf-8")),
            cate_id=int(body.categoryId or 0),
            secret=secret,
            source_type="URL",
            body=url,
        )
        ids.append(row.id)
        statuses.append(row.audit_status)
    return ok({"docIds": ids, "auditStatus": statuses})


@router.post("/kb/doc/import-text")
def kb_doc_import_text(
    body: KbImportTextBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    title = (body.title or "").strip()
    content = (body.content or "").strip()
    if not title or not content:
        return fail(1001, "标题和正文必填")
    if len(title) > 128:
        return fail(1001, "标题不超过 128 字")
    kb, secret, tenant_id, error = resolve_upload_kb(db, actor, int(body.kbId or 0), int(body.categoryId or 0), body.secretLevel)
    if error is not None:
        return error
    row = insert_pending_doc(
        db,
        kb=kb,
        tenant_id=tenant_id,
        actor_id=actor.id,
        title=title,
        file_key=f"kb/text/{row_token(title)}",
        content_type="text/plain",
        file_size=len(content.encode("utf-8")),
        cate_id=int(body.categoryId or 0),
        secret=secret,
        source_type="TEXT",
        body=content,
    )
    return ok({"docIds": [row.id], "auditStatus": [row.audit_status]})


def row_token(title: str) -> str:
    cleaned = "".join(ch for ch in title if ch.isalnum())[:24] or "note"
    return f"{cleaned}.txt"


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


def kb_grant_covers(db: Session, kb_id: int, tenant_id: int, actor: User) -> bool:
    now = utcnow()
    grants = db.scalars(
        select(AirKbGrant).where(
            AirKbGrant.deleted == 0,
            AirKbGrant.tenant_id == tenant_id,
            AirKbGrant.kb_id == kb_id,
            AirKbGrant.status == "ACTIVE",
        )
    ).all()
    if not grants:
        return False
    dept_ids = dept_ids_of(db, actor.id, tenant_id)
    role_ids = role_ids_of(db, actor.id)
    for item in grants:
        if item.expire_at is not None and item.expire_at < now:
            continue
        if item.grant_type == "PERSON" and int(item.grant_id_ref) == int(actor.id):
            return True
        if item.grant_type == "DEPT" and int(item.grant_id_ref) in dept_ids:
            return True
        if item.grant_type == "ROLE" and int(item.grant_id_ref) in role_ids:
            return True
    return False


def download_block_reason(db: Session, actor: User, row: AirKbDoc) -> str:
    if row.audit_status != "PUBLISHED":
        return "未发布文档不可下载"
    secret = (row.secret_level or "").strip() or "INTERNAL"
    if secret not in {"CONFIDENTIAL", "TOP_SECRET"}:
        return ""
    tenant_id = tenant_of(actor)
    if int(row.uploader_user_id or 0) == int(actor.id):
        return ""
    kb = load_kb(db, row.kb_id, tenant_id)
    if kb is not None and int(kb.owner_user_id or 0) == int(actor.id):
        return ""
    if target_allowed(secret, role_tags_of(db, actor)):
        return ""
    if kb_grant_covers(db, row.kb_id, tenant_id, actor):
        return ""
    return "当前密级无权下载"


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
    reason = download_block_reason(db, actor, row)
    if reason:
        return fail(1001, reason)
    payload, media, filename = doc_download_bytes(row)
    return Response(content=payload, media_type=media, headers={"Content-Disposition": content_disposition(filename)})


def download_filename(row: AirKbDoc) -> str:
    raw = (row.file_key or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if raw and "." in raw and not raw.lower().startswith("http"):
        return raw[:180]
    title = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (row.title or "document"))[:80] or "document"
    ext = "url" if (row.source_type or "") == "URL" else "txt"
    return f"{title}.{ext}"


def content_disposition(filename: str) -> str:
    ascii_name = "".join(ch if 32 <= ord(ch) < 127 and ch not in {'"', "\\"} else "_" for ch in filename) or "download.bin"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def doc_download_bytes(row: AirKbDoc) -> tuple[bytes, str, str]:
    filename = download_filename(row)
    text = row.body or ""
    if text:
        media = (row.content_type or "text/plain").split(";")[0].strip() or "text/plain"
        if not media.startswith("text/") and media not in {"application/json", "application/xml"}:
            media = "text/plain"
        return text.encode("utf-8"), f"{media}; charset=utf-8", filename
    note = f"{row.title or filename}\n{row.file_key or ''}\n"
    return note.encode("utf-8"), "text/plain; charset=utf-8", filename
