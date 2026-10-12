"""登录会话。容量挤掉最早会话返回 1003；管理员下线返回 1002。"""
from __future__ import annotations

import json
from datetime import timedelta

from app.core.clock import now
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.errors import BizError
from app.core.redis_client import get_redis
from app.core.security import decode_access, encode_access, new_refresh_token, new_session_id

MAX_SESSIONS = 3


def _user_key(uid: int) -> str:
    return f"ims:user:sids:{uid}"


def _load_list(uid: int) -> list[dict]:
    raw = get_redis().get(_user_key(uid))
    if not raw:
        return []
    return json.loads(raw)


def _save_list(uid: int, items: list[dict]) -> None:
    get_redis().set(_user_key(uid), json.dumps(items), ex=8 * 86400)


def assert_account_can_login(user) -> None:
    """冻结、离职不能登录，也不发仅工作台的会话。"""
    if getattr(user, "status", None) in {"FROZEN", "RESIGNED"}:
        raise BizError(1216)


def issue_session(user, *, keep_sid: str | None = None) -> dict:
    assert_account_can_login(user)
    redis = get_redis()
    settings = get_settings()
    sid = keep_sid or new_session_id()
    refresh = new_refresh_token()
    stamp = int(now().timestamp())
    items = _load_list(user.id)
    if keep_sid is None:
        items.append({"sid": sid, "at": stamp})
        while len(items) > MAX_SESSIONS:
            old = items.pop(0)
            redis.set(f"ims:sess:kick:{old['sid']}", "1", ex=8 * 86400)
            redis.delete(f"ims:sess:{old['sid']}")
        _save_list(user.id, items)
    redis.set(
        f"ims:sess:{sid}",
        json.dumps({"uid": user.id, "tid": user.tenant_id, "at": stamp}),
        ex=8 * 86400,
    )
    redis.set(
        f"ims:refresh:{refresh}",
        json.dumps({"sid": sid, "uid": user.id, "tid": user.tenant_id, "exp": stamp + settings.jwt_refresh_seconds}),
        ex=settings.jwt_refresh_seconds,
    )
    return {
        "accessToken": encode_access(user.id, user.tenant_id, sid),
        "refreshToken": refresh,
        "expiresIn": settings.jwt_access_seconds,
        "pwdResetRequired": bool(user.pwd_reset_required),
        "sessionId": sid,
    }


def revoke_sid(uid: int, sid: str) -> None:
    redis = get_redis()
    redis.delete(f"ims:sess:{sid}")
    items = [item for item in _load_list(uid) if item["sid"] != sid]
    _save_list(uid, items)


def revoke_user(uid: int, *, except_sid: str | None = None) -> None:
    redis = get_redis()
    kept = []
    for item in _load_list(uid):
        if item["sid"] == except_sid:
            kept.append(item)
            continue
        redis.delete(f"ims:sess:{item['sid']}")
    _save_list(uid, kept)


def load_access(token: str) -> RequestContext:
    payload = decode_access(token)
    sid = payload["sid"]
    uid = int(payload["sub"])
    tid = int(payload["tid"])
    redis = get_redis()
    if redis.get(f"ims:sess:kick:{sid}"):
        raise BizError(1003)
    raw = redis.get(f"ims:sess:{sid}")
    if not raw:
        raise BizError(1002)
    from app.services.principal import build_principal

    ctx = build_principal(uid, tid)
    ctx.session_id = sid
    return ctx


def rotate_refresh(token: str) -> dict:
    redis = get_redis()
    if redis.get(f"ims:refresh:used:{token}"):
        raise BizError(1002)
    raw = redis.get(f"ims:refresh:{token}")
    if not raw:
        raise BizError(1002)
    payload = json.loads(raw)
    if int(now().timestamp()) > int(payload["exp"]):
        raise BizError(1002)
    sid = payload["sid"]
    if redis.get(f"ims:sess:kick:{sid}") or not redis.get(f"ims:sess:{sid}"):
        raise BizError(1002)
    redis.delete(f"ims:refresh:{token}")
    redis.set(f"ims:refresh:used:{token}", "1", ex=8 * 86400)
    from app.domains.system.model import User
    from app.db.session import get_session

    user = get_session().get(User, int(payload["uid"]))
    if user is None or user.deleted:
        raise BizError(1002)
    if user.status in {"FROZEN", "RESIGNED"}:
        redis.delete(f"ims:refresh:{token}")
        redis.set(f"ims:refresh:used:{token}", "1", ex=8 * 86400)
        revoke_user(user.id)
        raise BizError(1216)
    _ensure_tenant_open(user.tenant_id)
    return issue_session(user, keep_sid=sid)


def _ensure_tenant_open(tenant_id: int) -> None:
    from app.domains.system.model import Tenant
    from app.db.session import get_session

    tenant = get_session().get(Tenant, tenant_id)
    if tenant is None:
        raise BizError(1008, "所属组织已停用")
    if tenant.status != "ENABLED":
        raise BizError(1008, "所属组织已停用")
    if tenant.expire_time is not None and tenant.expire_time <= now().replace(tzinfo=None):
        raise BizError(1008, "所属组织已停用")


def assert_tenant_open(tenant_id: int) -> None:
    _ensure_tenant_open(tenant_id)
