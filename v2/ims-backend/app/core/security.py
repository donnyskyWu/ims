"""密码、令牌。"""
from __future__ import annotations

import re
import secrets
import string
import uuid

import bcrypt
import jwt

from app.core.clock import now
from app.core.config import get_settings

_HASH_CACHE: dict[str, str] = {}


def hash_password(password: str) -> str:
    cached = _HASH_CACHE.get(password)
    if cached:
        return cached
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()
    _HASH_CACHE[password] = hashed
    return hashed


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except Exception:
        return False


def validate_password_policy(password: str) -> str | None:
    if not isinstance(password, str) or not 8 <= len(password) <= 32:
        return "密码长度须为 8 到 32 位"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "密码须同时包含字母和数字"
    return None


def random_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if validate_password_policy(value) is None:
            return value


def encode_access(user_id: int, tenant_id: int, session_id: str) -> str:
    settings = get_settings()
    issued = int(now().timestamp())
    payload = {
        "sub": str(user_id),
        "tid": tenant_id,
        "sid": session_id,
        "iat": issued,
        "exp": issued + settings.jwt_access_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
    except jwt.PyJWTError as exc:
        from app.core.errors import BizError

        raise BizError(1002) from exc
    exp = int(payload.get("exp") or 0)
    if int(now().timestamp()) >= exp:
        from app.core.errors import BizError

        raise BizError(1002)
    return payload


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def new_session_id() -> str:
    return uuid.uuid4().hex
