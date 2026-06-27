import pytest

from retail_mcp.audit import AuditLogger
from retail_mcp.cache import MemoryCache
from retail_mcp.circuit_breaker import CircuitBreaker
from retail_mcp.repository import InMemoryRetailRepository
from retail_mcp.security import Principal, Role
from retail_mcp.services import ResourceManager, ToolManager


@pytest.fixture
def repository() -> InMemoryRetailRepository:
    return InMemoryRetailRepository()


@pytest.fixture
def cache() -> MemoryCache:
    return MemoryCache()


@pytest.fixture
def resource_manager(repository, cache) -> ResourceManager:
    return ResourceManager(repository, cache, AuditLogger(), 60, 1.0, CircuitBreaker())


@pytest.fixture
def tool_manager(repository, cache) -> ToolManager:
    return ToolManager(repository, cache, AuditLogger(), 1.0)


@pytest.fixture
def admin() -> Principal:
    return Principal("admin-test", Role.ADMIN)


@pytest.fixture
def support() -> Principal:
    return Principal("support-test", Role.CUSTOMER_SERVICE)


@pytest.fixture
def analyst() -> Principal:
    return Principal("analyst-test", Role.SALES_ANALYST)


@pytest.fixture
def inventory_manager() -> Principal:
    return Principal("inventory-test", Role.INVENTORY_MANAGER)

