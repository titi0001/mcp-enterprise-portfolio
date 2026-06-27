import pytest
from pydantic import ValidationError

from retail_mcp.config import Settings


def test_production_rejects_development_credentials() -> None:
    with pytest.raises(ValidationError, match="development API keys"):
        Settings(environment="production", data_backend="postgres", redis_url="redis://redis")


def test_pool_minimum_cannot_exceed_maximum() -> None:
    with pytest.raises(ValidationError, match="cannot exceed"):
        Settings(database_pool_min=10, database_pool_max=2)

