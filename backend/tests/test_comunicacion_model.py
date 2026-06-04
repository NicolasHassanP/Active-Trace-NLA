"""
TDD tests for Comunicacion model (Tasks 3.3, 3.5 RED/GREEN/TRIANGULATE)
and TenantConfig model (Task 3.6, 3.7).

C-12 Design Decisions:
    - destinatario cifrado (EncryptedString); __repr__ no expone PII.
    - TenantConfig: UNIQUE (tenant_id, clave) WHERE deleted_at IS NULL.
    - Soft delete: delete marca deleted_at, nunca borra físicamente.
    - Scope por tenant: repo filtra por tenant automáticamente.

Uses real DB, no mocks. Follows test_calificaciones.py pattern.
"""
import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.models.tenant import Tenant, TenantEstado
from app.models.comunicacion import Comunicacion, ComunicacionEstado as ModelEstado
from app.models.tenant_config import TenantConfig
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
        nombre=f"TenantCom-{uuid.uuid4().hex[:6]}",
        estado=TenantEstado.ACTIVO,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


# ---------------------------------------------------------------------------
# §3.3 — RED/GREEN: destinatario cifrado, __repr__ sin PII
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_comunicacion_destinatario_cifrado_en_db(db_session, create_tables, monkeypatch):
    """
    El campo destinatario se almacena cifrado en la DB y se descifra al leer.
    __repr__ no expone el email en texto plano.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    lote_id = uuid.uuid4()

    com = Comunicacion(
        tenant_id=tenant.id,
        destinatario="alumno@test.edu",
        asunto="Aviso importante",
        cuerpo="Hola alumno",
        estado=ModelEstado.Pendiente,
        lote_id=lote_id,
    )
    db_session.add(com)
    await db_session.commit()
    await db_session.refresh(com)

    try:
        # El ORM retorna el valor descifrado
        assert com.destinatario == "alumno@test.edu"

        # En la DB el valor debe estar cifrado (no texto plano)
        raw = await db_session.execute(
            text("SELECT destinatario FROM comunicacion WHERE id = :id"),
            {"id": str(com.id)},
        )
        raw_val = raw.scalar()
        assert raw_val != "alumno@test.edu", "destinatario se guardó en texto plano (debe estar cifrado)"
        assert len(raw_val) > 20, "El valor cifrado debe tener longitud razonable"

        # __repr__ no expone el email
        repr_str = repr(com)
        assert "alumno@test.edu" not in repr_str

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE id = :id"),
            {"id": str(com.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


# ---------------------------------------------------------------------------
# §3.5 — TRIANGULATE: soft delete y scope por tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_comunicacion_soft_delete(db_session, create_tables, monkeypatch):
    """delete() marca deleted_at, no borra físicamente."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    lote_id = uuid.uuid4()

    com = Comunicacion(
        tenant_id=tenant.id,
        destinatario="soft@test.edu",
        asunto="Asunto",
        cuerpo="Cuerpo",
        estado=ModelEstado.Pendiente,
        lote_id=lote_id,
    )
    db_session.add(com)
    await db_session.commit()
    await db_session.refresh(com)

    try:
        repo = ComunicacionRepository(session=db_session, tenant_id=tenant.id)
        await repo.delete(com)

        # La fila sigue en la DB
        raw = await db_session.execute(
            text("SELECT deleted_at FROM comunicacion WHERE id = :id"),
            {"id": str(com.id)},
        )
        deleted_at = raw.scalar()
        assert deleted_at is not None, "deleted_at debe ser no-nulo tras soft delete"

        # El repositorio ya no la lista
        activos = await repo.list()
        ids = [c.id for c in activos]
        assert com.id not in ids

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE id = :id"),
            {"id": str(com.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant.id)},
        )
        await db_session.commit()


@pytest.mark.asyncio(loop_scope="function")
async def test_comunicacion_scope_tenant(db_session, create_tables, monkeypatch):
    """Un tenant no ve las comunicaciones de otro tenant."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant_a = await _make_tenant(db_session)
    tenant_b = await _make_tenant(db_session)
    lote_id = uuid.uuid4()

    com_a = Comunicacion(
        tenant_id=tenant_a.id,
        destinatario="a@test.edu",
        asunto="Asunto A",
        cuerpo="Cuerpo A",
        estado=ModelEstado.Pendiente,
        lote_id=lote_id,
    )
    db_session.add(com_a)
    await db_session.commit()
    await db_session.refresh(com_a)

    try:
        repo_b = ComunicacionRepository(session=db_session, tenant_id=tenant_b.id)
        result_b = await repo_b.list()
        assert com_a.id not in [c.id for c in result_b], "Tenant B no debe ver comunicaciones de Tenant A"

        repo_a = ComunicacionRepository(session=db_session, tenant_id=tenant_a.id)
        result_a = await repo_a.list()
        assert com_a.id in [c.id for c in result_a], "Tenant A debe ver su propia comunicacion"

    finally:
        await db_session.execute(
            text("DELETE FROM comunicacion WHERE id = :id"),
            {"id": str(com_a.id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id IN (:a, :b)"),
            {"a": str(tenant_a.id), "b": str(tenant_b.id)},
        )
        await db_session.commit()


# ---------------------------------------------------------------------------
# §3.6 — RED: TenantConfig unicidad (tenant_id, clave)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_tenant_config_unique_clave_por_tenant(db_session, create_tables, monkeypatch):
    """UNIQUE (tenant_id, clave) — duplicado viola el índice."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant = await _make_tenant(db_session)
    tenant_id = tenant.id  # capture before potential error states

    cfg1 = TenantConfig(
        tenant_id=tenant_id,
        clave="aprobacion_comunicacion_requerida",
        valor="true",
    )
    db_session.add(cfg1)
    await db_session.commit()
    await db_session.refresh(cfg1)
    cfg1_id = cfg1.id

    raised = False
    try:
        # Intentar duplicar la misma clave debe fallar
        cfg2 = TenantConfig(
            tenant_id=tenant_id,
            clave="aprobacion_comunicacion_requerida",
            valor="false",
        )
        db_session.add(cfg2)
        from sqlalchemy.exc import IntegrityError
        try:
            await db_session.commit()
        except IntegrityError:
            raised = True
            await db_session.rollback()
    finally:
        await db_session.execute(
            text("DELETE FROM tenant_config WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :id"),
            {"id": str(tenant_id)},
        )
        await db_session.commit()

    assert raised, "Insertar clave duplicada en tenant_config debería lanzar IntegrityError"


@pytest.mark.asyncio(loop_scope="function")
async def test_tenant_config_diferentes_tenants_misma_clave(db_session, create_tables, monkeypatch):
    """La misma clave puede existir en tenants distintos (no viola el UNIQUE)."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    tenant_a = await _make_tenant(db_session)
    tenant_b = await _make_tenant(db_session)

    cfg_a = TenantConfig(
        tenant_id=tenant_a.id,
        clave="aprobacion_comunicacion_requerida",
        valor="true",
    )
    cfg_b = TenantConfig(
        tenant_id=tenant_b.id,
        clave="aprobacion_comunicacion_requerida",
        valor="false",
    )
    db_session.add(cfg_a)
    db_session.add(cfg_b)
    try:
        await db_session.commit()
        await db_session.refresh(cfg_a)
        await db_session.refresh(cfg_b)
        assert cfg_a.id != cfg_b.id
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
