#!/usr/bin/env python3
"""快手内部作品与粉丝 Collector 真实冒烟。

只读环境变量，按真实 OpenAPI 各 GET 一次并打印摘要。
不打印 token / cookie，不读写 IMS 业务库。

环境变量：
  IMS_COLLECTOR_BASE_URL              Collector 根地址，例如 http://127.0.0.1:8000
  IMS_COLLECTOR_TOKEN                 Collector API token
  IMS_COLLECTOR_KUAISHOU_ACCOUNT_ID   Collector account_id（query account_id）

运行（在仓库根目录）：
  python scripts/collector_smoke_kuaishou.py

接口：
  GET /api/v1/internal/kuaishou/video-list?account_id=
  GET /api/v1/internal/kuaishou/follower-stats?account_id=
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

MSG_COOKIE = "Cookie 已失效"
MSG_ENGINE = "浏览器引擎不可用"


def _need(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"缺少环境变量 {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def _get(base: str, token: str, path: str, params: dict[str, str]) -> tuple[int, dict]:
    query = urllib.parse.urlencode(params)
    url = f"{base}{path}?{query}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    http_status = 0
    raw = b""
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            http_status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        http_status = exc.code
        raw = exc.read()
    try:
        body = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        body = {}
    return http_status, body if isinstance(body, dict) else {}


def _kind(http_status: int, body: dict) -> str:
    message = str(body.get("message") or body.get("msg") or "")
    code = body.get("code")
    if MSG_COOKIE in message:
        return "cookie_expired"
    if MSG_ENGINE in message:
        return "engine_unavailable"
    if "粉丝统计失败" in message:
        return "follower_failed"
    if code in (0, None) and http_status < 400:
        return "ok"
    return "error"


def _report(name: str, http_status: int, body: dict, secrets: list[str]) -> str:
    message = str(body.get("message") or body.get("msg") or "")
    code = body.get("code")
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    kind = _kind(http_status, body)
    videos = data.get("videos") if isinstance(data.get("videos"), list) else []
    follower_count = data.get("follower_count", data.get("followerCount"))
    public = message
    for secret in secrets:
        if secret:
            public = public.replace(secret, "***")
    print(f"endpoint={name}")
    print(f"http={http_status}")
    print(f"code={code}")
    print(f"status={kind}")
    if public:
        print(f"message={public[:200]}")
    if videos:
        print(f"videos={len(videos)}")
        if isinstance(videos[0], dict):
            print(f"first_video_id={videos[0].get('video_id') or ''}")
    if follower_count is not None:
        print(f"follower_count={follower_count}")
    return kind


def main() -> int:
    base = _need("IMS_COLLECTOR_BASE_URL").rstrip("/")
    token = _need("IMS_COLLECTOR_TOKEN")
    account_id = _need("IMS_COLLECTOR_KUAISHOU_ACCOUNT_ID")
    secrets = [
        token,
        os.environ.get("IMS_COLLECTOR_KUAISHOU_COOKIE", "").strip(),
        os.environ.get("IMS_COLLECTOR_KUAISHOU_AUTH_TOKEN", "").strip(),
    ]
    print(f"base={base}")
    print(f"account_id={account_id}")
    calls = [
        ("video-list", "/api/v1/internal/kuaishou/video-list"),
        ("follower-stats", "/api/v1/internal/kuaishou/follower-stats"),
    ]
    failed = False
    try:
        for name, path in calls:
            http_status, body = _get(base, token, path, {"account_id": account_id})
            if _report(name, http_status, body, secrets) != "ok":
                failed = True
    except urllib.error.URLError as exc:
        print(f"status=error message=无法连接 Collector ({exc.reason})")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
