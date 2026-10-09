"""Reset ims_test / ims_ops_test schema for pytest (single-connection DDL + lock)."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from sqlalchemy.exc import OperationalError

from app.core import Base, ensure_databases, engine
from app.main import seed
from app.ops_db import OpsBase, ops_engine

_DDL_LOCK = Path(__file__).resolve().parent / ".ims_test_ddl.lock"
_LOCK_WAIT_SEC = 180
_DDL_RETRIES = 5


def _acquire_ddl_lock() -> None:
    deadline = time.monotonic() + _LOCK_WAIT_SEC
    while time.monotonic() < deadline:
        try:
            fd = os.open(_DDL_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError:
            print("[schema] waiting for ddl lock…", flush=True)
            time.sleep(0.25)
    raise RuntimeError("ims_test DDL lock timeout; stop parallel pytest on ims_test")


def _release_ddl_lock() -> None:
    _DDL_LOCK.unlink(missing_ok=True)


def _run_ddl() -> None:
    from app import content_ai_models, ops_models  # noqa: F401

    stop = threading.Event()

    def _tick() -> None:
        while not stop.wait(5):
            print("[schema] ddl running…", flush=True)

    ticker = threading.Thread(target=_tick, daemon=True)
    ticker.start()
    try:
        _run_ddl_body()
    finally:
        stop.set()


def _run_ddl_body() -> None:
    ensure_databases()
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
    with ops_engine().begin() as conn:
        OpsBase.metadata.drop_all(bind=conn)
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
    with ops_engine().begin() as conn:
        OpsBase.metadata.create_all(bind=conn)
    seed()


def reset_ims_test_schema() -> None:  # noqa: D103
    print("[schema] reset start", flush=True)
    _acquire_ddl_lock()
    try:
        last: Exception | None = None
        for attempt in range(_DDL_RETRIES):
            try:
                _run_ddl()
                print("[schema] reset done", flush=True)
                return
            except OperationalError as exc:
                last = exc
                time.sleep(0.5 * (attempt + 1))
        if last is not None:
            raise last
    finally:
        _release_ddl_lock()
