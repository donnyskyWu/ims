"""系统时钟。库内 naive datetime 默认是 UTC（utcnow）；对外展示和日界按 Asia/Shanghai。

客户端传来的无时区日期/时间按北京时间理解，再折成 naive UTC 落库，避免筛选差一天。
已经是北京时间墙钟的字段（例如去掉时区后原样保存的会议时间、培训截止时间）用 civil=True。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))
UTC = timezone.utc


def as_shanghai(dt: datetime, *, civil: bool = False) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(BJ)
    if civil:
        return dt.replace(tzinfo=BJ)
    return dt.replace(tzinfo=UTC).astimezone(BJ)


def format_iso(dt: datetime | None, *, civil: bool = False) -> str:
    if dt is None:
        return ""
    return as_shanghai(dt, civil=civil).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def format_iso_or_none(dt: datetime | None, *, civil: bool = False) -> str | None:
    if dt is None:
        return None
    return format_iso(dt, civil=civil)


def format_display(dt: datetime | None, *, civil: bool = False) -> str:
    """页面统一格式：2026-10-20 00:00。"""
    if dt is None:
        return ""
    return as_shanghai(dt, civil=civil).strftime("%Y-%m-%d %H:%M")


def parse_to_utc_naive(value: str) -> datetime | None:
    """解析客户端时间。仅日期或无时区的时刻按北京时间，返回 naive UTC。"""
    text = (value or "").strip()
    if not text:
        return None
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        if len(text) == 10:
            parsed = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=BJ)
        else:
            parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BJ)
    return parsed.astimezone(UTC).replace(tzinfo=None)


def civil_day_bounds(start_day: str, end_day: str) -> tuple[datetime, datetime] | None:
    """北京日历日（含首尾）对应的 naive UTC 闭区间，用来筛 UTC 时间列。"""
    try:
        start = datetime.strptime(start_day, "%Y-%m-%d").replace(tzinfo=BJ)
        end = datetime.strptime(end_day, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=BJ)
    except ValueError:
        return None
    if start > end:
        return None
    return (
        start.astimezone(UTC).replace(tzinfo=None),
        end.astimezone(UTC).replace(tzinfo=None),
    )
