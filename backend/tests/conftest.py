import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import build_engine, build_session_factory


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/activia_trace_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = build_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    session_factory = build_session_factory(test_engine)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def test_app(test_engine):
    """FastAPI app with test engine wired into app.state."""
    from app.main import create_app
    from app.core.dependencies import get_db

    app = create_app()
    session_factory = build_session_factory(test_engine)
    app.state.session_factory = session_factory
    yield app


@pytest_asyncio.fixture
async def async_client(test_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client
