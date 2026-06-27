"""Cache abstractions with local and Redis implementations."""

import asyncio
import json
import time
from typing import Any, Protocol


class Cache(Protocol):
    async def get(self, key: str) -> dict[str, Any] | None: ...

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def close(self) -> None: ...


class MemoryCache:
    def __init__(self) -> None:
        self._values: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        async with self._lock:
            item = self._values.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at <= time.monotonic():
                self._values.pop(key, None)
                return None
            return value.copy()

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        async with self._lock:
            self._values[key] = (time.monotonic() + ttl_seconds, value.copy())

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._values.pop(key, None)

    async def close(self) -> None:
        self._values.clear()


class RedisCache:
    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def get(self, key: str) -> dict[str, Any] | None:
        raw = await self._redis.get(key)
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        await self._redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.aclose()
