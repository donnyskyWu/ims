"""进程内领域事件。"""
from __future__ import annotations

from app.core.clock import now


class EventBus:
    def __init__(self):
        self.items: list[dict] = []
        self._listeners: dict[str, list] = {}

    def subscribe(self, name: str, fn) -> None:
        bucket = self._listeners.setdefault(name, [])
        if fn not in bucket:
            bucket.append(fn)

    def publish(self, name: str, payload: dict | None = None):
        body = payload or {}
        self.items.append({"name": name, "payload": body, "at": now().isoformat()})
        for fn in list(self._listeners.get(name, [])):
            fn(dict(body))

    def of(self, name: str) -> list[dict]:
        return [item for item in self.items if item["name"] == name]

    def clear(self):
        self.items.clear()


events = EventBus()
