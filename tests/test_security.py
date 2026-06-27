import pytest

from retail_mcp.config import APIKeyDefinition
from retail_mcp.errors import AuthenticationError, AuthorizationError, RateLimitError
from retail_mcp.security import (
    AuthenticationManager,
    Permission,
    Role,
    TokenBucketRateLimiter,
)


def test_authentication_resolves_principal() -> None:
    manager = AuthenticationManager(
        [APIKeyDefinition(key="a-secure-test-key", subject="alice", role="customer_service")]
    )
    principal = manager.authenticate("a-secure-test-key")
    assert principal.subject == "alice"
    assert principal.role == Role.CUSTOMER_SERVICE


@pytest.mark.parametrize("key", [None, "", "incorrect-key"])
def test_authentication_rejects_missing_or_invalid_key(key: str | None) -> None:
    manager = AuthenticationManager(
        [APIKeyDefinition(key="a-secure-test-key", subject="alice", role="customer_service")]
    )
    with pytest.raises(AuthenticationError):
        manager.authenticate(key)


def test_authorization_enforces_role_permissions(support) -> None:
    AuthenticationManager.authorize(support, Permission.CUSTOMER_READ)
    with pytest.raises(AuthorizationError):
        AuthenticationManager.authorize(support, Permission.INVENTORY_WRITE)


def test_rate_limiter_rejects_request_after_capacity() -> None:
    limiter = TokenBucketRateLimiter(1)
    limiter.check("alice")
    with pytest.raises(RateLimitError):
        limiter.check("alice")
