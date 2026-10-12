"""Football live_room 只读。租户必须经映射，未映射则不查询。"""
from __future__ import annotations

from typing import NamedTuple

from app.core.config import get_settings
from app.integrations.base import open_select_engine
from app.integrations.football_live.schema_check import expected_columns, sensitive_columns

LIVE_DURATION_SQL = (
    "SELECT COUNT(*) AS cnt, COALESCE(SUM(TIMESTAMPDIFF(MINUTE, start_time, end_time)), 0) AS minutes "
    "FROM live_room WHERE author_id=? AND create_time BETWEEN ? AND ?"
)

_engines: dict[str, object] = {}
QUERIES: list[tuple[str, tuple]] = []


class LiveDuration(NamedTuple):
    count: int
    minutes: int


DISPLAY_MASK = "******"


def mask_sensitive(row: dict, settings) -> dict:
    """只读展示脱敏。表里仍是 seed 假数据，这里不回写。"""
    for name in sensitive_columns(settings):
        if name in row and row[name] not in (None, ""):
            row[name] = DISPLAY_MASK
    return row


def read_deleted(value) -> int:
    """deleted 的真实类型是 tinyint。整数值按 0/1 读取。"""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if raw == b"\x01":
            return 1
        if raw == b"\x00":
            return 0
        return 1 if raw[:1] == b"\x01" else 0
    if isinstance(value, int):
        return 1 if int(value) == 1 else 0
    raise TypeError("无法识别的删除标记")


def football_engine(settings=None):
    settings = settings or get_settings()
    url = settings.football_live.url()
    engine = _engines.get(url)
    if engine is None:
        engine = open_select_engine(url)
        _engines[url] = engine
    return engine


def _mark(sql: str, params: tuple) -> None:
    QUERIES.append((sql, tuple(params)))


def _fetch(sql: str, params: tuple, settings) -> list[dict]:
    _mark(sql, params)
    statement = sql.replace("?", "%s")
    engine = football_engine(settings)
    with engine.connect() as conn:
        result = conn.exec_driver_sql(statement, params)
        keys = list(result.keys())
        rows = []
        for rec in result.fetchall():
            rows.append({key: rec[index] for index, key in enumerate(keys)})
        return rows


def _rows(sql: str, params: tuple, settings, executor):
    if executor is not None:
        _mark(sql, params)
        raw = executor(sql, tuple(params))
        if raw is None:
            return []
        if isinstance(raw, dict):
            return [raw]
        if isinstance(raw, list):
            return raw
        return list(raw)
    return _fetch(sql, params, settings)


def _room_sql(settings) -> str:
    columns = list(expected_columns(settings).keys())
    selected = ", ".join(f"`{name}`" for name in columns)
    return f"SELECT {selected} FROM live_room WHERE id=? AND tenant_id=? AND deleted=0"


def get_room(ims_tenant_id, room_id, settings=None, executor=None):
    settings = settings or get_settings()
    tenant = settings.football_tenant_for(int(ims_tenant_id))
    if tenant is None:
        return None
    rows = _rows(_room_sql(settings), (room_id, tenant), settings, executor)
    if not rows:
        return None
    row = dict(rows[0])
    if row.get("deleted") is not None:
        row["deleted"] = read_deleted(row["deleted"])
        if row["deleted"] != 0:
            return None
    return mask_sensitive(row, settings)


def room_exists_for_bind(ims_tenant_id, room_id, settings=None, executor=None) -> bool:
    return get_room(ims_tenant_id, room_id, settings=settings, executor=executor) is not None


UNAVAILABLE = "UNAVAILABLE"


def football_row_or_unavailable(loader):
    """Football 超时或失败时返回不可用标记，不把异常抛给场次编辑。"""
    try:
        return loader()
    except Exception:
        return UNAVAILABLE


def merge_live_metrics(ims_snapshot: dict, football_row=None) -> dict:
    """IMS 快照始终返回。Football 不可用时只打标记，不抛给场次编辑。"""
    snapshot = dict(ims_snapshot or {})
    if football_row is UNAVAILABLE or football_row is None:
        snapshot["unavailable"] = True
        snapshot["hint"] = "暂不可用"
        return snapshot
    snapshot["unavailable"] = False
    snapshot["football"] = football_row
    return snapshot


def live_duration(author_id, start, end, settings=None, executor=None) -> LiveDuration:
    params = (author_id, start, end)
    if executor is not None:
        _mark(LIVE_DURATION_SQL, params)
        raw = executor(LIVE_DURATION_SQL, params)
        return LiveDuration(int(raw[0] or 0), int(raw[1] or 0))
    rows = _fetch(LIVE_DURATION_SQL, params, settings or get_settings())
    if not rows:
        return LiveDuration(0, 0)
    row = rows[0]
    count = row.get("cnt", row.get("COUNT(*)"))
    minutes = row.get("minutes")
    if count is None:
        count = next(iter(row.values()))
        minutes = list(row.values())[1]
    return LiveDuration(int(count or 0), int(minutes or 0))
