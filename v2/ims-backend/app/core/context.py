"""请求上下文。系统上下文不得用于处理 HTTP 请求。"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    trace_id: str = ""
    user_id: int | None = None
    tenant_id: int | None = None
    perm_codes: set[str] = field(default_factory=set)
    perm_details: dict = field(default_factory=dict)
    data_scopes: set[str] = field(default_factory=set)
    dept_ids: list[int] = field(default_factory=list)
    ip_group_ids: list[int] = field(default_factory=list)
    client_ip: str = ""
    system: bool = False
    skip_tenant: bool = False
    skip_scope: bool = False
    pwd_reset_required: bool = False
    session_id: str = ""
    username: str = ""
    nickname: str = ""


_ctx: ContextVar[RequestContext | None] = ContextVar("ims_ctx", default=None)


def get_ctx() -> RequestContext | None:
    return _ctx.get()


def set_ctx(ctx: RequestContext | None):
    return _ctx.set(ctx)


def reset_ctx(token) -> None:
    _ctx.reset(token)


@contextmanager
def use_context(ctx: RequestContext):
    token = set_ctx(ctx)
    try:
        yield ctx
    finally:
        reset_ctx(token)


def system_context(tenant_id: int, trace_id: str = "system") -> RequestContext:
    return RequestContext(
        trace_id=trace_id,
        user_id=0,
        tenant_id=tenant_id,
        system=True,
        skip_scope=True,
        data_scopes={"ALL"},
        nickname="系统",
        username="system",
    )
