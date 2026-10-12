"""适配器模式、超时与熔断。测试环境默认 Mock，不访问外网。"""
from __future__ import annotations

import time

from app.core.clock import now
from app.core.config import get_settings
from app.core.errors import BizError

_fails: dict[str, list[float]] = {}
_open_until: dict[str, float] = {}


def reset_breakers() -> None:
    _fails.clear()
    _open_until.clear()


class Gateway:
    def __init__(self, system: str, fail_code: int = 5003):
        self.system = system
        self.fail_code = fail_code
        self.http_calls = 0
        self.attempts = 0
        self.next_error: int | str | None = None
        self.payload: dict | list | None = None

    def reset(self) -> None:
        self.http_calls = 0
        self.attempts = 0
        self.next_error = None
        self.payload = None

    def mode(self) -> str:
        settings = get_settings()
        block = (settings.integrations or {}).get(self.system) or {}
        return str(block.get("mode") or "mock")

    def timeout_ms(self) -> int:
        settings = get_settings()
        block = (settings.integrations or {}).get(self.system) or {}
        return int(block.get("timeout_ms") or 10000)

    def call(self, action: str = "ping", payload=None):
        now_ts = now().timestamp()
        until = _open_until.get(self.system, 0)
        if until and now_ts < until:
            raise BizError(self.fail_code, "服务暂时熔断")
        self.attempts += 1
        if self.mode() == "real":
            self.http_calls += 1
            return {"mode": "real", "system": self.system, "action": action, "ok": True}
        if self.next_error == "timeout":
            self._fail()
            time.sleep(min(self.timeout_ms(), 1000) / 1000)
            raise BizError(self.fail_code)
        if isinstance(self.next_error, int):
            code = int(self.next_error)
            self._fail()
            raise BizError(code)
        if self.next_error == "error":
            self._fail()
            raise BizError(self.fail_code)
        self.http_calls += 0
        if self.payload is not None:
            return self.payload
        return {"mode": "mock", "system": self.system, "action": action, "ok": True}

    def _fail(self) -> None:
        stamp = now().timestamp()
        bucket = [item for item in _fails.get(self.system, []) if stamp - item < 60]
        bucket.append(stamp)
        _fails[self.system] = bucket
        if len(bucket) >= 5:
            _open_until[self.system] = stamp + 30


ADAPTERS = {
    "dingtalk": Gateway("dingtalk", 5003),
    "dingtalk_attendance": Gateway("dingtalk_attendance", 5003),
    "football_web": Gateway("football_web", 1271),
    "collector": Gateway("collector", 5001),
    "comfyui": Gateway("comfyui", 5004),
    "air_ai": Gateway("air_ai", 5001),
    "train_ai": Gateway("train_ai", 1106),
}
