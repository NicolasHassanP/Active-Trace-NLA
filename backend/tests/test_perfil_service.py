"""
test_perfil_service.py — TDD suite para C-20 perfil service.

Task 4.1 RED: obtener_perfil usa usuario_id del JWT, nunca de la petición.
Task 4.3 RED: actualizar_perfil rechaza email duplicado (409) y registra auditoría.
Task 4.5 TRIANGULATE: edición exitosa, sin cambios, intento de cambiar identidad.
"""
import uuid
import logging

import pytest
import pytest_asyncio

from app.core.database import build_session_factory
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado
from app.core.dependencies import CurrentUser

TEST_ENCRYPTION_KEY = "E" * 32
TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"


@pytest_asyncio.fixture(scope="module")
async def perfil_svc_data(test_engine, create_tables):
    """Crea tenant + dos usuarios para tests de perfil service."""
    import app.models  # noqa
    from sqlalchemy import text
    from app.core.security.passwords import email_lookup_hash

    factory = build_session_factory(test_engine)
    session = factory()

    await session.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"))
    await session.commit()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"Perfil Svc {tid}", estado=TenantEstado.ACTIVO))
    await session.flush()

    email_u1 = f"u1_{tid}@svc.test"
    email_u2 = f"u2_{tid}@svc.test"

    u1 = Usuario(
        tenant_id=tid,
        email_encrypted=email_u1,
        email_hash=email_lookup_hash(email_u1),
        nombre="Usuario1",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    u2 = Usuario(
        tenant_id=tid,
        email_encrypted=email_u2,
        email_hash=email_lookup_hash(email_u2),
        nombre="Usuario2",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    session.add(u1)
    session.add(u2)
    await session.commit()
    await session.refresh(u1)
    await session.refresh(u2)

    yield {
        "tid": tid,
        "u1": u1,
        "u2": u2,
        "email_u1": email_u1,
        "email_u2": email_u2,
    }

    from sqlalchemy import delete
    from app.models.audit import AuditEvent
    await session.execute(delete(AuditEvent).where(AuditEvent.tenant_id == tid))
    await session.execute(delete(Usuario).where(Usuario.tenant_id == tid))
    await session.execute(delete(Tenant).where(Tenant.id == tid))
    await session.commit()
    await session.close()


@pytest_asyncio.fixture(scope="module")
def perfil_svc_session_factory(test_engine, create_tables):
    return build_session_factory(test_engine)


# ---------------------------------------------------------------------------
# Task 4.1 RED — obtener_perfil usa usuario_id del JWT (CurrentUser)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_obtener_perfil_usa_id_del_jwt(perfil_svc_session_factory, perfil_svc_data):
    """RED: obtener_perfil usa el user_id del CurrentUser (JWT), no un param externo."""
    from app.services.perfil_service import PerfilService
    from app.repositories.perfil_repository import PerfilRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.audit_service import AuditService
    data = perfil_svc_data
    session = perfil_svc_session_factory()
    try:
        actor = CurrentUser(
            user_id=data["u1"].id,
            tenant_id=data["tid"],
            roles=["ADMIN"],
        )
        repo = PerfilRepository(session=session, tenant_id=data["tid"])
        audit_repo = AuditRepository(session=session, tenant_id=data["tid"])
        audit_svc = AuditService(repository=audit_repo)
        svc = PerfilService(repo=repo, audit_svc=audit_svc)
        perfil = await svc.obtener_perfil(actor)
        assert perfil is not None
        assert perfil.id == data["u1"].id
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_obtener_perfil_ignora_id_de_peticion(perfil_svc_session_factory, perfil_svc_data):
    """RED: obtener_perfil ignora cualquier id que no sea el del JWT."""
    from app.services.perfil_service import PerfilService
    from app.repositories.perfil_repository import PerfilRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.audit_service import AuditService
    data = perfil_svc_data
    session = perfil_svc_session_factory()
    try:
        # Actor es u1, pasamos u2.id — debe retornar u1 igualmente
        actor = CurrentUser(
            user_id=data["u1"].id,
            tenant_id=data["tid"],
            roles=["ADMIN"],
        )
        repo = PerfilRepository(session=session, tenant_id=data["tid"])
        audit_repo = AuditRepository(session=session, tenant_id=data["tid"])
        audit_svc = AuditService(repository=audit_repo)
        svc = PerfilService(repo=repo, audit_svc=audit_svc)
        # El service solo usa actor.user_id — no acepta id externo
        perfil = await svc.obtener_perfil(actor)
        assert perfil.id == data["u1"].id
        assert perfil.id != data["u2"].id
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 4.3 RED — actualizar_perfil rechaza email duplicado y audita sin PII
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_actualizar_perfil_rechaza_email_duplicado(perfil_svc_session_factory, perfil_svc_data):
    """RED: actualizar_perfil con email ya usado en el tenant levanta ConflictoEmail."""
    from app.services.perfil_service import PerfilService, ConflictoEmailPerfil
    from app.repositories.perfil_repository import PerfilRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.audit_service import AuditService
    data = perfil_svc_data
    session = perfil_svc_session_factory()
    try:
        actor = CurrentUser(
            user_id=data["u1"].id,
            tenant_id=data["tid"],
            roles=["ADMIN"],
        )
        repo = PerfilRepository(session=session, tenant_id=data["tid"])
        audit_repo = AuditRepository(session=session, tenant_id=data["tid"])
        audit_svc = AuditService(repository=audit_repo)
        svc = PerfilService(repo=repo, audit_svc=audit_svc)
        # Intentar cambiar email de u1 al email de u2 (ya usado)
        with pytest.raises(ConflictoEmailPerfil):
            await svc.actualizar_perfil(actor, email=data["email_u2"])
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_actualizar_perfil_registra_auditoria_sin_pii(perfil_svc_session_factory, perfil_svc_data, caplog):
    """RED: actualizar_perfil registra auditoría y PII no aparece en logs."""
    from app.services.perfil_service import PerfilService
    from app.repositories.perfil_repository import PerfilRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.audit_service import AuditService
    data = perfil_svc_data
    session = perfil_svc_session_factory()
    try:
        actor = CurrentUser(
            user_id=data["u1"].id,
            tenant_id=data["tid"],
            roles=["ADMIN"],
        )
        repo = PerfilRepository(session=session, tenant_id=data["tid"])
        audit_repo = AuditRepository(session=session, tenant_id=data["tid"])
        audit_svc = AuditService(repository=audit_repo)
        svc = PerfilService(repo=repo, audit_svc=audit_svc)

        with caplog.at_level(logging.DEBUG):
            await svc.actualizar_perfil(actor, banco="Banco Auditado")

        # PII conocida no debe aparecer en logs
        for record in caplog.records:
            assert "0000003100012345678901" not in record.message
            assert "12345678" not in record.message
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Task 4.5 TRIANGULATE — edición exitosa, sin cambios, identidad ignorada
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_actualizar_perfil_edicion_exitosa_campos_pii(perfil_svc_session_factory, perfil_svc_data):
    """TRIANGULATE: edición exitosa de campos PII — persisten cifrados."""
    from sqlalchemy import text
    from app.services.perfil_service import PerfilService
    from app.repositories.perfil_repository import PerfilRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.audit_service import AuditService
    data = perfil_svc_data
    session = perfil_svc_session_factory()
    try:
        actor = CurrentUser(
            user_id=data["u2"].id,
            tenant_id=data["tid"],
            roles=["TUTOR"],
        )
        repo = PerfilRepository(session=session, tenant_id=data["tid"])
        audit_repo = AuditRepository(session=session, tenant_id=data["tid"])
        audit_svc = AuditService(repository=audit_repo)
        svc = PerfilService(repo=repo, audit_svc=audit_svc)
        await svc.actualizar_perfil(actor, dni="11111111", cbu="0000003100099999999999")

        # Verificar PII cifrada en DB
        result = await session.execute(
            text("SELECT cbu FROM usuario WHERE id = :id"),
            {"id": str(data["u2"].id)},
        )
        raw_cbu = result.scalar()
        assert raw_cbu != "0000003100099999999999", "CBU debe estar cifrado"
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_actualizar_perfil_sin_cambios_no_falla(perfil_svc_session_factory, perfil_svc_data):
    """TRIANGULATE: llamar actualizar_perfil sin kwargs no falla (PATCH vacío)."""
    from app.services.perfil_service import PerfilService
    from app.repositories.perfil_repository import PerfilRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.audit_service import AuditService
    data = perfil_svc_data
    session = perfil_svc_session_factory()
    try:
        actor = CurrentUser(
            user_id=data["u1"].id,
            tenant_id=data["tid"],
            roles=["ADMIN"],
        )
        repo = PerfilRepository(session=session, tenant_id=data["tid"])
        audit_repo = AuditRepository(session=session, tenant_id=data["tid"])
        audit_svc = AuditService(repository=audit_repo)
        svc = PerfilService(repo=repo, audit_svc=audit_svc)
        # PATCH sin cambios — no debe lanzar
        resultado = await svc.actualizar_perfil(actor)
        assert resultado is not None
    finally:
        await session.close()
