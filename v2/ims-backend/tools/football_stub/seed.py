"""Football live_room 桩。IMS_ENV=prod 时创建和灌数都退出 2。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

COLUMNS = (
    "id",
    "tenant_id",
    "author_id",
    "nickname",
    "avatar",
    "live_id",
    "live_name",
    "cover",
    "status",
    "start_time",
    "end_time",
    "screen_mode",
    "access_mode",
    "watch_url",
    "replay_url",
    "push_url",
    "viewer_count",
    "like_count",
    "reserve_count",
    "deleted",
    "create_time",
)

# 八类场景。名称一律以 [STUB] 开头。时长按分钟可复核。
SCENARIOS = [
    {
        "id": 9101,
        "tenant_id": 1,
        "author_id": 501,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9101",
        "live_name": "[STUB] 进行中",
        "cover": "",
        "status": 1,
        "start_time": "2026-01-02 10:00:00",
        "end_time": "2026-01-02 11:30:00",
        "screen_mode": "H",
        "access_mode": "PUBLIC",
        "watch_url": "http://127.0.0.1/watch/9101",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 10,
        "like_count": 1,
        "reserve_count": 0,
        "deleted": 0,
        "create_time": "2026-01-02 09:00:00",
    },
    {
        "id": 9102,
        "tenant_id": 1,
        "author_id": 501,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9102",
        "live_name": "[STUB] 已结束",
        "cover": "",
        "status": 2,
        "start_time": "2026-01-02 12:00:00",
        "end_time": "2026-01-02 13:30:00",
        "screen_mode": "H",
        "access_mode": "PUBLIC",
        "watch_url": "",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 3,
        "like_count": 0,
        "reserve_count": 0,
        "deleted": 0,
        "create_time": "2026-01-02 11:00:00",
    },
    {
        "id": 9103,
        "tenant_id": 1,
        "author_id": 501,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9103",
        "live_name": "[STUB] 已删除",
        "cover": "",
        "status": 2,
        "start_time": "2026-01-03 12:00:00",
        "end_time": "2026-01-03 13:00:00",
        "screen_mode": "V",
        "access_mode": "PUBLIC",
        "watch_url": "",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 0,
        "like_count": 0,
        "reserve_count": 0,
        "deleted": 1,
        "create_time": "2026-01-03 11:00:00",
    },
    {
        "id": 9104,
        "tenant_id": 1,
        "author_id": 501,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9104",
        "live_name": "[STUB] 未开始",
        "cover": "",
        "status": 0,
        "start_time": None,
        "end_time": None,
        "screen_mode": "H",
        "access_mode": "PUBLIC",
        "watch_url": "",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 0,
        "like_count": 0,
        "reserve_count": 0,
        "deleted": 0,
        "create_time": "2026-01-04 09:00:00",
    },
    {
        "id": 9105,
        "tenant_id": 1,
        "author_id": 502,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9105",
        "live_name": "[STUB] 回放可看",
        "cover": "",
        "status": 2,
        "start_time": "2026-01-05 10:00:00",
        "end_time": "2026-01-05 10:30:00",
        "screen_mode": "H",
        "access_mode": "PUBLIC",
        "watch_url": "",
        "replay_url": "http://127.0.0.1/replay/9105",
        "push_url": "",
        "viewer_count": 8,
        "like_count": 2,
        "reserve_count": 0,
        "deleted": 0,
        "create_time": "2026-01-05 09:30:00",
    },
    {
        "id": 9106,
        "tenant_id": 1,
        "author_id": 502,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9106",
        "live_name": "[STUB] 预约中",
        "cover": "",
        "status": 0,
        "start_time": None,
        "end_time": None,
        "screen_mode": "H",
        "access_mode": "TICKET",
        "watch_url": "",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 0,
        "like_count": 0,
        "reserve_count": 4,
        "deleted": 0,
        "create_time": "2026-01-06 09:00:00",
    },
    {
        "id": 9107,
        "tenant_id": 2,
        "author_id": 503,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9107",
        "live_name": "[STUB] 其他租户",
        "cover": "",
        "status": 1,
        "start_time": "2026-01-07 10:00:00",
        "end_time": "2026-01-07 10:10:00",
        "screen_mode": "H",
        "access_mode": "PUBLIC",
        "watch_url": "",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 1,
        "like_count": 0,
        "reserve_count": 0,
        "deleted": 0,
        "create_time": "2026-01-07 09:00:00",
    },
    {
        "id": 9108,
        "tenant_id": 1,
        "author_id": 501,
        "nickname": "stub",
        "avatar": "",
        "live_id": "stub-9108",
        "live_name": "[STUB] 零时长",
        "cover": "",
        "status": 2,
        "start_time": "2026-01-08 10:00:00",
        "end_time": "2026-01-08 10:00:00",
        "screen_mode": "H",
        "access_mode": "PUBLIC",
        "watch_url": "",
        "replay_url": "",
        "push_url": "",
        "viewer_count": 0,
        "like_count": 0,
        "reserve_count": 0,
        "deleted": 0,
        "create_time": "2026-01-08 09:00:00",
    },
]


def guard_env() -> None:
    if os.environ.get("IMS_ENV") == "prod":
        raise SystemExit(2)


def _statements(sql: str) -> list[str]:
    kept = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        kept.append(line)
    parts = []
    for part in "\n".join(kept).split(";"):
        if part.strip():
            parts.append(part.strip())
    return parts


def _writer_engine():
    guard_env()
    from app.core.config import load_settings

    env = os.environ.get("IMS_ENV") or "dev"
    settings = load_settings(env)
    fb = settings.football_live
    user = os.environ.get("IMS_FOOTBALL_ADMIN_USER", "ims_football")
    password = quote_plus(os.environ.get("IMS_FOOTBALL_ADMIN_PASSWORD", "ims"))
    url = f"mysql+pymysql://{user}:{password}@{fb.host}:{fb.port}/{fb.name}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, future=True)


def create_schema(engine=None) -> None:
    guard_env()
    engine = engine or _writer_engine()
    sql = (Path(__file__).with_name("create.sql")).read_text(encoding="utf-8")
    with engine.begin() as conn:
        for statement in _statements(sql):
            conn.execute(text(statement))


def _upsert_sql() -> str:
    cols = ", ".join(f"`{name}`" for name in COLUMNS)
    holders = ", ".join(f":{name}" for name in COLUMNS)
    updates = ", ".join(f"`{name}`=VALUES(`{name}`)" for name in COLUMNS if name != "id")
    return f"INSERT INTO live_room ({cols}) VALUES ({holders}) ON DUPLICATE KEY UPDATE {updates}"


def seed(engine=None) -> int:
    guard_env()
    engine = engine or _writer_engine()
    create_schema(engine)
    statement = text(_upsert_sql())
    with engine.begin() as conn:
        for row in SCENARIOS:
            if not str(row["live_name"]).startswith("[STUB]"):
                raise RuntimeError("桩数据名称必须以 [STUB] 开头")
            conn.execute(statement, row)
    return len(SCENARIOS)


def main(argv=None) -> int:
    guard_env()
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["create"]:
        create_schema()
        return 0
    seed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
