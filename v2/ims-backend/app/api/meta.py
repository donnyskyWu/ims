"""路由元数据。路由函数返回数据对象，由包装器套统一响应。"""
from __future__ import annotations

import inspect
from functools import wraps

REGISTRY: list[dict] = []


def mark(
    perm: str | None = None,
    *,
    anonymous: bool = False,
    login_only: bool = False,
    scope_model=None,
    sensitive_view: bool = False,
    returns_plain: bool = False,
    idempotent: bool = False,
    operate: tuple[str, str] | None = None,
    any_perm: tuple[str, ...] | None = None,
    **_ignored,
):
    def deco(fn):
        meta = {
            "perm": perm,
            "anonymous": anonymous,
            "login_only": login_only,
            "scope_model": scope_model,
            "sensitive_view": sensitive_view,
            "returns_plain": returns_plain,
            "idempotent": idempotent,
            "operate": operate,
            "any_perm": any_perm,
            "fn": fn,
        }

        @wraps(fn)
        def wrapped(*args, **kwargs):
            from app.api.runtime import invoke

            return invoke(meta, fn, args, kwargs)

        wrapped.__ims_meta__ = meta
        wrapped.__ims_view__ = fn
        REGISTRY.append(meta)
        meta["endpoint"] = wrapped
        return wrapped

    return deco


def iter_endpoints():
    for item in REGISTRY:
        yield item
