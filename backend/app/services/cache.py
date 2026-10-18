"""Redis-backed cache and rate limiter with an automatic in-memory fallback.

If Redis is unreachable (or REDIS_URL is empty) the app keeps working: it
silently falls back to a per-process dictionary. Nothing in the app depends
on Redis for correctness, only for speed and shared rate limits.
"""

import json
import logging
import threading
import time
from typing import Any

import redis

log = logging.getLogger(__name__)


class Cache:
    def __init__(self, url: str = "") -> None:
        self._redis: redis.Redis | None = None
        self._mem: dict[str, tuple[float, str]] = {}
        self._counters: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

        if url:
            try:
                client = redis.Redis.from_url(
                    url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
                )
                client.ping()
                self._redis = client
                log.info("Cache backend: redis")
            except Exception as exc:  # noqa: BLE001 - any failure -> memory fallback
                log.warning("Redis unavailable (%s); using in-memory cache", exc)

    # -- introspection -------------------------------------------------
    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "memory"

    def ping(self) -> bool:
        if self._redis is None:
            return True
        try:
            return bool(self._redis.ping())
        except Exception:  # noqa: BLE001
            return False

    def clear_memory(self) -> None:
        with self._lock:
            self._mem.clear()
            self._counters.clear()

    # -- JSON values ---------------------------------------------------
    def get_json(self, key: str) -> Any | None:
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                return json.loads(raw) if raw else None
            except Exception as exc:  # noqa: BLE001
                log.warning("Redis get failed: %s", exc)
        with self._lock:
            item = self._mem.get(key)
            if not item:
                return None
            expires, raw = item
            if expires < time.time():
                self._mem.pop(key, None)
                return None
            return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl: int) -> None:
        raw = json.dumps(value, ensure_ascii=False, default=str)
        if self._redis is not None:
            try:
                self._redis.set(key, raw, ex=ttl)
                return
            except Exception as exc:  # noqa: BLE001
                log.warning("Redis set failed: %s", exc)
        with self._lock:
            self._mem[key] = (time.time() + ttl, raw)

    def delete(self, *keys: str) -> None:
        if not keys:
            return
        if self._redis is not None:
            try:
                self._redis.delete(*keys)
            except Exception as exc:  # noqa: BLE001
                log.warning("Redis delete failed: %s", exc)
        with self._lock:
            for k in keys:
                self._mem.pop(k, None)

    # -- rate limiting -------------------------------------------------
    def hit(self, key: str, window_seconds: int = 60) -> int:
        """Fixed-window counter. Returns the number of hits in the current window."""
        if self._redis is not None:
            try:
                count = int(self._redis.incr(key))
                if count == 1:
                    self._redis.expire(key, window_seconds)
                return count
            except Exception as exc:  # noqa: BLE001
                log.warning("Redis incr failed: %s", exc)
        now = time.time()
        with self._lock:
            expires, count = self._counters.get(key, (0.0, 0))
            if expires < now:
                expires, count = now + window_seconds, 0
            count += 1
            self._counters[key] = (expires, count)
            return count
