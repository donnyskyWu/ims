"""AIR 技能库登记 · 审核（W9-5 首片）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirSkill, User

router = APIRouter(prefix="/air/skill", tags=["air-skill"])

BJ = timezone(timedelta(hours=8))


class SkillBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    skillName: str
    category: str = "内容生产"
    versionLabel: str = "v1.0"


class SkillAuditBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    approve: bool
    auditNote: str = ""


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_skill_no(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(AirSkill).where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id)
    )
    seq = int(count or 0) + 1
    return f"SKL-{seq:04d}"


def skill_vo(row: AirSkill, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "skillNo": row.skill_no,
        "skillName": row.skill_name,
        "category": row.category,
        "versionLabel": row.version_label,
        "status": row.status,
        "auditStatus": row.audit_status,
        "ownerName": names.get(row.owner_user_id, ""),
        "grantCount": row.grant_count,
        "invokeCount": row.invoke_count,
        "createdAt": iso(row.created_at),
    }


@router.get("/summary")
def skill_summary(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    total = int(
        db.scalar(
            select(func.count())
            .select_from(AirSkill)
            .where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id)
        )
        or 0
    )
    published = int(
        db.scalar(
            select(func.count())
            .select_from(AirSkill)
            .where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id, AirSkill.status == "PUBLISHED")
        )
        or 0
    )
    pending = int(
        db.scalar(
            select(func.count())
            .select_from(AirSkill)
            .where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id, AirSkill.audit_status == "PENDING")
        )
        or 0
    )
    invoke = int(
        db.scalar(
            select(func.coalesce(func.sum(AirSkill.invoke_count), 0)).where(
                AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id
            )
        )
        or 0
    )
    return ok({"skillCount": total, "publishedCount": published, "pendingAuditCount": pending, "invokeTotal": invoke})


@router.get("/list")
def skill_list(
    skillName: str | None = None,
    status: str | None = None,
    category: str | None = None,
    pageNo: int = 1,
    pageSize: int = 10,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    q = select(AirSkill).where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id)
    if skillName:
        q = q.where(AirSkill.skill_name.like(f"%{skillName.strip()}%"))
    if status:
        q = q.where(AirSkill.status == status.strip().upper())
    if category:
        q = q.where(AirSkill.category == category.strip())
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(AirSkill.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.owner_user_id for r in rows])
    return paged([skill_vo(r, names) for r in rows], total, page_no, size)


@router.post("")
def skill_create(body: SkillBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    name = body.skillName.strip()
    if not name:
        return fail(1001, "技能名称必填")
    now = utcnow()
    row = AirSkill(
        skill_no=next_skill_no(db, tenant_id),
        skill_name=name,
        category=body.category.strip() or "内容生产",
        version_label=body.versionLabel.strip() or "v1.0",
        status="DRAFT",
        audit_status="NONE",
        owner_user_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.owner_user_id])
    return ok(skill_vo(row, names))


@router.put("/{skill_id}/submit-audit")
def skill_submit_audit(skill_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = db.get(AirSkill, skill_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    if row.status not in {"DRAFT", "PENDING"}:
        return fail(1001, "当前状态不可提交审核")
    row.status = "PENDING"
    row.audit_status = "PENDING"
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(skill_vo(row, names))


@router.put("/{skill_id}/audit")
def skill_audit(
    skill_id: int,
    body: SkillAuditBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(AirSkill, skill_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    if row.audit_status != "PENDING":
        return fail(1001, "非待审核状态")
    row.updated_at = utcnow()
    if body.approve:
        row.status = "PUBLISHED"
        row.audit_status = "APPROVED"
    else:
        row.status = "DRAFT"
        row.audit_status = "REJECTED"
    names = user_names(db, [row.owner_user_id])
    return ok(skill_vo(row, names))
