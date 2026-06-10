"""
test_c20_seed_rbac_migration.py — TDD tests for C-20 migration 018.

The 018 migration seeds the RBAC permisos `perfil:editar` and `inbox:usar`
per-tenant, with grants per the C-20 design spec:
    - perfil:editar (scope 'propio') → ALL 7 roles, including ALUMNO (OQ-1).
    - inbox:usar    (scope 'global') → all roles EXCEPT ALUMNO.

The suite does not run Alembic migrations (conftest uses create_all). This file
imports the standalone seed helper `seed_c20_rbac_for_tenant` from migration 018
(loaded via importlib by path, since the versions/ dir is not a package) and
exercises it against the real test DB.

Uses real DB (activia_trace_test). No DB mocks.
"""
import asyncio
import importlib
import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)

ROLES = ["ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"]


# ---------------------------------------------------------------------------
# Load the migration-018 helper by path (versions/ is not an importable package)
# ---------------------------------------------------------------------------

def _load_seed_helper():
    """
    Load the migration-018 module by path.

    The local `backend/alembic/` package (empty __init__.py) shadows the installed
    `alembic` library when tests run from `backend/`. The migration does
    `from alembic import op` at module level, so we must ensure the *real* alembic
    library resolves before exec'ing the module. We do that by dropping the shadow
    paths from sys.path and clearing the cached empty `alembic` module, importing
    the real library, then exec'ing the migration.
    """
    backend_dir = Path(__file__).resolve().parent.parent
    mig_path = backend_dir / "alembic" / "versions" / "018_c20_seed_rbac_perfil_inbox.py"

    saved_path = list(sys.path)
    saved_alembic = {k: v for k, v in sys.modules.items()
                     if k == "alembic" or k.startswith("alembic.")}
    try:
        # Remove paths that would resolve `alembic` to the local shadow package.
        sys.path[:] = [
            p for p in sys.path
            if Path(p or ".").resolve() not in (backend_dir, backend_dir / "alembic")
        ]
        for k in list(saved_alembic):
            del sys.modules[k]
        importlib.import_module("alembic")  # load the real library

        spec = importlib.util.spec_from_file_location("_mig_018", mig_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.seed_c20_rbac_for_tenant
    finally:
        sys.path[:] = saved_path
        # Restore the original (shadow) alembic modules so other tests/imports see
        # the same state they had before.
        for k in [m for m in sys.modules if m == "alembic" or m.startswith("alembic.")]:
            del sys.modules[k]
        sys.modules.update(saved_alembic)


seed_c20_rbac_for_tenant = _load_seed_helper()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def migration_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def seeded_tenant(migration_engine):
    """
    Create a fresh test tenant with the 7 system roles, run the C-20 seed helper
    (the helper itself seeds permisos + grants), yield the tenant_id, then clean up.
    """
    import app.models  # noqa: F401  (ensure base schema metadata is importable)

    tid = uuid.uuid4()

    async with migration_engine.begin() as conn:
        # Ensure base schema + enums exist (create_all is safe/idempotent).
        await conn.execute(text(
            "DO $$ BEGIN CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        ))
        await conn.execute(text(
            "DO $$ BEGIN CREATE TYPE permiso_scope AS ENUM ('global', 'propio'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        ))
        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Create the tenant.
        await conn.execute(text(
            "INSERT INTO tenants (id, nombre, estado, created_at, updated_at) "
            "VALUES (:tid, :nombre, 'activo', now(), now()) ON CONFLICT DO NOTHING"
        ), {"tid": str(tid), "nombre": f"C20Seed_{tid.hex[:8]}"})

        # Seed the 7 system roles.
        for nombre in ROLES:
            await conn.execute(text(
                "INSERT INTO rol (id, tenant_id, nombre, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :tid, :nombre, now(), now()) "
                "ON CONFLICT ON CONSTRAINT uq_rol_tenant_nombre DO NOTHING"
            ), {"tid": str(tid), "nombre": nombre})

        # Run the C-20 seed helper (sync API → run via run_sync on the connection).
        await conn.run_sync(lambda sync_conn: seed_c20_rbac_for_tenant(sync_conn, tid))

    yield tid

    # Teardown: remove all rows created for this tenant.
    async with migration_engine.begin() as conn:
        await conn.execute(text("DELETE FROM rol_permiso WHERE tenant_id = :tid"), {"tid": str(tid)})
        await conn.execute(text("DELETE FROM permiso WHERE tenant_id = :tid"), {"tid": str(tid)})
        await conn.execute(text("DELETE FROM rol WHERE tenant_id = :tid"), {"tid": str(tid)})
        await conn.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": str(tid)})


async def _roles_with_permiso(conn, tid, codigo):
    result = await conn.execute(text("""
        SELECT r.nombre, rp.scope
        FROM rol_permiso rp
        JOIN rol r ON r.id = rp.rol_id
        JOIN permiso p ON p.id = rp.permiso_id
        WHERE rp.tenant_id = :tid AND p.codigo = :codigo
    """), {"tid": str(tid), "codigo": codigo})
    return {row[0]: row[1] for row in result.fetchall()}


# ---------------------------------------------------------------------------
# RED — permisos exist after seed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_permisos_perfil_e_inbox_existen(migration_engine, seeded_tenant):
    """RED: ambos permisos C-20 existen en el catálogo del tenant."""
    async with migration_engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT codigo FROM permiso WHERE tenant_id = :tid "
            "AND codigo IN ('perfil:editar', 'inbox:usar')"
        ), {"tid": str(seeded_tenant)})
        codigos = {row[0] for row in result.fetchall()}
    assert codigos == {"perfil:editar", "inbox:usar"}


@pytest.mark.asyncio(loop_scope="module")
async def test_perfil_editar_otorgado_a_los_7_roles(migration_engine, seeded_tenant):
    """RED: perfil:editar otorgado a TODOS los 7 roles con scope 'propio'."""
    async with migration_engine.connect() as conn:
        grants = await _roles_with_permiso(conn, seeded_tenant, "perfil:editar")
    assert set(grants.keys()) == set(ROLES), f"Faltan roles: {set(ROLES) - set(grants)}"
    assert all(scope == "propio" for scope in grants.values()), grants


@pytest.mark.asyncio(loop_scope="module")
async def test_inbox_usar_otorgado_a_6_roles_sin_alumno(migration_engine, seeded_tenant):
    """RED: inbox:usar otorgado a 6 roles (todos menos ALUMNO) con scope 'global'."""
    expected = {"TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"}
    async with migration_engine.connect() as conn:
        grants = await _roles_with_permiso(conn, seeded_tenant, "inbox:usar")
    assert set(grants.keys()) == expected, f"Esperado {expected}, obtenido {set(grants)}"
    assert all(scope == "global" for scope in grants.values()), grants


# ---------------------------------------------------------------------------
# TRIANGULATE — ALUMNO has perfil:editar but NOT inbox:usar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_alumno_tiene_perfil_pero_no_inbox(migration_engine, seeded_tenant):
    """TRIANGULATE: ALUMNO tiene perfil:editar pero NO inbox:usar."""
    async with migration_engine.connect() as conn:
        perfil = await _roles_with_permiso(conn, seeded_tenant, "perfil:editar")
        inbox = await _roles_with_permiso(conn, seeded_tenant, "inbox:usar")
    assert "ALUMNO" in perfil, "ALUMNO debe tener perfil:editar"
    assert perfil["ALUMNO"] == "propio"
    assert "ALUMNO" not in inbox, "ALUMNO NO debe tener inbox:usar"


# ---------------------------------------------------------------------------
# Idempotencia — running the helper twice does not duplicate rows
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="module")
async def test_seed_es_idempotente(migration_engine, seeded_tenant):
    """Idempotencia: re-correr el helper no duplica permisos ni grants."""
    async with migration_engine.connect() as conn:
        perm_antes = (await conn.execute(text(
            "SELECT COUNT(*) FROM permiso WHERE tenant_id = :tid "
            "AND codigo IN ('perfil:editar', 'inbox:usar')"
        ), {"tid": str(seeded_tenant)})).scalar()
        grants_antes = (await conn.execute(text("""
            SELECT COUNT(*) FROM rol_permiso rp
            JOIN permiso p ON p.id = rp.permiso_id
            WHERE rp.tenant_id = :tid AND p.codigo IN ('perfil:editar', 'inbox:usar')
        """), {"tid": str(seeded_tenant)})).scalar()

    # Run the helper a second time.
    async with migration_engine.begin() as conn:
        await conn.run_sync(lambda sc: seed_c20_rbac_for_tenant(sc, seeded_tenant))

    async with migration_engine.connect() as conn:
        perm_despues = (await conn.execute(text(
            "SELECT COUNT(*) FROM permiso WHERE tenant_id = :tid "
            "AND codigo IN ('perfil:editar', 'inbox:usar')"
        ), {"tid": str(seeded_tenant)})).scalar()
        grants_despues = (await conn.execute(text("""
            SELECT COUNT(*) FROM rol_permiso rp
            JOIN permiso p ON p.id = rp.permiso_id
            WHERE rp.tenant_id = :tid AND p.codigo IN ('perfil:editar', 'inbox:usar')
        """), {"tid": str(seeded_tenant)})).scalar()

    assert perm_despues == perm_antes == 2, (perm_antes, perm_despues)
    # 7 (perfil) + 6 (inbox) = 13 grants, unchanged after re-run.
    assert grants_despues == grants_antes == 13, (grants_antes, grants_despues)
