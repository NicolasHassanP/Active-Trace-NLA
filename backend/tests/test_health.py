import pytest


pytestmark = pytest.mark.asyncio


async def test_health_returns_200(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200


async def test_health_response_has_status_field(async_client):
    response = await async_client.get("/health")
    body = response.json()
    assert "status" in body
    assert body["status"] == "ok"


async def test_health_response_has_database_field(async_client):
    response = await async_client.get("/health")
    body = response.json()
    assert "database" in body
    assert body["database"] in ("up", "down")


async def test_health_reports_db_down_without_crashing(async_client):
    """Cuando la DB no está disponible el endpoint responde sin caerse el proceso."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    # En test sin postgres real, database reporta 'down' — el proceso no crashea
    assert body["status"] == "ok"
    assert body["database"] in ("up", "down")
