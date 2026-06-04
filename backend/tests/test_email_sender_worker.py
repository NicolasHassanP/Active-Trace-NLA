"""
TDD tests for EmailSender (Protocol + TestSender) and comunicacion_worker.

C-12 Tasks: 6.1-6.5

Design decisions tested:
    - OQ-3: TestSender cumple el contrato async send(), registra in-memory.
    - OQ-3: TestSender puede configurarse para forzar fallo.
    - OQ-5: Error es TERMINAL — worker no re-procesa mensajes en Error.
    - Worker: polling toma Pendiente habilitado → Enviado registrando enviado_at.
    - Worker: fallo de envío → estado Error con error_detalle.
    - Worker: NO toma mensajes Pendiente sin aprobación requerida no aprobados.

Uses real DB, no mocks.
"""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text

from app.models.tenant import Tenant, TenantEstado
from app.models.comunicacion import ComunicacionEstado as ModelEstado
from app.models.usuario import Usuario, UsuarioEstado
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.repositories.tenant_config_repository import TenantConfigRepository
from app.workers.email_sender import TestSender
from app.workers.comunicacion_worker import ComunicacionWorker


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


async def _make_tenant(db_session) -> Tenant:
    t = Tenant(
        nombre=f"TenantWorker-{uuid.uuid4().hex[:6]}",
        estado=TenantEstado.ACTIVO,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


async def _make_usuario(db_session, tenant_id: uuid.UUID) -> Usuario:
    from app.core.security.passwords import email_lookup_hash
    email = f"worker{uuid.uuid4().hex[:4]}@test.edu"
    u = Usuario(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        nombre="Worker",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


# ---------------------------------------------------------------------------
# §6.1 — RED: TestSender cumple el contrato EmailSender
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_test_sender_cumple_contrato():
    """TestSender.send() es callable async y registra el envío in-memory."""
    sender = TestSender()
    await sender.send(
        destinatario="test@example.com",
        asunto="Asunto",
        cuerpo="Cuerpo",
    )
    assert len(sender.enviados) == 1
    assert sender.enviados[0]["destinatario"] == "test@example.com"
    assert sender.enviados[0]["asunto"] == "Asunto"


@pytest.mark.asyncio(loop_scope="function")
async def test_test_sender_modo_fallo():
    """TestSender en modo fallo lanza excepción al llamar send()."""
    sender = TestSender(forzar_fallo=True, mensaje_error="Fallo simulado")
    with pytest.raises(Exception, match="Fallo simulado"):
        await sender.send(
            destinatario="fail@example.com",
            asunto="Asunto",
            cuerpo="Cuerpo",
        )


@pytest.mark.asyncio(loop_scope="function")
async def test_test_sender_multiples_envios():
    """TestSender registra múltiples envíos."""
    sender = TestSender()
    for i in range(3):
        await sender.send(
            destinatario=f"user{i}@example.com",
            asunto="Asunto",
            cuerpo="Cuerpo",
        )
    assert len(sender.enviados) == 3


# ---------------------------------------------------------------------------
# §6.3 — RED: worker procesa Pendiente habilitado → Enviado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_worker_procesa_pendiente_habilitado(db_session, create_tables, monkeypatch):
    """Worker procesa un mensaje Pendiente aprobado → Enviado con enviado_at."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    aprobador = await _make_usuario(db_session, tenant.id)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)

    try:
        coms = await repo.encolar_lote(
            destinatarios=["dest@test.edu"],
            asunto="Asunto",
            cuerpo="Cuerpo del mensaje",
            lote_id=lote_id,
        )
        # Simular aprobación con usuario real
        await repo.actualizar_estado(
            comunicacion=coms[0],
            nuevo_estado=ModelEstado.Pendiente,
            aprobado_por=aprobador.id,
        )

        sender = TestSender()
        worker = ComunicacionWorker(sender=sender, session=db_session)
        procesados = await worker.procesar_ciclo(tenant_id=tenant.id)

        # El mensaje debe estar Enviado con enviado_at
        await db_session.refresh(coms[0])
        assert coms[0].estado == ModelEstado.Enviado
        assert coms[0].enviado_at is not None
        assert procesados == 1
        assert len(sender.enviados) == 1

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
# §6.5 — TRIANGULATE: fallo de envío → Error con error_detalle
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_worker_fallo_marca_error(db_session, create_tables, monkeypatch):
    """Worker en fallo marca el mensaje como Error con error_detalle."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    aprobador = await _make_usuario(db_session, tenant.id)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)

    try:
        coms = await repo.encolar_lote(
            destinatarios=["fail@test.edu"],
            asunto="Asunto",
            cuerpo="Cuerpo",
            lote_id=lote_id,
        )
        await repo.actualizar_estado(
            comunicacion=coms[0],
            nuevo_estado=ModelEstado.Pendiente,
            aprobado_por=aprobador.id,
        )

        sender = TestSender(forzar_fallo=True, mensaje_error="SMTP timeout")
        worker = ComunicacionWorker(sender=sender, session=db_session)
        await worker.procesar_ciclo(tenant_id=tenant.id)

        await db_session.refresh(coms[0])
        assert coms[0].estado == ModelEstado.Error
        assert coms[0].error_detalle is not None
        assert "SMTP timeout" in coms[0].error_detalle

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


@pytest.mark.asyncio(loop_scope="function")
async def test_worker_no_reprocesa_mensaje_en_error(db_session, create_tables, monkeypatch):
    """Worker NO re-procesa mensajes en estado Error (OQ-5: Error es TERMINAL)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
    aprobador_id = uuid.uuid4()

    try:
        coms = await repo.encolar_lote(
            destinatarios=["err@test.edu"],
            asunto="Asunto",
            cuerpo="Cuerpo",
            lote_id=lote_id,
        )
        # Poner directamente en estado Error (simular que ya falló)
        await repo.actualizar_estado(
            comunicacion=coms[0],
            nuevo_estado=ModelEstado.Enviando,
        )
        await repo.actualizar_estado(
            comunicacion=coms[0],
            nuevo_estado=ModelEstado.Error,
            error_detalle="Error previo",
        )

        sender = TestSender()
        worker = ComunicacionWorker(sender=sender, session=db_session)
        procesados = await worker.procesar_ciclo(tenant_id=tenant.id)

        # El worker no debe procesar el mensaje en Error
        assert procesados == 0
        assert len(sender.enviados) == 0
        await db_session.refresh(coms[0])
        assert coms[0].estado == ModelEstado.Error  # Estado no cambió

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_worker_no_toma_pendiente_sin_aprobar(db_session, create_tables, monkeypatch):
    """Worker NO procesa mensajes Pendiente sin aprobación (aprobado_por=None)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    lote_id = uuid.uuid4()

    repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)

    try:
        # Encolar sin aprobar
        coms = await repo.encolar_lote(
            destinatarios=["unapproved@test.edu"],
            asunto="Asunto",
            cuerpo="Cuerpo",
            lote_id=lote_id,
        )
        # NO llamar actualizar_estado con aprobado_por

        sender = TestSender()
        worker = ComunicacionWorker(sender=sender, session=db_session)
        procesados = await worker.procesar_ciclo(tenant_id=tenant.id)

        assert procesados == 0
        assert len(sender.enviados) == 0
        await db_session.refresh(coms[0])
        assert coms[0].estado == ModelEstado.Pendiente

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()
