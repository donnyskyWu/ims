from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditBase
from app.db.columns import plain_id


class StoredFile(AuditBase):
    __tablename__ = "ims_file"
    __entity_label__ = "文件"
    __table_args__ = (UniqueConstraint("file_key", "deleted", name="uq_file_key"),)
    file_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scene: Mapped[str] = mapped_column(String(32), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ext: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    biz_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    biz_id: Mapped[int | None] = plain_id()
    ever_bound: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    orphan_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
