"""FastAPI endpoint smoke tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(api_client) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "langchain-document-pipeline"


@pytest.mark.asyncio
async def test_dashboard_html(api_client) -> None:
    response = await api_client.get("/")
    assert response.status_code == 200
    assert "Document Pipeline" in response.text
