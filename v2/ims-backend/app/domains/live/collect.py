"""平台消费模拟。取不到时返回 None，风控记「余额数据暂不可用」。"""
from __future__ import annotations

from decimal import Decimal

UNAVAILABLE: set[int] = set()
CONSUME: dict[int, Decimal] = {}


def consume_of(account_id: int) -> Decimal | None:
    if int(account_id) in UNAVAILABLE:
        return None
    return CONSUME.get(int(account_id), Decimal("0"))


def set_consume(account_id: int, yuan) -> None:
    CONSUME[int(account_id)] = Decimal(str(yuan))


def mark_unavailable(account_id: int) -> None:
    UNAVAILABLE.add(int(account_id))


def reset() -> None:
    UNAVAILABLE.clear()
    CONSUME.clear()
