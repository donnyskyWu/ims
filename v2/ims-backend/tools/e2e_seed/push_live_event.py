"""向直播中的场次推一条模拟采集事件。仅非生产环境。"""
from __future__ import annotations

import os
import sys

from app.core.config import load_settings, set_settings
from app.core.context import system_context, use_context
from app.db.session import init_engine, session_scope
from app.domains.live.alarm import accept
from app.domains.master.model import LiveSession


def push(session_code: str, metric: str, value: str | None = None) -> int:
    if os.environ.get("IMS_ENV") == "prod":
        return 2
    settings = load_settings(os.environ.get("IMS_ENV") or "test")
    set_settings(settings)
    init_engine(settings)
    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            row = session.query(LiveSession).filter(LiveSession.session_code == session_code).one_or_none()
            if row is None:
                return 1
            accept(row.id, metric, value=value, text=metric)
    return 0


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else ""
    metric = sys.argv[2] if len(sys.argv) > 2 else "VIEWER_DROP"
    value = sys.argv[3] if len(sys.argv) > 3 else "40"
    raise SystemExit(push(code, metric, value))
