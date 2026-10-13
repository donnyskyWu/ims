"""B9 直播造数。只在非生产环境执行，叠加已有账号与设备，不写密钥。"""
from __future__ import annotations

import os
import sys

from app.core.clock import now_naive
from app.core.context import system_context, use_context
from app.core.config import load_settings, set_settings
from app.db.session import init_engine, session_scope
from app.domains.live.alarm import ensure_rules


def main() -> int:
    if os.environ.get("IMS_ENV") == "prod":
        return 2
    settings = load_settings(os.environ.get("IMS_ENV") or "test")
    set_settings(settings)
    init_engine(settings)
    with session_scope(commit=True) as _session:
        with use_context(system_context(1)):
            ensure_rules()
    if os.environ.get("B9_BULK") == "1":
        _bulk()
    return 0


def _bulk() -> None:
    from app.domains.master.model import LiveSession

    with session_scope(commit=True) as session:
        with use_context(system_context(1)):
            have = session.query(LiveSession).count()
            missing = max(0, 10000 - int(have))
            now = now_naive()
            for index in range(missing):
                session.add(
                    LiveSession(
                        name=f"压测{index}",
                        status="ENABLED",
                        session_code=f"IMS{now:%Y%m%d}DYS{90000 + index:05d}",
                        platform="DOUYIN",
                        topic=f"压测场次{index}",
                        session_status="ENDED",
                        is_supplement=0,
                        football_sync_status="UNLINKED",
                    )
                )
            session.flush()


if __name__ == "__main__":
    sys.exit(main())
