"""会话、租户过滤、事务。"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import create_engine, event, false, true
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from app.core.config import Settings, get_settings
from app.core.context import get_ctx
from app.db.base import AssocBase, AuditBase

_engine = None
_factory = None
_session: ContextVar[Session | None] = ContextVar("ims_session", default=None)
_installed = False
SQL_LOG: list[str] = []
_sql_log_on = False


def set_sql_log(enabled: bool) -> None:
    global _sql_log_on
    _sql_log_on = enabled
    if enabled:
        SQL_LOG.clear()


def init_engine(settings: Settings | None = None):
    global _engine, _factory
    settings = settings or get_settings()
    _engine = create_engine(settings.db.url(), pool_pre_ping=True, future=True)
    _factory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    _install_filters()
    _install_sql_log(_engine)
    return _engine


def _install_sql_log(engine):
    @event.listens_for(engine, "before_cursor_execute")
    def _log(conn, cursor, statement, parameters, context, executemany):
        if _sql_log_on:
            SQL_LOG.append(statement)


def get_engine():
    if _engine is None:
        init_engine()
    return _engine


def get_session() -> Session:
    session = _session.get()
    if session is None:
        raise RuntimeError("当前没有数据库会话")
    return session


def _install_filters():
    global _installed
    if _installed:
        return
    _installed = True

    @event.listens_for(Session, "do_orm_execute")
    def _filter(execute_state):
        if not execute_state.is_select:
            return
        ctx = get_ctx()
        options = []
        if not execute_state.execution_options.get("include_deleted", False):

            def deleted_crit(cls):
                if not hasattr(cls, "deleted"):
                    return true()
                return cls.deleted == 0

            options.append(with_loader_criteria(AuditBase, deleted_crit, include_aliases=True))
        skip_tenant = execute_state.execution_options.get("skip_tenant", False)
        if ctx and ctx.skip_tenant:
            skip_tenant = True
        if ctx and ctx.tenant_id is not None and not skip_tenant:
            tenant_id = ctx.tenant_id

            def tenant_crit(cls):
                if getattr(cls, "__platform__", False) or not hasattr(cls, "tenant_id"):
                    return true()
                return cls.tenant_id == tenant_id

            options.append(with_loader_criteria(AuditBase, tenant_crit, include_aliases=True))
            options.append(with_loader_criteria(AssocBase, tenant_crit, include_aliases=True))
        if options:
            execute_state.statement = execute_state.statement.options(*options)


@contextmanager
def session_scope(commit: bool = False):
    factory = _factory or sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    session = factory()
    token = _session.set(session)
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _session.reset(token)
        session.close()


def transactional(fn):
    def wrapper(*args, **kwargs):
        session = get_session()
        depth = session.info.get("tx_depth", 0)
        session.info["tx_depth"] = depth + 1
        try:
            result = fn(*args, **kwargs)
            if depth == 0:
                if session.info.get("tx_failed"):
                    session.rollback()
                else:
                    session.commit()
            return result
        except Exception:
            session.info["tx_failed"] = True
            if depth == 0:
                session.rollback()
            raise
        finally:
            session.info["tx_depth"] = depth
            if depth == 0:
                session.info["tx_failed"] = False

    wrapper.__wrapped__ = fn
    wrapper.__name__ = getattr(fn, "__name__", "transactional")
    return wrapper
