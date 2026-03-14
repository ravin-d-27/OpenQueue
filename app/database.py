from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

import asyncpg

from .settings import get_settings


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def _ensure_pool(self) -> asyncpg.Pool:
        """
        Lazily create and return the asyncpg pool.
        """
        if self.pool is not None:
            return self.pool

        settings = get_settings()

        self.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            # Required for PgBouncer / Supabase Transaction pooler:
            # PgBouncer does not support PostgreSQL named prepared statements,
            # so asyncpg must be told not to cache them.
            statement_cache_size=0,
        )

        # Optional: set statement_timeout for all connections in the pool.
        # This prevents runaway queries from hanging indefinitely.
        if settings.db_statement_timeout_ms:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "SET statement_timeout = $1",
                    int(settings.db_statement_timeout_ms),
                )

        return self.pool

    @asynccontextmanager
    async def get_pool(self):
        pool = await self._ensure_pool()
        yield pool


db = Database()
