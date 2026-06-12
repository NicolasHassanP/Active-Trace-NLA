"""
test_estructura_audit.py — TDD suite para el gap de auditoría en C-06.

Cubre la emisión de AuditEvent con accion=ESTRUCTURA_GESTIONAR en cada
operación ABM de estructura académica (Carrera, Materia, Cohorte).

Ciclo TDD: RED → GREEN → TRIANGULATE → REFACTOR

DB real: activia_trace_test. Sin mocks.
Patrón: idéntico a test_estructura_academica.py y test_programa.py.
"""
import datetime
import uuid
from datetime import date

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditResultado
from app.models.estructura import EstadoEstructura
from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
from app.models.tenant import Tenant, TenantEstado
from app.repositories.audit_repository import AuditRepository
from app.repositories.estructura_repository import (
    CarreraRepository,
    CohorteRepository,
    MateriaRepository,
)
from app.services.estructura_service import EstructuraService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_actor(tenant_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_id, roles=["ADMIN"])


async def _make_svc(session, tid: uuid.UUID) -> tuple[EstructuraService, AuditRepository]:
    audit_repo = AuditRepository(session=session, tenant_id=tid)
    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
        audit_repo=audit_repo,
    )
    return svc, audit_repo


async def _setup_tenant(session, nombre: str) -> uuid.UUID:
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=nombre, estado=TenantEstado.ACTIVO))
    await session.commit()
    return tid


# ===========================================================================
# Task AUD-1 — RED: crear Materia emite AuditEvent ESTRUCTURA_GESTIONAR
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_crear_materia_emite_audit_event(test_engine, create_tables):
    """
    AUD-1.1 RED: al crear una Materia, se registra un AuditEvent con
    accion=ESTRUCTURA_GESTIONAR, modulo='estructura', entidad_tipo='Materia',
    entidad_id = id de la materia, y resultado=ok.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "Audit Materia Tenant")
    actor = _make_actor(tid)

    svc, audit_repo = await _make_svc(session, tid)
    materia = await svc.crear_materia(actor, "AUDIT_MAT_1", "Auditada 1")

    # Verificar que el AuditEvent fue creado
    eventos = await audit_repo.list()
    assert len(eventos) >= 1

    # Encontrar el evento de creación de esta materia
    evento = next(
        (e for e in eventos if e.entidad_id == str(materia.id)),
        None,
    )
    assert evento is not None, "No se encontró AuditEvent para la materia creada"
    assert evento.accion == AuditAction.ESTRUCTURA_GESTIONAR
    assert evento.modulo == "estructura"
    assert evento.entidad_tipo == "Materia"
    assert evento.resultado == AuditResultado.ok
    assert evento.registros_afectados == 1
    assert evento.after["accion"] == "alta"

    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_crear_materia_audit_actor_es_del_jwt(test_engine, create_tables):
    """
    AUD-1.2 GREEN: el actor_user_id en el AuditEvent coincide con el user_id del JWT (CurrentUser).
    Identidad SIEMPRE desde la sesión (regla dura #8).
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "Audit Actor Tenant")
    actor_user_id = uuid.uuid4()
    actor = CurrentUser(user_id=actor_user_id, tenant_id=tid, roles=["ADMIN"])

    svc, audit_repo = await _make_svc(session, tid)
    materia = await svc.crear_materia(actor, "AUDIT_ACTOR_MAT", "Actor Test Materia")

    eventos = await audit_repo.list()
    evento = next((e for e in eventos if e.entidad_id == str(materia.id)), None)
    assert evento is not None
    assert evento.actor_user_id == actor_user_id, (
        f"actor_user_id debe ser {actor_user_id} (del JWT), got {evento.actor_user_id}"
    )

    await session.close()


# ===========================================================================
# Task AUD-2 — TRIANGULATE: editar Carrera también emite ESTRUCTURA_GESTIONAR
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_editar_carrera_emite_audit_event(test_engine, create_tables):
    """
    AUD-2.1 TRIANGULATE: editar una Carrera registra AuditEvent con
    accion=ESTRUCTURA_GESTIONAR, entidad_tipo='Carrera'.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "Audit Carrera Edit Tenant")
    actor = _make_actor(tid)

    svc, audit_repo = await _make_svc(session, tid)
    carrera = await svc.crear_carrera(actor, "AUDIT_CAR_EDIT", "Carrera Auditable")

    # Editar nombre
    carrera_editada = await svc.editar_carrera(
        carrera.id,
        actor=actor,
        nombre="Carrera Auditada Editada",
    )

    eventos = await audit_repo.list()
    # Debe haber al menos 2 eventos: alta + editar
    eventos_carrera = [e for e in eventos if e.entidad_id == str(carrera.id)]
    assert len(eventos_carrera) >= 2, (
        f"Esperaba ≥2 eventos para la carrera, encontré {len(eventos_carrera)}"
    )

    evento_editar = next(
        (e for e in eventos_carrera if e.after.get("accion") == "editar"),
        None,
    )
    assert evento_editar is not None, "No se encontró AuditEvent de editar Carrera"
    assert evento_editar.accion == AuditAction.ESTRUCTURA_GESTIONAR
    assert evento_editar.entidad_tipo == "Carrera"
    assert evento_editar.actor_user_id == actor.user_id

    await session.close()


# ===========================================================================
# Task AUD-3 — TRIANGULATE: dar_baja Cohorte emite ESTRUCTURA_GESTIONAR
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_dar_baja_cohorte_emite_audit_event(test_engine, create_tables):
    """
    AUD-3.1 TRIANGULATE: dar baja a una Cohorte registra AuditEvent con
    accion=ESTRUCTURA_GESTIONAR, entidad_tipo='Cohorte', accion='baja'.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "Audit Cohorte Baja Tenant")
    actor = _make_actor(tid)

    svc, audit_repo = await _make_svc(session, tid)
    carrera = await svc.crear_carrera(actor, "AUDIT_CAR_COH_BAJA", "Carrera para Cohorte Baja")
    cohorte = await svc.crear_cohorte(
        actor, carrera.id, "AUDIT_COH_BAJA", 2025, date(2025, 8, 1), None
    )

    cohorte_id = cohorte.id
    await svc.dar_baja_cohorte(cohorte_id, actor=actor)

    eventos = await audit_repo.list()
    # Debe existir evento de baja de cohorte
    evento_baja = next(
        (
            e for e in eventos
            if e.entidad_id == str(cohorte_id)
            and e.entidad_tipo == "Cohorte"
            and e.after.get("accion") == "baja"
        ),
        None,
    )
    assert evento_baja is not None, "No se encontró AuditEvent de baja de Cohorte"
    assert evento_baja.accion == AuditAction.ESTRUCTURA_GESTIONAR
    assert evento_baja.resultado == AuditResultado.ok
    assert evento_baja.actor_user_id == actor.user_id

    await session.close()


# ===========================================================================
# Task AUD-4 — TRIANGULATE: sin audit_repo no falla (backwards compat)
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_crear_materia_sin_audit_repo_no_falla(test_engine, create_tables):
    """
    AUD-4.1: EstructuraService sin audit_repo (None) no lanza error al crear.
    Garantiza backwards compat con tests existentes que no inyectan audit_repo.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "No Audit Repo Tenant")
    actor = _make_actor(tid)

    # Construir service SIN audit_repo (por defecto None)
    svc = EstructuraService(
        carrera_repo=CarreraRepository(session=session, tenant_id=tid),
        cohorte_repo=CohorteRepository(session=session, tenant_id=tid),
        materia_repo=MateriaRepository(session=session, tenant_id=tid),
        # audit_repo omitido
    )

    # No debe lanzar excepción
    materia = await svc.crear_materia(actor, "NO_AUDIT_REPO_MAT", "No Audit Repo")
    assert materia.id is not None

    await session.close()


# ===========================================================================
# Task AUD-5 — TRIANGULATE: dar_baja Carrera y crear Cohorte también auditan
# ===========================================================================


@pytest.mark.asyncio(loop_scope="function")
async def test_dar_baja_carrera_emite_audit_event(test_engine, create_tables):
    """
    AUD-5.1 TRIANGULATE: dar baja a una Carrera registra AuditEvent con
    entidad_tipo='Carrera', accion='baja'.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "Audit Carrera Baja Tenant")
    actor = _make_actor(tid)

    svc, audit_repo = await _make_svc(session, tid)
    carrera = await svc.crear_carrera(actor, "AUDIT_CAR_BAJA", "Carrera para Baja")
    carrera_id = carrera.id

    await svc.dar_baja_carrera(carrera_id, actor=actor)

    eventos = await audit_repo.list()
    evento_baja = next(
        (
            e for e in eventos
            if e.entidad_id == str(carrera_id)
            and e.entidad_tipo == "Carrera"
            and e.after.get("accion") == "baja"
        ),
        None,
    )
    assert evento_baja is not None, "No se encontró AuditEvent de baja de Carrera"
    assert evento_baja.accion == AuditAction.ESTRUCTURA_GESTIONAR
    assert evento_baja.actor_user_id == actor.user_id

    await session.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_crear_cohorte_emite_audit_event(test_engine, create_tables):
    """
    AUD-5.2 TRIANGULATE: crear una Cohorte registra AuditEvent con
    entidad_tipo='Cohorte', accion='alta'.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    tid = await _setup_tenant(session, "Audit Cohorte Alta Tenant")
    actor = _make_actor(tid)

    svc, audit_repo = await _make_svc(session, tid)
    carrera = await svc.crear_carrera(actor, "AUDIT_CAR_COH_ALTA", "Carrera para Cohorte Alta")
    cohorte = await svc.crear_cohorte(
        actor, carrera.id, "AUDIT_COH_ALTA", 2025, date(2025, 8, 1), None
    )

    eventos = await audit_repo.list()
    evento_alta = next(
        (
            e for e in eventos
            if e.entidad_id == str(cohorte.id)
            and e.entidad_tipo == "Cohorte"
            and e.after.get("accion") == "alta"
        ),
        None,
    )
    assert evento_alta is not None, "No se encontró AuditEvent de alta de Cohorte"
    assert evento_alta.accion == AuditAction.ESTRUCTURA_GESTIONAR
    assert evento_alta.actor_user_id == actor.user_id

    await session.close()
