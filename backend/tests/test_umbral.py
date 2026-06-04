"""
TDD tests for UmbralService and CalificacionRepository (umbral portion).

C-10 Design Decision D5:
    UmbralService.get_efectivo(asignacion_id, materia_id) returns UmbralMateriaRead:
        - If no UmbralMateria record → returns defaults (umbral_pct=60, valores_aprobatorios default).
        - If exists → returns configured values.
    UmbralService.configurar(materia_id, umbral_pct, valores_aprobatorios, current_user):
        - Resolves asignacion_id from current_user.user_id + materia_id.
        - Get-or-create upsert.
        - Returns UmbralMateriaRead.

Safety net: pre-existing tests must still pass before these run.
Uses real DB (no mock), inline setup per test with try/finally cleanup (same pattern as test_padron.py).
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from app.core.dependencies import CurrentUser
from app.models.calificacion import UmbralMateria
from app.models.estructura import Materia, EstadoEstructura
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.tenant import Tenant, TenantEstado
from app.repositories.calificacion_repository import CalificacionRepository
from app.services.umbral_service import UmbralService
from app.schemas.calificacion import UmbralMateriaRead


# ---------------------------------------------------------------------------
# Helpers — monkeypatch settings to avoid reading from .env
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


def _make_current_user(user_id: uuid.UUID, tenant_id: uuid.UUID) -> CurrentUser:
    return CurrentUser(user_id=user_id, tenant_id=tenant_id, roles=["PROFESOR"])


# ---------------------------------------------------------------------------
# Inline setup/cleanup helpers
# ---------------------------------------------------------------------------

async def _create_umbral_context(db_session, monkeypatch):
    """
    Create a tenant, materia, and two users with asignaciones for umbral tests.
    Returns a dict with all the created objects.
    """
    from app.core.security.passwords import email_lookup_hash
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    # Ensure session is in clean state
    try:
        await db_session.rollback()
    except Exception:
        pass

    # Tenant
    tenant = Tenant(nombre=f"Umbral Tenant {uuid.uuid4().hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    # Materia
    materia = Materia(
        tenant_id=tenant.id,
        nombre="Matemáticas Test",
        codigo=f"MAT-{uuid.uuid4().hex[:6]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)

    # Usuario A
    email_a = f"profa-{uuid.uuid4().hex[:8]}@umbral.test"
    usuario_a = Usuario(
        tenant_id=tenant.id,
        email_encrypted=email_a,
        email_hash=email_lookup_hash(email_a),
        nombre="Profesora A",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    db_session.add(usuario_a)
    await db_session.commit()
    await db_session.refresh(usuario_a)

    # Asignacion A
    asignacion_a = Asignacion(
        tenant_id=tenant.id,
        usuario_id=usuario_a.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia.id,
        desde=date(2026, 1, 1),
    )
    db_session.add(asignacion_a)
    await db_session.commit()
    await db_session.refresh(asignacion_a)

    # Usuario B
    email_b = f"profb-{uuid.uuid4().hex[:8]}@umbral.test"
    usuario_b = Usuario(
        tenant_id=tenant.id,
        email_encrypted=email_b,
        email_hash=email_lookup_hash(email_b),
        nombre="Profesor B",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    db_session.add(usuario_b)
    await db_session.commit()
    await db_session.refresh(usuario_b)

    # Asignacion B
    asignacion_b = Asignacion(
        tenant_id=tenant.id,
        usuario_id=usuario_b.id,
        rol=RolAsignacion.PROFESOR,
        materia_id=materia.id,
        desde=date(2026, 1, 1),
    )
    db_session.add(asignacion_b)
    await db_session.commit()
    await db_session.refresh(asignacion_b)

    return {
        "tenant": tenant,
        "materia": materia,
        "usuario_a": usuario_a,
        "asignacion_a": asignacion_a,
        "usuario_b": usuario_b,
        "asignacion_b": asignacion_b,
    }


async def _cleanup_umbral(db_session, tenant_id: uuid.UUID):
    """Clean up all test data for a tenant (follow FK order)."""
    tid = str(tenant_id)
    # umbral_materia → calificacion → asignacion → materia → usuario → tenant
    await db_session.execute(text("DELETE FROM umbral_materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM calificacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM asignacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid})
    await db_session.commit()


# ---------------------------------------------------------------------------
# §8.1 / §8.2 — get_efectivo returns default when no UmbralMateria exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_efectivo_returns_default_when_none(db_session, create_tables, monkeypatch):
    """No UmbralMateria → returns default umbral_pct=60 and default valores."""
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    asignacion_a = ctx["asignacion_a"]
    materia = ctx["materia"]

    try:
        repo = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        svc = UmbralService(repo=repo)

        result = await svc.get_efectivo(
            asignacion_id=asignacion_a.id,
            materia_id=materia.id,
        )

        assert isinstance(result, UmbralMateriaRead)
        assert result.umbral_pct == 60
        assert "Satisfactorio" in result.valores_aprobatorios
        assert result.is_default is True
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §8.3 / §8.4 — configurar creates UmbralMateria for the asignacion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_configurar_creates_umbral_for_asignacion(db_session, create_tables, monkeypatch):
    """PROFESOR sets umbral_pct=70 → UmbralMateria created with asignacion_id resolved."""
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    asignacion_a = ctx["asignacion_a"]
    materia = ctx["materia"]
    usuario_a = ctx["usuario_a"]

    try:
        repo = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        svc = UmbralService(repo=repo)
        current_user = _make_current_user(usuario_a.id, tenant.id)

        result = await svc.configurar(
            materia_id=materia.id,
            umbral_pct=70,
            valores_aprobatorios=["Satisfactorio"],
            current_user=current_user,
        )

        assert isinstance(result, UmbralMateriaRead)
        assert result.umbral_pct == 70
        assert result.asignacion_id == asignacion_a.id
        assert result.is_default is False

        # get_efectivo should now return 70, not the default
        result2 = await svc.get_efectivo(
            asignacion_id=asignacion_a.id,
            materia_id=materia.id,
        )
        assert result2.umbral_pct == 70
        assert result2.is_default is False
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §8.5 — Threshold of one docente does not affect another
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_threshold_one_docente_does_not_affect_another(db_session, create_tables, monkeypatch):
    """A=80, B=50 same materia → independent records, get_efectivo per asignacion distinct."""
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    asignacion_a = ctx["asignacion_a"]
    asignacion_b = ctx["asignacion_b"]
    materia = ctx["materia"]
    usuario_a = ctx["usuario_a"]
    usuario_b = ctx["usuario_b"]

    try:
        repo = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        svc = UmbralService(repo=repo)

        # A sets 80
        await svc.configurar(
            materia_id=materia.id,
            umbral_pct=80,
            valores_aprobatorios=["Supera lo esperado"],
            current_user=_make_current_user(usuario_a.id, tenant.id),
        )
        # B sets 50
        await svc.configurar(
            materia_id=materia.id,
            umbral_pct=50,
            valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
            current_user=_make_current_user(usuario_b.id, tenant.id),
        )

        result_a = await svc.get_efectivo(
            asignacion_id=asignacion_a.id,
            materia_id=materia.id,
        )
        result_b = await svc.get_efectivo(
            asignacion_id=asignacion_b.id,
            materia_id=materia.id,
        )

        assert result_a.umbral_pct == 80
        assert result_b.umbral_pct == 50
        assert result_a.asignacion_id != result_b.asignacion_id
    finally:
        await _cleanup_umbral(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §8.6 — Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_umbral_tenant_isolation(db_session, create_tables, monkeypatch):
    """T1's UmbralMateria is not visible when scoped to a different T2 tenant_id."""
    ctx = await _create_umbral_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    asignacion_a = ctx["asignacion_a"]
    materia = ctx["materia"]
    usuario_a = ctx["usuario_a"]

    try:
        # Set umbral for T1
        repo_t1 = CalificacionRepository(session=db_session, tenant_id=tenant.id)
        svc_t1 = UmbralService(repo=repo_t1)
        await svc_t1.configurar(
            materia_id=materia.id,
            umbral_pct=75,
            valores_aprobatorios=["Satisfactorio"],
            current_user=_make_current_user(usuario_a.id, tenant.id),
        )

        # Scope to T2 (random UUID) → should return default because records belong to T1
        other_tenant_id = uuid.uuid4()
        repo_t2 = CalificacionRepository(session=db_session, tenant_id=other_tenant_id)
        svc_t2 = UmbralService(repo=repo_t2)

        result = await svc_t2.get_efectivo(
            asignacion_id=asignacion_a.id,
            materia_id=materia.id,
        )

        # Should fall back to default — T1's UmbralMateria is not visible in T2 scope
        assert result.is_default is True
        assert result.umbral_pct == 60
    finally:
        await _cleanup_umbral(db_session, tenant.id)
