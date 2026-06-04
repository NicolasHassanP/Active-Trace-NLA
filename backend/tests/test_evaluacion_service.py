"""
test_evaluacion_service.py — TDD tests for C-14 EvaluacionService.

Tasks 3.1–3.6:
    3.1 crear_convocatoria: valida cupo_total > 0, crea Evaluacion + turnos, audita.
    3.2 importar_candidatos: idempotente, audita.
    3.3 cerrar_convocatoria: set cerrada=True, preserva datos.
    3.4 crear_reserva: gating por candidato, lock + cupo, unicidad, cierre.
    3.5 cancelar_reserva: dueño, libera cupo, re-reserva.
    3.6 metricas, agenda, registro_academico, registrar_resultado.

RED → GREEN → TRIANGULATE: strict TDD cycle.
DB real: activia_trace_test. Sin mocks.
"""
import asyncio
import uuid
from datetime import date

import pytest
import pytest_asyncio
from dotenv import load_dotenv
import os
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
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_activa_por_convocatoria "
            "ON reserva_evaluacion (tenant_id, evaluacion_id, alumno_id) "
            "WHERE estado = 'Activa' AND deleted_at IS NULL"
        ))

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

def _make_tid():
    return uuid.uuid4()


from app.core.dependencies import CurrentUser


def _actor(tid, uid, roles=None):
    return CurrentUser(user_id=uid, tenant_id=tid, roles=roles or ["PROFESOR"])


async def _create_tenant(session, tid, name):
    from app.models.tenant import Tenant, TenantEstado
    t = Tenant(id=tid, nombre=name, estado=TenantEstado.ACTIVO)
    session.add(t)
    await session.flush()
    return t


async def _create_estructura(session, tid):
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


async def _create_usuario(session, tid, suffix):
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"svc_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    u = Usuario(
        tenant_id=tid, email_encrypted=email, email_hash=_hash(email),
        nombre="Test", apellidos=suffix, estado=UsuarioEstado.activo,
    )
    session.add(u)
    await session.flush()
    return u


def _make_service(session, tid):
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository,
        EvaluacionRepository,
        ReservaEvaluacionRepository,
        ResultadoEvaluacionRepository,
        TurnoEvaluacionRepository,
    )
    from app.repositories.audit_repository import AuditRepository
    from app.services.evaluacion_service import EvaluacionService
    return EvaluacionService(
        evaluacion_repo=EvaluacionRepository(session=session, tenant_id=tid),
        turno_repo=TurnoEvaluacionRepository(session=session, tenant_id=tid),
        candidato_repo=CandidatoEvaluacionRepository(session=session, tenant_id=tid),
        reserva_repo=ReservaEvaluacionRepository(session=session, tenant_id=tid),
        resultado_repo=ResultadoEvaluacionRepository(session=session, tenant_id=tid),
        audit_repo=AuditRepository(session=session, tenant_id=tid),
    )


# ---------------------------------------------------------------------------
# 3.1: crear_convocatoria
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_convocatoria_con_turnos(svc_session):
    """3.1 RED: crear convocatoria con 2 turnos → Evaluacion + 2 TurnoEvaluacion."""
    from app.schemas.evaluacion import CrearConvocatoriaRequest, TurnoRequest
    from app.models.evaluacion import EvaluacionTipo

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"SvcT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    await svc_session.commit()

    actor = _actor(tid, uuid.uuid4())
    svc = _make_service(svc_session, tid)

    req = CrearConvocatoriaRequest(
        materia_id=mat.id, cohorte_id=coh.id,
        tipo=EvaluacionTipo.Coloquio, instancia="Test Coloquio",
        dias_disponibles=7,
        turnos=[
            TurnoRequest(fecha=date(2026, 9, 1), cupo_total=10),
            TurnoRequest(fecha=date(2026, 9, 2), cupo_total=8),
        ],
    )
    result = await svc.crear_convocatoria(req, actor)
    assert result.evaluacion.cerrada is False
    assert len(result.turnos) == 2
    cupos = {t.cupo_total for t in result.turnos}
    assert cupos == {10, 8}

    # Cleanup
    from app.repositories.evaluacion_repository import EvaluacionRepository, TurnoEvaluacionRepository
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in result.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    ev = await repo_ev.get_by_id(result.evaluacion.id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_convocatoria_cupo_cero_raises(svc_session):
    """3.1 TRIANGULATE: cupo_total <= 0 raises ValidationError or EvaluacionValidationError."""
    from app.schemas.evaluacion import TurnoRequest
    from pydantic import ValidationError

    # The schema validator catches cupo_total=0 before it reaches the service.
    # This is the correct fail-fast behavior (422 at the HTTP layer).
    with pytest.raises((ValidationError, ValueError)):
        TurnoRequest(fecha=date(2026, 9, 1), cupo_total=0)


# ---------------------------------------------------------------------------
# 3.2: importar_candidatos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_importar_candidatos_idempotente(svc_session):
    """3.2 RED: importar 2 veces mismo alumno → solo 1 candidato."""
    from app.schemas.evaluacion import CrearConvocatoriaRequest, TurnoRequest, ImportarCandidatosRequest
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import EvaluacionRepository, TurnoEvaluacionRepository

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"ImpT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "imp_al")
    await svc_session.commit()

    actor = _actor(tid, uuid.uuid4())
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Imp test",
            turnos=[TurnoRequest(fecha=date(2026, 10, 1), cupo_total=5)],
        ),
        actor,
    )
    ev_id = conv.evaluacion.id

    # Import once
    await svc.importar_candidatos(ImportarCandidatosRequest(
        evaluacion_id=ev_id, alumno_ids=[al.id]
    ), actor)
    # Import again (same alumno)
    await svc.importar_candidatos(ImportarCandidatosRequest(
        evaluacion_id=ev_id, alumno_ids=[al.id]
    ), actor)

    from app.repositories.evaluacion_repository import CandidatoEvaluacionRepository
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    cands = await cand_repo.list_by_evaluacion(ev_id)
    assert len(cands) == 1  # no duplicate

    # Cleanup
    for c in cands:
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 3.3: cerrar_convocatoria
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_cerrar_convocatoria_bloquea_reservas(svc_session):
    """3.3 + 3.4: cerrar convocatoria → nuevas reservas rechazadas (409)."""
    from fastapi import HTTPException
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ImportarCandidatosRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository, TurnoEvaluacionRepository,
    )

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"CierreT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "cierre_al")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al = _actor(tid, al.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Cierre test",
            turnos=[TurnoRequest(fecha=date(2026, 11, 1), cupo_total=5)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno_id = conv.turnos[0].id

    # Import alumno as candidate
    await svc.importar_candidatos(
        ImportarCandidatosRequest(evaluacion_id=ev_id, alumno_ids=[al.id]),
        actor_prof,
    )

    # Close convocatoria
    await svc.cerrar_convocatoria(ev_id, actor_prof)

    # Attempt to reserve after close → 409
    with pytest.raises(HTTPException) as exc_info:
        await svc.crear_reserva(
            ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id),
            actor_al,
        )
    assert exc_info.value.status_code == 409

    # Cleanup
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    cands = await cand_repo.list_by_evaluacion(ev_id)
    for c in cands:
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 3.4: crear_reserva
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_reserva_exitosa(svc_session):
    """3.4 RED: candidate alumno reserves available turn → Activa reservation."""
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ImportarCandidatosRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo, ReservaEstado
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository, ReservaEvaluacionRepository,
        TurnoEvaluacionRepository,
    )

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"ResT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "res_al")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al = _actor(tid, al.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Reserva exitosa",
            turnos=[TurnoRequest(fecha=date(2026, 12, 1), cupo_total=10)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno_id = conv.turnos[0].id

    await svc.importar_candidatos(
        ImportarCandidatosRequest(evaluacion_id=ev_id, alumno_ids=[al.id]),
        actor_prof,
    )

    reserva = await svc.crear_reserva(
        ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id),
        actor_al,
    )
    assert reserva.estado == ReservaEstado.Activa
    assert reserva.alumno_id == al.id

    # Cleanup
    repo_res = ReservaEvaluacionRepository(session=svc_session, tenant_id=tid)
    r = await repo_res.get_by_id(reserva.id)
    if r:
        await svc_session.delete(r)
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for c in await cand_repo.list_by_evaluacion(ev_id):
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_reserva_no_candidato_returns_403(svc_session):
    """3.4 TRIANGULATE: non-candidate alumno → 403."""
    from fastapi import HTTPException
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import EvaluacionRepository, TurnoEvaluacionRepository

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"NoCandT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al_no_cand = await _create_usuario(svc_session, tid, "no_cand")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al = _actor(tid, al_no_cand.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="NoCand test",
            turnos=[TurnoRequest(fecha=date(2026, 12, 5), cupo_total=5)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno_id = conv.turnos[0].id

    with pytest.raises(HTTPException) as exc_info:
        await svc.crear_reserva(
            ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id),
            actor_al,
        )
    assert exc_info.value.status_code == 403

    # Cleanup
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_reserva_cupo_lleno_returns_409(svc_session):
    """3.4 TRIANGULATE: full turn → 409."""
    from fastapi import HTTPException
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ImportarCandidatosRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo, ReservaEvaluacion, ReservaEstado
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository, ReservaEvaluacionRepository,
        TurnoEvaluacionRepository,
    )

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"CupoT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "cupo_al")
    al2 = await _create_usuario(svc_session, tid, "cupo_al2")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al = _actor(tid, al.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Cupo 1",
            turnos=[TurnoRequest(fecha=date(2026, 12, 10), cupo_total=1)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno_id = conv.turnos[0].id

    await svc.importar_candidatos(
        ImportarCandidatosRequest(evaluacion_id=ev_id, alumno_ids=[al.id, al2.id]),
        actor_prof,
    )

    # First reservation fills the cupo
    await svc.crear_reserva(ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id), actor_al)

    # Second attempt (different alumno but cupo=1) → 409
    actor_al2 = _actor(tid, al2.id, roles=["ALUMNO"])
    with pytest.raises(HTTPException) as exc_info:
        await svc.crear_reserva(
            ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id),
            actor_al2,
        )
    assert exc_info.value.status_code == 409

    # Cleanup
    repo_res = ReservaEvaluacionRepository(session=svc_session, tenant_id=tid)
    all_res = await repo_res.list()
    for r in all_res:
        if r.evaluacion_id == ev_id:
            await svc_session.delete(r)
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for c in await cand_repo.list_by_evaluacion(ev_id):
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_segunda_reserva_misma_convocatoria_returns_409(svc_session):
    """3.4 TRIANGULATE: second active reservation same convocatoria → 409 (D4)."""
    from fastapi import HTTPException
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ImportarCandidatosRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository, ReservaEvaluacionRepository,
        TurnoEvaluacionRepository,
    )

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"Dup2T_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "dup2_al")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al = _actor(tid, al.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Dup reserva",
            turnos=[
                TurnoRequest(fecha=date(2026, 12, 15), cupo_total=5),
                TurnoRequest(fecha=date(2026, 12, 16), cupo_total=5),
            ],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno1_id = conv.turnos[0].id
    turno2_id = conv.turnos[1].id

    await svc.importar_candidatos(
        ImportarCandidatosRequest(evaluacion_id=ev_id, alumno_ids=[al.id]),
        actor_prof,
    )

    # Reserve on turno 1
    await svc.crear_reserva(ReservaRequest(turno_id=turno1_id, evaluacion_id=ev_id), actor_al)

    # Attempt to reserve on turno 2 (same convocatoria) → 409
    with pytest.raises(HTTPException) as exc_info:
        await svc.crear_reserva(
            ReservaRequest(turno_id=turno2_id, evaluacion_id=ev_id),
            actor_al,
        )
    assert exc_info.value.status_code == 409

    # Cleanup
    repo_res = ReservaEvaluacionRepository(session=svc_session, tenant_id=tid)
    all_res = await repo_res.list()
    for r in all_res:
        if r.evaluacion_id == ev_id:
            await svc_session.delete(r)
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for c in await cand_repo.list_by_evaluacion(ev_id):
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 3.5: cancelar_reserva
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_cancelar_reserva_libera_cupo(svc_session):
    """3.5 RED: cancelar reserva → estado Cancelada, re-reserva posible."""
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ImportarCandidatosRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo, ReservaEstado
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository, ReservaEvaluacionRepository,
        TurnoEvaluacionRepository,
    )

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"CancelSvcT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "cancel_svc_al")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al = _actor(tid, al.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Cancel svc",
            turnos=[TurnoRequest(fecha=date(2026, 12, 20), cupo_total=1)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno_id = conv.turnos[0].id

    await svc.importar_candidatos(
        ImportarCandidatosRequest(evaluacion_id=ev_id, alumno_ids=[al.id]),
        actor_prof,
    )

    reserva = await svc.crear_reserva(
        ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id), actor_al
    )
    reserva_id = reserva.id

    # Cancel
    await svc.cancelar_reserva(reserva_id, actor_al)

    repo_res = ReservaEvaluacionRepository(session=svc_session, tenant_id=tid)
    r = await repo_res.get_by_id(reserva_id)
    assert r.estado == ReservaEstado.Cancelada

    # Re-reserve (cupo freed)
    nueva = await svc.crear_reserva(
        ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id), actor_al
    )
    assert nueva.estado == ReservaEstado.Activa

    # Cleanup
    for r_obj in await repo_res.list():
        if r_obj.evaluacion_id == ev_id:
            await svc_session.delete(r_obj)
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for c in await cand_repo.list_by_evaluacion(ev_id):
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_cancelar_reserva_ajena_returns_403(svc_session):
    """3.5 TRIANGULATE: cancelar reserva de otro alumno → 403."""
    from fastapi import HTTPException
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ImportarCandidatosRequest, ReservaRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import (
        CandidatoEvaluacionRepository, EvaluacionRepository, ReservaEvaluacionRepository,
        TurnoEvaluacionRepository,
    )

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"OtherT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al1 = await _create_usuario(svc_session, tid, "other_al1")
    al2 = await _create_usuario(svc_session, tid, "other_al2")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al1 = _actor(tid, al1.id, roles=["ALUMNO"])
    actor_al2 = _actor(tid, al2.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Other test",
            turnos=[TurnoRequest(fecha=date(2026, 12, 25), cupo_total=5)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id
    turno_id = conv.turnos[0].id

    await svc.importar_candidatos(
        ImportarCandidatosRequest(evaluacion_id=ev_id, alumno_ids=[al1.id, al2.id]),
        actor_prof,
    )

    # al1 reserves
    reserva = await svc.crear_reserva(
        ReservaRequest(turno_id=turno_id, evaluacion_id=ev_id), actor_al1
    )

    # al2 tries to cancel al1's reservation → 403
    with pytest.raises(HTTPException) as exc_info:
        await svc.cancelar_reserva(reserva.id, actor_al2)
    assert exc_info.value.status_code in (403, 404)

    # Cleanup
    repo_res = ReservaEvaluacionRepository(session=svc_session, tenant_id=tid)
    for r in await repo_res.list():
        if r.evaluacion_id == ev_id:
            await svc_session.delete(r)
    cand_repo = CandidatoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for c in await cand_repo.list_by_evaluacion(ev_id):
        await svc_session.delete(c)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


# ---------------------------------------------------------------------------
# 3.6: metricas, agenda, registro_academico, registrar_resultado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_registrar_resultado_upsert(svc_session):
    """3.6 RED: registrar_resultado upsert → no duplicate."""
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ResultadoRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import EvaluacionRepository, TurnoEvaluacionRepository

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"ResRegT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al = await _create_usuario(svc_session, tid, "res_reg_al")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="Resultado reg",
            turnos=[TurnoRequest(fecha=date(2026, 12, 28), cupo_total=5)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id

    await svc.registrar_resultado(
        ResultadoRequest(evaluacion_id=ev_id, alumno_id=al.id, nota_final="8"),
        actor_prof,
    )
    await svc.registrar_resultado(
        ResultadoRequest(evaluacion_id=ev_id, alumno_id=al.id, nota_final="Aprobado"),
        actor_prof,
    )

    from app.repositories.evaluacion_repository import ResultadoEvaluacionRepository
    repo = ResultadoEvaluacionRepository(session=svc_session, tenant_id=tid)
    todos = await repo.list_by_evaluacion(ev_id)
    al_results = [x for x in todos if x.alumno_id == al.id]
    assert len(al_results) == 1
    assert al_results[0].nota_final == "Aprobado"

    # Cleanup
    for x in todos:
        await svc_session.delete(x)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_alumno_lee_solo_propio_resultado(svc_session):
    """3.6 TRIANGULATE: alumno reads only own result."""
    from fastapi import HTTPException
    from app.schemas.evaluacion import (
        CrearConvocatoriaRequest, ResultadoRequest, TurnoRequest,
    )
    from app.models.evaluacion import EvaluacionTipo
    from app.repositories.evaluacion_repository import EvaluacionRepository, TurnoEvaluacionRepository

    tid = _make_tid()
    await _create_tenant(svc_session, tid, f"AlResT_{tid.hex[:4]}")
    _, mat, coh = await _create_estructura(svc_session, tid)
    al1 = await _create_usuario(svc_session, tid, "alres_al1")
    al2 = await _create_usuario(svc_session, tid, "alres_al2")
    await svc_session.commit()

    actor_prof = _actor(tid, uuid.uuid4(), roles=["PROFESOR"])
    actor_al1 = _actor(tid, al1.id, roles=["ALUMNO"])
    svc = _make_service(svc_session, tid)

    conv = await svc.crear_convocatoria(
        CrearConvocatoriaRequest(
            materia_id=mat.id, cohorte_id=coh.id,
            tipo=EvaluacionTipo.Coloquio, instancia="AlRes",
            turnos=[TurnoRequest(fecha=date(2026, 12, 30), cupo_total=5)],
        ),
        actor_prof,
    )
    ev_id = conv.evaluacion.id

    await svc.registrar_resultado(
        ResultadoRequest(evaluacion_id=ev_id, alumno_id=al1.id, nota_final="9"),
        actor_prof,
    )
    await svc.registrar_resultado(
        ResultadoRequest(evaluacion_id=ev_id, alumno_id=al2.id, nota_final="7"),
        actor_prof,
    )

    # al1 reads own result
    resultado = await svc.get_resultado_alumno(ev_id, actor_al1)
    assert resultado.nota_final == "9"

    # Cleanup
    from app.repositories.evaluacion_repository import ResultadoEvaluacionRepository
    repo = ResultadoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for x in await repo.list_by_evaluacion(ev_id):
        await svc_session.delete(x)
    repo_turno = TurnoEvaluacionRepository(session=svc_session, tenant_id=tid)
    for t in conv.turnos:
        turno = await repo_turno.get_by_id(t.id)
        if turno:
            await repo_turno.delete(turno)
    repo_ev = EvaluacionRepository(session=svc_session, tenant_id=tid)
    ev = await repo_ev.get_by_id(ev_id)
    if ev:
        await repo_ev.delete(ev)
    await svc_session.commit()
