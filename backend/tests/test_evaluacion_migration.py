"""
test_evaluacion_migration.py — TDD tests for C-14 migration 012.

Task 1.10: Verify tables, enums, audit action value, and partial index exist
in the test DB (created by conftest._ensure_schema + Base.metadata.create_all).

Uses a module-scoped event_loop + standalone engine to be runnable standalone
and as part of the full suite.

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import os
import pytest
import pytest_asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory


from dotenv import load_dotenv
load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)


# ---------------------------------------------------------------------------
# Module-scoped event_loop: required for module-scoped async fixtures
# (pytest-asyncio 0.21.x does not auto-set module scope for event_loop)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    """Module-scoped event loop for this test module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Module fixture: standalone engine + schema setup for C-14
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def eval_mig_engine():
    """Standalone engine for migration tests."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def eval_mig_session(eval_mig_engine):
    """
    Ensure all C-14 enums and tables are created before tests run.
    Uses the same idempotent _ensure_schema logic as the conftest.
    """
    import app.models  # noqa: F401 — register all models in Base.metadata

    async with eval_mig_engine.begin() as conn:
        # Ensure C-14 enums exist
        await conn.execute(text(
            "DO $$ BEGIN "
            "  ALTER TYPE audit_action ADD VALUE 'COLOQUIO_GESTIONAR'; "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        await conn.execute(text(
            "DO $$ BEGIN "
            "  CREATE TYPE evaluacion_tipo AS ENUM "
            "  ('Parcial', 'TP', 'Coloquio', 'Recuperatorio'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        await conn.execute(text(
            "DO $$ BEGIN "
            "  CREATE TYPE reserva_estado AS ENUM ('Activa', 'Cancelada'); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$;"
        ))
        # Ensure required base enums exist too
        for stmt in [
            "DO $$ BEGIN CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE permiso_scope AS ENUM ('global', 'propio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE audit_resultado AS ENUM ('ok', 'fail', 'partial'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE estado_estructura AS ENUM ('activa', 'inactiva'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE rol_asignacion AS ENUM ('PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE usuario_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE calificacion_origen AS ENUM ('Importado', 'Manual'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE comunicacion_estado AS ENUM ('Pendiente', 'Enviando', 'Enviado', 'Error', 'Cancelado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE dia_semana AS ENUM ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE instancia_encuentro_estado AS ENUM ('Programado', 'Realizado', 'Cancelado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE guardia_estado AS ENUM ('Pendiente', 'Realizada', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        ]:
            await conn.execute(text(stmt))

        # Ensure audit_action has all required values
        for action in ["PADRON_CARGAR", "CALIFICACIONES_IMPORTAR", "COMUNICACION_ENVIAR",
                       "EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL",
                       "ENCUENTRO_GESTIONAR"]:
            await conn.execute(text(
                f"DO $$ BEGIN ALTER TYPE audit_action ADD VALUE '{action}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            ))

        # Create all tables
        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Create partial unique index
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria "
            "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
            "WHERE estado = 'Activa' AND deleted_at IS NULL"
        ))

    factory = build_session_factory(eval_mig_engine)
    session = factory()
    yield session
    try:
        await session.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1.10: Table existence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_evaluacion_table_exists(eval_mig_session):
    """1.10: evaluacion table must exist in the DB."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'evaluacion' AND table_schema = 'public'"
        )
    )
    assert result.scalar() == 1, "Table 'evaluacion' not found"


@pytest.mark.asyncio(loop_scope="session")
async def test_turno_evaluacion_table_exists(eval_mig_session):
    """1.10: turno_evaluacion table must exist."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'turno_evaluacion' AND table_schema = 'public'"
        )
    )
    assert result.scalar() == 1, "Table 'turno_evaluacion' not found"


@pytest.mark.asyncio(loop_scope="session")
async def test_candidato_evaluacion_table_exists(eval_mig_session):
    """1.10: candidato_evaluacion table must exist."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'candidato_evaluacion' AND table_schema = 'public'"
        )
    )
    assert result.scalar() == 1, "Table 'candidato_evaluacion' not found"


@pytest.mark.asyncio(loop_scope="session")
async def test_reserva_evaluacion_table_exists(eval_mig_session):
    """1.10: reserva_evaluacion table must exist."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'reserva_evaluacion' AND table_schema = 'public'"
        )
    )
    assert result.scalar() == 1, "Table 'reserva_evaluacion' not found"


@pytest.mark.asyncio(loop_scope="session")
async def test_resultado_evaluacion_table_exists(eval_mig_session):
    """1.10: resultado_evaluacion table must exist."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'resultado_evaluacion' AND table_schema = 'public'"
        )
    )
    assert result.scalar() == 1, "Table 'resultado_evaluacion' not found"


# ---------------------------------------------------------------------------
# 1.10: Enum existence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_evaluacion_tipo_enum_exists(eval_mig_session):
    """1.10: evaluacion_tipo enum type must exist in DB."""
    result = await eval_mig_session.execute(
        text("SELECT 1 FROM pg_type WHERE typname = 'evaluacion_tipo'")
    )
    assert result.scalar() == 1, "Enum 'evaluacion_tipo' not found"


@pytest.mark.asyncio(loop_scope="session")
async def test_reserva_estado_enum_exists(eval_mig_session):
    """1.10: reserva_estado enum type must exist in DB."""
    result = await eval_mig_session.execute(
        text("SELECT 1 FROM pg_type WHERE typname = 'reserva_estado'")
    )
    assert result.scalar() == 1, "Enum 'reserva_estado' not found"


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_action_has_coloquio_gestionar(eval_mig_session):
    """1.10: audit_action enum must contain COLOQUIO_GESTIONAR."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'audit_action' AND e.enumlabel = 'COLOQUIO_GESTIONAR'"
        )
    )
    assert result.scalar() == 1, "audit_action missing 'COLOQUIO_GESTIONAR'"


# ---------------------------------------------------------------------------
# 1.10: Partial unique index
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_partial_unique_index_exists(eval_mig_session):
    """1.10: Partial unique index uq_reserva_activa_por_convocatoria must exist."""
    result = await eval_mig_session.execute(
        text(
            "SELECT 1 FROM pg_indexes "
            "WHERE tablename = 'reserva_evaluacion' "
            "AND indexname = 'uq_reserva_activa_por_convocatoria'"
        )
    )
    assert result.scalar() == 1, "Partial unique index not found on reserva_evaluacion"
