"""示例域，供框架单测与权限冒烟使用。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.types import EncryptedString
from app.db.columns import ref_column
from app.db.refs import Ref


class DemoOrder(AuditBase):
    __tablename__ = "ims_demo_order"
    __entity_label__ = "示例订单"
    __track_changes__ = True
    __scope_fields__ = {"dept": "dept_id", "ip_group": "ip_group_id", "owner": "owner_user_id"}
    __field_labels__ = {"amount": "金额", "mobile": "手机号", "id_card": "证件号", "name": "名称", "cost": "成本", "rate": "比例", "status": "状态"}
    __table_args__ = (UniqueConstraint("tenant_id", "code", "deleted", name="uq_demo_order_code"),)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    dept_id: Mapped[int | None] = ref_column(Ref("ims_sys_dept", "RESTRICT", enforce_delete=False))
    ip_group_id: Mapped[int | None] = ref_column(Ref("ims_ipg_group", "RESTRICT", enforce_delete=False))
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT"))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    id_card: Mapped[str | None] = mapped_column(EncryptedString, nullable=True, info={"sensitive": "id_card"})
    id_card_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile: Mapped[str | None] = mapped_column(EncryptedString, nullable=True, info={"sensitive": "mobile"})
    mobile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, info={"sensitive": "cost"})
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", info={"dict": "dict_demo_status"})
    biz_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    biz_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    realname_id: Mapped[int | None] = ref_column(Ref("ims_master_realname", "RESTRICT", enforce_delete=False))


class DemoOrderItem(AuditBase):
    __tablename__ = "ims_demo_order_item"
    __entity_label__ = "示例明细"
    order_id: Mapped[int] = ref_column(Ref("ims_demo_order", "CASCADE_SOFT"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")


class DemoNote(AuditBase):
    __tablename__ = "ims_demo_note"
    __entity_label__ = "示例备注"
    __track_changes__ = True
    order_id: Mapped[int | None] = ref_column(Ref("ims_demo_order", "SET_NULL"))
    content: Mapped[str] = mapped_column(String(200), nullable=False, default="")


class DemoDoc(AuditBase):
    __tablename__ = "ims_demo_doc"
    __versioned__ = True
    __entity_label__ = "示例文档"
    __scope_fields__ = {"owner": "owner_user_id"}
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))


class DemoDeptOnly(AuditBase):
    __tablename__ = "ims_demo_dept_only"
    __entity_label__ = "仅部门范围示例"
    __scope_fields__ = {"dept": "dept_id"}
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    dept_id: Mapped[int | None] = ref_column(Ref("ims_sys_dept", "RESTRICT", enforce_delete=False))


class DemoShare(AuditBase):
    __tablename__ = "ims_demo_share"
    __entity_label__ = "示例分享"
    __shared__ = True
    __scope_fields__ = {"dept": "dept_id", "owner": "owner_user_id"}
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    dept_id: Mapped[int | None] = ref_column(Ref("ims_sys_dept", "RESTRICT", enforce_delete=False))
    owner_user_id: Mapped[int | None] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False))
    publish_scope: Mapped[dict | None] = mapped_column(JSON, nullable=True)
