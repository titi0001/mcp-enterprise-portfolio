"""Typed configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIKeyDefinition(BaseModel):
    """A bootstrap API key record supplied by a secret manager."""

    key: str = Field(min_length=12)
    subject: str = Field(min_length=2, max_length=100)
    role: Literal["customer_service", "inventory_manager", "sales_analyst", "admin"]


class Settings(BaseSettings):
    """Application settings. Production refuses bundled development credentials."""

    model_config = SettingsConfigDict(
        env_prefix="RETAIL_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    data_backend: Literal["memory", "postgres"] = "memory"
    database_url: str = "postgresql://retail:retail@localhost:5432/retail"
    database_pool_min: int = Field(default=2, ge=1, le=50)
    database_pool_max: int = Field(default=20, ge=1, le=200)
    redis_url: str | None = None
    cache_ttl_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_per_minute: int = Field(default=120, ge=1, le=100_000)
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    api_keys: list[APIKeyDefinition] = [
        APIKeyDefinition(
            key="dev-customer-key", subject="local-support", role="customer_service"
        ),
        APIKeyDefinition(
            key="dev-inventory-key", subject="local-inventory", role="inventory_manager"
        ),
        APIKeyDefinition(key="dev-analytics-key", subject="local-analyst", role="sales_analyst"),
        APIKeyDefinition(key="dev-admin-key", subject="local-admin", role="admin"),
    ]
    stdio_api_key: str = "dev-admin-key"

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.database_pool_min > self.database_pool_max:
            raise ValueError("database_pool_min cannot exceed database_pool_max")
        if self.environment == "production":
            if self.data_backend != "postgres":
                raise ValueError("production requires the postgres data backend")
            if any(item.key.startswith("dev-") for item in self.api_keys):
                raise ValueError("development API keys are forbidden in production")
            if not self.redis_url:
                raise ValueError("production requires Redis for shared caching")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
