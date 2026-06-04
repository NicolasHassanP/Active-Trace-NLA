"""
TDD tests for CalificacionService.detectar_sin_corregir (F1.2, RN-07/RN-08).

C-10 Design:
    - Only textual activities are checked (RN-08).
    - Numeric activities completed-without-grade are NOT reported.
    - Textual with existing nota_textual is NOT reported.
    - Textual completed-without-grade IS reported as EntregaSinCorregir.
"""
import csv
import io
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from app.core.dependencies import CurrentUser
from app.models.tenant import Tenant, TenantEstado
from app.models.estructura import Materia, Cohorte, EstadoEstructura, Carrera
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.padron import VersionPadron, EntradaPadron
from app.models.calificacion import Calificacion, CalificacionOrigen
from app.schemas.calificacion import ReporteFinalizacionRequest


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


async def _create_fin_context(db_session, monkeypatch):
    """Create a minimal context for finalizacion tests."""
    from app.core.security.passwords import email_lookup_hash
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    # Ensure session is in clean state before creating new context
    try:
        await db_session.rollback()
    except Exception:
        pass

    tenant = Tenant(nombre=f"Fin Tenant {uuid.uuid4().hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    carrera = Carrera(
        tenant_id=tenant.id,
        nombre="Ingeniería Fin",
        codigo=f"INGFIN-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera)
    await db_session.commit()
    await db_session.refresh(carrera)

    cohorte = Cohorte(
        tenant_id=tenant.id,
        nombre="Cohorte Fin 2026",
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
        nombre="Historia Fin",
        codigo=f"HIST-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)

    email_prof = f"profin-{uuid.uuid4().hex[:8]}@fin.test"
    profesor = Usuario(
        tenant_id=tenant.id,
        email_encrypted=email_prof,
        email_hash=email_lookup_hash(email_prof),
        nombre="Prof Fin",
        apellidos="Test",
        estado=UsuarioEstado.activo,
    )
    db_session.add(profesor)
    await db_session.commit()
    await db_session.refresh(profesor)

    version = VersionPadron(
        tenant_id=tenant.id,
        materia_id=materia.id,
        cohorte_id=cohorte.id,
        cargado_por=profesor.id,
        activa=True,
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)

    email_a = f"alumno-a-fin-{uuid.uuid4().hex[:8]}@alumnos.test"
    entry_a = EntradaPadron(
        tenant_id=tenant.id,
        version_id=version.id,
        nombre="Alumno A Fin",
        apellidos="Test",
        email_encrypted=email_a,
    )
    db_session.add(entry_a)
    await db_session.commit()
    await db_session.refresh(entry_a)

    return {
        "tenant": tenant, "cohorte": cohorte, "materia": materia,
        "profesor": profesor, "version": version, "entry_a": entry_a,
        "email_a": email_a,
    }


async def _cleanup_fin(db_session, tenant_id: uuid.UUID):
    tid = str(tenant_id)
    await db_session.execute(text("DELETE FROM calificacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM umbral_materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM entrada_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM version_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM asignacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM cohorte WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM carrera WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tid})
    await db_session.commit()


def _make_fin_service(db_session, tenant_id):
    from app.repositories.calificacion_repository import CalificacionRepository
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.calificacion_service import CalificacionService
    repo = CalificacionRepository(session=db_session, tenant_id=tenant_id)
    padron_repo = PadronRepository(session=db_session, tenant_id=tenant_id)
    audit_repo = AuditRepository(session=db_session, tenant_id=tenant_id)
    return CalificacionService(repo=repo, padron_repo=padron_repo, audit_repo=audit_repo)


# ---------------------------------------------------------------------------
# §10.1 / §10.2 — Completed textual without grade is reported
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_completed_textual_without_grade_is_reported(db_session, create_tables, monkeypatch):
    """Completion marks textual activity done, no Calificacion → reported as ungraded."""
    ctx = await _create_fin_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    cohorte = ctx["cohorte"]
    materia = ctx["materia"]
    profesor = ctx["profesor"]
    entry_a = ctx["entry_a"]
    email_a = ctx["email_a"]

    try:
        svc = _make_fin_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        req = ReporteFinalizacionRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            filas_finalizacion=[
                {
                    "email": email_a,
                    "actividad": "TP 1",
                    "completado": True,
                    "escala": "textual",
                }
            ],
        )
        result = await svc.detectar_sin_corregir(req=req, current_user=current_user)

        assert len(result) == 1
        assert result[0].entrada_padron_id == entry_a.id
        assert result[0].actividad == "TP 1"
    finally:
        await _cleanup_fin(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §10.3 — Numeric activity excluded from ungraded (RN-08)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_numeric_activity_excluded_from_ungraded(db_session, create_tables, monkeypatch):
    """Numeric completed-without-grade is NOT reported (RN-08)."""
    ctx = await _create_fin_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    cohorte = ctx["cohorte"]
    materia = ctx["materia"]
    profesor = ctx["profesor"]
    email_a = ctx["email_a"]

    try:
        svc = _make_fin_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        req = ReporteFinalizacionRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            filas_finalizacion=[
                {
                    "email": email_a,
                    "actividad": "Tarea 1",
                    "completado": True,
                    "escala": "numerica",  # numeric → excluded
                }
            ],
        )
        result = await svc.detectar_sin_corregir(req=req, current_user=current_user)

        # Numeric activity NOT reported
        assert len(result) == 0
    finally:
        await _cleanup_fin(db_session, tenant.id)


# ---------------------------------------------------------------------------
# §10.4 — Textual with existing grade is NOT reported
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_textual_with_existing_grade_not_reported(db_session, create_tables, monkeypatch):
    """Textual completed with existing nota_textual → NOT reported as ungraded."""
    ctx = await _create_fin_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    cohorte = ctx["cohorte"]
    materia = ctx["materia"]
    profesor = ctx["profesor"]
    entry_a = ctx["entry_a"]
    email_a = ctx["email_a"]

    try:
        # Insert an existing Calificacion with nota_textual
        from datetime import datetime, timezone
        cal = Calificacion(
            tenant_id=tenant.id,
            entrada_padron_id=entry_a.id,
            materia_id=materia.id,
            importado_por=profesor.id,
            actividad="TP 1",
            nota_textual="Satisfactorio",
            aprobado=True,
            origen=CalificacionOrigen.Importado,
            importado_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(cal)
        await db_session.commit()

        svc = _make_fin_service(db_session, tenant.id)
        current_user = _make_current_user(profesor.id, tenant.id)

        req = ReporteFinalizacionRequest(
            materia_id=materia.id,
            cohorte_id=cohorte.id,
            filas_finalizacion=[
                {
                    "email": email_a,
                    "actividad": "TP 1",
                    "completado": True,
                    "escala": "textual",
                }
            ],
        )
        result = await svc.detectar_sin_corregir(req=req, current_user=current_user)

        # Already has a grade → NOT reported
        assert len(result) == 0
    finally:
        await _cleanup_fin(db_session, tenant.id)
