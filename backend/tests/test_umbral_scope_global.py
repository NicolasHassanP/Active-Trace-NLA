"""
TDD tests for ADMIN scope global + umbral por-materia feature.

Covers:
    - get_efectivo precedence: override → default materia/cohorte → 60%
    - ADMIN (scope global) GET/PUT umbral sin asignacion → 200
    - PROFESOR (scope propio) GET/PUT umbral → override (comportamiento actual)
    - Usuario sin permiso → 403
    - Aislamiento por tenant
    - 404 si scope propio y no tiene asignacion

Strict TDD: RED → GREEN → triangulate → REFACTOR.
Uses real DB, no DB mocks. create_usuario_con_identidad() pattern (C-28).
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from app.models.tenant import Tenant, TenantEstado
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.usuario import Asignacion, RolAsignacion
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.calificacion import UmbralMateria


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


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
        UMBRAL_PCT_DEFECTO = 60
        VALORES_APROBATORIOS_DEFECTO = ["Satisfactorio", "Supera lo esperado"]
        NOTA_MAXIMA_DEFECTO = 10.0

    return FakeSettings()


def _make_jwt(tenant_id, user_id, roles):
    import datetime
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
    return jose_jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")


async def _create_umbral_context(db_session, monkeypatch):
    """
    Create a context with: tenant, carrera, cohorte, materia, roles/permisos,
    ADMIN user (scope global) and PROFESOR user (scope propio, with asignacion).
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    try:
        await db_session.rollback()
    except Exception:
        pass

    tenant = Tenant(nombre=f"Umbral Scope Tenant {uuid.uuid4().hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    # Academic structure
    carrera = Carrera(
        tenant_id=tenant.id,
        nombre="Ingeniería Umbral",
        codigo=f"IU-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera)
    await db_session.commit()
    await db_session.refresh(carrera)

    cohorte = Cohorte(
        tenant_id=tenant.id,
        nombre="Cohorte Umbral 2026",
        anio=2026,
        carrera_id=carrera.id,
        vig_desde=date(2026, 3, 1),
        estado=EstadoEstructura.activa,
    )
    db_session.add(cohorte)
    await db_session.commit()
    await db_session.refresh(cohorte)

    materia = Materia(
        tenant_id=tenant.id,
        nombre="Algebra Umbral",
        codigo=f"AU-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)

    # Roles
    for rol_nombre in ("PROFESOR", "COORDINADOR", "ADMIN", "FINANZAS"):
        db_session.add(Rol(tenant_id=tenant.id, nombre=rol_nombre))
    await db_session.commit()

    from sqlalchemy import select as sqla_select
    from app.models.rbac import Rol as RolModel
    result = await db_session.execute(sqla_select(RolModel).where(RolModel.tenant_id == tenant.id))
    roles = {r.nombre: r for r in result.scalars().all()}

    # Permission calificaciones:configurar-umbral
    perm_umbral = Permiso(
        tenant_id=tenant.id,
        codigo="calificaciones:configurar-umbral",
        modulo="calificaciones",
        accion="configurar-umbral",
    )
    db_session.add(perm_umbral)
    await db_session.commit()
    await db_session.refresh(perm_umbral)

    # ADMIN → global, PROFESOR → propio
    db_session.add(RolPermiso(
        tenant_id=tenant.id,
        rol_id=roles["ADMIN"].id,
        permiso_id=perm_umbral.id,
        scope=PermisoScope.global_,
    ))
    db_session.add(RolPermiso(
        tenant_id=tenant.id,
        rol_id=roles["COORDINADOR"].id,
        permiso_id=perm_umbral.id,
        scope=PermisoScope.global_,
    ))
    db_session.add(RolPermiso(
        tenant_id=tenant.id,
        rol_id=roles["PROFESOR"].id,
        permiso_id=perm_umbral.id,
        scope=PermisoScope.propio,
    ))
    await db_session.commit()

    # ADMIN user (no asignacion — scope global)
    from tests.conftest import create_usuario_con_identidad
    admin_email = f"admin-{uuid.uuid4().hex[:8]}@umbral.test"
    admin = await create_usuario_con_identidad(
        db_session, tenant.id,
        email=admin_email,
        nombre="Admin Umbral",
        apellidos="Test",
    )
    await db_session.commit()
    await db_session.refresh(admin)

    # PROFESOR user (con asignacion a la materia)
    prof_email = f"prof-{uuid.uuid4().hex[:8]}@umbral.test"
    profesor = await create_usuario_con_identidad(
        db_session, tenant.id,
        email=prof_email,
        nombre="Prof Umbral",
        apellidos="Test",
    )
    await db_session.commit()
    await db_session.refresh(profesor)

    asignacion = Asignacion(
        tenant_id=tenant.id,
        usuario_id=profesor.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia.id,
        desde=date(2026, 1, 1),
    )
    db_session.add(asignacion)
    await db_session.commit()
    await db_session.refresh(asignacion)

    return {
        "tenant": tenant,
        "carrera": carrera,
        "cohorte": cohorte,
        "materia": materia,
        "roles": roles,
        "perm_umbral": perm_umbral,
        "admin": admin,
        "profesor": profesor,
        "asignacion": asignacion,
    }


async def _cleanup_umbral(db_session, tenant_id: uuid.UUID):
    from tests.conftest import delete_audit_events_for_tenant
    await delete_audit_events_for_tenant(db_session, tenant_id)
    tid = str(tenant_id)
    await db_session.execute(text("DELETE FROM umbral_materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM asignacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM rol_permiso WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM permiso WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM rol WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM cohorte WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM carrera WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM auth_identities WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid})
    await db_session.commit()


def _make_umbral_service(db_session, tenant_id):
    from app.repositories.calificacion_repository import CalificacionRepository
    from app.services.umbral_service import UmbralService
    repo = CalificacionRepository(session=db_session, tenant_id=tenant_id)
    return UmbralService(repo=repo)


# ---------------------------------------------------------------------------
# §U1 — get_efectivo: precedencia override → default materia/cohorte → 60%
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_efectivo_returns_system_default_when_no_records(db_session, create_tables, monkeypatch):
    """
    §U1.1 RED→GREEN: No UmbralMateria records → get_efectivo returns system default (60%).
    is_default=True.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]

    try:
        svc = _make_umbral_service(db_session, tenant.id)
        result = await svc.get_efectivo(
            materia_id=materia.id,
            asignacion_id=None,
            cohorte_id=None,
        )
        assert result.is_default is True
        assert result.umbral_pct == 60
        assert result.asignacion_id is None
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_get_efectivo_returns_default_materia_cohorte_when_set(db_session, create_tables, monkeypatch):
    """
    §U1.2 TRIANGULATE: When default materia/cohorte record exists → returns it with is_default=True.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]

    try:
        # Create a default umbral (asignacion_id=None)
        default_umbral = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=None,
            cohorte_id=cohorte.id,
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=["Aprobado"],
        )
        db_session.add(default_umbral)
        await db_session.commit()
        await db_session.refresh(default_umbral)

        svc = _make_umbral_service(db_session, tenant.id)
        result = await svc.get_efectivo(
            materia_id=materia.id,
            asignacion_id=None,
            cohorte_id=cohorte.id,
        )
        assert result.is_default is True
        assert result.umbral_pct == 75
        assert result.asignacion_id is None
        assert result.cohorte_id == cohorte.id
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_get_efectivo_override_takes_precedence_over_default(db_session, create_tables, monkeypatch):
    """
    §U1.3 TRIANGULATE: Override (asignacion_id set) beats default materia/cohorte.
    is_default=False.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    asignacion = ctx["asignacion"]

    try:
        # Create both default and override
        default_umbral = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=None,
            cohorte_id=cohorte.id,
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=["Aprobado"],
        )
        override_umbral = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            cohorte_id=None,
            materia_id=materia.id,
            umbral_pct=80,
            valores_aprobatorios=["Satisfactorio"],
        )
        db_session.add(default_umbral)
        db_session.add(override_umbral)
        await db_session.commit()

        svc = _make_umbral_service(db_session, tenant.id)
        result = await svc.get_efectivo(
            materia_id=materia.id,
            asignacion_id=asignacion.id,
            cohorte_id=cohorte.id,
        )
        # Override takes precedence
        assert result.is_default is False
        assert result.umbral_pct == 80
        assert result.asignacion_id == asignacion.id
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §U2 — ADMIN (scope global) GET/PUT sin asignacion → 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_get_umbral_without_asignacion_returns_200(async_client, db_session, monkeypatch):
    """
    §U2.1 RED→GREEN: ADMIN GET /umbral con scope global → 200 (no 404/500).
    No exige asignación propia del ADMIN.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    admin = ctx["admin"]
    materia = ctx["materia"]

    try:
        # ADMIN has no asignacion in this materia — should work with global scope
        token = _make_jwt(tenant.id, admin.auth_identity_id, ["ADMIN"])
        resp = await async_client.get(
            "/api/v1/calificaciones/umbral",
            params={"materia_id": str(materia.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["is_default"] is True
        assert data["umbral_pct"] == 60  # system default
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_admin_put_umbral_without_asignacion_creates_default(async_client, db_session, monkeypatch):
    """
    §U2.2 TRIANGULATE: ADMIN PUT /umbral con scope global → creates default record (asignacion_id=None).
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    admin = ctx["admin"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]

    try:
        token = _make_jwt(tenant.id, admin.auth_identity_id, ["ADMIN"])
        payload = {
            "materia_id": str(materia.id),
            "umbral_pct": 70,
            "valores_aprobatorios": ["Aprobado"],
            "cohorte_id": str(cohorte.id),
        }
        resp = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["umbral_pct"] == 70
        assert data["asignacion_id"] is None  # default scope global
        assert data["is_default"] is True  # it's a default record
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_admin_put_umbral_idempotent_update(async_client, db_session, monkeypatch):
    """
    §U2.3 TRIANGULATE: ADMIN PUT /umbral twice → updates (no duplicate).
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    admin = ctx["admin"]
    materia = ctx["materia"]

    try:
        token = _make_jwt(tenant.id, admin.auth_identity_id, ["ADMIN"])
        payload = {
            "materia_id": str(materia.id),
            "umbral_pct": 70,
            "valores_aprobatorios": ["Aprobado"],
        }
        resp1 = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 200

        payload2 = {
            "materia_id": str(materia.id),
            "umbral_pct": 80,
            "valores_aprobatorios": ["Aprobado", "Excelente"],
        }
        resp2 = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload2,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["umbral_pct"] == 80
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §U3 — PROFESOR (scope propio) → override (comportamiento actual)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profesor_put_umbral_creates_override(async_client, db_session, monkeypatch):
    """
    §U3.1 RED→GREEN: PROFESOR PUT /umbral → creates override with asignacion_id set.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    materia = ctx["materia"]

    try:
        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])
        payload = {
            "materia_id": str(materia.id),
            "umbral_pct": 65,
            "valores_aprobatorios": ["Satisfactorio"],
        }
        resp = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["umbral_pct"] == 65
        assert data["asignacion_id"] is not None  # override — has asignacion
        assert data["is_default"] is False
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_profesor_get_umbral_returns_override_when_set(async_client, db_session, monkeypatch):
    """
    §U3.2 TRIANGULATE: PROFESOR GET /umbral → returns own override.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    materia = ctx["materia"]
    asignacion = ctx["asignacion"]

    try:
        # Create an override record directly
        override = UmbralMateria(
            tenant_id=tenant.id,
            asignacion_id=asignacion.id,
            cohorte_id=None,
            materia_id=materia.id,
            umbral_pct=72,
            valores_aprobatorios=["Satisfactorio"],
        )
        db_session.add(override)
        await db_session.commit()

        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])
        resp = await async_client.get(
            "/api/v1/calificaciones/umbral",
            params={"materia_id": str(materia.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["umbral_pct"] == 72
        assert data["is_default"] is False
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_profesor_get_umbral_returns_default_when_no_override(async_client, db_session, monkeypatch):
    """
    §U3.3 TRIANGULATE: PROFESOR GET /umbral with no override → falls through to system default.
    is_default=True.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    materia = ctx["materia"]

    try:
        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])
        resp = await async_client.get(
            "/api/v1/calificaciones/umbral",
            params={"materia_id": str(materia.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["is_default"] is True
        assert data["umbral_pct"] == 60
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §U4 — Sin permiso → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_usuario_sin_permiso_get_umbral_returns_403(async_client, db_session, monkeypatch):
    """
    §U4.1 RED→GREEN: FINANZAS (no permission) GET /umbral → 403.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]

    try:
        finanzas_user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, finanzas_user_id, ["FINANZAS"])
        resp = await async_client.get(
            "/api/v1/calificaciones/umbral",
            params={"materia_id": str(materia.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_usuario_sin_permiso_put_umbral_returns_403(async_client, db_session, monkeypatch):
    """
    §U4.2 TRIANGULATE: FINANZAS PUT /umbral → 403.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]

    try:
        finanzas_user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, finanzas_user_id, ["FINANZAS"])
        payload = {
            "materia_id": str(materia.id),
            "umbral_pct": 70,
            "valores_aprobatorios": [],
        }
        resp = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §U5 — Aislamiento por tenant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_umbral_isolation_per_tenant(db_session, create_tables, monkeypatch):
    """
    §U5.1 RED→GREEN: Default umbral del tenant A no es visible desde el tenant B.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant_a = ctx["tenant"]
    materia_a = ctx["materia"]

    # Create a second tenant + materia
    tenant_b = Tenant(nombre=f"Tenant B {uuid.uuid4().hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant_b)
    await db_session.commit()
    await db_session.refresh(tenant_b)

    carrera_b = Carrera(
        tenant_id=tenant_b.id,
        nombre="Carrera B",
        codigo=f"CB-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera_b)
    await db_session.commit()

    materia_b = Materia(
        tenant_id=tenant_b.id,
        nombre="Materia B",
        codigo=f"MB-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia_b)
    await db_session.commit()
    await db_session.refresh(materia_b)

    try:
        # Set default for tenant_a/materia_a
        svc_a = _make_umbral_service(db_session, tenant_a.id)
        from app.core.dependencies import CurrentUser
        fake_user_a = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_a.id, roles=["ADMIN"])
        await svc_a.configurar(
            materia_id=materia_a.id,
            umbral_pct=77,
            valores_aprobatorios=[],
            current_user=fake_user_a,
            asignacion_id=None,
        )

        # Query from tenant_b perspective → should NOT see tenant_a's record
        svc_b = _make_umbral_service(db_session, tenant_b.id)
        result_b = await svc_b.get_efectivo(
            materia_id=materia_b.id,
            asignacion_id=None,
            cohorte_id=None,
        )
        # Should fall back to system default (60%), not tenant_a's 77%
        assert result_b.umbral_pct == 60
        assert result_b.is_default is True
    finally:
        await _cleanup_umbral(db_session, tenant_a.id)
        # Also clean tenant_b
        tid_b = str(tenant_b.id)
        await db_session.execute(text("DELETE FROM materia WHERE tenant_id = :tid"), {"tid": tid_b})
        await db_session.execute(text("DELETE FROM carrera WHERE tenant_id = :tid"), {"tid": tid_b})
        await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid_b})
        await db_session.commit()


# ---------------------------------------------------------------------------
# §U6 — scope propio + sin asignacion → 404 (no 500)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profesor_sin_asignacion_get_umbral_returns_404(async_client, db_session, monkeypatch):
    """
    §U6.1 RED→GREEN: PROFESOR (scope propio) GET /umbral para materia sin asignacion → 404 limpio (no 500).
    Mensaje en español.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]

    # Create a different materia (no asignacion for profesor)
    materia_otro = Materia(
        tenant_id=tenant.id,
        nombre="Otra Materia",
        codigo=f"OM-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia_otro)
    await db_session.commit()
    await db_session.refresh(materia_otro)

    try:
        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])
        resp = await async_client.get(
            "/api/v1/calificaciones/umbral",
            params={"materia_id": str(materia_otro.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        # Message should be in Spanish (not raw English "No active asignacion found...")
        detail = resp.json().get("detail", "")
        assert "asignaci" in detail.lower() or "materia" in detail.lower(), \
            f"Expected Spanish error message, got: {detail}"
        assert "No active asignacion found" not in detail, \
            "Should not expose raw English error"
    finally:
        # Cleanup the extra materia
        await db_session.execute(
            text("DELETE FROM materia WHERE tenant_id = :tid AND nombre = 'Otra Materia'"),
            {"tid": str(tenant.id)},
        )
        await db_session.commit()
        await _cleanup_umbral(db_session, tenant.id)


@pytest.mark.asyncio
async def test_profesor_sin_asignacion_put_umbral_returns_404(async_client, db_session, monkeypatch):
    """
    §U6.2 TRIANGULATE: PROFESOR PUT /umbral para materia sin asignacion → 404.
    """
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]

    materia_otro = Materia(
        tenant_id=tenant.id,
        nombre="Otra Materia PUT",
        codigo=f"OMP-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia_otro)
    await db_session.commit()
    await db_session.refresh(materia_otro)

    try:
        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])
        payload = {
            "materia_id": str(materia_otro.id),
            "umbral_pct": 70,
            "valores_aprobatorios": [],
        }
        resp = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    finally:
        await db_session.execute(
            text("DELETE FROM materia WHERE tenant_id = :tid AND nombre = 'Otra Materia PUT'"),
            {"tid": str(tenant.id)},
        )
        await db_session.commit()
        await _cleanup_umbral(db_session, tenant.id)
