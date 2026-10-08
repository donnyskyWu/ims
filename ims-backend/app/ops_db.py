import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core import server_url


class OpsBase(DeclarativeBase):
    pass


_engines: dict = {}
_sessions: dict = {}
_schema_ready: set[str] = set()


def ops_db_name() -> str:
    return os.environ.get("IMS_OPS_DB", "opsbiz")


def ops_engine():
    name = ops_db_name()
    cached = _engines.get(name)
    if cached is not None:
        return cached
    server = create_engine(server_url(), pool_pre_ping=True)
    with server.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4"))
    server.dispose()
    engine = create_engine(server_url(name), pool_pre_ping=True)
    _engines[name] = engine
    _sessions[name] = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    if name not in _schema_ready:
        from app import ops_models  # noqa: F401

        OpsBase.metadata.create_all(engine)
        _schema_ready.add(name)
    return engine


def ops_session():
    ops_engine()
    return _sessions[ops_db_name()]()


def ensure_ops() -> None:
    ops_engine()
