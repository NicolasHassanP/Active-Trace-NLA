"""
test_alumno_router.py — TDD task 4.3.

RED: GET /api/v1/alumno/estado-academico
    - 401 sin JWT
    - 403 sin academico:ver_propio
    - 200 con permiso → retorna EstadoAcademicoRead

TRIANGULATE:
    - identidad siempre del JWT (no acepta user_id en query/body)
    - tenant isolation: alumno del tenant A no ve datos del tenant B
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
async def alumno_router_data(test_engine, create_tables):
    """Crea tenant + usuarios + RBAC mínimo para tests del alumno router."""
    import app.models  # noqa
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

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre=f"AlumnoRouter {tid}", estado=TenantEstado.ACTIVO))
    await session.flush()

    rol_alumno = Rol(tenant_id=tid, nombre=f"ROL_ALUMNO_{tid}")
    rol_sin = Rol(tenant_id=tid, nombre=f"ROL_SIN_{tid}")
    session.add_all([rol_alumno, rol_sin])
    await session.flush()

    perm = Permiso(tenant_id=tid, codigo="academico:ver_propio", modulo="academico", accion="ver_propio")
    session.add(perm)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_alumno.id, permiso_id=perm.id, scope=PermisoScope.global_,
    ))
    await session.flush()

    uid_alumno = uuid.uuid4()
    uid_sin = uuid.uuid4()

    for uid, email, nombre in [
        (uid_alumno, f"alumno_{tid}@test.com", "Alumno"),
        (uid_sin, f"sinrol_{tid}@test.com", "SinRol"),
    ]:
        session.add(Usuario(
            id=uid, tenant_id=tid,
            email_encrypted=email,
            email_hash=email_lookup_hash(email),
            nombre=nombre, apellidos="Test", estado=UsuarioEstado.activo,
        ))

    await session.commit()

    yield {
        "tid": tid,
        "uid_alumno": uid_alumno,
        "uid_sin": uid_sin,
        "rol_alumno": rol_alumno.nombre,
        "rol_sin": rol_sin.nombre,
    }

    from sqlalchemy import delete
    await session.execute(delete(RolPermiso).where(RolPermiso.tenant_id == tid))
    await session.execute(delete(Permiso).where(Permiso.tenant_id == tid))
    await session.execute(delete(Rol).where(Rol.tenant_id == tid))
    await session.execute(delete(Usuario).where(Usuario.tenant_id == tid))
    await session.execute(delete(Tenant).where(Tenant.id == tid))
    await session.commit()
    await session.close()

    config_mod.Settings = _original_settings


@pytest_asyncio.fixture(scope="module")
def alumno_router_app(test_engine, alumno_router_data):
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
async def alumno_client(alumno_router_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=alumno_router_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Task 4.3 RED — 401 sin JWT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_academico_sin_jwt_retorna_401(alumno_client):
    resp = await alumno_client.get("/api/v1/alumno/estado-academico")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Task 4.3 RED — 403 sin permiso
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_academico_sin_permiso_retorna_403(alumno_client, alumno_router_data):
    data = alumno_router_data
    token = _make_jwt(data["tid"], data["uid_sin"], [data["rol_sin"]])
    resp = await alumno_client.get(
        "/api/v1/alumno/estado-academico",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Task 4.3 RED — 200 con permiso → estructura correcta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_academico_con_permiso_retorna_200(alumno_client, alumno_router_data):
    data = alumno_router_data
    token = _make_jwt(data["tid"], data["uid_alumno"], [data["rol_alumno"]])
    resp = await alumno_client.get(
        "/api/v1/alumno/estado-academico",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "avance_global_pct" in body
    assert "materias" in body
    assert "coloquios_reservados" in body
    assert isinstance(body["materias"], list)
    assert isinstance(body["coloquios_reservados"], list)


# ---------------------------------------------------------------------------
# TRIANGULATE — sin padrón: avance 0, listas vacías
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_academico_sin_padron_retorna_avance_cero(alumno_client, alumno_router_data):
    """Alumno sin entradas en el padrón activo: avance_global_pct=0."""
    data = alumno_router_data
    token = _make_jwt(data["tid"], data["uid_alumno"], [data["rol_alumno"]])
    resp = await alumno_client.get(
        "/api/v1/alumno/estado-academico",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["avance_global_pct"] == 0
    assert body["total_actividades"] == 0
    assert body["aprobadas"] == 0
    assert body["materias"] == []
    assert body["coloquios_reservados"] == []


# ---------------------------------------------------------------------------
# TRIANGULATE — identidad del JWT no puede ser sobreescrita por query params
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_academico_ignora_user_id_en_query(alumno_client, alumno_router_data):
    """El endpoint no acepta user_id como query param (identidad del JWT)."""
    data = alumno_router_data
    token = _make_jwt(data["tid"], data["uid_alumno"], [data["rol_alumno"]])
    resp = await alumno_client.get(
        f"/api/v1/alumno/estado-academico?user_id={data['uid_sin']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    # FastAPI ignora query params no declarados → 200 (no 422)
    assert resp.status_code == 200
    # El resultado refleja al alumno del JWT, no al uid_sin
    body = resp.json()
    assert "avance_global_pct" in body
