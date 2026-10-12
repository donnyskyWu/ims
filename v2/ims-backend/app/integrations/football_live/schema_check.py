"""Football live_room 结构校验。缺列或类型不同即报出，多出的列忽略。"""
from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy import create_engine, text

from app.core.config import ROOT, Settings

# MySQL 8 不保留整型显示宽度。精度用来区分 bigint(20) / int(11) / tinyint(4)，并拒绝 bit。
_INTEGER = {
    "bigint(20)": ("bigint", 19),
    "tinyint(4)": ("tinyint", 3),
    "int(11)": ("int", 10),
}


def schema_document(settings: Settings) -> dict:
    path = Path(settings.football_live.schema_file)
    if not path.is_absolute():
        path = ROOT / path
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def expected_columns(settings: Settings) -> dict[str, str]:
    data = schema_document(settings)
    return {name: str(kind).lower().replace(" ", "") for name, kind in (data.get("columns") or {}).items()}


def sensitive_columns(settings: Settings) -> tuple[str, ...]:
    data = schema_document(settings)
    return tuple(str(name) for name in (data.get("sensitive") or ()))


def type_matches(expected: str, data_type: str, column_type: str, numeric_precision) -> bool:
    expected = str(expected or "").lower().replace(" ", "")
    data_type = str(data_type or "").lower()
    column_type = str(column_type or "").lower()
    if "unsigned" in column_type and "unsigned" not in expected:
        return False
    if expected in _INTEGER:
        base, precision = _INTEGER[expected]
        if data_type != base:
            return False
        if numeric_precision is None:
            return False
        return int(numeric_precision) == precision
    reported = column_type.split()[0]
    if expected.startswith("varchar("):
        return reported == expected
    return data_type == expected or reported == expected


def check_schema(settings: Settings) -> list[str]:
    expected = expected_columns(settings)
    defaults = {name: str(value) for name, value in (schema_document(settings).get("defaults") or {}).items()}
    try:
        engine = create_engine(settings.football_live.url(), pool_pre_ping=True)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, NUMERIC_PRECISION, COLUMN_DEFAULT "
                    "FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'live_room'"
                ),
                {"db": settings.football_live.name},
            ).all()
    except Exception as exc:
        return [f"无法读取 live_room 结构: {exc.__class__.__name__}"]
    actual = {row[0]: row for row in rows}
    if not actual:
        return ["live_room 不存在"]
    problems = []
    for name, kind in expected.items():
        row = actual.get(name)
        if row is None:
            problems.append(f"缺少列 {name}")
            continue
        if not type_matches(kind, row[1], row[2], row[3]):
            problems.append(f"列 {name} 类型不一致，期望 {kind} 实际 {row[2]}")
        if name in defaults:
            got = "" if row[4] is None else str(row[4])
            if got != defaults[name]:
                problems.append(f"列 {name} 默认值不一致，期望 {defaults[name]} 实际 {got or '空'}")
    return problems
