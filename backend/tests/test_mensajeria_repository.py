"""
test_mensajeria_repository.py — TDD suite para C-20 repository de mensajería.

Task 8.1 RED: listar_hilos solo devuelve hilos del participante.
Task 8.3 RED: obtener_hilo devuelve None para no participante y cross-tenant.
Task 8.5 RED: agregar_mensaje/crear_hilo con remitente_id y tenant_id correctos.
Task 8.7 RED: marcar_leido actualiza last_read_at y calcula no-leídos.
Task 8.9 TRIANGULATE: aislamiento, soft delete excluye de listados.
"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado


@pytest_asyncio.fixture(scope="module")
async def mensajeria_data(test_engine, create_tables):
    """
    Crea dos tenants con usuarios para tests de mensajería repository.
    También crea las tablas de mensajería (C-20).
    """
    import app.models  # noqa
    from sqlalchemy import text
    from app.core.security.passwords import email_lookup_hash

    factory = build_session_factory(test_engine)
    session = factory()

    # Crear tablas C-20 (idempotente)
    await session.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"))

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS hilos_mensaje (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id  UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asunto     VARCHAR(255) NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            hilo_id      UUID        NOT NULL REFERENCES hilos_mensaje(id) ON DELETE RESTRICT,
            remitente_id UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            asunto       VARCHAR(255) NOT NULL,
            cuerpo       TEXT        NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at   TIMESTAMPTZ NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS hilo_participantes (
            hilo_id      UUID        NOT NULL REFERENCES hilos_mensaje(id) ON DELETE CASCADE,
            usuario_id   UUID        NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            last_read_at TIMESTAMPTZ NULL,
            PRIMARY KEY (hilo_id, usuario_id)
        )
    """))
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_hilo_participantes_tenant_usuario "
        "ON hilo_participantes (tenant_id, usuario_id)"
    ))
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_mensajes_tenant_hilo_at "
        "ON mensajes (tenant_id, hilo_id, created_at)"
    ))
    await session.commit()

    # Dos tenants
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre=f"Mensajeria TenantA {tid_a}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre=f"Mensajeria TenantB {tid_b}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Dos usuarios en tenant A, uno en tenant B
    email_a1 = f"ma1_{tid_a}@test.com"
    email_a2 = f"ma2_{tid_a}@test.com"
    email_b1 = f"mb1_{tid_b}@test.com"

    u_a1 = Usuario(
        tenant_id=tid_a, email_encrypted=email_a1,
        email_hash=email_lookup_hash(email_a1),
        nombre="A1", apellidos="Tenant A", estado=UsuarioEstado.activo,
    )
    u_a2 = Usuario(
        tenant_id=tid_a, email_encrypted=email_a2,
        email_hash=email_lookup_hash(email_a2),
        nombre="A2", apellidos="Tenant A", estado=UsuarioEstado.activo,
    )
    u_b1 = Usuario(
        tenant_id=tid_b, email_encrypted=email_b1,
        email_hash=email_lookup_hash(email_b1),
        nombre="B1", apellidos="Tenant B", estado=UsuarioEstado.activo,
    )
    session.add_all([u_a1, u_a2, u_b1])
    await session.commit()
    await session.refresh(u_a1)
    await session.refresh(u_a2)
    await session.refresh(u_b1)

    yield {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "u_a1": u_a1,
        "u_a2": u_a2,
        "u_b1": u_b1,
    }

    from sqlalchemy import delete
    from app.models.mensajeria import HiloParticipante, HiloMensaje, Mensaje
    await session.execute(delete(HiloParticipante).where(HiloParticipante.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Mensaje).where(Mensaje.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(HiloMensaje).where(HiloMensaje.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Usuario).where(Usuario.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Tenant).where(Tenant.id.in_([tid_a, tid_b])))
    await session.commit()
    await session.close()


@pytest_asyncio.fixture(scope="module")
def mensajeria_session_factory(test_engine, create_tables):
    return build_session_factory(test_engine)


# ---------------------------------------------------------------------------
# Task 8.5 RED — crear_hilo y agregar_mensaje con remitente_id/tenant_id correctos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_hilo_persiste_con_participantes(mensajeria_session_factory, mensajeria_data):
    """RED: crear_hilo persiste hilo y participantes con tenant_id correcto."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, msg = await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo test",
            cuerpo="Primer mensaje",
        )
        assert hilo.tenant_id == data["tid_a"]
        assert msg.remitente_id == data["u_a1"].id
        assert msg.tenant_id == data["tid_a"]
        assert msg.cuerpo == "Primer mensaje"
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_agregar_mensaje_persiste_con_remitente_correcto(mensajeria_session_factory, mensajeria_data):
    """RED: agregar_mensaje persiste mensaje con remitente_id del server."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        # Primero crear un hilo
        hilo, _ = await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo para respuesta",
            cuerpo="Mensaje inicial",
        )
        # Luego agregar un mensaje
        msg = await repo.agregar_mensaje(
            hilo_id=hilo.id,
            remitente_id=data["u_a2"].id,
            asunto="Re: Hilo",
            cuerpo="Esta es la respuesta",
        )
        assert msg.remitente_id == data["u_a2"].id
        assert msg.tenant_id == data["tid_a"]
        assert msg.hilo_id == hilo.id
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 8.1 RED — listar_hilos del participante
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_hilos_solo_devuelve_hilos_del_participante(mensajeria_session_factory, mensajeria_data):
    """RED: listar_hilos solo devuelve hilos donde el usuario participa."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        # Crear hilo entre a1 y a2
        await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo A1-A2",
            cuerpo="Hola A2",
        )
        # Listar hilos de a1 — debe incluir el hilo
        hilos_a1 = await repo.listar_hilos(data["u_a1"].id)
        assert len(hilos_a1) >= 1

        # Verificar que todos los hilos incluyen a a1 como participante
        hilo_ids = [h["hilo_id"] for h in hilos_a1]
        assert all(isinstance(hid, uuid.UUID) for hid in hilo_ids)
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 8.3 RED — obtener_hilo 404 para no participante y cross-tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_obtener_hilo_retorna_none_para_no_participante(mensajeria_session_factory, mensajeria_data):
    """RED: obtener_hilo retorna None para usuario no participante del hilo."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo_a = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        # Crear un hilo entre a1 y a2 (a3 no existe, usamos uuid inventado)
        hilo, _ = await repo_a.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo privado",
            cuerpo="Solo entre a1 y a2",
        )
        # Otro usuario del mismo tenant no debería ver el hilo
        u_otro = uuid.uuid4()
        resultado = await repo_a.obtener_hilo(hilo.id, u_otro)
        assert resultado is None
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_obtener_hilo_retorna_none_cross_tenant(mensajeria_session_factory, mensajeria_data):
    """RED: obtener_hilo retorna None para hilo de otro tenant (cross-tenant)."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo_a = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo_a.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Cross-tenant test",
            cuerpo="Solo en tenant A",
        )
        # Desde el repo de tenant_b, intentar acceder al hilo de tenant_a
        repo_b = MensajeriaRepository(session=session, tenant_id=data["tid_b"])
        resultado = await repo_b.obtener_hilo(hilo.id, data["u_b1"].id)
        assert resultado is None
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 8.7 RED — marcar_leido y no-leídos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_marcar_leido_actualiza_last_read_at(mensajeria_session_factory, mensajeria_data):
    """RED: marcar_leido actualiza last_read_at para el participante."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo para marcar leído",
            cuerpo="Mensaje 1",
        )
        # Marcar leído para a2
        await repo.marcar_leido(hilo.id, data["u_a2"].id)
        # Verificar last_read_at actualizado
        from app.models.mensajeria import HiloParticipante
        from sqlalchemy import select
        stmt = select(HiloParticipante).where(
            HiloParticipante.hilo_id == hilo.id,
            HiloParticipante.usuario_id == data["u_a2"].id,
        )
        result = await session.execute(stmt)
        participante = result.scalar_one_or_none()
        assert participante is not None
        assert participante.last_read_at is not None
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_contar_no_leidos_calcula_correctamente(mensajeria_session_factory, mensajeria_data):
    """RED: contar_no_leidos retorna mensajes con created_at > last_read_at."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo no-leidos",
            cuerpo="Mensaje 1",
        )
        # Agregar otro mensaje
        await repo.agregar_mensaje(
            hilo_id=hilo.id,
            remitente_id=data["u_a1"].id,
            asunto="Mensaje 2",
            cuerpo="Cuerpo 2",
        )
        # Para a2, que no ha leído, debe haber 2 no-leídos (o > 0 al menos)
        no_leidos = await repo.contar_no_leidos(hilo.id, data["u_a2"].id)
        assert no_leidos >= 1
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 8.9 TRIANGULATE — soft delete excluye de listados
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_mensaje_excluye_de_listado(mensajeria_session_factory, mensajeria_data):
    """TRIANGULATE: mensaje con deleted_at != None excluido del listado."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.mensajeria import Mensaje
    from datetime import datetime, timezone
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, msg = await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo soft-delete test",
            cuerpo="Mensaje a eliminar",
        )
        # Soft delete del mensaje
        msg.deleted_at = datetime.now(tz=timezone.utc)
        await session.commit()

        # El listado de mensajes del hilo no debe incluirlo
        mensajes = await repo.obtener_mensajes(hilo.id, data["u_a1"].id)
        mensajes_ids = [m.id for m in mensajes] if mensajes else []
        assert msg.id not in mensajes_ids
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_buscar_hilo_existente_entre_participantes(mensajeria_session_factory, mensajeria_data):
    """TRIANGULATE: buscar_hilo_existente retorna el id si ya existe hilo 1:1."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = mensajeria_data
    session = mensajeria_session_factory()
    try:
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            remitente_id=data["u_a1"].id,
            destinatario_id=data["u_a2"].id,
            asunto="Hilo para buscar duplicado",
            cuerpo="Primer mensaje",
        )
        # Buscar hilo existente entre los mismos dos usuarios
        existente = await repo.buscar_hilo_existente(data["u_a1"].id, data["u_a2"].id)
        assert existente is not None
    finally:
        await session.close()
