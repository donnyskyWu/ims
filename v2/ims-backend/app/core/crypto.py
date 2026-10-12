"""字段加密 AES-256-GCM 与 HMAC。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import get_settings


def _key_bytes(value: str) -> bytes:
    raw = value.encode()
    if len(raw) == 64 and all(c in "0123456789abcdefABCDEF" for c in value):
        return bytes.fromhex(value)
    return hashlib.sha256(raw).digest()


def encrypt(plain: str, version: str | None = None) -> str:
    settings = get_settings()
    ver = version or "v1"
    key = _key_bytes(settings.field_keys.get(ver) or settings.field_key)
    nonce = os.urandom(12)
    token = AESGCM(key).encrypt(nonce, plain.encode(), None)
    blob = base64.b64encode(nonce + token).decode()
    return f"{ver}:{blob}"


def decrypt(stored: str) -> str:
    settings = get_settings()
    ver, blob = stored.split(":", 1)
    raw = base64.b64decode(blob)
    nonce, token = raw[:12], raw[12:]
    key = _key_bytes(settings.field_keys.get(ver) or settings.field_key)
    return AESGCM(key).decrypt(nonce, token, None).decode()


def hmac_hash(plain: str) -> str:
    key = _key_bytes(get_settings().hash_key)
    return hmac.new(key, plain.encode(), hashlib.sha256).hexdigest()
