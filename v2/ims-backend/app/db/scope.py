"""数据范围谓词。未配置即无数据。"""
from __future__ import annotations

from sqlalchemy import false, or_, select

from app.core.context import get_ctx
from app.core.errors import BizError


class EmptyScope:
    pass


EMPTY = EmptyScope()


def scope_clause(model, write: bool = False):
    ctx = get_ctx()
    if ctx is None or ctx.user_id is None or ctx.tenant_id is None:
        if write:
            raise BizError(1008)
        return EMPTY
    if ctx.skip_scope or ctx.system:
        return None
    fields = getattr(model, "__scope_fields__", None)
    resolver = getattr(model, "__scope_resolver__", None)
    if not fields and not resolver:
        return None
    scopes = {item for item in (ctx.data_scopes or set()) if item}
    if not scopes:
        if write:
            raise BizError(1008)
        return EMPTY
    if "ALL" in scopes:
        return None
    clauses = []
    if resolver == "user":
        from app.domains.system.model import User, UserDept

        if "DEPT" in scopes:
            dept_ids = ctx.dept_ids or [-1]
            clauses.append(User.id.in_(select(UserDept.user_id).where(UserDept.dept_id.in_(dept_ids))))
        if "SELF" in scopes:
            clauses.append(User.id == ctx.user_id)
    else:
        if "DEPT" in scopes and fields and "dept" in fields:
            clauses.append(getattr(model, fields["dept"]).in_(ctx.dept_ids or [-1]))
        if "IP_GROUP" in scopes and fields and "ip_group" in fields:
            clauses.append(getattr(model, fields["ip_group"]).in_(ctx.ip_group_ids or [-1]))
        if "SELF" in scopes:
            owner = (fields or {}).get("owner") or "creator"
            if not hasattr(model, owner):
                owner = "creator"
            if hasattr(model, owner):
                clauses.append(getattr(model, owner) == ctx.user_id)
    if not clauses:
        if write:
            raise BizError(1008)
        return EMPTY
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)


def shared_visible(model):
    """发布时快照覆盖查看者才可见。"""
    ctx = get_ctx()
    base = scope_clause(model)
    if not getattr(model, "__shared__", False) or ctx is None:
        return base
    # 快照在查询后于 Python 侧再滤，避免把 JSON 谓词写死。
    return base
