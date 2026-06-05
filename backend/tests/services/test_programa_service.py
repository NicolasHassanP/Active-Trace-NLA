"""
test_programa_service.py — TDD RED/GREEN tests for C-17 ProgramaService + FechaAcademicaService.

Tasks 5.4–5.5:
    5.4 RED+GREEN: services orquestan repos + audit.
    5.5 TRIANGULATE: alta duplicada → 409; baja → soft delete + audit; re-alta tras baja permitida.

Uses real DB (activia_trace_test). Sin mocks de DB.
"""
import asyncio
import os
import uuid
from datetime import date

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory

load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def svc_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def svc_session(svc_engine):
    import app.models  # noqa: F401

    async with svc_engine.begin() as conn:
        for stmt in [
            "DO $$ BEGIN CREATE TYPE tenant_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE permiso_scope AS ENUM ('global', 'propio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE audit_action AS ENUM ('IMPERSONACION_INICIO', 'IMPERSONACION_FIN', 'AUDITORIA_CONSULTA'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE audit_resultado AS ENUM ('ok', 'fail', 'partial'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE estado_estructura AS ENUM ('activa', 'inactiva'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE rol_asignacion AS ENUM ('PROFESOR', 'TUTOR', 'COORDINADOR', 'NEXO', 'ADMIN', 'FINANZAS'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE usuario_estado AS ENUM ('activo', 'inactivo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE calificacion_origen AS ENUM ('Importado', 'Manual'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE comunicacion_estado AS ENUM ('Pendiente', 'Enviando', 'Enviado', 'Error', 'Cancelado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE dia_semana AS ENUM ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE instancia_encuentro_estado AS ENUM ('Programado', 'Realizado', 'Cancelado'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE guardia_estado AS ENUM ('Pendiente', 'Realizada', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE evaluacion_tipo AS ENUM ('Parcial', 'TP', 'Coloquio', 'Recuperatorio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE reserva_estado AS ENUM ('Activa', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE aviso_alcance AS ENUM ('Global', 'PorMateria', 'PorCohorte', 'PorRol'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE aviso_severidad AS ENUM ('Info', 'Advertencia', 'Critico'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE tarea_estado AS ENUM ('Pendiente', 'EnProgreso', 'Resuelta', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        ]:
            await conn.execute(text(stmt))

        for action in [
            "PADRON_CARGAR", "CALIFICACIONES_IMPORTAR", "COMUNICACION_ENVIAR",
            "EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL",
            "ENCUENTRO_GESTIONAR", "COLOQUIO_GESTIONAR", "AVISO_PUBLICAR",
            "TAREA_ASIGNAR", "TAREA_DELEGAR", "TAREA_CAMBIAR_ESTADO",
            "PROGRAMA_GESTIONAR", "FECHA_ACADEMICA_GESTIONAR",
        ]:
            await conn.execute(text(
                f"DO $$ BEGIN ALTER TYPE audit_action ADD VALUE '{action}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            ))

        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        for idx_sql in [
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) WHERE estado = 'Activa' AND deleted_at IS NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_programa_materia_tenant_combo ON programa_materia (tenant_id, materia_id, carrera_id, cohorte_id) WHERE deleted_at IS NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_fecha_academica_tenant_combo ON fecha_academica (tenant_id, materia_id, cohorte_id, tipo, numero, periodo) WHERE deleted_at IS NULL",
        ]:
            await conn.execute(text(idx_sql))

    factory = build_session_factory(svc_engine)
    session = factory()
    yield session
    try:
        await session.rollback()
        await session.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_materia(session, tid, suffix=""):
    from app.models.estructura import Materia, EstadoEstructura
    m = Materia(tenant_id=tid, codigo=f"SV_{uuid.uuid4().hex[:6]}",
                nombre=f"MatSvc{suffix}", estado=EstadoEstructura.activa)
    session.add(m)
    await session.flush()
    return m


async def _create_carrera(session, tid, suffix=""):
    from app.models.estructura import Carrera, EstadoEstructura
    c = Carrera(tenant_id=tid, codigo=f"CRS_{uuid.uuid4().hex[:6]}",
                nombre=f"CarSvc{suffix}", estado=EstadoEstructura.activa)
    session.add(c)
    await session.flush()
    return c


async def _create_cohorte(session, tid, carrera_id, suffix=""):
    from app.models.estructura import Cohorte, EstadoEstructura
    c = Cohorte(tenant_id=tid, carrera_id=carrera_id,
                nombre=f"CohSvc{suffix}", anio=2026,
                vig_desde=date(2026, 3, 1), estado=EstadoEstructura.activa)
    session.add(c)
    await session.flush()
    return c


def _make_current_user(tid):
    from app.core.dependencies import CurrentUser
    return CurrentUser(user_id=uuid.uuid4(), tenant_id=tid, roles=["ADMIN"])


def _make_programa_svc(session, tid):
    from app.repositories.programa_repository import ProgramaMateriaRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.programa_service import ProgramaService
    return ProgramaService(
        programa_repo=ProgramaMateriaRepository(session=session, tenant_id=tid),
        audit_repo=AuditRepository(session=session, tenant_id=tid),
    )


def _make_fecha_svc(session, tid):
    from app.repositories.fecha_academica_repository import FechaAcademicaRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.fecha_academica_service import FechaAcademicaService
    return FechaAcademicaService(
        fecha_repo=FechaAcademicaRepository(session=session, tenant_id=tid),
        audit_repo=AuditRepository(session=session, tenant_id=tid),
    )


# ---------------------------------------------------------------------------
# Task 5.4 RED+GREEN — ProgramaService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_programa_service_crear(svc_session):
    """5.4 RED+GREEN: ProgramaService.crear persists programa and registers audit."""
    from app.schemas.academico import ProgramaCreate
    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcProg_{tid.hex[:4]}")
    m = await _create_materia(svc_session, tid, "Crear")
    car = await _create_carrera(svc_session, tid, "Crear")
    coh = await _create_cohorte(svc_session, tid, car.id, "Crear")
    await svc_session.commit()

    svc = _make_programa_svc(svc_session, tid)
    current_user = _make_current_user(tid)

    payload = ProgramaCreate(
        materia_id=m.id,
        carrera_id=car.id,
        cohorte_id=coh.id,
        titulo="Programa de Matemáticas",
        referencia_archivo="blob://store/math-001",
    )
    result = await svc.crear(payload, current_user)
    assert result.id is not None
    assert result.titulo == "Programa de Matemáticas"
    assert result.referencia_archivo == "blob://store/math-001"

    # Cleanup
    from app.repositories.programa_repository import ProgramaMateriaRepository
    repo = ProgramaMateriaRepository(session=svc_session, tenant_id=tid)
    prog = await repo.get_by_id(result.id)
    if prog:
        await repo.delete(prog)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_programa_service_duplicado_raises_409(svc_session):
    """5.5 TRIANGULATE: alta duplicada raises ProgramaConflictError (→ 409)."""
    from app.schemas.academico import ProgramaCreate
    from app.services.programa_service import ProgramaConflictError
    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcDup_{tid.hex[:4]}")
    m = await _create_materia(svc_session, tid, "Dup")
    car = await _create_carrera(svc_session, tid, "Dup")
    coh = await _create_cohorte(svc_session, tid, car.id, "Dup")
    await svc_session.commit()

    svc = _make_programa_svc(svc_session, tid)
    current_user = _make_current_user(tid)

    payload = ProgramaCreate(
        materia_id=m.id, carrera_id=car.id, cohorte_id=coh.id,
        titulo="Prog", referencia_archivo="blob://1",
    )
    result = await svc.crear(payload, current_user)

    with pytest.raises(ProgramaConflictError):
        await svc.crear(payload, current_user)

    from app.repositories.programa_repository import ProgramaMateriaRepository
    repo = ProgramaMateriaRepository(session=svc_session, tenant_id=tid)
    prog = await repo.get_by_id(result.id)
    if prog:
        await repo.delete(prog)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_programa_service_baja(svc_session):
    """5.5 TRIANGULATE: baja → soft delete + audit; re-alta after baja → allowed."""
    from app.schemas.academico import ProgramaCreate
    from app.services.programa_service import ProgramaNotFoundError
    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcBaja_{tid.hex[:4]}")
    m = await _create_materia(svc_session, tid, "Baja")
    car = await _create_carrera(svc_session, tid, "Baja")
    coh = await _create_cohorte(svc_session, tid, car.id, "Baja")
    await svc_session.commit()

    svc = _make_programa_svc(svc_session, tid)
    current_user = _make_current_user(tid)

    payload = ProgramaCreate(
        materia_id=m.id, carrera_id=car.id, cohorte_id=coh.id,
        titulo="Prog Baja", referencia_archivo="blob://baja",
    )
    result = await svc.crear(payload, current_user)
    prog_id = result.id

    # Dar de baja
    await svc.eliminar(prog_id, current_user)

    # After baja, get_by_id returns None
    from app.repositories.programa_repository import ProgramaMateriaRepository
    repo = ProgramaMateriaRepository(session=svc_session, tenant_id=tid)
    fetched = await repo.get_by_id(prog_id)
    assert fetched is None  # soft-deleted

    # Re-alta should succeed
    result2 = await svc.crear(payload, current_user)
    assert result2.id != prog_id  # New ID

    prog2 = await repo.get_by_id(result2.id)
    if prog2:
        await repo.delete(prog2)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# Task 5.4 RED+GREEN — FechaAcademicaService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_fecha_academica_service_crear(svc_session):
    """5.4 RED+GREEN: FechaAcademicaService.crear persists fecha and registers audit."""
    from app.schemas.academico import FechaAcademicaCreate
    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcFA_{tid.hex[:4]}")
    m = await _create_materia(svc_session, tid, "FA")
    car = await _create_carrera(svc_session, tid, "FA")
    coh = await _create_cohorte(svc_session, tid, car.id, "FA")
    await svc_session.commit()

    svc = _make_fecha_svc(svc_session, tid)
    current_user = _make_current_user(tid)

    payload = FechaAcademicaCreate(
        materia_id=m.id, cohorte_id=coh.id,
        tipo="Parcial", numero=1, periodo="2026-1",
        fecha=date(2026, 5, 10), titulo="Primer Parcial",
    )
    result = await svc.crear(payload, current_user)
    assert result.id is not None
    assert result.titulo == "Primer Parcial"

    from app.repositories.fecha_academica_repository import FechaAcademicaRepository
    repo = FechaAcademicaRepository(session=svc_session, tenant_id=tid)
    fa = await repo.get_by_id(result.id)
    if fa:
        await repo.delete(fa)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_fecha_academica_service_duplicado_raises_409(svc_session):
    """5.5 TRIANGULATE: alta duplicada raises FechaAcademicaConflictError (→ 409)."""
    from app.schemas.academico import FechaAcademicaCreate
    from app.services.fecha_academica_service import FechaAcademicaConflictError
    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcFADup_{tid.hex[:4]}")
    m = await _create_materia(svc_session, tid, "FADup")
    car = await _create_carrera(svc_session, tid, "FADup")
    coh = await _create_cohorte(svc_session, tid, car.id, "FADup")
    await svc_session.commit()

    svc = _make_fecha_svc(svc_session, tid)
    current_user = _make_current_user(tid)

    payload = FechaAcademicaCreate(
        materia_id=m.id, cohorte_id=coh.id, tipo="Parcial",
        numero=1, periodo="2026-1", fecha=date(2026, 5, 10), titulo="Test",
    )
    result = await svc.crear(payload, current_user)

    with pytest.raises(FechaAcademicaConflictError):
        await svc.crear(payload, current_user)

    from app.repositories.fecha_academica_repository import FechaAcademicaRepository
    repo = FechaAcademicaRepository(session=svc_session, tenant_id=tid)
    fa = await repo.get_by_id(result.id)
    if fa:
        await repo.delete(fa)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_fecha_academica_service_editar(svc_session):
    """5.5 TRIANGULATE: editar updates fecha and titulo."""
    from app.schemas.academico import FechaAcademicaCreate, FechaAcademicaUpdate
    tid = uuid.uuid4()
    await _create_tenant(svc_session, tid, f"SvcFAEd_{tid.hex[:4]}")
    m = await _create_materia(svc_session, tid, "FAEd")
    car = await _create_carrera(svc_session, tid, "FAEd")
    coh = await _create_cohorte(svc_session, tid, car.id, "FAEd")
    await svc_session.commit()

    svc = _make_fecha_svc(svc_session, tid)
    current_user = _make_current_user(tid)

    payload = FechaAcademicaCreate(
        materia_id=m.id, cohorte_id=coh.id, tipo="TP",
        numero=1, periodo="2026-1", fecha=date(2026, 5, 10), titulo="TP Original",
    )
    result = await svc.crear(payload, current_user)

    update = FechaAcademicaUpdate(titulo="TP Actualizado", fecha=date(2026, 5, 20))
    updated = await svc.editar(result.id, update, current_user)
    assert updated.titulo == "TP Actualizado"
    assert updated.fecha == date(2026, 5, 20)

    from app.repositories.fecha_academica_repository import FechaAcademicaRepository
    repo = FechaAcademicaRepository(session=svc_session, tenant_id=tid)
    fa = await repo.get_by_id(result.id)
    if fa:
        await repo.delete(fa)
    await svc_session.commit()
