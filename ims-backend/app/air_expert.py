"""AIR 专家库 · 专家包组装与授权（W9-7 airExpert）。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirExpert, AirKb, AirSkill, User

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
    grantType: str = "USER"
    grantId: int
    expireAt: str = ""
    roleTemplateId: int | None = None


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


def assemble_preview(row: AirExpert, skills: list[AirSkill], kbs: list[AirKb]) -> dict:
    return {
        "systemPrompt": row.system_prompt,
        "skillRefs": [
            {"code": s.skill_no, "name": s.skill_name, "ver": s.version_label} for s in skills
        ],
        "kbRefs": [{"id": k.id, "name": k.kb_name, "secretLevel": k.secret_level} for k in kbs],
        "guidelines": "experts.assemble 仅下发组装包（system_prompt + 技能契约）；网关不执行模型（D2/BR-034）。",
    }


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
    if not name or not prompt:
        return fail(1001, "名称与 System Prompt 必填")
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
    data["assemblePreview"] = assemble_preview(row, skills, kbs)
    return ok(data)


@router.post("/grant")
def expert_grant(body: ExpertGrantBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    row = db.get(AirExpert, body.expertId)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "专家不存在")
    if row.status != "PUBLISHED":
        return fail(1001, "专家未发布不可授权")
    if body.grantId <= 0:
        return fail(1008, "授权对象无效")
    row.grant_count = int(row.grant_count or 0) + 1
    row.updated_at = utcnow()
    grant_id = row.id * 10000 + row.grant_count
    return ok({"grantId": grant_id, "status": "ACTIVE", "syncEventId": f"air-grant-{uuid.uuid4().hex[:12]}"})
