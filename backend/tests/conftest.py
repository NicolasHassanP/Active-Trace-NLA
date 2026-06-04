import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import Base, build_session_factory
import app.models  # noqa: F401 — registers all models in Base.metadata for create_all
# NOTE: C-03 infrastructure discovery: models MUST be imported before create_all runs.
# The conftest must import app.models at module level, not inside test functions.
# C-05: AuditEvent imported via app.models above (registered in models/__init__.py).

load_dotenv()  # carga backend/.env antes de leer TEST_DATABASE_URL

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


async def _ensure_schema(engine) -> None:
    """
    Idempotent schema setup: create required enums if missing,
    then run create_all with checkfirst=True so it is safe to call multiple
    times even after migration tests have dropped/recreated tables.
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'tenant_estado'")
        )
        if result.scalar() is None:
            await conn.execute(
                text("CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo')")
            )
        # C-04: permiso_scope enum required by rbac models (create_type=False)
        result2 = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'permiso_scope'")
        )
        if result2.scalar() is None:
            await conn.execute(
                text("CREATE TYPE permiso_scope AS ENUM ('global', 'propio')")
            )
        # C-05: audit_action enum required by AuditEvent model (create_type=False)
        result3 = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'audit_action'")
        )
        if result3.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE audit_action AS ENUM "
                    "('IMPERSONACION_INICIO', 'IMPERSONACION_FIN', 'AUDITORIA_CONSULTA')"
                )
            )
        # C-05: audit_resultado enum required by AuditEvent model (create_type=False)
        result4 = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'audit_resultado'")
        )
        if result4.scalar() is None:
            await conn.execute(
                text("CREATE TYPE audit_resultado AS ENUM ('ok', 'fail', 'partial')")
            )
        # C-06: estado_estructura enum required by Carrera/Cohorte/Materia models (create_type=False)
        result5 = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'estado_estructura'")
        )
        if result5.scalar() is None:
            await conn.execute(
                text("CREATE TYPE estado_estructura AS ENUM ('activa', 'inactiva')")
            )
        # C-07: rol_asignacion enum required by Asignacion model (create_type=False)
        result6 = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'rol_asignacion'")
        )
        if result6.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE rol_asignacion AS ENUM "
                    "('PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS')"
                )
            )
        # C-07: usuario_estado enum required by Usuario model (create_type=False)
        result7 = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'usuario_estado'")
        )
        if result7.scalar() is None:
            await conn.execute(
                text("CREATE TYPE usuario_estado AS ENUM ('activo', 'inactivo')")
            )
        # C-09: PADRON_CARGAR added to audit_action enum in migration 007.
        # We check if the value exists first to avoid locking issues with ALTER TYPE.
        result_padron_action = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'PADRON_CARGAR'"
            )
        )
        if result_padron_action.scalar() is None:
            # Only ALTER if value doesn't exist yet (avoids locking)
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'PADRON_CARGAR'")
            )
        # C-10: CALIFICACIONES_IMPORTAR added to audit_action enum in migration 008.
        result_cal_action = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'CALIFICACIONES_IMPORTAR'"
            )
        )
        if result_cal_action.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'CALIFICACIONES_IMPORTAR'")
            )
        # C-10: calificacion_origen enum required by Calificacion model (create_type=False)
        result_cal_origen = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'calificacion_origen'")
        )
        if result_cal_origen.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE calificacion_origen AS ENUM ('Importado', 'Manual')"
                )
            )
        # C-12: comunicacion_estado enum required by Comunicacion model (create_type=False)
        result_com_estado = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'comunicacion_estado'")
        )
        if result_com_estado.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE comunicacion_estado AS ENUM "
                    "('Pendiente', 'Enviando', 'Enviado', 'Error', 'Cancelado')"
                )
            )
        # C-12: COMUNICACION_ENVIAR added to audit_action enum in migration 009.
        result_com_enviar = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'COMUNICACION_ENVIAR'"
            )
        )
        if result_com_enviar.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'COMUNICACION_ENVIAR'")
            )
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        # C-12: tenant_config UNIQUE (tenant_id, clave) — add if not present
        result_tc_uq = await conn.execute(
            text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = 'uq_tenant_config_tenant_clave_full'"
            )
        )
        if result_tc_uq.scalar() is None:
            await conn.execute(
                text(
                    "ALTER TABLE tenant_config "
                    "ADD CONSTRAINT uq_tenant_config_tenant_clave_full "
                    "UNIQUE (tenant_id, clave)"
                )
            )


@pytest_asyncio.fixture(scope="session")
async def create_tables(test_engine):
    """
    Create all registered tables once per session; drop them at the end.

    Uses checkfirst=True so it is safe even if migration tests have
    temporarily dropped and re-created tables in the same session.
    """
    await _ensure_schema(test_engine)
    yield
    async with test_engine.begin() as conn:
        from sqlalchemy import text
        # Drop dynamic test tables not tracked in Base.metadata (e.g. C-02 TenantScopedRepository tests).
        await conn.execute(text("DROP TABLE IF EXISTS test_biz_entity_v2 CASCADE"))
        # C-09: version_padron and entrada_padron are now in Base.metadata (registered in models/__init__.py)
        # and will be dropped by drop_all in the correct FK order. No explicit drop needed here.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TYPE IF EXISTS tenant_estado CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS permiso_scope CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS audit_action CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS audit_resultado CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS estado_estructura CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS rol_asignacion CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS usuario_estado CASCADE"))
        # C-10: calificacion_origen enum
        await conn.execute(text("DROP TYPE IF EXISTS calificacion_origen CASCADE"))
        # C-12: comunicacion_estado enum
        await conn.execute(text("DROP TYPE IF EXISTS comunicacion_estado CASCADE"))


@pytest_asyncio.fixture(scope="session")
async def db_session(test_engine, create_tables) -> AsyncSession:
    """
    Session-scoped async DB session.

    Shared across all tests in the session. Tests that modify data must
    clean up after themselves (delete rows) or rollback explicitly.

    IMPORTANT: If the session enters a PendingRollbackError state (e.g. from
    an IntegrityError during a test), the test that caused the error must call
    `await db_session.rollback()` before proceeding. Individual tests are
    responsible for their own error recovery.
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
