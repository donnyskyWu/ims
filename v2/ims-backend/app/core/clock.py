"""可注入的北京时间源。"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
_frozen: datetime | None = None


def now() -> datetime:
    if _frozen is not None:
        if _frozen.tzinfo is None:
            return _frozen.replace(tzinfo=SHANGHAI)
        return _frozen.astimezone(SHANGHAI)
    return datetime.now(SHANGHAI)


def now_naive() -> datetime:
    return now().replace(tzinfo=None)


def today():
    return now().date()


def freeze(value: datetime | None) -> None:
    global _frozen
    _frozen = value


def unfreeze() -> None:
    freeze(None)


@contextmanager
def frozen_at(value: datetime):
    prev = _frozen
    freeze(value)
    try:
        yield
    finally:
        freeze(prev)


def parse_input_datetime(raw: str) -> datetime:
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        if "T" in text or "+" in text or text.endswith("Z"):
            dt = datetime.fromisoformat(text)
        else:
            dt = datetime.fromisoformat(text.replace(" ", "T"))
    except ValueError as exc:
        raise ValueError("时间格式不正确") from exc
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(SHANGHAI).replace(tzinfo=None)


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        aware = value.replace(tzinfo=SHANGHAI)
    else:
        aware = value.astimezone(SHANGHAI)
    return aware.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def advance(delta: timedelta) -> datetime:
    freeze(now() + delta)
    return now()
