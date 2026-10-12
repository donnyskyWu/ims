"""定时任务注册、分布式锁与执行记录。"""
from __future__ import annotations

import threading
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.clock import now_naive
from app.core.context import get_ctx, system_context, use_context
from app.core.errors import BizError
from app.core.redis_client import get_redis
from app.db.session import get_session
from app.domains.system.model import JobLog, LoginLog, OperateLog

JOBS: list = []
LOCK_TTL = 30
WATCH_INTERVAL = 10
watch_state = {"extends": 0}


class JobSpec:
    def __init__(self, name: str, cron: str, fn):
        self.name = name
        self.cron = cron
        self.fn = fn

    def __getitem__(self, item):
        return getattr(self, item)


def job(name: str, cron: str):
    def deco(fn):
        if not any(item.name == name for item in JOBS):
            JOBS.append(JobSpec(name, cron, fn))
        fn.job_name = name
        fn.cron = cron
        return fn

    return deco


def run_job(name: str, trigger: str = "SCHEDULE") -> dict:
    ctx = get_ctx()
    if ctx is None:
        with use_context(system_context(1)):
            return _run(name, trigger)
    return _run(name, trigger)


def _run(name: str, trigger: str) -> dict:
    spec = _find(name)
    redis = get_redis()
    key = f"ims:job:lock:{name}"
    token = uuid.uuid4().hex
    locked = redis.set(key, token, nx=True, ex=int(LOCK_TTL))
    if not locked:
        return {"skipped": True, "success": False, "message": "已在其他实例执行"}
    stop = threading.Event()
    thread = threading.Thread(target=_watch, args=(stop, redis, key, token), name=f"job-watch-{name}", daemon=True)
    thread.start()
    started = now_naive()
    try:
        spec.fn()
    except Exception as exc:
        _failure(name, trigger, started, exc)
        return {"skipped": False, "success": False, "message": str(exc)}
    else:
        _success(name, trigger, started)
        return {"skipped": False, "success": True, "message": "完成"}
    finally:
        stop.set()
        thread.join(timeout=1)
        current = redis.get(key)
        if current == token:
            redis.delete(key)


def _watch(stop: threading.Event, redis, key: str, token: str) -> None:
    while True:
        interval = max(0.01, float(WATCH_INTERVAL))
        if stop.wait(interval):
            return
        _extend_lock(redis, key, token, LOCK_TTL)


def _extend_lock(redis, key: str, token: str, ttl: int) -> bool:
    current = redis.get(key)
    if current != token:
        return False
    redis.expire(key, int(ttl))
    watch_state["extends"] = int(watch_state.get("extends") or 0) + 1
    return True


def _find(name: str) -> JobSpec:
    for item in JOBS:
        if item.name == name:
            return item
    raise BizError(1001, "未知的任务")


def _success(name: str, trigger: str, started) -> None:
    get_session().add(
        JobLog(
            job_name=name,
            trigger_mode=trigger,
            started_at=started,
            finished_at=now_naive(),
            success=1,
            error_digest=None,
        )
    )
    get_session().flush()


def _failure(name: str, trigger: str, started, exc: Exception) -> None:
    session = get_session()
    session.rollback()
    session.add(
        JobLog(
            job_name=name,
            trigger_mode=trigger,
            started_at=started,
            finished_at=now_naive(),
            success=0,
            error_digest=str(exc)[:500],
        )
    )
    session.flush()
    try:
        _alert(name)
    except Exception:
        pass


def _alert(name: str) -> None:
    from app.domains.message.service import send_notify
    from app.domains.todo.service import users_with_perm

    holders = users_with_perm("ims:system:job:run") or [1]
    for user_id in holders:
        send_notify(user_id, "任务执行失败", f"定时任务 {name} 执行失败", "JOB_FAIL", f"{name}:{uuid.uuid4().hex}")


@job("integrity", "0 3 * * *")
def integrity():
    return {"issues": 0}


@job("org_reconcile", "0 2 * * *")
def org_reconcile():
    return {"ok": True}


@job("file_cleanup", "0 4 * * *")
def file_cleanup():
    from app.domains.file.service import cleanup_expired

    return cleanup_expired()


@job("log_cleanup", "30 4 * * *")
def log_cleanup():
    cutoff = now_naive() - timedelta(days=180)
    session = get_session()
    removed = 0
    for model in (OperateLog, LoginLog):
        rows = list(session.scalars(select(model).where(model.create_time < cutoff).execution_options(skip_tenant=True)))
        for row in rows:
            row.deleted = row.id
            removed += 1
    if removed:
        session.flush()
    return removed


@job("flow_overdue", "*/10 * * * *")
def flow_overdue():
    from app.domains.flow.service import scan_overdue

    return scan_overdue()


@job("attendance_pull", "30 1 * * *")
def attendance_pull():
    return {"pulled": 0}


@job("outbox_retry", "*/5 * * * *")
def outbox_retry():
    return {"retried": 0}


@job("notify_retry", "*/5 * * * *")
def notify_retry():
    from app.domains.message.service import retry_pending

    return retry_pending()


@job("org_event_retry", "*/5 * * * *")
def org_event_retry():
    return {"retried": 0}


@job("export_retry", "*/10 * * * *")
def export_retry():
    return {"retried": 0}


@job("position_role_revoke", "*/10 * * * *")
def position_role_revoke():
    from app.services.position import revoke_expired

    return revoke_expired()
