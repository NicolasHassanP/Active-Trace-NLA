"""
test_auditoria_router.py — Tasks 11.1, 11.2, 11.3, 11.4, 11.5 RED/GREEN/TRIANGULATE

Tests for GET /api/v1/auditoria (D8, spec audit-query).

Coverage:
  11.1 RED   — No permission → 403 (fail-closed).
  11.2 RED   — scope=propio → only own events; scope=global → all tenant events.
  11.3 GREEN — Router implemented.
  11.4 GREEN — Router registered in main.
  11.5 TRIANG — Tenant isolation + AUDITORIA_CONSULTA registered on each call.

Identity comes from JWT only. Uses real DB.
"""
import uuid
import datetime
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.core.database import build_session_factory
from app.models.audit import AuditAction, AuditEvent, AuditResultado
from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.repositories.audit_repository import AuditRepository


# ---------------------------------------------------------------------------
# JWT helper — same pattern as test_require_permission.py
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
    return FakeSettings()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def audit_test_setup(test_engine, create_tables):
    """
    Set up two tenants with RBAC catalog for auditoria tests:
      tenant_a: user_admin → ADMIN role with auditoria:ver (global)
      tenant_a: user_coord → COORDINADOR role with auditoria:ver (propio)
      tenant_b: user_b    → ADMIN with auditoria:ver (global)
    Returns a dict with all relevant IDs.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    # Tenants
    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre="Audit Test Tenant A", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre="Audit Test Tenant B", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Users (just UUIDs — we don't have a users table yet in C-05)
    user_admin_a = uuid.uuid4()
    user_coord_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # Roles for tenant A
    rol_admin_a = Rol(tenant_id=tid_a, nombre="AUDIT_ADMIN")
    rol_coord_a = Rol(tenant_id=tid_a, nombre="AUDIT_COORD")
    session.add_all([rol_admin_a, rol_coord_a])
    await session.flush()

    # Role for tenant B
    rol_b = Rol(tenant_id=tid_b, nombre="AUDIT_ADMIN_B")
    session.add(rol_b)
    await session.flush()

    # Permission
    perm_a_global = Permiso(
        tenant_id=tid_a, codigo="auditoria:ver", modulo="auditoria", accion="ver"
    )
    perm_a_propio = Permiso(
        tenant_id=tid_a, codigo="auditoria:ver_propio", modulo="auditoria", accion="ver"
    )
    perm_b = Permiso(
        tenant_id=tid_b, codigo="auditoria:ver", modulo="auditoria", accion="ver"
    )
    session.add_all([perm_a_global, perm_a_propio, perm_b])
    await session.flush()

    # Grant ADMIN global, COORD propio
    session.add(RolPermiso(
        tenant_id=tid_a, rol_id=rol_admin_a.id,
        permiso_id=perm_a_global.id, scope=PermisoScope.global_,
    ))
    session.add(RolPermiso(
        tenant_id=tid_a, rol_id=rol_coord_a.id,
        permiso_id=perm_a_global.id, scope=PermisoScope.propio,
    ))
    session.add(RolPermiso(
        tenant_id=tid_b, rol_id=rol_b.id,
        permiso_id=perm_b.id, scope=PermisoScope.global_,
    ))
    await session.commit()
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "user_admin_a": user_admin_a,
        "user_coord_a": user_coord_a,
        "user_b": user_b,
        "rol_admin_a": "AUDIT_ADMIN",
        "rol_coord_a": "AUDIT_COORD",
        "rol_b": "AUDIT_ADMIN_B",
    }


@pytest_asyncio.fixture(scope="module")
def audit_app(test_engine, audit_test_setup):
    """FastAPI app with test engine for auditoria router tests."""
    from app.main import create_app

    app = create_app()
    session_factory = build_session_factory(test_engine)
    app.state.session_factory = session_factory
    return app


# ---------------------------------------------------------------------------
# Task 11.1 — No permission → 403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_auditoria_without_permission_returns_403(
    monkeypatch, audit_app, audit_test_setup
):
    """Task 11.1 RED: user with no permissions gets 403 on GET /api/v1/auditoria."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)

    s = audit_test_setup
    # Create a token with a role that has NO auditoria:ver permission
    token = _make_jwt(
        tenant_id=s["tid_a"],
        user_id=uuid.uuid4(),
        roles=["NO_PERMISSION_ROLE"],
    )

    async with AsyncClient(
        transport=ASGITransport(app=audit_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio(loop_scope="function")
async def test_auditoria_without_token_returns_401(audit_app):
    """No JWT → 401."""
    async with AsyncClient(
        transport=ASGITransport(app=audit_app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/auditoria")

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Task 11.2 — scope propio vs global
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_auditoria_scope_propio_returns_only_own_events(
    monkeypatch, test_engine, audit_app, audit_test_setup
):
    """Task 11.2: scope=propio → only events for actor_user_id = current user."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)

    s = audit_test_setup
    user_id = s["user_coord_a"]
    tenant_id = s["tid_a"]
    other_user_id = uuid.uuid4()

    # Seed events for both users in tenant A
    factory = build_session_factory(test_engine)
    session = factory()
    repo_a = AuditRepository(session=session, tenant_id=tenant_id)

    own_event = await repo_a.record(AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=user_id,
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    ))
    other_event = await repo_a.record(AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=other_user_id,
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    ))
    await session.close()

    token = _make_jwt(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=[s["rol_coord_a"]],  # propio scope
    )

    async with AsyncClient(
        transport=ASGITransport(app=audit_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # All returned events must belong to the requesting user
    actor_ids = {e["actor_user_id"] for e in data}
    assert str(other_user_id) not in actor_ids, (
        "scope=propio should not return other users' events"
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_auditoria_scope_global_returns_all_tenant_events(
    monkeypatch, test_engine, audit_app, audit_test_setup
):
    """Task 11.2: scope=global → all events of the tenant."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)

    s = audit_test_setup
    tenant_id = s["tid_a"]
    user_admin = s["user_admin_a"]
    user_other = uuid.uuid4()

    # Seed events for two different users in tenant A
    factory = build_session_factory(test_engine)
    session = factory()
    repo_a = AuditRepository(session=session, tenant_id=tenant_id)
    await repo_a.record(AuditEvent(
        tenant_id=tenant_id, actor_user_id=user_admin,
        accion=AuditAction.AUDITORIA_CONSULTA, modulo="auditoria",
        entidad_tipo="AuditEvent", resultado=AuditResultado.ok,
    ))
    await repo_a.record(AuditEvent(
        tenant_id=tenant_id, actor_user_id=user_other,
        accion=AuditAction.AUDITORIA_CONSULTA, modulo="auditoria",
        entidad_tipo="AuditEvent", resultado=AuditResultado.ok,
    ))
    await session.close()

    token = _make_jwt(
        tenant_id=tenant_id,
        user_id=user_admin,
        roles=[s["rol_admin_a"]],  # global scope
    )

    async with AsyncClient(
        transport=ASGITransport(app=audit_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Both users' events present
    actor_ids = {e["actor_user_id"] for e in data}
    assert str(user_other) in actor_ids, "Global scope must include other users' events"


# ---------------------------------------------------------------------------
# Task 11.5 — Tenant isolation + AUDITORIA_CONSULTA registered
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_auditoria_tenant_isolation(
    monkeypatch, test_engine, audit_app, audit_test_setup
):
    """Task 11.5: user of tenant A never sees events of tenant B."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)

    s = audit_test_setup
    tenant_a = s["tid_a"]
    tenant_b = s["tid_b"]
    user_b = s["user_b"]

    # Seed an event in tenant B
    factory = build_session_factory(test_engine)
    session = factory()
    repo_b = AuditRepository(session=session, tenant_id=tenant_b)
    b_event = await repo_b.record(AuditEvent(
        tenant_id=tenant_b, actor_user_id=user_b,
        accion=AuditAction.AUDITORIA_CONSULTA, modulo="auditoria",
        entidad_tipo="AuditEvent", resultado=AuditResultado.ok,
    ))
    await session.close()

    # Authenticate as admin in tenant A (global scope)
    token = _make_jwt(
        tenant_id=tenant_a,
        user_id=s["user_admin_a"],
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=audit_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    event_ids = {e["id"] for e in data}
    tenant_ids_seen = {e["tenant_id"] for e in data}

    # No event from tenant B must appear
    assert str(b_event.id) not in event_ids, (
        "Tenant isolation broken: tenant A sees tenant B event"
    )
    assert str(tenant_b) not in tenant_ids_seen, (
        "Tenant isolation broken: tenant A sees tenant B tenant_id"
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_auditoria_query_registers_auditoria_consulta(
    monkeypatch, test_engine, audit_app, audit_test_setup
):
    """Task 11.5 OQ-2: every call to GET /auditoria registers AUDITORIA_CONSULTA."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)

    s = audit_test_setup
    tenant_id = s["tid_a"]
    user_id = uuid.uuid4()  # Fresh user so we can count his events

    # Seed ADMIN role for this new user
    factory = build_session_factory(test_engine)
    session = factory()
    repo = AuditRepository(session=session, tenant_id=tenant_id)

    token = _make_jwt(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=[s["rol_admin_a"]],
    )

    async with AsyncClient(
        transport=ASGITransport(app=audit_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200

    # After the call, there should be at least one AUDITORIA_CONSULTA event for this user
    events = await repo.list(actor_user_id=user_id)
    await session.close()

    consulta_events = [
        e for e in events if e.accion == AuditAction.AUDITORIA_CONSULTA
    ]
    assert len(consulta_events) >= 1, (
        "GET /auditoria must register AUDITORIA_CONSULTA event (OQ-2)"
    )
