"""系统参数运行时解析：DB 行值 > 环境变量 IMS_* > 注册默认值。"""

from __future__ import annotations

import os
import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import SessionLocal

SECRET_MASK = "********"

# param_key -> (env_var, default when no DB row and env empty)
PARAM_ENV_DEFAULT: dict[str, tuple[str | None, str]] = {
    "dingtalk.corpId": ("IMS_DINGTALK_CORP_ID", "ims-corp"),
    "dingtalk.clientId": ("IMS_DINGTALK_CLIENT_ID", ""),
    "dingtalk.clientSecret": ("IMS_DINGTALK_CLIENT_SECRET", ""),
    "dingtalk.agentId": ("IMS_DINGTALK_AGENT_ID", ""),
    "dingtalk.appId": ("IMS_DINGTALK_APP_ID", ""),
    "dingtalk.callbackToken": ("IMS_DINGTALK_TOKEN", "ims-dev-dingtalk-token"),
    "dingtalk.callbackAesKey": (
        "IMS_DINGTALK_AES_KEY",
        "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG",
    ),
    "dingtalk.l3Enabled": ("IMS_DINGTALK_L3", ""),
    "football.webapiBaseUrl": ("IMS_FOOTBALL_WEBAPI_BASE_URL", ""),
    "bi.dingtalk.webhook.url": ("IMS_BI_DINGTALK_WEBHOOK_URL", ""),
    "content.ai.baseUrl": ("IMS_CONTENT_AI_BASE_URL", ""),
    "content.ai.tokenSecret": ("IMS_CONTENT_AI_TOKEN", ""),
    "comfyui.baseUrl": ("IMS_COMFYUI_BASE_URL", ""),
    "comfyui.tokenSecret": ("IMS_COMFYUI_TOKEN", ""),
}

SECRET_PARAM_KEYS = frozenset(
    {
        "dingtalk.clientSecret",
        "dingtalk.callbackToken",
        "dingtalk.callbackAesKey",
        "bi.dingtalk.webhook.url",
        "content.ai.tokenSecret",
        "comfyui.tokenSecret",
    }
)

_cache: dict[str, str] = {}
_cache_ts = 0.0
_cache_lock = threading.Lock()
CACHE_TTL_SEC = 5.0


def invalidate_param_cache() -> None:
    global _cache_ts
    with _cache_lock:
        _cache.clear()
        _cache_ts = 0.0


def is_secret_param(key: str) -> bool:
    return key in SECRET_PARAM_KEYS or key.endswith("Secret") or ".secret" in key


def mask_secret_value(value: str | None) -> str:
    if not (value or "").strip():
        return ""
    return SECRET_MASK


def _registry(key: str) -> tuple[str | None, str]:
    return PARAM_ENV_DEFAULT.get(key, (None, ""))


def _db_param_value(db: Session, key: str) -> str | None:
    from app.models import SysParam

    row = db.scalar(select(SysParam).where(SysParam.param_key == key))
    if row is None:
        return None
    return row.param_value if row.param_value is not None else ""


def _resolve(key: str, default: str | None, db: Session) -> str:
    env_name, reg_default = _registry(key)
    fallback = reg_default if default is None else default

    db_val = _db_param_value(db, key)
    if db_val is not None and db_val.strip():
        return db_val.strip()
    if env_name:
        env_val = (os.environ.get(env_name) or "").strip()
        if env_val:
            return env_val
    return fallback


def get_param(key: str, default: str | None = None, *, db: Session | None = None) -> str:
    global _cache_ts
    if db is not None:
        return _resolve(key, default, db)

    now = time.monotonic()
    with _cache_lock:
        if _cache_ts and (now - _cache_ts) < CACHE_TTL_SEC and key in _cache:
            return _cache[key]

    session = SessionLocal()
    try:
        resolved = _resolve(key, default, session)
    finally:
        session.close()

    with _cache_lock:
        _cache[key] = resolved
        _cache_ts = now
    return resolved


def param_bool(key: str, *, db: Session | None = None) -> bool:
    raw = get_param(key, db=db).strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    if key == "dingtalk.l3Enabled":
        return dingtalk_l3_enabled(db=db)
    return False


def dingtalk_l3_enabled(*, db: Session | None = None) -> bool:
    raw = get_param("dingtalk.l3Enabled", db=db).strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    corp = get_param("dingtalk.corpId", db=db).strip()
    client_id = get_param("dingtalk.clientId", db=db).strip()
    secret = get_param("dingtalk.clientSecret", db=db).strip()
    return bool(corp and client_id and secret)


def param_display_value(key: str, raw: str | None) -> str:
    text = raw if raw is not None else ""
    if is_secret_param(key) and text.strip():
        return SECRET_MASK
    return text
