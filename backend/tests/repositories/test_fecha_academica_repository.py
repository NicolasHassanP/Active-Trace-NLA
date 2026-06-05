"""
test_fecha_academica_repository.py — TDD RED/GREEN tests for C-17 FechaAcademicaRepository.

Tasks 3.3–3.6:
    3.3 RED: alta, listar con filtros (materia/cohorte/tipo/periodo), listar ordenado por fecha, aislamiento tenant.
    3.4 GREEN: FechaAcademicaRepository implementado.
    3.5 TRIANGULATE: filtros combinados, lista vacía, registros de otro tenant invisibles.
    3.6 REFACTOR: queries solo en repos.

DB real: activia_trace_test. Sin mocks.
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
async def repo_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def repo_session(repo_engine):
    """Ensure schema + enums + indexes exist and return a module-scoped session."""
    import app.models  # noqa: F401

    async with repo_engine.begin() as conn:
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

    factory = build_session_factory(repo_engine)
    session = factory()
    yield session
    try:
        await session.rollback()
        await session.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_materia(session, tid, suffix=""):
    from app.models.estructura import Materia, EstadoEstructura
    m = Materia(
        tenant_id=tid,
        codigo=f"FA_{uuid.uuid4().hex[:6]}",
        nombre=f"MatFA{suffix}",
        estado=EstadoEstructura.activa,
    )
    session.add(m)
    await session.flush()
    return m


async def _create_carrera(session, tid, suffix=""):
    from app.models.estructura import Carrera, EstadoEstructura
    c = Carrera(
        tenant_id=tid,
        codigo=f"CRFA_{uuid.uuid4().hex[:6]}",
        nombre=f"CarFA{suffix}",
        estado=EstadoEstructura.activa,
    )
    session.add(c)
    await session.flush()
    return c


async def _create_cohorte(session, tid, carrera_id, suffix=""):
    from app.models.estructura import Cohorte, EstadoEstructura
    c = Cohorte(
        tenant_id=tid,
        carrera_id=carrera_id,
        nombre=f"CohFA{suffix}2026",
        anio=2026,
        vig_desde=date(2026, 3, 1),
        estado=EstadoEstructura.activa,
    )
    session.add(c)
    await session.flush()
    return c


def _make_repo(session, tid):
    from app.repositories.fecha_academica_repository import FechaAcademicaRepository
    return FechaAcademicaRepository(session=session, tenant_id=tid)


def _new_fecha(tid, materia_id, cohorte_id, tipo="Parcial", numero=1,
               periodo="2026-1", fecha=None, titulo="Primer Parcial"):
    from app.models.academico import FechaAcademica, FechaAcademicaTipo
    return FechaAcademica(
        tenant_id=tid,
        materia_id=materia_id,
        cohorte_id=cohorte_id,
        tipo=FechaAcademicaTipo(tipo),
        numero=numero,
        periodo=periodo,
        fecha=fecha or date(2026, 5, 10),
        titulo=titulo,
    )


# ---------------------------------------------------------------------------
# Task 3.3 RED — basic CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_fecha_y_recuperar(repo_session):
    """3.3 RED: create fecha → same tenant can retrieve it."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FACRUD_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "Crud")
    car = await _create_carrera(repo_session, tid, "Crud")
    coh = await _create_cohorte(repo_session, tid, car.id, "Crud")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    fa = _new_fecha(tid, m.id, coh.id, titulo="Examen TDD")
    fa = await repo.add(fa)

    fetched = await repo.get_by_id(fa.id)
    assert fetched is not None
    assert fetched.id == fa.id
    assert fetched.tenant_id == tid
    assert fetched.titulo == "Examen TDD"

    await repo.delete(fetched)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_fecha_cross_tenant_returns_none(repo_session):
    """3.3 RED: get_by_id from another tenant returns None."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"FaA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"FaB_{tid_b.hex[:4]}")
    m = await _create_materia(repo_session, tid_a, "Cross")
    car = await _create_carrera(repo_session, tid_a, "Cross")
    coh = await _create_cohorte(repo_session, tid_a, car.id, "Cross")
    await repo_session.commit()

    repo_a = _make_repo(repo_session, tid_a)
    fa = await repo_a.add(_new_fecha(tid_a, m.id, coh.id))

    repo_b = _make_repo(repo_session, tid_b)
    fetched = await repo_b.get_by_id(fa.id)
    assert fetched is None

    await repo_a.delete(fa)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 3.3 RED — listar con filtros
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_filter_by_materia(repo_session):
    """3.3 RED: listar() filters by materia_id."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FAListM_{tid.hex[:4]}")
    m1 = await _create_materia(repo_session, tid, "M1")
    m2 = await _create_materia(repo_session, tid, "M2")
    car = await _create_carrera(repo_session, tid, "LM")
    coh = await _create_cohorte(repo_session, tid, car.id, "LM")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    fa1 = await repo.add(_new_fecha(tid, m1.id, coh.id, titulo="FA Materia 1"))
    fa2 = await repo.add(_new_fecha(tid, m2.id, coh.id, titulo="FA Materia 2"))

    results = await repo.listar(materia_id=m1.id)
    ids = {f.id for f in results}
    assert fa1.id in ids
    assert fa2.id not in ids

    await repo.delete(fa1)
    await repo.delete(fa2)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_filter_by_tipo(repo_session):
    """3.3 RED: listar() filters by tipo."""
    from app.models.academico import FechaAcademicaTipo
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FAListT_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "ListT")
    car = await _create_carrera(repo_session, tid, "ListT")
    coh = await _create_cohorte(repo_session, tid, car.id, "ListT")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    fa_parcial = await repo.add(_new_fecha(tid, m.id, coh.id, tipo="Parcial", numero=1))
    fa_tp = await repo.add(_new_fecha(tid, m.id, coh.id, tipo="TP", numero=1))

    results = await repo.listar(tipo=FechaAcademicaTipo.Parcial)
    ids = {f.id for f in results}
    assert fa_parcial.id in ids
    assert fa_tp.id not in ids

    await repo.delete(fa_parcial)
    await repo.delete(fa_tp)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_filter_by_periodo(repo_session):
    """3.3 RED: listar() filters by periodo."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FAListP_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "ListP")
    car = await _create_carrera(repo_session, tid, "ListP")
    coh = await _create_cohorte(repo_session, tid, car.id, "ListP")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    fa_2026 = await repo.add(_new_fecha(tid, m.id, coh.id, numero=1, periodo="2026-1"))
    fa_2025 = await repo.add(_new_fecha(tid, m.id, coh.id, tipo="TP", numero=1, periodo="2025-2"))

    results = await repo.listar(periodo="2026-1")
    ids = {f.id for f in results}
    assert fa_2026.id in ids
    assert fa_2025.id not in ids

    await repo.delete(fa_2026)
    await repo.delete(fa_2025)
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 3.4 GREEN — listar_calendario ordered by fecha
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_calendario_ordered_by_fecha(repo_session):
    """3.4 GREEN: listar_calendario returns fechas ordered ASC by fecha."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FACal_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "Cal")
    car = await _create_carrera(repo_session, tid, "Cal")
    coh = await _create_cohorte(repo_session, tid, car.id, "Cal")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    # Insert in reverse order
    fa_later = await repo.add(_new_fecha(tid, m.id, coh.id, tipo="Parcial", numero=1,
                                          fecha=date(2026, 9, 1), titulo="Segundo"))
    fa_earlier = await repo.add(_new_fecha(tid, m.id, coh.id, tipo="TP", numero=1,
                                            fecha=date(2026, 5, 1), titulo="Primero"))

    results = await repo.listar_calendario(m.id, coh.id)
    # Should be ordered by fecha ASC
    assert len(results) >= 2
    fechas_ids = [f.id for f in results]
    idx_earlier = fechas_ids.index(fa_earlier.id)
    idx_later = fechas_ids.index(fa_later.id)
    assert idx_earlier < idx_later, "listar_calendario must return items ordered ASC by fecha"

    await repo.delete(fa_later)
    await repo.delete(fa_earlier)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_existe_activo_para_combo_fecha(repo_session):
    """3.4 GREEN: existe_activo_para_combo checks (materia, cohorte, tipo, numero, periodo)."""
    from app.models.academico import FechaAcademicaTipo
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FaCombo_{tid.hex[:4]}")
    m = await _create_materia(repo_session, tid, "Combo")
    car = await _create_carrera(repo_session, tid, "Combo")
    coh = await _create_cohorte(repo_session, tid, car.id, "Combo")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)

    exists = await repo.existe_activo_para_combo(
        m.id, coh.id, FechaAcademicaTipo.Parcial, 1, "2026-1"
    )
    assert not exists

    fa = await repo.add(_new_fecha(tid, m.id, coh.id, tipo="Parcial", numero=1, periodo="2026-1"))
    exists = await repo.existe_activo_para_combo(
        m.id, coh.id, FechaAcademicaTipo.Parcial, 1, "2026-1"
    )
    assert exists

    await repo.delete(fa)
    exists_after = await repo.existe_activo_para_combo(
        m.id, coh.id, FechaAcademicaTipo.Parcial, 1, "2026-1"
    )
    assert not exists_after
    await repo_session.commit()


# ---------------------------------------------------------------------------
# Task 3.5 TRIANGULATE — edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_combined_filters(repo_session):
    """3.5 TRIANGULATE: listar() with multiple filters applied simultaneously."""
    from app.models.academico import FechaAcademicaTipo
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FACombined_{tid.hex[:4]}")
    m1 = await _create_materia(repo_session, tid, "Comb1")
    m2 = await _create_materia(repo_session, tid, "Comb2")
    car = await _create_carrera(repo_session, tid, "Comb")
    coh = await _create_cohorte(repo_session, tid, car.id, "Comb")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    fa_match = await repo.add(_new_fecha(tid, m1.id, coh.id, tipo="Parcial", numero=1,
                                          periodo="2026-1", titulo="Match"))
    fa_wrong_mat = await repo.add(_new_fecha(tid, m2.id, coh.id, tipo="Parcial", numero=1,
                                              periodo="2026-1", titulo="Wrong mat"))
    fa_wrong_tipo = await repo.add(_new_fecha(tid, m1.id, coh.id, tipo="TP", numero=1,
                                               periodo="2026-1", titulo="Wrong tipo"))

    results = await repo.listar(materia_id=m1.id, tipo=FechaAcademicaTipo.Parcial, periodo="2026-1")
    ids = {f.id for f in results}
    assert fa_match.id in ids
    assert fa_wrong_mat.id not in ids
    assert fa_wrong_tipo.id not in ids

    for fa in [fa_match, fa_wrong_mat, fa_wrong_tipo]:
        await repo.delete(fa)
    await repo_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_empty_results(repo_session):
    """3.5 TRIANGULATE: listar() returns empty list when no results."""
    tid = uuid.uuid4()
    await _create_tenant(repo_session, tid, f"FAEmpty_{tid.hex[:4]}")
    await repo_session.commit()

    repo = _make_repo(repo_session, tid)
    results = await repo.listar()
    assert results == []


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_tenant_isolation(repo_session):
    """3.5 TRIANGULATE: listar() never returns fechas from other tenants."""
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    await _create_tenant(repo_session, tid_a, f"FAIsolA_{tid_a.hex[:4]}")
    await _create_tenant(repo_session, tid_b, f"FAIsolB_{tid_b.hex[:4]}")
    m = await _create_materia(repo_session, tid_a, "Isol")
    car = await _create_carrera(repo_session, tid_a, "Isol")
    coh = await _create_cohorte(repo_session, tid_a, car.id, "Isol")
    await repo_session.commit()

    repo_a = _make_repo(repo_session, tid_a)
    fa = await repo_a.add(_new_fecha(tid_a, m.id, coh.id, titulo="In Tenant A"))

    repo_b = _make_repo(repo_session, tid_b)
    results_b = await repo_b.listar()
    ids_b = {f.id for f in results_b}
    assert fa.id not in ids_b

    await repo_a.delete(fa)
    await repo_session.commit()
