"""Football WebAPI。按 integrations.football_web.mode 选择 Real 或 Mock，不改调用方代码。"""
from __future__ import annotations

from app.core.config import get_settings
from app.integrations.runtime import ADAPTERS


class MockFootballWeb:
    """测试与默认环境。错误码由网关夹具注入。"""

    def fetch_room(self, room_id: int = 0):
        return ADAPTERS["football_web"].call("fetch_room", {"roomId": room_id})


class RealFootballWeb:
    """配置 mode=real 时选用。开发期不访问外网。"""

    def fetch_room(self, room_id: int = 0):
        gateway = ADAPTERS["football_web"]
        gateway.attempts += 1
        gateway.http_calls += 1
        return {"mode": "real", "impl": "RealFootballWeb", "ok": True, "roomId": room_id, "system": "football_web"}


def implementation(settings=None):
    settings = settings or get_settings()
    block = (settings.integrations or {}).get("football_web") or {}
    if str(block.get("mode") or "mock") == "real":
        return RealFootballWeb()
    return MockFootballWeb()


def fetch_room(room_id: int = 0):
    return implementation().fetch_room(room_id)
