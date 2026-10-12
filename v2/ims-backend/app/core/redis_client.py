"""Redis 与 dev 进程内回退。"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

import redis

from app.core.config import Settings, get_settings
from app.core.errors import BizError


class RedisDown(Exception):
    """测试注入的缓存不可用。"""


class MemoryRedis:
    """开发环境进程内替代，接口对齐测试所需命令。"""

    def __init__(self):
        self._data: dict[str, tuple[str, float | None]] = {}
        self._lock = threading.Lock()

    def _purge(self, key):
        item = self._data.get(key)
        if item and item[1] is not None and item[1] < time.time():
            self._data.pop(key, None)

    def ping(self):
        return True

    def get(self, key):
        with self._lock:
            self._purge(key)
            item = self._data.get(key)
            return None if item is None else item[0]

    def set(self, key, value, ex=None, px=None, nx=False):
        with self._lock:
            self._purge(key)
            if nx and key in self._data:
                return None
            ttl = None
            if ex:
                ttl = time.time() + int(ex)
            if px:
                ttl = time.time() + int(px) / 1000
            self._data[key] = (value if isinstance(value, str) else str(value), ttl)
            return True

    def delete(self, *keys):
        with self._lock:
            count = 0
            for key in keys:
                if key in self._data:
                    self._data.pop(key, None)
                    count += 1
            return count

    def incr(self, key):
        with self._lock:
            self._purge(key)
            current = int(self._data[key][0]) if key in self._data else 0
            ttl = self._data[key][1] if key in self._data else None
            current += 1
            self._data[key] = (str(current), ttl)
            return current

    def expire(self, key, seconds):
        with self._lock:
            if key not in self._data:
                return False
            self._data[key] = (self._data[key][0], time.time() + int(seconds))
            return True

    def ttl(self, key):
        with self._lock:
            self._purge(key)
            item = self._data.get(key)
            if not item or item[1] is None:
                return -1
            return max(0, int(item[1] - time.time()))

    def setnx(self, key, value):
        return bool(self.set(key, value, nx=True))

    def flushdb(self):
        with self._lock:
            self._data.clear()

    def getdel(self, key):
        with self._lock:
            self._purge(key)
            item = self._data.pop(key, None)
            return None if item is None else item[0]


_client: Any = None
_memory = MemoryRedis()


def configure_redis(settings: Settings, force_memory: bool = False):
    global _client
    if force_memory or settings.redis_memory:
        settings.redis_memory = True
        _client = _memory
        return _client
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=2,
    )
    try:
        client.ping()
    except redis.RedisError:
        if settings.env == "dev":
            settings.redis_memory = True
            _client = _memory
            return _client
        raise
    _client = client
    return client


def get_redis():
    global _client
    from app.core.fault import faults

    faults.raise_if("redis.down")
    if _client is None:
        try:
            configure_redis(get_settings())
        except redis.RedisError as exc:
            raise BizError(5002) from exc
    return _client


def reset_redis_client():
    global _client
    _client = None


def json_get(key, default=None):
    raw = get_redis().get(key)
    if raw is None:
        return default
    return json.loads(raw)


def json_set(key, value, ex=None):
    get_redis().set(key, json.dumps(value, ensure_ascii=False), ex=ex)
