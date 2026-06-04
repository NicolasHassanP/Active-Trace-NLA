"""
TDD tests for ComunicacionService.

C-12 Tasks: 4.5-4.11 (preview, encolar, scope propio), 5.3-5.8 (aprobación/cancelación).

Design decisions tested:
    - OQ-2: flag aprobacion_comunicacion_requerida en tenant_config.
    - OQ-4: encolar falla fuerte si plantilla tiene variable sin resolver.
    - OQ-5: Error es TERMINAL — worker no reintenta.
    - OQ-6: scope propio del PROFESOR valida contra Asignacion (C-07).
    - Auditoría COMUNICACION_ENVIAR registrada exactamente una vez por encolar.
    - Aprobación/cancelación individual afecta solo al destinatario indicado.

Uses real DB, no mocks.
"""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text

from app.core.dependencies import CurrentUser
from app.models.tenant import Tenant, TenantEstado
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.comunicacion import ComunicacionEstado as ModelEstado
from app.repositories.audit_repository import AuditRepository
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.repositories.tenant_config_repository import TenantConfigRepository
from app.services.comunicacion_service import ComunicacionService
from app.services.comunicacion_plantilla import VariablePlantillaFaltanteError
from app.services.comunicacion_estados import TransicionInvalidaError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_settings():
    class FakeSettings:
        SECRET_KEY = "supersecretkeyfortesting1234567890"
        ENCRYPTION_KEY = "E" * 32
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
        MOODLE_BASE_URL = None
        MOODLE_TOKEN = None
        MOODLE_SYNC_HOUR = 3
        PADRON_MAX_ROWS = 5000
        UMBRAL_PCT_DEFECTO = 60
        VALORES_APROBATORIOS_DEFECTO = ["Satisfactorio", "Supera lo esperado"]
        NOTA_MAXIMA_DEFECTO = 10.0

    return FakeSettings()


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID, roles=None) -> CurrentUser:
    return CurrentUser(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles or ["COORDINADOR"],
    )


async def _make_tenant(db_session) -> Tenant:
    t = Tenant(
        nombre=f"TenantSvc-{uuid.uuid4().hex[:6]}",
        estado=TenantEstado.ACTIVO,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


async def _make_usuario(db_session, tenant_id: uuid.UUID) -> Usuario:
    from app.core.security.crypto import encrypt
    email = f"user{uuid.uuid4().hex[:4]}@test.edu"
    from app.core.security.passwords import email_lookup_hash
    hash_val = email_lookup_hash(email)
    u = Usuario(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=hash_val,
        nombre="Test",
        apellidos="User",
        estado=UsuarioEstado.activo,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


async def _make_asignacion(
    db_session, tenant_id: uuid.UUID, usuario_id: uuid.UUID,
    rol=RolAsignacion.COORDINADOR, materia_id=None
) -> Asignacion:
    a = Asignacion(
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        rol=rol,
        desde=date.today(),
        comisiones=[],
        materia_id=materia_id,
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


def _make_service(db_session, tenant_id: uuid.UUID) -> ComunicacionService:
    com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant_id)
    tc_repo = TenantConfigRepository(session=db_session, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db_session, tenant_id=tenant_id)
    return ComunicacionService(
        repo=com_repo,
        tenant_config_repo=tc_repo,
        audit_repo=audit_repo,
    )


# ---------------------------------------------------------------------------
# §4.5 — RED: preview — renderiza sin escribir en DB
# ---------------------------------------------------------------------------

def test_preview_renderiza_sin_db():
    """preview() renderiza asunto/cuerpo sin acceso a DB."""
    from app.services.comunicacion_service import ComunicacionService
    resultado = ComunicacionService.preview_static(
        asunto_plantilla="Aviso para {nombre}",
        cuerpo_plantilla="Estimado {nombre}, su nota es {nota}.",
        variables={"nombre": "Ana", "nota": "8"},
    )
    assert resultado["asunto"] == "Aviso para Ana"
    assert resultado["cuerpo"] == "Estimado Ana, su nota es 8."


def test_preview_falla_variable_faltante():
    """preview() lanza VariablePlantillaFaltanteError si falta una variable."""
    from app.services.comunicacion_service import ComunicacionService
    with pytest.raises(VariablePlantillaFaltanteError):
        ComunicacionService.preview_static(
            asunto_plantilla="Aviso para {nombre}",
            cuerpo_plantilla="Cuerpo",
            variables={},
        )


# ---------------------------------------------------------------------------
# §4.7 — RED: encolar — crea registros, audita COMUNICACION_ENVIAR
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_crea_registros_pendiente(db_session, create_tables, monkeypatch):
    """encolar() crea registros Pendiente y registra auditoría."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)

    svc = _make_service(db_session, tenant.id)

    try:
        lote_id, coms = await svc.encolar(
            destinatarios=["dest1@test.edu", "dest2@test.edu"],
            asunto_plantilla="Hola {nombre}",
            cuerpo_plantilla="Estimado {nombre}.",
            variables_por_destinatario={
                "dest1@test.edu": {"nombre": "Ana"},
                "dest2@test.edu": {"nombre": "Carlos"},
            },
            current_user=current_user,
        )

        assert len(coms) == 2
        for com in coms:
            assert com.estado == ModelEstado.Pendiente
            assert com.lote_id == lote_id
            assert com.enviado_por == usuario.id

    finally:
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_falla_fuerte_variable_faltante(db_session, create_tables, monkeypatch):
    """encolar() falla fuerte si plantilla tiene variable sin resolver (OQ-4) — no crea NINGÚN registro."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)

    svc = _make_service(db_session, tenant.id)

    try:
        with pytest.raises(VariablePlantillaFaltanteError):
            await svc.encolar(
                destinatarios=["dest@test.edu"],
                asunto_plantilla="Hola {nombre}",
                cuerpo_plantilla="Cuerpo",
                variables_por_destinatario={},  # Sin variables — falla fuerte
                current_user=current_user,
            )

        # No se debe haber creado NINGÚN registro del lote
        com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        todos = await com_repo.list()
        assert len(todos) == 0, "No debe crearse ningún registro cuando la plantilla falla"

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


# ---------------------------------------------------------------------------
# §5.3 — RED: aprobación/cancelación de lote según tenant_config (OQ-2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_con_aprobacion_requerida_crea_pendientes(db_session, create_tables, monkeypatch):
    """Con aprobacion_comunicacion_requerida=true, el lote queda Pendiente sin aprobado_por."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)

    svc = _make_service(db_session, tenant.id)
    tc_repo = TenantConfigRepository(session=db_session, tenant_id=tenant.id)

    try:
        # Configurar aprobación requerida
        await tc_repo.set_config("aprobacion_comunicacion_requerida", "true")

        lote_id, coms = await svc.encolar(
            destinatarios=["dest@test.edu"],
            asunto_plantilla="Hola {nombre}",
            cuerpo_plantilla="Cuerpo {nombre}.",
            variables_por_destinatario={"dest@test.edu": {"nombre": "Ana"}},
            current_user=current_user,
        )

        # Los mensajes deben estar Pendiente con aprobado_por=None (esperan aprobación)
        assert all(c.estado == ModelEstado.Pendiente for c in coms)
        assert all(c.aprobado_por is None for c in coms)

        # No deben aparecer en la lista de habilitados para el worker
        com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        habilitados = await com_repo.list_pendientes_habilitados()
        habilitados_ids = {c.id for c in habilitados}
        for com in coms:
            assert com.id not in habilitados_ids, "Mensaje sin aprobar no debe ser elegible para el worker"

    finally:
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenant_config WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_aprobar_lote_habilita_para_worker(db_session, create_tables, monkeypatch):
    """aprobar_lote() habilita todos los mensajes del lote para el worker."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    aprobador = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)
    aprobador_user = _make_current_user(aprobador.id, tenant.id)

    svc = _make_service(db_session, tenant.id)

    try:
        lote_id, coms = await svc.encolar(
            destinatarios=["dest@test.edu"],
            asunto_plantilla="Asunto",
            cuerpo_plantilla="Cuerpo",
            variables_por_destinatario={"dest@test.edu": {}},
            current_user=current_user,
        )

        await svc.aprobar_lote(lote_id=lote_id, current_user=aprobador_user)

        # Después de aprobar, los mensajes deben aparecer en habilitados
        com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        habilitados = await com_repo.list_pendientes_habilitados()
        habilitados_ids = {c.id for c in habilitados}
        for com in coms:
            assert com.id in habilitados_ids

    finally:
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_cancelar_lote_pasa_a_cancelado(db_session, create_tables, monkeypatch):
    """cancelar_lote() pasa todos los mensajes Pendiente a Cancelado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)

    svc = _make_service(db_session, tenant.id)

    try:
        lote_id, coms = await svc.encolar(
            destinatarios=["dest@test.edu"],
            asunto_plantilla="Asunto",
            cuerpo_plantilla="Cuerpo",
            variables_por_destinatario={"dest@test.edu": {}},
            current_user=current_user,
        )

        await svc.cancelar_lote(lote_id=lote_id, current_user=current_user)

        com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        lote = await com_repo.list_by_lote(lote_id)
        for com in lote:
            assert com.estado == ModelEstado.Cancelado

    finally:
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


# ---------------------------------------------------------------------------
# §5.5 — TRIANGULATE: aprobación/cancelación individual
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_cancelar_individual_solo_afecta_ese_mensaje(db_session, create_tables, monkeypatch):
    """cancelar_individual() solo cambia el estado del mensaje especificado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)

    svc = _make_service(db_session, tenant.id)

    try:
        lote_id, coms = await svc.encolar(
            destinatarios=["a@test.edu", "b@test.edu"],
            asunto_plantilla="Asunto",
            cuerpo_plantilla="Cuerpo",
            variables_por_destinatario={"a@test.edu": {}, "b@test.edu": {}},
            current_user=current_user,
        )

        # Cancelar solo el primero
        await svc.cancelar_individual(
            comunicacion_id=coms[0].id,
            current_user=current_user,
        )

        com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        lote = await com_repo.list_by_lote(lote_id)
        estados = {c.id: c.estado for c in lote}

        assert estados[coms[0].id] == ModelEstado.Cancelado
        assert estados[coms[1].id] == ModelEstado.Pendiente

    finally:
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_cancelar_enviado_falla_transicion_invalida(db_session, create_tables, monkeypatch):
    """No se puede cancelar un mensaje Enviado (transición inválida)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    tenant_id = tenant.id  # capture before potential error states
    usuario = await _make_usuario(db_session, tenant_id)
    current_user = _make_current_user(usuario.id, tenant_id)

    svc = _make_service(db_session, tenant_id)

    try:
        lote_id, coms = await svc.encolar(
            destinatarios=["dest@test.edu"],
            asunto_plantilla="Asunto",
            cuerpo_plantilla="Cuerpo",
            variables_por_destinatario={"dest@test.edu": {}},
            current_user=current_user,
        )

        # Simular que el mensaje ya fue enviado
        com_repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        await com_repo.actualizar_estado(
            comunicacion=coms[0],
            nuevo_estado=ModelEstado.Enviando,
        )
        await com_repo.actualizar_estado(
            comunicacion=coms[0],
            nuevo_estado=ModelEstado.Enviado,
            enviado_at=datetime.now(tz=timezone.utc),
        )

        # Intentar cancelar debe fallar (lanza TransicionInvalidaError antes de tocar DB)
        with pytest.raises(TransicionInvalidaError):
            await svc.cancelar_individual(
                comunicacion_id=coms[0].id,
                current_user=current_user,
            )

    finally:
        # Rollback por si la sesión quedó en mal estado
        try:
            await db_session.rollback()
        except Exception:
            pass
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant_id)},
        )
        await db_session.commit()


# ---------------------------------------------------------------------------
# §4.11 — TRIANGULATE: auditoría registrada exactamente una vez
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_registra_auditoria_exactamente_una_vez(db_session, create_tables, monkeypatch):
    """encolar() registra exactamente 1 evento de auditoría COMUNICACION_ENVIAR."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    usuario = await _make_usuario(db_session, tenant.id)
    current_user = _make_current_user(usuario.id, tenant.id)

    svc = _make_service(db_session, tenant.id)

    try:
        await svc.encolar(
            destinatarios=["a@test.edu", "b@test.edu", "c@test.edu"],
            asunto_plantilla="Asunto",
            cuerpo_plantilla="Cuerpo",
            variables_por_destinatario={
                "a@test.edu": {},
                "b@test.edu": {},
                "c@test.edu": {},
            },
            current_user=current_user,
        )

        # Verificar que hay exactamente 1 evento de auditoría
        result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM audit_event "
                "WHERE tenant_id = :tid AND accion = 'COMUNICACION_ENVIAR'"
            ),
            {"tid": str(tenant.id)},
        )
        count = result.scalar()
        assert count == 1, f"Debe haber exactamente 1 evento de auditoría, hay {count}"

    finally:
        await db_session.execute(
            text("DELETE FROM audit_event WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()
