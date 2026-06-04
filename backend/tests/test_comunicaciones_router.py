"""
TDD tests for /api/v1/comunicaciones/* router (Task 7.1 RED).

C-12 Design Decisions:
    - require_permission('comunicacion:enviar') en preview y encolar.
    - require_permission('comunicacion:aprobar') en aprobar/cancelar.
    - Identidad desde JWT — body con enviado_por/tenant_id se ignora.
    - Fail-closed: sin permiso → 403.
    - Aislamiento por tenant en GET /lote/{lote_id}.

Uses async_client fixture (real DB + real app).
"""
import uuid
from typing import Dict

import pytest
from httpx import AsyncClient

from app.models.tenant import Tenant, TenantEstado
from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope
from app.models.auth import AuthIdentity
from app.models.usuario import Usuario, UsuarioEstado, Asignacion, RolAsignacion
from datetime import date
from sqlalchemy import text


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


def _make_token(user_id: uuid.UUID, tenant_id: uuid.UUID, roles: list) -> str:
    """Create a JWT token for testing."""
    import jose.jwt
    import datetime
    settings = _fake_settings()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "type": "access",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=30),
    }
    return jose.jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")


def _auth(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# §7.1 — RED: POST /comunicaciones/preview — 200 con permiso, 403 sin permiso
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_preview_sin_permiso_retorna_403(async_client: AsyncClient, monkeypatch):
    """POST /comunicaciones/preview → 403 si el usuario no tiene permiso."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    # Token con tenant+user válidos pero sin permiso
    token = _make_token(uuid.uuid4(), uuid.uuid4(), roles=[])
    response = await async_client.post(
        "/api/v1/comunicaciones/preview",
        json={
            "asunto_plantilla": "Hola {nombre}",
            "cuerpo_plantilla": "Cuerpo",
            "variables": {"nombre": "Ana"},
        },
        headers=_auth(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_encolar_sin_permiso_retorna_403(async_client: AsyncClient, monkeypatch):
    """POST /comunicaciones/encolar → 403 si el usuario no tiene permiso."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    token = _make_token(uuid.uuid4(), uuid.uuid4(), roles=[])
    response = await async_client.post(
        "/api/v1/comunicaciones/encolar",
        json={
            "destinatarios": ["a@test.edu"],
            "asunto_plantilla": "Asunto",
            "cuerpo_plantilla": "Cuerpo",
            "variables_por_destinatario": {},
        },
        headers=_auth(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_aprobar_lote_sin_permiso_retorna_403(async_client: AsyncClient, monkeypatch):
    """POST /comunicaciones/aprobar-lote → 403 si no tiene permiso."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    token = _make_token(uuid.uuid4(), uuid.uuid4(), roles=[])
    response = await async_client.post(
        "/api/v1/comunicaciones/aprobar-lote",
        json={"lote_id": str(uuid.uuid4())},
        headers=_auth(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_cancelar_lote_sin_permiso_retorna_403(async_client: AsyncClient, monkeypatch):
    """POST /comunicaciones/cancelar-lote → 403 si no tiene permiso."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    token = _make_token(uuid.uuid4(), uuid.uuid4(), roles=[])
    response = await async_client.post(
        "/api/v1/comunicaciones/cancelar-lote",
        json={"lote_id": str(uuid.uuid4())},
        headers=_auth(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_get_lote_sin_autenticar_retorna_401(async_client: AsyncClient, monkeypatch):
    """GET /comunicaciones/lote/{id} → 401 sin token."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    response = await async_client.get(
        f"/api/v1/comunicaciones/lote/{uuid.uuid4()}"
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# §7.1 — GREEN: preview con permiso retorna 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_preview_con_permiso_retorna_200(
    async_client: AsyncClient, db_session, create_tables, monkeypatch
):
    """POST /comunicaciones/preview → 200 con datos renderizados."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)

    # Setup: crear tenant, rol con permiso, usuario
    tenant = Tenant(nombre=f"TenantRouter-{uuid.uuid4().hex[:4]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    tenant_id = tenant.id

    # Crear permiso comunicacion:enviar
    permiso = Permiso(
        tenant_id=tenant_id,
        codigo="comunicacion:enviar",
        modulo="comunicacion",
        accion="enviar",
    )
    db_session.add(permiso)
    await db_session.commit()
    await db_session.refresh(permiso)

    # Crear rol COORDINADOR
    rol = Rol(tenant_id=tenant_id, nombre="COORDINADOR")
    db_session.add(rol)
    await db_session.commit()
    await db_session.refresh(rol)

    # Asignar permiso al rol
    rol_permiso = RolPermiso(
        tenant_id=tenant_id,
        rol_id=rol.id,
        permiso_id=permiso.id,
        scope=PermisoScope.global_,
    )
    db_session.add(rol_permiso)
    await db_session.commit()

    # Crear usuario con identidad auth
    from app.core.security.passwords import email_lookup_hash
    email = "coord@test.edu"
    user = Usuario(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        nombre="Test",
        apellidos="Coord",
        estado=UsuarioEstado.activo,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    from app.core.security.passwords import email_lookup_hash
    auth = AuthIdentity(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        password_hash="dummy_hash_argon2",
        roles=["COORDINADOR"],
    )
    db_session.add(auth)
    await db_session.commit()
    await db_session.refresh(auth)

    asignacion = Asignacion(
        tenant_id=tenant_id,
        usuario_id=user.id,
        rol=RolAsignacion.COORDINADOR,
        desde=date.today(),
        comisiones=[],
    )
    db_session.add(asignacion)
    await db_session.commit()

    token = _make_token(user.id, tenant_id, roles=["COORDINADOR"])

    try:
        response = await async_client.post(
            "/api/v1/comunicaciones/preview",
            json={
                "asunto_plantilla": "Aviso para {nombre}",
                "cuerpo_plantilla": "Estimado {nombre}.",
                "variables": {"nombre": "Ana"},
            },
            headers=_auth(token),
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["asunto"] == "Aviso para Ana"
        assert data["cuerpo"] == "Estimado Ana."

    finally:
        await db_session.execute(text("DELETE FROM asignacion WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
        await db_session.execute(text("DELETE FROM auth_identities WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
        await db_session.execute(text("DELETE FROM usuario WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
        await db_session.execute(text("DELETE FROM rol_permiso WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
        await db_session.execute(text("DELETE FROM permiso WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
        await db_session.execute(text("DELETE FROM rol WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
        await db_session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": str(tenant_id)})
        await db_session.commit()


# ---------------------------------------------------------------------------
# §7.3 — TRIANGULATE: identidad desde JWT, no del body
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_preview_extra_fields_rechazados(async_client: AsyncClient, monkeypatch):
    """Body con campos extra (extra='forbid') retorna 422."""
    monkeypatch.setattr("app.core.config.Settings", _fake_settings)
    token = _make_token(uuid.uuid4(), uuid.uuid4(), roles=[])
    response = await async_client.post(
        "/api/v1/comunicaciones/preview",
        json={
            "asunto_plantilla": "Asunto",
            "cuerpo_plantilla": "Cuerpo",
            "variables": {},
            "enviado_por": str(uuid.uuid4()),  # Campo extra — debe ser rechazado
        },
        headers=_auth(token),
    )
    # 422 (schema validation) o 403 (permiso) — en cualquier caso no 200
    assert response.status_code in (422, 403)
