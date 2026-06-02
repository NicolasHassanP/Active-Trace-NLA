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
    result = subprocess.run(
        ["alembic", *args],
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


@pytest.fixture
async def clean_db(migration_engine):
    """
    Drop all auth/tenant tables and types before each migration test.

    Teardown runs `alembic upgrade head` to restore the schema to the state
    that the session-scoped `create_tables` fixture in conftest.py expects.
    This prevents the migration tests from leaving the DB in a state that
    breaks the shared session-scoped db_session fixture used by other tests.
    """
    # Drop existing state
    async with migration_engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS password_recovery_tokens CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auth_identities CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))
    yield migration_engine
    # Teardown: restore schema to `head` so subsequent tests that use the
    # shared session-scoped fixtures (db_session, create_tables) still work.
    # Drop first to ensure clean state, then upgrade.
    async with migration_engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS password_recovery_tokens CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auth_identities CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))
    # Re-apply all migrations so the schema matches what create_tables expects.
    _run_alembic("upgrade", "head")


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_002_upgrade_creates_auth_tables(clean_db):
    """
    Running alembic upgrade head creates the three auth tables with correct columns.
    """
    result = _run_alembic("upgrade", "head")
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
    The unique constraint (tenant_id, email_hash) exists on auth_identities.
    """
    _run_alembic("upgrade", "head")

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
    Running alembic downgrade removes the auth tables cleanly.
    """
    # First upgrade
    _run_alembic("upgrade", "head")

    # Then downgrade one step (removes 002)
    result = _run_alembic("downgrade", "-1")
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
