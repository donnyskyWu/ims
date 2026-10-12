"""行对象转 camelCase 字典，时间按北京时间输出。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.core.clock import format_datetime
from app.core.serialize import ser_money


def camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def dump_row(obj, fields: list[str] | None = None) -> dict:
    names = fields or [col.name for col in obj.__table__.columns]
    data = {}
    for name in names:
        value = getattr(obj, name)
        if isinstance(value, datetime):
            value = format_datetime(value)
        elif isinstance(value, date):
            value = value.strftime("%Y-%m-%d")
        elif isinstance(value, Decimal):
            value = ser_money(value)
        data[camel(name)] = value
    return data
