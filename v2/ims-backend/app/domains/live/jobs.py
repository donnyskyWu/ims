"""直播定时任务。由 services.jobs 导入后注册。"""
from __future__ import annotations

from app.services.jobs import job


@job("live_auto_end", "*/10 * * * *")
def live_auto_end():
    from app.domains.live.service import auto_end_due

    return auto_end_due()


@job("live_report_overdue", "*/30 * * * *")
def live_report_overdue():
    from app.domains.live.service import mark_overdue

    return mark_overdue()


@job("live_alarm_escalate", "* * * * *")
def live_alarm_escalate():
    from app.domains.live.alarm import escalate_due

    return escalate_due()


@job("live_football_sync_retry", "*/5 * * * *")
def live_football_sync_retry():
    from sqlalchemy import select

    from app.db.session import get_session
    from app.domains.live.service import sync_room
    from app.domains.master.model import LiveSession
    from app.domains.system.model import Outbox

    session = get_session()
    rows = list(session.scalars(select(Outbox).where(Outbox.topic == "live.football.sync", Outbox.status == "PENDING")))
    done = 0
    for row in rows:
        if int(row.retry_count or 0) >= 5:
            row.status = "FAILED"
            continue
        payload = row.payload or {}
        found = session.get(LiveSession, int(payload.get("sessionId") or 0))
        row.retry_count = int(row.retry_count or 0) + 1
        if found is None or not found.football_room_id:
            row.status = "FAILED"
            continue
        try:
            sync_room(found.session_code, {"force": True})
            row.status = "DONE"
            done += 1
        except Exception:
            if int(row.retry_count) >= 5:
                row.status = "FAILED"
    session.flush()
    return done
