"""字符串枚举。每个枚举声明 __dict_type__，值必须在字典种子中有中文标签。"""
from __future__ import annotations

from enum import Enum


class CodeEnum(str, Enum):
    __dict_type__ = ""

    def __str__(self):
        return self.value


class UserStatus(CodeEnum):
    __dict_type__ = "dict_user_status"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    RESIGNED = "RESIGNED"


class DeptSource(CodeEnum):
    __dict_type__ = "dict_dept_source"
    DINGTALK = "DINGTALK"
    LOCAL = "LOCAL"
    SYSTEM = "SYSTEM"


class RoleSource(CodeEnum):
    __dict_type__ = "dict_role_source"
    MANUAL = "MANUAL"
    DINGTALK_AUTO = "DINGTALK_AUTO"


class RoleStatus(CodeEnum):
    __dict_type__ = "dict_role_status"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    PENDING_CONFIG = "PENDING_CONFIG"


class DataScope(CodeEnum):
    __dict_type__ = "dict_data_scope"
    ALL = "ALL"
    DEPT = "DEPT"
    IP_GROUP = "IP_GROUP"
    SELF = "SELF"


class CommonStatus(CodeEnum):
    __dict_type__ = "dict_common_status"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class TodoType(CodeEnum):
    __dict_type__ = "dict_todo_type"
    APPROVAL = "APPROVAL"
    RETURN = "RETURN"
    REVIEW = "REVIEW"
    CONFIRM = "CONFIRM"
    WARNING = "WARNING"
    ALERT = "ALERT"
    LEARN = "LEARN"


class TodoStatus(CodeEnum):
    __dict_type__ = "dict_todo_status"
    PENDING = "PENDING"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class LoginResult(CodeEnum):
    __dict_type__ = "dict_login_result"
    SUCCESS = "SUCCESS"
    BAD_CREDENTIAL = "BAD_CREDENTIAL"
    LOCKED = "LOCKED"
    DISABLED = "DISABLED"
    UNMAPPED = "UNMAPPED"
    LOGOUT = "LOGOUT"
    KICKED = "KICKED"


class OrgSyncStatus(CodeEnum):
    __dict_type__ = "dict_org_sync_status"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    RETRYING = "RETRYING"
    DEAD = "DEAD"
    EXPIRED = "EXPIRED"


class FlowStatus(CodeEnum):
    __dict_type__ = "dict_flow_status"
    RUNNING = "RUNNING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"
    TIMEOUT = "TIMEOUT"


class NotifyStatus(CodeEnum):
    __dict_type__ = "dict_notify_status"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED_DUP = "SKIPPED_DUP"
    DISABLED = "DISABLED"


class DemoStatus(CodeEnum):
    __dict_type__ = "dict_demo_status"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class PlatformType(CodeEnum):
    __dict_type__ = "dict_platform_type"
    DOUYIN = "DOUYIN"
    KUAISHOU = "KUAISHOU"
    WECHAT_CHANNELS = "WECHAT_CHANNELS"
    XIAOHONGSHU = "XIAOHONGSHU"
    WECHAT_MP = "WECHAT_MP"
    OTHER = "OTHER"


class MsgType(CodeEnum):
    __dict_type__ = "dict_msg_type"
    SYSTEM = "SYSTEM"
    TODO = "TODO"


DISABLED_STATUSES = {"DISABLED", "CANCELLED", "CLOSED", "RESIGNED", "FROZEN"}


def all_enum_classes():
    return [
        UserStatus,
        DeptSource,
        RoleSource,
        RoleStatus,
        DataScope,
        CommonStatus,
        TodoType,
        TodoStatus,
        LoginResult,
        OrgSyncStatus,
        FlowStatus,
        NotifyStatus,
        DemoStatus,
        PlatformType,
        MsgType,
    ]
