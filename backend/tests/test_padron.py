"""
test_padron.py — TDD suite para C-09 padrón (repository + service + router).

Cubre tasks 8.x, 9.x, 12.x del tasks.md.

Ciclo: RED → GREEN → TRIANGULATE → REFACTOR.

DB real: activia_trace_test. Sin mocks de DB.
Mocks: MoodleWSClient (no llama a Moodle real).

Nota de arquitectura asyncio: los fixtures de sesión (db_session, test_app, async_client)
usan el event loop de la sesión. Los tests function-scoped usan el loop de función.
Para evitar "Future attached to a different loop", toda lógica de DB en los tests
usa directamente db_session (que ya está en el scope correcto).

Seguimos el mismo patrón que test_estructura_academica.py y test_usuarios_asignaciones.py:
setup inline por test, cleanup manual vía DELETE SQL.
"""
import datetime
import io
import uuid
from unittest.mock import AsyncMock, patch

import openpyxl
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.models.tenant import Tenant, TenantEstado
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.padron import EntradaPadron, VersionPadron
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia


# ---------------------------------------------------------------------------
# JWT / settings helper
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    roles: list,
    secret: str = TEST_SECRET_KEY,
) -> str:
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
        MOODLE_BASE_URL = None
        MOODLE_TOKEN = None
        MOODLE_SYNC_HOUR = 3
        PADRON_MAX_ROWS = 5000

    return FakeSettings()


# ---------------------------------------------------------------------------
# Setup helpers (inline per test)
# ---------------------------------------------------------------------------

async def _create_padron_tenant(db_session):
    """Crea un tenant con estructura académica básica para tests de padrón."""
    tenant = Tenant(nombre="Tenant Padron", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    carrera = Carrera(
        tenant_id=tenant.id,
        nombre="Ingeniería",
        codigo=f"ING-{uuid.uuid4().hex[:6]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera)
    await db_session.commit()
    await db_session.refresh(carrera)

    cohorte = Cohorte(
        tenant_id=tenant.id,
        carrera_id=carrera.id,
        nombre="Cohorte 2024",
        anio=2024,
        vig_desde=datetime.date(2024, 1, 1),
        estado=EstadoEstructura.activa,
    )
    db_session.add(cohorte)
    await db_session.commit()
    await db_session.refresh(cohorte)

    materia = Materia(
        tenant_id=tenant.id,
        nombre="Matemáticas",
        codigo=f"MAT-{uuid.uuid4().hex[:6]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)

    return tenant, carrera, cohorte, materia


async def _create_padron_roles_and_perms(db_session, tenant):
    """Crea roles y permisos padron:cargar / padron:gestionar para el tenant."""
    roles = {}
    for nombre in ("PROFESOR", "COORDINADOR", "ADMIN"):
        rol = Rol(tenant_id=tenant.id, nombre=nombre)
        db_session.add(rol)
    await db_session.commit()

    # Re-query to get IDs
    result = await db_session.execute(
        text("SELECT id, nombre FROM rol WHERE tenant_id = :tid"),
        {"tid": str(tenant.id)},
    )
    for row in result:
        roles[row[1]] = row[0]

    perm_cargar = Permiso(tenant_id=tenant.id, codigo="padron:cargar", modulo="padron", accion="cargar")
    perm_gestionar = Permiso(tenant_id=tenant.id, codigo="padron:gestionar", modulo="padron", accion="gestionar")
    db_session.add(perm_cargar)
    db_session.add(perm_gestionar)
    await db_session.commit()
    await db_session.refresh(perm_cargar)
    await db_session.refresh(perm_gestionar)

    for rol_nombre in ("PROFESOR", "COORDINADOR", "ADMIN"):
        db_session.add(RolPermiso(
            tenant_id=tenant.id,
            rol_id=uuid.UUID(str(roles[rol_nombre])),
            permiso_id=perm_cargar.id,
            scope=PermisoScope.global_,
        ))
    for rol_nombre in ("COORDINADOR", "ADMIN"):
        db_session.add(RolPermiso(
            tenant_id=tenant.id,
            rol_id=uuid.UUID(str(roles[rol_nombre])),
            permiso_id=perm_gestionar.id,
            scope=PermisoScope.global_,
        ))
    await db_session.commit()

    return perm_cargar, perm_gestionar


async def _create_test_usuario(db_session, tenant_id):
    """Crea un usuario de prueba con AuthIdentity real (C-28: auth_identity_id ≠ usuario.id).

    Usa create_usuario_con_identidad para garantizar que el JWT sub (auth_identity_id)
    resuelva correctamente a un Usuario de dominio vía resolve_domain_user_id.
    Retorna el Usuario; usa usuario.auth_identity_id como sub del JWT en endpoint tests.
    """
    from tests.conftest import create_usuario_con_identidad
    return await create_usuario_con_identidad(db_session, tenant_id)


async def _cleanup_padron(db_session, tenant_id):
    """Limpia todos los datos de padrón para el tenant en reverse FK order."""
    from tests.conftest import delete_audit_events_for_tenant
    await delete_audit_events_for_tenant(db_session, tenant_id)
    tid = str(tenant_id)
    await db_session.execute(text("DELETE FROM entrada_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM version_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM rol_permiso WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM permiso WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM rol WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM asignacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM cohorte WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM carrera WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM auth_identities WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid})
    await db_session.commit()


# ---------------------------------------------------------------------------
# Task 8.1 [RED] → 8.2 [GREEN]: get_active_version retorna None cuando no hay
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_active_version_none(db_session, monkeypatch):
    """
    RED: get_active_version sin versiones para materia×cohorte → None.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        result = await repo.get_active_version(materia.id, cohorte.id)
        assert result is None
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_get_active_version_unknown_materia(db_session, monkeypatch):
    """
    Triangulación: materia inexistente → None.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository

    tenant, _, cohorte, _ = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        result = await repo.get_active_version(uuid.uuid4(), cohorte.id)
        assert result is None
    finally:
        await _cleanup_padron(db_session, tenant.id)


# ---------------------------------------------------------------------------
# Task 8.3 [RED] → 8.4 [GREEN]: create_and_activate desactiva la versión previa
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_activate_deactivates_previous(db_session, monkeypatch):
    """
    RED: insertar v1 activa; create_and_activate(v2) → v1.activa=False, v2.activa=True.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)

        # Crear v1 activa
        v1_data = {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        v1 = await repo.create_and_activate(v1_data, [
            {"nombre": "A1", "apellidos": "B1", "email_encrypted": "a1@t.com"},
        ])
        assert v1.activa is True

        # Crear v2 → v1 debe quedar inactiva
        v2_data = {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        v2 = await repo.create_and_activate(v2_data, [
            {"nombre": "A2", "apellidos": "B2", "email_encrypted": "a2@t.com"},
        ])

        # Refresh v1
        await db_session.refresh(v1)
        assert v1.activa is False
        assert v2.activa is True
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_create_and_activate_first_version_no_previous(db_session, monkeypatch):
    """
    Triangulación: primera versión — no hay previa que desactivar.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        version_data = {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        version = await repo.create_and_activate(version_data, [])
        assert version.activa is True
        assert version.id is not None
    finally:
        await _cleanup_padron(db_session, tenant.id)


# ---------------------------------------------------------------------------
# Task 8.5 [RED] → 8.6 [GREEN]: aislamiento por tenant en get_active_version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation_active_version(db_session, monkeypatch):
    """
    RED: versión activa en tenant A → consulta en tenant B retorna None.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository

    tenant_a, _, cohorte, materia = await _create_padron_tenant(db_session)
    tenant_b = Tenant(nombre="Tenant B", estado=TenantEstado.ACTIVO)
    db_session.add(tenant_b)
    await db_session.commit()
    await db_session.refresh(tenant_b)

    try:
        repo_a = PadronRepository(session=db_session, tenant_id=tenant_a.id)
        version_data = {"tenant_id": tenant_a.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        version = await repo_a.create_and_activate(version_data, [])

        repo_b = PadronRepository(session=db_session, tenant_id=tenant_b.id)
        result_b = await repo_b.get_active_version(materia.id, cohorte.id)
        assert result_b is None

        result_a = await repo_a.get_active_version(materia.id, cohorte.id)
        assert result_a is not None
        assert result_a.id == version.id
    finally:
        await _cleanup_padron(db_session, tenant_a.id)
        await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": str(tenant_b.id)})
        await db_session.commit()


# ---------------------------------------------------------------------------
# Task 8.7 [RED] → 8.8 [GREEN]: soft_delete_version
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_version(db_session, monkeypatch):
    """
    RED: soft_delete_version → version.deleted_at set, version.activa=False, entries soft-deleted.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository
    from datetime import timezone

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        version_data = {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        entries = [
            {"nombre": "D1", "apellidos": "E1", "email_encrypted": "d1@t.com"},
            {"nombre": "D2", "apellidos": "E2", "email_encrypted": "d2@t.com"},
        ]
        version = await repo.create_and_activate(version_data, entries)

        now = datetime.datetime.now(tz=timezone.utc)
        await repo.soft_delete_version(version.id, now)

        await db_session.refresh(version)
        assert version.deleted_at is not None
        assert version.activa is False

        stmt = select(EntradaPadron).where(EntradaPadron.version_id == version.id)
        result = await db_session.execute(stmt)
        all_entries = list(result.scalars().all())
        assert len(all_entries) == 2
        assert all(e.deleted_at is not None for e in all_entries)
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_soft_delete_version_no_entries(db_session, monkeypatch):
    """
    Triangulación: soft_delete versión sin entradas — no falla.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository
    from datetime import timezone

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        version = await repo.create_and_activate(
            {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}, []
        )
        now = datetime.datetime.now(tz=timezone.utc)
        await repo.soft_delete_version(version.id, now)
        await db_session.refresh(version)
        assert version.deleted_at is not None
    finally:
        await _cleanup_padron(db_session, tenant.id)


# ---------------------------------------------------------------------------
# Tasks 9.x — Service tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_returns_rows_without_db_write(db_session, monkeypatch):
    """
    Task 9.1 RED → 9.2 GREEN:
    PadronService.preview con xlsx válido → retorna rows, 0 VersionPadron en DB.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.core.dependencies import CurrentUser

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["nombre", "apellidos", "email", "comision", "regional"])
        ws.append(["Fiona", "Torres", "fiona@test.com", "A", "Norte"])
        ws.append(["Gus", "Vera", "gus@test.com", "B", "Sur"])
        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()

        current_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant.id, roles=["PROFESOR"])
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session)
        rows = await svc.preview(xlsx_bytes, "padron.xlsx", materia.id, cohorte.id, current_user)

        assert len(rows) == 2
        assert rows[0].nombre == "Fiona"
        assert rows[1].nombre == "Gus"

        # Verify no DB writes
        result = await db_session.execute(
            select(VersionPadron).where(VersionPadron.tenant_id == tenant.id)
        )
        assert len(list(result.scalars().all())) == 0
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_activar_creates_version_and_entries(db_session, monkeypatch):
    """
    Task 9.3 RED → 9.4 GREEN:
    PadronService.activar con 3 rows → 1 VersionPadron (activa=True) + 3 EntradaPadron.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from app.schemas.padron import PadronRowDTO

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario = await _create_test_usuario(db_session, tenant.id)
        rows = [
            PadronRowDTO(nombre="H1", apellidos="A1", email="h1@test.com"),
            PadronRowDTO(nombre="H2", apellidos="A2", email="h2@test.com"),
            PadronRowDTO(nombre="H3", apellidos="A3", email="h3@test.com"),
        ]
        current_user = CurrentUser(user_id=usuario.id, tenant_id=tenant.id, roles=["COORDINADOR"])
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        version = await svc.activar(rows, materia.id, cohorte.id, current_user, domain_user_id=usuario.id)

        assert version.activa is True
        assert version.cargado_por == usuario.id

        result = await db_session.execute(
            select(EntradaPadron).where(
                EntradaPadron.version_id == version.id,
                EntradaPadron.deleted_at.is_(None),
            )
        )
        entries = list(result.scalars().all())
        assert len(entries) == 3
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_activar_records_audit_padron_cargar(db_session, monkeypatch):
    """
    Task 9.5 RED → 9.6 GREEN:
    Después de activar → AuditLog con accion='PADRON_CARGAR', filas_afectadas=2.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from app.schemas.padron import PadronRowDTO
    from app.models.audit import AuditEvent, AuditAction

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario = await _create_test_usuario(db_session, tenant.id)
        rows = [
            PadronRowDTO(nombre="I1", apellidos="B1", email="i1@test.com"),
            PadronRowDTO(nombre="I2", apellidos="B2", email="i2@test.com"),
        ]
        current_user = CurrentUser(user_id=usuario.id, tenant_id=tenant.id, roles=["COORDINADOR"])
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        await svc.activar(rows, materia.id, cohorte.id, current_user, domain_user_id=usuario.id)

        stmt = select(AuditEvent).where(
            AuditEvent.tenant_id == tenant.id,
            AuditEvent.actor_user_id == usuario.id,
            AuditEvent.accion == AuditAction.PADRON_CARGAR,
        )
        result = await db_session.execute(stmt)
        audit_entry = result.scalar_one_or_none()
        assert audit_entry is not None
        assert audit_entry.registros_afectados == 2
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_vaciar_own_version_succeeds(db_session, monkeypatch):
    """
    Task 9.7 RED → 9.8 GREEN:
    vaciar como el mismo usuario que cargó → soft-deleted.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from app.schemas.padron import PadronRowDTO

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario = await _create_test_usuario(db_session, tenant.id)
        current_user = CurrentUser(user_id=usuario.id, tenant_id=tenant.id, roles=["PROFESOR"])

        rows = [PadronRowDTO(nombre="J1", apellidos="C1", email="j1@test.com")]
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        version = await svc.activar(rows, materia.id, cohorte.id, current_user, domain_user_id=usuario.id)
        assert version.activa is True

        await svc.vaciar(materia.id, cohorte.id, current_user, has_gestionar=False, domain_user_id=usuario.id)

        await db_session.refresh(version)
        assert version.deleted_at is not None
        assert version.activa is False
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_vaciar_other_user_version_raises_403(db_session, monkeypatch):
    """
    Task 9.9 RED → 9.10 GREEN:
    vaciar versión de otro usuario como PROFESOR (sin padron:gestionar) → HTTPException 403.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from app.schemas.padron import PadronRowDTO
    from fastapi import HTTPException

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario_a = await _create_test_usuario(db_session, tenant.id)
        usuario_b = await _create_test_usuario(db_session, tenant.id)
        user_a = CurrentUser(user_id=usuario_a.id, tenant_id=tenant.id, roles=["PROFESOR"])
        user_b = CurrentUser(user_id=usuario_b.id, tenant_id=tenant.id, roles=["PROFESOR"])

        rows = [PadronRowDTO(nombre="K1", apellidos="D1", email="k1@test.com")]
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        await svc.activar(rows, materia.id, cohorte.id, user_a, domain_user_id=usuario_a.id)

        with pytest.raises(HTTPException) as exc_info:
            await svc.vaciar(materia.id, cohorte.id, user_b, has_gestionar=False, domain_user_id=usuario_b.id)

        assert exc_info.value.status_code == 403
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_vaciar_no_active_version_raises_404(db_session, monkeypatch):
    """
    Task 9.11 RED → 9.12 GREEN:
    vaciar sin versión activa → HTTPException 404.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from fastapi import HTTPException

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        current_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant.id, roles=["COORDINADOR"])
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        with pytest.raises(HTTPException) as exc_info:
            await svc.vaciar(uuid.uuid4(), uuid.uuid4(), current_user, has_gestionar=True, domain_user_id=uuid.uuid4())

        assert exc_info.value.status_code == 404
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_vaciar_gestionar_can_delete_any_version(db_session, monkeypatch):
    """
    Triangulación 9.8:
    Usuario con padron:gestionar puede vaciar versión de otro usuario.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from app.schemas.padron import PadronRowDTO

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario_a = await _create_test_usuario(db_session, tenant.id)
        usuario_coord = await _create_test_usuario(db_session, tenant.id)
        user_a = CurrentUser(user_id=usuario_a.id, tenant_id=tenant.id, roles=["PROFESOR"])
        coordinador = CurrentUser(user_id=usuario_coord.id, tenant_id=tenant.id, roles=["COORDINADOR"])

        rows = [PadronRowDTO(nombre="L1", apellidos="E1", email="l1@test.com")]
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        version = await svc.activar(rows, materia.id, cohorte.id, user_a, domain_user_id=usuario_a.id)
        await svc.vaciar(materia.id, cohorte.id, coordinador, has_gestionar=True, domain_user_id=usuario_coord.id)

        await db_session.refresh(version)
        assert version.activa is False
    finally:
        await _cleanup_padron(db_session, tenant.id)


# ---------------------------------------------------------------------------
# Tasks 9.13–9.16 — sync_from_moodle tests (mocked client)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_from_moodle_creates_version(db_session, monkeypatch):
    """
    Task 9.13 RED → 9.14 GREEN:
    sync_from_moodle con 2 usuarios mock → 1 VersionPadron + 2 EntradaPadron.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario = await _create_test_usuario(db_session, tenant.id)
        moodle_users = [
            {"firstname": "M1", "lastname": "F1", "email": "m1@moodle.com"},
            {"firstname": "M2", "lastname": "F2", "email": "m2@moodle.com"},
        ]
        mock_client = AsyncMock()
        mock_client.get_enrolled_users = AsyncMock(return_value=moodle_users)

        current_user = CurrentUser(user_id=usuario.id, tenant_id=tenant.id, roles=["COORDINADOR"])
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        version = await svc.sync_from_moodle(
            course_id=99, materia_id=materia.id, cohorte_id=cohorte.id,
            current_user=current_user, moodle_client=mock_client,
            domain_user_id=usuario.id,
        )

        assert version.activa is True

        result = await db_session.execute(
            select(EntradaPadron).where(
                EntradaPadron.version_id == version.id,
                EntradaPadron.deleted_at.is_(None),
            )
        )
        assert len(list(result.scalars().all())) == 2
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_sync_from_moodle_502_propagates(db_session, monkeypatch):
    """
    Task 9.15 RED → 9.16 GREEN:
    MoodleWSError(502) del cliente → service levanta HTTPException(502).
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.services.padron_service import PadronService
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.core.dependencies import CurrentUser
    from app.integrations.moodle_ws import MoodleWSError
    from fastapi import HTTPException

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        usuario = await _create_test_usuario(db_session, tenant.id)
        mock_client = AsyncMock()
        mock_client.get_enrolled_users = AsyncMock(
            side_effect=MoodleWSError(502, "Moodle WS unavailable")
        )
        current_user = CurrentUser(user_id=usuario.id, tenant_id=tenant.id, roles=["COORDINADOR"])
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        audit_repo = AuditRepository(session=db_session, tenant_id=tenant.id)
        svc = PadronService(repo=repo, db=db_session, audit_repo=audit_repo)

        with pytest.raises(HTTPException) as exc_info:
            await svc.sync_from_moodle(
                course_id=99, materia_id=materia.id, cohorte_id=cohorte.id,
                current_user=current_user, moodle_client=mock_client,
                domain_user_id=usuario.id,
            )

        assert exc_info.value.status_code == 502
    finally:
        await _cleanup_padron(db_session, tenant.id)


# ---------------------------------------------------------------------------
# Tasks 12.x — Router integration tests (using shared async_client fixture)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_endpoint_unauthenticated_returns_401(async_client, db_session, monkeypatch):
    """Task 12.1: preview sin auth → 401."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nombre", "apellidos", "email"])
    ws.append(["Test", "User", "test@test.com"])
    buf = io.BytesIO()
    wb.save(buf)

    resp = await async_client.post(
        "/api/v1/padron/preview",
        files={"file": ("padron.xlsx", buf.getvalue(), "application/octet-stream")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_preview_endpoint_unauthorized_returns_403(async_client, db_session, monkeypatch):
    """Task 12.2: preview con rol sin padron:cargar → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        # Create FINANZAS role (no padron:cargar grant)
        user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, user_id, ["FINANZAS"])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["nombre", "apellidos", "email"])
        ws.append(["Test", "User", "test@test.com"])
        buf = io.BytesIO()
        wb.save(buf)

        resp = await async_client.post(
            "/api/v1/padron/preview",
            files={"file": ("padron.xlsx", buf.getvalue(), "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_preview_endpoint_valid_file_returns_rows(async_client, db_session, monkeypatch):
    """Task 12.3: preview con archivo válido → 200 + rows."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        await _create_padron_roles_and_perms(db_session, tenant)

        user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, user_id, ["PROFESOR"])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["nombre", "apellidos", "email", "comision", "regional"])
        ws.append(["Test", "User", "test@preview.com", "A", "Norte"])
        ws.append(["Test2", "User2", "test2@preview.com", "B", "Sur"])
        buf = io.BytesIO()
        wb.save(buf)

        resp = await async_client.post(
            "/api/v1/padron/preview",
            files={"file": ("padron.xlsx", buf.getvalue(), "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["nombre"] == "Test"
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_activar_endpoint_creates_version(async_client, db_session, monkeypatch):
    """Task 12.4: activar endpoint crea versión."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        await _create_padron_roles_and_perms(db_session, tenant)
        usuario = await _create_test_usuario(db_session, tenant.id)
        # C-28: JWT sub must be auth_identity_id, not usuario.id
        token = _make_jwt(tenant.id, usuario.auth_identity_id, ["COORDINADOR"])

        body = {
            "materia_id": str(materia.id),
            "cohorte_id": str(cohorte.id),
            "rows": [
                {"nombre": "N1", "apellidos": "A1", "email": "n1@activar.com"},
                {"nombre": "N2", "apellidos": "A2", "email": "n2@activar.com"},
            ],
        }

        resp = await async_client.post(
            "/api/v1/padron/activar",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["activa"] is True
        assert data["filas_total"] == 2
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_vaciar_endpoint_403_on_other_user_version(async_client, db_session, monkeypatch):
    """Task 12.5: vaciar versión de otro usuario como PROFESOR → 403."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        await _create_padron_roles_and_perms(db_session, tenant)
        usuario_a = await _create_test_usuario(db_session, tenant.id)
        usuario_b = await _create_test_usuario(db_session, tenant.id)

        # User A (COORDINADOR) crea versión — C-28: JWT sub = auth_identity_id
        token_a = _make_jwt(tenant.id, usuario_a.auth_identity_id, ["COORDINADOR"])

        body = {
            "materia_id": str(materia.id),
            "cohorte_id": str(cohorte.id),
            "rows": [{"nombre": "P1", "apellidos": "Q1", "email": "p1@test.com"}],
        }
        resp_a = await async_client.post(
            "/api/v1/padron/activar",
            json=body,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.status_code == 201

        # User B (PROFESOR, sin gestionar) intenta vaciar → 403 — C-28: JWT sub = auth_identity_id
        token_b = _make_jwt(tenant.id, usuario_b.auth_identity_id, ["PROFESOR"])

        resp_b = await async_client.delete(
            f"/api/v1/padron/vaciar?materia_id={materia.id}&cohorte_id={cohorte.id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 403
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_sync_moodle_endpoint_503_when_not_configured(async_client, db_session, monkeypatch):
    """Task 12.6: sync-moodle → 503 cuando MOODLE_BASE_URL no está configurado."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        await _create_padron_roles_and_perms(db_session, tenant)

        user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, user_id, ["COORDINADOR"])

        body = {
            "course_id": 999,
            "materia_id": str(materia.id),
            "cohorte_id": str(cohorte.id),
        }

        # With MOODLE_BASE_URL=None (fake settings), should return 503
        resp = await async_client.post(
            "/api/v1/padron/sync-moodle",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 503
    finally:
        await _cleanup_padron(db_session, tenant.id)


# ---------------------------------------------------------------------------
# Task 13.x — usuario_id linking: EntradaPadron se linkea al Usuario existente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_activate_links_usuario_id_by_email(db_session, monkeypatch):
    """
    Task 13.1 RED → 13.2 GREEN:
    Si existe un Usuario en el tenant con el mismo email que una entrada del padrón,
    create_and_activate debe setear EntradaPadron.usuario_id = usuario.id.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository
    from app.models.usuario import Usuario, UsuarioEstado
    from app.core.security.passwords import email_lookup_hash

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        # Crear un usuario cuyo email coincide con una entrada del padrón
        email_alumno = "alumno-con-cuenta@test.com"
        usuario = Usuario(
            tenant_id=tenant.id,
            email_encrypted=email_alumno,
            email_hash=email_lookup_hash(email_alumno),
            nombre="Alumno",
            apellidos="ConCuenta",
            estado=UsuarioEstado.activo,
        )
        db_session.add(usuario)
        await db_session.commit()
        await db_session.refresh(usuario)

        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        version_data = {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        entries_data = [
            # Esta entrada tiene email que matchea el usuario creado
            {"nombre": "Alumno", "apellidos": "ConCuenta", "email_encrypted": email_alumno},
            # Esta entrada no tiene usuario en el sistema
            {"nombre": "Sin", "apellidos": "Cuenta", "email_encrypted": "sin-cuenta@test.com"},
        ]
        version = await repo.create_and_activate(version_data, entries_data)

        # Verificar el resultado de las entradas
        result = await db_session.execute(
            select(EntradaPadron).where(
                EntradaPadron.version_id == version.id,
                EntradaPadron.deleted_at.is_(None),
            )
        )
        entries = list(result.scalars().all())
        assert len(entries) == 2

        # Separar por nombre para verificar cada caso
        by_nombre = {e.nombre: e for e in entries}

        # La entrada con cuenta debe tener usuario_id seteado
        assert by_nombre["Alumno"].usuario_id == usuario.id, (
            "EntradaPadron.usuario_id debe ser linkeado al Usuario existente con el mismo email"
        )

        # La entrada sin cuenta debe tener usuario_id = None
        assert by_nombre["Sin"].usuario_id is None, (
            "EntradaPadron.usuario_id debe ser None cuando no hay Usuario con ese email"
        )
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_create_and_activate_no_link_when_no_users_exist(db_session, monkeypatch):
    """
    Task 13.3 TRIANGULATE:
    Si no hay ningún Usuario en el sistema, todas las entradas quedan con usuario_id = None.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository

    tenant, _, cohorte, materia = await _create_padron_tenant(db_session)
    try:
        repo = PadronRepository(session=db_session, tenant_id=tenant.id)
        version_data = {"tenant_id": tenant.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        entries_data = [
            {"nombre": "Nuevo", "apellidos": "Alumno", "email_encrypted": "nuevo@test.com"},
        ]
        version = await repo.create_and_activate(version_data, entries_data)

        result = await db_session.execute(
            select(EntradaPadron).where(EntradaPadron.version_id == version.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        assert entries[0].usuario_id is None
    finally:
        await _cleanup_padron(db_session, tenant.id)


@pytest.mark.asyncio
async def test_create_and_activate_tenant_isolation_no_cross_link(db_session, monkeypatch):
    """
    Task 13.4 TRIANGULATE — aislamiento multi-tenant:
    Un Usuario en tenant B no debe linkearse a entradas del padrón de tenant A,
    aunque el email sea idéntico.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    from app.repositories.padron_repository import PadronRepository
    from app.models.usuario import Usuario, UsuarioEstado
    from app.models.tenant import Tenant, TenantEstado
    from app.core.security.passwords import email_lookup_hash

    tenant_a, _, cohorte, materia = await _create_padron_tenant(db_session)
    tenant_b = Tenant(nombre="Tenant B Isolation", estado=TenantEstado.ACTIVO)
    db_session.add(tenant_b)
    await db_session.commit()
    await db_session.refresh(tenant_b)

    try:
        email_compartido = "compartido@test.com"

        # Crear usuario en tenant B con el mismo email
        usuario_b = Usuario(
            tenant_id=tenant_b.id,
            email_encrypted=email_compartido,
            email_hash=email_lookup_hash(email_compartido),
            nombre="Usuario",
            apellidos="TenantB",
            estado=UsuarioEstado.activo,
        )
        db_session.add(usuario_b)
        await db_session.commit()
        await db_session.refresh(usuario_b)

        # Importar padrón en tenant A con ese email
        repo_a = PadronRepository(session=db_session, tenant_id=tenant_a.id)
        version_data = {"tenant_id": tenant_a.id, "materia_id": materia.id, "cohorte_id": cohorte.id}
        entries_data = [
            {"nombre": "Alumno", "apellidos": "TenantA", "email_encrypted": email_compartido},
        ]
        version = await repo_a.create_and_activate(version_data, entries_data)

        result = await db_session.execute(
            select(EntradaPadron).where(EntradaPadron.version_id == version.id)
        )
        entries = list(result.scalars().all())
        assert len(entries) == 1
        # No debe linkearse al usuario de otro tenant
        assert entries[0].usuario_id is None, (
            "EntradaPadron de tenant A no debe linkearse al Usuario de tenant B"
        )
    finally:
        await _cleanup_padron(db_session, tenant_a.id)
        await db_session.execute(
            text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": str(tenant_b.id)}
        )
        await db_session.execute(
            text("DELETE FROM tenants WHERE id = :tid"), {"tid": str(tenant_b.id)}
        )
        await db_session.commit()
