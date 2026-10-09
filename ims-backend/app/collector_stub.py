"""本地 unify-collector 桩。路径与真实内部作品 / 粉丝接口一致。

作品统计（douyin video-stats、douyin accounts/{id}/videos/stats、kuaishou video-stats）
与作品列表的播放 / 点赞 / 评论 / 转发重复，日快照已覆盖，桩不另开这些路径。

`account_id` 含 `COOKIE_EXPIRED` → Cookie 已失效；
含 `ENGINE_DOWN` → 浏览器引擎不可用；
含 `FOLLOWER_FAIL` 时作品仍成功，粉丝统计与粉丝列表返回「粉丝统计失败」。
业务错误用 HTTP 200 + code/message。
"""

from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from app.collector_client import (
    CODE_COOKIE,
    CODE_ENGINE,
    CODE_FOLLOWER,
    DOUYIN_FOLLOWER_STATS_PATH,
    HEALTH_PATH,
    IMPORT_PATH,
    KUAISHOU_FOLLOWER_STATS_PATH,
    KUAISHOU_VIDEO_LIST_PATH,
    MSG_COOKIE,
    MSG_ENGINE,
    MSG_FOLLOWER,
    WECHAT_CHANNELS_FOLLOWER_STATS_PATH,
    WECHAT_CHANNELS_VIDEO_LIST_PATH,
)

DOUYIN_FOLLOWER_COUNT = 12880
KUAISHOU_FOLLOWER_COUNT = 8600
WECHAT_CHANNELS_FOLLOWER_COUNT = 24600

_DOUYIN_VIDEOS = [
    {
        "video_id": "dyv-2001",
        "title": "抖音内部作品甲",
        "cover_url": "",
        "play_count": 2100,
        "like_count": 40,
        "comment_count": 6,
        "share_count": 2,
        "publish_time": "2026-10-03 10:00:00",
        "duration_sec": 18,
    },
    {
        "video_id": "dyv-2002",
        "title": "抖音内部作品乙",
        "cover_url": "",
        "play_count": 960,
        "like_count": 18,
        "comment_count": 2,
        "share_count": 1,
        "publish_time": "2026-10-04 11:20:00",
        "duration_sec": 24,
    },
]

_SUCCESS_VIDEOS = [
    {
        "video_id": "ksv-1001",
        "title": "快手内部作品甲",
        "cover_url": "",
        "play_count": 1200,
        "like_count": 30,
        "comment_count": 4,
        "share_count": 1,
        "publish_time": "2026-10-01 08:00:00",
        "duration_sec": 15,
    },
    {
        "video_id": "ksv-1002",
        "title": "快手内部作品乙",
        "cover_url": "",
        "play_count": 800,
        "like_count": 12,
        "comment_count": 1,
        "share_count": 0,
        "publish_time": "2026-10-02 09:30:00",
        "duration_sec": 21,
    },
]

_DOUYIN_FOLLOWERS = [
    {"follower_id": "dyf-3001", "nickname": "抖音粉丝甲", "followed_at": "2026-10-01 08:00:00"},
    {"follower_id": "dyf-3002", "nickname": "抖音粉丝乙", "followed_at": "2026-10-02 09:00:00"},
]

_WECHAT_VIDEOS = [
    {
        "export_id": "wxv-4001",
        "object_id": "obj-4001",
        "title": "视频号内部作品甲",
        "description": "视频号内部作品甲",
        "create_time": "2026-10-05 12:00:00",
        "read_count": 3200,
        "like_count": 55,
        "fav_count": 4,
        "comment_count": 8,
        "forward_count": 3,
        "cover_url": "",
        "duration": 19,
    },
    {
        "export_id": "wxv-4002",
        "object_id": "obj-4002",
        "title": "视频号内部作品乙",
        "description": "视频号内部作品乙",
        "create_time": "2026-10-06 13:10:00",
        "read_count": 1500,
        "like_count": 22,
        "fav_count": 1,
        "comment_count": 3,
        "forward_count": 1,
        "cover_url": "",
        "duration": 27,
    },
]

_DY_VIDEO_RE = re.compile(r"^/api/v1/internal/douyin/accounts/([^/]+)/videos$")
_DY_FOLLOWER_RE = re.compile(r"^/api/v1/internal/douyin/accounts/([^/]+)/followers$")


def scenario_of(*parts: str, follower: bool = False) -> str:
    blob = " ".join(part for part in parts if part)
    if "COOKIE_EXPIRED" in blob:
        return "cookie"
    if "ENGINE_DOWN" in blob:
        return "engine"
    if follower and "FOLLOWER_FAIL" in blob:
        return "follower_fail"
    return "ok"


def collector_account_id(platform_account_id: str, platform: str = "kuaishou") -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", platform_account_id or "")[:80] or "unknown"
    if platform == "douyin":
        slug = "douyin"
    elif platform in {"wechat_channels", "wechat-channels"}:
        slug = "wechat_channels"
    else:
        slug = "kuaishou"
    return f"acc_{slug}_{safe}"


def _business(kind: str) -> tuple[int, str]:
    if kind == "cookie":
        return CODE_COOKIE, MSG_COOKIE
    if kind == "engine":
        return CODE_ENGINE, MSG_ENGINE
    if kind == "follower_fail":
        return CODE_FOLLOWER, MSG_FOLLOWER
    return 0, "ok"


def _stats(account_id: str, platform: str) -> dict:
    if platform == "douyin":
        return {
            "account_id": account_id,
            "follower_count": DOUYIN_FOLLOWER_COUNT,
            "following_count": 36,
            "new_follower_count": 12,
        }
    if platform == "wechat_channels":
        return {
            "account_id": account_id,
            "total_followers": WECHAT_CHANNELS_FOLLOWER_COUNT,
            "new_followers_today": 18,
            "unfollowed_today": 2,
            "net_growth_today": 16,
            "stat_date": "",
        }
    return {
        "account_id": account_id,
        "follower_count": KUAISHOU_FOLLOWER_COUNT,
        "following_count": 20,
        "new_follower_count": 5,
    }


class CollectorStub:
    def __init__(self) -> None:
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port = 0

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        handler = _handler_factory()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = int(self.httpd.server_address[1])
        self.thread = threading.Thread(target=self.httpd.serve_forever, name="collector-stub", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None


def start_embedded_stub() -> None:
    """IMS_COLLECTOR_STUB=1 且未指定地址时，在 API 进程内拉起桩。"""
    flag = os.environ.get("IMS_COLLECTOR_STUB", "").strip().lower()
    if flag not in {"1", "true", "yes"}:
        return
    if os.environ.get("IMS_COLLECTOR_BASE_URL", "").strip():
        return
    stub = CollectorStub()
    stub.start()
    os.environ["IMS_COLLECTOR_BASE_URL"] = stub.base_url


def _handler_factory():
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:
            return

        def _authorized(self) -> bool:
            expected = os.environ.get("IMS_COLLECTOR_TOKEN", "").strip()
            if not expected:
                return True
            header = self.headers.get("Authorization", "")
            return header == f"Bearer {expected}"

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                data = json.loads(raw.decode())
            except json.JSONDecodeError:
                return {}
            return data if isinstance(data, dict) else {}

        def _send(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _query_account(self) -> str:
            parsed = urlparse(self.path)
            values = parse_qs(parsed.query).get("account_id") or []
            return unquote(values[0]) if values else ""

        def _fail_or_data(self, kind: str, data: dict | None) -> None:
            code, message = _business(kind)
            if kind == "ok":
                self._send(200, {"code": 0, "message": "ok", "data": data})
                return
            self._send(200, {"code": code, "message": message, "data": None})

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path == "/livez":
                self._send(200, {"code": 0, "message": "ok", "data": {"status": "up"}})
                return
            if not self._authorized():
                self._send(401, {"code": 401, "message": "unauthorized", "data": None})
                return
            if path == HEALTH_PATH:
                account_id = self._query_account()
                kind = scenario_of(account_id)
                code, message = _business(kind)
                if kind == "ok":
                    data = {"conn_status": "CONNECTED", "collector_account_id": account_id}
                elif kind == "cookie":
                    data = {"conn_status": "COOKIE_EXPIRED", "collector_account_id": account_id}
                else:
                    data = {"conn_status": "ENGINE_UNAVAILABLE", "collector_account_id": account_id}
                self._send(200, {"code": code, "message": message, "data": data})
                return
            video_match = _DY_VIDEO_RE.match(path)
            follower_match = _DY_FOLLOWER_RE.match(path)
            if video_match:
                account_id = unquote(video_match.group(1))
                kind = scenario_of(account_id)
                if kind == "ok":
                    self._fail_or_data("ok", {"videos": _DOUYIN_VIDEOS})
                else:
                    self._fail_or_data(kind, None)
                return
            if follower_match:
                account_id = unquote(follower_match.group(1))
                kind = scenario_of(account_id, follower=True)
                if kind == "ok":
                    self._fail_or_data("ok", {"followers": _DOUYIN_FOLLOWERS})
                else:
                    self._fail_or_data(kind, None)
                return
            if path == DOUYIN_FOLLOWER_STATS_PATH:
                account_id = self._query_account()
                kind = scenario_of(account_id, follower=True)
                self._fail_or_data(kind, _stats(account_id, "douyin") if kind == "ok" else None)
                return
            if path == KUAISHOU_VIDEO_LIST_PATH:
                account_id = self._query_account()
                kind = scenario_of(account_id)
                self._fail_or_data(kind, {"videos": _SUCCESS_VIDEOS} if kind == "ok" else None)
                return
            if path == KUAISHOU_FOLLOWER_STATS_PATH:
                account_id = self._query_account()
                kind = scenario_of(account_id, follower=True)
                self._fail_or_data(kind, _stats(account_id, "kuaishou") if kind == "ok" else None)
                return
            if path == WECHAT_CHANNELS_VIDEO_LIST_PATH:
                account_id = self._query_account()
                kind = scenario_of(account_id)
                self._fail_or_data(kind, {"videos": _WECHAT_VIDEOS, "total": len(_WECHAT_VIDEOS)} if kind == "ok" else None)
                return
            if path == WECHAT_CHANNELS_FOLLOWER_STATS_PATH:
                account_id = self._query_account()
                kind = scenario_of(account_id, follower=True)
                self._fail_or_data(kind, _stats(account_id, "wechat_channels") if kind == "ok" else None)
                return
            self._send(404, {"code": 404, "message": "not found", "data": None})

        def do_POST(self) -> None:  # noqa: N802
            path = unquote(urlparse(self.path).path)
            if not self._authorized():
                self._send(401, {"code": 401, "message": "unauthorized", "data": None})
                return
            body = self._read_json()
            if path == IMPORT_PATH:
                platform_account_id = str(body.get("platform_account_id") or "")
                cookie = str(body.get("cookie") or "")
                platform = str(body.get("platform") or "kuaishou")
                if not cookie or not platform_account_id:
                    self._send(200, {"code": 1001, "message": "凭证未配置", "data": None})
                    return
                collector_id = collector_account_id(platform_account_id, platform)
                self._send(
                    200,
                    {
                        "code": 0,
                        "message": "ok",
                        "data": {"collector_account_id": collector_id, "bind_status": "BOUND"},
                    },
                )
                return
            self._send(404, {"code": 404, "message": "not found", "data": None})

    return Handler


def main() -> None:
    port = int(os.environ.get("IMS_COLLECTOR_STUB_PORT", "18991"))
    handler = _handler_factory()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"collector stub http://127.0.0.1:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
