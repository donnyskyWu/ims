"""审计基类与引用声明。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.clock import now_naive
from app.core.context import get_ctx


class Base(DeclarativeBase):
    pass


def audit_gaps(models) -> list[str]:
    """业务表必须继承审计基类或关联基类。"""
    gaps = []
    for model in models:
        table = getattr(model, "__tablename__", "")
        if not str(table).startswith("ims_"):
            continue
        if issubclass(model, (AuditBase, AssocBase)):
            continue
        gaps.append(getattr(model, "__name__", table))
    return gaps


class TenantBound:
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class AuditBase(Base, TenantBound):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    creator: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_naive)
    updater: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    update_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_naive)
    deleted: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class AssocBase(Base, TenantBound):
    """关联表：只要 tenant_id、create_time、creator。"""

    __abstract__ = True
    __audit_exempt__ = "assoc"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    creator: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_naive)


def _touch_insert(mapper, connection, target):
    ctx = get_ctx()
    current = now_naive()
    user_id = ctx.user_id if ctx and ctx.user_id is not None else 0
    if getattr(target, "creator", None) in (None, 0) or not isinstance(getattr(target, "creator", None), int):
        target.creator = user_id
    if getattr(target, "create_time", None) is None:
        target.create_time = current
    if hasattr(target, "updater") and getattr(target, "updater", None) in (None, 0):
        target.updater = user_id
    if hasattr(target, "update_time") and getattr(target, "update_time", None) is None:
        target.update_time = current
    if hasattr(target, "deleted") and getattr(target, "deleted", None) is None:
        target.deleted = 0
    if ctx and ctx.tenant_id is not None and not getattr(target.__class__, "__platform__", False):
        target.tenant_id = ctx.tenant_id
    elif getattr(target, "tenant_id", None) is None:
        target.tenant_id = ctx.tenant_id if ctx and ctx.tenant_id is not None else 1


def _touch_update(mapper, connection, target):
    ctx = get_ctx()
    if hasattr(target, "updater"):
        target.updater = ctx.user_id if ctx and ctx.user_id is not None else 0
    if hasattr(target, "update_time"):
        target.update_time = now_naive()


event.listen(AuditBase, "before_insert", _touch_insert, propagate=True)
event.listen(AuditBase, "before_update", _touch_update, propagate=True)
event.listen(AssocBase, "before_insert", _touch_insert, propagate=True)


def audit_exempt_kind(model) -> str | None:
    return getattr(model, "__audit_exempt__", None)
