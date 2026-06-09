"""
test_perfil_router.py — TDD e2e suite para C-20 router de perfil.

Task 5.1 RED: GET /api/v1/perfil → 401 sin JWT, 200 con JWT.
Task 5.3 RED: PATCH /api/v1/perfil → 403 sin permiso, 422 campo prohibido,
              409 email duplicado, 200 happy path.
Task 5.5 TRIANGULATE: intento de editar con id en body ignorado; cuil → 422.
"""
import datetime
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import build_session_factory
from app.models.rbac import Permiso, Rol, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.models.usuario import Usuario, UsuarioEstado
from tests.conftest import create_usuario_con_identidad

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(tenant_id: uuid.UUID, user_id: uuid.UUID, roles: list) -> str:
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


@pytest_asyncio.fixture(scope="module")
async def perfil_router_data(test_engine, create_tables):
    """Crea tenant + usuarios con RBAC para tests e2e del router de perfil."""
    import app.models  # noqa
    import app.core.config as config_mod
    from sqlalchemy import text
    from app.core.security.passwords import email_lookup_hash

    # Patch settings BEFORE creating any encrypted data so keys match
    _original_settings = config_mod.Settings

    class PatchedSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test"
        MOODLE_BASE_URL = None
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"

    config_mod.Settings = PatchedSettings

    factory = build_session_factory(test_engine)
    session = factory()

    await session.execute(text("ALTER TABLE usuario ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"))
    await session.commit()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"Perfil Router {tid}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Rol con perfil:editar
    rol_con_perm = Rol(tenant_id=tid, nombre=f"ADMIN_PERFIL_{tid}")
    # Rol sin perfil:editar
    rol_sin_perm = Rol(tenant_id=tid, nombre=f"ROL_NOPERM_{tid}")
    session.add_all([rol_con_perm, rol_sin_perm])
    await session.flush()

    perm_perfil = Permiso(
        tenant_id=tid,
        codigo="perfil:editar",
        modulo="perfil",
        accion="editar",
    )
    session.add(perm_perfil)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid,
        rol_id=rol_con_perm.id,
        permiso_id=perm_perfil.id,
        scope=PermisoScope.global_,
    ))
    await session.flush()

    # C-28: use canonical helper — creates AuthIdentity + Usuario with auth_identity_id != usuario.id.
    # JWT sub = usuario.auth_identity_id (NOT usuario.id).
    email_con_perm = f"con_perm_{tid}@test.com"
    email_sin_perm = f"sin_perm_{tid}@test.com"
    email_otro = f"otro_{tid}@test.com"

    u_con_perm = await create_usuario_con_identidad(
        session, tid,
        email=email_con_perm,
        nombre="Con",
        apellidos="Permiso",
    )
    u_sin_perm = await create_usuario_con_identidad(
        session, tid,
        email=email_sin_perm,
        nombre="Sin",
        apellidos="Permiso",
    )
    # Usuario extra para test de email duplicado (no necesita autenticarse → sin AuthIdentity)
    u_otro = Usuario(
        tenant_id=tid,
        email_encrypted=email_otro,
        email_hash=email_lookup_hash(email_otro),
        nombre="Otro",
        apellidos="Usuario",
        estado=UsuarioEstado.activo,
    )
    session.add(u_otro)
    await session.commit()

    yield {
        "tid": tid,
        "uid_con_perm": u_con_perm.id,
        "uid_sin_perm": u_sin_perm.id,
        "auth_con_perm": u_con_perm.auth_identity_id,
        "auth_sin_perm": u_sin_perm.auth_identity_id,
        "rol_con_perm": rol_con_perm.nombre,
        "rol_sin_perm": rol_sin_perm.nombre,
        "email_con_perm": email_con_perm,
        "email_sin_perm": email_sin_perm,
        "email_otro": email_otro,
    }

    # Cleanup
    from sqlalchemy import delete
    from app.models.audit import AuditEvent
    from app.models.auth import AuthIdentity
    await session.execute(delete(AuditEvent).where(AuditEvent.tenant_id == tid))
    await session.execute(delete(RolPermiso).where(RolPermiso.tenant_id == tid))
    await session.execute(delete(Permiso).where(Permiso.tenant_id == tid))
    await session.execute(delete(Rol).where(Rol.tenant_id == tid))
    await session.execute(delete(Usuario).where(Usuario.tenant_id == tid))
    # C-28: delete auth_identities created by create_usuario_con_identidad
    await session.execute(delete(AuthIdentity).where(AuthIdentity.tenant_id == tid))
    await session.execute(delete(Tenant).where(Tenant.id == tid))
    await session.commit()
    await session.close()

    # Restore settings
    config_mod.Settings = _original_settings


@pytest_asyncio.fixture(scope="module")
def perfil_router_app(test_engine, perfil_router_data):
    """FastAPI app con settings parcheadas para tests de perfil router."""
    import os
    import app.core.config as config_mod

    # Patch Settings class so JWT decode uses the same key as JWT generation
    _original_settings = config_mod.Settings

    class PatchedSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        DATABASE_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
        )
        MOODLE_BASE_URL = None
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"

    config_mod.Settings = PatchedSettings

    from app.main import create_app
    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory

    yield app

    config_mod.Settings = _original_settings


@pytest_asyncio.fixture(scope="module")
async def perfil_client(perfil_router_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=perfil_router_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Task 5.1 RED — GET /api/v1/perfil
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_perfil_sin_jwt_retorna_401(perfil_client):
    """RED: GET /api/v1/perfil sin JWT → 401."""
    resp = await perfil_client.get("/api/v1/perfil")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_perfil_con_jwt_retorna_200_perfil_titular(perfil_client, perfil_router_data):
    """RED: GET /api/v1/perfil con JWT → 200 y devuelve perfil del titular del JWT."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.get(
        "/api/v1/perfil",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(data["uid_con_perm"])


@pytest.mark.asyncio
async def test_get_perfil_ignora_usuario_id_en_query(perfil_client, perfil_router_data):
    """RED: GET /api/v1/perfil ignora ?usuario_id= y devuelve perfil del titular."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.get(
        f"/api/v1/perfil?usuario_id={data['uid_sin_perm']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(data["uid_con_perm"])


# ---------------------------------------------------------------------------
# Task 5.3 RED — PATCH /api/v1/perfil
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_perfil_sin_permiso_retorna_403(perfil_client, perfil_router_data):
    """RED: PATCH /api/v1/perfil sin permil:editar → 403."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_sin_perm"], [data["rol_sin_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"banco": "Nuevo Banco"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_patch_perfil_campo_prohibido_retorna_422(perfil_client, perfil_router_data):
    """RED: PATCH /api/v1/perfil con campo no declarado (tenant_id) → 422."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"tenant_id": str(data["tid"])},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_perfil_cuil_retorna_422(perfil_client, perfil_router_data):
    """RED: PATCH /api/v1/perfil con cuil → 422 (extra='forbid')."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"cuil": "20-12345678-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_perfil_email_duplicado_retorna_409(perfil_client, perfil_router_data):
    """RED: PATCH /api/v1/perfil con email ya usado → 409."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"email": data["email_otro"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_patch_perfil_happy_path_retorna_200(perfil_client, perfil_router_data):
    """RED: PATCH /api/v1/perfil happy path → 200 con datos actualizados."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"banco": "Banco Nacional", "regional": "Norte"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["banco"] == "Banco Nacional"
    assert body["regional"] == "Norte"


# ---------------------------------------------------------------------------
# Task 5.5 TRIANGULATE — anti-spoofing y cuil=422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_perfil_id_en_body_es_ignorado(perfil_client, perfil_router_data):
    """TRIANGULATE: PATCH con id en body → ignorado (extra='forbid' lo rechaza)."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"id": str(data["uid_sin_perm"])},
        headers={"Authorization": f"Bearer {token}"},
    )
    # extra='forbid' rechaza 'id' → 422
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_perfil_estado_en_body_retorna_422(perfil_client, perfil_router_data):
    """TRIANGULATE: PATCH con 'estado' en body → 422 (campo no declarado)."""
    data = perfil_router_data
    token = _make_jwt(data["tid"], data["auth_con_perm"], [data["rol_con_perm"]])
    resp = await perfil_client.patch(
        "/api/v1/perfil",
        json={"estado": "inactivo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
