import pytest

from retail_mcp.circuit_breaker import CircuitBreaker, CircuitState
from retail_mcp.errors import DependencyUnavailableError


async def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=60)

    async def fail() -> None:
        raise RuntimeError("dependency failed")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(fail)
    assert breaker.state == CircuitState.OPEN
    with pytest.raises(DependencyUnavailableError):
        await breaker.call(fail)


async def test_circuit_breaker_resets_after_success() -> None:
    breaker = CircuitBreaker(failure_threshold=2)

    async def succeed() -> str:
        return "ok"

    assert await breaker.call(succeed) == "ok"
    assert breaker.state == CircuitState.CLOSED

