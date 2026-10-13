"""钉钉适配器。测试环境走 Mock，不访问公网。mode=real 时通讯录走真实拉取。"""
from __future__ import annotations

from app.core.errors import BizError
from app.integrations.dingtalk.directory import AUTH_SCOPE_HINT, pull_org_directory


class DingState:
    def __init__(self):
        self.profile = {"userid": "dt_a", "mobile": "13800001111", "name": "钉钉用户"}
        self.error = None
        self.departments: list[dict] = []
        self.users: list[dict] = []
        self.notify_calls: list[dict] = []
        self.http_calls = 0
        self.force_off = False
        # None 表示通讯录里没有这个人，首登不建账号。
        self.login_sync: dict | None = None

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


def fetch_user(userid: str) -> dict | None:
    """按钉钉 userid 拉人员详情。不在企业或已离职时返回 None。"""
    ding_state.http_calls += 1
    if ding_state.error == "timeout":
        raise BizError(5003)
    if ding_state.error == "error":
        raise BizError(1006)
    profile = ding_state.login_sync
    if not profile:
        return None
    remote_id = str(profile.get("userid") or profile.get("dingtalkUserId") or "")
    if remote_id != str(userid):
        return None
    if profile.get("active") is False or str(profile.get("status") or "") == "RESIGNED":
        return None
    return dict(profile)


def dingtalk_enabled() -> bool:
    if ding_state.force_off:
        return False
    from app.core.config import get_settings

    mode = str((get_settings().dingtalk or {}).get("mode") or "mock").lower()
    return mode not in {"off", "disabled", "false", "0", ""}


def _real_directory() -> bool:
    """只有显式 real 才访问钉钉。mock / 测试保持内存目录。"""
    if ding_state.force_off:
        return False
    from app.core.config import get_settings

    mode = str((get_settings().dingtalk or {}).get("mode") or "mock").lower()
    return mode == "real"


def _reject_unusable_directory(payload: dict | None, err: str | None) -> dict:
    """没有完整部门结果就失败返回，对账不会拿空列表去停用本地部门。"""
    text = err or ""
    if "50004" in text:
        raise BizError(1006, AUTH_SCOPE_HINT)
    if text:
        lowered = text.lower()
        if "timeout" in lowered or "timed out" in lowered:
            raise BizError(5003)
        raise BizError(1006, "钉钉组织拉取失败，已中止同步")
    departments = (payload or {}).get("departments") or []
    if not departments:
        raise BizError(1006, "钉钉未返回部门，已中止同步，避免停用本地部门")
    return payload or {}


def list_directory() -> dict:
    if _real_directory():
        payload, err = pull_org_directory()
        return _reject_unusable_directory(payload, err)
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
