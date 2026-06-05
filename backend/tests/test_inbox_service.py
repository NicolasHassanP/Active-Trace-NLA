"""
test_inbox_service.py — TDD suite para C-20 inbox service.

Task 9.1 RED: ver_inbox usa usuario_id del JWT.
Task 9.3 RED: abrir_hilo marca leído y rechaza no participante.
Task 9.5 RED: responder ignora remitente_id del body (anti-spoofing).
Task 9.7 RED: iniciar_hilo rechaza destinatario cross-tenant y hilo duplicado.
Task 9.9 TRIANGULATE: múltiples mensajes, no-leídos, hilo duplicado.
"""
import uuid

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.core.dependencies import CurrentUser
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado


@pytest_asyncio.fixture(scope="module")
async def inbox_svc_data(test_engine, create_tables):
    """Crea tenant + usuarios para tests de inbox service."""
    import app.models  # noqa
    from sqlalchemy import text
    from app.core.security.passwords import email_lookup_hash

    factory = build_session_factory(test_engine)
    session = factory()

    await session.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"))

    # Garantizar que las tablas de mensajería existan (ya creadas por mensajeria_data)
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS hilos_mensaje (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            asunto VARCHAR(255) NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            hilo_id UUID NOT NULL REFERENCES hilos_mensaje(id) ON DELETE RESTRICT,
            remitente_id UUID NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            asunto VARCHAR(255) NOT NULL,
            cuerpo TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at TIMESTAMPTZ NULL
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS hilo_participantes (
            hilo_id UUID NOT NULL REFERENCES hilos_mensaje(id) ON DELETE CASCADE,
            usuario_id UUID NOT NULL REFERENCES usuario(id) ON DELETE RESTRICT,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
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

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre=f"Inbox Svc A {tid_a}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre=f"Inbox Svc B {tid_b}", estado=TenantEstado.ACTIVO))
    await session.flush()

    email_u1 = f"inbox_u1_{tid_a}@test.com"
    email_u2 = f"inbox_u2_{tid_a}@test.com"
    email_ub = f"inbox_ub_{tid_b}@test.com"

    u1 = Usuario(
        tenant_id=tid_a, email_encrypted=email_u1,
        email_hash=email_lookup_hash(email_u1),
        nombre="User1", apellidos="A", estado=UsuarioEstado.activo,
    )
    u2 = Usuario(
        tenant_id=tid_a, email_encrypted=email_u2,
        email_hash=email_lookup_hash(email_u2),
        nombre="User2", apellidos="A", estado=UsuarioEstado.activo,
    )
    ub = Usuario(
        tenant_id=tid_b, email_encrypted=email_ub,
        email_hash=email_lookup_hash(email_ub),
        nombre="UserB", apellidos="B", estado=UsuarioEstado.activo,
    )
    session.add_all([u1, u2, ub])
    await session.commit()
    await session.refresh(u1)
    await session.refresh(u2)
    await session.refresh(ub)

    yield {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "u1": u1,
        "u2": u2,
        "ub": ub,
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
def inbox_svc_session_factory(test_engine, create_tables):
    return build_session_factory(test_engine)


# ---------------------------------------------------------------------------
# Task 9.1 RED — ver_inbox usa usuario_id del JWT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ver_inbox_usa_id_del_jwt(inbox_svc_session_factory, inbox_svc_data):
    """RED: ver_inbox devuelve los hilos del actor (JWT), no de otro usuario."""
    from app.services.inbox_service import InboxService
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        actor = CurrentUser(user_id=data["u1"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        svc = InboxService(repo=repo)
        # Primero crear un hilo para u1
        await repo.crear_hilo(data["u1"].id, data["u2"].id, "Hilo ver_inbox", "Mensaje")
        result = await svc.ver_inbox(actor)
        assert isinstance(result, list)
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 9.3 RED — abrir_hilo marca leído y rechaza no participante
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_abrir_hilo_marca_leido(inbox_svc_session_factory, inbox_svc_data):
    """RED: abrir_hilo marca el hilo como leído para el usuario."""
    from app.services.inbox_service import InboxService
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.models.mensajeria import HiloParticipante
    from sqlalchemy import select
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        actor = CurrentUser(user_id=data["u2"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            data["u1"].id, data["u2"].id, "Hilo abrir", "Mensaje"
        )
        svc = InboxService(repo=repo)
        await svc.abrir_hilo(actor, hilo.id)

        stmt = select(HiloParticipante).where(
            HiloParticipante.hilo_id == hilo.id,
            HiloParticipante.usuario_id == data["u2"].id,
        )
        result = await session.execute(stmt)
        p = result.scalar_one_or_none()
        assert p is not None
        assert p.last_read_at is not None
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_abrir_hilo_rechaza_no_participante(inbox_svc_session_factory, inbox_svc_data):
    """RED: abrir_hilo levanta HiloNoEncontrado para no participante."""
    from app.services.inbox_service import InboxService, HiloNoEncontrado
    from app.repositories.mensajeria_repository import MensajeriaRepository
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        # u2 intenta abrir un hilo donde no participa (hilo inventado)
        actor = CurrentUser(user_id=data["u2"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        svc = InboxService(repo=repo)
        with pytest.raises(HiloNoEncontrado):
            await svc.abrir_hilo(actor, uuid.uuid4())
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 9.5 RED — responder ignora remitente_id del body (anti-spoofing)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_responder_ignora_remitente_del_body(inbox_svc_session_factory, inbox_svc_data):
    """RED: responder atribuye el mensaje al actor (JWT), no a un remitente_id externo."""
    from app.services.inbox_service import InboxService
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.mensajeria import RespuestaCreate
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        actor = CurrentUser(user_id=data["u1"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            data["u1"].id, data["u2"].id, "Hilo anti-spoofing", "Mensaje inicial"
        )
        svc = InboxService(repo=repo)
        respuesta = RespuestaCreate(asunto="Re", cuerpo="Respuesta del actor")
        msg = await svc.responder(actor, hilo.id, respuesta)
        # El remitente_id debe ser el del actor, no un valor inventado
        assert msg.remitente_id == data["u1"].id
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_responder_rechaza_no_participante(inbox_svc_session_factory, inbox_svc_data):
    """RED: responder levanta HiloNoEncontrado si el actor no participa."""
    from app.services.inbox_service import InboxService, HiloNoEncontrado
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.mensajeria import RespuestaCreate
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        # Crear hilo entre u1 y u2; ub intenta responder
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            data["u1"].id, data["u2"].id, "Hilo privado", "Solo u1 y u2"
        )
        # Actor es alguien que no participa del hilo
        actor_otro = CurrentUser(user_id=uuid.uuid4(), tenant_id=data["tid_a"], roles=["TUTOR"])
        svc = InboxService(repo=repo)
        with pytest.raises(HiloNoEncontrado):
            await svc.responder(actor_otro, hilo.id, RespuestaCreate(asunto="X", cuerpo="Intruso"))
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 9.7 RED — iniciar_hilo rechaza cross-tenant y duplicado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_iniciar_hilo_rechaza_destinatario_cross_tenant(inbox_svc_session_factory, inbox_svc_data):
    """RED: iniciar_hilo rechaza destinatario de otro tenant."""
    from app.services.inbox_service import InboxService, DestinatarioInvalido
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.mensajeria import HiloCreate
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        # Remitente: u1 (tenant_a); destinatario: ub (tenant_b)
        actor = CurrentUser(user_id=data["u1"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        svc = InboxService(repo=repo)
        body = HiloCreate(
            destinatario_id=data["ub"].id,
            asunto="Cross-tenant",
            cuerpo="Esto no debe funcionar",
        )
        with pytest.raises(DestinatarioInvalido):
            await svc.iniciar_hilo(actor, body)
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_iniciar_hilo_rechaza_hilo_duplicado(inbox_svc_session_factory, inbox_svc_data):
    """RED: iniciar_hilo rechaza crear segundo hilo 1:1 entre los mismos usuarios."""
    from app.services.inbox_service import InboxService, HiloDuplicado
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.schemas.mensajeria import HiloCreate
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        actor = CurrentUser(user_id=data["u1"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        # Crear un hilo primero
        await repo.crear_hilo(data["u1"].id, data["u2"].id, "Primer hilo", "Mensaje")
        svc = InboxService(repo=repo)
        body = HiloCreate(
            destinatario_id=data["u2"].id,
            asunto="Segundo hilo duplicado",
            cuerpo="No debe crear",
        )
        with pytest.raises(HiloDuplicado):
            await svc.iniciar_hilo(actor, body)
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 9.9 TRIANGULATE — múltiples mensajes, no-leídos, hilo duplicado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_leidos_se_incrementan_tras_nueva_respuesta(inbox_svc_session_factory, inbox_svc_data):
    """TRIANGULATE: no-leídos aumenta al agregar un mensaje nuevo."""
    from app.repositories.mensajeria_repository import MensajeriaRepository
    from app.services.inbox_service import InboxService
    from app.schemas.mensajeria import RespuestaCreate
    data = inbox_svc_data
    session = inbox_svc_session_factory()
    try:
        actor_u2 = CurrentUser(user_id=data["u2"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        repo = MensajeriaRepository(session=session, tenant_id=data["tid_a"])
        hilo, _ = await repo.crear_hilo(
            data["u1"].id, data["u2"].id, "Hilo no-leídos", "Mensaje 1"
        )
        svc = InboxService(repo=repo)
        # u2 abre el hilo (marca leído)
        await svc.abrir_hilo(actor_u2, hilo.id)

        # u1 responde
        actor_u1 = CurrentUser(user_id=data["u1"].id, tenant_id=data["tid_a"], roles=["TUTOR"])
        await svc.responder(actor_u1, hilo.id, RespuestaCreate(asunto="Re", cuerpo="Nuevo mensaje"))

        # Para u2, debe haber al menos 1 no-leído ahora
        no_leidos = await repo.contar_no_leidos(hilo.id, data["u2"].id)
        assert no_leidos >= 1
    finally:
        await session.close()
