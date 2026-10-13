"""主链路配套房间。不重建替身表，避免冲掉 FW-H06 的 8 条场景。生产环境拒绝执行。"""
from __future__ import annotations

from sqlalchemy import text

from tools.football_stub.seed import COLUMNS, _row, _upsert_sql, _writer_engine, guard_env

EXTRAS = (
    _row(id=9001, live_name="[STUB] 主链路直播中", status=2, start_time="2026-10-01 10:00:00", end_time="2026-10-01 12:00:00", create_time="2026-10-01 09:00:00", viewer_count=12, like_count=3),
    _row(id=9002, live_name="[STUB] 主链路已结束", status=3, start_time="2026-10-01 13:00:00", end_time="2026-10-01 14:00:00", create_time="2026-10-01 12:30:00", viewer_count=4),
    _row(id=9003, live_name="[STUB] 主链路已删除", status=3, deleted=1, create_time="2026-10-02 09:00:00"),
    _row(id=9004, tenant_id=2, live_name="[STUB] 主链路他租户", status=2, create_time="2026-10-02 09:00:00", viewer_count=1),
    _row(id=9005, live_name="[STUB] 主链路空计数", status=2, create_time="2026-10-03 09:00:00", viewer_count=None, like_count=None, reserve_count=None),
)


def ensure(engine=None) -> int:
    guard_env()
    engine = engine or _writer_engine()
    statement = text(_upsert_sql())
    with engine.begin() as conn:
        for row in EXTRAS:
            if not str(row["live_name"]).startswith("[STUB]"):
                raise RuntimeError("桩数据名称必须以 [STUB] 开头")
            conn.execute(statement, {name: row.get(name) for name in COLUMNS})
    return len(EXTRAS)


if __name__ == "__main__":
    raise SystemExit(0 if ensure() else 2)
