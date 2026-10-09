"""AIR 模型与提示词配置（W9-8 airCfg · OPS M8 收编首片）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.corp import page_args, paged, tenant_of, user_names
from app.models import AirApiKey, AirAuditLog, AirModelConfig, AirPromptConfig, User

router = APIRouter(prefix="/air/cfg", tags=["air-cfg"])

BJ = timezone(timedelta(hours=8))


class ModelSaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    vendor: str
    modelName: str
    useCase: str = "CHAT"
    endpointUrl: str = ""
    status: str = "CONNECTED"


class PromptSaveBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    scene: str
    docType: str = ""
    versionLabel: str = "v1.0"
    content: str
    status: str = "ENABLED"


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def next_model_code(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(AirModelConfig).where(
            AirModelConfig.deleted == 0, AirModelConfig.tenant_id == tenant_id
        )
    )
    return f"MDL-{int(count or 0) + 1:04d}"


def next_prompt_code(db: Session, tenant_id: int) -> str:
    count = db.scalar(
        select(func.count()).select_from(AirPromptConfig).where(
            AirPromptConfig.deleted == 0, AirPromptConfig.tenant_id == tenant_id
        )
    )
    return f"PRM-{int(count or 0) + 1:04d}"


def model_vo(row: AirModelConfig, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "configCode": row.config_code,
        "vendor": row.vendor,
        "modelName": row.model_name,
        "useCase": row.use_case,
        "endpointUrl": row.endpoint_url,
        "status": row.status,
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }


def prompt_vo(row: AirPromptConfig, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "promptCode": row.prompt_code,
        "scene": row.scene,
        "docType": row.doc_type,
        "versionLabel": row.version_label,
        "content": row.content,
        "status": row.status,
        "creatorName": names.get(row.creator_id, ""),
        "updatedAt": iso(row.updated_at),
    }


def seed_defaults(db: Session, tenant_id: int, creator_id: int) -> None:
    has_model = db.scalar(
        select(func.count()).select_from(AirModelConfig).where(
            AirModelConfig.deleted == 0, AirModelConfig.tenant_id == tenant_id
        )
    )
    if not has_model:
        now = utcnow()
        db.add(
            AirModelConfig(
                config_code="MDL-0001",
                vendor="QWEN",
                model_name="qwen-plus",
                use_case="CHAT",
                endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                status="CONNECTED",
                creator_id=creator_id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    has_prompt = db.scalar(
        select(func.count()).select_from(AirPromptConfig).where(
            AirPromptConfig.deleted == 0, AirPromptConfig.tenant_id == tenant_id
        )
    )
    if not has_prompt:
        now = utcnow()
        db.add(
            AirPromptConfig(
                prompt_code="PRM-0001",
                scene="内容排版",
                doc_type="ARTICLE",
                version_label="v1.0",
                content="你是神鱼体育内容助手，输出简洁 Markdown。",
                status="ENABLED",
                creator_id=creator_id,
                tenant_id=tenant_id,
                created_at=now,
                updated_at=now,
            )
        )
    db.flush()


@router.get("/model/page")
def model_page(
    keyword: str | None = None,
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_defaults(db, tenant_id, actor.id)
    q = select(AirModelConfig).where(AirModelConfig.deleted == 0, AirModelConfig.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((AirModelConfig.model_name.like(kw)) | (AirModelConfig.vendor.like(kw)))
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(AirModelConfig.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([model_vo(r, names) for r in rows], total, page_no, size)


@router.post("/model")
def model_create(body: ModelSaveBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    name = body.modelName.strip()
    vendor = body.vendor.strip()
    if not vendor or not name:
        return fail(1001, "厂商与模型名必填")
    now = utcnow()
    row = AirModelConfig(
        config_code=next_model_code(db, tenant_id),
        vendor=vendor,
        model_name=name,
        use_case=body.useCase.strip() or "CHAT",
        endpoint_url=body.endpointUrl.strip(),
        status=body.status.strip() or "CONNECTED",
        creator_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.creator_id])
    return ok(model_vo(row, names))


@router.put("/model/{model_id}")
def model_update(
    model_id: int, body: ModelSaveBody, db: Session = Depends(db_session), actor: User = Depends(current_user)
):
    tenant_id = tenant_of(actor)
    row = db.get(AirModelConfig, model_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "配置不存在")
    row.vendor = body.vendor.strip() or row.vendor
    row.model_name = body.modelName.strip() or row.model_name
    row.use_case = body.useCase.strip() or row.use_case
    row.endpoint_url = body.endpointUrl.strip()
    row.status = body.status.strip() or row.status
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    return ok(model_vo(row, names))


@router.get("/prompt/page")
def prompt_page(
    keyword: str | None = None,
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_defaults(db, tenant_id, actor.id)
    q = select(AirPromptConfig).where(AirPromptConfig.deleted == 0, AirPromptConfig.tenant_id == tenant_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where((AirPromptConfig.scene.like(kw)) | (AirPromptConfig.content.like(kw)))
    page_no, size = page_args(pageNo, pageSize)
    stmt = q.order_by(AirPromptConfig.id.desc())
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.creator_id for r in rows])
    return paged([prompt_vo(r, names) for r in rows], total, page_no, size)


@router.post("/prompt")
def prompt_create(body: PromptSaveBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = tenant_of(actor)
    if not body.scene.strip() or not body.content.strip():
        return fail(1001, "场景与提示词正文必填")
    now = utcnow()
    row = AirPromptConfig(
        prompt_code=next_prompt_code(db, tenant_id),
        scene=body.scene.strip(),
        doc_type=body.docType.strip(),
        version_label=body.versionLabel.strip() or "v1.0",
        content=body.content.strip(),
        status=body.status.strip() or "ENABLED",
        creator_id=actor.id,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    names = user_names(db, [row.creator_id])
    return ok(prompt_vo(row, names))


@router.put("/prompt/{prompt_id}")
def prompt_update(
    prompt_id: int, body: PromptSaveBody, db: Session = Depends(db_session), actor: User = Depends(current_user)
):
    tenant_id = tenant_of(actor)
    row = db.get(AirPromptConfig, prompt_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "提示词不存在")
    row.scene = body.scene.strip() or row.scene
    row.doc_type = body.docType.strip()
    row.version_label = body.versionLabel.strip() or row.version_label
    row.content = body.content.strip() or row.content
    row.status = body.status.strip() or row.status
    row.updated_at = utcnow()
    names = user_names(db, [row.creator_id])
    return ok(prompt_vo(row, names))


def seed_air_keys(db: Session, tenant_id: int, actor_id: int) -> None:
    has = db.scalar(
        select(func.count()).select_from(AirApiKey).where(AirApiKey.deleted == 0, AirApiKey.tenant_id == tenant_id)
    )
    if has:
        return
    now = utcnow()
    db.add(
        AirApiKey(
            key_code="KEY-0001",
            owner_user_id=actor_id,
            key_prefix="ims_sk_••••",
            key_mask="ims_sk_••••",
            device_name="个人通用",
            qpm_limit=60,
            status="ACTIVE",
            whitelist="mcp.content,mcp.report",
            last_used_at=now,
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()


def seed_air_audit(db: Session, tenant_id: int, actor_id: int) -> None:
    has = db.scalar(
        select(func.count()).select_from(AirAuditLog).where(AirAuditLog.deleted == 0, AirAuditLog.tenant_id == tenant_id)
    )
    if has:
        return
    now = utcnow()
    db.add(
        AirAuditLog(
            trace_id="tr-w9-demo",
            scene="内容排版",
            model_name="qwen-plus",
            token_in=820,
            token_out=410,
            latency_ms=1260,
            status="OK",
            operator_user_id=actor_id,
            tenant_id=tenant_id,
            created_at=now,
        )
    )
    db.flush()


def key_vo(row: AirApiKey, names: dict[int, str], accounts: dict[int, str] | None = None) -> dict:
    mask = row.key_mask or row.key_prefix
    return {
        "id": row.id,
        "keyCode": row.key_code,
        "ownerUserId": row.owner_user_id,
        "ownerName": names.get(row.owner_user_id, ""),
        "ownerUsername": (accounts or {}).get(row.owner_user_id, ""),
        "keyPrefix": row.key_prefix,
        "keyMask": mask,
        "deviceName": row.device_name or "",
        "qpmLimit": int(row.qpm_limit if row.qpm_limit is not None else 60),
        "status": row.status,
        "freezeReason": row.freeze_reason or "",
        "whitelist": row.whitelist,
        "expireAt": iso(row.expire_at) if row.expire_at else "",
        "graceUntil": iso(row.grace_until) if row.grace_until else "",
        "lastUsedAt": iso(row.last_used_at),
    }


def audit_vo(row: AirAuditLog, names: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "traceId": row.trace_id,
        "scene": row.scene,
        "modelName": row.model_name,
        "tokenIn": row.token_in,
        "tokenOut": row.token_out,
        "latencyMs": row.latency_ms,
        "status": row.status,
        "operatorName": names.get(row.operator_user_id, ""),
        "createdAt": iso(row.created_at),
    }


KEY_STATUSES = frozenset({"ACTIVE", "FROZEN", "REVOKED"})


@router.get("/key/page")
def key_page(
    pageNo: int = 1,
    pageSize: int = 20,
    userName: str | None = None,
    status: str | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_air_keys(db, tenant_id, actor.id)
    wanted = (status or "").strip().upper()
    if wanted and wanted not in KEY_STATUSES:
        return fail(1001, "status 仅支持 ACTIVE、FROZEN、REVOKED")
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AirApiKey).where(AirApiKey.deleted == 0, AirApiKey.tenant_id == tenant_id)
    if wanted:
        stmt = stmt.where(AirApiKey.status == wanted)
    keyword = (userName or "").strip()
    if keyword:
        like = f"%{keyword}%"
        matched_owners = select(User.id).where(
            User.deleted == 0,
            or_(User.username.like(like), User.nickname.like(like)),
        )
        stmt = stmt.where(AirApiKey.owner_user_id.in_(matched_owners))
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.order_by(AirApiKey.id.desc()).offset((page_no - 1) * size).limit(size)).all())
    owner_ids = [r.owner_user_id for r in rows]
    names = user_names(db, owner_ids)
    owners = list(db.scalars(select(User).where(User.id.in_(owner_ids))).all()) if owner_ids else []
    accounts = {row.id: row.username for row in owners}
    return paged([key_vo(r, names, accounts) for r in rows], total, page_no, size)


@router.get("/audit/page")
def audit_page(
    pageNo: int = 1,
    pageSize: int = 20,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = tenant_of(actor)
    seed_air_audit(db, tenant_id, actor.id)
    page_no, size = page_args(pageNo, pageSize)
    stmt = select(AirAuditLog).where(AirAuditLog.deleted == 0, AirAuditLog.tenant_id == tenant_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = list(db.scalars(stmt.order_by(AirAuditLog.id.desc()).offset((page_no - 1) * size).limit(size)).all())
    names = user_names(db, [r.operator_user_id for r in rows])
    return paged([audit_vo(r, names) for r in rows], total, page_no, size)
