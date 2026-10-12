"""认证、钉钉映射、岗位供给、组织同步。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AssocBase, AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref

_USER = "ims_sys_user"
_ROLE = "ims_sys_role"


class UserMapping(AuditBase):
    __tablename__ = "ims_auth_user_mapping"
    __entity_label__ = "钉钉映射"
    __table_args__ = (
        UniqueConstraint("tenant_id", "dingtalk_user_id", "deleted", name="uq_map_ding"),
        UniqueConstraint("tenant_id", "user_id", "deleted", name="uq_map_user"),
    )
    user_id: Mapped[int] = ref_column(Ref(_USER, "RESTRICT"), nullable=False)
    dingtalk_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    union_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dept_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sync_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PositionRoleRule(AuditBase):
    __tablename__ = "ims_auth_position_role_rule"
    __entity_label__ = "岗位供给规则"
    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_name", "deleted", name="uq_pos_rule_name"),
        UniqueConstraint("tenant_id", "active_slot", "deleted", name="uq_pos_rule_active"),
    )
    position_code: Mapped[str] = mapped_column(String(64), nullable=False)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "RESTRICT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    archived: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 仅启用且未归档时等于岗位编码，用来保证一个岗位只有一条启用规则。
    active_slot: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PositionRoleExtra(AssocBase):
    """附加角色。主角色仍在规则表 role_id。不建物理外键。"""

    __tablename__ = "ims_auth_position_role_extra"
    rule_id: Mapped[int] = ref_column(Ref("ims_auth_position_role_rule", "CASCADE_SOFT"), nullable=False)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "RESTRICT"), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PositionRuleRole(AssocBase):
    """当前版本授予的角色。主角色同时写在规则表 role_id。"""

    __tablename__ = "ims_auth_position_rule_role"
    __table_args__ = (UniqueConstraint("rule_id", "role_id", name="uq_rule_role"),)
    rule_id: Mapped[int] = ref_column(Ref("ims_auth_position_role_rule", "CASCADE_SOFT"), nullable=False)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "RESTRICT"), nullable=False)
    role_type: Mapped[str] = mapped_column(String(16), nullable=False, default="EXTRA")


class PositionRuleVersion(AuditBase):
    __tablename__ = "ims_auth_position_rule_version"
    __audit_exempt__ = "log"
    rule_id: Mapped[int] = ref_column(Ref("ims_auth_position_role_rule", "CASCADE_SOFT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rule_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    main_role_id: Mapped[int | None] = plain_id()
    extra_role_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False, default="EDIT")
    operator_id: Mapped[int | None] = plain_id()


class AuthEventLog(AuditBase):
    __tablename__ = "ims_auth_event_log"
    __table_args__ = (UniqueConstraint("tenant_id", "event_id", "deleted", name="uq_auth_event"),)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="POSITION")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class OrgSyncEvent(AuditBase):
    __tablename__ = "ims_auth_org_sync_event"
    __audit_exempt__ = "log"
    __table_args__ = (UniqueConstraint("event_id", name="uq_org_event"),)
    event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    biz_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    subject_user_id: Mapped[int | None] = plain_id()
    subject_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dept_id: Mapped[int | None] = plain_id()
    before_dept_names: Mapped[str | None] = mapped_column(String(500), nullable=True)
    after_dept_names: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OrgSyncBatch(AuditBase):
    __tablename__ = "ims_auth_org_sync_batch"
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dept_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dept_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dept_disabled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_resigned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unassigned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    same_name_notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trigger_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    operator_id: Mapped[int | None] = plain_id()
    diff_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class OrgSyncDiff(AuditBase):
    __tablename__ = "ims_auth_org_sync_diff"
    batch_id: Mapped[int | None] = plain_id()
    diff_type: Mapped[str] = mapped_column(String(32), nullable=False)
    diff_label: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[int | None] = plain_id()
    dingtalk_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ims_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)


class OrgSyncEventAttempt(AuditBase):
    __tablename__ = "ims_auth_org_sync_event_attempt"
    __audit_exempt__ = "log"
    event_row_id: Mapped[int] = plain_id(nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trigger: Mapped[str] = mapped_column(String(16), nullable=False, default="AUTO")
    operator_id: Mapped[int | None] = plain_id()
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="FAIL")
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String(255), nullable=True)


class OrgSyncBatchItem(AuditBase):
    __tablename__ = "ims_auth_org_sync_batch_item"
    __audit_exempt__ = "log"
    batch_id: Mapped[int | None] = plain_id()
    object_type: Mapped[str] = mapped_column(String(16), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dept_id: Mapped[int | None] = plain_id()
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    before_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    after_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="FIXED")
    error_msg: Mapped[str | None] = mapped_column(String(255), nullable=True)
