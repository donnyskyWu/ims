"""组织模块 L3：真实钉钉 API / 生产密钥联调（默认 skip）。"""

from __future__ import annotations

import os

import pytest

from app.settings_runtime import get_param


def _l3_gate() -> tuple[bool, str]:
    l3_flag = get_param("dingtalk.l3Enabled").strip().lower()
    explicit = os.environ.get("IMS_DINGTALK_L3") == "1" or l3_flag in ("true", "1", "yes")
    if not explicit:
        return False, "Set IMS_DINGTALK_L3=1 or dingtalk.l3Enabled=true（系统参数 / .env）"
    pairs = (
        ("dingtalk.clientId", get_param("dingtalk.clientId")),
        ("dingtalk.clientSecret", get_param("dingtalk.clientSecret")),
        ("dingtalk.corpId", get_param("dingtalk.corpId")),
    )
    missing = [label for label, val in pairs if not (val or "").strip()]
    if missing:
        return False, f"Missing credentials: {', '.join(missing)}"
    return True, ""


_ok, _skip_reason = _l3_gate()
pytestmark = [
    pytest.mark.l3,
    pytest.mark.skipif(not _ok, reason=_skip_reason),
]


def test_dingtalk_oauth_access_token_live():
    from app.dingtalk_client import fetch_oauth_access_token

    token, err = fetch_oauth_access_token()
    assert err is None, err
    assert token and len(token) >= 16


def test_dingtalk_app_metadata_present_for_l3():
    assert get_param("dingtalk.agentId").strip(), "dingtalk.agentId required for L3"
    assert get_param("dingtalk.appId").strip(), "dingtalk.appId required for L3"


def test_dingtalk_callback_crypto_roundtrip_with_configured_corp():
    from app.dingtalk_crypto import decrypt_encrypt, pack

    plain = '{"eventType":"l3_ping","dingtalkEventId":"l3-crypto-1"}'
    body, headers = pack(plain, "1700000000", "l3-nonce-1")
    assert headers.get("sign")
    decrypted = decrypt_encrypt(body["encrypt"])
    assert decrypted == plain
