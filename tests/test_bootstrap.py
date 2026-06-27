from retail_mcp.bootstrap import build_container
from retail_mcp.config import Settings
from retail_mcp.security import AuthenticationManager


async def test_memory_container_lifecycle() -> None:
    settings = Settings(environment="test", data_backend="memory", redis_url=None)
    authentication = AuthenticationManager(settings.api_keys)
    container = await build_container(settings, authentication)

    assert await container.ready() is True
    assert container.settings.environment == "test"

    await container.close()
