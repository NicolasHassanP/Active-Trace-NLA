"""
test_c28_domain_user_id.py — TDD regression tests for C-28 fix-domain-user-id-transversal.

D4 (design): Each test creates an auth_identity + usuario with DIFFERENT UUIDs.
This is the critical invariant: auth_identity_id != usuario.id.
Tests that use the same UUID for both would be tautological (prohibited by Strict TDD).

Coverage:
    Task 2 — avisos: listar_feed / listar_pendientes use usuario.id (not auth_identity_id)
    Task 3 — encuentros: listar_instancias filters asignaciones by usuario.id
    Task 4 — guardias: consultar filters asignaciones by usuario.id; registrar resolves correctly
    Task 5 — padron: vaciar compares cargado_por against usuario.id
    Task 6 — fallback hardening: service signatures require domain_user_id (no Optional default)

DB real: activia_trace_test. No DB mocks (regla dura #4).
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.core.dependencies import CurrentUser
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(tz=timezone.utc)


def _make_tenant_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_auth_identity_id() -> uuid.UUID:
    """A separate UUID that represents the auth_identities.id (JWT sub)."""
    return uuid.uuid4()


def _make_usuario(tid: uuid.UUID, auth_identity_id: uuid.UUID, suffix: str) -> Usuario:
    """
    Creates a Usuario with auth_identity_id set EXPLICITLY to a DIFFERENT UUID
    than the usuario.id (which is auto-generated on flush).
    This guarantees auth_identity_id != usuario.id in tests.
    """
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"c28_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    return Usuario(
        tenant_id=tid,
        email_encrypted=email,
        email_hash=_hash(email),
        nombre="C28",
        apellidos=suffix,
        estado=UsuarioEstado.activo,
        auth_identity_id=auth_identity_id,
    )


def _actor(tid: uuid.UUID, auth_identity_id: uuid.UUID, roles=None) -> CurrentUser:
    """CurrentUser.user_id == auth_identity_id (the JWT sub). NOT usuario.id."""
    return CurrentUser(
        user_id=auth_identity_id,
        tenant_id=tid,
        roles=roles or ["PROFESOR"],
    )


# ---------------------------------------------------------------------------
# Session-scoped DB fixture (shared across all tests in this module)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def c28_session(test_engine, create_tables):
    """
    Creates a clean session for C-28 tests.
    All test data is created with auth_identity_id != usuario.id explicitly.
    """
    factory = build_session_factory(test_engine)
    session = factory()
    yield session
    try:
        await session.rollback()
        await session.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Task 2 — Avisos: listar_feed / listar_pendientes use usuario.id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_aviso_feed_uses_domain_user_id_for_ack_filtering(c28_session):
    """
    2.2 RED: listar_feed must filter acks by usuario.id (domain FK), not auth_identity_id.

    Setup: create aviso + ack tied to domain usuario.id.
    If listar_feed passes auth_identity_id (wrong UUID), the ack is not found → ack_count wrong.
    If it passes domain usuario.id (correct), the ack is found.
    """
    from app.models.aviso import Aviso, AcknowledgmentAviso, AvisoAlcance, AvisoSeveridad
    from app.repositories.aviso_repository import AcknowledgmentRepository, AvisoRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.aviso_service import AvisoService

    # Two DIFFERENT UUIDs: this is the invariant being tested
    tid = uuid.uuid4()
    auth_id = uuid.uuid4()   # auth_identities.id (what JWT carries)
    c28_session.add(Tenant(id=tid, nombre=f"C28AvisoT_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await c28_session.flush()

    usuario = _make_usuario(tid, auth_id, "aviso_feed")
    c28_session.add(usuario)
    await c28_session.flush()

    domain_uid = usuario.id  # usuario.id — the domain FK
    # Invariant check: auth_id must differ from domain_uid
    assert auth_id != domain_uid, "Test setup invalid: auth_identity_id must differ from usuario.id"

    # Create aviso in active window
    inicio = _now() - timedelta(hours=1)
    fin = _now() + timedelta(hours=1)
    aviso = Aviso(
        tenant_id=tid,
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="C28 Feed Test",
        cuerpo="body",
        inicio_en=inicio,
        fin_en=fin,
        requiere_ack=True,
        activo=True,
    )
    c28_session.add(aviso)
    await c28_session.flush()

    # Create ack tied to domain usuario.id (the correct FK)
    ack = AcknowledgmentAviso(
        tenant_id=tid,
        aviso_id=aviso.id,
        usuario_id=domain_uid,   # FK to usuario.id
        confirmado_at=_now(),
    )
    c28_session.add(ack)
    await c28_session.commit()

    # Build service with domain_uid passed explicitly
    svc = AvisoService(
        aviso_repo=AvisoRepository(session=c28_session, tenant_id=tid),
        ack_repo=AcknowledgmentRepository(session=c28_session, tenant_id=tid),
        audit_repo=AuditRepository(session=c28_session, tenant_id=tid),
    )
    actor = _actor(tid, auth_id)

    # listar_feed must receive domain_uid (not auth_id) to find the ack correctly
    feed = await svc.listar_feed(
        usuario_id=domain_uid,
        roles=actor.roles,
        cohorte_id=None,
        actor=actor,
    )

    aviso_result = next((a for a in feed if a.id == aviso.id), None)
    assert aviso_result is not None, "Aviso not found in feed"
    # ack_count is a global count of all acks on the aviso (not user-specific)
    # So ack_count == 1 proves the ack exists (tied to domain_uid)
    assert aviso_result.ack_count == 1, (
        f"Expected ack_count=1 when passing domain_uid={domain_uid}, got {aviso_result.ack_count}. "
        "If it's 0, no ack was found by the repository."
    )

    # 2.4 Triangulation: listar_pendientes with domain_uid should exclude the acked aviso
    # But with auth_id (wrong UUID) it should still appear (no ack found for that UUID)
    pendientes_correct = await svc.listar_pendientes(
        usuario_id=domain_uid,  # correct: finds the ack → aviso not in pending
        roles=actor.roles,
        cohorte_id=None,
        actor=actor,
    )
    ids_pendientes_correct = [a.id for a in pendientes_correct]
    assert aviso.id not in ids_pendientes_correct, (
        "Aviso should NOT be in pendientes when domain_uid is passed: ack exists for this user."
    )

    # With wrong UUID (auth_id), the ack is NOT found → aviso STILL appears in pendientes
    pendientes_wrong = await svc.listar_pendientes(
        usuario_id=auth_id,  # wrong UUID — no ack tied to this
        roles=actor.roles,
        cohorte_id=None,
        actor=actor,
    )
    ids_pendientes_wrong = [a.id for a in pendientes_wrong]
    assert aviso.id in ids_pendientes_wrong, (
        "Aviso SHOULD appear in pendientes when auth_identity_id is passed: "
        "no ack has usuario_id == auth_identity_id (FK points to usuario.id). "
        "This confirms the UUID spaces are distinct and the bug was real."
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_aviso_pendientes_uses_domain_user_id(c28_session):
    """
    2.4 TRIANGULATE: listar_pendientes excludes aviso already acked by domain usuario.id.

    An aviso with requiere_ack=True should NOT appear in pendientes if
    the ack was created with the correct domain_uid.
    """
    from app.models.aviso import Aviso, AcknowledgmentAviso, AvisoAlcance, AvisoSeveridad
    from app.repositories.aviso_repository import AcknowledgmentRepository, AvisoRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.aviso_service import AvisoService

    tid = uuid.uuid4()
    auth_id = uuid.uuid4()
    c28_session.add(Tenant(id=tid, nombre=f"C28PendT_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await c28_session.flush()

    usuario = _make_usuario(tid, auth_id, "aviso_pend")
    c28_session.add(usuario)
    await c28_session.flush()
    domain_uid = usuario.id
    assert auth_id != domain_uid

    inicio = _now() - timedelta(hours=1)
    fin = _now() + timedelta(hours=1)
    aviso = Aviso(
        tenant_id=tid,
        alcance=AvisoAlcance.Global,
        severidad=AvisoSeveridad.Info,
        titulo="C28 Pendientes Test",
        cuerpo="body",
        inicio_en=inicio,
        fin_en=fin,
        requiere_ack=True,
        activo=True,
    )
    c28_session.add(aviso)
    await c28_session.flush()

    # Ack the aviso with domain_uid (correct FK)
    ack = AcknowledgmentAviso(
        tenant_id=tid,
        aviso_id=aviso.id,
        usuario_id=domain_uid,
        confirmado_at=_now(),
    )
    c28_session.add(ack)
    await c28_session.commit()

    svc = AvisoService(
        aviso_repo=AvisoRepository(session=c28_session, tenant_id=tid),
        ack_repo=AcknowledgmentRepository(session=c28_session, tenant_id=tid),
        audit_repo=AuditRepository(session=c28_session, tenant_id=tid),
    )
    actor = _actor(tid, auth_id)

    # With domain_uid → aviso was acked → should NOT appear in pendientes
    pendientes = await svc.listar_pendientes(
        usuario_id=domain_uid,
        roles=actor.roles,
        cohorte_id=None,
        actor=actor,
    )
    ids_pendientes = [a.id for a in pendientes]
    assert aviso.id not in ids_pendientes, (
        "Aviso should NOT be in pendientes: it was already acknowledged via domain_uid"
    )


# ---------------------------------------------------------------------------
# Task 3 — Encuentros: listar_instancias filters by usuario.id
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def c28_enc_setup(test_engine, create_tables):
    """Creates tenant + user with auth_identity_id != usuario.id + asignacion."""
    from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
    from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository

    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    auth_id = uuid.uuid4()  # DIFFERENT from usuario.id (will be auto-generated)
    session.add(Tenant(id=tid, nombre=f"C28EncT_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await session.flush()

    carrera = Carrera(
        tenant_id=tid,
        codigo=f"C28C_{uuid.uuid4().hex[:4]}",
        nombre="Carrera C28",
        estado=EstadoEstructura.activa,
    )
    materia = Materia(
        tenant_id=tid,
        codigo=f"C28M_{uuid.uuid4().hex[:4]}",
        nombre="Materia C28",
        estado=EstadoEstructura.activa,
    )
    session.add_all([carrera, materia])
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre="Coh C28",
        anio=2026,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    await session.flush()

    usr_repo = UsuarioRepository(session=session, tenant_id=tid)
    usuario = _make_usuario(tid, auth_id, "enc_c28")
    await usr_repo.add(usuario)

    asig_repo = AsignacionRepository(session=session, tenant_id=tid)
    asig = Asignacion(
        usuario_id=usuario.id,  # FK to usuario.id — NOT auth_identity_id
        rol=RolAsignacion.PROFESOR,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo.add(asig)
    await session.commit()
    await session.close()

    return {
        "tid": tid,
        "auth_id": auth_id,
        "domain_uid": usuario.id,
        "mat_id": materia.id,
        "car_id": carrera.id,
        "coh_id": cohorte.id,
        "asig_id": asig.id,
    }


@pytest.mark.asyncio(loop_scope="session")
async def test_encuentro_listar_instancias_uses_domain_user_id(db_session, create_tables, c28_enc_setup):
    """
    3.2 RED: listar_instancias (non-global role) must filter asignaciones by usuario.id.

    If it passes auth_identity_id (wrong UUID), it finds no asignaciones → returns empty.
    If it passes domain usuario.id (correct), it finds the asignacion and returns slot instances.
    """
    from app.models.encuentro import InstanciaEncuentro, InstanciaEncuentroEstado, SlotEncuentro
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.encuentro_repository import (
        InstanciaEncuentroRepository,
        SlotEncuentroRepository,
    )
    from app.repositories.usuario_repository import AsignacionRepository
    from app.services.encuentro_service import EncuentroService

    ctx = c28_enc_setup
    tid = ctx["tid"]
    auth_id = ctx["auth_id"]
    domain_uid = ctx["domain_uid"]
    mat_id = ctx["mat_id"]
    asig_id = ctx["asig_id"]

    # Invariant check
    assert auth_id != domain_uid, "Test setup invalid: auth_identity_id must differ from usuario.id"

    from datetime import time as dtime

    # Create slot + instance for this asignacion
    slot = SlotEncuentro(
        tenant_id=tid,
        asignacion_id=asig_id,
        materia_id=mat_id,
        titulo="C28 Enc Test Slot",
        hora=dtime(10, 0),
        cant_semanas=0,
        fecha_unica=date.today(),
    )
    db_session.add(slot)
    await db_session.flush()

    instancia = InstanciaEncuentro(
        tenant_id=tid,
        slot_id=slot.id,
        materia_id=mat_id,
        fecha=date.today(),
        hora=dtime(10, 0),
        titulo="C28 Enc Test Instancia",
        estado=InstanciaEncuentroEstado.Programado,
    )
    db_session.add(instancia)
    await db_session.commit()

    svc = EncuentroService(
        slot_repo=SlotEncuentroRepository(session=db_session, tenant_id=tid),
        instancia_repo=InstanciaEncuentroRepository(session=db_session, tenant_id=tid),
        asignacion_repo=AsignacionRepository(session=db_session, tenant_id=tid),
        audit_repo=AuditRepository(session=db_session, tenant_id=tid),
    )

    actor = _actor(tid, auth_id, roles=["PROFESOR"])

    # GREEN: with domain_uid → finds asignacion → returns instancia
    instancias_correct = await svc.listar_instancias(
        actor=actor,
        domain_user_id=domain_uid,
        materia_id=mat_id,
    )
    instancia_ids = [i.id for i in instancias_correct]
    assert instancia.id in instancia_ids, (
        f"Expected instancia {instancia.id} in results when using domain_uid={domain_uid}. "
        f"Got: {instancia_ids}. The service may be using auth_identity_id instead."
    )

    # 3.4 TRIANGULATE: with auth_id (wrong UUID) → finds NO asignacion → empty result
    instancias_wrong = await svc.listar_instancias(
        actor=actor,
        domain_user_id=auth_id,  # wrong UUID — no asignacion has this usuario_id
        materia_id=mat_id,
    )
    instancia_ids_wrong = [i.id for i in instancias_wrong]
    assert instancia.id not in instancia_ids_wrong, (
        "Using auth_identity_id should NOT find asignaciones (FK points to usuario.id). "
        "This confirms the test is not a tautology."
    )


# ---------------------------------------------------------------------------
# Task 4 — Guardias: consultar filters asignaciones by usuario.id
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def c28_grd_setup(test_engine, create_tables):
    """Creates tenant + two users with distinct auth_identity_ids + asignaciones."""
    from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository

    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    auth_id_1 = uuid.uuid4()
    auth_id_2 = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"C28GrdT_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await session.flush()

    carrera = Carrera(
        tenant_id=tid,
        codigo=f"C28GC_{uuid.uuid4().hex[:4]}",
        nombre="Carrera C28Grd",
        estado=EstadoEstructura.activa,
    )
    materia = Materia(
        tenant_id=tid,
        codigo=f"C28GM_{uuid.uuid4().hex[:4]}",
        nombre="Materia C28Grd",
        estado=EstadoEstructura.activa,
    )
    session.add_all([carrera, materia])
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre="Coh C28Grd",
        anio=2026,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    await session.flush()

    usr_repo = UsuarioRepository(session=session, tenant_id=tid)
    user1 = _make_usuario(tid, auth_id_1, "grd_c28_u1")
    user2 = _make_usuario(tid, auth_id_2, "grd_c28_u2")
    await usr_repo.add(user1)
    await usr_repo.add(user2)

    asig_repo = AsignacionRepository(session=session, tenant_id=tid)
    asig1 = Asignacion(
        usuario_id=user1.id,
        rol=RolAsignacion.TUTOR,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        desde=date.today(),
        comisiones=[],
    )
    asig2 = Asignacion(
        usuario_id=user2.id,
        rol=RolAsignacion.TUTOR,
        materia_id=materia.id,
        carrera_id=carrera.id,
        cohorte_id=cohorte.id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo.add(asig1)
    await asig_repo.add(asig2)
    await session.commit()
    await session.close()

    return {
        "tid": tid,
        "auth_id_1": auth_id_1,
        "auth_id_2": auth_id_2,
        "domain_uid_1": user1.id,
        "domain_uid_2": user2.id,
        "mat_id": materia.id,
        "car_id": carrera.id,
        "coh_id": cohorte.id,
        "asig_id_1": asig1.id,
        "asig_id_2": asig2.id,
    }


@pytest.mark.asyncio(loop_scope="session")
async def test_guardia_registrar_uses_domain_user_id(db_session, create_tables, c28_grd_setup):
    """
    4.2 RED: registrar guardia resolves asignacion_id via domain_user_id (usuario.id),
    not auth_identity_id.

    Invariant: domain_uid_1 != auth_id_1.
    If registrar is passed auth_id_1 (wrong), no asignacion is found → ValueError.
    If passed domain_uid_1 (correct), asignacion is found → guardia.asignacion_id is set.
    """
    from app.models.encuentro import DiaSemana, GuardiaEstado
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.guardia_repository import GuardiaRepository
    from app.repositories.usuario_repository import AsignacionRepository
    from app.schemas.guardia import RegistrarGuardiaRequest
    from app.services.guardia_service import GuardiaService

    ctx = c28_grd_setup
    tid = ctx["tid"]
    auth_id_1 = ctx["auth_id_1"]
    domain_uid_1 = ctx["domain_uid_1"]
    mat_id = ctx["mat_id"]
    car_id = ctx["car_id"]
    coh_id = ctx["coh_id"]
    asig_id_1 = ctx["asig_id_1"]

    assert auth_id_1 != domain_uid_1, "Test setup invalid: IDs must differ"

    svc = GuardiaService(
        guardia_repo=GuardiaRepository(session=db_session, tenant_id=tid),
        asignacion_repo=AsignacionRepository(session=db_session, tenant_id=tid),
        audit_repo=AuditRepository(session=db_session, tenant_id=tid),
    )
    actor = _actor(tid, auth_id_1, roles=["TUTOR"])
    req = RegistrarGuardiaRequest(
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        dia=DiaSemana.Lunes,
        horario="08:00-10:00",
    )

    # GREEN: with domain_uid_1 → finds asignacion → guardia registered correctly
    guardia = await svc.registrar(req, actor, domain_user_id=domain_uid_1)
    assert guardia.asignacion_id == asig_id_1, (
        f"Expected asig_id_1={asig_id_1}, got {guardia.asignacion_id}. "
        "The service may be using auth_identity_id for asignacion lookup."
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_guardia_registrar_with_wrong_id_raises(db_session, create_tables, c28_grd_setup):
    """
    4.4 TRIANGULATE: registrar with auth_identity_id (wrong) raises ValueError
    because no asignacion has usuario_id == auth_identity_id.
    """
    from app.models.encuentro import DiaSemana
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.guardia_repository import GuardiaRepository
    from app.repositories.usuario_repository import AsignacionRepository
    from app.schemas.guardia import RegistrarGuardiaRequest
    from app.services.guardia_service import GuardiaService

    ctx = c28_grd_setup
    tid = ctx["tid"]
    auth_id_1 = ctx["auth_id_1"]
    mat_id = ctx["mat_id"]
    car_id = ctx["car_id"]
    coh_id = ctx["coh_id"]

    svc = GuardiaService(
        guardia_repo=GuardiaRepository(session=db_session, tenant_id=tid),
        asignacion_repo=AsignacionRepository(session=db_session, tenant_id=tid),
        audit_repo=AuditRepository(session=db_session, tenant_id=tid),
    )
    actor = _actor(tid, auth_id_1, roles=["TUTOR"])
    req = RegistrarGuardiaRequest(
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        dia=DiaSemana.Martes,
        horario="10:00-12:00",
    )

    # Passing auth_id as domain_user_id → no asignacion found → ValueError
    with pytest.raises(ValueError, match="no tiene ninguna asignación activa"):
        await svc.registrar(req, actor, domain_user_id=auth_id_1)


@pytest.mark.asyncio(loop_scope="session")
async def test_guardia_consultar_isolates_by_domain_user_id(db_session, create_tables, c28_grd_setup):
    """
    4.4 TRIANGULATE: two actors with different asignaciones see only their own guardias.
    """
    from app.models.encuentro import DiaSemana
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.guardia_repository import GuardiaRepository
    from app.repositories.usuario_repository import AsignacionRepository
    from app.schemas.guardia import GuardiaFiltros, RegistrarGuardiaRequest
    from app.services.guardia_service import GuardiaService

    ctx = c28_grd_setup
    tid = ctx["tid"]
    auth_id_1 = ctx["auth_id_1"]
    auth_id_2 = ctx["auth_id_2"]
    domain_uid_1 = ctx["domain_uid_1"]
    domain_uid_2 = ctx["domain_uid_2"]
    mat_id = ctx["mat_id"]
    car_id = ctx["car_id"]
    coh_id = ctx["coh_id"]

    assert domain_uid_1 != domain_uid_2, "Test setup invalid"

    svc = GuardiaService(
        guardia_repo=GuardiaRepository(session=db_session, tenant_id=tid),
        asignacion_repo=AsignacionRepository(session=db_session, tenant_id=tid),
        audit_repo=AuditRepository(session=db_session, tenant_id=tid),
    )

    actor1 = _actor(tid, auth_id_1, roles=["TUTOR"])
    actor2 = _actor(tid, auth_id_2, roles=["TUTOR"])

    req = RegistrarGuardiaRequest(
        materia_id=mat_id, carrera_id=car_id, cohorte_id=coh_id,
        dia=DiaSemana.Miercoles, horario="14:00-16:00",
    )

    guardia1 = await svc.registrar(req, actor1, domain_user_id=domain_uid_1)
    guardia2 = await svc.registrar(req, actor2, domain_user_id=domain_uid_2)

    filtros = GuardiaFiltros()

    # Actor1 (domain_uid_1) sees their own guardias, NOT actor2's
    guardias_1 = await svc.consultar(filtros, actor1, domain_user_id=domain_uid_1)
    ids_1 = [g.id for g in guardias_1]
    assert guardia1.id in ids_1
    assert guardia2.id not in ids_1, (
        "Actor1 should NOT see actor2's guardias. Isolation via usuario.id is broken."
    )

    # Actor2 (domain_uid_2) sees their own guardias, NOT actor1's
    guardias_2 = await svc.consultar(filtros, actor2, domain_user_id=domain_uid_2)
    ids_2 = [g.id for g in guardias_2]
    assert guardia2.id in ids_2
    assert guardia1.id not in ids_2, (
        "Actor2 should NOT see actor1's guardias. Isolation via usuario.id is broken."
    )


# ---------------------------------------------------------------------------
# Task 5 — Padrón: vaciar compares cargado_por against domain_user_id
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def c28_padron_setup(test_engine, create_tables):
    """Creates tenant + materia + cohorte for padron tests."""
    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"C28PadronT_{tid.hex[:4]}", estado=TenantEstado.ACTIVO))
    await session.flush()

    carrera = Carrera(
        tenant_id=tid,
        codigo=f"C28PC_{uuid.uuid4().hex[:4]}",
        nombre="Carrera C28Padron",
        estado=EstadoEstructura.activa,
    )
    materia = Materia(
        tenant_id=tid,
        codigo=f"C28PM_{uuid.uuid4().hex[:4]}",
        nombre="Materia C28Padron",
        estado=EstadoEstructura.activa,
    )
    session.add_all([carrera, materia])
    await session.flush()

    cohorte = Cohorte(
        tenant_id=tid,
        carrera_id=carrera.id,
        nombre="Coh C28Padron",
        anio=2026,
        vig_desde=date.today(),
        estado=EstadoEstructura.activa,
    )
    session.add(cohorte)
    await session.commit()
    await session.close()

    return {
        "tid": tid,
        "mat_id": materia.id,
        "coh_id": cohorte.id,
    }


@pytest.mark.asyncio(loop_scope="session")
async def test_padron_vaciar_owner_can_delete_own_version(db_session, create_tables, c28_padron_setup):
    """
    5.2 RED: PROFESOR can vaciar version they loaded (cargado_por == domain_user_id).
    """
    from fastapi import HTTPException
    from app.models.padron import VersionPadron
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.padron_repository import PadronRepository
    from app.services.padron_service import PadronService

    ctx = c28_padron_setup
    tid = ctx["tid"]
    mat_id = ctx["mat_id"]
    coh_id = ctx["coh_id"]

    auth_id = uuid.uuid4()
    usuario = _make_usuario(tid, auth_id, "padron_owner")
    db_session.add(usuario)
    await db_session.flush()
    domain_uid = usuario.id
    assert auth_id != domain_uid

    # Create a version with cargado_por = domain_uid (the correct FK)
    version = VersionPadron(
        tenant_id=tid,
        materia_id=mat_id,
        cohorte_id=coh_id,
        activa=True,
        cargado_por=domain_uid,  # FK to usuario.id
    )
    db_session.add(version)
    await db_session.commit()

    svc = PadronService(
        repo=PadronRepository(session=db_session, tenant_id=tid),
        db=db_session,
        audit_repo=AuditRepository(session=db_session, tenant_id=tid),
    )
    actor = _actor(tid, auth_id, roles=["PROFESOR"])

    # Owner with domain_uid can vaciar — should NOT raise 403
    await svc.vaciar(
        materia_id=mat_id,
        cohorte_id=coh_id,
        current_user=actor,
        has_gestionar=False,
        domain_user_id=domain_uid,  # correct: usuario.id
    )
    # If we reach here, the ownership check passed correctly


@pytest.mark.asyncio(loop_scope="session")
async def test_padron_vaciar_non_owner_raises_403(db_session, create_tables, c28_padron_setup):
    """
    5.4 TRIANGULATE: PROFESOR cannot vaciar version loaded by another user.
    cargado_por is owner's domain_uid; other user has a different domain_uid.
    """
    from fastapi import HTTPException
    from app.models.padron import VersionPadron
    from app.repositories.audit_repository import AuditRepository
    from app.repositories.padron_repository import PadronRepository
    from app.services.padron_service import PadronService

    ctx = c28_padron_setup
    tid = ctx["tid"]
    mat_id = ctx["mat_id"]
    coh_id = ctx["coh_id"]

    auth_id_owner = uuid.uuid4()
    auth_id_other = uuid.uuid4()

    owner = _make_usuario(tid, auth_id_owner, "padron_real_owner")
    other = _make_usuario(tid, auth_id_other, "padron_non_owner")
    db_session.add(owner)
    db_session.add(other)
    await db_session.flush()

    domain_uid_owner = owner.id
    domain_uid_other = other.id
    assert auth_id_owner != domain_uid_owner
    assert auth_id_other != domain_uid_other
    assert domain_uid_owner != domain_uid_other

    # Version loaded by domain_uid_owner; create a NEW version after previous test deleted it
    version = VersionPadron(
        tenant_id=tid,
        materia_id=mat_id,
        cohorte_id=coh_id,
        activa=True,
        cargado_por=domain_uid_owner,
    )
    db_session.add(version)
    await db_session.commit()

    svc = PadronService(
        repo=PadronRepository(session=db_session, tenant_id=tid),
        db=db_session,
        audit_repo=AuditRepository(session=db_session, tenant_id=tid),
    )
    # Non-owner actor
    actor_other = _actor(tid, auth_id_other, roles=["PROFESOR"])

    # Non-owner passing their domain_uid → should get 403
    with pytest.raises(HTTPException) as exc_info:
        await svc.vaciar(
            materia_id=mat_id,
            cohorte_id=coh_id,
            current_user=actor_other,
            has_gestionar=False,
            domain_user_id=domain_uid_other,  # different user
        )
    assert exc_info.value.status_code == 403

    # CRITICAL: if they passed auth_identity_id (wrong UUID), the check would also fail
    # but for the WRONG reason (it wouldn't match the domain FK).
    # This test specifically verifies the check uses domain_user_id correctly.


# ---------------------------------------------------------------------------
# Task 6 — Fallback hardening: services must reject missing domain_user_id
# ---------------------------------------------------------------------------

def test_guardia_consultar_requires_domain_user_id():
    """
    6.2 RED: GuardiaService.consultar signature has domain_user_id: uuid.UUID (no Optional default).
    Calling without it raises TypeError.
    """
    import inspect
    from app.services.guardia_service import GuardiaService

    sig = inspect.signature(GuardiaService.consultar)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from GuardiaService.consultar"
    # Must not have a default (required parameter)
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_guardia_registrar_requires_domain_user_id():
    """
    6.2 TRIANGULATE: GuardiaService.registrar requires domain_user_id.
    """
    import inspect
    from app.services.guardia_service import GuardiaService

    sig = inspect.signature(GuardiaService.registrar)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from GuardiaService.registrar"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_encuentro_crear_slot_requires_domain_user_id():
    """
    6.3 RED: EncuentroService.crear_slot requires domain_user_id (no Optional fallback).
    """
    import inspect
    from app.services.encuentro_service import EncuentroService

    sig = inspect.signature(EncuentroService.crear_slot)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from EncuentroService.crear_slot"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_encuentro_listar_instancias_requires_domain_user_id():
    """
    6.3 TRIANGULATE: EncuentroService.listar_instancias requires domain_user_id.
    """
    import inspect
    from app.services.encuentro_service import EncuentroService

    sig = inspect.signature(EncuentroService.listar_instancias)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from EncuentroService.listar_instancias"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_padron_vaciar_requires_domain_user_id():
    """
    6.4 RED: PadronService.vaciar requires domain_user_id (no Optional fallback).
    """
    import inspect
    from app.services.padron_service import PadronService

    sig = inspect.signature(PadronService.vaciar)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from PadronService.vaciar"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_padron_activar_requires_domain_user_id():
    """
    6.4 TRIANGULATE: PadronService.activar requires domain_user_id (no Optional fallback).
    """
    import inspect
    from app.services.padron_service import PadronService

    sig = inspect.signature(PadronService.activar)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from PadronService.activar"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_calificacion_service_importar_requires_domain_user_id():
    """
    6.5 RED: CalificacionService.importar requires domain_user_id (no Optional fallback).
    """
    import inspect
    from app.services.calificacion_service import CalificacionService

    sig = inspect.signature(CalificacionService.importar)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from CalificacionService.importar"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_equipo_service_listar_mis_equipos_requires_domain_user_id():
    """
    6.6 RED: EquipoService.listar_mis_equipos requires domain_user_id (no Optional/fallback).
    """
    import inspect
    from app.services.equipo_service import EquipoService

    sig = inspect.signature(EquipoService.listar_mis_equipos)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from EquipoService.listar_mis_equipos"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_alumno_service_requires_domain_user_id():
    """
    6.7 RED: AlumnoService.get_estado_academico requires domain_user_id (no Optional fallback).
    """
    import inspect
    from app.services.alumno_service import AlumnoService

    sig = inspect.signature(AlumnoService.get_estado_academico)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from AlumnoService.get_estado_academico"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_analisis_service_atrasados_requires_domain_user_id():
    """
    6.8 RED: AnalisisService.atrasados requires domain_user_id (no Optional fallback).
    """
    import inspect
    from app.services.analisis_service import AnalisisService

    sig = inspect.signature(AnalisisService.atrasados)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from AnalisisService.atrasados"
    assert param.default is inspect.Parameter.empty, (
        f"domain_user_id must be required (no default), got default={param.default}"
    )


def test_analisis_service_ranking_requires_domain_user_id():
    """
    6.8 TRIANGULATE: AnalisisService.ranking requires domain_user_id.
    """
    import inspect
    from app.services.analisis_service import AnalisisService

    sig = inspect.signature(AnalisisService.ranking)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from AnalisisService.ranking"
    assert param.default is inspect.Parameter.empty


def test_analisis_service_notas_finales_requires_domain_user_id():
    """
    6.8 TRIANGULATE: AnalisisService.notas_finales requires domain_user_id.
    """
    import inspect
    from app.services.analisis_service import AnalisisService

    sig = inspect.signature(AnalisisService.notas_finales)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from AnalisisService.notas_finales"
    assert param.default is inspect.Parameter.empty


def test_analisis_service_monitor_requires_domain_user_id():
    """
    6.8 TRIANGULATE: AnalisisService.monitor requires domain_user_id.
    """
    import inspect
    from app.services.analisis_service import AnalisisService

    sig = inspect.signature(AnalisisService.monitor)
    param = sig.parameters.get("domain_user_id")
    assert param is not None, "domain_user_id parameter missing from AnalisisService.monitor"
    assert param.default is inspect.Parameter.empty
