from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import plain_id, ref_column
from app.db.refs import Ref


class Message(AuditBase):
    __tablename__ = "ims_sys_message"
    __entity_label__ = "站内信"
    receiver_id: Mapped[int] = ref_column(Ref("ims_sys_user", "RESTRICT", enforce_delete=False), nullable=False)
    msg_type: Mapped[str] = mapped_column(String(32), nullable=False, default="SYSTEM", info={"dict": "dict_msg_type"})
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    route: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_module: Mapped[str | None] = mapped_column(String(64), nullable=True)
    read_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNREAD")
    read_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NotifyRecord(AuditBase):
    __tablename__ = "ims_sys_notify_record"
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    biz_key: Mapped[str] = mapped_column(String(128), nullable=False)
    receiver_id: Mapped[int] = plain_id(nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SENT")
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
