"""账号领用、流转、归还、充值与采集凭证。不建物理外键。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import ref_column
from app.db.refs import Ref
from app.db.types import EncryptedString

_USER = Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False)
_ACCOUNT = Ref("ims_account_platform", "RESTRICT", allow_disabled=True)


class CollectCredential(AuditBase):
    __tablename__ = "ims_account_collect_credential"
    __entity_label__ = "采集凭证"
    __table_args__ = (UniqueConstraint("tenant_id", "account_id", "deleted", name="uq_collect_account"),)
    account_id: Mapped[int] = ref_column(_ACCOUNT, nullable=False)
    cookie_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    token_enc: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    field_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_probe_ok: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collector_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    probe_message: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AccountApply(AuditBase):
    __tablename__ = "ims_account_apply"
    __entity_label__ = "领用单"
    __table_args__ = (UniqueConstraint("tenant_id", "apply_no", "deleted", name="uq_apply_no"),)
    apply_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    account_id: Mapped[int] = ref_column(_ACCOUNT, nullable=False)
    applicant_user_id: Mapped[int] = ref_column(_USER, nullable=False)
    purpose: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    plan_start: Mapped[date] = mapped_column(Date, nullable=False)
    plan_end: Mapped[date] = mapped_column(Date, nullable=False)
    apply_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_APPROVAL", info={"dict": "dict_apply_status"})
    flow_instance_id: Mapped[int | None] = mapped_column(Integer, nullable=True, info={"not_a_ref": True})
    handover_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idle_reminded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AccountTransfer(AuditBase):
    __tablename__ = "ims_account_transfer"
    __entity_label__ = "流转单"
    __table_args__ = (UniqueConstraint("tenant_id", "transfer_no", "deleted", name="uq_transfer_no"),)
    transfer_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    account_id: Mapped[int] = ref_column(_ACCOUNT, nullable=False)
    transfer_type: Mapped[str] = mapped_column(String(32), nullable=False, default="TRANSFER", info={"dict": "dict_transfer_type"})
    from_user_id: Mapped[int | None] = ref_column(_USER)
    to_user_id: Mapped[int | None] = ref_column(_USER)
    reason_type: Mapped[str | None] = mapped_column(String(32), nullable=True, info={"dict": "dict_transfer_reason"})
    remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_CONFIRM", info={"dict": "dict_transfer_status"})
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_assets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ReturnOrder(AuditBase):
    __tablename__ = "ims_account_return_order"
    __entity_label__ = "归还单"
    __table_args__ = (UniqueConstraint("tenant_id", "return_no", "deleted", name="uq_return_no"),)
    return_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    user_id: Mapped[int] = ref_column(_USER, nullable=False)
    resign_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="IN_PROGRESS", info={"dict": "dict_return_order_status"})
    manual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    suspend_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)


class ReturnItem(AuditBase):
    __tablename__ = "ims_account_return_item"
    __entity_label__ = "归还项"
    order_id: Mapped[int] = ref_column(Ref("ims_account_return_order", "CASCADE_SOFT"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ACCOUNT")
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0, info={"not_a_ref": True})
    item_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    item_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", info={"dict": "dict_return_item_status"})
    handler_user_id: Mapped[int | None] = ref_column(_USER)
    transfer_to_user_id: Mapped[int | None] = ref_column(_USER)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
    transfer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, info={"not_a_ref": True})


class Recharge(AuditBase):
    __tablename__ = "ims_account_recharge"
    __entity_label__ = "充值"
    account_id: Mapped[int] = ref_column(_ACCOUNT, nullable=False)
    amount_fen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="ALIPAY", info={"dict": "dict_recharge_channel"})
    recharge_date: Mapped[date] = mapped_column(Date, nullable=False)
    voucher_file_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verify_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED", info={"dict": "dict_recharge_verify_status"})
    verify_diff_fen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_user_id: Mapped[int | None] = ref_column(_USER)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)


class RechargeVerify(AuditBase):
    __tablename__ = "ims_account_recharge_verify"
    __entity_label__ = "充值核对"
    month: Mapped[str] = mapped_column(String(7), nullable=False, default="")
    total_recharge_fen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    platform_consumed_fen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diff_rate_bp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diff_detail: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ticket_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
