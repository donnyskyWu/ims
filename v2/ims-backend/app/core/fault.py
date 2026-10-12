"""测试故障注入。"""
from __future__ import annotations


class Faults:
    def __init__(self):
        self.armed: dict[str, BaseException] = {}

    def arm(self, name: str, exc: BaseException):
        self.armed[name] = exc

    def clear(self):
        self.armed.clear()

    def raise_if(self, name: str):
        exc = self.armed.pop(name, None)
        if exc is not None:
            raise exc


faults = Faults()
