"""编号生成。Redis 优先，库表行锁兜底，恢复后取较大值续号。"""
from __future__ import annotations

import threading
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.clock import now_naive
from app.core.errors import BizError
from app.core.events import events
from app.core.redis_client import get_redis
from app.db.session import get_session
from app.domains.system.model import Sequence

PLATFORM_EXT = {
    "DOUYIN": "DYS",
    "KUAISHOU": "KSH",
    "WECHAT_CHANNELS": "WXS",
    "XIAOHONGSHU": "XHS",
    "WECHAT_MP": "GZH",
    "OTHER": "OTH",
}
TTL = 48 * 3600
# 同一进程内串行分配。100 路并发打到同一 Redis 连接时，INCR 已在服务端生效但客户端超时，
# 再走库表兜底会发出重复号。
_ALLOC_LOCK = threading.Lock()


def _date(when: datetime | None) -> str:
    return (when or now_naive()).strftime("%Y%m%d")


def _db_get(rule: str, day: str, group: str) -> Sequence | None:
    return get_session().scalar(
        select(Sequence).where(Sequence.rule_name == rule, Sequence.seq_date == day, Sequence.group_key == group).with_for_update()
    )


def _db_put(rule: str, day: str, group: str, value: int) -> int:
    session = get_session()
    row = _db_get(rule, day, group)
    if row is None:
        row = Sequence(rule_name=rule, seq_date=day, group_key=group, current_value=value)
        session.add(row)
    elif int(row.current_value) < value:
        row.current_value = value
    session.flush()
    return int(row.current_value)


def _db_incr(rule: str, day: str, group: str) -> int:
    session = get_session()
    row = _db_get(rule, day, group)
    if row is None:
        row = Sequence(rule_name=rule, seq_date=day, group_key=group, current_value=1)
        session.add(row)
        session.flush()
        return 1
    row.current_value = int(row.current_value) + 1
    session.flush()
    return int(row.current_value)


def _save_allocated(rule: str, day: str, group: str, value: int) -> None:
    """把已分配序号写入序列表。插入竞争时重试，不改已分配的号。"""
    for _ in range(5):
        try:
            _db_put(rule, day, group, value)
            return
        except IntegrityError:
            get_session().rollback()
    _db_put(rule, day, group, value)


def next_value(rule: str, group: str = "", when: datetime | None = None) -> int:
    day = _date(when)
    key = f"ims:seq:{rule}:{day}:{group}"
    allocated: int | None = None
    try:
        from app.core.fault import faults

        faults.raise_if("redis.seq")
        with _ALLOC_LOCK:
            redis = get_redis()
            # 键不存在时用库中已发最大值播种，恢复后从较大值续号；并发时序号只来自 INCR。
            if redis.get(key) is None:
                stored = _db_get(rule, day, group)
                base = int(stored.current_value) if stored is not None else 0
                redis.set(key, str(base), nx=True, ex=TTL)
            allocated = int(redis.incr(key))
            try:
                redis.expire(key, TTL)
            except Exception:
                pass
            _save_allocated(rule, day, group, allocated)
        return allocated
    except BizError:
        raise
    except Exception:
        # Redis 已经发出的号必须原样返回，不能再 _db_incr，否则与已发出的号重复。
        if allocated is not None:
            return allocated
        try:
            get_session().rollback()
        except Exception:
            pass
        return _db_incr(rule, day, group)


def format_code(prefix: str, when: datetime | None = None, width: int = 4, group: str = "") -> str:
    day = _date(when)
    value = next_value(prefix, group, when)
    return f"{prefix}{day}{value:0{width}d}"


def session_code(platform: str, when: datetime | None = None) -> str:
    ext = PLATFORM_EXT.get(platform)
    if not ext:
        raise BizError(1503, data={"fieldErrors": [{"field": "platform", "message": "平台不存在"}]})
    day = _date(when)
    value = next_value("SESSION", ext, when)
    width = 4 if value <= 9999 else 5
    if value == 10000:
        events.publish("seq.p2", {"platform": platform, "date": day, "value": value})
    return f"IMS{day}{ext}{value:0{width}d}"
