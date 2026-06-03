"""
test_require_permission.py — Tasks 5.2, 5.4-5.6 RED/TRIANGULATE

Tests for require_permission(codigo) FastAPI dependency:
- ALUMNO (no permissions) → 403.
- COORDINADOR with the permission → endpoint executes (200).
- No JWT → 401 (before permission check).
- User from tenant without catalog → 403.
- Guard exposes scope (propio vs global).
- Identity/roles come only from token, not from request body/headers.

Pattern: mount a minimal FastAPI test app with a protected endpoint,
         seed the catalog, then call via httpx AsyncClient.
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://postgres:280502@localhost:5432/activia_trace_test",
    "SECRET_KEY": "supersecretkeyfortesting1234567890",
    "ENCRYPTION_KEY": "E" * 32,
}


def _fake_settings():
    """Return a minimal settings-like object to avoid loading from .env."""
    class FakeSettings:
        SECRET_KEY = TEST_ENV["SECRET_KEY"]
        ENCRYPTION_KEY = TEST_ENV["ENCRYPTION_KEY"]
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
    return FakeSettings()


def setup_env(monkeypatch):
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)
    # Patch _settings() to avoid Settings() failing due to TEST_DATABASE_URL
    # in the environment (pydantic extra='forbid').
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)


# ---------------------------------------------------------------------------
# Fixture: minimal FastAPI app for require_permission tests
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def guard_tenant(test_engine):
    """Tenant for guard tests."""
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Guard Test Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def empty_guard_tenant(test_engine):
    """Tenant with NO catalog seeded (for 'no catalog → 403' test)."""
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Empty Guard Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def guard_seeded(test_engine, create_tables, guard_tenant):
    """
    Seed catalog for guard tests:
    ALUMNO_G  → (no permissions)
    PROFESOR_G → calificaciones:importar (propio), atrasados:ver (propio)
    COORD_G   → calificaciones:importar (global), atrasados:ver (global)
    """
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = guard_tenant

    rol_alumno = Rol(tenant_id=tid, nombre="ALUMNO_G")
    rol_prof = Rol(tenant_id=tid, nombre="PROFESOR_G")
    rol_coord = Rol(tenant_id=tid, nombre="COORD_G")
    session.add_all([rol_alumno, rol_prof, rol_coord])
    await session.flush()

    perm_calc = Permiso(
        tenant_id=tid, codigo="calificaciones:importar",
        modulo="calificaciones", accion="importar",
    )
    perm_atrasados = Permiso(
        tenant_id=tid, codigo="atrasados:ver",
        modulo="atrasados", accion="ver",
    )
    session.add_all([perm_calc, perm_atrasados])
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_prof.id,
        permiso_id=perm_calc.id, scope=PermisoScope.propio,
    ))
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_prof.id,
        permiso_id=perm_atrasados.id, scope=PermisoScope.propio,
    ))
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_coord.id,
        permiso_id=perm_calc.id, scope=PermisoScope.global_,
    ))
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_coord.id,
        permiso_id=perm_atrasados.id, scope=PermisoScope.global_,
    ))

    await session.commit()
    await session.close()


def _make_token(monkeypatch, tenant_id: uuid.UUID, roles: list) -> str:
    """
    Build a valid access JWT for the given tenant and roles.

    Encodes the token directly with jose.jwt using the TEST_ENV SECRET_KEY
    to avoid triggering Settings() which would fail due to TEST_DATABASE_URL
    being present in the test environment (pydantic extra='forbid').
    """
    import datetime
    from jose import jwt as jose_jwt

    secret_key = TEST_ENV["SECRET_KEY"]
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    exp = now + datetime.timedelta(minutes=30)
    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    return jose_jwt.encode(payload, secret_key, algorithm="HS256")


def _build_test_app(test_engine):
    """Build a minimal FastAPI app with a protected endpoint for testing."""
    from fastapi import FastAPI, Depends
    from app.core.dependencies import require_permission
    from app.core.database import build_session_factory
    from app.services.authorization_service import PermissionGrant

    app = FastAPI()
    session_factory = build_session_factory(test_engine)
    app.state.session_factory = session_factory

    @app.get("/protected/calificaciones")
    async def protected_endpoint(
        grant: PermissionGrant = Depends(require_permission("calificaciones:importar")),
    ):
        return {"status": "ok", "scope": grant.scope.value}

    @app.get("/protected/atrasados")
    async def protected_atrasados(
        grant: PermissionGrant = Depends(require_permission("atrasados:ver")),
    ):
        return {"status": "ok", "scope": grant.scope.value}

    return app


# ---------------------------------------------------------------------------
# Task 5.2 — RED: require_permission doesn't exist yet
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_alumno_without_permission_gets_403(
    monkeypatch, test_engine, guard_seeded, guard_tenant
):
    """ALUMNO_G has no permissions → require_permission responds 403."""
    setup_env(monkeypatch)
    token = _make_token(monkeypatch, guard_tenant, ["ALUMNO_G"])
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/protected/calificaciones",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Task 5.4 — TRIANGULATE: coordinator passes, no JWT → 401, empty catalog → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_coordinator_with_permission_gets_200(
    monkeypatch, test_engine, guard_seeded, guard_tenant
):
    """Happy: COORD_G has calificaciones:importar → guard passes, returns 200."""
    setup_env(monkeypatch)
    token = _make_token(monkeypatch, guard_tenant, ["COORD_G"])
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/protected/calificaciones",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio(loop_scope="function")
async def test_no_jwt_gets_401(monkeypatch, test_engine, guard_seeded, guard_tenant):
    """Edge: no JWT → 401 (identity check before permission check)."""
    setup_env(monkeypatch)
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/protected/calificaciones")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio(loop_scope="function")
async def test_user_from_empty_catalog_tenant_gets_403(
    monkeypatch, test_engine, empty_guard_tenant
):
    """Edge: tenant with no catalog → empty permissions → 403."""
    setup_env(monkeypatch)
    token = _make_token(monkeypatch, empty_guard_tenant, ["ADMIN"])
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/protected/calificaciones",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Task 5.5 — TRIANGULATE: guard exposes scope correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_profesor_gets_propio_scope(
    monkeypatch, test_engine, guard_seeded, guard_tenant
):
    """PROFESOR_G has atrasados:ver propio → guard returns scope=propio."""
    setup_env(monkeypatch)
    token = _make_token(monkeypatch, guard_tenant, ["PROFESOR_G"])
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/protected/atrasados",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["scope"] == "propio"


@pytest.mark.asyncio(loop_scope="function")
async def test_coordinator_gets_global_scope(
    monkeypatch, test_engine, guard_seeded, guard_tenant
):
    """COORD_G has atrasados:ver global → guard returns scope=global."""
    setup_env(monkeypatch)
    token = _make_token(monkeypatch, guard_tenant, ["COORD_G"])
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/protected/atrasados",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["scope"] == "global"


# ---------------------------------------------------------------------------
# Task 5.6 — TRIANGULATE: identity comes only from token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_roles_in_body_do_not_grant_access(
    monkeypatch, test_engine, guard_seeded, guard_tenant
):
    """
    Edge: even if a request header tries to inject roles, the guard
    must use only the roles from the JWT claim.
    User has token with ALUMNO_G (no permission) → 403 regardless of headers.
    """
    setup_env(monkeypatch)
    token = _make_token(monkeypatch, guard_tenant, ["ALUMNO_G"])
    app = _build_test_app(test_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/protected/calificaciones",
            headers={
                "Authorization": f"Bearer {token}",
                # Attempting to inject a role via a custom header — must be ignored
                "X-Roles": "COORD_G",
            },
        )
    assert resp.status_code == 403, (
        f"Custom role header should be ignored, expected 403 got {resp.status_code}"
    )
