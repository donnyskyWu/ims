"""进程内领域事件。"""
from __future__ import annotations

from app.core.clock import now


class EventBus:
    def __init__(self):
        self.items: list[dict] = []

    def publish(self, name: str, payload: dict | None = None):
        self.items.append({"name": name, "payload": payload or {}, "at": now().isoformat()})

    def of(self, name: str) -> list[dict]:
        return [item for item in self.items if item["name"] == name]

    def clear(self):
        self.items.clear()


events = EventBus()
