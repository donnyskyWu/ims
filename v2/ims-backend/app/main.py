"""应用工厂。"""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.runtime import new_trace, reset_current_request, set_current_request
from app.catalog import ANON_ROUTES, PERM_CODES
from app.core.config import get_settings, load_settings, set_settings
from app.core.error_codes import check_messages, install_registry
from app.core.errors import StartupError
from app.core.redis_client import configure_redis, get_redis
from app.db.refs import validate_refs
from app.db.repository import register_tables
from app.db.session import get_engine, init_engine
from app.domains import all_models
from app.domains.auth.router import router as auth_router
from app.domains.callback.router import router as callback_router
from app.domains.demo.router import router as demo_router
from app.domains.file.router import router as file_router
from app.domains.flow.router import router as flow_router
from app.domains.message.router import router as message_router
from app.domains.system.extra_router import router as system_extra_router
from app.domains.system.ops_router import router as system_ops_router
from app.domains.system.org_router import router as org_router
from app.domains.system.router import router as system_router
from app.domains.todo.router import router as todo_router
from app.domains.export_task.router import router as export_router

log = logging.getLogger("ims")

MOUNTS = [
    ("/admin-api/ims/auth", auth_router),
    ("/admin-api/ims/system", system_router),
    ("/admin-api/ims/system", system_extra_router),
    ("/admin-api/ims/demo", demo_router),
    ("/admin-api/ims/callback", callback_router),
    ("/admin-api/ims/file", file_router),
    ("/admin-api/ims/message", message_router),
    ("/admin-api/ims/todo", todo_router),
    ("/admin-api/ims/flow", flow_router),
    ("/admin-api/ims/system", system_ops_router),
    ("/admin-api/ims/system", org_router),
    ("/admin-api/ims/export-task", export_router),
]


def create_app(settings=None, extra_routers=None, extra_errors=None, extra_models=None, config_path: str | None = None):
    if settings is None:
        settings = load_settings(config_path=config_path) if config_path else load_settings()
    set_settings(settings)
    try:
        install_registry(extra_errors)
    except ValueError as exc:
        raise StartupError(str(exc)) from exc
    bad_msg = check_messages()
    if bad_msg:
        raise StartupError("错误码文案含编码: " + "; ".join(bad_msg))
    try:
        configure_redis(settings)
    except Exception as exc:
        raise StartupError("Redis 不可用") from exc
    init_engine(settings)
    models = list(all_models()) + list(extra_models or [])
    problems = validate_refs(models)
    if problems:
        raise StartupError("引用登记不通过: " + "; ".join(problems))
    register_tables(models)
    app = FastAPI(
        title="IMS",
        version=settings.version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    _install_middleware(app)
    app.add_api_route("/health", health, methods=["GET"], summary="健康检查")
    for prefix, router in MOUNTS:
        app.include_router(router, prefix=prefix)
    if settings.env == "test":
        from app.domains.demo.error_router import router as error_router

        app.include_router(error_router, prefix="/admin-api/ims/demo")
    for router in extra_routers or []:
        prefix = getattr(router, "prefix_override", "")
        app.include_router(router, prefix=prefix)
    _validate_routes(app)
    _football_schema(settings)
    app.state.settings = settings
    return app


def _install_middleware(app: FastAPI):
    @app.middleware("http")
    async def _trace(request: Request, call_next):
        request.state.trace_id = new_trace(request)
        request.state.client_ip = request.client.host if request.client else ""
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            raw = await request.body()
            request.state.raw_body = raw
            try:
                request.state.json_body = json.loads(raw.decode() or "{}") if raw else {}
            except Exception:
                request.state.json_body = {}
        token = set_current_request(request)
        try:
            response = await call_next(request)
        finally:
            reset_current_request(token)
        response.headers["X-Trace-Id"] = request.state.trace_id
        log.info("trace=%s %s %s", request.state.trace_id, request.method, request.url.path)
        return response


def health():
    settings = get_settings()
    db = "UP"
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db = "DOWN"
    if settings.redis_memory:
        redis_state = "MEMORY"
    else:
        try:
            get_redis().ping()
            redis_state = "UP"
        except Exception:
            redis_state = "DOWN"
    football = "DISABLED"
    if settings.football_live.enabled:
        football = "UP"
        try:
            from sqlalchemy import create_engine

            engine = create_engine(settings.football_live.url(), pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            football = "DOWN"
    status = "UP"
    http_status = 200
    if db == "DOWN":
        status = "DOWN"
        http_status = 503
    elif redis_state == "DOWN" or football == "DOWN":
        status = "DEGRADED"
    body = {
        "code": 0,
        "msg": "成功",
        "data": {"status": status, "db": db, "redis": redis_state, "footballLive": football, "version": settings.version},
    }
    return JSONResponse(status_code=http_status, content=body)


def _iter_routes(app: FastAPI):
    for route in app.routes:
        if type(route).__name__ == "_IncludedRouter":
            prefix = route.include_context.prefix or ""
            for sub in route.original_router.routes:
                yield prefix + getattr(sub, "path", ""), sub
            continue
        path = getattr(route, "path", None)
        if path:
            yield path, route


def _validate_routes(app: FastAPI):
    missing_summary = []
    for path, route in _iter_routes(app):
        methods = getattr(route, "methods", None) or set()
        endpoint = getattr(route, "endpoint", None)
        if path in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
            continue
        summary = getattr(route, "summary", None)
        if not summary and path != "/health":
            missing_summary.append(path)
            continue
        if path != "/health" and not path.startswith("/admin-api/ims/"):
            raise StartupError(f"路由前缀不符: {path}")
        meta = getattr(endpoint, "__ims_meta__", None)
        if path == "/health":
            continue
        if meta is None:
            raise StartupError(f"路由未声明权限: {path}")
        for method in methods:
            if meta.get("anonymous") and (method, path) not in ANON_ROUTES:
                raise StartupError(f"匿名路由不在白名单: {method} {path}")
        if not meta.get("anonymous") and not meta.get("login_only") and not meta.get("perm") and not meta.get("any_perm"):
            raise StartupError(f"路由未声明权限码: {path}")
        for code in [meta.get("perm"), *(meta.get("any_perm") or [])]:
            if code and code not in PERM_CODES:
                raise StartupError(f"权限码未在菜单种子中登记: {code}")
        model = meta.get("scope_model")
        if model is not None and not getattr(model, "__scope_fields__", None) and not getattr(model, "__scope_resolver__", None):
            raise StartupError(f"数据范围模型未声明范围字段: {getattr(model, '__name__', model)}")
    if missing_summary:
        raise StartupError("路由缺少摘要: " + ", ".join(missing_summary))


def _football_schema(settings):
    mode = settings.football_live.schema_check
    if mode == "off" or not settings.football_live.enabled:
        return
    from app.integrations.football_live.schema_check import check_schema

    warnings = check_schema(settings)
    if warnings and mode == "strict":
        raise StartupError("Football 结构不一致: " + "; ".join(warnings))
    for item in warnings:
        log.warning("Football 结构警告: %s", item)


def app():
    return create_app()
