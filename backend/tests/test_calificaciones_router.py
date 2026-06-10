"""
Integration tests for /api/v1/calificaciones router (tasks 12.1-12.6).

Uses the shared async_client fixture from conftest.
Follows the same pattern as test_padron.py tasks 12.x.
"""
import csv
import io
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from app.models.tenant import Tenant, TenantEstado
from app.models.estructura import Carrera, Cohorte, EstadoEstructura, Materia
from app.models.usuario import Asignacion, RolAsignacion, Usuario, UsuarioEstado
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.padron import VersionPadron, EntradaPadron


# ---------------------------------------------------------------------------
# JWT helpers
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


def _make_csv_bytes(headers, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


_IDENTITY = ["Nombre", "Apellido(s)", "Dirección de correo"]
_ESCALA_TEXTUAL = ["Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado"]


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

async def _create_router_context(db_session, monkeypatch):
    """Create tenant with calificaciones permissions, usuarios, and active padron."""
    from app.core.security.passwords import email_lookup_hash
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    # Ensure session is in clean state
    try:
        await db_session.rollback()
    except Exception:
        pass

    tenant = Tenant(nombre=f"Cal Router Tenant {uuid.uuid4().hex[:8]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    # Roles
    for rol_nombre in ("PROFESOR", "COORDINADOR", "ADMIN", "FINANZAS"):
        db_session.add(Rol(tenant_id=tenant.id, nombre=rol_nombre))
    await db_session.commit()

    from sqlalchemy import select as sqla_select
    from app.models.rbac import Rol as RolModel
    result = await db_session.execute(
        sqla_select(RolModel).where(RolModel.tenant_id == tenant.id)
    )
    roles = {r.nombre: r for r in result.scalars().all()}

    # Permisos
    perm_importar = Permiso(
        tenant_id=tenant.id,
        codigo="calificaciones:importar",
        modulo="calificaciones",
        accion="importar",
    )
    perm_umbral = Permiso(
        tenant_id=tenant.id,
        codigo="calificaciones:configurar-umbral",
        modulo="calificaciones",
        accion="configurar-umbral",
    )
    db_session.add(perm_importar)
    db_session.add(perm_umbral)
    await db_session.commit()
    await db_session.refresh(perm_importar)
    await db_session.refresh(perm_umbral)

    # Grants
    for rol_name in ("PROFESOR", "COORDINADOR", "ADMIN"):
        db_session.add(RolPermiso(
            tenant_id=tenant.id,
            rol_id=roles[rol_name].id,
            permiso_id=perm_importar.id,
            scope=PermisoScope.global_,
        ))
        db_session.add(RolPermiso(
            tenant_id=tenant.id,
            rol_id=roles[rol_name].id,
            permiso_id=perm_umbral.id,
            scope=PermisoScope.global_,
        ))
    await db_session.commit()

    # Academic structure
    carrera = Carrera(
        tenant_id=tenant.id,
        nombre="Ingeniería Router",
        codigo=f"INGR-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(carrera)
    await db_session.commit()
    await db_session.refresh(carrera)

    cohorte = Cohorte(
        tenant_id=tenant.id,
        nombre="Cohorte Router 2026",
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
        nombre="Algebra Router",
        codigo=f"ALR-{uuid.uuid4().hex[:4]}",
        estado=EstadoEstructura.activa,
    )
    db_session.add(materia)
    await db_session.commit()
    await db_session.refresh(materia)

    # PROFESOR usuario — C-28: create with real AuthIdentity so auth_identity_id ≠ usuario.id
    # Use create_usuario_con_identidad so resolve_domain_user_id and _resolve_asignacion
    # can look up the Usuario via auth_identity_id from the JWT sub.
    from tests.conftest import create_usuario_con_identidad
    email_prof = f"profr-{uuid.uuid4().hex[:8]}@router.test"
    profesor = await create_usuario_con_identidad(
        db_session, tenant.id,
        email=email_prof,
        nombre="Prof Router",
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

    # Active padron
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

    email_alum = f"alum-{uuid.uuid4().hex[:8]}@alumnos.test"
    entry = EntradaPadron(
        tenant_id=tenant.id,
        version_id=version.id,
        nombre="Alumno Router",
        apellidos="Test",
        email_encrypted=email_alum,
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    return {
        "tenant": tenant, "roles": roles, "perm_importar": perm_importar,
        "perm_umbral": perm_umbral, "cohorte": cohorte, "materia": materia,
        "profesor": profesor, "asignacion": asignacion, "version": version,
        "entry": entry, "email_alum": email_alum,
    }


async def _cleanup_router(db_session, tenant_id: uuid.UUID):
    from tests.conftest import delete_audit_events_for_tenant
    await delete_audit_events_for_tenant(db_session, tenant_id)
    tid = str(tenant_id)
    await db_session.execute(text("DELETE FROM calificacion WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM umbral_materia WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM entrada_padron WHERE tenant_id = :tid"), {"tid": tid})
    await db_session.execute(text("DELETE FROM version_padron WHERE tenant_id = :tid"), {"tid": tid})
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


# ---------------------------------------------------------------------------
# 12.1 — preview endpoint unauthenticated → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_endpoint_unauthenticated_returns_401(async_client, db_session, monkeypatch):
    """Task 12.1: preview without auth → 401."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    file_bytes = _make_csv_bytes(["Nombre", "Apellido(s)", "Dirección de correo", "Tarea 1 (Real)"], [])
    resp = await async_client.post(
        "/api/v1/calificaciones/preview",
        files={"file": ("notas.csv", file_bytes, "text/csv")},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 12.2 — preview endpoint unauthorized (missing calificaciones:importar) → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_endpoint_unauthorized_returns_403(async_client, db_session, monkeypatch):
    """Task 12.2: preview with role that has no calificaciones:importar → 403."""
    ctx = await _create_router_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    try:
        # FINANZAS has no calificaciones:importar
        finanzas_user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, finanzas_user_id, ["FINANZAS"])

        file_bytes = _make_csv_bytes(["Nombre", "Apellido(s)", "Dirección de correo", "Tarea 1 (Real)"], [])
        resp = await async_client.post(
            "/api/v1/calificaciones/preview",
            files={"file": ("notas.csv", file_bytes, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup_router(db_session, tenant.id)


# ---------------------------------------------------------------------------
# 12.3 — preview endpoint with valid file → 200 + activities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_preview_endpoint_valid_file_returns_activities(async_client, db_session, monkeypatch):
    """Task 12.3: valid file with (Real) column → 200 + activities detected."""
    ctx = await _create_router_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    try:
        token = _make_jwt(tenant.id, profesor.id, ["PROFESOR"])
        headers_csv = _IDENTITY + ["Tarea 1 (Real)", "TP 1"]
        rows = [
            ["Alumno Router", "Test", ctx["email_alum"], "8", "Satisfactorio"],
        ]
        file_bytes = _make_csv_bytes(headers_csv, rows)

        resp = await async_client.post(
            "/api/v1/calificaciones/preview",
            files={"file": ("notas.csv", file_bytes, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        activity_names = [a["actividad"] for a in data["actividades"]]
        assert "Tarea 1" in activity_names
        assert "TP 1" in activity_names
    finally:
        await _cleanup_router(db_session, tenant.id)


# ---------------------------------------------------------------------------
# 12.4 — importar endpoint creates calificaciones for selected activities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_importar_endpoint_creates_calificaciones_for_selected(async_client, db_session, monkeypatch):
    """Task 12.4: importar with valid payload → 201 + list of CalificacionRead."""
    ctx = await _create_router_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    email_alum = ctx["email_alum"]
    try:
        # C-28: JWT sub must be auth_identity_id so resolve_domain_user_id finds the domain user
        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])

        # Build preview filas (simulate what preview returns)
        headers_csv = _IDENTITY + ["Tarea 1 (Real)"]
        rows = [["Alumno Router", "Test", email_alum, "8"]]
        file_bytes = _make_csv_bytes(headers_csv, rows)

        preview_resp = await async_client.post(
            "/api/v1/calificaciones/preview",
            files={"file": ("notas.csv", file_bytes, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert preview_resp.status_code == 200
        preview_data = preview_resp.json()

        # Importar with selected activities
        importar_payload = {
            "materia_id": str(materia.id),
            "cohorte_id": str(cohorte.id),
            "actividades_seleccionadas": ["Tarea 1"],
            "filas": preview_data["filas"],
        }
        resp = await async_client.post(
            "/api/v1/calificaciones/importar",
            json=importar_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 1
        assert data[0]["actividad"] == "Tarea 1"
    finally:
        await _cleanup_router(db_session, tenant.id)


# ---------------------------------------------------------------------------
# 12.5 — umbral PUT creates umbral + GET unauthorized returns 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_umbral_put_endpoint_creates_umbral(async_client, db_session, monkeypatch):
    """Task 12.5a: PUT /umbral with valid payload → 200 + UmbralMateriaRead."""
    ctx = await _create_router_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    materia = ctx["materia"]
    try:
        # C-28: JWT sub must be auth_identity_id so _resolve_asignacion joins correctly
        token = _make_jwt(tenant.id, profesor.auth_identity_id, ["PROFESOR"])
        payload = {
            "materia_id": str(materia.id),
            "umbral_pct": 70,
            "valores_aprobatorios": ["Satisfactorio", "Supera lo esperado"],
        }
        resp = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["umbral_pct"] == 70
        assert data["is_default"] is False
    finally:
        await _cleanup_router(db_session, tenant.id)


@pytest.mark.asyncio
async def test_umbral_put_unauthorized_returns_403(async_client, db_session, monkeypatch):
    """Task 12.5b: PUT /umbral without calificaciones:configurar-umbral → 403."""
    ctx = await _create_router_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    materia = ctx["materia"]
    try:
        # FINANZAS has no calificaciones:configurar-umbral
        finanzas_user_id = uuid.uuid4()
        token = _make_jwt(tenant.id, finanzas_user_id, ["FINANZAS"])
        payload = {
            "materia_id": str(materia.id),
            "umbral_pct": 70,
            "valores_aprobatorios": ["Satisfactorio"],
        }
        resp = await async_client.put(
            "/api/v1/calificaciones/umbral",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
    finally:
        await _cleanup_router(db_session, tenant.id)


# ---------------------------------------------------------------------------
# 12.6 — finalizacion endpoint reports textual only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_finalizacion_endpoint_reports_textual_only(async_client, db_session, monkeypatch):
    """Task 12.6: POST /finalizacion with textual completed + numeric → only textual reported."""
    ctx = await _create_router_context(db_session, monkeypatch)
    tenant = ctx["tenant"]
    profesor = ctx["profesor"]
    materia = ctx["materia"]
    cohorte = ctx["cohorte"]
    email_alum = ctx["email_alum"]
    try:
        token = _make_jwt(tenant.id, profesor.id, ["PROFESOR"])
        payload = {
            "materia_id": str(materia.id),
            "cohorte_id": str(cohorte.id),
            "filas_finalizacion": [
                {
                    "email": email_alum,
                    "actividad": "TP 1",
                    "completado": True,
                    "escala": "textual",  # Should be reported (no grade)
                },
                {
                    "email": email_alum,
                    "actividad": "Tarea 1",
                    "completado": True,
                    "escala": "numerica",  # Should NOT be reported
                },
            ],
        }
        resp = await async_client.post(
            "/api/v1/calificaciones/finalizacion",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only the textual activity reported
        assert len(data) == 1
        assert data[0]["actividad"] == "TP 1"
    finally:
        await _cleanup_router(db_session, tenant.id)
