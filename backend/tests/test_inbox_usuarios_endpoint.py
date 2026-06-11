"""
test_inbox_usuarios_endpoint.py — TDD suite para GET /api/v1/inbox/usuarios

Implementa el endpoint de búsqueda de usuarios gateado a inbox:usar,
espejo de GET /asignaciones/usuarios pero con permiso diferente.

Cubre:
    Task 1a — usuario con inbox:usar busca y recibe resultados filtrados por q
    Task 1b — triangulación: q distinto / sin q (lista completa acotada)
    Task 1c — 403 si el rol NO tiene inbox:usar
    Task 1d — aislamiento por tenant (usuario de otro tenant no aparece)

Strict TDD: RED → GREEN → TRIANGULATE → REFACTOR.
DB real (activia_trace_test). Sin mocks.
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
from app.models.auth import AuthIdentity
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def inbox_usuarios_data(test_engine, create_tables):
    """
    Crea dos tenants con RBAC para tests del endpoint GET /inbox/usuarios.

    tenant_a:
      - rol_inbox (con permiso inbox:usar)
      - rol_sin   (sin permiso inbox:usar)
      - u1 ("García", "Carlos") — vinculado a auth_identity
      - u2 ("López", "Ana") — vinculado a auth_identity
      - u_sin — sin rol inbox

    tenant_b:
      - u_otro — para verificar aislamiento cross-tenant
    """
    import app.core.config as config_mod
    from app.core.security.passwords import email_lookup_hash

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

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre=f"InboxUsr TenantA {tid_a}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre=f"InboxUsr TenantB {tid_b}", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Roles en tenant_a
    rol_inbox = Rol(tenant_id=tid_a, nombre=f"ROL_INBOX_USR_{tid_a}")
    rol_sin = Rol(tenant_id=tid_a, nombre=f"ROL_SIN_USR_{tid_a}")
    session.add_all([rol_inbox, rol_sin])
    await session.flush()

    # Permiso inbox:usar sólo para rol_inbox
    perm_inbox = Permiso(tenant_id=tid_a, codigo="inbox:usar", modulo="inbox", accion="usar")
    session.add(perm_inbox)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid_a,
        rol_id=rol_inbox.id,
        permiso_id=perm_inbox.id,
        scope=PermisoScope.global_,
    ))
    await session.flush()

    # Usuarios en tenant_a (usando helper canónico C-28)
    u1 = await create_usuario_con_identidad(
        session, tid_a,
        email=f"inbox_usr_u1_{tid_a}@test.com",
        nombre="Carlos",
        apellidos="García",
    )
    u2 = await create_usuario_con_identidad(
        session, tid_a,
        email=f"inbox_usr_u2_{tid_a}@test.com",
        nombre="Ana",
        apellidos="López",
    )
    u_sin = await create_usuario_con_identidad(
        session, tid_a,
        email=f"inbox_usr_norol_{tid_a}@test.com",
        nombre="Sin",
        apellidos="Permiso",
    )

    # Usuario en tenant_b para verificar aislamiento
    u_otro = await create_usuario_con_identidad(
        session, tid_b,
        email=f"inbox_usr_otro_{tid_b}@test.com",
        nombre="OtroTenant",
        apellidos="Usuario",
    )

    await session.commit()

    yield {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "uid1": u1.id,
        "uid2": u2.id,
        "uid_sin": u_sin.id,
        "uid_otro": u_otro.id,
        "auth1": u1.auth_identity_id,
        "auth2": u2.auth_identity_id,
        "auth_sin": u_sin.auth_identity_id,
        "auth_otro": u_otro.auth_identity_id,
        "rol_inbox": rol_inbox.nombre,
        "rol_sin": rol_sin.nombre,
        # Apellidos para verificar filtrado por q
        "apellidos_u1": "García",
        "apellidos_u2": "López",
    }

    # Cleanup
    from sqlalchemy import delete

    await session.execute(delete(RolPermiso).where(RolPermiso.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Permiso).where(Permiso.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Rol).where(Rol.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Usuario).where(Usuario.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(AuthIdentity).where(AuthIdentity.tenant_id.in_([tid_a, tid_b])))
    await session.execute(delete(Tenant).where(Tenant.id.in_([tid_a, tid_b])))
    await session.commit()
    await session.close()

    config_mod.Settings = _original_settings


@pytest_asyncio.fixture(scope="module")
def inbox_usuarios_app(test_engine, inbox_usuarios_data):
    import app.core.config as config_mod

    _original = config_mod.Settings

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

    from app.main import create_app

    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory

    yield app

    config_mod.Settings = _original


@pytest_asyncio.fixture(scope="module")
async def inbox_usuarios_client(inbox_usuarios_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=inbox_usuarios_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Task 1c — RED: 403 sin inbox:usar
# (se escribe primero — el endpoint aún no existe)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_usuarios_inbox_sin_permiso_retorna_403(
    inbox_usuarios_client, inbox_usuarios_data
):
    """RED Task 1c: GET /api/v1/inbox/usuarios sin inbox:usar → 403 (fail-closed)."""
    data = inbox_usuarios_data
    token = _make_jwt(data["tid_a"], data["auth_sin"], [data["rol_sin"]])
    resp = await inbox_usuarios_client.get(
        "/api/v1/inbox/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 1a — RED: búsqueda con q filtra por nombre/apellidos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_usuarios_inbox_con_q_filtra_resultados(
    inbox_usuarios_client, inbox_usuarios_data
):
    """
    RED Task 1a: GET /api/v1/inbox/usuarios?q=García devuelve solo usuarios
    cuyo nombre/apellidos hacen ILIKE match con 'García'.
    El usuario u1 (Carlos García) debe aparecer; u2 (Ana López) no.
    """
    data = inbox_usuarios_data
    token = _make_jwt(data["tid_a"], data["auth1"], [data["rol_inbox"]])
    resp = await inbox_usuarios_client.get(
        "/api/v1/inbox/usuarios?q=García",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resultados = resp.json()
    ids_resultado = [r["id"] for r in resultados]
    assert str(data["uid1"]) in ids_resultado, "u1 García debe aparecer en la búsqueda"
    assert str(data["uid2"]) not in ids_resultado, "u2 López NO debe aparecer con q=García"


# ---------------------------------------------------------------------------
# Task 1b — TRIANGULATE: q distinto + sin q
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_usuarios_inbox_con_q_lopez_filtra_correctamente(
    inbox_usuarios_client, inbox_usuarios_data
):
    """
    TRIANGULATE Task 1b: GET /api/v1/inbox/usuarios?q=López devuelve u2 (Ana López)
    y NO devuelve u1 (Carlos García).
    """
    data = inbox_usuarios_data
    token = _make_jwt(data["tid_a"], data["auth1"], [data["rol_inbox"]])
    resp = await inbox_usuarios_client.get(
        "/api/v1/inbox/usuarios?q=López",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resultados = resp.json()
    ids_resultado = [r["id"] for r in resultados]
    assert str(data["uid2"]) in ids_resultado, "u2 López debe aparecer en la búsqueda"
    assert str(data["uid1"]) not in ids_resultado, "u1 García NO debe aparecer con q=López"


@pytest.mark.asyncio
async def test_buscar_usuarios_inbox_sin_q_devuelve_todos_del_tenant(
    inbox_usuarios_client, inbox_usuarios_data
):
    """
    TRIANGULATE Task 1b: GET /api/v1/inbox/usuarios sin q devuelve todos los
    usuarios activos del tenant (hasta 20). u1 y u2 deben estar presentes.
    """
    data = inbox_usuarios_data
    token = _make_jwt(data["tid_a"], data["auth1"], [data["rol_inbox"]])
    resp = await inbox_usuarios_client.get(
        "/api/v1/inbox/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resultados = resp.json()
    ids_resultado = [r["id"] for r in resultados]
    assert str(data["uid1"]) in ids_resultado
    assert str(data["uid2"]) in ids_resultado
    # Máximo 20 resultados (limit del repo)
    assert len(resultados) <= 20


# ---------------------------------------------------------------------------
# Task 1d — TRIANGULATE: aislamiento por tenant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_usuarios_inbox_aislamiento_tenant(
    inbox_usuarios_client, inbox_usuarios_data
):
    """
    TRIANGULATE Task 1d: usuario de tenant_a NO ve usuarios de tenant_b.
    u_otro pertenece a tenant_b y NUNCA debe aparecer en la respuesta de tenant_a.
    """
    data = inbox_usuarios_data
    token = _make_jwt(data["tid_a"], data["auth1"], [data["rol_inbox"]])
    resp = await inbox_usuarios_client.get(
        "/api/v1/inbox/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    ids_resultado = [r["id"] for r in resp.json()]
    assert str(data["uid_otro"]) not in ids_resultado, (
        "Usuario de otro tenant NO debe aparecer en la búsqueda"
    )


# ---------------------------------------------------------------------------
# Contrato del schema de respuesta
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_usuarios_inbox_respuesta_no_expone_pii(
    inbox_usuarios_client, inbox_usuarios_data
):
    """
    TRIANGULATE: la respuesta expone solo campos no-PII
    (id, nombre, apellidos, email, legajo). Nunca tenant_id, dni, cbu, cuil.
    """
    data = inbox_usuarios_data
    token = _make_jwt(data["tid_a"], data["auth1"], [data["rol_inbox"]])
    resp = await inbox_usuarios_client.get(
        "/api/v1/inbox/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resultados = resp.json()
    assert len(resultados) > 0, "Debe haber al menos un usuario en la respuesta"
    for item in resultados:
        assert "id" in item
        assert "nombre" in item
        assert "apellidos" in item
        assert "email" in item
        # PII nunca expuesta
        assert "tenant_id" not in item
        assert "dni" not in item
        assert "cuil" not in item
        assert "cbu" not in item
        assert "email_hash" not in item
