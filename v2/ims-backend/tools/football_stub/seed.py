"""Football live_room 桩。IMS_ENV=prod 时创建和灌数都退出 2。

建表语句与 shenyu-live 原文一致，写在 create.sql。本脚本只连本地替身库，
写账号是 ims_football，不是只读账号，也不是 shenyu 高权限账号。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

# 不存在的房间。测试用这个常量，不往表里插。
MISSING_ROOM_ID = 9199
FAKE_BIND_PASSWORD = "stub-bind-pwd"
FAKE_LOGIN_PASSWORD = "stub-login-pwd"

COLUMNS = (
    "id",
    "author_id",
    "nickname",
    "avatar_url",
    "live_id",
    "live_name",
    "cover",
    "status",
    "live_mode",
    "screen_type",
    "watch_type",
    "enable_playback",
    "enable_low_latency",
    "enable_heat",
    "enable_completion",
    "start_time",
    "end_time",
    "view_url",
    "playback_url",
    "server_url",
    "tenant_id",
    "create_time",
    "update_time",
    "creator",
    "deleted",
    "bind_mobile",
    "bind_mobile_password",
    "reserve_count",
    "like_count",
    "virtual_like_count",
    "viewer_count",
    "login_pwd",
)


def _row(**overrides):
    row = {
        "author_id": 501,
        "nickname": "stub",
        "avatar_url": "http://127.0.0.1/avatar/stub",
        "cover": "",
        "status": 1,
        "live_mode": 1,
        "screen_type": 1,
        "watch_type": 1,
        "enable_playback": 0,
        "enable_low_latency": 0,
        "enable_heat": 0,
        "enable_completion": 0,
        "start_time": None,
        "end_time": None,
        "view_url": None,
        "playback_url": None,
        "server_url": None,
        "tenant_id": 1,
        "update_time": None,
        "creator": "stub",
        "deleted": 0,
        "bind_mobile": "13800000000",
        "bind_mobile_password": FAKE_BIND_PASSWORD,
        "reserve_count": 0,
        "like_count": 0,
        "virtual_like_count": 0,
        "viewer_count": 0,
        "login_pwd": FAKE_LOGIN_PASSWORD,
    }
    row.update(overrides)
    row["live_id"] = f"stub-{row['id']}"
    return row


# 八类：五种状态、已删除、他租户、零时长。同日多场是 9101+9102，跨天是 9105。
SCENARIOS = [
    _row(
        id=9101,
        live_name="[STUB] 直播中",
        status=2,
        screen_type=1,
        watch_type=1,
        start_time="2026-01-02 10:00:00",
        end_time="2026-01-02 11:30:00",
        view_url="http://127.0.0.1/watch/9101",
        server_url="http://127.0.0.1/push/9101",
        create_time="2026-01-02 09:00:00",
        like_count=1,
        viewer_count=10,
    ),
    _row(
        id=9102,
        live_name="[STUB] 已结束",
        status=3,
        enable_playback=1,
        start_time="2026-01-02 12:00:00",
        end_time="2026-01-02 13:30:00",
        playback_url="http://127.0.0.1/replay/9102",
        create_time="2026-01-02 11:00:00",
        viewer_count=3,
    ),
    _row(
        id=9103,
        live_name="[STUB] 已删除",
        status=3,
        screen_type=2,
        start_time="2026-01-03 12:00:00",
        end_time="2026-01-03 13:00:00",
        create_time="2026-01-03 11:00:00",
        deleted=1,
    ),
    _row(
        id=9104,
        live_name="[STUB] 未开始",
        status=1,
        create_time="2026-01-04 09:00:00",
    ),
    _row(
        id=9105,
        author_id=502,
        live_name="[STUB] 暂停",
        status=5,
        enable_playback=1,
        start_time="2026-01-05 23:00:00",
        end_time="2026-01-06 00:30:00",
        playback_url="http://127.0.0.1/replay/9105",
        create_time="2026-01-05 09:30:00",
        viewer_count=8,
        like_count=2,
    ),
    _row(
        id=9106,
        author_id=502,
        live_name="[STUB] 过期",
        status=4,
        watch_type=2,
        create_time="2026-01-06 09:00:00",
        reserve_count=4,
    ),
    _row(
        id=9107,
        author_id=503,
        tenant_id=2,
        live_name="[STUB] 他租户",
        status=2,
        start_time="2026-01-07 10:00:00",
        end_time="2026-01-07 10:10:00",
        create_time="2026-01-07 09:00:00",
        viewer_count=1,
    ),
    _row(
        id=9108,
        live_name="[STUB] 零时长",
        status=3,
        start_time="2026-01-08 10:00:00",
        end_time="2026-01-08 10:00:00",
        create_time="2026-01-08 09:00:00",
        reserve_count=None,
        like_count=None,
        viewer_count=None,
    ),
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
        conn.execute(text("DROP TABLE IF EXISTS live_room"))
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
            conn.execute(statement, {name: row.get(name) for name in COLUMNS})
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
