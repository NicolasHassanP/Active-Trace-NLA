"""
test_evaluacion_repositories.py — TDD tests for C-14 evaluacion repositories.

Tasks 2.1–2.5:
    2.1 EvaluacionRepository: CRUD + listar_con_metricas (derivado, no denormalizado).
    2.2 TurnoEvaluacionRepository: alta de turnos, get_for_update, conteo reservas activas.
    2.3 CandidatoEvaluacionRepository: import idempotente, existencia de candidato.
    2.4 ReservaEvaluacionRepository: alta, cancelación, conteo activas.
    2.5 ResultadoEvaluacionRepository: upsert, consulta consolidada, consulta propio alumno.

RED → GREEN: write tests referencing production code that doesn't exist yet.
TRIANGULATE: at least 2 test cases per behavior.

DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import build_session_factory


import os
from dotenv import load_dotenv
load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
)


# ---------------------------------------------------------------------------
# Module-scoped event_loop + engine
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def eval_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def eval_session(eval_engine):
    """Create all tables and return a session."""
    import app.models  # noqa: F401

    async with eval_engine.begin() as conn:
        # Ensure all required enums
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
            "DO $$ BEGIN CREATE TYPE evaluacion_tipo AS ENUM ('Parcial', 'TP', 'Coloquio', 'Recuperatorio'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
            "DO $$ BEGIN CREATE TYPE reserva_estado AS ENUM ('Activa', 'Cancelada'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        ]:
            await conn.execute(text(stmt))

        for action in ["PADRON_CARGAR", "CALIFICACIONES_IMPORTAR", "COMUNICACION_ENVIAR",
                       "EQUIPOS_ASIGNACION_MASIVA", "EQUIPOS_CLONAR", "EQUIPOS_VIGENCIA_GENERAL",
                       "ENCUENTRO_GESTIONAR", "COLOQUIO_GESTIONAR"]:
            await conn.execute(text(
                f"DO $$ BEGIN ALTER TYPE audit_action ADD VALUE '{action}'; "
                "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            ))

        from app.core.database import Base
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Partial unique index
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria "
            "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
            "WHERE estado = 'Activa' AND deleted_at IS NULL"
        ))

    factory = build_session_factory(eval_engine)
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

def _make_tenant_id() -> uuid.UUID:
    return uuid.uuid4()


async def _create_tenant(session, tid: uuid.UUID, name: str):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_estructura(session, tid: uuid.UUID):
    """Create minimal academic structure for a tenant."""
    from app.models.estructura import Carrera, Cohorte, Materia, EstadoEstructura
    car = Carrera(tenant_id=tid, codigo=f"C_{uuid.uuid4().hex[:4]}", nombre="Carrera", estado=EstadoEstructura.activa)
    mat = Materia(tenant_id=tid, codigo=f"M_{uuid.uuid4().hex[:4]}", nombre="Materia", estado=EstadoEstructura.activa)
    session.add(car)
    session.add(mat)
    await session.flush()
    coh = Cohorte(tenant_id=tid, carrera_id=car.id, nombre="Coh", anio=2026,
                  vig_desde=date.today(), estado=EstadoEstructura.activa)
    session.add(coh)
    await session.flush()
    return car, mat, coh


async def _create_usuario(session, tid: uuid.UUID, suffix: str):
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"eval_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    return u


# ---------------------------------------------------------------------------
# 2.1: EvaluacionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_evaluacion_repo_add_and_get(eval_session):
    """2.1 RED: add Evaluacion and retrieve by id within same tenant."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import EvaluacionRepository

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"EvalT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)

    repo = EvaluacionRepository(session=eval_session, tenant_id=tid)
    ev = Evaluacion(
        materia_id=mat.id, cohorte_id=coh.id,
        tipo=EvaluacionTipo.Coloquio, instancia="1er Parcial", dias_disponibles=7,
    )
    saved = await repo.add(ev)
    assert saved.id is not None
    assert saved.tenant_id == tid
    assert saved.cerrada is False

    fetched = await repo.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.instancia == "1er Parcial"

    # Cleanup
    await repo.delete(saved)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_evaluacion_repo_tenant_isolation(eval_session):
    """2.1 TRIANGULATE: Tenant A evaluacion not visible in Tenant B."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import EvaluacionRepository

    tid_a = _make_tenant_id()
    tid_b = _make_tenant_id()
    await _create_tenant(eval_session, tid_a, f"TenA_{tid_a.hex[:4]}")
    await _create_tenant(eval_session, tid_b, f"TenB_{tid_b.hex[:4]}")
    _, mat_a, coh_a = await _create_estructura(eval_session, tid_a)
    _, mat_b, coh_b = await _create_estructura(eval_session, tid_b)

    repo_a = EvaluacionRepository(session=eval_session, tenant_id=tid_a)
    repo_b = EvaluacionRepository(session=eval_session, tenant_id=tid_b)

    ev_a = Evaluacion(
        materia_id=mat_a.id, cohorte_id=coh_a.id,
        tipo=EvaluacionTipo.Coloquio, instancia="Tenant A eval",
    )
    saved_a = await repo_a.add(ev_a)

    # Tenant B repo should not see Tenant A evaluacion
    not_visible = await repo_b.get_by_id(saved_a.id)
    assert not_visible is None

    # Cleanup
    await repo_a.delete(saved_a)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_evaluacion_repo_listar_con_metricas(eval_session):
    """2.1: listar_con_metricas returns convocados/reservas_activas/cupos_libres derived."""
    from app.models.evaluacion import (
        CandidatoEvaluacion, Evaluacion, EvaluacionTipo,
        ReservaEvaluacion, ReservaEstado, TurnoEvaluacion,
    )
    from app.repositories.evaluacion_repository import EvaluacionRepository

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"MetricT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al1 = await _create_usuario(eval_session, tid, "m_al1")
    al2 = await _create_usuario(eval_session, tid, "m_al2")

    repo = EvaluacionRepository(session=eval_session, tenant_id=tid)
    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="Metricas", dias_disponibles=5)
    ev = await repo.add(ev)

    # Add turno
    turno = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 9, 1), cupo_total=10)
    eval_session.add(turno)
    await eval_session.flush()  # get turno.id

    # Add 2 candidatos
    c1 = CandidatoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, alumno_id=al1.id)
    c2 = CandidatoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, alumno_id=al2.id)
    eval_session.add(c1)
    eval_session.add(c2)
    await eval_session.flush()  # get c1.id, c2.id

    # Add 1 reserva activa
    r1 = ReservaEvaluacion(tenant_id=tid, turno_id=turno.id, evaluacion_id=ev.id,
                           alumno_id=al1.id, estado=ReservaEstado.Activa)
    eval_session.add(r1)

    await eval_session.commit()
    await eval_session.refresh(turno)
    await eval_session.refresh(c1)
    await eval_session.refresh(c2)
    await eval_session.refresh(r1)

    metricas_list = await repo.listar_con_metricas()
    ev_metrics = next((m for m in metricas_list if m["id"] == ev.id), None)
    assert ev_metrics is not None
    assert ev_metrics["convocados"] == 2
    assert ev_metrics["reservas_activas"] == 1
    assert ev_metrics["cupos_libres"] == 9  # 10 - 1 activa

    # Cleanup
    await eval_session.delete(r1)
    await eval_session.delete(c1)
    await eval_session.delete(c2)
    await eval_session.delete(turno)
    await repo.delete(ev)
    await eval_session.commit()


# ---------------------------------------------------------------------------
# 2.2: TurnoEvaluacionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_turno_repo_add_and_list_by_evaluacion(eval_session):
    """2.2 RED: add turnos and list by evaluacion_id."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, TurnoEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"TurnoT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_turno = TurnoEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="Turnos test")
    ev = await repo_ev.add(ev)

    from app.models.evaluacion import TurnoEvaluacion
    t1 = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 10, 1), cupo_total=5)
    t2 = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 10, 2), cupo_total=8)
    eval_session.add(t1)
    eval_session.add(t2)
    await eval_session.commit()
    await eval_session.refresh(t1)
    await eval_session.refresh(t2)

    turnos = await repo_turno.list_by_evaluacion(ev.id)
    assert len(turnos) == 2
    cupos = {t.cupo_total for t in turnos}
    assert cupos == {5, 8}

    # Cleanup
    await eval_session.delete(t1)
    await eval_session.delete(t2)
    await repo_ev.delete(ev)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_turno_repo_get_for_update_locks_row(eval_session):
    """2.2 TRIANGULATE: get_for_update returns the turno (lock tested via integration)."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo, TurnoEvaluacion
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, TurnoEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"LockT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_turno = TurnoEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.TP, instancia="Lock test")
    ev = await repo_ev.add(ev)

    t = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 11, 1), cupo_total=3)
    eval_session.add(t)
    await eval_session.commit()
    await eval_session.refresh(t)

    locked = await repo_turno.get_for_update(t.id)
    assert locked is not None
    assert locked.cupo_total == 3

    # Cleanup
    await eval_session.rollback()
    await eval_session.delete(t)
    await repo_ev.delete(ev)
    await eval_session.commit()


# ---------------------------------------------------------------------------
# 2.3: CandidatoEvaluacionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_candidato_repo_import_idempotente(eval_session):
    """2.3 RED: import idempotente — same (evaluacion_id, alumno_id) not duplicated."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"CandT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al = await _create_usuario(eval_session, tid, "cand_al")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_cand = CandidatoEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="Candidatos")
    ev = await repo_ev.add(ev)

    # Import once
    await repo_cand.import_idempotente(ev.id, [al.id])
    # Import again (same alumno)
    await repo_cand.import_idempotente(ev.id, [al.id])

    candidatos = await repo_cand.list_by_evaluacion(ev.id)
    assert len(candidatos) == 1  # no duplicate

    # Cleanup
    for c in candidatos:
        await eval_session.delete(c)
    await repo_ev.delete(ev)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_candidato_repo_scope_por_convocatoria(eval_session):
    """2.3 TRIANGULATE: candidatos scoped to the convocatoria."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"CandScope_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al = await _create_usuario(eval_session, tid, "scope_al")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_cand = CandidatoEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev1 = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                     tipo=EvaluacionTipo.Coloquio, instancia="E1")
    ev2 = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                     tipo=EvaluacionTipo.Coloquio, instancia="E2")
    ev1 = await repo_ev.add(ev1)
    ev2 = await repo_ev.add(ev2)

    # Add alumno to ev1 only
    await repo_cand.import_idempotente(ev1.id, [al.id])

    # Querying ev2 should return empty
    cands_ev2 = await repo_cand.list_by_evaluacion(ev2.id)
    assert len(cands_ev2) == 0

    # Querying ev1 should return 1
    cands_ev1 = await repo_cand.list_by_evaluacion(ev1.id)
    assert len(cands_ev1) == 1

    # is_candidato
    assert await repo_cand.is_candidato(ev1.id, al.id) is True
    assert await repo_cand.is_candidato(ev2.id, al.id) is False

    # Cleanup
    for c in cands_ev1:
        await eval_session.delete(c)
    await repo_ev.delete(ev1)
    await repo_ev.delete(ev2)
    await eval_session.commit()


# ---------------------------------------------------------------------------
# 2.4: ReservaEvaluacionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_reserva_repo_add_and_count(eval_session):
    """2.4 RED: add reserva activa and count correctly."""
    from app.models.evaluacion import (
        CandidatoEvaluacion, Evaluacion, EvaluacionTipo,
        ReservaEvaluacion, ReservaEstado, TurnoEvaluacion,
    )
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, ReservaEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"ResT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al = await _create_usuario(eval_session, tid, "res_al")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_res = ReservaEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="Reserva test")
    ev = await repo_ev.add(ev)

    turno = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 12, 1), cupo_total=5)
    eval_session.add(turno)
    await eval_session.commit()
    await eval_session.refresh(turno)

    # Add reserva
    res = ReservaEvaluacion(tenant_id=tid, turno_id=turno.id, evaluacion_id=ev.id,
                            alumno_id=al.id, estado=ReservaEstado.Activa)
    eval_session.add(res)
    await eval_session.commit()
    await eval_session.refresh(res)

    count = await repo_res.count_activas_by_turno(turno.id)
    assert count == 1

    # Cleanup
    await eval_session.delete(res)
    await eval_session.delete(turno)
    await repo_ev.delete(ev)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_reserva_repo_cancelar_excluye_conteo(eval_session):
    """2.4 TRIANGULATE: cancelled reservation excluded from count."""
    from app.models.evaluacion import (
        Evaluacion, EvaluacionTipo, ReservaEvaluacion, ReservaEstado, TurnoEvaluacion,
    )
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, ReservaEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"CancelT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al = await _create_usuario(eval_session, tid, "cancel_al")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_res = ReservaEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="Cancel test")
    ev = await repo_ev.add(ev)

    turno = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 12, 5), cupo_total=10)
    eval_session.add(turno)
    await eval_session.commit()
    await eval_session.refresh(turno)

    res = ReservaEvaluacion(tenant_id=tid, turno_id=turno.id, evaluacion_id=ev.id,
                            alumno_id=al.id, estado=ReservaEstado.Activa)
    eval_session.add(res)
    await eval_session.commit()
    await eval_session.refresh(res)

    # Cancel
    await repo_res.cancelar(res)
    count = await repo_res.count_activas_by_turno(turno.id)
    assert count == 0  # cancelled reservation excluded

    # Cleanup
    await eval_session.delete(res)
    await eval_session.delete(turno)
    await repo_ev.delete(ev)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_reserva_repo_count_activas_por_alumno_convocatoria(eval_session):
    """2.4: count_activas_por_alumno_convocatoria for unique reservation enforcement."""
    from app.models.evaluacion import (
        Evaluacion, EvaluacionTipo, ReservaEvaluacion, ReservaEstado, TurnoEvaluacion,
    )
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, ReservaEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"ResCountT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al = await _create_usuario(eval_session, tid, "rcount_al")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_res = ReservaEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="AlumnoCount")
    ev = await repo_ev.add(ev)

    turno = TurnoEvaluacion(tenant_id=tid, evaluacion_id=ev.id, fecha=date(2026, 12, 10), cupo_total=5)
    eval_session.add(turno)
    await eval_session.commit()
    await eval_session.refresh(turno)

    # Before reserva: count 0
    count_before = await repo_res.count_activas_por_alumno_convocatoria(al.id, ev.id)
    assert count_before == 0

    res = ReservaEvaluacion(tenant_id=tid, turno_id=turno.id, evaluacion_id=ev.id,
                            alumno_id=al.id, estado=ReservaEstado.Activa)
    eval_session.add(res)
    await eval_session.commit()
    await eval_session.refresh(res)

    # After reserva: count 1
    count_after = await repo_res.count_activas_por_alumno_convocatoria(al.id, ev.id)
    assert count_after == 1

    # Cleanup
    await eval_session.delete(res)
    await eval_session.delete(turno)
    await repo_ev.delete(ev)
    await eval_session.commit()


# ---------------------------------------------------------------------------
# 2.5: ResultadoEvaluacionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_resultado_repo_upsert_no_duplica(eval_session):
    """2.5 RED: upsert by (evaluacion_id, alumno_id) does not duplicate."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, ResultadoEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"ResUpsT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al = await _create_usuario(eval_session, tid, "res_ups_al")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_res = ResultadoEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="Resultado test")
    ev = await repo_ev.add(ev)

    # First insert
    r = await repo_res.upsert(ev.id, al.id, nota_final="8")
    assert r.nota_final == "8"

    # Second upsert (update)
    r2 = await repo_res.upsert(ev.id, al.id, nota_final="Aprobado")
    assert r2.nota_final == "Aprobado"

    # Only one row should exist
    todos = await repo_res.list_by_evaluacion(ev.id)
    alumno_results = [x for x in todos if x.alumno_id == al.id]
    assert len(alumno_results) == 1
    assert alumno_results[0].nota_final == "Aprobado"

    # Cleanup
    for x in todos:
        await eval_session.delete(x)
    await repo_ev.delete(ev)
    await eval_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_resultado_repo_alumno_lee_solo_propio(eval_session):
    """2.5 TRIANGULATE: get_by_alumno returns only own result."""
    from app.models.evaluacion import Evaluacion, EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        EvaluacionRepository, ResultadoEvaluacionRepository,
    )

    tid = _make_tenant_id()
    await _create_tenant(eval_session, tid, f"ResOwn_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(eval_session, tid)
    al1 = await _create_usuario(eval_session, tid, "own_al1")
    al2 = await _create_usuario(eval_session, tid, "own_al2")

    repo_ev = EvaluacionRepository(session=eval_session, tenant_id=tid)
    repo_res = ResultadoEvaluacionRepository(session=eval_session, tenant_id=tid)

    ev = Evaluacion(materia_id=mat.id, cohorte_id=coh.id,
                    tipo=EvaluacionTipo.Coloquio, instancia="AlumnoOwn")
    ev = await repo_ev.add(ev)

    await repo_res.upsert(ev.id, al1.id, nota_final="9")
    await repo_res.upsert(ev.id, al2.id, nota_final="7")

    # al1 sees only own
    res_al1 = await repo_res.get_by_alumno(ev.id, al1.id)
    assert res_al1 is not None
    assert res_al1.nota_final == "9"

    # al2 sees only own
    res_al2 = await repo_res.get_by_alumno(ev.id, al2.id)
    assert res_al2 is not None
    assert res_al2.nota_final == "7"

    # Cleanup
    todos = await repo_res.list_by_evaluacion(ev.id)
    for x in todos:
        await eval_session.delete(x)
    await repo_ev.delete(ev)
    await eval_session.commit()
