import pytest
from httpx import ASGITransport, AsyncClient


pytestmark = pytest.mark.asyncio


async def test_app_instantiates_without_error():
    from app.main import create_app

    app = create_app()
    assert app is not None


async def test_app_serves_requests_via_asgi(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
