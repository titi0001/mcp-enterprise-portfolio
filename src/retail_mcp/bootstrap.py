"""Application dependency construction and lifecycle."""

from dataclasses import dataclass
from typing import Any

from redis.asyncio import from_url

from retail_mcp.audit import AuditLogger
from retail_mcp.cache import Cache, MemoryCache, RedisCache
from retail_mcp.circuit_breaker import CircuitBreaker
from retail_mcp.config import Settings
from retail_mcp.database import PostgresConnectionPool
from retail_mcp.metrics import DEPENDENCY_HEALTH
from retail_mcp.repository import (
    InMemoryRetailRepository,
    PostgresRetailRepository,
    RetailRepository,
)
from retail_mcp.security import AuthenticationManager
from retail_mcp.services import ResourceManager, ToolManager


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    authentication: AuthenticationManager
    repository: RetailRepository
    cache: Cache
    resources: ResourceManager
    tools: ToolManager

    async def ready(self) -> bool:
        healthy = await self.repository.health()
        DEPENDENCY_HEALTH.labels("database").set(1 if healthy else 0)
        return healthy

    async def close(self) -> None:
        await self.cache.close()
        await self.repository.close()


async def build_container(
    settings: Settings, authentication: AuthenticationManager
) -> ApplicationContainer:
    repository: RetailRepository
    if settings.data_backend == "postgres":
        pool = PostgresConnectionPool(
            settings.database_url,
            settings.database_pool_min,
            settings.database_pool_max,
        )
        await pool.start()
        repository = PostgresRetailRepository(pool)
    else:
        repository = InMemoryRetailRepository()

    cache: Cache
    if settings.redis_url:
        redis_client: Any = from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        cache = RedisCache(redis_client)
        DEPENDENCY_HEALTH.labels("redis").set(1)
    else:
        cache = MemoryCache()
        DEPENDENCY_HEALTH.labels("redis").set(0)

    audit = AuditLogger()
    resources = ResourceManager(
        repository,
        cache,
        audit,
        settings.cache_ttl_seconds,
        settings.request_timeout_seconds,
        CircuitBreaker(),
    )
    tools = ToolManager(repository, cache, audit, settings.request_timeout_seconds)
    return ApplicationContainer(settings, authentication, repository, cache, resources, tools)
