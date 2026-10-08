"""BR-212 行级双重过滤（查看者 dataScope ∩ 创建者 ims_user_scope）· BI 报表/分享。"""

from __future__ import annotations

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.models import BiReportDef, BiShareLink, User, UserDept, UserScope
from app.scope import DataScope


def primary_dept_id(db: Session, user_id: int, tenant_id: int) -> int:
    dept = db.scalar(
        select(UserDept.dept_id)
        .where(UserDept.user_id == user_id, UserDept.tenant_id == tenant_id)
        .order_by(UserDept.dept_id.asc())
        .limit(1)
    )
    return int(dept or 0)


def creator_br212_exists(creator_col, scope: DataScope, tenant_id: int):
    parts = [UserScope.scope_type == "ALL"]
    if scope.dept_ids:
        parts.append(
            and_(
                UserScope.scope_type == "DEPT",
                UserScope.scope_value.in_([str(d) for d in scope.dept_ids]),
            )
        )
    if scope.ip_group_ids:
        parts.append(
            and_(
                UserScope.scope_type == "IP_GROUP",
                UserScope.scope_value.in_([str(g) for g in scope.ip_group_ids]),
            )
        )
    parts.append(and_(UserScope.scope_type == "SELF", UserScope.user_id == scope.user_id))
    return exists(
        select(1).where(
            UserScope.deleted == 0,
            UserScope.tenant_id == tenant_id,
            UserScope.user_id == creator_col,
            or_(*parts),
        )
    )


def apply_viewer_axis_report(stmt: Select, scope: DataScope | None) -> Select:
    if scope is None or scope.kind == "ALL":
        return stmt
    if scope.kind == "SELF":
        return stmt.where(BiReportDef.creator_id == scope.user_id)
    if scope.kind == "DEPT":
        if not scope.dept_ids:
            return stmt.where(BiReportDef.id < 0)
        return stmt.where(BiReportDef.dept_id.in_(scope.dept_ids))
    return stmt.where(BiReportDef.id < 0)


def apply_viewer_axis_share(stmt: Select, scope: DataScope | None) -> Select:
    if scope is None or scope.kind == "ALL":
        return stmt
    if scope.kind == "SELF":
        return stmt.where(BiShareLink.creator_user_id == scope.user_id)
    if scope.kind == "DEPT":
        if not scope.dept_ids:
            return stmt.where(BiShareLink.id < 0)
        return stmt.where(BiShareLink.dept_id.in_(scope.dept_ids))
    return stmt.where(BiShareLink.id < 0)


def restrict_report_def(stmt: Select, scope: DataScope | None, tenant_id: int) -> Select:
    stmt = apply_viewer_axis_report(stmt, scope)
    if scope is not None:
        stmt = stmt.where(creator_br212_exists(BiReportDef.creator_id, scope, tenant_id))
    return stmt


def restrict_share_link(stmt: Select, scope: DataScope | None, tenant_id: int) -> Select:
    stmt = apply_viewer_axis_share(stmt, scope)
    if scope is not None:
        stmt = stmt.where(creator_br212_exists(BiShareLink.creator_user_id, scope, tenant_id))
    return stmt


def report_row_visible(db: Session, row: BiReportDef, actor: User, scope: DataScope | None) -> bool:
    if row.deleted or row.tenant_id != (actor.tenant_id or 0):
        return False
    tenant_id = actor.tenant_id or 0
    stmt = restrict_report_def(
        select(BiReportDef.id).where(BiReportDef.id == row.id, BiReportDef.deleted == 0),
        scope,
        tenant_id,
    )
    found = db.scalar(stmt)
    return found is not None


def share_row_visible(db: Session, row: BiShareLink, actor: User, scope: DataScope | None) -> bool:
    if row.deleted or row.tenant_id != (actor.tenant_id or 0):
        return False
    tenant_id = actor.tenant_id or 0
    stmt = restrict_share_link(
        select(BiShareLink.id).where(BiShareLink.id == row.id, BiShareLink.deleted == 0),
        scope,
        tenant_id,
    )
    found = db.scalar(stmt)
    return found is not None
