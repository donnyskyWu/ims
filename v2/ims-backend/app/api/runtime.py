"""请求包装：会话、认证、幂等、操作日志、统一响应。"""
from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from contextvars import ContextVar

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import OperationalError

from app.catalog import ANON_ROUTES, PWD_RESET_ALLOW
from app.core.context import RequestContext, reset_ctx, set_ctx
from app.core.errors import BizError
from app.core.serialize import stringify_ids
from app.db.session import session_scope

_request_cv: ContextVar[Request | None] = ContextVar("ims_request", default=None)
log = logging.getLogger("ims.http")


def current_request() -> Request | None:
    return _request_cv.get()


def set_current_request(request: Request | None):
    return _request_cv.set(request)


def reset_current_request(token) -> None:
    _request_cv.reset(token)


def envelope(data, code=0, msg="成功"):
    return {"code": code, "msg": msg, "data": stringify_ids(data)}


def invoke(meta: dict, fn, args, kwargs):
    request = current_request()
    started = time.perf_counter()
    path = request.url.path if request else ""
    method = request.method if request else "POST"
    trace = getattr(request.state, "trace_id", "") if request else ""
    try:
        with session_scope(commit=False) as session:
            ctx = _build_ctx(request, meta)
            token = set_ctx(ctx)
            try:
                cached = _idempotent_begin(request, meta, ctx)
                if cached is not None:
                    return cached
                if request is not None and meta.get("operate") is None and method != "GET":
                    pass
                data = fn(*args, **kwargs)
                if isinstance(data, Response):
                    session.commit()
                    return data
                body = envelope(data)
                session.commit()
                _idempotent_store(request, meta, ctx, body, 200)
                _operate(meta, request, ctx, True, None, data, started)
                return body
            except BizError as exc:
                session.rollback()
                body = {"code": exc.code, "msg": exc.msg, "data": stringify_ids(exc.data)}
                _idempotent_store(request, meta, ctx, body, exc.http_status)
                _operate(meta, request, ctx, False, exc.code, None, started)
                return JSONResponse(status_code=exc.http_status, content=body)
            except OperationalError as exc:
                session.rollback()
                log.exception("数据库异常 trace=%s", trace)
                return JSONResponse(status_code=200, content={"code": 5001, "msg": "数据库异常，请稍后再试", "data": None})
            except Exception as exc:
                session.rollback()
                from app.core.redis_client import RedisDown

                if exc.__class__.__name__ in {"RedisError", "ConnectionError", "TimeoutError"} or isinstance(exc, RedisDown):
                    log.exception("缓存异常 trace=%s", trace)
                    return JSONResponse(status_code=200, content={"code": 5002, "msg": "缓存服务异常，请稍后再试", "data": None})
                log.error("未处理异常 trace=%s\n%s", trace, traceback.format_exc())
                return JSONResponse(status_code=200, content={"code": 5007, "msg": "系统繁忙，请稍后再试", "data": None})
            finally:
                reset_ctx(token)
    except BizError as exc:
        return JSONResponse(status_code=exc.http_status, content={"code": exc.code, "msg": exc.msg, "data": exc.data})
    except Exception as exc:
        from app.core.redis_client import RedisDown

        trace = getattr(request.state, "trace_id", "") if request else ""
        if isinstance(exc, RedisDown) or exc.__class__.__name__ in {"RedisError", "ConnectionError", "TimeoutError"}:
            log.exception("缓存异常 trace=%s", trace)
            return JSONResponse(status_code=200, content={"code": 5002, "msg": "缓存服务异常，请稍后再试", "data": None})
        if isinstance(exc, OperationalError):
            log.exception("数据库异常 trace=%s", trace)
            return JSONResponse(status_code=200, content={"code": 5001, "msg": "数据库异常，请稍后再试", "data": None})
        log.error("未处理异常 trace=%s\n%s", trace, traceback.format_exc())
        return JSONResponse(status_code=200, content={"code": 5007, "msg": "系统繁忙，请稍后再试", "data": None})


def _build_ctx(request: Request | None, meta: dict) -> RequestContext:
    trace = getattr(request.state, "trace_id", "") if request else ""
    ip = getattr(request.state, "client_ip", "") if request else ""
    if meta.get("anonymous"):
        return RequestContext(trace_id=trace, client_ip=ip)
    if request is None:
        raise BizError(1008)
    auth = request.headers.get("authorization") or ""
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not token:
        if meta.get("anonymous"):
            return RequestContext(trace_id=trace, client_ip=ip)
        raise BizError(1008)
    from app.services.sessions import load_access

    principal = load_access(token)
    path = request.url.path
    method = request.method
    if principal.pwd_reset_required and (method, path) not in PWD_RESET_ALLOW:
        raise BizError(1008, "请先修改密码")
    if not meta.get("login_only") and not meta.get("anonymous"):
        allowed = set(meta.get("any_perm") or [])
        if meta.get("perm"):
            allowed.add(meta["perm"])
        if not allowed or not (principal.perm_codes & allowed):
            raise BizError(1008)
    principal.trace_id = trace
    principal.client_ip = ip
    return principal


def _idem_key(request, ctx) -> str | None:
    if request is None:
        return None
    token = request.headers.get("x-client-token")
    if not token:
        return ""
    uid = ctx.user_id if ctx else 0
    return f"ims:idem:{uid}:{token}"


def _idempotent_begin(request, meta, ctx):
    if not meta.get("idempotent"):
        return None
    key = _idem_key(request, ctx)
    if key == "":
        raise BizError(1001, data={"fieldErrors": [{"field": "xClientToken", "message": "缺少幂等令牌"}]})
    from app.core.redis_client import get_redis

    redis = get_redis()
    existing = redis.get(key)
    if existing:
        payload = json.loads(existing)
        if payload.get("state") == "done":
            return JSONResponse(status_code=payload.get("status") or 200, content=payload["body"])
        deadline = time.time() + 5
        while time.time() < deadline:
            time.sleep(0.05)
            existing = redis.get(key)
            if existing:
                payload = json.loads(existing)
                if payload.get("state") == "done":
                    return JSONResponse(status_code=payload.get("status") or 200, content=payload["body"])
        raise BizError(1001, "请求正在处理中")
    redis.set(key, json.dumps({"state": "run"}), ex=600)
    return None


def _idempotent_store(request, meta, ctx, body, status):
    if not meta.get("idempotent"):
        return
    key = _idem_key(request, ctx)
    if not key:
        return
    from app.core.redis_client import get_redis

    get_redis().set(key, json.dumps({"state": "done", "status": status, "body": body}), ex=86400)


def _operate(meta, request, ctx, success, code, data, started):
    if request is None or request.method == "GET":
        return
    operate = meta.get("operate")
    if not operate and success:
        return
    if not operate:
        return
    try:
        from app.domains.system.model import OperateLog
        from app.db.session import session_scope as scope
        from app.core.context import use_context

        raw = {}
        if request.method != "GET":
            raw = getattr(request.state, "json_body", None) or {}
        digest = _mask_params(raw)
        object_id = None
        if isinstance(data, dict) and "id" in data:
            object_id = str(data["id"])
        row = OperateLog(
            operator_id=ctx.user_id if ctx else None,
            operator_name=(ctx.nickname or ctx.username) if ctx else "",
            module=operate[0],
            action=operate[1],
            object_type=operate[0],
            object_id=object_id,
            success=1 if success else 0,
            error_code=code,
            ip=ctx.client_ip if ctx else "",
            cost_ms=int((time.perf_counter() - started) * 1000),
            path=request.url.path,
            method=request.method,
            params_digest=digest,
            tenant_id=ctx.tenant_id if ctx and ctx.tenant_id else 1,
            creator=ctx.user_id if ctx and ctx.user_id else 0,
        )
        with scope(commit=True) as session:
            with use_context(ctx):
                session.add(row)
                session.flush()
    except Exception:
        log.exception("操作日志写入失败 trace=%s", getattr(ctx, "trace_id", ""))


def _mask_params(raw) -> str:
    if not isinstance(raw, dict):
        return ""

    def mask(key, value):
        low = key.lower().replace("_", "")
        if low in {"password", "secret", "apikey", "token", "appsecret"} or "password" in low:
            return "******"
        if "mobile" in low and isinstance(value, str) and len(value) >= 7:
            return value[:3] + "****" + value[-4:]
        if low == "idcard" and isinstance(value, str) and len(value) >= 8:
            return value[:3] + "*" * (len(value) - 7) + value[-4:]
        hidden = {"phone", "phonenumber", "idno", "certno", "certnoplain", "iccid"}
        if low in hidden and isinstance(value, str) and value:
            if len(value) <= 7:
                return "****"
            return value[:3] + "****" + value[-4:]
        if isinstance(value, dict):
            return {k: mask(k, v) for k, v in value.items()}
        return value

    try:
        return json.dumps({k: mask(k, v) for k, v in raw.items()}, ensure_ascii=False)
    except Exception:
        return ""


def new_trace(request: Request) -> str:
    incoming = request.headers.get("x-trace-id")
    if incoming:
        return incoming
    return str(uuid.uuid4())
