"""PostgreSQL connection-pool lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg


class PostgresConnectionPool:
    def __init__(self, dsn: str, minimum: int, maximum: int) -> None:
        self.dsn = dsn
        self.minimum = minimum
        self.maximum = maximum
        self._pool: asyncpg.Pool | None = None

    async def start(self) -> None:
        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=self.minimum,
            max_size=self.maximum,
            command_timeout=10,
            max_inactive_connection_lifetime=300,
        )

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        if self._pool is None:
            raise RuntimeError("database pool is not started")
        async with self._pool.acquire() as connection:
            yield connection

    async def health(self) -> bool:
        try:
            async with self.connection() as connection:
                return await connection.fetchval("SELECT 1") == 1
        except Exception:
            return False

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
