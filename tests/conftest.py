"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_db_pool(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid requiring a live PostgreSQL instance for unit/API smoke tests."""
    if request.node.get_closest_marker("integration") is not None:
        return
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    class _AcquireCtx:
        async def __aenter__(self) -> AsyncMock:
            return mock_conn

        async def __aexit__(self, *args: object) -> None:
            return None

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = _AcquireCtx()

    async def fake_get_pool() -> MagicMock:
        return mock_pool

    monkeypatch.setattr("src.db.connection.get_pool", fake_get_pool)
    monkeypatch.setattr("src.db.connection.close_pool", AsyncMock())


@pytest.fixture
async def api_client():
    """Async HTTP client against the FastAPI app."""
    from httpx import ASGITransport, AsyncClient

    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
