"""Tests for root and health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """Verify root endpoint returns system status and docs URL."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Aegis Knowledge System"
    assert data["status"] == "online"
    assert "docs_url" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """Verify health endpoint reports healthy database status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
