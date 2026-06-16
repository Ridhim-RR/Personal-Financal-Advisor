"""Redis cache service for market data, session store, and rate limiting."""

import json
import os
from typing import Optional, Any

import redis


class CacheService:
    """Thin wrapper around Redis for caching market data and sessions.

    Falls back to a no-op in-memory cache if Redis is unavailable.
    """

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._local: dict[str, Any] = {}
        self._enabled = False
        url = os.getenv("REDIS_URL", "")
        if url:
            try:
                self._client = redis.from_url(url, decode_responses=True, socket_timeout=2)
                self._client.ping()
                self._enabled = True
            except Exception:
                self._client = None

    def get(self, key: str) -> Optional[Any]:
        if self._enabled and self._client:
            val = self._client.get(key)
            if val:
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return val
        return self._local.get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        encoded = json.dumps(value) if not isinstance(value, str) else value
        if self._enabled and self._client:
            self._client.setex(key, ttl, encoded)
        else:
            self._local[key] = value

    def delete(self, key: str) -> None:
        if self._enabled and self._client:
            self._client.delete(key)
        self._local.pop(key, None)

    def flush(self) -> None:
        if self._enabled and self._client:
            self._client.flushdb()
        self._local.clear()


cache = CacheService()
