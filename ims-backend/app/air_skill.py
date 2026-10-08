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
from app.models import AirEvent, AirSkill, AirSkillGrant, Role, User, UserDept, UserMapping, UserRole

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


GRANT_TYPES = frozenset({"DEPT", "ROLE", "PERSON"})


class SkillStatusBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    status: str


class SkillGrantBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    skillId: int
    grantType: str = ""
    grantId: int = 0
    expireAt: str = ""
    allStaff: bool = False


def parse_expire(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.replace(hour=23, minute=59, second=59)


def write_event(db: Session, tenant_id: int, event_type: str, payload: dict) -> str:
    row = AirEvent(
        event_type=event_type,
        payload=payload,
        sync_status="PENDING",
        tenant_id=tenant_id,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return f"air-evt-{row.id}"


def dept_ids_of(db: Session, user_id: int, tenant_id: int) -> set[int]:
    rows = db.scalars(
        select(UserDept.dept_id).where(UserDept.user_id == user_id, UserDept.tenant_id == tenant_id)
    ).all()
    found = {int(item) for item in rows}
    mappings = db.scalars(
        select(UserMapping).where(
            UserMapping.user_id == user_id,
            UserMapping.deleted == 0,
            UserMapping.tenant_id == tenant_id,
        )
    ).all()
    for mapping in mappings:
        for item in mapping.dept_ids or []:
            if str(item).isdigit():
                found.add(int(item))
    return found


def role_ids_of(db: Session, user_id: int) -> set[int]:
    return {int(item) for item in db.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id)).all()}


def grant_is_current(row: AirSkillGrant, now: datetime) -> bool:
    if row.deleted or row.status != "ACTIVE":
        return False
    if row.expire_at is not None and row.expire_at < now:
        return False
    return True


def grant_matches(row: AirSkillGrant, user_id: int, dept_ids: set[int], role_ids: set[int]) -> bool:
    if row.all_staff:
        return True
    if row.grant_type == "PERSON" and int(row.grant_id_ref) == int(user_id):
        return True
    if row.grant_type == "DEPT" and int(row.grant_id_ref) in dept_ids:
        return True
    if row.grant_type == "ROLE" and int(row.grant_id_ref) in role_ids:
        return True
    return False


def skill_visible_to(db: Session, skill: AirSkill, user_id: int) -> bool:
    """已发布且命中一条未过期的 ACTIVE 授权。停用、草稿、待审核都不进 skills.list。"""
    if skill.deleted or skill.status != "PUBLISHED":
        return False
    now = utcnow()
    grants = db.scalars(
        select(AirSkillGrant).where(
            AirSkillGrant.skill_id == skill.id,
            AirSkillGrant.deleted == 0,
            AirSkillGrant.tenant_id == skill.tenant_id,
            AirSkillGrant.status == "ACTIVE",
        )
    ).all()
    if not grants:
        return False
    dept_ids = dept_ids_of(db, user_id, skill.tenant_id)
    role_ids = role_ids_of(db, user_id)
    return any(grant_matches(item, user_id, dept_ids, role_ids) for item in grants if grant_is_current(item, now))


def dept_exists(db: Session, tenant_id: int, dept_id: int) -> bool:
    found = db.scalar(
        select(UserDept.dept_id).where(UserDept.dept_id == dept_id, UserDept.tenant_id == tenant_id).limit(1)
    )
    if found is not None:
        return True
    mappings = db.scalars(
        select(UserMapping).where(UserMapping.deleted == 0, UserMapping.tenant_id == tenant_id)
    ).all()
    for mapping in mappings:
        if dept_id in {int(item) for item in (mapping.dept_ids or []) if str(item).isdigit()}:
            return True
    return False


def resolve_grant_target(db: Session, tenant_id: int, grant_type: str, grant_id: int) -> tuple[str | None, str | None]:
    if grant_type == "PERSON":
        user = db.get(User, grant_id)
        if user is None or user.deleted or (user.tenant_id or 0) != tenant_id:
            return None, "授权对象不存在"
        return (user.nickname or user.username or str(user.id)), None
    if grant_type == "ROLE":
        role = db.get(Role, grant_id)
        if role is None or role.deleted or (role.tenant_id or 0) != tenant_id:
            return None, "授权对象不存在"
        return role.role_name, None
    if grant_type == "DEPT":
        if grant_id <= 0 or not dept_exists(db, tenant_id, grant_id):
            return None, "授权对象不存在"
        return f"部门#{grant_id}", None
    return None, "授权类型无效"


def grant_vo(row: AirSkillGrant) -> dict:
    return {
        "grantId": row.id,
        "grantType": row.grant_type,
        "grantObjId": row.grant_id_ref,
        "grantName": row.grant_name,
        "allStaff": bool(row.all_staff),
        "expireAt": iso(row.expire_at) if row.expire_at else "",
        "status": row.status,
    }


def load_skill(db: Session, skill_id: int, tenant_id: int) -> AirSkill | None:
    row = db.get(AirSkill, skill_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return None
    return row


def active_grant_count(db: Session, skill_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AirSkillGrant)
            .where(
                AirSkillGrant.skill_id == skill_id,
                AirSkillGrant.deleted == 0,
                AirSkillGrant.status == "ACTIVE",
            )
        )
        or 0
    )


@router.get("/{skill_id}")
def skill_detail(skill_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    row = load_skill(db, skill_id, tenant_of(actor))
    if row is None:
        return fail(1504, "资源不可用")
    names = user_names(db, [row.owner_user_id])
    data = skill_vo(row, names)
    grants = db.scalars(
        select(AirSkillGrant)
        .where(AirSkillGrant.skill_id == row.id, AirSkillGrant.deleted == 0, AirSkillGrant.tenant_id == row.tenant_id)
        .order_by(AirSkillGrant.id.desc())
    ).all()
    data["grants"] = [grant_vo(item) for item in grants]
    return ok(data)


@router.put("/{skill_id}/status")
def skill_status(
    skill_id: int,
    body: SkillStatusBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    row = load_skill(db, skill_id, tenant_of(actor))
    if row is None:
        return fail(1504, "资源不可用")
    wanted = body.status.strip().upper()
    if wanted not in {"ENABLED", "DISABLED"}:
        return fail(1001, "状态仅支持 ENABLED 或 DISABLED")
    if wanted == "DISABLED":
        if row.status != "PUBLISHED":
            return fail(1001, "仅已发布技能可停用")
        row.status = "DISABLED"
    else:
        if row.status != "DISABLED":
            return fail(1001, "仅已停用技能可启用")
        row.status = "PUBLISHED"
    row.updated_at = utcnow()
    return ok(None)


@router.post("/grant")
def skill_grant(body: SkillGrantBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = load_skill(db, body.skillId, tenant_id)
    if row is None:
        return fail(1001, "技能不存在")
    if row.status != "PUBLISHED":
        return fail(1001, "未过审不得分发（BR-025）")
    expire_at = None
    if (body.expireAt or "").strip():
        expire_at = parse_expire(body.expireAt)
        if expire_at is None:
            return fail(1001, "有效期格式应为 YYYY-MM-DD")
    if body.allStaff:
        exists = db.scalar(
            select(AirSkillGrant).where(
                AirSkillGrant.skill_id == row.id,
                AirSkillGrant.deleted == 0,
                AirSkillGrant.tenant_id == tenant_id,
                AirSkillGrant.status == "ACTIVE",
                AirSkillGrant.all_staff == 1,
            )
        )
        if exists is not None:
            return fail(1001, "授权已存在")
        grant_type = ""
        grant_id = 0
        grant_name = "全员"
        all_staff = 1
    else:
        grant_type = body.grantType.strip().upper()
        if grant_type not in GRANT_TYPES:
            return fail(1001, "授权类型仅支持 DEPT、ROLE、PERSON")
        grant_name, error = resolve_grant_target(db, tenant_id, grant_type, body.grantId)
        if error:
            return fail(1001, error)
        grant_id = body.grantId
        all_staff = 0
        exists = db.scalar(
            select(AirSkillGrant).where(
                AirSkillGrant.skill_id == row.id,
                AirSkillGrant.deleted == 0,
                AirSkillGrant.tenant_id == tenant_id,
                AirSkillGrant.status == "ACTIVE",
                AirSkillGrant.all_staff == 0,
                AirSkillGrant.grant_type == grant_type,
                AirSkillGrant.grant_id_ref == grant_id,
            )
        )
        if exists is not None:
            return fail(1001, "授权已存在")
    now = utcnow()
    grant = AirSkillGrant(
        skill_id=row.id,
        grant_type=grant_type,
        grant_id_ref=grant_id,
        grant_name=grant_name or "",
        all_staff=all_staff,
        status="ACTIVE",
        expire_at=expire_at,
        granted_by=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(grant)
    db.flush()
    row.grant_count = active_grant_count(db, row.id)
    row.updated_at = now
    sync_id = write_event(
        db,
        tenant_id,
        "SKILL_GRANT",
        {
            "skillId": row.id,
            "grantId": grant.id,
            "grantType": grant_type,
            "grantIdRef": grant_id,
            "allStaff": bool(all_staff),
        },
    )
    data = grant_vo(grant)
    data["syncEventId"] = sync_id
    return ok(data)


@router.delete("/grant/{grant_id}")
def skill_grant_revoke(grant_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    grant = db.get(AirSkillGrant, grant_id)
    if grant is None or grant.deleted or grant.tenant_id != tenant_id:
        return fail(1001, "授权不存在")
    skill = load_skill(db, grant.skill_id, tenant_id)
    if skill is None:
        return fail(1001, "技能不存在")
    if grant.status != "ACTIVE":
        return fail(1001, "授权已收回")
    now = utcnow()
    grant.status = "REVOKED"
    grant.updated_at = now
    db.flush()
    skill.grant_count = active_grant_count(db, skill.id)
    skill.updated_at = now
    write_event(
        db,
        tenant_id,
        "SKILL_GRANT_REVOKED",
        {"skillId": skill.id, "grantId": grant.id, "grantType": grant.grant_type},
    )
    return ok(None)
