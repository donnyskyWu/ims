"""AIR 专家库 · 专家包组装与授权（W9-7 airExpert）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.air_skill import (
    dept_ids_of,
    grant_is_current,
    grant_matches,
    parse_expire,
    resolve_grant_target,
    role_ids_of,
    write_event,
)
from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirExpert, AirExpertGrant, AirKb, AirSkill, User

router = APIRouter(prefix="/air/expert", tags=["air-expert"])

BJ = timezone(timedelta(hours=8))
MCP_TOOLS = frozenset({"skills.list", "skills.get", "experts.list", "experts.assemble"})


class ExpertSaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    expertCode: str = ""
    expertName: str
    scene: str = ""
    systemPrompt: str
    skillIds: list[int] = Field(default_factory=list)
    kbIds: list[int] = Field(default_factory=list)
    toolWhitelist: list[str] = Field(default_factory=list)
    ownerUserId: int | None = None


class ExpertGrantBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    expertId: int
    grantType: str = ""
    grantId: int = 0
    expireAt: str = ""
    roleTemplateId: int | None = None


GRANT_TYPES = frozenset({"DEPT", "ROLE", "PERSON"})
ASSEMBLE_GUIDELINES = "experts.assemble 仅下发组装包（system_prompt + 技能契约）；网关不执行模型（D2/BR-034）。"


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_expert_code(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(AirExpert).where(AirExpert.deleted == 0, AirExpert.tenant_id == tenant_id)
    )
    seq = int(count or 0) + 1
    return f"EXP-{seq:04d}"


def bump_ver(ver: str) -> str:
    raw = (ver or "v1.0").lstrip("vV")
    parts = raw.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return "v1.1"
    return f"v{major}.{minor + 1}"


def validate_tools(tools: list[str]) -> str | None:
    for name in tools:
        if name not in MCP_TOOLS:
            return name
    return None


def load_skills(db: Session, tenant_id: int, skill_ids: list[int]) -> tuple[list[AirSkill], str | None]:
    if not skill_ids:
        return [], None
    rows = list(
        db.scalars(
            select(AirSkill).where(
                AirSkill.deleted == 0,
                AirSkill.tenant_id == tenant_id,
                AirSkill.id.in_(skill_ids),
            )
        ).all()
    )
    by_id = {r.id: r for r in rows}
    for sid in skill_ids:
        row = by_id.get(sid)
        if row is None:
            return [], f"技能 id={sid} 不存在"
        if row.status != "PUBLISHED":
            return [], row.skill_name
    return [by_id[s] for s in skill_ids if s in by_id], None


def load_kbs(db: Session, tenant_id: int, kb_ids: list[int]) -> tuple[list[AirKb], str | None]:
    if not kb_ids:
        return [], None
    rows = list(
        db.scalars(
            select(AirKb).where(AirKb.deleted == 0, AirKb.tenant_id == tenant_id, AirKb.id.in_(kb_ids))
        ).all()
    )
    by_id = {r.id: r for r in rows}
    for kid in kb_ids:
        if kid not in by_id:
            return [], f"知识库 id={kid} 不存在"
    return [by_id[k] for k in kb_ids if k in by_id], None


def expert_vo(row: AirExpert, names: dict[int, str], skills: list[AirSkill] | None = None, kbs: list[AirKb] | None = None) -> dict:
    skill_rows = skills or []
    kb_rows = kbs or []
    return {
        "id": row.id,
        "expertCode": row.expert_code,
        "expertName": row.expert_name,
        "scene": row.scene,
        "ver": row.version_label,
        "status": row.status,
        "systemPrompt": row.system_prompt,
        "skillIds": list(row.skill_ids or []),
        "kbIds": list(row.kb_ids or []),
        "toolWhitelist": list(row.tool_whitelist or []),
        "grantCount": row.grant_count,
        "assembleCount": row.assemble_count,
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id, ""),
        "skillChips": [{"id": s.id, "name": s.skill_name, "code": s.skill_no} for s in skill_rows],
        "kbChips": [{"id": k.id, "name": k.kb_name, "secretLevel": k.secret_level} for k in kb_rows],
        "updatedAt": iso(row.updated_at),
    }


def split_mounted_skills(db: Session, tenant_id: int, skill_ids: list[int]) -> tuple[list[AirSkill], int]:
    """已发布技能进入组装包。缺失或未发布的计入过滤命中。不调用模型。"""
    if not skill_ids:
        return [], 0
    rows = list(
        db.scalars(
            select(AirSkill).where(
                AirSkill.deleted == 0,
                AirSkill.tenant_id == tenant_id,
                AirSkill.id.in_(skill_ids),
            )
        ).all()
    )
    by_id = {row.id: row for row in rows}
    kept: list[AirSkill] = []
    dropped = 0
    for skill_id in skill_ids:
        row = by_id.get(skill_id)
        if row is None or row.status != "PUBLISHED":
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def mcp_assemble_package(db: Session, row: AirExpert) -> tuple[dict, int]:
    skills, dropped = split_mounted_skills(db, row.tenant_id, list(row.skill_ids or []))
    package = {
        "systemPrompt": row.system_prompt,
        "skillRefs": [{"code": skill.skill_no, "md": ""} for skill in skills],
        "guidelines": ASSEMBLE_GUIDELINES,
    }
    return package, dropped


def assemble_preview(row: AirExpert, skills: list[AirSkill]) -> dict:
    return {
        "systemPrompt": row.system_prompt,
        "skillRefs": [
            {"code": skill.skill_no, "name": skill.skill_name, "ver": skill.version_label, "md": ""}
            for skill in skills
        ],
        "guidelines": ASSEMBLE_GUIDELINES,
    }


def expert_visible_to(db: Session, expert: AirExpert, user_id: int) -> bool:
    """已发布且命中一条未过期的 ACTIVE 授权。"""
    if expert.deleted or expert.status != "PUBLISHED":
        return False
    now = utcnow()
    grants = db.scalars(
        select(AirExpertGrant).where(
            AirExpertGrant.expert_id == expert.id,
            AirExpertGrant.deleted == 0,
            AirExpertGrant.tenant_id == expert.tenant_id,
            AirExpertGrant.status == "ACTIVE",
        )
    ).all()
    if not grants:
        return False
    dept_ids = dept_ids_of(db, user_id, expert.tenant_id)
    role_ids = role_ids_of(db, user_id)
    return any(grant_matches(item, user_id, dept_ids, role_ids) for item in grants if grant_is_current(item, now))


def expert_grant_vo(row: AirExpertGrant) -> dict:
    return {
        "grantId": row.id,
        "grantType": row.grant_type,
        "grantObjId": row.grant_id_ref,
        "grantName": row.grant_name,
        "expireAt": iso(row.expire_at) if row.expire_at else "",
        "status": row.status,
    }


def active_expert_grants(db: Session, expert_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AirExpertGrant)
            .where(
                AirExpertGrant.expert_id == expert_id,
                AirExpertGrant.deleted == 0,
                AirExpertGrant.status == "ACTIVE",
            )
        )
        or 0
    )


@router.get("/summary")
def expert_summary(db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    total = int(
        db.scalar(
            select(func.count()).select_from(AirExpert).where(AirExpert.deleted == 0, AirExpert.tenant_id == tenant_id)
        )
        or 0
    )
    published = int(
        db.scalar(
            select(func.count())
            .select_from(AirExpert)
            .where(AirExpert.deleted == 0, AirExpert.tenant_id == tenant_id, AirExpert.status == "PUBLISHED")
        )
        or 0
    )
    skill_cnt = int(
        db.scalar(
            select(func.count()).select_from(AirSkill).where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id)
        )
        or 0
    )
    kb_cnt = int(
        db.scalar(select(func.count()).select_from(AirKb).where(AirKb.deleted == 0, AirKb.tenant_id == tenant_id)) or 0
    )
    return ok({"expertCount": total, "publishedCount": published, "skillCount": skill_cnt, "kbCount": kb_cnt})


@router.get("/page")
def expert_page(
    expertName: str | None = None,
    status: str | None = None,
    ownerUserId: int | None = None,
    pageNo: int = 1,
    pageSize: int = 12,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    q = select(AirExpert).where(AirExpert.deleted == 0, AirExpert.tenant_id == tenant_id)
    if expertName:
        kw = f"%{expertName.strip()}%"
        q = q.where(
            (AirExpert.expert_name.like(kw)) | (AirExpert.expert_code.like(kw)) | (AirExpert.scene.like(kw))
        )
    if status:
        q = q.where(AirExpert.status == status.strip().upper())
    if ownerUserId:
        q = q.where(AirExpert.owner_user_id == ownerUserId)
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(AirExpert.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.owner_user_id for r in rows])
    all_skill_ids: set[int] = set()
    all_kb_ids: set[int] = set()
    for r in rows:
        all_skill_ids.update(r.skill_ids or [])
        all_kb_ids.update(r.kb_ids or [])
    skill_map = {}
    if all_skill_ids:
        for s in db.scalars(
            select(AirSkill).where(AirSkill.deleted == 0, AirSkill.tenant_id == tenant_id, AirSkill.id.in_(all_skill_ids))
        ).all():
            skill_map[s.id] = s
    kb_map = {}
    if all_kb_ids:
        for k in db.scalars(
            select(AirKb).where(AirKb.deleted == 0, AirKb.tenant_id == tenant_id, AirKb.id.in_(all_kb_ids))
        ).all():
            kb_map[k.id] = k
    items = []
    for r in rows:
        skills = [skill_map[i] for i in (r.skill_ids or []) if i in skill_map]
        kbs = [kb_map[i] for i in (r.kb_ids or []) if i in kb_map]
        items.append(expert_vo(r, names, skills, kbs))
    return paged(items, total, page_no, size)


@router.post("")
def expert_create(body: ExpertSaveBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    name = body.expertName.strip()
    prompt = body.systemPrompt.strip()
    if not name:
        return fail(1001, "专家名称必填")
    if not body.scene.strip():
        return fail(1001, "适用场景必填")
    if not prompt:
        return fail(1001, "System Prompt 必填")
    bad_tool = validate_tools(body.toolWhitelist)
    if bad_tool:
        return fail(1001, f"工具白名单非法: {bad_tool}")
    skills, skill_err = load_skills(db, tenant_id, body.skillIds)
    if skill_err:
        return fail(1001, f"挂载技能须为已发布: {skill_err}")
    kbs, kb_err = load_kbs(db, tenant_id, body.kbIds)
    if kb_err:
        return fail(1001, kb_err)
    now = utcnow()
    code = body.expertCode.strip() or next_expert_code(db, tenant_id)
    owner = body.ownerUserId or actor.id
    row = AirExpert(
        expert_code=code,
        expert_name=name,
        scene=body.scene.strip(),
        system_prompt=prompt,
        skill_ids=list(body.skillIds),
        kb_ids=list(body.kbIds),
        tool_whitelist=list(body.toolWhitelist) or ["experts.assemble", "skills.get"],
        version_label="v1.0",
        status="DRAFT",
        owner_user_id=owner,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.owner_user_id])
    return ok(expert_vo(row, names, skills, kbs))


@router.put("/{expert_id}")
def expert_update(
    expert_id: int,
    body: ExpertSaveBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    row = db.get(AirExpert, expert_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    name = body.expertName.strip()
    prompt = body.systemPrompt.strip()
    if not name or not prompt or not body.scene.strip():
        return fail(1001, "名称、适用场景与 System Prompt 必填")
    bad_tool = validate_tools(body.toolWhitelist)
    if bad_tool:
        return fail(1001, f"工具白名单非法: {bad_tool}")
    skills, skill_err = load_skills(db, tenant_id, body.skillIds)
    if skill_err:
        return fail(1001, f"挂载技能须为已发布: {skill_err}")
    kbs, kb_err = load_kbs(db, tenant_id, body.kbIds)
    if kb_err:
        return fail(1001, kb_err)
    row.expert_name = name
    row.scene = body.scene.strip()
    row.system_prompt = prompt
    row.skill_ids = list(body.skillIds)
    row.kb_ids = list(body.kbIds)
    row.tool_whitelist = list(body.toolWhitelist) or list(row.tool_whitelist or [])
    row.version_label = bump_ver(row.version_label)
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    return ok(expert_vo(row, names, skills, kbs))


@router.put("/{expert_id}/publish")
def expert_publish(expert_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = db.get(AirExpert, expert_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    if not row.system_prompt.strip():
        return fail(1001, "System Prompt 为空不可发布")
    row.status = "PUBLISHED"
    row.updated_at = utcnow()
    names = user_names(db, [row.owner_user_id])
    skills, _ = load_skills(db, tenant_id, list(row.skill_ids or []))
    kbs, _ = load_kbs(db, tenant_id, list(row.kb_ids or []))
    return ok(expert_vo(row, names, skills, kbs))


@router.get("/{expert_id}")
def expert_detail(expert_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = db.get(AirExpert, expert_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1504, "资源不可用")
    names = user_names(db, [row.owner_user_id])
    skills, _ = load_skills(db, tenant_id, list(row.skill_ids or []))
    kbs, _ = load_kbs(db, tenant_id, list(row.kb_ids or []))
    data = expert_vo(row, names, skills, kbs)
    data["assemblePreview"] = assemble_preview(row, skills)
    grants = db.scalars(
        select(AirExpertGrant)
        .where(
            AirExpertGrant.expert_id == row.id,
            AirExpertGrant.deleted == 0,
            AirExpertGrant.tenant_id == row.tenant_id,
        )
        .order_by(AirExpertGrant.id.desc())
    ).all()
    data["grants"] = [expert_grant_vo(item) for item in grants]
    return ok(data)


@router.post("/grant")
def expert_grant(body: ExpertGrantBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = db.get(AirExpert, body.expertId)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "专家不存在")
    if row.status != "PUBLISHED":
        return fail(1001, "专家未发布不可授权")
    expire_at = None
    if (body.expireAt or "").strip():
        expire_at = parse_expire(body.expireAt)
        if expire_at is None:
            return fail(1001, "有效期格式应为 YYYY-MM-DD")
    grant_type = body.grantType.strip().upper()
    if grant_type not in GRANT_TYPES:
        return fail(1001, "授权类型仅支持 DEPT、ROLE、PERSON")
    grant_name, error = resolve_grant_target(db, tenant_id, grant_type, body.grantId)
    if error:
        return fail(1001, error)
    exists = db.scalar(
        select(AirExpertGrant).where(
            AirExpertGrant.expert_id == row.id,
            AirExpertGrant.deleted == 0,
            AirExpertGrant.tenant_id == tenant_id,
            AirExpertGrant.status == "ACTIVE",
            AirExpertGrant.grant_type == grant_type,
            AirExpertGrant.grant_id_ref == body.grantId,
        )
    )
    if exists is not None:
        return fail(1001, "授权已存在")
    now = utcnow()
    grant = AirExpertGrant(
        expert_id=row.id,
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
    row.grant_count = active_expert_grants(db, row.id)
    row.updated_at = now
    payload = {
        "expertId": row.id,
        "grantId": grant.id,
        "grantType": grant_type,
        "grantIdRef": body.grantId,
    }
    if body.roleTemplateId:
        payload["roleTemplateId"] = body.roleTemplateId
    sync_id = write_event(db, tenant_id, "EXPERT_GRANT", payload)
    data = expert_grant_vo(grant)
    data["syncEventId"] = sync_id
    return ok(data)


@router.delete("/grant/{grant_id}")
def expert_grant_revoke(grant_id: int, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    grant = db.get(AirExpertGrant, grant_id)
    if grant is None or grant.deleted or grant.tenant_id != tenant_id:
        return fail(1001, "授权不存在")
    row = db.get(AirExpert, grant.expert_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "专家不存在")
    if grant.status != "ACTIVE":
        return fail(1001, "授权已收回")
    now = utcnow()
    grant.status = "REVOKED"
    grant.updated_at = now
    db.flush()
    row.grant_count = active_expert_grants(db, row.id)
    row.updated_at = now
    write_event(
        db,
        tenant_id,
        "EXPERT_GRANT_REVOKED",
        {"expertId": row.id, "grantId": grant.id, "grantType": grant.grant_type},
    )
    return ok(None)
