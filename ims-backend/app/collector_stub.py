"""本地 unify-collector 桩。响应形状与真实快手内部作品接口一致。

`user_id` / `platform_account_id` / `account_id` 含 `COOKIE_EXPIRED` → Cookie 已失效；
含 `ENGINE_DOWN` → 浏览器引擎不可用；其余返回两条作品。业务错误用 HTTP 200 + code/message。
"""

from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.collector_client import (
    CODE_COOKIE,
    CODE_ENGINE,
    HEALTH_PATH,
    IMPORT_PATH,
    INTERNAL_VIDEOS_PATH,
    MSG_COOKIE,
    MSG_ENGINE,
)

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


def scenario_of(*parts: str) -> str:
    blob = " ".join(part for part in parts if part)
    if "COOKIE_EXPIRED" in blob:
        return "cookie"
    if "ENGINE_DOWN" in blob:
        return "engine"
    return "ok"


def collector_account_id(platform_account_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", platform_account_id or "")[:80] or "unknown"
    return f"acc_kuaishou_{safe}"


def _business(kind: str) -> tuple[int, str, dict | None]:
    if kind == "cookie":
        return CODE_COOKIE, MSG_COOKIE, None
    if kind == "engine":
        return CODE_ENGINE, MSG_ENGINE, None
    return 0, "ok", None


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

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path == "/livez":
                self._send(200, {"code": 0, "message": "ok", "data": {"status": "up"}})
                return
            if not self._authorized():
                self._send(401, {"code": 401, "message": "unauthorized", "data": None})
                return
            if path == HEALTH_PATH:
                query = self.path.split("?", 1)[1] if "?" in self.path else ""
                account_id = ""
                for part in query.split("&"):
                    if part.startswith("account_id="):
                        account_id = part.split("=", 1)[1]
                kind = scenario_of(account_id)
                code, message, _ = _business(kind)
                if kind == "ok":
                    data = {"conn_status": "CONNECTED", "collector_account_id": account_id}
                elif kind == "cookie":
                    data = {"conn_status": "COOKIE_EXPIRED", "collector_account_id": account_id}
                else:
                    data = {"conn_status": "ENGINE_UNAVAILABLE", "collector_account_id": account_id}
                self._send(200, {"code": code, "message": message, "data": data})
                return
            self._send(404, {"code": 404, "message": "not found", "data": None})

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if not self._authorized():
                self._send(401, {"code": 401, "message": "unauthorized", "data": None})
                return
            body = self._read_json()
            if path == IMPORT_PATH:
                platform_account_id = str(body.get("platform_account_id") or "")
                cookie = str(body.get("cookie") or "")
                if not cookie or not platform_account_id:
                    self._send(200, {"code": 1001, "message": "凭证未配置", "data": None})
                    return
                collector_id = collector_account_id(platform_account_id)
                self._send(
                    200,
                    {
                        "code": 0,
                        "message": "ok",
                        "data": {"collector_account_id": collector_id, "bind_status": "BOUND"},
                    },
                )
                return
            if path == INTERNAL_VIDEOS_PATH:
                user_id = str(body.get("user_id") or "")
                cookie = str(body.get("cookie") or "")
                kind = scenario_of(user_id, cookie)
                code, message, _ = _business(kind)
                if kind == "ok":
                    self._send(200, {"code": 0, "message": "ok", "data": {"videos": _SUCCESS_VIDEOS}})
                    return
                self._send(200, {"code": code, "message": message, "data": None})
                return
            self._send(404, {"code": 404, "message": "not found", "data": None})

    return Handler


def main() -> None:
    import os as _os

    port = int(_os.environ.get("IMS_COLLECTOR_STUB_PORT", "18991"))
    handler = _handler_factory()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"collector stub http://127.0.0.1:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
