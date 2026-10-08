import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core import JWT_SECRET


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _key() -> bytes:
    return hashlib.sha256(JWT_SECRET.encode()).digest()


def encrypt_text(plain: str) -> str:
    if plain is None:
        return ""
    nonce = os.urandom(12)
    token = AESGCM(_key()).encrypt(nonce, plain.encode(), None)
    return base64.b64encode(nonce + token).decode()


def decrypt_text(token: str) -> str:
    if not token:
        return ""
    raw = base64.b64decode(token.encode())
    nonce, cipher = raw[:12], raw[12:]
    return AESGCM(_key()).decrypt(nonce, cipher, None).decode()
