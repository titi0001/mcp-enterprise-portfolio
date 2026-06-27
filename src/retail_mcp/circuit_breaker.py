"""Small asynchronous circuit breaker for dependency isolation."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

from retail_mcp.errors import DependencyUnavailableError

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at = 0.0
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.monotonic() - self.opened_at < self.recovery_seconds:
                    raise DependencyUnavailableError(
                        "A required service is temporarily unavailable"
                    )
                self.state = CircuitState.HALF_OPEN
        try:
            result = await operation()
        except Exception:
            async with self._lock:
                self.failures += 1
                if self.failures >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    self.opened_at = time.monotonic()
            raise
        async with self._lock:
            self.failures = 0
            self.state = CircuitState.CLOSED
        return result
