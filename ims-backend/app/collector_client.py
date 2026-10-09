"""unify-collector HTTP 客户端。

与本地桩、`scripts/collector_smoke_kuaishou.py`、`scripts/collector_smoke_douyin.py` 使用同一形状：

- `POST /api/v1/accounts/import`
- `GET  /api/v1/accounts/health?account_id=`
- `POST /api/v1/internal/kuaishou/videos`
- `POST /api/v1/internal/douyin/videos`

鉴权头 `Authorization: Bearer <IMS_COLLECTOR_TOKEN>`，地址 `IMS_COLLECTOR_BASE_URL`。
业务错误可以是 HTTP 200，正文 `message` 为「Cookie 已失效」或「浏览器引擎不可用」。
上游若用 4xx/5xx 带同样文案，这里只归类，不向调用方抛未捕获异常。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

IMPORT_PATH = "/api/v1/accounts/import"
HEALTH_PATH = "/api/v1/accounts/health"
KUAISHOU_VIDEOS_PATH = "/api/v1/internal/kuaishou/videos"
DOUYIN_VIDEOS_PATH = "/api/v1/internal/douyin/videos"
INTERNAL_VIDEOS_PATH = KUAISHOU_VIDEOS_PATH

MSG_COOKIE = "Cookie 已失效"
MSG_ENGINE = "浏览器引擎不可用"
CODE_COOKIE = 40101
CODE_ENGINE = 50301


@dataclass
class CollectorCall:
    kind: str
    message: str
    videos: list[dict] = field(default_factory=list)
    collector_account_id: str = ""
    http_status: int = 0


def base_url() -> str:
    return os.environ.get("IMS_COLLECTOR_BASE_URL", "").strip().rstrip("/")


def token() -> str:
    return os.environ.get("IMS_COLLECTOR_TOKEN", "").strip()


def classify(message: str, code: int | None = None) -> str:
    text = message or ""
    if MSG_COOKIE in text or code == CODE_COOKIE:
        return "cookie"
    if MSG_ENGINE in text or code == CODE_ENGINE:
        return "engine"
    return "error"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    secret = token()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    return headers


def _read_body(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _call(method: str, path: str, *, json_body: dict | None = None, params: dict | None = None) -> CollectorCall:
    root = base_url()
    if not root:
        return CollectorCall(kind="error", message="未配置 Collector 地址（IMS_COLLECTOR_BASE_URL）")
    url = f"{root}{path}"
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.request(method, url, headers=_headers(), json=json_body, params=params)
    except httpx.HTTPError:
        return CollectorCall(kind="error", message="无法连接 Collector")
    body = _read_body(response)
    message = str(body.get("message") or body.get("msg") or "")
    code = body.get("code")
    code_int = code if isinstance(code, int) else None
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    kind = "ok"
    if code_int not in (None, 0) or response.status_code >= 400:
        kind = classify(message, code_int)
        if kind == "error" and not message:
            message = f"采集失败（HTTP {response.status_code}）"
    videos = data.get("videos") if isinstance(data.get("videos"), list) else []
    collector_id = str(data.get("collector_account_id") or data.get("collectorAccountId") or "")
    return CollectorCall(
        kind=kind if kind != "ok" or response.status_code < 400 else "error",
        message=message or ("ok" if kind == "ok" else "采集失败"),
        videos=[item for item in videos if isinstance(item, dict)],
        collector_account_id=collector_id,
        http_status=response.status_code,
    )


def import_account(
    *,
    platform_account_id: str,
    credential_ref: str,
    cookie: str,
    auth_token: str,
    platform: str = "kuaishou",
) -> CollectorCall:
    return _call(
        "POST",
        IMPORT_PATH,
        json_body={
            "platform": platform,
            "platform_account_id": platform_account_id,
            "credential_ref": credential_ref,
            "cookie": cookie,
            "auth_token": auth_token,
        },
    )


def account_health(collector_account_id: str) -> CollectorCall:
    return _call("GET", HEALTH_PATH, params={"account_id": collector_account_id})


def kuaishou_internal_videos(*, user_id: str, cookie: str, auth_token: str) -> CollectorCall:
    return _call(
        "POST",
        KUAISHOU_VIDEOS_PATH,
        json_body={"user_id": user_id, "cookie": cookie, "auth_token": auth_token},
    )


def douyin_internal_videos(*, user_id: str, cookie: str, auth_token: str = "") -> CollectorCall:
    body = {"user_id": user_id, "cookie": cookie}
    if auth_token:
        body["auth_token"] = auth_token
    return _call("POST", DOUYIN_VIDEOS_PATH, json_body=body)
