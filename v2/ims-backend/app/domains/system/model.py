"""组织、权限、字典、日志等系统表。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AssocBase, AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref

_DEPT = "ims_sys_dept"
_USER = "ims_sys_user"
_ROLE = "ims_sys_role"
_MENU = "ims_sys_menu"
_PKG = "ims_sys_tenant_package"


class Tenant(AuditBase):
    __tablename__ = "ims_sys_tenant"
    __platform__ = True
    __entity_label__ = "租户"
    __audit_exempt__ = None
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    package_id: Mapped[int | None] = ref_column(Ref(_PKG, "RESTRICT", enforce_delete=False))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TenantPackage(AuditBase):
    __tablename__ = "ims_sys_tenant_package"
    __platform__ = True
    __entity_label__ = "套餐"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")


class TenantPackageMenu(AssocBase):
    __tablename__ = "ims_sys_tenant_package_menu"
    __platform__ = True
    package_id: Mapped[int] = ref_column(Ref(_PKG, "CASCADE_SOFT"), nullable=False)
    menu_id: Mapped[int] = ref_column(Ref(_MENU, "RESTRICT"), nullable=False)


class User(AuditBase):
    __tablename__ = "ims_sys_user"
    __entity_label__ = "用户"
    __table_args__ = (UniqueConstraint("tenant_id", "username", "deleted", name="uq_user_username"),)
    __scope_resolver__ = "user"
    __scope_fields__ = {"dept": "main_dept_id", "owner": "id"}
    username: Mapped[str] = mapped_column(String(30), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    emp_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    mobile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", info={"dict": "dict_user_status"})
    main_dept_id: Mapped[int | None] = ref_column(Ref(_DEPT, "RESTRICT", enforce_delete=False))
    position_code: Mapped[str | None] = mapped_column(String(64), nullable=True, info={"dict": "dict_position"})
    login_fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lock_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pwd_reset_required: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL")
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perm_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class UserDept(AssocBase):
    __tablename__ = "ims_sys_user_dept"
    __table_args__ = (UniqueConstraint("user_id", "dept_id", name="uq_user_dept"),)
    user_id: Mapped[int] = ref_column(Ref(_USER, "CASCADE_SOFT", enforce_delete=False), nullable=False)
    dept_id: Mapped[int] = ref_column(Ref(_DEPT, "RESTRICT", enforce_delete=False), nullable=False)
    is_main: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL")


class Dept(AuditBase):
    __tablename__ = "ims_sys_dept"
    __entity_label__ = "部门"
    __table_args__ = (UniqueConstraint("tenant_id", "dingtalk_dept_id", "deleted", name="uq_dept_ding"),)
    parent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, info={"not_a_ref": True})
    path: Mapped[str] = mapped_column(String(500), nullable=False, default="/")
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leader_user_id: Mapped[int | None] = ref_column(Ref(_USER, "RESTRICT", enforce_delete=False))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_common_status"})
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL", info={"dict": "dict_dept_source"})
    dingtalk_dept_id: Mapped[int | None] = plain_id()
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    local_orphan: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Role(AuditBase):
    __tablename__ = "ims_sys_role"
    __entity_label__ = "角色"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_key", "deleted", name="uq_role_key"),
        UniqueConstraint("tenant_id", "position_code", "deleted", name="uq_role_position"),
    )
    role_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL", info={"dict": "dict_role_source"})
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED", info={"dict": "dict_role_status"})
    data_scope: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_data_scope"})
    position_code: Mapped[str | None] = mapped_column(String(64), nullable=True, info={"dict": "dict_position"})
    is_standard: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Menu(AuditBase):
    __tablename__ = "ims_sys_menu"
    __platform__ = True
    __entity_label__ = "菜单"
    __table_args__ = (UniqueConstraint("perm_code", "deleted", name="uq_menu_perm"),)
    parent_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, info={"not_a_ref": True})
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    perm_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    component: Mapped[str | None] = mapped_column(String(200), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visible: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")


class RoleMenu(AssocBase):
    __tablename__ = "ims_sys_role_menu"
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "CASCADE_SOFT"), nullable=False)
    menu_id: Mapped[int] = ref_column(Ref(_MENU, "RESTRICT"), nullable=False)


class RolePermDetail(AssocBase):
    __tablename__ = "ims_role_perm_detail"
    __table_args__ = (UniqueConstraint("role_id", "perm_code", name="uq_role_perm"),)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "CASCADE_SOFT"), nullable=False)
    perm_code: Mapped[str] = mapped_column(String(80), nullable=False)
    r: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    w: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserRole(AssocBase):
    __tablename__ = "ims_sys_user_role"
    __entity_label__ = "成员"
    user_id: Mapped[int] = ref_column(Ref(_USER, "CASCADE_SOFT", enforce_delete=False), nullable=False)
    role_id: Mapped[int] = ref_column(Ref(_ROLE, "RESTRICT"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    manual_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grant_position_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoke_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DictType(AuditBase):
    __tablename__ = "ims_sys_dict_type"
    __platform__ = True
    __entity_label__ = "字典类型"
    __table_args__ = (UniqueConstraint("dict_type", "deleted", name="uq_dict_type"),)
    dict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DictData(AuditBase):
    __tablename__ = "ims_sys_dict_data"
    __platform__ = True
    __entity_label__ = "字典值"
    __table_args__ = (UniqueConstraint("dict_type", "dict_value", "deleted", name="uq_dict_value"),)
    dict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    dict_value: Mapped[str] = mapped_column(String(64), nullable=False)
    dict_label: Mapped[str] = mapped_column(String(50), nullable=False)
    color_type: Mapped[str] = mapped_column(String(16), nullable=False, default="neutral")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ENABLED")
    is_builtin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL")
    ext_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Param(AuditBase):
    __tablename__ = "ims_sys_param"
    __platform__ = True
    __entity_label__ = "参数"
    __table_args__ = (UniqueConstraint("param_key", "deleted", name="uq_param_key"),)
    param_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    group_name: Mapped[str] = mapped_column("group_name", String(32), nullable=False, default="通用")
    value_type: Mapped[str] = mapped_column(String(16), nullable=False, default="TEXT")
    min_value: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_value: Mapped[str | None] = mapped_column(String(32), nullable=True)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class IntegrityScan(AuditBase):
    __tablename__ = "ims_sys_integrity_scan"
    __audit_exempt__ = "log"
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tenant_filter: Mapped[int | None] = plain_id()


class IntegrityIssue(AuditBase):
    __tablename__ = "ims_sys_integrity_issue"
    __audit_exempt__ = "log"
    scan_id: Mapped[int | None] = plain_id()
    issue_type: Mapped[str] = mapped_column(String(32), nullable=False)
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    target_table: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[int | None] = plain_id()
    suggestion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    last_seen_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    seen_on: Mapped[str] = mapped_column(String(10), nullable=False, default="")


class Sequence(AuditBase):
    __tablename__ = "ims_sys_sequence"
    __table_args__ = (UniqueConstraint("rule_name", "seq_date", "group_key", "deleted", name="uq_sequence"),)
    rule_name: Mapped[str] = mapped_column(String(32), nullable=False)
    seq_date: Mapped[str] = mapped_column(String(8), nullable=False)
    group_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OperateLog(AuditBase):
    __tablename__ = "ims_sys_operate_log"
    __audit_exempt__ = "log"
    operator_id: Mapped[int | None] = plain_id()
    operator_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    module: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str | None] = mapped_column(String(80), nullable=True)
    object_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    params_digest: Mapped[str | None] = mapped_column(Text, nullable=True)


class LoginLog(AuditBase):
    __tablename__ = "ims_sys_login_log"
    __audit_exempt__ = "log"
    username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[int | None] = plain_id()
    login_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PASSWORD")
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ChangeLog(AuditBase):
    __tablename__ = "ims_sys_change_log"
    __audit_exempt__ = "log"
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False)
    biz_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    field_label: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False, default="USER_EDIT")
    operator_id: Mapped[int | None] = plain_id()


class SensitiveViewLog(AuditBase):
    __tablename__ = "ims_sys_sensitive_view_log"
    __audit_exempt__ = "log"
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False)
    biz_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    viewer_id: Mapped[int | None] = plain_id()
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Timeline(AuditBase):
    __tablename__ = "ims_sys_timeline"
    __audit_exempt__ = "log"
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False)
    biz_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    operator_id: Mapped[int | None] = plain_id()
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class JobLog(AuditBase):
    __tablename__ = "ims_sys_job_log"
    __audit_exempt__ = "log"
    job_name: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="SCHEDULE")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    success: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_digest: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ExportTask(AuditBase):
    __tablename__ = "ims_sys_export_task"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    query_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, default="demo_order")


class Outbox(AuditBase):
    __tablename__ = "ims_sys_outbox"
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MigrationPending(AuditBase):
    __tablename__ = "ims_sys_migration_pending"
    source_system: Mapped[str] = mapped_column(String(32), nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class WorkCalendar(AuditBase):
    __tablename__ = "ims_sys_work_calendar"
    __platform__ = True
    __table_args__ = (UniqueConstraint("cal_date", "deleted", name="uq_calendar_date"),)
    cal_date: Mapped[str] = mapped_column(String(10), nullable=False)
    day_type: Mapped[str] = mapped_column(String(32), nullable=False)


class LeaveRecord(AuditBase):
    __tablename__ = "ims_meet_leave_record"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "leave_date", "approval_no", "deleted", name="uq_leave"),
    )
    user_id: Mapped[int] = ref_column(Ref(_USER, "RESTRICT", enforce_delete=False), nullable=False)
    leave_date: Mapped[str] = mapped_column(String(10), nullable=False)
    portion: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False, default=1)
    approval_no: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)


class SyncState(AuditBase):
    __tablename__ = "ims_sys_sync_state"
    __table_args__ = (UniqueConstraint("tenant_id", "state_key", "deleted", name="uq_sync_state"),)
    state_key: Mapped[str] = mapped_column(String(64), nullable=False)
    state_value: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class TrainAiCallLog(AuditBase):
    __tablename__ = "ims_train_ai_call_log"
    __audit_exempt__ = "log"
    operator_id: Mapped[int | None] = plain_id()
    material_id: Mapped[int | None] = plain_id()
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
