"""直播场次扩展表。只加列，不建物理外键。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import ref_column
from app.db.refs import Ref

_SESSION = Ref("ims_live_session", "RESTRICT", enforce_delete=False)
_USER = Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False)
_ASSET = Ref("ims_asset_ledger", "RESTRICT", enforce_delete=False)


class LiveSessionDevice(AuditBase):
    __tablename__ = "ims_live_session_device"
    __entity_label__ = "场次设备"
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    asset_id: Mapped[int] = ref_column(_ASSET, nullable=False)


class LiveRiskCheck(AuditBase):
    __tablename__ = "ims_live_risk_check"
    __entity_label__ = "场次风控"
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    check_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    check_item: Mapped[str] = mapped_column(String(32), nullable=False, default="", info={"dict": "dict_risk_check_item"})
    check_result: Mapped[str] = mapped_column(String(16), nullable=False, default="PASS")
    score_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LiveReport(AuditBase):
    __tablename__ = "ims_live_report"
    __entity_label__ = "下播报告"
    __table_args__ = (UniqueConstraint("tenant_id", "session_id", "deleted", name="uq_live_report_session"),)
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gmv: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    order_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    viewer_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_online: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_fans: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    ad_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    entry_status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT", info={"dict": "dict_entry_status"})
    entry_user_id: Mapped[int | None] = ref_column(_USER)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirm_user_id: Mapped[int | None] = ref_column(_USER)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class LiveCost(AuditBase):
    __tablename__ = "ims_live_cost"
    __entity_label__ = "场次成本"
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    cost_type: Mapped[str] = mapped_column(String(16), nullable=False, default="AD", info={"dict": "dict_live_cost_type"})
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    ref_recharge_id: Mapped[int | None] = ref_column(Ref("ims_account_recharge", "RESTRICT", enforce_delete=True))
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)


class LiveReportCorrection(AuditBase):
    __tablename__ = "ims_live_report_correction"
    __entity_label__ = "下播更正"
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    operator_id: Mapped[int | None] = ref_column(_USER)


class LiveDataSnapshot(AuditBase):
    __tablename__ = "ims_live_data_snapshot"
    __entity_label__ = "直播数据快照"
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="FOOTBALL")
    viewer_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reserve_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    room_start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    room_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LiveAlarmRule(AuditBase):
    __tablename__ = "ims_live_alarm_rule"
    __entity_label__ = "直播告警规则"
    __table_args__ = (UniqueConstraint("tenant_id", "rule_name", "deleted", name="uq_live_alarm_rule_name"),)
    rule_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    rule_type: Mapped[str] = mapped_column(String(16), nullable=False, default="THRESHOLD")
    metric: Mapped[str] = mapped_column(String(32), nullable=False, default="", info={"dict": "dict_alarm_metric"})
    operator: Mapped[str] = mapped_column(String(16), nullable=False, default="GT")
    threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    window_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(8), nullable=False, default="2", info={"dict": "dict_alert_level"})
    notify_role_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notify_user_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DISABLED", info={"dict": "dict_common_status"})
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class LiveAlarmRecord(AuditBase):
    __tablename__ = "ims_live_alarm_record"
    __entity_label__ = "直播告警"
    rule_id: Mapped[int | None] = ref_column(Ref("ims_live_alarm_rule", "RESTRICT", enforce_delete=False))
    session_id: Mapped[int] = ref_column(_SESSION, nullable=False)
    alarm_level: Mapped[str] = mapped_column(String(8), nullable=False, default="2", info={"dict": "dict_alert_level"})
    alarm_content: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    occur_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    merge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_occur_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    handle_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNHANDLED", info={"dict": "dict_alarm_handle_status"})
    handler_user_id: Mapped[int | None] = ref_column(_USER)
    handle_remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalated: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LiveSupplement(AuditBase):
    __tablename__ = "ims_live_supplement"
    __entity_label__ = "历史补录"
    register_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supplement_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    applicant_id: Mapped[int | None] = ref_column(_USER)
    approver_id: Mapped[int | None] = ref_column(_USER)
    opinion: Mapped[str | None] = mapped_column(String(512), nullable=True)
    session_id: Mapped[int | None] = ref_column(_SESSION)
    cost_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reject_editable: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
