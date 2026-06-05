"""
Tests for Alembic migration 002_create_auth_tables.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Task 3.4: upgrade creates tables+indexes; downgrade removes them cleanly.
"""
import os
import subprocess
import pytest
from sqlalchemy import text


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)

ALEMBIC_DATABASE_URL = TEST_DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql+asyncpg://"
)


def _backend_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _alembic_env():
    return {
        **os.environ,
        "DATABASE_URL": TEST_DATABASE_URL,
        "SECRET_KEY": "s" * 34,
        "ENCRYPTION_KEY": "E" * 32,
    }


def _run_alembic(*args):
    # Use Python 3.10 alembic explicitly — asyncpg is installed there, not in system Python.
    alembic_cmd = r"C:\Users\Leand\AppData\Local\Programs\Python\Python310\Scripts\alembic.exe"
    result = subprocess.run(
        [alembic_cmd, *args],
        cwd=_backend_dir(),
        capture_output=True,
        text=True,
        env=_alembic_env(),
    )
    return result


@pytest.fixture
async def migration_engine():
    """Fresh engine for migration tests; does NOT use create_all."""
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=__import__('sqlalchemy.pool', fromlist=['NullPool']).NullPool)
    yield engine
    await engine.dispose()


async def _force_clean_schema(engine) -> None:
    """
    Force-drop all application tables and types using CASCADE in a single
    transaction. More reliable than `alembic downgrade base` because it
    doesn't fail on FK cycles or partial migration states.
    """
    async with engine.begin() as conn:
        # Drop all tables with CASCADE to bypass FK ordering issues
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))


@pytest.fixture
async def clean_db(migration_engine):
    """
    Force-wipe the schema before each migration test, then restore it on teardown.

    Using DROP SCHEMA CASCADE is the only reliable way to reach a clean state
    regardless of FK cycles or partial migration states.
    """
    await _force_clean_schema(migration_engine)
    yield migration_engine
    # Teardown: restore full schema so other tests can use the shared db_session.
    await _force_clean_schema(migration_engine)
    _run_alembic("upgrade", "head")


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_002_upgrade_creates_auth_tables(clean_db):
    """
    Running alembic upgrade 002 creates the three auth tables with correct columns.
    """
    result = _run_alembic("upgrade", "002")
    assert result.returncode == 0, f"alembic upgrade failed:\n{result.stdout}\n{result.stderr}"

    # Verify tables exist
    engine = clean_db
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
        tables = {r[0] for r in result}

    assert "tenants" in tables
    assert "auth_identities" in tables
    assert "refresh_sessions" in tables
    assert "password_recovery_tokens" in tables


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_002_creates_unique_constraint(clean_db):
    """
    The unique constraint (tenant_id, email_hash) exists on auth_identities after upgrade 002.
    """
    _run_alembic("upgrade", "002")

    engine = clean_db
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'auth_identities'
                  AND constraint_type = 'UNIQUE'
            """)
        )
        constraints = {r[0] for r in result}

    assert any("email" in c or "tenant" in c for c in constraints), \
        f"Expected email/tenant unique constraint, got: {constraints}"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_002_downgrade_removes_auth_tables(clean_db):
    """
    Running alembic downgrade -1 from 002 removes auth tables, keeping 001 (tenants).
    """
    # Upgrade just to 002 (not head — avoids running all 014 migrations)
    result = _run_alembic("upgrade", "002")
    assert result.returncode == 0, f"alembic upgrade 002 failed:\n{result.stdout}\n{result.stderr}"

    # Downgrade to 001 = reverts 002 (auth tables), leaves 001 (tenants) intact.
    result = _run_alembic("downgrade", "001")
    assert result.returncode == 0, f"alembic downgrade failed:\n{result.stdout}\n{result.stderr}"

    engine = clean_db
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
        tables = {r[0] for r in result}

    # Auth tables should be gone after downgrade
    assert "auth_identities" not in tables
    assert "refresh_sessions" not in tables
    assert "password_recovery_tokens" not in tables
    # tenants should still be present (001 is still applied)
    assert "tenants" in tables
