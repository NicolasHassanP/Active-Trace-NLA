import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import Base, build_session_factory


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Session-scoped async engine with NullPool.

    NullPool avoids connection-reuse issues on Windows + Python 3.14 where
    the ProactorEventLoop closes underlying socket handles between tests,
    invalidating pooled asyncpg connections.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def create_tables(test_engine):
    """Create all registered tables once per session; drop them at the end."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def db_session(test_engine, create_tables) -> AsyncSession:
    """
    Session-scoped async DB session.

    Shared across all tests in the session. Tests that modify data must
    clean up after themselves (delete rows) or rollback explicitly.
    """
    session_factory = build_session_factory(test_engine)
    session = session_factory()
    yield session
    try:
        await session.close()
    except Exception:
        pass  # Best effort on teardown


@pytest_asyncio.fixture(scope="session")
async def test_app(test_engine, create_tables):
    """FastAPI app with test engine wired into app.state."""
    from app.main import create_app

    app = create_app()
    session_factory = build_session_factory(test_engine)
    app.state.session_factory = session_factory
    yield app


@pytest_asyncio.fixture(scope="session")
async def async_client(test_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client
