import os
import uuid as _uuid_mod
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
        # C-08: EQUIPOS_* actions added to audit_action enum in migration 010.
        for equipo_action in (
            "EQUIPOS_ASIGNACION_MASIVA",
            "EQUIPOS_CLONAR",
            "EQUIPOS_VIGENCIA_GENERAL",
        ):
            result_eq = await conn.execute(
                text(
                    "SELECT 1 FROM pg_enum e "
                    "JOIN pg_type t ON e.enumtypid = t.oid "
                    "WHERE t.typname = 'audit_action' AND e.enumlabel = :label"
                ),
                {"label": equipo_action},
            )
            if result_eq.scalar() is None:
                await conn.execute(
                    text(f"ALTER TYPE audit_action ADD VALUE '{equipo_action}'")
                )
        # C-13: ENCUENTRO_GESTIONAR added to audit_action enum in migration 011.
        result_enc_action = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'ENCUENTRO_GESTIONAR'"
            )
        )
        if result_enc_action.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'ENCUENTRO_GESTIONAR'")
            )
        # C-13: dia_semana enum required by SlotEncuentro and Guardia (create_type=False)
        result_dia = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'dia_semana'")
        )
        if result_dia.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE dia_semana AS ENUM "
                    "('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')"
                )
            )
        # C-13: instancia_encuentro_estado enum
        result_inst_est = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'instancia_encuentro_estado'")
        )
        if result_inst_est.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE instancia_encuentro_estado AS ENUM "
                    "('Programado', 'Realizado', 'Cancelado')"
                )
            )
        # C-13: guardia_estado enum
        result_grd_est = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'guardia_estado'")
        )
        if result_grd_est.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE guardia_estado AS ENUM "
                    "('Pendiente', 'Realizada', 'Cancelada')"
                )
            )
        # C-14: COLOQUIO_GESTIONAR added to audit_action enum in migration 012.
        result_col_action = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'COLOQUIO_GESTIONAR'"
            )
        )
        if result_col_action.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'COLOQUIO_GESTIONAR'")
            )
        # C-14: evaluacion_tipo enum required by Evaluacion model (create_type=False)
        result_eval_tipo = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'evaluacion_tipo'")
        )
        if result_eval_tipo.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE evaluacion_tipo AS ENUM "
                    "('Parcial', 'TP', 'Coloquio', 'Recuperatorio')"
                )
            )
        # C-14: reserva_estado enum required by ReservaEvaluacion model (create_type=False)
        result_reserva_estado = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'reserva_estado'")
        )
        if result_reserva_estado.scalar() is None:
            await conn.execute(
                text("CREATE TYPE reserva_estado AS ENUM ('Activa', 'Cancelada')")
            )
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        # C-20: genero column on usuario (added by migration 016, after create_all so usuario exists)
        await conn.execute(text(
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"
        ))
        # C-20: indexes not defined in SQLAlchemy models (defined in migration)
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_hilo_participantes_tenant_usuario "
            "ON hilo_participantes (tenant_id, usuario_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_mensajes_tenant_hilo_at "
            "ON mensajes (tenant_id, hilo_id, created_at)"
        ))
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
        # C-14: partial unique index on reserva_evaluacion (one active reservation per convocatoria)
        result_reserva_idx = await conn.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'reserva_evaluacion' "
                "AND indexname = 'uq_reserva_activa_por_convocatoria'"
            )
        )
        if result_reserva_idx.scalar() is None:
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX uq_reserva_activa_por_convocatoria "
                    "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
                    "WHERE estado = 'Activa' AND deleted_at IS NULL"
                )
            )

        # C-15: aviso enums
        result_aviso_alcance = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'aviso_alcance'")
        )
        if result_aviso_alcance.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE aviso_alcance AS ENUM "
                    "('Global', 'PorMateria', 'PorCohorte', 'PorRol')"
                )
            )
        result_aviso_sev = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'aviso_severidad'")
        )
        if result_aviso_sev.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE aviso_severidad AS ENUM "
                    "('Info', 'Advertencia', 'Critico')"
                )
            )
        result_aviso_pub = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'AVISO_PUBLICAR'"
            )
        )
        if result_aviso_pub.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'AVISO_PUBLICAR'")
            )

        # C-16: tarea enum and audit actions
        result_tarea_estado = await conn.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'tarea_estado'")
        )
        if result_tarea_estado.scalar() is None:
            await conn.execute(
                text(
                    "CREATE TYPE tarea_estado AS ENUM "
                    "('Pendiente', 'EnProgreso', 'Resuelta', 'Cancelada')"
                )
            )
        for tarea_action in ("TAREA_ASIGNAR", "TAREA_DELEGAR", "TAREA_CAMBIAR_ESTADO"):
            result_ta = await conn.execute(
                text(
                    "SELECT 1 FROM pg_enum e "
                    "JOIN pg_type t ON e.enumtypid = t.oid "
                    "WHERE t.typname = 'audit_action' AND e.enumlabel = :label"
                ),
                {"label": tarea_action},
            )
            if result_ta.scalar() is None:
                await conn.execute(
                    text(f"ALTER TYPE audit_action ADD VALUE '{tarea_action}'")
                )
        # C-20: PERFIL_EDITAR added to audit_action enum in migration 016.
        result_perfil_editar = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'PERFIL_EDITAR'"
            )
        )
        if result_perfil_editar.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'PERFIL_EDITAR'")
            )
        # C-06 audit gap fix: ESTRUCTURA_GESTIONAR added to audit_action enum in migration 021.
        result_estr_action = await conn.execute(
            text(
                "SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'audit_action' AND e.enumlabel = 'ESTRUCTURA_GESTIONAR'"
            )
        )
        if result_estr_action.scalar() is None:
            await conn.execute(
                text("ALTER TYPE audit_action ADD VALUE 'ESTRUCTURA_GESTIONAR'")
            )
        # C-17: programa/fecha_academica audit actions
        for acad_action in ("PROGRAMA_GESTIONAR", "FECHA_ACADEMICA_GESTIONAR"):
            result_acad = await conn.execute(
                text(
                    "SELECT 1 FROM pg_enum e "
                    "JOIN pg_type t ON e.enumtypid = t.oid "
                    "WHERE t.typname = 'audit_action' AND e.enumlabel = :label"
                ),
                {"label": acad_action},
            )
            if result_acad.scalar() is None:
                await conn.execute(
                    text(f"ALTER TYPE audit_action ADD VALUE '{acad_action}'")
                )
        # C-19: umbral_materia scope global — cohorte_id + nullable asignacion_id + new indexes
        await conn.execute(text(
            "ALTER TABLE umbral_materia ADD COLUMN IF NOT EXISTS cohorte_id UUID "
            "REFERENCES cohorte(id) ON DELETE RESTRICT"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_um_cohorte_id ON umbral_materia (cohorte_id)"
        ))
        # Make asignacion_id nullable (idempotent)
        await conn.execute(text(
            "ALTER TABLE umbral_materia ALTER COLUMN asignacion_id DROP NOT NULL"
        ))
        # Drop old unique index (if exists)
        await conn.execute(text(
            "DROP INDEX IF EXISTS uq_um_asignacion_materia"
        ))
        # Create two partial unique indexes (idempotent via IF NOT EXISTS)
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_um_default_materia_cohorte "
            "ON umbral_materia(tenant_id, materia_id, cohorte_id) "
            "WHERE asignacion_id IS NULL AND deleted_at IS NULL"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_um_asignacion_override "
            "ON umbral_materia(tenant_id, asignacion_id, materia_id) "
            "WHERE asignacion_id IS NOT NULL AND deleted_at IS NULL"
        ))

        # C-17: partial unique indexes for programa_materia and fecha_academica
        result_pm_idx = await conn.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'programa_materia' "
                "AND indexname = 'ux_programa_materia_tenant_combo'"
            )
        )
        if result_pm_idx.scalar() is None:
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_programa_materia_tenant_combo "
                    "ON programa_materia (tenant_id, materia_id, carrera_id, cohorte_id) "
                    "WHERE deleted_at IS NULL"
                )
            )
        result_fa_idx = await conn.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'fecha_academica' "
                "AND indexname = 'ux_fecha_academica_tenant_combo'"
            )
        )
        if result_fa_idx.scalar() is None:
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ux_fecha_academica_tenant_combo "
                    "ON fecha_academica (tenant_id, materia_id, cohorte_id, tipo, numero, periodo) "
                    "WHERE deleted_at IS NULL"
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
        # C-02: test_notas may have been left by test_base_repository tests
        await conn.execute(text("DROP TABLE IF EXISTS test_notas CASCADE"))
        # C-09: version_padron and entrada_padron are now in Base.metadata (registered in models/__init__.py)
        # and will be dropped by drop_all in the correct FK order. No explicit drop needed here.
        # C-20: mensajería tables (FK order: participantes → mensajes → hilos)
        await conn.execute(text("DROP TABLE IF EXISTS hilo_participantes CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS mensajes CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS hilos_mensaje CASCADE"))
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
        # C-13: encuentros/guardias enums
        await conn.execute(text("DROP TYPE IF EXISTS dia_semana CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS instancia_encuentro_estado CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS guardia_estado CASCADE"))
        # C-14: evaluacion/coloquios enums
        await conn.execute(text("DROP TYPE IF EXISTS evaluacion_tipo CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS reserva_estado CASCADE"))
        # C-15: aviso enums
        await conn.execute(text("DROP TYPE IF EXISTS aviso_alcance CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS aviso_severidad CASCADE"))
        # C-16: tarea enum
        await conn.execute(text("DROP TYPE IF EXISTS tarea_estado CASCADE"))
        # C-17: no new enum (reuses evaluacion_tipo from C-14)


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


# ---------------------------------------------------------------------------
# Test-only helper: delete audit_event rows for a tenant without tripping the
# immutability trigger (trg_audit_event_immutable).
#
# Strategy: audit_event is append-only in production (D3 trigger blocks DELETE
# and UPDATE at the DB level).  During test teardown we MUST be able to remove
# per-tenant data so we can subsequently DELETE the tenant row (the FK is
# ON DELETE RESTRICT).  Relying solely on the session-scoped drop_all is not
# enough because individual module fixtures clean up their tenants mid-session.
#
# We temporarily disable the row-level trigger for the duration of the DELETE,
# then immediately re-enable it.  The trigger still exists and still guards
# production code; this bypass is test-infrastructure only and scoped to the
# DISABLE/ENABLE block.
#
# Usage (in any test module teardown):
#   await delete_audit_events_for_tenant(session, tenant_id)
#   # then continue with DELETE FROM tenants ...
# ---------------------------------------------------------------------------

async def delete_audit_events_for_tenant(session: AsyncSession, tenant_id) -> None:
    """Remove audit_event rows for *tenant_id* while bypassing the immutability trigger.

    The trigger ``trg_audit_event_immutable`` is a row-level BEFORE trigger, so it
    fires on every DELETE row.  DISABLE/ENABLE TRIGGER is a DDL statement that
    bypasses it within this block.  This is safe in tests because the table is
    dropped entirely at end of session (``create_tables`` teardown).

    The trigger is only installed when alembic migrations run (migration 004).
    The conftest ``_ensure_schema`` uses ``create_all`` which does NOT install
    triggers.  We check for the trigger's existence before disabling it so that
    this helper works in both cases (trigger present or absent).

    Args:
        session: The active AsyncSession (shared, session-scoped).
        tenant_id: UUID of the tenant whose audit_event rows should be removed.
    """
    from sqlalchemy import text

    tid = str(tenant_id)

    # Check whether the trigger is installed (it is only installed by alembic migration 004,
    # not by create_all used in _ensure_schema).
    result = await session.execute(
        text(
            "SELECT 1 FROM pg_trigger t "
            "JOIN pg_class c ON t.tgrelid = c.oid "
            "WHERE t.tgname = 'trg_audit_event_immutable' AND c.relname = 'audit_event'"
        )
    )
    trigger_exists = result.scalar() is not None

    if trigger_exists:
        await session.execute(text("ALTER TABLE audit_event DISABLE TRIGGER trg_audit_event_immutable"))
    await session.execute(
        text("DELETE FROM audit_event WHERE tenant_id = :tid"),
        {"tid": tid},
    )
    if trigger_exists:
        await session.execute(text("ALTER TABLE audit_event ENABLE TRIGGER trg_audit_event_immutable"))


# ---------------------------------------------------------------------------
# C-28 invariant helper: create a Usuario with a real AuthIdentity FK parent.
#
# WHY this helper exists
# ----------------------
# C-28 established the invariant: auth_identity_id ≠ usuario.id.
# `usuario.auth_identity_id` has a REAL FK → auth_identities.id.
# Any test that sets auth_identity_id to a random UUID (without creating the
# corresponding AuthIdentity row) gets a FK violation at INSERT time.
# Additionally, `resolve_domain_user_id` (dependencies.py) looks up the domain
# user by `tenant_id + auth_identity_id + deleted_at IS NULL`, so if the
# auth_identity_id does not match a real AuthIdentity row the endpoint returns
# 500 "Usuario de dominio no encontrado".
#
# This helper is THE canonical way to create a domain user in endpoint tests.
# It always guarantees auth_identity_id ≠ usuario.id (they are distinct UUIDs).
#
# USAGE:
#   usuario = await create_usuario_con_identidad(session, tid)
#   token   = _make_jwt(tid, usuario.auth_identity_id, ["SOME_ROL"])
#   # use usuario.id wherever a domain FK (e.g. remitente_id) is needed
# ---------------------------------------------------------------------------

async def create_usuario_con_identidad(
    session: AsyncSession,
    tenant_id,
    *,
    email: str | None = None,
    nombre: str = "Test",
    apellidos: str = "User",
    roles: list | None = None,
    **extra_campos,
):
    """
    Create an AuthIdentity row and a linked Usuario in a single flush.

    C-28 invariant: auth_identity_id ≠ usuario.id — both are generated
    independently as separate UUIDs by this helper.

    The caller MUST use ``usuario.auth_identity_id`` as the JWT ``sub``
    (not ``usuario.id``) so that ``resolve_domain_user_id`` resolves correctly.

    Args:
        session:     Active AsyncSession (shared or module-scoped).
        tenant_id:   UUID of the tenant to scope both rows.
        email:       Optional email string (auto-generated if omitted).
        nombre:      First name for the Usuario row.
        apellidos:   Last name for the Usuario row.
        roles:       Roles list stored in AuthIdentity snapshot (default []).
        **extra_campos: Additional keyword args forwarded to the Usuario
                     constructor (e.g. estado, legajo, banco).

    Returns:
        The Usuario instance after flush (has .id and .auth_identity_id set).
    """
    from app.models.auth import AuthIdentity
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash, hash_password

    if email is None:
        email = f"testuser_{_uuid_mod.uuid4().hex[:8]}@conftest.test"

    auth = AuthIdentity(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        password_hash=hash_password("TestPass1!"),
        roles=roles or [],
        is_active=True,
    )
    session.add(auth)
    await session.flush()  # auth.id is now available

    usuario_kwargs = dict(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        nombre=nombre,
        apellidos=apellidos,
        estado=UsuarioEstado.activo,
        auth_identity_id=auth.id,  # C-28: DISTINCT from usuario.id
    )
    usuario_kwargs.update(extra_campos)

    usuario = Usuario(**usuario_kwargs)
    session.add(usuario)
    await session.flush()  # usuario.id is now available

    return usuario
