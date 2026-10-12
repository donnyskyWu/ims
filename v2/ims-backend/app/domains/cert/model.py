"""证件预警、分级配置与查看审计。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import ref_column
from app.db.refs import Ref


class CertExpireTask(AuditBase):
    __tablename__ = "ims_cert_expire_task"
    __entity_label__ = "证件预警"
    cert_id: Mapped[int] = ref_column(Ref("ims_master_cert", "RESTRICT", enforce_delete=False), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="YELLOW", info={"dict": "dict_cert_warn_level"})
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="WARNING", info={"dict": "dict_cert_expire_status"})
    notified_user_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remind_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace: Mapped[list | None] = mapped_column(JSON, nullable=True)


class CertLevelConfig(AuditBase):
    __tablename__ = "ims_cert_level_config"
    __entity_label__ = "证件分级"
    l2_role_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    l3_user_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    opacity: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("0.12"))
    position: Mapped[str] = mapped_column(String(32), nullable=False, default="BOTTOM_RIGHT")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CertViewLog(AuditBase):
    __tablename__ = "ims_cert_view_log"
    __entity_label__ = "证件查看"
    __audit_exempt__ = "log"
    cert_id: Mapped[int] = ref_column(Ref("ims_master_cert", "RESTRICT", enforce_delete=False), nullable=False)
    viewer_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    viewer_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    view_level: Mapped[str] = mapped_column(String(8), nullable=False, default="L1")
    watermark_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_flag: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    holder_label: Mapped[str | None] = mapped_column(Text, nullable=True)
