from datetime import date, datetime

from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, Float, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core import Base, utcnow


class User(Base):
    __tablename__ = "ims_sys_user"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    mobile: Mapped[str] = mapped_column(String(20), default="")
    password_hash: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    dingtalk_user_id: Mapped[str] = mapped_column(String(64), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LoginGuard(Base):
    __tablename__ = "ims_auth_login_guard"
    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuthSession(Base):
    __tablename__ = "ims_auth_session"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    refresh_token: Mapped[str] = mapped_column(String(512))
    revoked: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SsoState(Base):
    __tablename__ = "ims_auth_sso_state"
    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    expire_at: Mapped[datetime] = mapped_column(DateTime)


class ImportBatch(Base):
    __tablename__ = "ims_sys_user_import"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uk_import_source"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)


class Menu(Base):
    __tablename__ = "ims_sys_menu"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(BigInteger, default=0)
    name: Mapped[str] = mapped_column(String(64))
    menu_type: Mapped[str] = mapped_column(String(16), default="MENU")
    route: Mapped[str] = mapped_column(String(128), default="")
    perm_code: Mapped[str] = mapped_column(String(128), default="")
    visible: Mapped[int] = mapped_column(Integer, default=1)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Role(Base):
    __tablename__ = "ims_sys_role"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(64))
    role_key: Mapped[str] = mapped_column(String(64), unique=True)
    data_scope: Mapped[str] = mapped_column(String(16), default="SELF")
    dingtalk_position: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    source: Mapped[str] = mapped_column(String(16), default="MANUAL")
    status: Mapped[str] = mapped_column(String(20), default="ENABLED")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RoleMenu(Base):
    __tablename__ = "ims_sys_role_menu"
    __table_args__ = (UniqueConstraint("role_id", "menu_id", name="uk_role_menu"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(BigInteger, index=True)
    menu_id: Mapped[int] = mapped_column(BigInteger)
    perm_code: Mapped[str] = mapped_column(String(128), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RolePerm(Base):
    __tablename__ = "ims_role_perm_detail"
    __table_args__ = (UniqueConstraint("role_id", "perm_code", name="uk_role_perm"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(BigInteger, index=True)
    module_code: Mapped[str] = mapped_column(String(64), default="")
    perm_code: Mapped[str] = mapped_column(String(128))
    perm_level: Mapped[str] = mapped_column(String(8))
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserRole(Base):
    __tablename__ = "ims_sys_user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uk_user_role"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DictType(Base):
    __tablename__ = "ims_sys_dict_type"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dict_type: Mapped[str] = mapped_column(String(64), unique=True)
    type_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DictData(Base):
    __tablename__ = "ims_sys_dict_data"
    __table_args__ = (UniqueConstraint("dict_type", "dict_value", name="uk_dict_value"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dict_type: Mapped[str] = mapped_column(String(64), index=True)
    dict_label: Mapped[str] = mapped_column(String(64))
    dict_value: Mapped[str] = mapped_column(String(64))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SysParam(Base):
    __tablename__ = "ims_sys_param"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    param_key: Mapped[str] = mapped_column(String(128), unique=True)
    param_value: Mapped[str] = mapped_column(String(512), default="")
    remark: Mapped[str] = mapped_column(String(128), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Todo(Base):
    __tablename__ = "ims_auth_todo"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignee_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    task_type: Mapped[str] = mapped_column(String(32))
    ref_type: Mapped[str] = mapped_column(String(32), default="")
    ref_id: Mapped[int] = mapped_column(BigInteger, default=0)
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OrgEvent(Base):
    __tablename__ = "ims_auth_org_event"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uk_org_event_idem"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dingtalk_event_id: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    union_id: Mapped[str] = mapped_column(String(64), default="")
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    before_dept: Mapped[str] = mapped_column(String(128), default="")
    after_dept: Mapped[str] = mapped_column(String(128), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="")
    sync_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dead_letter: Mapped[int] = mapped_column(Integer, default=0)
    alert_code: Mapped[str] = mapped_column(String(64), default="")
    last_error: Mapped[str] = mapped_column(String(512), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserMapping(Base):
    __tablename__ = "ims_auth_user_mapping"
    __table_args__ = (UniqueConstraint("tenant_id", "dingtalk_user_id", name="uk_map_ding"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    dingtalk_user_id: Mapped[str] = mapped_column(String(64))
    union_id: Mapped[str] = mapped_column(String(64), default="")
    dept_ids: Mapped[list] = mapped_column(JSON, default=list)
    prev_dept_ids: Mapped[list] = mapped_column(JSON, default=list)
    sync_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    buffer_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class WorkMessage(Base):
    __tablename__ = "ims_auth_message"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(String(512), default="")
    channel: Mapped[str] = mapped_column(String(16), default="IN_APP")
    read_flag: Mapped[int] = mapped_column(Integer, default=0)
    source_module: Mapped[str] = mapped_column(String(32), default="")
    ref_type: Mapped[str] = mapped_column(String(32), default="")
    ref_id: Mapped[int] = mapped_column(BigInteger, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PositionRule(Base):
    __tablename__ = "ims_position_template"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_name: Mapped[str] = mapped_column(String(64))
    dingtalk_position: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    grant_role_ids: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(String(200), default="")
    applied_user_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserDept(Base):
    __tablename__ = "ims_auth_user_dept"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserScope(Base):
    __tablename__ = "ims_user_scope"
    __table_args__ = (Index("idx_scope", "scope_type", "scope_value"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    scope_type: Mapped[str] = mapped_column(String(16))
    scope_value: Mapped[str] = mapped_column(String(64), default="")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OperateLog(Base):
    __tablename__ = "ims_sys_operate_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    module: Mapped[str] = mapped_column(String(16), default="系统")
    action: Mapped[str] = mapped_column(String(64), default="")
    operator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    operator_name: Mapped[str] = mapped_column(String(64), default="")
    path: Mapped[str] = mapped_column(String(256), default="")
    detail_json: Mapped[str] = mapped_column(Text, default="")
    result_code: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LoginLog(Base):
    __tablename__ = "ims_sys_login_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    success: Mapped[int] = mapped_column(Integer, default=0)
    result_code: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(128), default="")
    login_type: Mapped[str] = mapped_column(String(16), default="PASSWORD")
    path: Mapped[str] = mapped_column(String(256), default="")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CertArchive(Base):
    __tablename__ = "ims_cert_archive"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    holder_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    holder_name: Mapped[str] = mapped_column(String(64), default="")
    cert_type: Mapped[str] = mapped_column(String(32), default="")
    cert_no_enc: Mapped[str] = mapped_column(String(512), default="")
    cert_no_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    issue_date: Mapped[str] = mapped_column(String(10), default="")
    expire_date: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(32), default="EFFECTIVE")
    uploaded_by: Mapped[int] = mapped_column(BigInteger, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CertExpireLog(Base):
    """CERT-002 / BR-013 到期预警。同证件同时仅一条未解除记录。"""

    __tablename__ = "ims_cert_expire_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cert_id: Mapped[int] = mapped_column(BigInteger, index=True)
    holder_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(16), default="YELLOW")
    notify_user_ids: Mapped[str] = mapped_column(Text, default="[]")
    notified_levels: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="WARNING")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CertViewLog(Base):
    """CERT-S-R3 查看审计。同一查看人、同一证件，滚动 1 小时内第 11 次拦截。"""

    __tablename__ = "ims_cert_view_log"
    __table_args__ = (Index("idx_cert_view_hour", "tenant_id", "viewer_user_id", "cert_id", "created_at"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cert_id: Mapped[int] = mapped_column(BigInteger, index=True)
    viewer_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    viewer_name: Mapped[str] = mapped_column(String(64), default="")
    view_level: Mapped[int] = mapped_column(Integer, default=2)
    watermark_text: Mapped[str] = mapped_column(String(512), default="")
    view_duration: Mapped[int] = mapped_column(Integer, default=0)
    ip: Mapped[str] = mapped_column(String(64), default="")
    device: Mapped[str] = mapped_column(String(256), default="")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CertRemindLog(Base):
    """CERT-002 人工催办事实。重复催办各记一条，不占用同级别扫描去重。"""

    __tablename__ = "ims_cert_remind_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expire_log_id: Mapped[int] = mapped_column(BigInteger, index=True)
    cert_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel: Mapped[str] = mapped_column(String(16), default="BOTH")
    reminded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveSessionSeq(Base):
    __tablename__ = "ims_live_session_seq"
    __table_args__ = (UniqueConstraint("tenant_id", "biz_date", "platform_code", name="uk_live_seq_day"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    biz_date: Mapped[str] = mapped_column(String(8))
    platform_code: Mapped[str] = mapped_column(String(3))
    seq_val: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)


class LiveSessionToken(Base):
    __tablename__ = "ims_live_session_token"
    __table_args__ = (UniqueConstraint("tenant_id", "client_token", name="uk_live_client_token"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_token: Mapped[str] = mapped_column(String(64))
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveSession(Base):
    __tablename__ = "ims_live_session"
    __table_args__ = (UniqueConstraint("session_code", name="uk_live_session_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32))
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    realname_person_id: Mapped[int] = mapped_column(BigInteger, default=0)
    realname_name: Mapped[str] = mapped_column(String(64), default="")
    responsible_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    device_asset_ids: Mapped[str] = mapped_column(Text, default="[]")
    platform: Mapped[str] = mapped_column(String(32), default="")
    topic: Mapped[str] = mapped_column(String(256), default="")
    plan_start_time: Mapped[str] = mapped_column(String(32), default="")
    plan_end_time: Mapped[str] = mapped_column(String(32), default="")
    session_status: Mapped[str] = mapped_column(String(32), default="PENDING_RISK_CHECK")
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    approver_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    approve_comment: Mapped[str] = mapped_column(String(512), default="")
    football_room_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    football_sync_status: Mapped[str] = mapped_column(String(16), default="UNLINKED")
    last_football_sync_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_supplement: Mapped[int] = mapped_column(Integer, default=0)
    supplement_reason: Mapped[str] = mapped_column(String(256), default="")
    cancel_reason: Mapped[str] = mapped_column(String(256), default="")
    actual_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actual_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveRiskCheck(Base):
    __tablename__ = "ims_live_risk_check"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, index=True)
    check_item: Mapped[str] = mapped_column(String(32))
    check_result: Mapped[str] = mapped_column(String(16))
    score_weight: Mapped[int] = mapped_column(Integer, default=0)
    checked_at: Mapped[str] = mapped_column(String(32), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class LiveReport(Base):
    __tablename__ = "ims_live_report"
    __table_args__ = (UniqueConstraint("session_code", name="uk_live_report_session"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    actual_start: Mapped[str] = mapped_column(String(32), default="")
    actual_end: Mapped[str] = mapped_column(String(32), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    gmv: Mapped[float] = mapped_column(Float, default=0.0)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    viewer_count: Mapped[int] = mapped_column(Integer, default=0)
    peak_online: Mapped[int] = mapped_column(Integer, default=0)
    new_fans: Mapped[int] = mapped_column(Integer, default=0)
    ad_cost: Mapped[float] = mapped_column(Float, default=0.0)
    entry_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    entry_status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    submitted_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveCost(Base):
    """下播成本明细（ims_live_cost）。cost_type：AD / RECHARGE / GIFT / SAMPLE。"""

    __tablename__ = "ims_live_cost"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    cost_type: Mapped[str] = mapped_column(String(16), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    ref_record_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[str] = mapped_column(String(256), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveReportCorrection(Base):
    """下播报告更正单。提交后原值只读，修改留新旧对比。"""

    __tablename__ = "ims_live_report_correction"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    report_id: Mapped[int] = mapped_column(BigInteger, default=0)
    correction_reason: Mapped[str] = mapped_column(String(512), default="")
    before_json: Mapped[str] = mapped_column(Text, default="{}")
    after_json: Mapped[str] = mapped_column(Text, default="{}")
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class LiveDataSnapshot(Base):
    __tablename__ = "ims_live_data_snapshot"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    viewer_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_online: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gmv_from_platform: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="MANUAL")
    captured_at: Mapped[str] = mapped_column(String(32), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class LiveAlarmRecord(Base):
    __tablename__ = "ims_live_alarm_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, default=0)
    rule_name: Mapped[str] = mapped_column(String(64), default="")
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    alarm_level: Mapped[int] = mapped_column(Integer, default=1)
    alarm_content: Mapped[str] = mapped_column(String(512), default="")
    occur_at: Mapped[str] = mapped_column(String(32), default="")
    handle_status: Mapped[str] = mapped_column(String(16), default="UNHANDLED")
    handler_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    handle_remark: Mapped[str] = mapped_column(String(512), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class ContentSop(Base):
    __tablename__ = "ims_content_sop"
    __table_args__ = (UniqueConstraint("sop_code", "version", name="uk_content_sop_ver"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sop_code: Mapped[str] = mapped_column(String(32), index=True)
    sop_name: Mapped[str] = mapped_column(String(128))
    content_type: Mapped[str] = mapped_column(String(32), default="")
    sop_level: Mapped[str] = mapped_column(String(16), default="STANDARD")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    marketing_plan: Mapped[str] = mapped_column(String(32), default="")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentSopNode(Base):
    __tablename__ = "ims_content_sop_node"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sop_id: Mapped[int] = mapped_column(BigInteger, index=True)
    node_order: Mapped[int] = mapped_column(Integer, default=0)
    node_name: Mapped[str] = mapped_column(String(64), default="")
    standard_desc: Mapped[str] = mapped_column(Text, default="")
    deliverable_spec: Mapped[dict] = mapped_column(JSON, default=dict)
    quality_checklist: Mapped[list] = mapped_column(JSON, default=list)
    owner_role: Mapped[str] = mapped_column(String(16), default="R6")
    node_type: Mapped[str] = mapped_column(String(32), default="NORMAL")
    document_type: Mapped[str] = mapped_column(String(32), default="")
    instruction_text: Mapped[str] = mapped_column(Text, default="")
    attachment_urls: Mapped[list] = mapped_column(JSON, default=list)
    sla_hours: Mapped[int] = mapped_column(Integer, default=24)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)


class ContentPlan(Base):
    __tablename__ = "ims_content_plan"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    plan_name: Mapped[str] = mapped_column(String(128))
    sop_id: Mapped[int] = mapped_column(BigInteger, index=True)
    ip_group_ids: Mapped[list] = mapped_column(JSON, default=list)
    start_date: Mapped[str] = mapped_column(String(10), default="")
    end_date: Mapped[str] = mapped_column(String(10), default="")
    description: Mapped[str] = mapped_column(String(512), default="")
    terminate_reason: Mapped[str] = mapped_column(String(512), default="")
    plan_status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentProject(Base):
    __tablename__ = "ims_content_project"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    content_status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    document_type: Mapped[str] = mapped_column(String(32), default="")
    task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    ai_generate_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    review_passed: Mapped[int] = mapped_column(Integer, default=0)
    submitter_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    content_type: Mapped[str] = mapped_column(String(32), default="SHORT_VIDEO")
    platform_type: Mapped[str] = mapped_column(String(32), default="")
    ip_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    competition_id: Mapped[str] = mapped_column(String(64), default="")
    competition_name: Mapped[str] = mapped_column(String(256), default="")
    match_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_scheme: Mapped[list] = mapped_column(JSON, default=list)
    match_summary: Mapped[str] = mapped_column(String(128), default="")
    layout_html: Mapped[str] = mapped_column(Text, default="")
    ai_generate_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author_article_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fb_sync_status: Mapped[str] = mapped_column(String(16), default="NONE")
    fb_sync_version: Mapped[int] = mapped_column(Integer, default=0)
    last_fb_sync_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_fb_sync_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentFbSyncOutbox(Base):
    __tablename__ = "ims_fb_sync_outbox"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uk_fb_sync_idem"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content_project_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(16), default="UPSERT")
    idempotency_key: Mapped[str] = mapped_column(String(128), default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sync_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_msg: Mapped[str | None] = mapped_column(String(512), nullable=True)
    dead_letter: Mapped[int] = mapped_column(Integer, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentWorkTaskSheet(Base):
    __tablename__ = "ims_content_work_task_sheet"
    __table_args__ = (UniqueConstraint("tenant_id", "ip_group_id", "work_date", name="uk_wt_sheet_day"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    work_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    confirmed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ContentWorkTaskAssignment(Base):
    __tablename__ = "ims_content_work_task_assignment"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sheet_id: Mapped[int] = mapped_column(BigInteger, index=True)
    row_no: Mapped[int] = mapped_column(Integer, default=0)
    author_id: Mapped[int] = mapped_column(BigInteger, index=True)
    assignee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    publish_account_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    work_date: Mapped[str] = mapped_column(String(10), default="")
    marketing_plan: Mapped[str] = mapped_column(String(32), default="")
    is_live: Mapped[int] = mapped_column(Integer, default=0)
    live_time: Mapped[str] = mapped_column(String(8), default="")
    sales_platform: Mapped[str] = mapped_column(String(32), default="NONE")
    win_prediction: Mapped[str] = mapped_column(String(16), default="UNKNOWN")
    competitions: Mapped[list] = mapped_column(JSON, default=list)
    row_status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)


class ContentTask(Base):
    __tablename__ = "ims_content_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(BigInteger, index=True)
    sop_id: Mapped[int] = mapped_column(BigInteger, index=True)
    sop_node_id: Mapped[int] = mapped_column(BigInteger, index=True)
    ip_group_id: Mapped[int] = mapped_column(BigInteger, index=True)
    author_id: Mapped[int] = mapped_column(BigInteger, index=True)
    assignee_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    node_name: Mapped[str] = mapped_column(String(64), default="")
    node_type: Mapped[str] = mapped_column(String(32), default="NORMAL")
    task_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    visible_in_list: Mapped[int] = mapped_column(Integer, default=1)
    marketing_plan: Mapped[str] = mapped_column(String(32), default="")
    work_date: Mapped[str] = mapped_column(String(10), default="")
    competitions: Mapped[list] = mapped_column(JSON, default=list)
    plan_name: Mapped[str] = mapped_column(String(128), default="")
    deliverables: Mapped[str] = mapped_column(Text, default="")
    user_attachments: Mapped[list] = mapped_column(JSON, default=list)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentWorkTaskAssignmentTask(Base):
    __tablename__ = "ims_content_work_task_assignment_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(BigInteger, index=True)
    task_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)


class ContentReview(Base):
    __tablename__ = "ims_content_review"
    __table_args__ = (UniqueConstraint("review_no", name="uk_content_review_no"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    review_no: Mapped[str] = mapped_column(String(32))
    content_project_id: Mapped[int] = mapped_column(BigInteger, index=True)
    content_title: Mapped[str] = mapped_column(String(256), default="")
    submitter_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    reviewer_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    review_round: Mapped[int] = mapped_column(Integer, default=1)
    checklist_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reject_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    first_pass: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentPublish(Base):
    __tablename__ = "ims_content_publish"
    __table_args__ = (UniqueConstraint("publish_no", name="uk_content_publish_no"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    publish_no: Mapped[str] = mapped_column(String(32))
    content_project_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    platform: Mapped[str] = mapped_column(String(32), default="")
    plan_publish_at: Mapped[str] = mapped_column(String(32), default="")
    caption: Mapped[str] = mapped_column(String(512), default="")
    publish_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    publish_status: Mapped[str] = mapped_column(String(32), default="PENDING_PUBLISH")
    archive_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    archive_package_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    archive_file_list: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    archived_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentReviewSeq(Base):
    __tablename__ = "ims_content_review_seq"
    __table_args__ = (UniqueConstraint("tenant_id", "biz_date", name="uk_review_seq_day"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    biz_date: Mapped[str] = mapped_column(String(8))
    seq_val: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)


class ContentPublishSeq(Base):
    __tablename__ = "ims_content_publish_seq"
    __table_args__ = (UniqueConstraint("tenant_id", "biz_date", name="uk_publish_seq_day"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    biz_date: Mapped[str] = mapped_column(String(8))
    seq_val: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)


class ContentSopSeq(Base):
    __tablename__ = "ims_content_sop_seq"
    __table_args__ = (UniqueConstraint("tenant_id", "biz_date", name="uk_sop_seq_day"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    biz_date: Mapped[str] = mapped_column(String(8))
    seq_val: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0)


class MetadataEntity(Base):
    __tablename__ = "ims_metadata_entity"
    __table_args__ = (UniqueConstraint("tenant_id", "entity_code", name="uk_metadata_entity_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_code: Mapped[str] = mapped_column(String(64))
    entity_name: Mapped[str] = mapped_column(String(128), default="")
    table_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BiCustomQuery(Base):
    __tablename__ = "ims_bi_custom_query"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    query_name: Mapped[str] = mapped_column(String(128), default="")
    entity_code: Mapped[str] = mapped_column(String(64), default="")
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    creator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MetadataField(Base):
    __tablename__ = "ims_metadata_field"
    __table_args__ = (UniqueConstraint("entity_id", "field_code", name="uk_metadata_field_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_id: Mapped[int] = mapped_column(BigInteger, index=True)
    field_code: Mapped[str] = mapped_column(String(64), default="")
    column_name: Mapped[str] = mapped_column(String(128), default="")
    display_name: Mapped[str] = mapped_column(String(128), default="")
    data_type: Mapped[str] = mapped_column(String(32), default="STRING")
    query_condition_type: Mapped[str] = mapped_column(String(32), default="EQ")
    dict_type: Mapped[str] = mapped_column(String(64), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MeetDailyReport(Base):
    __tablename__ = "ims_meet_daily_report"
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "report_date", name="uk_meet_daily_user_date"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    user_name: Mapped[str] = mapped_column(String(64), default="")
    dept_name: Mapped[str] = mapped_column(String(128), default="")
    report_date: Mapped[str] = mapped_column(String(10), default="")
    content_done: Mapped[str] = mapped_column(Text, default="")
    content_plan: Mapped[str] = mapped_column(Text, default="")
    content_issue: Mapped[str] = mapped_column(Text, default="")
    week_summary: Mapped[str] = mapped_column(Text, default="")
    extra_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    submit_status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    supplement: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_on_time: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReportSubmission(Base):
    __tablename__ = "ims_report_submission"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "template_id",
            "period",
            "submitter_user_id",
            "author_id",
            "account_id",
            name="uk_report_submission_dedup",
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    submission_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    template_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    template_version: Mapped[int] = mapped_column(Integer, default=1)
    period: Mapped[str] = mapped_column(String(32), default="", index=True)
    submitter_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    author_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    account_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    data_content: Mapped[dict] = mapped_column(JSON, default=dict)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    submit_status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    is_on_time: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReportAudit(Base):
    __tablename__ = "ims_report_audit"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    auditor_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    audit_round: Mapped[int] = mapped_column(Integer, default=1)
    conclusion: Mapped[str] = mapped_column(String(16), default="APPROVED")
    reject_reason: Mapped[str] = mapped_column(String(512), default="")
    reject_reason_tags: Mapped[list] = mapped_column(JSON, default=list)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReportTemplate(Base):
    __tablename__ = "ims_report_template"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    template_name: Mapped[str] = mapped_column(String(128), default="")
    fields_schema: Mapped[list] = mapped_column(JSON, default=list)
    period_type: Mapped[str] = mapped_column(String(16), default="DAILY")
    deadline_rule: Mapped[str] = mapped_column(String(64), default="22:00")
    assignees: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    business_line: Mapped[str] = mapped_column(String(16), default="BUSINESS")
    dept_name: Mapped[str] = mapped_column(String(128), default="")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MeetDailyReview(Base):
    __tablename__ = "ims_meet_daily_review"
    __table_args__ = (
        UniqueConstraint("tenant_id", "report_id", "review_level", name="uk_meet_daily_review_level"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    reviewer_user_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    reviewer_name: Mapped[str] = mapped_column(String(64), default="")
    review_level: Mapped[int] = mapped_column(Integer, default=1)
    action: Mapped[str] = mapped_column(String(24), default="READ")
    comment: Mapped[str] = mapped_column(Text, default="")
    follow_up_items: Mapped[list] = mapped_column(JSON, default=list)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MeetMinutes(Base):
    __tablename__ = "ims_meet_minutes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    minutes_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    meeting_title: Mapped[str] = mapped_column(String(256), default="")
    meeting_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    meeting_room: Mapped[str] = mapped_column(String(128), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    organizer_name: Mapped[str] = mapped_column(String(64), default="")
    attendees: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    action_items: Mapped[list] = mapped_column(JSON, default=list)
    minutes_status: Mapped[str] = mapped_column(String(24), default="REGISTERED")
    recorder_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    recorder_name: Mapped[str] = mapped_column(String(64), default="")
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirKb(Base):
    __tablename__ = "ims_kb"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_name: Mapped[str] = mapped_column(String(128), default="")
    secret_level: Mapped[str] = mapped_column(String(24), default="INTERNAL")
    owner_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirKbCategory(Base):
    __tablename__ = "ims_kb_category"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    category_name: Mapped[str] = mapped_column(String(64), default="")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    sort_no: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirKbDoc(Base):
    __tablename__ = "ims_kb_doc"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    file_key: Mapped[str] = mapped_column(String(512), default="", index=True)
    content_type: Mapped[str] = mapped_column(String(64), default="application/octet-stream")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    cate_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    audit_status: Mapped[str] = mapped_column(String(16), default="PUBLISHED")
    uploader_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainMaterialCate(Base):
    __tablename__ = "ims_train_material_cate"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cate_name: Mapped[str] = mapped_column(String(128), default="")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    position_code: Mapped[str] = mapped_column(String(16), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainTask(Base):
    __tablename__ = "ims_train_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    task_name: Mapped[str] = mapped_column(String(256), default="")
    material_ids: Mapped[list] = mapped_column(JSON, default=list)
    assign_scope: Mapped[str] = mapped_column(String(16), default="BY_USER")
    assign_targets: Mapped[list] = mapped_column(JSON, default=list)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirm_type: Mapped[str] = mapped_column(String(16), default="DURATION")
    quiz: Mapped[list] = mapped_column(JSON, default=list)
    pass_score: Mapped[int] = mapped_column(Integer, default=0)
    assigned_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="IN_PROGRESS")
    creator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainTaskRecord(Base):
    __tablename__ = "ims_train_task_record"
    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "user_id", name="uk_train_task_record_user"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    material_progress: Mapped[dict] = mapped_column(JSON, default=dict)
    confirm_status: Mapped[int] = mapped_column(Integer, default=0)
    confirm_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    study_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainStatDaily(Base):
    """TRN-S-R1 部门日汇总。完成率口径与 finish-rate 相同：已确认 / 应完成（含逾期）。"""

    __tablename__ = "ims_train_stat_daily"
    __table_args__ = (
        UniqueConstraint("tenant_id", "stat_date", "dept_id", name="uk_train_stat_daily"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    dept_name: Mapped[str] = mapped_column(String(128), default="")
    assigned_count: Mapped[int] = mapped_column(Integer, default=0)
    finished_count: Mapped[int] = mapped_column(Integer, default=0)
    finish_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainMaterial(Base):
    __tablename__ = "ims_train_material"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    material_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    cate_id: Mapped[int] = mapped_column(BigInteger, index=True, default=0)
    material_type: Mapped[str] = mapped_column(String(16), default="DOC")
    file_key: Mapped[str] = mapped_column(String(256), default="")
    link_url: Mapped[str] = mapped_column(String(512), default="")
    position_codes: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    uploader_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FinCost(Base):
    __tablename__ = "ims_fin_cost"
    __table_args__ = (
        UniqueConstraint("tenant_id", "session_code", name="uk_fin_cost_session"),
        UniqueConstraint("tenant_id", "client_token", name="uk_fin_cost_client_token"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    platform: Mapped[str] = mapped_column(String(32), default="")
    cost_gmv: Mapped[float] = mapped_column(Float, default=0.0)
    cost_refund: Mapped[float] = mapped_column(Float, default=0.0)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)
    commission_amount: Mapped[float] = mapped_column(Float, default=0.0)
    ad_cost: Mapped[float] = mapped_column(Float, default=0.0)
    recharge_cost: Mapped[float] = mapped_column(Float, default=0.0)
    fixed_cost: Mapped[float] = mapped_column(Float, default=0.0)
    sample_cost: Mapped[float] = mapped_column(Float, default=0.0)
    share_daren: Mapped[float] = mapped_column(Float, default=0.0)
    share_realname: Mapped[float] = mapped_column(Float, default=0.0)
    share_cost_type: Mapped[str] = mapped_column(String(16), default="MANUAL")
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    entry_status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    entry_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    entry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_token: Mapped[str] = mapped_column(String(64), default="")
    remark: Mapped[str] = mapped_column(String(512), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FinProfit(Base):
    __tablename__ = "ims_fin_profit"
    __table_args__ = (UniqueConstraint("tenant_id", "session_code", name="uk_fin_profit_session"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    gross_profit: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    calc_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    calc_version: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FinShareResult(Base):
    """FIN-003 分成单（手工拆分窄切片 · #57）。规则引擎 CRUD 不在本表。"""

    __tablename__ = "ims_fin_share_result"
    __table_args__ = (
        UniqueConstraint("tenant_id", "session_code", "share_target", name="uk_fin_share_session_target"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_code: Mapped[str] = mapped_column(String(32), index=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, default=0)
    rule_name: Mapped[str] = mapped_column(String(128), default="手工分成")
    share_target: Mapped[str] = mapped_column(String(16), default="DAREN")
    target_ref_id: Mapped[int] = mapped_column(BigInteger, default=0)
    target_ref_name: Mapped[str] = mapped_column(String(64), default="")
    share_base: Mapped[float] = mapped_column(Float, default=0.0)
    share_amount: Mapped[float] = mapped_column(Float, default=0.0)
    calc_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="PENDING_AUDIT")
    fin_audit_passed: Mapped[int] = mapped_column(Integer, default=0)
    biz_audit_passed: Mapped[int] = mapped_column(Integer, default=0)
    audited_by: Mapped[int] = mapped_column(BigInteger, default=0)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_off_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payoff_note: Mapped[str] = mapped_column(String(256), default="")
    payoff_voucher: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FinShareRule(Base):
    """FIN-003 分成规则。编辑在原行递增 version，不改写已生成分成单。"""

    __tablename__ = "ims_fin_share_rule"
    __table_args__ = (
        UniqueConstraint("tenant_id", "client_token", name="uk_fin_share_rule_token"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(64), default="")
    share_target: Mapped[str] = mapped_column(String(16), default="DAREN", index=True)
    base_type: Mapped[str] = mapped_column(String(16), default="NET_PROFIT")
    rate_type: Mapped[str] = mapped_column(String(16), default="FIXED")
    fixed_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    ladder_config: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rule_scope: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED", index=True)
    effective_from: Mapped[str] = mapped_column(String(32), default="")
    effective_to: Mapped[str] = mapped_column(String(32), default="")
    client_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class FinPeriod(Base):
    """财务期间结账（FinanceStatus.LOCKED · AT-FIN-002 POST /fin/period/close）。"""

    __tablename__ = "ims_fin_period"
    __table_args__ = (UniqueConstraint("tenant_id", "period_month", name="uk_fin_period_month"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[str] = mapped_column(String(7), default="", index=True)
    finance_status: Mapped[str] = mapped_column(String(16), default="OPEN")
    locked_by: Mapped[int] = mapped_column(BigInteger, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfScheme(Base):
    __tablename__ = "ims_perf_scheme"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scheme_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    template_name: Mapped[str] = mapped_column(String(128), default="")
    position_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    period_type: Mapped[str] = mapped_column(String(16), default="QUARTERLY")
    status: Mapped[str] = mapped_column(String(16), default="INACTIVE")
    items: Mapped[list] = mapped_column(JSON, default=list)
    metric_summary: Mapped[str] = mapped_column(String(512), default="")
    evaluatee_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfMetric(Base):
    """PERF-001 指标定义。COMPETE_SUBMIT_RATE 在 V2 固定 DISABLED。"""

    __tablename__ = "ims_perf_metric"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    metric_name: Mapped[str] = mapped_column(String(128), default="")
    data_source: Mapped[str] = mapped_column(String(16), default="MANUAL")
    source_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=0.0)
    score_rule: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    enable_note: Mapped[str] = mapped_column(String(256), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfPositionBind(Base):
    """岗位指标集绑定。同一岗位再次保存时旧行软删后重写。"""

    __tablename__ = "ims_perf_position_bind"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    position_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    metric_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    weight_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfPeriod(Base):
    """绩效月锁定。发布后 finance_status=LOCKED，与财务期间同语义。"""

    __tablename__ = "ims_perf_period"
    __table_args__ = (UniqueConstraint("tenant_id", "period_month", name="uk_perf_period_month"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[str] = mapped_column(String(7), default="", index=True)
    finance_status: Mapped[str] = mapped_column(String(16), default="OPEN")
    locked_by: Mapped[int] = mapped_column(BigInteger, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfCalcResult(Base):
    """PERF-002 月度结果。重算新增 version，旧行 is_current=0 留审计。"""

    __tablename__ = "ims_perf_result"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period_month", "user_id", "version", name="uk_perf_result_ver"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[str] = mapped_column(String(7), default="", index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    user_name: Mapped[str] = mapped_column(String(64), default="")
    position_code: Mapped[str] = mapped_column(String(32), default="")
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    dept_name: Mapped[str] = mapped_column(String(128), default="")
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    rank_in_dept: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_status: Mapped[str] = mapped_column(String(32), default="CALCULATING", index=True)
    calc_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approve_remark: Mapped[str] = mapped_column(String(512), default="")
    calc_task_id: Mapped[str] = mapped_column(String(32), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfCalcDetail(Base):
    """指标明细快照。data_status：AUTO / MANUAL / MISSING。"""

    __tablename__ = "ims_perf_result_detail"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    metric_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    metric_code: Mapped[str] = mapped_column(String(64), default="")
    metric_name: Mapped[str] = mapped_column(String(128), default="")
    source_module: Mapped[str] = mapped_column(String(16), default="")
    metric_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    metric_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    data_status: Mapped[str] = mapped_column(String(16), default="MISSING")
    supplement_reason: Mapped[str] = mapped_column(String(256), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfRank(Base):
    """发布后的部门排名与分档。grade_level 用 PerfGradeLevel，不用 S–D。"""

    __tablename__ = "ims_perf_rank"
    __table_args__ = (
        UniqueConstraint("tenant_id", "period_month", "user_id", "version", name="uk_perf_rank_ver"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    period_month: Mapped[str] = mapped_column(String(7), default="", index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    dept_name: Mapped[str] = mapped_column(String(128), default="")
    user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    user_name: Mapped[str] = mapped_column(String(64), default="")
    total_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    rank_no: Mapped[int] = mapped_column(Integer, default=0)
    grade_level: Mapped[str] = mapped_column(String(16), default="IMPROVE")
    alert_status: Mapped[str] = mapped_column(String(16), default="NONE")
    consecutive_months: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[int] = mapped_column(Integer, default=1)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertRule(Base):
    __tablename__ = "ims_alert_rule"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    rule_name: Mapped[str] = mapped_column(String(128), default="")
    metric_type: Mapped[str] = mapped_column(String(32), default="THRESHOLD")
    level: Mapped[int] = mapped_column(Integer, default=2)
    threshold_expr: Mapped[str] = mapped_column(String(256), default="")
    cron_expr: Mapped[str] = mapped_column(String(64), default="0 */15 * * *")
    enabled: Mapped[int] = mapped_column(Integer, default=0)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertRecord(Base):
    __tablename__ = "ims_alert_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alert_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    source_ref_type: Mapped[str] = mapped_column(String(32), default="")
    source_ref_id: Mapped[int] = mapped_column(BigInteger, default=0)
    level: Mapped[int] = mapped_column(Integer, default=2)
    content: Mapped[str] = mapped_column(String(512), default="")
    push_status: Mapped[int] = mapped_column(Integer, default=1)
    response_status: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentLayoutTemplate(Base):
    __tablename__ = "ims_content_layout_template"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    template_name: Mapped[str] = mapped_column(String(128), default="")
    source: Mapped[str] = mapped_column(String(16), default="CUSTOM")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    preview_html: Mapped[str] = mapped_column(Text, default="")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PerfRecord(Base):
    __tablename__ = "ims_perf_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    scheme_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    target_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    ip_group_id: Mapped[int] = mapped_column(BigInteger, default=0)
    period_type: Mapped[str] = mapped_column(String(16), default="QUARTERLY")
    period_start: Mapped[str] = mapped_column(String(32), default="")
    period_end: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    calc_base_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    manual_adjustment: Mapped[float] = mapped_column(Float, default=0.0)
    adjust_remark: Mapped[str] = mapped_column(String(256), default="")
    evaluator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EffRelation(Base):
    __tablename__ = "ims_eff_relation"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    relation_type: Mapped[str] = mapped_column(String(16), default="PRIMARY")
    target_type: Mapped[str] = mapped_column(String(16), default="IP_GROUP")
    target_id: Mapped[int] = mapped_column(BigInteger, default=0)
    target_name: Mapped[str] = mapped_column(String(128), default="")
    share_ratio: Mapped[float] = mapped_column(Float, default=100.0)
    effective_from: Mapped[str] = mapped_column(String(32), default="")
    effective_to: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    changed_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BiReportDef(Base):
    __tablename__ = "ims_bi_report_def"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    report_name: Mapped[str] = mapped_column(String(128), default="")
    report_type: Mapped[str] = mapped_column(String(16), default="REPORT")
    category: Mapped[str] = mapped_column(String(64), default="")
    sub_category: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    layout_json: Mapped[str] = mapped_column(Text, default="{}")
    creator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BiMetric(Base):
    __tablename__ = "ims_bi_metric"
    __table_args__ = (UniqueConstraint("tenant_id", "metric_code", name="uk_bi_metric_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    metric_code: Mapped[str] = mapped_column(String(64), default="")
    metric_name: Mapped[str] = mapped_column(String(128), default="")
    metric_type: Mapped[str] = mapped_column(String(16), default="BASIC")
    category: Mapped[str] = mapped_column(String(64), default="")
    calc_freq: Mapped[str] = mapped_column(String(16), default="DAY")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    formula: Mapped[str] = mapped_column(String(512), default="")
    ref_count: Mapped[int] = mapped_column(Integer, default=0)
    creator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BiSubscription(Base):
    __tablename__ = "ims_bi_subscription"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sub_name: Mapped[str] = mapped_column(String(128), default="")
    target_type: Mapped[str] = mapped_column(String(16), default="REPORT")
    report_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    report_name: Mapped[str] = mapped_column(String(128), default="")
    period: Mapped[str] = mapped_column(String(16), default="WEEK")
    push_time: Mapped[str] = mapped_column(String(16), default="09:00")
    channels: Mapped[str] = mapped_column(String(64), default="SITE+DING")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    last_push_status: Mapped[str] = mapped_column(String(32), default="")
    last_push_at: Mapped[str] = mapped_column(String(32), default="")
    subscriber_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BiShareLink(Base):
    __tablename__ = "ims_bi_share_link"
    __table_args__ = (UniqueConstraint("tenant_id", "link_token", name="uk_bi_share_token"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    link_token: Mapped[str] = mapped_column(String(64), default="", index=True)
    target_type: Mapped[str] = mapped_column(String(16), default="REPORT")
    target_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    target_name: Mapped[str] = mapped_column(String(128), default="")
    approval_status: Mapped[str] = mapped_column(String(24), default="NOT_REQUIRED")
    expire_at: Mapped[str] = mapped_column(String(32), default="")
    creator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    dept_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QueryTemplate(Base):
    __tablename__ = "ims_query_template"
    __table_args__ = (UniqueConstraint("tenant_id", "template_code", name="uk_query_template_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    mode: Mapped[str] = mapped_column(String(16), default="DRILL")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    menu_seed: Mapped[int] = mapped_column(Integer, default=0)
    menu_route: Mapped[str] = mapped_column(String(256), default="")
    perm_code: Mapped[str] = mapped_column(String(128), default="")
    desc: Mapped[str] = mapped_column(String(512), default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirSkill(Base):
    __tablename__ = "ims_air_skill"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    skill_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    skill_name: Mapped[str] = mapped_column(String(128), default="")
    category: Mapped[str] = mapped_column(String(64), default="")
    version_label: Mapped[str] = mapped_column(String(16), default="v1.0")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    audit_status: Mapped[str] = mapped_column(String(16), default="NONE")
    owner_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    grant_count: Mapped[int] = mapped_column(Integer, default=0)
    invoke_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirSkillGrant(Base):
    """技能授权。表名跟随现有 ims_air_skill，对应契约 ims_skill_grant。"""

    __tablename__ = "ims_air_skill_grant"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    skill_id: Mapped[int] = mapped_column(BigInteger, index=True)
    grant_type: Mapped[str] = mapped_column(String(16), default="")
    grant_id_ref: Mapped[int] = mapped_column(BigInteger, default=0)
    grant_name: Mapped[str] = mapped_column(String(128), default="")
    all_staff: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    granted_by: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirEvent(Base):
    """AI 资产事件。授权写入后网关按表实时读，不另做延迟队列。"""

    __tablename__ = "ims_air_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    sync_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirModelConfig(Base):
    __tablename__ = "ims_air_model_config"
    __table_args__ = (UniqueConstraint("tenant_id", "config_code", name="uk_air_model_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_code: Mapped[str] = mapped_column(String(32), default="")
    vendor: Mapped[str] = mapped_column(String(32), default="")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    use_case: Mapped[str] = mapped_column(String(64), default="CHAT")
    endpoint_url: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(16), default="DISCONNECTED")
    creator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirPromptConfig(Base):
    __tablename__ = "ims_air_prompt_config"
    __table_args__ = (UniqueConstraint("tenant_id", "prompt_code", name="uk_air_prompt_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prompt_code: Mapped[str] = mapped_column(String(32), default="")
    scene: Mapped[str] = mapped_column(String(64), default="")
    doc_type: Mapped[str] = mapped_column(String(64), default="")
    version_label: Mapped[str] = mapped_column(String(16), default="v1.0")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    creator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirExpert(Base):
    __tablename__ = "ims_air_expert"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expert_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    expert_name: Mapped[str] = mapped_column(String(128), default="")
    scene: Mapped[str] = mapped_column(String(256), default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    skill_ids: Mapped[list] = mapped_column(JSON, default=list)
    kb_ids: Mapped[list] = mapped_column(JSON, default=list)
    tool_whitelist: Mapped[list] = mapped_column(JSON, default=list)
    version_label: Mapped[str] = mapped_column(String(16), default="v1.0")
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    owner_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    grant_count: Mapped[int] = mapped_column(Integer, default=0)
    assemble_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirExpertGrant(Base):
    """专家授权。表名跟随 ims_air_expert，对应契约 ims_expert_grant。"""

    __tablename__ = "ims_air_expert_grant"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    expert_id: Mapped[int] = mapped_column(BigInteger, index=True)
    grant_type: Mapped[str] = mapped_column(String(16), default="")
    grant_id_ref: Mapped[int] = mapped_column(BigInteger, default=0)
    grant_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    granted_by: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CompAsset(Base):
    __tablename__ = "ims_comp_asset"
    __table_args__ = (UniqueConstraint("tenant_id", "comp_name_std", name="uk_comp_asset_name"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    comp_name_std: Mapped[str] = mapped_column(String(128), default="")
    comp_account_id: Mapped[str] = mapped_column(String(64), default="")
    platform: Mapped[str] = mapped_column(String(32), default="", index=True)
    base_info: Mapped[dict] = mapped_column(JSON, default=dict)
    latest_version: Mapped[int] = mapped_column(Integer, default=1)
    reference_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="APPROVED")
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FlowTemplate(Base):
    __tablename__ = "ims_flow_template"
    __table_args__ = (UniqueConstraint("tenant_id", "template_code", name="uk_flow_template_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    template_name: Mapped[str] = mapped_column(String(128), default="")
    business_domain: Mapped[str] = mapped_column(String(16), default="COMMON", index=True)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT")
    version_label: Mapped[str] = mapped_column(String(16), default="v1.0")
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    creator_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FlowTask(Base):
    __tablename__ = "ims_flow_task"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    node_order: Mapped[int] = mapped_column(Integer, default=1)
    node_name: Mapped[str] = mapped_column(String(128), default="")
    node_type: Mapped[str] = mapped_column(String(16), default="APPROVE")
    assignee_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    task_status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    comment: Mapped[str] = mapped_column(String(512), default="")
    remind_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FlowInstance(Base):
    __tablename__ = "ims_flow_instance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "instance_no", name="uk_flow_instance_no"),
        UniqueConstraint("tenant_id", "business_key", name="uk_flow_instance_biz_key"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instance_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    template_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    template_name: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(256), default="")
    business_key: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)
    instance_status: Mapped[str] = mapped_column(String(16), default="RUNNING", index=True)
    current_node_name: Mapped[str] = mapped_column(String(128), default="")
    initiator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ExamQuestion(Base):
    __tablename__ = "ims_exam_question"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    stem: Mapped[str] = mapped_column(String(512), default="")
    knowledge_domain: Mapped[str] = mapped_column(String(64), default="", index=True)
    question_type: Mapped[str] = mapped_column(String(16), default="SINGLE")
    score: Mapped[float] = mapped_column(Float, default=10.0)
    ref_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlertDedupPolicy(Base):
    __tablename__ = "ims_alert_dedup_policy"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    policy_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    policy_name: Mapped[str] = mapped_column(String(128), default="")
    window_minutes: Mapped[int] = mapped_column(Integer, default=15)
    merge_key_expr: Mapped[str] = mapped_column(String(256), default="")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    merged_count: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirApiKey(Base):
    """人员 Key。明文只在生成/换新响应出现一次，库内仅存 SHA-256（BR-020）。"""

    __tablename__ = "ims_air_api_key"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    key_prefix: Mapped[str] = mapped_column(String(16), default="")
    key_mask: Mapped[str] = mapped_column(String(64), default="")
    key_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    device_name: Mapped[str] = mapped_column(String(64), default="")
    qpm_limit: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    freeze_reason: Mapped[str] = mapped_column(String(64), default="")
    whitelist: Mapped[str] = mapped_column(String(512), default="")
    client_token: Mapped[str] = mapped_column(String(64), default="")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    grace_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirQpmBucket(Base):
    """单 Key 的一分钟调用计数。测试注入时钟，不依赖墙钟睡 60 秒。"""

    __tablename__ = "ims_air_qpm_bucket"
    __table_args__ = (UniqueConstraint("key_id", "window_start", name="uk_air_qpm_window"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_id: Mapped[int] = mapped_column(BigInteger, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)


class AirMcpLog(Base):
    """MCP 调用审计（契约表 ims_mcp_log）。网关本地写入，不调用外部模型。"""

    __tablename__ = "ims_mcp_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    tool: Mapped[str] = mapped_column(String(64), default="")
    param_digest: Mapped[str] = mapped_column(String(64), default="")
    result_code: Mapped[str] = mapped_column(String(16), default="")
    cost_ms: Mapped[int] = mapped_column(Integer, default=0)
    # 网关不执行模型（BR-034），token_cnt 由本地写入，缺省 0。
    token_cnt: Mapped[int] = mapped_column(Integer, default=0)
    # 组装时被剔除的未发布技能数。密级检索过滤已移除，不另计 knowledgeContext。
    filter_hit: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AirAuthFail(Base):
    """Key 认证失败计数（BR-033）。10 分钟窗口，成功调用清空。"""

    __tablename__ = "ims_air_auth_fail"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_id: Mapped[int] = mapped_column(BigInteger, index=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)


class AirAuditLog(Base):
    __tablename__ = "ims_air_audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    scene: Mapped[str] = mapped_column(String(64), default="")
    model_name: Mapped[str] = mapped_column(String(64), default="")
    token_in: Mapped[int] = mapped_column(Integer, default=0)
    token_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="OK")
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notify(Base):
    __tablename__ = "ims_sys_notify"
    __table_args__ = (UniqueConstraint("tenant_id", "event_type", "biz_key", name="uk_notify_event"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64))
    biz_key: Mapped[str] = mapped_column(String(128))
    receiver: Mapped[str] = mapped_column(String(64), default="")
    receiver_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    channel: Mapped[str] = mapped_column(String(16), default="IN_APP")
    status: Mapped[str] = mapped_column(String(16), default="DELIVERED")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountApply(Base):
    __tablename__ = "ims_acct_apply"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    apply_no: Mapped[str] = mapped_column(String(32), unique=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    platform: Mapped[str] = mapped_column(String(32), default="")
    applicant_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    purpose: Mapped[str] = mapped_column(String(256), default="")
    plan_start: Mapped[str] = mapped_column(String(32), default="")
    plan_end: Mapped[str] = mapped_column(String(32), default="")
    apply_status: Mapped[str] = mapped_column(String(32), default="PENDING_APPROVAL")
    handover_json: Mapped[str] = mapped_column(Text, default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountTimelineEvent(Base):
    __tablename__ = "ims_acct_timeline_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    ref_no: Mapped[str] = mapped_column(String(32), default="")
    ref_id: Mapped[int] = mapped_column(BigInteger, default=0)
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    snapshot_summary: Mapped[str] = mapped_column(String(512), default="")
    remark: Mapped[str] = mapped_column(String(256), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountTransfer(Base):
    """ACCT-002 账号流转/收回。流转待新责任人确认后改责任人（TRF-R1）；收回单管理员发起后直接生效并冻结（TRF-R2）。"""

    __tablename__ = "ims_acct_transfer"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transfer_no: Mapped[str] = mapped_column(String(32), unique=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    from_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    to_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    transfer_type: Mapped[str] = mapped_column(String(16), default="TRANSFER")
    reason_type: Mapped[str] = mapped_column(String(32), default="")
    remark: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="PENDING_CONFIRM")
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountRecharge(Base):
    """ACCT-004 冲话费登记。凭证原文仅财务角色（acct:r3）在列表接口回传。"""

    __tablename__ = "ims_acct_recharge"
    __table_args__ = (UniqueConstraint("client_token", name="uk_acct_recharge_token"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(BigInteger, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    channel: Mapped[str] = mapped_column(String(64), default="")
    voucher_url: Mapped[str] = mapped_column(String(512), default="")
    recharge_date: Mapped[str] = mapped_column(String(16), default="")
    verify_status: Mapped[str] = mapped_column(String(16), default="UNVERIFIED")
    verify_diff: Mapped[float | None] = mapped_column(Float, nullable=True)
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    client_token: Mapped[str] = mapped_column(String(64))
    remark: Mapped[str] = mapped_column(String(256), default="")
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetLedger(Base):
    """07 资产台账。AssetStatus：PENDING_REVIEW → IN_USE → RETURNED → SCRAPPED。"""

    __tablename__ = "ims_asset_ledger"
    __table_args__ = (UniqueConstraint("tenant_id", "asset_code", name="uk_asset_ledger_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_code: Mapped[str] = mapped_column(String(64), default="")
    asset_name: Mapped[str] = mapped_column(String(128), default="")
    asset_type: Mapped[str] = mapped_column(String(32), default="OFFICE", index=True)
    spec: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW", index=True)
    owner_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    purchase_date: Mapped[str] = mapped_column(String(10), default="")
    purchase_batch_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subject_id: Mapped[int] = mapped_column(BigInteger, default=0)
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    updater: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetPurchaseBatch(Base):
    """采购 CSV 入台账（#68）。成功行已提交，失败行只记行号与字段，不回滚已入库行。"""

    __tablename__ = "ims_asset_purchase_batch"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_no: Mapped[str] = mapped_column(String(32), unique=True)
    file_name: Mapped[str] = mapped_column(String(128), default="")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    partial: Mapped[int] = mapped_column(Integer, default=0)
    error_detail: Mapped[str] = mapped_column(Text, default="[]")
    creator: Mapped[int] = mapped_column(BigInteger, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetLifecycleEvent(Base):
    """资产领用 / 使用 / 归还 / 报废时间线。"""

    __tablename__ = "ims_asset_lifecycle"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_type: Mapped[str] = mapped_column(String(16), default="REGISTER")
    from_status: Mapped[str] = mapped_column(String(32), default="")
    to_status: Mapped[str] = mapped_column(String(32), default="")
    actor_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    owner_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[str] = mapped_column(String(256), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AccountRechargeVerify(Base):
    """ACCT-004 月度账实核对。差异率 ≥ 2% 记 DIFF 并生成财务核查工单（1026 / BR-017）。"""

    __tablename__ = "ims_acct_recharge_verify"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    verify_no: Mapped[str] = mapped_column(String(32), unique=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    account_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="")
    total_recharge: Mapped[float] = mapped_column(Float, default=0.0)
    platform_consumed: Mapped[float] = mapped_column(Float, default=0.0)
    diff_amount: Mapped[float] = mapped_column(Float, default=0.0)
    diff_rate: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="MATCHED")
    work_order_id: Mapped[int] = mapped_column(BigInteger, default=0)
    operator_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetHierarchy(Base):
    """实名人向下的资产层级。level 从 1 起，>5 的查询返回 1013。"""

    __tablename__ = "ims_asset_hierarchy"
    __table_args__ = (UniqueConstraint("tenant_id", "asset_id", name="uk_asset_hierarchy_asset"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, index=True)
    parent_asset_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    realname_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    path: Mapped[str] = mapped_column(String(512), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetBind(Base):
    """资产绑定账号 / 场次（ASSET-002 · #72）。一台资产一条有效绑定。"""

    __tablename__ = "ims_asset_bind"
    __table_args__ = (UniqueConstraint("tenant_id", "asset_id", name="uk_asset_bind_asset"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(BigInteger, index=True)
    asset_code: Mapped[str] = mapped_column(String(64), default="")
    account_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    account_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    platform: Mapped[str] = mapped_column(String(32), default="")
    session_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    session_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    verified_person_id: Mapped[int] = mapped_column(BigInteger, default=0)
    bind_type: Mapped[str] = mapped_column(String(16), default="HOLD")
    bind_status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetVerifyBatch(Base):
    """ASSET-003 登记关联校验批次。一种校验类型一行。"""

    __tablename__ = "ims_asset_verify_batch"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_no: Mapped[str] = mapped_column(String(64), unique=True)
    run_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    verify_type: Mapped[str] = mapped_column(String(32), default="")
    scope: Mapped[str] = mapped_column(String(16), default="FULL")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    complete_rate: Mapped[float] = mapped_column(Float, default=1.0)
    consistency_rate: Mapped[float] = mapped_column(Float, default=1.0)
    error_detail: Mapped[str] = mapped_column(Text, default="")
    task_status: Mapped[str] = mapped_column(String(32), default="PENDING_DISPATCH", index=True)
    owner_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    remark: Mapped[str] = mapped_column(String(256), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetVerifyError(Base):
    """关联校验异常明细。"""

    __tablename__ = "ims_asset_verify_error"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(BigInteger, index=True)
    batch_no: Mapped[str] = mapped_column(String(64), default="", index=True)
    run_no: Mapped[str] = mapped_column(String(32), default="", index=True)
    record_id: Mapped[int] = mapped_column(BigInteger, default=0)
    record_type: Mapped[str] = mapped_column(String(32), default="")
    asset_code: Mapped[str] = mapped_column(String(64), default="")
    inconsistent_fields: Mapped[str] = mapped_column(Text, default="[]")
    description: Mapped[str] = mapped_column(String(256), default="")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AssetTraceLog(Base):
    """穿透查询审计（ASSET-F-R3）。"""

    __tablename__ = "ims_asset_trace"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trace_type: Mapped[str] = mapped_column(String(16), default="forward")
    asset_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    realname_id: Mapped[int] = mapped_column(BigInteger, default=0)
    node_chain: Mapped[str] = mapped_column(Text, default="[]")
    query_user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DcTraceLog(Base):
    """穿透查询审计（DC-T-R4 · ims_dc_trace_log）。"""

    __tablename__ = "ims_dc_trace_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_type: Mapped[str] = mapped_column(String(32), default="")
    entry_id: Mapped[str] = mapped_column(String(64), default="")
    entry_label: Mapped[str] = mapped_column(String(128), default="")
    query_user_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    result_rows: Mapped[int] = mapped_column(Integer, default=0)
    cost_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tenant_id: Mapped[int] = mapped_column(BigInteger, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
