"""Authentication, RBAC, request identity, and rate limiting."""

import contextvars
import hashlib
import hmac
import threading
import time
from dataclasses import dataclass
from enum import StrEnum

from retail_mcp.config import APIKeyDefinition
from retail_mcp.errors import AuthenticationError, AuthorizationError, RateLimitError


class Role(StrEnum):
    CUSTOMER_SERVICE = "customer_service"
    INVENTORY_MANAGER = "inventory_manager"
    SALES_ANALYST = "sales_analyst"
    ADMIN = "admin"


class Permission(StrEnum):
    CUSTOMER_READ = "customer:read"
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    SALES_READ = "sales:read"
    ORDER_WRITE = "order:write"
    TICKET_READ = "ticket:read"
    TICKET_WRITE = "ticket:write"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.CUSTOMER_SERVICE: frozenset(
        {
            Permission.CUSTOMER_READ,
            Permission.INVENTORY_READ,
            Permission.TICKET_READ,
            Permission.TICKET_WRITE,
        }
    ),
    Role.INVENTORY_MANAGER: frozenset(
        {Permission.INVENTORY_READ, Permission.INVENTORY_WRITE, Permission.SALES_READ}
    ),
    Role.SALES_ANALYST: frozenset(
        {Permission.CUSTOMER_READ, Permission.INVENTORY_READ, Permission.SALES_READ}
    ),
    Role.ADMIN: frozenset(Permission),
}


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: Role

    @property
    def permissions(self) -> frozenset[Permission]:
        return ROLE_PERMISSIONS[self.role]


_principal_context: contextvars.ContextVar[Principal | None] = contextvars.ContextVar(
    "principal", default=None
)
_request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="not-set"
)


def set_request_context(principal: Principal, request_id: str) -> tuple[object, object]:
    return _principal_context.set(principal), _request_id_context.set(request_id)


def reset_request_context(tokens: tuple[object, object]) -> None:
    _principal_context.reset(tokens[0])
    _request_id_context.reset(tokens[1])


def current_principal() -> Principal:
    principal = _principal_context.get()
    if principal is None:
        raise AuthenticationError("Authentication is required")
    return principal


def current_request_id() -> str:
    return _request_id_context.get()


class AuthenticationManager:
    """Stores only SHA-256 API-key digests and compares them in constant time."""

    def __init__(self, definitions: list[APIKeyDefinition]) -> None:
        self._records = [
            (self._digest(item.key), Principal(item.subject, Role(item.role)))
            for item in definitions
        ]

    @staticmethod
    def _digest(api_key: str) -> bytes:
        return hashlib.sha256(api_key.encode("utf-8")).digest()

    def authenticate(self, api_key: str | None) -> Principal:
        if not api_key:
            raise AuthenticationError("Missing API key")
        candidate = self._digest(api_key)
        for expected, principal in self._records:
            if hmac.compare_digest(candidate, expected):
                return principal
        raise AuthenticationError("Invalid API key")

    @staticmethod
    def authorize(principal: Principal, permission: Permission) -> None:
        if permission not in principal.permissions:
            raise AuthorizationError("You are not authorized to perform this operation")


class TokenBucketRateLimiter:
    """In-process token bucket. Use a gateway or Redis-backed limiter across replicas."""

    def __init__(self, requests_per_minute: int) -> None:
        self.capacity = float(requests_per_minute)
        self.refill_per_second = self.capacity / 60.0
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, subject: str) -> None:
        now = time.monotonic()
        with self._lock:
            tokens, previous = self._buckets.get(subject, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - previous) * self.refill_per_second)
            if tokens < 1:
                self._buckets[subject] = (tokens, now)
                raise RateLimitError("Request rate limit exceeded")
            self._buckets[subject] = (tokens - 1, now)
