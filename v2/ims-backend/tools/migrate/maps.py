"""历史租户到 IMS 租户的映射。skip 不是错误。"""
from __future__ import annotations

from decimal import Decimal

FOOTBALL_SKIP = {2, 3, 4, 121, 122}


def _as_int(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, (float, Decimal)):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def map_tenant(system, value) -> tuple[str, int | None]:
    name = str(system or "").strip().lower()
    number = _as_int(value)
    if name in {"legacy_ims", "opsbiz"}:
        if number == 0:
            return ("ok", 1)
        return ("pending", None)
    if name == "football":
        if number == 1:
            return ("ok", 1)
        if number in FOOTBALL_SKIP:
            return ("skip", None)
        return ("pending", None)
    if name == "ai_platform":
        if value is None or number == 1:
            return ("ok", 1)
        return ("pending", None)
    return ("pending", None)
