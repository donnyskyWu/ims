"""公司容量留痕。证件预警与分级表在 cert 域。"""
from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import ref_column
from app.db.refs import Ref


class CompanyCapacityLog(AuditBase):
    __tablename__ = "ims_org_company_capacity_log"
    __entity_label__ = "容量调整"
    company_id: Mapped[int] = ref_column(Ref("ims_org_company", "RESTRICT", enforce_delete=False), nullable=False)
    before_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    after_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    operator_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    operator_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
