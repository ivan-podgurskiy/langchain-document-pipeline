"""Async PostgreSQL connection pool using asyncpg."""

from __future__ import annotations

import asyncpg
from asyncpg import Pool

from src.config import settings

_pool: Pool | None = None


async def get_pool() -> Pool:
    """Return the global connection pool, creating it if necessary."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=settings.db_pool_size,
            command_timeout=60,
        )
    return _pool


async def close_pool() -> None:
    """Close the global connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def execute_query(query: str, *args: object) -> list[asyncpg.Record]:
    """Execute a query and return all rows.

    Args:
        query: SQL query string with $1, $2, ... placeholders.
        *args: Positional arguments for the query placeholders.

    Returns:
        List of asyncpg Record objects.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute_command(query: str, *args: object) -> str:
    """Execute a DML command (INSERT/UPDATE/DELETE) and return the status tag.

    Args:
        query: SQL statement with $1, $2, ... placeholders.
        *args: Positional arguments for the statement.

    Returns:
        PostgreSQL command tag (e.g. 'INSERT 0 1').
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)
