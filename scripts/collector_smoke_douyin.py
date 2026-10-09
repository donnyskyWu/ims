#!/usr/bin/env python3
"""抖音内部作品 Collector 真实冒烟。

只读环境变量，调用一次内部作品接口并打印摘要。
不打印 token / cookie，不读写 IMS 业务库。

环境变量：
  IMS_COLLECTOR_BASE_URL         Collector 根地址，例如 http://127.0.0.1:8000
  IMS_COLLECTOR_TOKEN            Collector API token
  IMS_COLLECTOR_DOUYIN_COOKIE    抖音 cookie
  IMS_COLLECTOR_DOUYIN_USER_ID   抖音平台账号 id（user_id）

运行（在仓库根目录）：
  python scripts/collector_smoke_douyin.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PATH = "/api/v1/internal/douyin/videos"
MSG_COOKIE = "Cookie 已失效"
MSG_ENGINE = "浏览器引擎不可用"


def _need(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"缺少环境变量 {name}", file=sys.stderr)
        raise SystemExit(2)
    return value


def main() -> int:
    base = _need("IMS_COLLECTOR_BASE_URL").rstrip("/")
    token = _need("IMS_COLLECTOR_TOKEN")
    cookie = _need("IMS_COLLECTOR_DOUYIN_COOKIE")
    user_id = _need("IMS_COLLECTOR_DOUYIN_USER_ID")
    payload = json.dumps(
        {"user_id": user_id, "cookie": cookie},
        ensure_ascii=False,
    ).encode()
    request = urllib.request.Request(
        f"{base}{PATH}",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
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
    except urllib.error.URLError as exc:
        print(f"base={base}")
        print(f"user_id={user_id}")
        print(f"status=error message=无法连接 Collector ({exc.reason})")
        return 1
    try:
        body = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    message = str(body.get("message") or body.get("msg") or "")
    code = body.get("code")
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    videos = data.get("videos") if isinstance(data.get("videos"), list) else []
    if MSG_COOKIE in message:
        kind = "cookie_expired"
    elif MSG_ENGINE in message:
        kind = "engine_unavailable"
    elif code in (0, None) and http_status < 400:
        kind = "ok"
    else:
        kind = "error"
    print(f"base={base}")
    print(f"user_id={user_id}")
    print(f"http={http_status}")
    print(f"code={code}")
    print(f"status={kind}")
    public = message
    for secret in (cookie, token):
        if secret:
            public = public.replace(secret, "***")
    if public:
        print(f"message={public[:200]}")
    print(f"videos={len(videos)}")
    if videos and isinstance(videos[0], dict):
        first = videos[0]
        title = str(first.get("title") or "")[:40]
        print(f"first_video_id={first.get('video_id') or ''}")
        print(f"first_title={title}")
    return 0 if kind == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
