"""
test_encuentros.py — TDD suite para C-13 encuentros (slots + instancias).

RED → GREEN → TRIANGULATE → REFACTOR cycle para tasks 7.1–7.9.

Tests:
    7.1 RED:  test_crear_slot_recurrente_genera_n_instancias
    7.3 RED:  test_crear_encuentro_unico_genera_una_instancia
    7.4 RED:  test_crear_slot_ambos_modos_raises_422 / test_crear_slot_ningun_modo_raises_422
    7.5 RED:  test_editar_instancia_actualiza_estado_y_video
    7.6 RED:  test_editar_instancia_no_afecta_hermanas
    7.7 RED:  test_listar_encuentros_coordinador_ve_todos / test_listar_encuentros_profesor_ve_solo_propios
    7.8 RED:  test_crear_slot_records_audit_encuentro_gestionar
    7.9 RED:  test_encuentros_tenant_isolation

DB real: activia_trace_test. Sin mocks de DB.
"""
import datetime
import uuid
from datetime import date, time
from typing import Tuple

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.database import build_session_factory
from app.core.dependencies import CurrentUser
from app.models.audit import AuditAction, AuditEvent
from app.models.encuentro import DiaSemana, GuardiaEstado, InstanciaEncuentroEstado
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.repositories.audit_repository import AuditRepository
from app.repositories.encuentro_repository import (
    InstanciaEncuentroRepository,
    SlotEncuentroRepository,
)
from app.repositories.usuario_repository import AsignacionRepository, UsuarioRepository
from app.schemas.encuentro import (
    BloqueHtmlResponse,
    CrearSlotRequest,
    EditarInstanciaRequest,
)
from app.services.encuentro_service import EncuentroService, EncuentroValidationError
from tests.conftest import create_usuario_con_identidad


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list, secret: str = TEST_SECRET_KEY) -> str:
    from jose import jwt as jose_jwt
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    exp = now + datetime.timedelta(minutes=30)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jose_jwt.encode(payload, secret, algorithm="HS256")


def _fake_settings():
    class FakeSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
    return FakeSettings()


def _make_current_user(tid: uuid.UUID, uid: uuid.UUID, roles: list | None = None) -> CurrentUser:
    return CurrentUser(user_id=uid, tenant_id=tid, roles=roles or ["TESTROL"])


def _make_usuario(tid: uuid.UUID, suffix: str) -> Usuario:
    """Build a Usuario model instance for service-only tests (no JWT/HTTP needed).

    Does NOT create an AuthIdentity row. Only use in service-layer tests where
    the actor is a CurrentUser built directly (not via JWT → resolve_domain_user_id).
    For HTTP/endpoint tests, use create_usuario_con_identidad from conftest instead.
    """
    from app.core.security.passwords import email_lookup_hash as _hash
    email = f"enc_{suffix}_{uuid.uuid4().hex[:6]}@test.com"
    return Usuario(
        tenant_id=tid,
        email_encrypted=email,
        email_hash=_hash(email),
        nombre="Test",
        apellidos=suffix,
        estado=UsuarioEstado.activo,
    )


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def enc_setup(test_engine, create_tables):
    """
    Creates two tenants with minimal RBAC + academic structure.
    Returns context dict with all IDs needed by tests.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Enc Tenant A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Enc Tenant B", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Create roles for permission seeding
    rol_a = Rol(tenant_id=tid_a, nombre="ENC_ROL_A")
    rol_b = Rol(tenant_id=tid_b, nombre="ENC_ROL_B")
    rol_coord_a = Rol(tenant_id=tid_a, nombre="ENC_COORD_A")
    session.add_all([rol_a, rol_b, rol_coord_a])
    await session.flush()

    # Permissions
    perm_a = Permiso(tenant_id=tid_a, codigo="encuentros:gestionar", modulo="encuentros", accion="gestionar")
    perm_b = Permiso(tenant_id=tid_b, codigo="encuentros:gestionar", modulo="encuentros", accion="gestionar")
    session.add_all([perm_a, perm_b])
    await session.flush()

    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_a.id, permiso_id=perm_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_b.id, permiso_id=perm_b.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_coord_a.id, permiso_id=perm_a.id, scope=PermisoScope.global_))
    await session.flush()

    # Academic structure for tenant A
    carrera_a = Carrera(tenant_id=tid_a, codigo=f"CA_{uuid.uuid4().hex[:4]}", nombre="Carrera A", estado=EstadoEstructura.activa)
    materia_a = Materia(tenant_id=tid_a, codigo=f"MA_{uuid.uuid4().hex[:4]}", nombre="Materia A", estado=EstadoEstructura.activa)
    session.add(carrera_a)
    session.add(materia_a)
    await session.flush()

    cohorte_a = Cohorte(tenant_id=tid_a, carrera_id=carrera_a.id, nombre="Coh A", anio=2026, vig_desde=date.today(), estado=EstadoEstructura.activa)
    session.add(cohorte_a)
    await session.flush()

    # Academic structure for tenant B
    carrera_b = Carrera(tenant_id=tid_b, codigo=f"CB_{uuid.uuid4().hex[:4]}", nombre="Carrera B", estado=EstadoEstructura.activa)
    materia_b = Materia(tenant_id=tid_b, codigo=f"MB_{uuid.uuid4().hex[:4]}", nombre="Materia B", estado=EstadoEstructura.activa)
    session.add(carrera_b)
    session.add(materia_b)
    await session.flush()

    cohorte_b = Cohorte(tenant_id=tid_b, carrera_id=carrera_b.id, nombre="Coh B", anio=2026, vig_desde=date.today(), estado=EstadoEstructura.activa)
    session.add(cohorte_b)

    # Create users + asignaciones for tenant A
    # C-28: use canonical helper — creates AuthIdentity + Usuario with auth_identity_id != usuario.id.
    # HTTP tests: JWT sub = usuario.auth_identity_id (auth_a / auth_coord keys).
    # Service tests: domain_user_id = usuario.id (user_a / user_coord keys).
    user_a = await create_usuario_con_identidad(
        session, tid_a,
        email=f"enc_a_{uuid.uuid4().hex[:6]}@test.com",
        nombre="Test", apellidos="enc_a",
    )
    user_coord = await create_usuario_con_identidad(
        session, tid_a,
        email=f"enc_coord_{uuid.uuid4().hex[:6]}@test.com",
        nombre="Test", apellidos="enc_coord",
    )

    # Asignacion for user_a (PROFESOR) on materia_a
    asig_repo_a = AsignacionRepository(session=session, tenant_id=tid_a)
    asig_a = Asignacion(
        usuario_id=user_a.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia_a.id,
        carrera_id=carrera_a.id,
        cohorte_id=cohorte_a.id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo_a.add(asig_a)

    await session.commit()
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "rol_a": "ENC_ROL_A",
        "rol_b": "ENC_ROL_B",
        "rol_coord": "ENC_COORD_A",
        "mat_a": materia_a.id,
        "car_a": carrera_a.id,
        "coh_a": cohorte_a.id,
        "mat_b": materia_b.id,
        "car_b": carrera_b.id,
        "coh_b": cohorte_b.id,
        "user_a": user_a.id,
        "user_coord": user_coord.id,
        "asig_a": asig_a.id,
        # C-28: HTTP tests MUST use these as JWT sub (auth_identity_id != usuario.id)
        "auth_a": user_a.auth_identity_id,
        "auth_coord": user_coord.auth_identity_id,
    }


@pytest_asyncio.fixture(scope="module")
def enc_app(test_engine, enc_setup):
    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


@pytest_asyncio.fixture(scope="module")
async def enc_client(enc_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=enc_app), base_url="http://test"
    ) as client:
        yield client


def _make_enc_service(session, tenant_id):
    slot_repo = SlotEncuentroRepository(session=session, tenant_id=tenant_id)
    inst_repo = InstanciaEncuentroRepository(session=session, tenant_id=tenant_id)
    asig_repo = AsignacionRepository(session=session, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=session, tenant_id=tenant_id)
    return EncuentroService(
        slot_repo=slot_repo,
        instancia_repo=inst_repo,
        asignacion_repo=asig_repo,
        audit_repo=audit_repo,
    )


# ---------------------------------------------------------------------------
# 7.1 RED → 7.2 GREEN
# test_crear_slot_recurrente_genera_n_instancias
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_recurrente_genera_n_instancias(db_session, create_tables, enc_setup, monkeypatch):
    """7.1 RED: crear_slot con cant_semanas=4 → 4 instancias Programado, slot_id set, tenant_id correcto."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    asig_id = enc_setup["asig_a"]
    user_id = enc_setup["user_a"]

    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Clase Recurrente",
        hora=time(18, 0),
        dia_semana=DiaSemana.Lunes,
        fecha_inicio=date(2026, 6, 8),  # Monday
        cant_semanas=4,
    )
    actor = _make_current_user(tid, user_id)

    svc = _make_enc_service(db_session, tid)
    result = await svc.crear_slot(req, actor, domain_user_id=user_id)

    assert result.slot.titulo == "Clase Recurrente"
    assert len(result.instancias) == 4
    for inst in result.instancias:
        assert inst.estado == InstanciaEncuentroEstado.Programado
        assert inst.slot_id == result.slot.id

    # Verify tenant_id in DB
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    db_instancias = await inst_repo.list_by_slot(result.slot.id)
    assert len(db_instancias) == 4
    for db_inst in db_instancias:
        assert db_inst.tenant_id == tid

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(result.slot.id)
    if slot:
        await slot_repo.delete(slot)
    for db_inst in db_instancias:
        await inst_repo.delete(db_inst)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 7.3 RED → GREEN
# test_crear_encuentro_unico_genera_una_instancia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_encuentro_unico_genera_una_instancia(db_session, create_tables, enc_setup, monkeypatch):
    """7.3 RED: fecha_unica set, cant_semanas=0 → 1 instancia con fecha=fecha_unica."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]

    fecha_unica = date(2026, 7, 15)
    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Clase Única",
        hora=time(10, 0),
        fecha_unica=fecha_unica,
        cant_semanas=0,
    )
    actor = _make_current_user(tid, user_id)

    svc = _make_enc_service(db_session, tid)
    result = await svc.crear_slot(req, actor, domain_user_id=user_id)

    assert len(result.instancias) == 1
    assert result.instancias[0].fecha == fecha_unica

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(result.slot.id)
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(result.slot.id)
    for inst in db_insts:
        await inst_repo.delete(inst)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 7.4 RED → GREEN: mode validation (RN-13)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_ambos_modos_raises_422(db_session, create_tables, enc_setup, monkeypatch):
    """7.4 RED: both cant_semanas>0 AND fecha_unica → EncuentroValidationError(422)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]

    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Conflicto de modo",
        hora=time(9, 0),
        dia_semana=DiaSemana.Martes,
        fecha_inicio=date(2026, 6, 2),
        cant_semanas=2,
        fecha_unica=date(2026, 7, 1),  # both modes!
    )
    actor = _make_current_user(tid, user_id)
    svc = _make_enc_service(db_session, tid)

    with pytest.raises(EncuentroValidationError):
        await svc.crear_slot(req, actor, domain_user_id=user_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_ningun_modo_raises_422(db_session, create_tables, enc_setup, monkeypatch):
    """7.4 RED: neither cant_semanas>0 nor fecha_unica → EncuentroValidationError(422)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]

    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Sin modo",
        hora=time(9, 0),
        cant_semanas=0,
        fecha_unica=None,
    )
    actor = _make_current_user(tid, user_id)
    svc = _make_enc_service(db_session, tid)

    with pytest.raises(EncuentroValidationError):
        await svc.crear_slot(req, actor, domain_user_id=user_id)


# ---------------------------------------------------------------------------
# 7.5 RED → GREEN: editar instancia (RN-14)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_editar_instancia_actualiza_estado_y_video(db_session, create_tables, enc_setup, monkeypatch):
    """7.5 RED: set Realizado + video_url → instance updated, slot/siblings unchanged."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]

    # Create slot with 3 instances
    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Slot para editar",
        hora=time(15, 0),
        dia_semana=DiaSemana.Miercoles,
        fecha_inicio=date(2026, 7, 1),
        cant_semanas=3,
    )
    actor = _make_current_user(tid, user_id)
    svc = _make_enc_service(db_session, tid)
    created = await svc.crear_slot(req, actor, domain_user_id=user_id)

    target_id = created.instancias[0].id
    patch = EditarInstanciaRequest(
        estado=InstanciaEncuentroEstado.Realizado,
        video_url="https://vimeo.com/edited",
    )
    updated = await svc.editar_instancia(target_id, patch, actor)

    assert updated.estado == InstanciaEncuentroEstado.Realizado
    assert updated.video_url == "https://vimeo.com/edited"

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(created.slot.id)
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(created.slot.id)
    for inst in db_insts:
        await inst_repo.delete(inst)
    # Also cleanup the edited one (might not be in the slot query anymore if already deleted)
    from sqlalchemy import select
    from app.models.encuentro import InstanciaEncuentro
    stmt = select(InstanciaEncuentro).where(InstanciaEncuentro.id == target_id, InstanciaEncuentro.tenant_id == tid)
    r = await db_session.execute(stmt)
    remaining = r.scalar_one_or_none()
    if remaining and remaining.deleted_at is None:
        await inst_repo.delete(remaining)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 7.6 RED → GREEN: sibling independence (RN-14)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_editar_instancia_no_afecta_hermanas(db_session, create_tables, enc_setup, monkeypatch):
    """7.6 RED: cancel one instance → other 2 siblings unchanged (Programado)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]

    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Slot hermanas",
        hora=time(16, 0),
        dia_semana=DiaSemana.Viernes,
        fecha_inicio=date(2026, 8, 7),
        cant_semanas=3,
    )
    actor = _make_current_user(tid, user_id)
    svc = _make_enc_service(db_session, tid)
    created = await svc.crear_slot(req, actor, domain_user_id=user_id)

    instancias = created.instancias
    assert len(instancias) == 3

    # Cancel only the first instance
    patch = EditarInstanciaRequest(estado=InstanciaEncuentroEstado.Cancelado)
    await svc.editar_instancia(instancias[0].id, patch, actor)

    # Load siblings from DB and verify they are still Programado
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    for inst_read in instancias[1:]:
        db_inst = await inst_repo.get_by_id(inst_read.id)
        assert db_inst is not None
        assert db_inst.estado == InstanciaEncuentroEstado.Programado

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(created.slot.id)
    if slot:
        await slot_repo.delete(slot)
    for inst_read in instancias:
        from sqlalchemy import select
        from app.models.encuentro import InstanciaEncuentro
        stmt = select(InstanciaEncuentro).where(
            InstanciaEncuentro.id == inst_read.id,
            InstanciaEncuentro.tenant_id == tid,
        )
        r = await db_session.execute(stmt)
        inst_obj = r.scalar_one_or_none()
        if inst_obj and inst_obj.deleted_at is None:
            await inst_repo.delete(inst_obj)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 7.7 RED → GREEN: role-scoped listing (D11)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_listar_encuentros_coordinador_ve_todos(db_session, create_tables, enc_setup, monkeypatch):
    """7.7 RED: COORDINADOR/ADMIN sees all instances of the tenant."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]
    user_coord = enc_setup["user_coord"]

    # Create slot as PROFESOR
    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Para coordinador",
        hora=time(17, 0),
        dia_semana=DiaSemana.Jueves,
        fecha_inicio=date(2026, 9, 3),
        cant_semanas=2,
    )
    actor_profesor = _make_current_user(tid, user_id, roles=["PROFESOR"])
    svc = _make_enc_service(db_session, tid)
    created = await svc.crear_slot(req, actor_profesor, domain_user_id=user_id)

    # COORDINADOR should see all instances (no materia filter, no asignacion filter)
    actor_coord = _make_current_user(tid, user_coord, roles=["COORDINADOR"])
    instancias = await svc.listar_instancias(actor=actor_coord, domain_user_id=user_coord, materia_id=None)

    ids = {inst.id for inst in instancias}
    for inst in created.instancias:
        assert inst.id in ids, f"Coordinador should see instance {inst.id}"

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(created.slot.id)
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(created.slot.id)
    for inst in db_insts:
        await inst_repo.delete(inst)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_listar_encuentros_profesor_ve_solo_propios(db_session, create_tables, enc_setup, monkeypatch):
    """7.7 RED: PROFESOR sees only instances from their own asignaciones."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    car_id = enc_setup["car_a"]
    coh_id = enc_setup["coh_a"]
    user_id = enc_setup["user_a"]

    # Create a SECOND user + asignacion (otro profesor)
    usr_repo = UsuarioRepository(session=db_session, tenant_id=tid)
    asig_repo = AsignacionRepository(session=db_session, tenant_id=tid)
    user2 = _make_usuario(tid, "prof2")
    await usr_repo.add(user2)
    asig2 = Asignacion(
        usuario_id=user2.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=mat_id,
        carrera_id=car_id,
        cohorte_id=coh_id,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo.add(asig2)

    actor1 = _make_current_user(tid, user_id, roles=["PROFESOR"])
    actor2 = _make_current_user(tid, user2.id, roles=["PROFESOR"])
    svc = _make_enc_service(db_session, tid)

    # Create slot for user1
    req1 = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Slot de prof1",
        hora=time(8, 0),
        dia_semana=DiaSemana.Lunes,
        fecha_inicio=date(2026, 10, 5),
        cant_semanas=2,
    )
    created1 = await svc.crear_slot(req1, actor1, domain_user_id=user_id)

    # Create slot for user2
    req2 = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Slot de prof2",
        hora=time(9, 0),
        dia_semana=DiaSemana.Martes,
        fecha_inicio=date(2026, 10, 6),
        cant_semanas=2,
    )
    created2 = await svc.crear_slot(req2, actor2, domain_user_id=user2.id)

    # PROFESOR 1 should only see their own instances
    instancias1 = await svc.listar_instancias(actor=actor1, domain_user_id=user_id, materia_id=None)
    ids1 = {inst.id for inst in instancias1}

    for inst in created1.instancias:
        assert inst.id in ids1, "Prof1 should see their own instances"
    for inst in created2.instancias:
        assert inst.id not in ids1, "Prof1 should NOT see prof2's instances"

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    for created in [created1, created2]:
        slot = await slot_repo.get_by_id(created.slot.id)
        if slot:
            await slot_repo.delete(slot)
        db_insts = await inst_repo.list_by_slot(created.slot.id)
        for inst in db_insts:
            await inst_repo.delete(inst)
    await asig_repo.delete(asig2)
    await usr_repo.delete(user2)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 7.8 RED → GREEN: audit logging
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_records_audit_encuentro_gestionar(db_session, create_tables, enc_setup, monkeypatch):
    """7.8 RED: crear_slot emits AuditEvent with accion=ENCUENTRO_GESTIONAR."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    user_id = enc_setup["user_a"]
    # Use user_id which has a real asignacion in the DB
    actor_id = user_id

    req = CrearSlotRequest(
        materia_id=mat_id,
        titulo="Slot Auditado",
        hora=time(11, 0),
        fecha_unica=date(2026, 11, 5),
    )
    actor = _make_current_user(tid, actor_id)
    svc = _make_enc_service(db_session, tid)
    result = await svc.crear_slot(req, actor, domain_user_id=actor_id)

    from sqlalchemy import select
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == tid,
            AuditEvent.actor_user_id == actor_id,
            AuditEvent.accion == AuditAction.ENCUENTRO_GESTIONAR,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    r = await db_session.execute(stmt)
    event = r.scalar_one_or_none()
    assert event is not None, "Audit event ENCUENTRO_GESTIONAR not emitted"
    assert event.registros_afectados == 1

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(result.slot.id)
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(result.slot.id)
    for inst in db_insts:
        await inst_repo.delete(inst)
    await db_session.commit()


# ---------------------------------------------------------------------------
# 7.9 RED → GREEN: tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_encuentros_tenant_isolation(db_session, create_tables, enc_setup, monkeypatch):
    """7.9 RED: T1 slots/instances not visible in T2."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tid_a = enc_setup["tid_a"]
    tid_b = enc_setup["tid_b"]
    mat_a = enc_setup["mat_a"]
    mat_b = enc_setup["mat_b"]
    user_a = enc_setup["user_a"]

    # Create slot in tenant A
    # First need an asignacion in tenant B
    car_b = enc_setup["car_b"]
    coh_b = enc_setup["coh_b"]
    usr_repo_b = UsuarioRepository(session=db_session, tenant_id=tid_b)
    asig_repo_b = AsignacionRepository(session=db_session, tenant_id=tid_b)
    user_b = _make_usuario(tid_b, "tenb_enc")
    await usr_repo_b.add(user_b)
    asig_b = Asignacion(
        usuario_id=user_b.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=mat_b,
        carrera_id=car_b,
        cohorte_id=coh_b,
        desde=date.today(),
        comisiones=[],
    )
    await asig_repo_b.add(asig_b)

    # user_a has an asignacion in tenant A (PROFESOR on mat_a)
    actor_a = _make_current_user(tid_a, user_a, roles=["PROFESOR"])
    actor_b = _make_current_user(tid_b, user_b.id, roles=["PROFESOR"])

    svc_a = _make_enc_service(db_session, tid_a)
    svc_b = _make_enc_service(db_session, tid_b)

    req_a = CrearSlotRequest(
        materia_id=mat_a,
        titulo="Slot Tenant A",
        hora=time(12, 0),
        fecha_unica=date(2026, 12, 1),
    )
    req_b = CrearSlotRequest(
        materia_id=mat_b,
        titulo="Slot Tenant B",
        hora=time(13, 0),
        fecha_unica=date(2026, 12, 2),
    )
    created_a = await svc_a.crear_slot(req_a, actor_a, domain_user_id=user_a)
    created_b = await svc_b.crear_slot(req_b, actor_b, domain_user_id=user_b.id)

    # Tenant A actor (with PROFESOR role = scoped to own slots) sees only tenant A instances
    # Both actors have PROFESOR role so listing is scoped to their own asignaciones
    instancias_a = await svc_a.listar_instancias(actor=actor_a, domain_user_id=user_a, materia_id=None)
    ids_a = {inst.id for inst in instancias_a}
    for inst in created_b.instancias:
        assert inst.id not in ids_a, "Tenant B instances must not appear in Tenant A listing"

    # Cleanup
    for tid, svc, created, usr_repo, asig_repo in [
        (tid_a, svc_a, created_a, None, None),
        (tid_b, svc_b, created_b, usr_repo_b, asig_repo_b),
    ]:
        slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
        inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
        slot = await slot_repo.get_by_id(created.slot.id)
        if slot:
            await slot_repo.delete(slot)
        db_insts = await inst_repo.list_by_slot(created.slot.id)
        for inst in db_insts:
            await inst_repo.delete(inst)
    await asig_repo_b.delete(asig_b)
    await usr_repo_b.delete(user_b)
    await db_session.commit()


# ---------------------------------------------------------------------------
# HTTP router integration tests (task 10)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_endpoint_unauthenticated_returns_401(enc_client):
    """10.1: POST /encuentros/slots without token → 401."""
    resp = await enc_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(uuid.uuid4()),
            "titulo": "Test",
            "hora": "18:00:00",
            "fecha_unica": "2026-12-01",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_endpoint_unauthorized_returns_403(enc_client, enc_setup, monkeypatch):
    """10.2: POST /encuentros/slots without permission → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = enc_setup["tid_a"]
    token = _make_jwt(tid, uuid.uuid4(), roles=["SIN_PERMISO"])
    resp = await enc_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(uuid.uuid4()),
            "titulo": "Test",
            "hora": "18:00:00",
            "fecha_unica": "2026-12-01",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_crear_slot_recurrente_endpoint_creates_instances(enc_client, enc_setup, db_session, monkeypatch):
    """10.3: POST /encuentros/slots recurrente → 201 con instancias."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    # C-28: JWT sub = auth_identity_id (NOT usuario.id) so resolve_domain_user_id works
    token = _make_jwt(tid, enc_setup["auth_a"], roles=[enc_setup["rol_a"]])

    resp = await enc_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(mat_id),
            "titulo": "Clase HTTP recurrente",
            "hora": "19:00:00",
            "dia_semana": "Lunes",
            "fecha_inicio": "2026-11-02",
            "cant_semanas": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "slot" in data
    assert "instancias" in data
    assert len(data["instancias"]) == 2

    # Cleanup
    slot_id = uuid.UUID(data["slot"]["id"])
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(slot_id)
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(slot_id)
    for inst in db_insts:
        await inst_repo.delete(inst)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_editar_instancia_endpoint_updates_estado(enc_client, enc_setup, db_session, monkeypatch):
    """10.4: PATCH /encuentros/instancias/{id} → 200 with updated estado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    # C-28: JWT sub = auth_identity_id (NOT usuario.id) so resolve_domain_user_id works
    token = _make_jwt(tid, enc_setup["auth_a"], roles=[enc_setup["rol_a"]])

    # Create slot first
    slot_resp = await enc_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(mat_id),
            "titulo": "Para editar",
            "hora": "08:00:00",
            "fecha_unica": "2026-12-10",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert slot_resp.status_code == 201
    instancia_id = slot_resp.json()["instancias"][0]["id"]
    slot_id = uuid.UUID(slot_resp.json()["slot"]["id"])

    # Edit the instance
    patch_resp = await enc_client.patch(
        f"/api/v1/encuentros/instancias/{instancia_id}",
        json={"estado": "Realizado"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["estado"] == "Realizado"

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(slot_id)
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(slot_id)
    for inst in db_insts:
        await inst_repo.delete(inst)
    from sqlalchemy import select
    from app.models.encuentro import InstanciaEncuentro
    stmt = select(InstanciaEncuentro).where(
        InstanciaEncuentro.id == uuid.UUID(instancia_id),
        InstanciaEncuentro.tenant_id == tid,
    )
    r = await db_session.execute(stmt)
    rem = r.scalar_one_or_none()
    if rem and rem.deleted_at is None:
        await inst_repo.delete(rem)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_bloque_html_endpoint_returns_html(enc_client, enc_setup, db_session, monkeypatch):
    """10.5: GET /encuentros/bloque-html → 200 with html field."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tid = enc_setup["tid_a"]
    mat_id = enc_setup["mat_a"]
    # C-28: JWT sub = auth_identity_id (NOT usuario.id) so resolve_domain_user_id works
    token = _make_jwt(tid, enc_setup["auth_a"], roles=[enc_setup["rol_a"]])

    # Create a slot first
    slot_resp = await enc_client.post(
        "/api/v1/encuentros/slots",
        json={
            "materia_id": str(mat_id),
            "titulo": "Para HTML",
            "hora": "20:00:00",
            "fecha_unica": "2026-12-15",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert slot_resp.status_code == 201
    slot_id = slot_resp.json()["slot"]["id"]

    resp = await enc_client.get(
        f"/api/v1/encuentros/bloque-html?materia_id={mat_id}&slot_id={slot_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "html" in data
    assert "Para HTML" in data["html"]

    # Cleanup
    slot_repo = SlotEncuentroRepository(session=db_session, tenant_id=tid)
    inst_repo = InstanciaEncuentroRepository(session=db_session, tenant_id=tid)
    slot = await slot_repo.get_by_id(uuid.UUID(slot_id))
    if slot:
        await slot_repo.delete(slot)
    db_insts = await inst_repo.list_by_slot(uuid.UUID(slot_id))
    for inst in db_insts:
        await inst_repo.delete(inst)
    await db_session.commit()
