"""钉钉适配器。测试环境走 Mock，不访问公网。"""
from __future__ import annotations

from app.core.errors import BizError


class DingState:
    def __init__(self):
        self.profile = {"userid": "dt_a", "mobile": "13800001111", "name": "钉钉用户"}
        self.error = None
        self.departments: list[dict] = []
        self.users: list[dict] = []
        self.notify_calls: list[dict] = []
        self.http_calls = 0

    def reset(self):
        self.__init__()


ding_state = DingState()


def get_user_by_code(code: str) -> dict:
    ding_state.http_calls += 1
    if ding_state.error == "timeout":
        raise BizError(5003)
    if ding_state.error == "error":
        raise BizError(1006)
    return dict(ding_state.profile)


def list_directory() -> dict:
    ding_state.http_calls += 1
    if ding_state.error == "timeout":
        raise BizError(5003)
    if ding_state.error == "error":
        raise BizError(1006)
    return {"departments": list(ding_state.departments), "users": list(ding_state.users)}


def send_work_notice(user_id: str, title: str, content: str) -> None:
    ding_state.http_calls += 1
    ding_state.notify_calls.append({"userId": user_id, "title": title, "content": content})
    if ding_state.error == "notify_fail":
        raise BizError(1006)
