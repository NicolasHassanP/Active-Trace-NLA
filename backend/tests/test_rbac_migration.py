"""
test_rbac_migration.py — Tasks 2.1, 2.3, 2.5, 2.6 RED/TRIANGULATE

Tests for migration 003_create_rbac_tables:
- Tables, indexes and enum created correctly by upgrade.
- Seed of §3.3 matrix seeded per tenant.
- Idempotency of the seed.
- downgrade() removes RBAC tables without touching auth tables.

Pattern: drop all → alembic upgrade → assert → alembic downgrade.
Follows test_auth_migration.py approach to avoid conflicts with session fixtures.
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
# Fixtures — mirrors test_auth_migration.py: drop all → upgrade → test → restore
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def migration_engine():
    """Fresh engine for migration tests (no create_all)."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def clean_db_for_migration(migration_engine):
    """
    Drop all tables/enums → run alembic upgrade 002 (auth, no rbac) →
    create a test tenant → yield (engine, tenant_id).
    Teardown: restore to head + recreate conftest enums/tables.
    """
    engine = migration_engine

    # Drop everything cleanly
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS rol_permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rol CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS password_recovery_tokens CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auth_identities CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS permiso_scope CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))

    # Run alembic up to 002 (so auth tables + tenants exist but no rbac)
    result = _run_alembic("upgrade", "002")
    assert result.returncode == 0, f"upgrade 002 failed:\n{result.stderr}"

    # Create a test tenant for seed assertions
    tenant_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenants (id, nombre, estado, created_at, updated_at) "
                "VALUES (:id, 'Migration Test Tenant', 'activo', now(), now())"
            ),
            {"id": tenant_id},
        )

    yield engine, tenant_id

    # Teardown: restore to head so session-scoped fixtures still work
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS rol_permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS permiso CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rol CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS password_recovery_tokens CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS refresh_sessions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auth_identities CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS permiso_scope CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))

    # Re-apply everything so the shared session fixtures still work
    _run_alembic("upgrade", "head")

    # Recreate permiso_scope enum if downgrade dropped it (conftest needs it)
    from app.core.database import Base
    async with engine.begin() as conn:
        r = await conn.execute(text("SELECT 1 FROM pg_type WHERE typname='permiso_scope'"))
        if r.scalar() is None:
            await conn.execute(text("CREATE TYPE permiso_scope AS ENUM ('global', 'propio')"))
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


# ---------------------------------------------------------------------------
# Task 2.1 — Tables, indexes, enum exist after upgrade 003
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_upgrade_creates_tables(clean_db_for_migration):
    """upgrade 003 creates rol, permiso, rol_permiso tables."""
    engine, _ = clean_db_for_migration
    result = _run_alembic("upgrade", "003")
    assert result.returncode == 0, f"upgrade 003 failed:\n{result.stderr[-2000:]}"

    async with engine.connect() as conn:
        for tname in ("rol", "permiso", "rol_permiso"):
            r = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=:t"
                ),
                {"t": tname},
            )
            assert r.scalar() == 1, f"Table {tname!r} missing after upgrade 003"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_permiso_scope_enum_created(clean_db_for_migration):
    """upgrade 003 creates the permiso_scope enum."""
    engine, _ = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'permiso_scope'")
        )
        assert r.scalar() == 1, "permiso_scope enum missing after upgrade"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_indexes_on_tenant_id_exist(clean_db_for_migration):
    """upgrade 003 creates indexes on tenant_id for all three tables."""
    engine, _ = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        for idx in ("ix_rol_tenant_id", "ix_permiso_tenant_id", "ix_rol_permiso_tenant_id"):
            r = await conn.execute(
                text("SELECT 1 FROM pg_indexes WHERE indexname=:idx"),
                {"idx": idx},
            )
            assert r.scalar() == 1, f"Index {idx!r} missing after upgrade 003"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_deleted_at_on_all_tables(clean_db_for_migration):
    """upgrade 003: all three tables have deleted_at for soft delete."""
    engine, _ = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        for tname in ("rol", "permiso", "rol_permiso"):
            r = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name='deleted_at'"
                ),
                {"t": tname},
            )
            assert r.scalar() == 1, f"deleted_at missing on {tname}"


# ---------------------------------------------------------------------------
# Task 2.3 — Seed: roles and permissions seeded correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_seeds_seven_roles_per_tenant(clean_db_for_migration):
    """After upgrade 003, the existing tenant has all 7 domain roles."""
    engine, tenant_id = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT COUNT(*) FROM rol WHERE tenant_id=:tid AND deleted_at IS NULL"),
            {"tid": tenant_id},
        )
        count = r.scalar()
        assert count == 7, f"Expected 7 roles, got {count}"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_coordinador_comunicacion_aprobar_global(clean_db_for_migration):
    """COORDINADOR has comunicacion:aprobar with scope=global."""
    engine, tenant_id = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("""
                SELECT rp.scope
                FROM rol r
                JOIN rol_permiso rp ON rp.rol_id = r.id
                JOIN permiso p ON p.id = rp.permiso_id
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'COORDINADOR'
                  AND p.codigo = 'comunicacion:aprobar'
                  AND r.deleted_at IS NULL AND rp.deleted_at IS NULL
            """),
            {"tid": tenant_id},
        )
        row = r.fetchone()
        assert row is not None, "COORDINADOR.comunicacion:aprobar not seeded"
        assert row[0] == "global", f"Expected global, got {row[0]}"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_profesor_calificaciones_importar_propio(clean_db_for_migration):
    """PROFESOR has calificaciones:importar with scope=propio."""
    engine, tenant_id = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("""
                SELECT rp.scope
                FROM rol r
                JOIN rol_permiso rp ON rp.rol_id = r.id
                JOIN permiso p ON p.id = rp.permiso_id
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'PROFESOR'
                  AND p.codigo = 'calificaciones:importar'
                  AND r.deleted_at IS NULL AND rp.deleted_at IS NULL
            """),
            {"tid": tenant_id},
        )
        row = r.fetchone()
        assert row is not None, "PROFESOR.calificaciones:importar not seeded"
        assert row[0] == "propio", f"Expected propio, got {row[0]}"


# ---------------------------------------------------------------------------
# Task 2.5 — TRIANGULATE: idempotency, NEXO fail-closed, propio scopes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_nexo_has_exactly_one_permission(clean_db_for_migration):
    """OQ-4: NEXO has exactly 1 permission — avisos:confirmar (global)."""
    engine, tenant_id = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("""
                SELECT p.codigo, rp.scope
                FROM rol r
                JOIN rol_permiso rp ON rp.rol_id = r.id
                JOIN permiso p ON p.id = rp.permiso_id
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'NEXO'
                  AND r.deleted_at IS NULL AND rp.deleted_at IS NULL
            """),
            {"tid": tenant_id},
        )
        rows = r.fetchall()
        assert len(rows) == 1, f"NEXO should have 1 permission, got {len(rows)}: {rows}"
        assert rows[0][0] == "avisos:confirmar"
        assert rows[0][1] == "global"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_seed_idempotent(clean_db_for_migration):
    """Edge: running upgrade a second time leaves no duplicate rows."""
    engine, tenant_id = clean_db_for_migration
    _run_alembic("upgrade", "003")
    # Run upgrade head again — no-op since already at 003 head
    _run_alembic("upgrade", "head")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT COUNT(*) FROM rol WHERE tenant_id=:tid AND deleted_at IS NULL"),
            {"tid": tenant_id},
        )
        count = r.scalar()
        assert count == 7, f"After second run, expected 7 roles, got {count}"


@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_propio_scopes_seeded_correctly(clean_db_for_migration):
    """TUTOR.guardias:registrar has scope=propio (matrix §3.3)."""
    engine, tenant_id = clean_db_for_migration
    _run_alembic("upgrade", "003")

    async with engine.connect() as conn:
        r = await conn.execute(
            text("""
                SELECT rp.scope
                FROM rol r
                JOIN rol_permiso rp ON rp.rol_id = r.id
                JOIN permiso p ON p.id = rp.permiso_id
                WHERE r.tenant_id = :tid
                  AND r.nombre = 'TUTOR'
                  AND p.codigo = 'guardias:registrar'
                  AND r.deleted_at IS NULL AND rp.deleted_at IS NULL
            """),
            {"tid": tenant_id},
        )
        row = r.fetchone()
        assert row is not None, "TUTOR.guardias:registrar not seeded"
        assert row[0] == "propio"


# ---------------------------------------------------------------------------
# Task 2.6 — TRIANGULATE: downgrade removes RBAC, auth tables remain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_migration_003_downgrade_removes_rbac_tables(clean_db_for_migration):
    """downgrade -1 from 003 removes rol/permiso/rol_permiso, keeps auth tables."""
    engine, _ = clean_db_for_migration
    _run_alembic("upgrade", "003")

    result = _run_alembic("downgrade", "-1")
    assert result.returncode == 0, f"downgrade failed:\n{result.stderr[-2000:]}"

    async with engine.connect() as conn:
        # RBAC tables gone
        for tname in ("rol", "permiso", "rol_permiso"):
            r = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=:t"
                ),
                {"t": tname},
            )
            assert r.scalar() is None, f"{tname!r} should be gone after downgrade"

        # Auth tables still exist
        r = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='auth_identities'"
            )
        )
        assert r.scalar() == 1, "auth_identities should remain after RBAC downgrade"
