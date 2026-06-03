"""
test_audit_migration.py — Tasks 3.7, 4.1, 4.2, 4.3 RED/GREEN

Tests for migration 004_create_audit_event_table:
  - Table, enums and indexes created by upgrade.
  - NO updated_at / deleted_at columns (append-only).
  - Trigger: UPDATE on audit_event raises exception (task 4.1).
  - Trigger: DELETE on audit_event raises exception (task 4.2).
  - Downgrade removes table, trigger and enums.

Pattern: drop all → alembic upgrade 003 → test upgrade 004 → downgrade → restore.
Follows test_rbac_migration.py approach.
"""
import os
import subprocess
import uuid
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
# Fixtures — drop all → upgrade 003 → yield → teardown
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def migration_engine_004():
    """Fresh engine for migration 004 tests (no create_all)."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def clean_db_for_004(migration_engine_004):
    """
    Drop all tables/enums → run alembic upgrade 003 (so audit table doesn't exist yet).
    Teardown: restore to head + recreate conftest enums/tables.
    """
    engine = migration_engine_004

    # Drop everything cleanly
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS audit_event CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rol_permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rol CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS password_recovery_tokens CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auth_identities CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS audit_action CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS audit_resultado CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS permiso_scope CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))
        await conn.execute(text("DROP FUNCTION IF EXISTS audit_event_immutable() CASCADE"))

    # Run alembic up to 003 (so rbac + tenants exist but no audit table)
    result = _run_alembic("upgrade", "003")
    assert result.returncode == 0, f"upgrade 003 failed:\n{result.stderr}"

    yield engine

    # Teardown: restore to head so session-scoped fixtures still work
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS audit_event CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rol_permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rol CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS password_recovery_tokens CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auth_identities CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS audit_action CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS audit_resultado CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS permiso_scope CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))
        await conn.execute(text("DROP FUNCTION IF EXISTS audit_event_immutable() CASCADE"))

    # Re-apply everything so the shared session fixtures still work
    _run_alembic("upgrade", "head")

    # Recreate enums if downgrade dropped them (conftest needs them)
    from app.core.database import Base
    async with engine.begin() as conn:
        for enum_name, enum_vals in [
            ("permiso_scope", "('global', 'propio')"),
            ("audit_action", "('IMPERSONACION_INICIO', 'IMPERSONACION_FIN', 'AUDITORIA_CONSULTA')"),
            ("audit_resultado", "('ok', 'fail', 'partial')"),
        ]:
            r = await conn.execute(
                text(f"SELECT 1 FROM pg_type WHERE typname=:n"),
                {"n": enum_name},
            )
            if r.scalar() is None:
                await conn.execute(
                    text(f"CREATE TYPE {enum_name} AS ENUM {enum_vals}")
                )
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


# ---------------------------------------------------------------------------
# Task 3.7 — upgrade 004 creates table, enums and indexes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_upgrade_creates_audit_event_table(clean_db_for_004):
    """upgrade 004 creates the audit_event table."""
    engine = clean_db_for_004
    result = _run_alembic("upgrade", "004")
    assert result.returncode == 0, f"upgrade 004 failed:\n{result.stderr[-3000:]}"

    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='audit_event'"
            )
        )
        assert r.scalar() == 1, "audit_event table not created"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_audit_action_enum_created(clean_db_for_004):
    """upgrade 004 creates the audit_action enum."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname='audit_action'")
        )
        assert r.scalar() == 1, "audit_action enum missing"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_audit_resultado_enum_created(clean_db_for_004):
    """upgrade 004 creates the audit_resultado enum."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname='audit_resultado'")
        )
        assert r.scalar() == 1, "audit_resultado enum missing"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_no_updated_at_column(clean_db_for_004):
    """D2: audit_event has no updated_at column."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='audit_event' AND column_name='updated_at'"
            )
        )
        assert r.scalar() is None, "audit_event must NOT have updated_at"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_no_deleted_at_column(clean_db_for_004):
    """D2: audit_event has no deleted_at column."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    async with engine.connect() as conn:
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='audit_event' AND column_name='deleted_at'"
            )
        )
        assert r.scalar() is None, "audit_event must NOT have deleted_at"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_indexes_created(clean_db_for_004):
    """upgrade 004 creates both composite indexes."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    async with engine.connect() as conn:
        for idx in ("ix_audit_event_tenant_created", "ix_audit_event_tenant_actor"):
            r = await conn.execute(
                text("SELECT 1 FROM pg_indexes WHERE indexname=:idx"),
                {"idx": idx},
            )
            assert r.scalar() == 1, f"Index {idx!r} missing after upgrade 004"


# ---------------------------------------------------------------------------
# Tasks 4.1–4.3 — Immutability trigger (D3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_update_rejected_by_trigger(clean_db_for_004):
    """Task 4.1 RED: UPDATE on audit_event raises DB exception (trigger D3)."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    # Insert a tenant and event to try to update
    tenant_id = uuid.uuid4()
    event_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenants (id, nombre, estado, created_at, updated_at) "
                "VALUES (:id, 'Trigger Test Tenant', 'activo', now(), now())"
            ),
            {"id": tenant_id},
        )
        await conn.execute(
            text("""
                INSERT INTO audit_event
                    (id, tenant_id, actor_user_id, accion, modulo, entidad_tipo,
                     resultado, created_at)
                VALUES
                    (:id, :tid, :actor, 'AUDITORIA_CONSULTA', 'auditoria',
                     'AuditEvent', 'ok', now())
            """),
            {"id": event_id, "tid": tenant_id, "actor": actor_id},
        )

    # Attempt UPDATE — must raise
    from sqlalchemy.exc import DBAPIError
    async with engine.begin() as conn:
        with pytest.raises(DBAPIError):
            await conn.execute(
                text(
                    "UPDATE audit_event SET modulo='hacked' WHERE id=:id"
                ),
                {"id": event_id},
            )


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_delete_rejected_by_trigger(clean_db_for_004):
    """Task 4.2 RED: DELETE on audit_event raises DB exception (trigger D3)."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    tenant_id = uuid.uuid4()
    event_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenants (id, nombre, estado, created_at, updated_at) "
                "VALUES (:id, 'Delete Test Tenant', 'activo', now(), now())"
            ),
            {"id": tenant_id},
        )
        await conn.execute(
            text("""
                INSERT INTO audit_event
                    (id, tenant_id, actor_user_id, accion, modulo, entidad_tipo,
                     resultado, created_at)
                VALUES
                    (:id, :tid, :actor, 'IMPERSONACION_INICIO', 'impersonacion',
                     'User', 'ok', now())
            """),
            {"id": event_id, "tid": tenant_id, "actor": actor_id},
        )

    # Attempt DELETE — must raise
    from sqlalchemy.exc import DBAPIError
    async with engine.begin() as conn:
        with pytest.raises(DBAPIError):
            await conn.execute(
                text("DELETE FROM audit_event WHERE id=:id"),
                {"id": event_id},
            )


# ---------------------------------------------------------------------------
# Task 3.7 downgrade — removes table and enums
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_004_downgrade_removes_audit_table(clean_db_for_004):
    """downgrade -1 from 004 removes audit_event and enums; rbac tables remain."""
    engine = clean_db_for_004
    _run_alembic("upgrade", "004")

    result = _run_alembic("downgrade", "-1")
    assert result.returncode == 0, f"downgrade failed:\n{result.stderr[-3000:]}"

    async with engine.connect() as conn:
        # audit_event gone
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='audit_event'"
            )
        )
        assert r.scalar() is None, "audit_event should be gone after downgrade"

        # RBAC tables still exist
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='rol'"
            )
        )
        assert r.scalar() == 1, "rol table should remain after audit downgrade"
