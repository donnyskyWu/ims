"""AIR Key 生成 / 换新 / 吊销，以及可注入时钟的 QPM 分钟窗。

契约：POST /air/key/generate（2.4.1）、POST /air/key/{id}/renew（2.4.5，Body 含 qpmLimit）、
POST /air/key/{id}/revoke（2.4.3）。没有单独的「改原 Key 限额」路由，调整限额走换新。
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api import current_user, db_session, fail, ok
from app.core import utcnow
from app.models import AirApiKey, AirAuthFail, AirQpmBucket, Role, User, UserRole

router = APIRouter(prefix="/air/key", tags=["air-key"])

DEFAULT_QPM = 60
AUTH_FAIL_LIMIT = 10
AUTH_FAIL_WINDOW = timedelta(minutes=10)
_clock_override: Callable[[], datetime] | None = None


def set_qpm_clock(clock: Callable[[], datetime] | None) -> None:
    """测试注入分钟窗时钟。生产路径保持 None，走 utcnow。"""
    global _clock_override
    _clock_override = clock


def qpm_now() -> datetime:
    if _clock_override is not None:
        return _clock_override().replace(tzinfo=None)
    return utcnow()


def window_start(moment: datetime | None = None) -> datetime:
    current = moment or qpm_now()
    return current.replace(second=0, microsecond=0)


def hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def mask_key(plain: str) -> str:
    tail = plain[-4:] if len(plain) >= 4 else plain
    return f"air-****…****{tail}"


def parse_expire(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    day = text[:10]
    try:
        parsed = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.replace(hour=23, minute=59, second=59)


def next_key_code(db: Session, tenant_id: int) -> str:
    rows = db.scalars(
        select(AirApiKey.key_code).where(AirApiKey.deleted == 0, AirApiKey.tenant_id == tenant_id)
    ).all()
    highest = 0
    for code in rows:
        if code.startswith("KEY-") and code[4:].isdigit():
            highest = max(highest, int(code[4:]))
    return f"KEY-{highest + 1:04d}"


def config_snippets(plain: str) -> dict[str, str]:
    import json

    payload = {
        "mcpServers": {
            "ims": {
                "url": "/ims/mcp",
                "headers": {"Authorization": f"Bearer {plain}"},
            }
        }
    }
    text = json.dumps(payload, ensure_ascii=False)
    return {name: text for name in ("CURSOR", "CLAUDE_DESKTOP", "WORKBUDDY", "GENERIC")}


def active_key_count(db: Session, tenant_id: int, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AirApiKey)
            .where(
                AirApiKey.deleted == 0,
                AirApiKey.tenant_id == tenant_id,
                AirApiKey.owner_user_id == user_id,
                AirApiKey.status == "ACTIVE",
            )
        )
        or 0
    )


def issue_key(
    db: Session,
    *,
    tenant_id: int,
    user_id: int,
    device_name: str,
    qpm_limit: int,
    expire_at: datetime,
    client_token: str,
) -> tuple[AirApiKey, str]:
    plain = "air-" + secrets.token_urlsafe(24)
    now = utcnow()
    row = AirApiKey(
        key_code=next_key_code(db, tenant_id),
        owner_user_id=user_id,
        key_prefix="air-",
        key_mask=mask_key(plain),
        key_hash=hash_key(plain),
        device_name=device_name,
        qpm_limit=qpm_limit,
        status="ACTIVE",
        whitelist="",
        client_token=client_token,
        expire_at=expire_at,
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row, plain


def plain_vo(row: AirApiKey, plain: str) -> dict:
    return {
        "keyId": row.id,
        "keyCode": row.key_code,
        "keyMask": row.key_mask,
        "plainKey": plain,
        "qpmLimit": int(row.qpm_limit),
        "configSnippets": config_snippets(plain),
    }


class GenerateBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    userId: int
    deviceName: str = "个人通用"
    qpmLimit: int | None = None
    expireAt: str
    clientToken: str
    ipWhitelist: list[str] | None = None


class RenewBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    deviceName: str | None = None
    expireAt: str | None = None
    qpmLimit: int | None = None


class RevokeBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reason: str | None = None


def resolve_qpm(value: int | None) -> int | None:
    if value is None:
        return DEFAULT_QPM
    if value < 1 or value > 100_000:
        return None
    return value


def try_consume_qpm(db: Session, key: AirApiKey) -> bool:
    """当前分钟窗内未达 key.qpm_limit 则 +1。限额每次从行上读，不缓存。"""
    start = window_start()
    limit = int(key.qpm_limit if key.qpm_limit is not None else DEFAULT_QPM)
    row = db.scalar(
        select(AirQpmBucket)
        .where(AirQpmBucket.key_id == key.id, AirQpmBucket.window_start == start)
        .with_for_update()
    )
    if row is None:
        if limit <= 0:
            return False
        db.add(
            AirQpmBucket(
                key_id=key.id,
                window_start=start,
                hit_count=1,
                tenant_id=key.tenant_id,
            )
        )
        db.flush()
        return True
    if row.hit_count >= limit:
        return False
    row.hit_count += 1
    db.flush()
    return True


def note_auth_result(db: Session, key: AirApiKey, *, ok: bool) -> bool:
    """连续认证失败满 10 次（10 分钟内）冻结 Key。成功调用清空计数。返回是否刚刚冻结。"""
    if ok:
        db.execute(delete(AirAuthFail).where(AirAuthFail.key_id == key.id))
        return False
    now = qpm_now()
    cutoff = now - AUTH_FAIL_WINDOW
    db.execute(delete(AirAuthFail).where(AirAuthFail.key_id == key.id, AirAuthFail.failed_at < cutoff))
    db.add(AirAuthFail(key_id=key.id, failed_at=now, tenant_id=key.tenant_id or 0))
    db.flush()
    count = int(
        db.scalar(
            select(func.count())
            .select_from(AirAuthFail)
            .where(AirAuthFail.key_id == key.id, AirAuthFail.failed_at >= cutoff)
        )
        or 0
    )
    if count < AUTH_FAIL_LIMIT or key.status != "ACTIVE":
        return False
    key.status = "FROZEN"
    key.freeze_reason = "认证失败锁定"
    key.updated_at = utcnow()
    _notify_auth_lock(db, key)
    return True


def _notify_auth_lock(db: Session, key: AirApiKey) -> None:
    from app.audit import publish_notify

    owner = db.get(User, key.owner_user_id)
    publish_notify(
        db,
        event_type="AIR_AUTH_LOCK",
        biz_key=f"key:{key.id}:owner",
        receiver=(owner.username if owner is not None else ""),
        receiver_user_id=key.owner_user_id,
        tenant_id=key.tenant_id or 0,
        creator=key.owner_user_id,
    )
    admins = db.scalars(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.role_key == "sys:admin", Role.deleted == 0, User.deleted == 0, User.status == "ENABLED")
    ).all()
    seen = {int(key.owner_user_id)}
    for admin in admins:
        if admin.id in seen:
            continue
        seen.add(admin.id)
        publish_notify(
            db,
            event_type="AIR_AUTH_LOCK",
            biz_key=f"key:{key.id}:audit:{admin.id}",
            receiver=admin.username,
            receiver_user_id=admin.id,
            tenant_id=key.tenant_id or 0,
            creator=key.owner_user_id,
        )


def key_blocked_reason(key: AirApiKey) -> str | None:
    if key.deleted or key.status in {"REVOKED", "FROZEN"}:
        return "REVOKED" if key.status == "REVOKED" else key.status or "REVOKED"
    now = qpm_now()
    if key.expire_at is not None and now > key.expire_at:
        return "EXPIRED"
    if key.grace_until is not None and now > key.grace_until:
        return "GRACE_ENDED"
    return None


@router.post("/generate")
def key_generate(body: GenerateBody, db: Session = Depends(db_session), actor: User = Depends(current_user)):
    tenant_id = actor.tenant_id or 0
    token = body.clientToken.strip()
    if not token:
        return fail(1001, "clientToken 必填")
    if body.ipWhitelist:
        return fail(1001, "白名单总开关未开启，不可填写 ipWhitelist")
    device = (body.deviceName or "").strip() or "个人通用"
    qpm = resolve_qpm(body.qpmLimit)
    if qpm is None:
        return fail(1001, "QPM 限额须为 1 到 100000 的整数")
    expire_at = parse_expire(body.expireAt)
    if expire_at is None:
        return fail(1001, "有效期必填，格式 YYYY-MM-DD")
    owner = db.get(User, body.userId)
    if owner is None or owner.deleted or (owner.tenant_id or 0) != tenant_id or owner.status != "ENABLED":
        return fail(1001, "归属人员不存在或已停用")
    reused = db.scalar(
        select(AirApiKey).where(
            AirApiKey.deleted == 0,
            AirApiKey.tenant_id == tenant_id,
            AirApiKey.client_token == token,
        )
    )
    if reused is not None:
        return fail(1001, "clientToken 已使用，明文不可再次展示（BR-020）")
    if active_key_count(db, tenant_id, owner.id) >= 1:
        return fail(1001, "该人员已有启用 Key，请走换新（BR-019）")
    row, plain = issue_key(
        db,
        tenant_id=tenant_id,
        user_id=owner.id,
        device_name=device,
        qpm_limit=qpm,
        expire_at=expire_at,
        client_token=token,
    )
    return ok(plain_vo(row, plain))


@router.post("/{key_id}/renew")
def key_renew(
    key_id: int,
    body: RenewBody,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = actor.tenant_id or 0
    old = db.get(AirApiKey, key_id)
    if old is None or old.deleted or old.tenant_id != tenant_id:
        return fail(1001, "Key 不存在")
    if old.status == "REVOKED":
        return fail(1001, "已吊销的 Key 不可换新")
    if active_key_count(db, tenant_id, old.owner_user_id) >= 3:
        return fail(1001, "设备维度最多 3 把 Key（BR-019）")
    qpm = int(old.qpm_limit if old.qpm_limit is not None else DEFAULT_QPM)
    if body.qpmLimit is not None:
        parsed = resolve_qpm(body.qpmLimit)
        if parsed is None:
            return fail(1001, "QPM 限额须为 1 到 100000 的整数")
        qpm = parsed
    expire_at = old.expire_at
    if body.expireAt:
        parsed_expire = parse_expire(body.expireAt)
        if parsed_expire is None:
            return fail(1001, "有效期格式 YYYY-MM-DD")
        expire_at = parsed_expire
    if expire_at is None:
        return fail(1001, "有效期必填")
    device = (body.deviceName or "").strip() or old.device_name or "个人通用"
    row, plain = issue_key(
        db,
        tenant_id=tenant_id,
        user_id=old.owner_user_id,
        device_name=device,
        qpm_limit=qpm,
        expire_at=expire_at,
        client_token="",
    )
    old.grace_until = qpm_now() + timedelta(hours=24)
    old.updated_at = utcnow()
    return ok(plain_vo(row, plain))


@router.post("/{key_id}/revoke")
def key_revoke(
    key_id: int,
    body: RevokeBody | None = None,
    db: Session = Depends(db_session),
    actor: User = Depends(current_user),
):
    tenant_id = actor.tenant_id or 0
    row = db.get(AirApiKey, key_id)
    if row is None or row.deleted or row.tenant_id != tenant_id:
        return fail(1001, "Key 不存在")
    if row.status == "REVOKED":
        return ok(None)
    row.status = "REVOKED"
    row.updated_at = utcnow()
    return ok(None)
