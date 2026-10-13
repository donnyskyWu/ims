"""设备台账、穿透关联与校验工单。不建物理外键。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref


class AssetLedger(AuditBase):
    __tablename__ = "ims_asset_ledger"
    __entity_label__ = "资产"
    __table_args__ = (UniqueConstraint("tenant_id", "asset_code", "deleted", name="uq_asset_code"),)
    asset_code: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    asset_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, default="OFFICE", info={"dict": "dict_asset_type"})
    spec: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW", info={"dict": "dict_asset_status"})
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT", enforce_delete=True))
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    photo_file_keys: Mapped[list | None] = mapped_column(JSON, nullable=True)
    purchase_batch_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class AssetEvent(AuditBase):
    __tablename__ = "ims_asset_event"
    __entity_label__ = "资产动态"
    asset_id: Mapped[int] = ref_column(Ref("ims_asset_ledger", "CASCADE_SOFT", enforce_delete=False), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    from_owner_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    to_owner_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    operator_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssetBind(AuditBase):
    """账号与场次的绑定位。本批只建表，写入留给后续批次。"""

    __tablename__ = "ims_asset_bind"
    __entity_label__ = "资产绑定"
    asset_id: Mapped[int] = ref_column(Ref("ims_asset_ledger", "RESTRICT"), nullable=False)
    account_id: Mapped[int | None] = ref_column(Ref("ims_account_platform", "RESTRICT", allow_disabled=True))
    session_id: Mapped[int | None] = plain_id()
    bind_type: Mapped[str] = mapped_column(String(32), nullable=False, default="HOLD")
    bind_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    effective_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssetPurchaseBatch(AuditBase):
    __tablename__ = "ims_asset_purchase_batch"
    __entity_label__ = "采购批次"
    batch_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    file_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="office")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_detail: Mapped[list | None] = mapped_column(JSON, nullable=True)


class AssetVerifyBatch(AuditBase):
    __tablename__ = "ims_asset_verify_batch"
    __entity_label__ = "校验批次"
    __table_args__ = (UniqueConstraint("tenant_id", "batch_no", "deleted", name="uq_verify_batch"),)
    batch_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    verify_type: Mapped[str] = mapped_column(String(32), nullable=False, default="asset_person", info={"dict": "dict_asset_verify_type"})
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="FULL")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="RUNNING")


class AssetVerifyTask(AuditBase):
    __tablename__ = "ims_asset_verify_task"
    __entity_label__ = "校验工单"
    task_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    batch_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    asset_id: Mapped[int] = ref_column(Ref("ims_asset_ledger", "RESTRICT", enforce_delete=False), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    inconsistent_fields: Mapped[list | None] = mapped_column(JSON, nullable=True)
    task_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_DISPATCH", info={"dict": "dict_asset_verify_task_status"})
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", allow_disabled=True, enforce_delete=False))
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    fix_remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recheck_remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    batch_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, info={"not_a_ref": True})
