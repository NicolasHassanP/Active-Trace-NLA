"""
TDD tests for ComunicacionRepository and TenantConfigRepository.

C-12 Tasks: 4.1 (SAFETY NET), 4.2-4.4 (encolar_lote), 5.1-5.2 (TenantConfigRepository).

Uses real DB, no mocks.
"""
import uuid

import pytest
from sqlalchemy import text

from app.models.tenant import Tenant, TenantEstado
from app.models.comunicacion import ComunicacionEstado as ModelEstado
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.repositories.tenant_config_repository import TenantConfigRepository


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
        nombre=f"TenantRepo-{uuid.uuid4().hex[:6]}",
        estado=TenantEstado.ACTIVO,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


# ---------------------------------------------------------------------------
# §4.2 — RED: encolar_lote crea N registros Pendiente con lote_id común
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_lote_crea_registros_pendiente(db_session, create_tables, monkeypatch):
    """encolar_lote() crea N registros en estado Pendiente con el mismo lote_id."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    tenant_id = tenant.id
    lote_id = uuid.uuid4()
    destinatarios = ["a@test.edu", "b@test.edu", "c@test.edu"]

    repo = ComunicacionRepository(session=db_session, tenant_id=tenant_id)

    try:
        created = await repo.encolar_lote(
            destinatarios=destinatarios,
            asunto="Asunto de prueba",
            cuerpo="Cuerpo de prueba",
            lote_id=lote_id,
        )

        assert len(created) == 3
        for com in created:
            assert com.estado == ModelEstado.Pendiente
            assert com.lote_id == lote_id
            assert com.tenant_id == tenant_id
    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant_id)},
        )
        await db_session.commit()


# ---------------------------------------------------------------------------
# §4.4 — TRIANGULATE: aislamiento multi-tenant y list_by_lote
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_lote_aislamiento_multitenant(db_session, create_tables, monkeypatch):
    """Tenant B no ve el lote del Tenant A."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant_a = await _make_tenant(db_session)
    tenant_b = await _make_tenant(db_session)
    lote_id = uuid.uuid4()

    repo_a = ComunicacionRepository(session=db_session, tenant_id=tenant_a.id)

    try:
        await repo_a.encolar_lote(
            destinatarios=["x@test.edu"],
            asunto="Solo de A",
            cuerpo="Cuerpo",
            lote_id=lote_id,
        )

        # Tenant B no debe ver el lote de A
        repo_b = ComunicacionRepository(session=db_session, tenant_id=tenant_b.id)
        lote_b = await repo_b.list_by_lote(lote_id)
        assert len(lote_b) == 0, "Tenant B no debe ver el lote de Tenant A"

        # Tenant A ve su propio lote
        lote_a = await repo_a.list_by_lote(lote_id)
        assert len(lote_a) == 1

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE tenant_id IN (:a, :b)"),
            {"a": str(tenant_a.id), "b": str(tenant_b.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id IN (:a, :b)"),
            {"a": str(tenant_a.id), "b": str(tenant_b.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_list_by_lote_filtra_por_lote(db_session, create_tables, monkeypatch):
    """list_by_lote() solo retorna los mensajes del lote especificado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    lote_1 = uuid.uuid4()
    lote_2 = uuid.uuid4()

    repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)

    try:
        await repo.encolar_lote(
            destinatarios=["lote1@test.edu"],
            asunto="Lote 1",
            cuerpo="Cuerpo 1",
            lote_id=lote_1,
        )
        await repo.encolar_lote(
            destinatarios=["lote2a@test.edu", "lote2b@test.edu"],
            asunto="Lote 2",
            cuerpo="Cuerpo 2",
            lote_id=lote_2,
        )

        resultado_lote1 = await repo.list_by_lote(lote_1)
        resultado_lote2 = await repo.list_by_lote(lote_2)

        assert len(resultado_lote1) == 1
        assert len(resultado_lote2) == 2

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


# ---------------------------------------------------------------------------
# §5.1-5.2 — TenantConfigRepository.get_bool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_tenant_config_get_bool_true(db_session, create_tables, monkeypatch):
    """get_bool() retorna True cuando la fila existe con valor 'true'."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    repo = TenantConfigRepository(session=db_session, tenant_id=tenant.id)

    try:
        await repo.set_config("aprobacion_comunicacion_requerida", "true")
        result = await repo.get_bool("aprobacion_comunicacion_requerida", default=False)
        assert result is True
    finally:
        await db_session.execute(
            text("DELETE FROM tenant_config WHERE tenant_id = :tid"),
            {"tid": str(tenant.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_tenant_config_get_bool_false_ausente(db_session, create_tables, monkeypatch):
    """get_bool() retorna el default cuando la fila no existe."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    repo = TenantConfigRepository(session=db_session, tenant_id=tenant.id)

    try:
        result = await repo.get_bool("clave_inexistente", default=False)
        assert result is False

        result_true_default = await repo.get_bool("clave_inexistente", default=True)
        assert result_true_default is True
    finally:
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_tenant_config_get_bool_aislamiento_tenant(db_session, create_tables, monkeypatch):
    """Tenant A no lee el flag de Tenant B."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant_a = await _make_tenant(db_session)
    tenant_b = await _make_tenant(db_session)

    repo_a = TenantConfigRepository(session=db_session, tenant_id=tenant_a.id)
    repo_b = TenantConfigRepository(session=db_session, tenant_id=tenant_b.id)

    try:
        # Solo Tenant A tiene la config
        await repo_a.set_config("aprobacion_comunicacion_requerida", "true")

        result_a = await repo_a.get_bool("aprobacion_comunicacion_requerida", default=False)
        result_b = await repo_b.get_bool("aprobacion_comunicacion_requerida", default=False)

        assert result_a is True, "Tenant A debe leer su propia config"
        assert result_b is False, "Tenant B no debe leer la config de Tenant A"

    finally:
        await db_session.execute(
            text("DELETE FROM tenant_config WHERE tenant_id IN (:a, :b)"),
            {"a": str(tenant_a.id), "b": str(tenant_b.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id IN (:a, :b)"),
            {"a": str(tenant_a.id), "b": str(tenant_b.id)},
        )
        await db_session.commit()
