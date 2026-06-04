"""
TDD test for migration 009_create_comunicaciones.py (Task 3.1 RED).

Verifies that alembic upgrade 009 creates:
    - Table 'comunicacion' with all columns and indexes.
    - Table 'tenant_config' with UNIQUE (tenant_id, clave).
    - Enum 'comunicacion_estado'.
    - 'COMUNICACION_ENVIAR' added to audit_action enum.

Pattern: matches test_audit_migration.py — isolated DB teardown/restore.
"""
import os
import subprocess
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
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
    return subprocess.run(
        ["alembic", *args],
        cwd=_backend_dir(),
        capture_output=True,
        text=True,
        env=_alembic_env(),
    )


# ---------------------------------------------------------------------------
# Fixture — drop all → upgrade 008 → yield → teardown
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def migration_engine_009():
    """Fresh engine for migration 009 tests (no create_all)."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


_TABLES_TO_DROP = [
    "comunicacion",
    "tenant_config",
    "umbral_materia",
    "calificacion",
    "entrada_padron",
    "version_padron",
    "asignacion",
    "usuario",
    "materia",
    "cohorte",
    "carrera",
    "audit_event",
    "rol_permiso",
    "permiso",
    "rol",
    "password_recovery_tokens",
    "refresh_sessions",
    "auth_identities",
    "tenants",
    "alembic_version",
]

_ENUMS_TO_DROP = [
    "comunicacion_estado",
    "calificacion_origen",
    "usuario_estado",
    "rol_asignacion",
    "estado_estructura",
    "audit_action",
    "audit_resultado",
    "permiso_scope",
    "tenant_estado",
]

_FUNCTIONS_TO_DROP = [
    "audit_event_immutable",
]


async def _drop_all(engine):
    async with engine.begin() as conn:
        for table in _TABLES_TO_DROP:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        for enum in _ENUMS_TO_DROP:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum} CASCADE"))
        for func in _FUNCTIONS_TO_DROP:
            await conn.execute(text(f"DROP FUNCTION IF EXISTS {func}() CASCADE"))


@pytest_asyncio.fixture
async def clean_db_for_009(migration_engine_009):
    """
    Drop all → upgrade to 008 → yield → restore to head.
    """
    engine = migration_engine_009
    await _drop_all(engine)

    # Run alembic up to 008 (so 009 tables don't exist yet)
    result = _run_alembic("upgrade", "008")
    assert result.returncode == 0, f"upgrade 008 failed:\n{result.stderr}"

    yield engine

    # Teardown: restore to head
    await _drop_all(engine)
    _run_alembic("upgrade", "head")

    # Recreate session-scoped test schema
    from app.core.database import Base
    from tests.conftest import _ensure_schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


# ---------------------------------------------------------------------------
# Task 3.1 — upgrade 009 creates comunicacion + tenant_config + enum
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_creates_comunicacion_table(clean_db_for_009):
    """upgrade 009 creates the 'comunicacion' table."""
    engine = clean_db_for_009
    result = _run_alembic("upgrade", "009")
    assert result.returncode == 0, f"upgrade 009 failed:\n{result.stderr[-3000:]}"

    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'comunicacion'"
            )
        )
        assert r.scalar() == 1, "Table 'comunicacion' was not created by migration 009"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_creates_tenant_config_table(clean_db_for_009):
    """upgrade 009 creates the 'tenant_config' table."""
    engine = clean_db_for_009
    _run_alembic("upgrade", "009")

    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'tenant_config'"
            )
        )
        assert r.scalar() == 1, "Table 'tenant_config' was not created by migration 009"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_creates_comunicacion_estado_enum(clean_db_for_009):
    """upgrade 009 creates the 'comunicacion_estado' enum type."""
    engine = clean_db_for_009
    _run_alembic("upgrade", "009")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'comunicacion_estado'")
        )
        assert r.scalar() == 1, "Enum 'comunicacion_estado' was not created"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_adds_comunicacion_enviar_to_audit_action(clean_db_for_009):
    """upgrade 009 adds 'COMUNICACION_ENVIAR' to audit_action enum."""
    engine = clean_db_for_009
    _run_alembic("upgrade", "009")

    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' "
                "AND e.enumlabel = 'COMUNICACION_ENVIAR'"
            )
        )
        assert r.scalar() == 1, "COMUNICACION_ENVIAR not added to audit_action enum"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_tenant_config_unique_constraint(clean_db_for_009):
    """upgrade 009 creates UNIQUE (tenant_id, clave) on tenant_config."""
    engine = clean_db_for_009
    _run_alembic("upgrade", "009")

    async with engine.connect() as conn:
        # Check partial unique index exists
        r = await conn.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'tenant_config' "
                "AND indexname LIKE '%tenant_config%clave%'"
            )
        )
        assert r.scalar() == 1, "UNIQUE (tenant_id, clave) index not found on tenant_config"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_downgrade_removes_tables(clean_db_for_009):
    """downgrade from 009 removes comunicacion and tenant_config tables."""
    engine = clean_db_for_009
    _run_alembic("upgrade", "009")

    result = _run_alembic("downgrade", "008")
    assert result.returncode == 0, f"downgrade 009 failed:\n{result.stderr[-3000:]}"

    async with engine.connect() as conn:
        for table_name in ("comunicacion", "tenant_config"):
            r = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = :name"
                ),
                {"name": table_name},
            )
            assert r.scalar() is None, f"Table '{table_name}' was not removed by downgrade"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_009_downgrade_removes_enum(clean_db_for_009):
    """downgrade from 009 removes the comunicacion_estado enum."""
    engine = clean_db_for_009
    _run_alembic("upgrade", "009")
    _run_alembic("downgrade", "008")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'comunicacion_estado'")
        )
        assert r.scalar() is None, "Enum 'comunicacion_estado' was not removed by downgrade"
