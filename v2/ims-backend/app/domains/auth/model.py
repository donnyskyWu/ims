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
    position_code: Mapped[str] = mapped_column(String(64), nullable=False)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "RESTRICT"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    archived: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PositionRoleExtra(AssocBase):
    """附加角色。主角色仍在规则表 role_id。不建物理外键。"""

    __tablename__ = "ims_auth_position_role_extra"
    rule_id: Mapped[int] = ref_column(Ref("ims_auth_position_role_rule", "CASCADE_SOFT"), nullable=False)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "RESTRICT"), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


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
