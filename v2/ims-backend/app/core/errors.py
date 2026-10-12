"""业务异常。"""
from __future__ import annotations

from app.core.error_codes import get_entry


class BizError(Exception):
    def __init__(self, code: int, msg: str | None = None, data=None, *, http_status: int | None = None, **params):
        entry = get_entry(code)
        template = entry.msg if entry else "系统繁忙，请稍后再试"
        if msg is None:
            try:
                msg = template.format(**params) if params else template
            except Exception:
                msg = template
        self.code = code
        self.msg = msg
        self.data = data
        self.params = params
        if http_status is not None:
            self.http_status = http_status
        elif code in (1002, 1003):
            self.http_status = 401
        else:
            self.http_status = 200
        super().__init__(self.msg)


class StartupError(Exception):
    pass


class UniqueConflict(Exception):
    def __init__(self, field: str, message: str = "编码已存在"):
        self.field = field
        self.message = message
        super().__init__(message)
