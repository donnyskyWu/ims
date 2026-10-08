"""钉钉回调验签与 AES 解密。只服务组织事件入队，不访问外部用户系统。"""

import base64
import hashlib
import hmac
import os
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.settings_runtime import get_param


def _aes_key_raw() -> str:
    return get_param("dingtalk.callbackAesKey")


def _corp_id() -> str:
    return get_param("dingtalk.corpId")


def _token() -> str:
    return get_param("dingtalk.callbackToken")


def aes_key() -> bytes:
    raw = base64.b64decode(_aes_key_raw() + "=")
    if len(raw) != 32:
        raise ValueError("钉钉 AES Key 长度不正确")
    return raw


def sign(timestamp: str, nonce: str, encrypt: str) -> str:
    parts = sorted([_token(), timestamp, nonce, encrypt])
    return hashlib.sha1("".join(parts).encode()).hexdigest()


def signature_ok(timestamp: str, nonce: str, encrypt: str, given: str) -> bool:
    if not timestamp or not nonce or not encrypt or not given:
        return False
    expect = sign(timestamp, nonce, encrypt)
    if len(expect) != len(given):
        return False
    return hmac.compare_digest(expect, given.lower())


def _pad(data: bytes) -> bytes:
    size = 32
    n = size - (len(data) % size)
    if n == 0:
        n = size
    return data + bytes([n]) * n


def _unpad(data: bytes) -> bytes:
    n = data[-1]
    if n < 1 or n > 32 or data[-n:] != bytes([n]) * n:
        raise ValueError("解密填充无效")
    return data[:-n]


def encrypt_plain(plain: str) -> str:
    key = aes_key()
    body = plain.encode()
    packed = os.urandom(16) + struct.pack("!I", len(body)) + body + _corp_id().encode()
    padded = _pad(packed)
    cipher = Cipher(algorithms.AES(key), modes.CBC(key[:16]))
    enc = cipher.encryptor()
    return base64.b64encode(enc.update(padded) + enc.finalize()).decode()


def decrypt_encrypt(encrypt: str) -> str:
    key = aes_key()
    cipher = Cipher(algorithms.AES(key), modes.CBC(key[:16]))
    dec = cipher.decryptor()
    raw = dec.update(base64.b64decode(encrypt)) + dec.finalize()
    content = _unpad(raw)
    msg_len = struct.unpack("!I", content[16:20])[0]
    return content[20 : 20 + msg_len].decode()


def pack(plain: str, timestamp: str, nonce: str) -> tuple[dict, dict]:
    encrypt = encrypt_plain(plain)
    headers = {"timestamp": timestamp, "nonce": nonce, "sign": sign(timestamp, nonce, encrypt)}
    return {"encrypt": encrypt}, headers
