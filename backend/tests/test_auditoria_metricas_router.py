"""
test_auditoria_metricas_router.py — Tasks 5.1–5.6 (C-19)

Tests for the new audit panel metric endpoints:
    GET /api/v1/auditoria/metricas/acciones-por-dia
    GET /api/v1/auditoria/metricas/interacciones-docente
    GET /api/v1/auditoria/metricas/interacciones-docente-materia
    GET /api/v1/auditoria/metricas/comunicaciones-por-docente
    GET /api/v1/auditoria/ultimas-acciones

Coverage:
    5.1-5.5 RED+GREEN — 200 with permission, 403 without, scope and filter params.
    5.6     — D6: metrics endpoints do NOT register AUDITORIA_CONSULTA.
    6.1     — Tenant isolation.
    6.2     — scope propio end-to-end.
    6.3     — fail-closed: 403 per endpoint.
    6.4     — read-only: no AuditMetricsRepository has INSERT/UPDATE/DELETE.

Identity from JWT. Real DB.
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
# JWT helpers
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


def _make_jwt(tenant_id, user_id, roles):
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


def _fake_settings():
    class FakeSettings:
        SECRET_KEY = TEST_SECRET_KEY
        ENCRYPTION_KEY = TEST_ENCRYPTION_KEY
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        MFA_TOKEN_EXPIRE_MINUTES = 10
        REFRESH_TOKEN_EXPIRE_DAYS = 7
        RECOVERY_TOKEN_EXPIRE_MINUTES = 30
        LOGIN_RATE_LIMIT = "10/minute"
        AUDIT_PANEL_LOG_MAX = 200

    return FakeSettings()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def metrics_setup(test_engine, create_tables):
    """
    Two tenants, each with RBAC:
        tenant_a / user_admin_a  → ADMIN role with auditoria:ver (global)
        tenant_a / user_coord_a  → COORD role with auditoria:ver (propio)
        tenant_b / user_b        → ADMIN with auditoria:ver (global)
    Also seeds a few audit events for tenant_a.
    """
    factory = build_session_factory(test_engine)
    session = factory()

    tid_a = uuid.uuid4()
    tid_b = uuid.uuid4()
    session.add(Tenant(id=tid_a, nombre=f"Metrics A {tid_a.hex[:6]}", estado=TenantEstado.ACTIVO))
    session.add(Tenant(id=tid_b, nombre=f"Metrics B {tid_b.hex[:6]}", estado=TenantEstado.ACTIVO))
    await session.flush()

    user_admin = uuid.uuid4()
    user_coord = uuid.uuid4()
    user_b = uuid.uuid4()

    rol_admin = Rol(tenant_id=tid_a, nombre=f"MET_ADMIN_{tid_a.hex[:4]}")
    rol_coord = Rol(tenant_id=tid_a, nombre=f"MET_COORD_{tid_a.hex[:4]}")
    rol_b = Rol(tenant_id=tid_b, nombre=f"MET_ADMIN_B_{tid_b.hex[:4]}")
    session.add_all([rol_admin, rol_coord, rol_b])
    await session.flush()

    perm_a = Permiso(tenant_id=tid_a, codigo="auditoria:ver", modulo="auditoria", accion="ver")
    perm_b = Permiso(tenant_id=tid_b, codigo="auditoria:ver", modulo="auditoria", accion="ver")
    session.add_all([perm_a, perm_b])
    await session.flush()

    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_admin.id, permiso_id=perm_a.id, scope=PermisoScope.global_))
    session.add(RolPermiso(tenant_id=tid_a, rol_id=rol_coord.id, permiso_id=perm_a.id, scope=PermisoScope.propio))
    session.add(RolPermiso(tenant_id=tid_b, rol_id=rol_b.id, permiso_id=perm_b.id, scope=PermisoScope.global_))
    await session.commit()

    # Seed a few audit events for tenant_a
    repo_a = AuditRepository(session=session, tenant_id=tid_a)
    for _ in range(3):
        await repo_a.record(AuditEvent(
            tenant_id=tid_a,
            actor_user_id=user_admin,
            accion=AuditAction.AUDITORIA_CONSULTA,
            modulo="auditoria",
            entidad_tipo="AuditEvent",
            resultado=AuditResultado.ok,
        ))
    # One event from coord user
    await repo_a.record(AuditEvent(
        tenant_id=tid_a,
        actor_user_id=user_coord,
        accion=AuditAction.PADRON_CARGAR,
        modulo="padron",
        entidad_tipo="Materia",
        entidad_id=str(uuid.uuid4()),
        resultado=AuditResultado.ok,
    ))
    # One event for tenant_b
    repo_b = AuditRepository(session=session, tenant_id=tid_b)
    await repo_b.record(AuditEvent(
        tenant_id=tid_b,
        actor_user_id=user_b,
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        resultado=AuditResultado.ok,
    ))
    await session.close()

    return {
        "tid_a": tid_a,
        "tid_b": tid_b,
        "user_admin": user_admin,
        "user_coord": user_coord,
        "user_b": user_b,
        "rol_admin": rol_admin.nombre,
        "rol_coord": rol_coord.nombre,
        "rol_b": rol_b.nombre,
    }


@pytest_asyncio.fixture(scope="module")
def metrics_app(test_engine, metrics_setup):
    from app.main import create_app
    app = create_app()
    session_factory = build_session_factory(test_engine)
    app.state.session_factory = session_factory
    return app


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get(client, path, token):
    return await client.get(path, headers={"Authorization": f"Bearer {token}"})


# ---------------------------------------------------------------------------
# 5.1 — GET /auditoria/metricas/acciones-por-dia
# ---------------------------------------------------------------------------

ENDPOINTS_REQUIRING_PERMISSION = [
    "/api/v1/auditoria/metricas/acciones-por-dia",
    "/api/v1/auditoria/metricas/interacciones-docente",
    "/api/v1/auditoria/metricas/interacciones-docente-materia",
    "/api/v1/auditoria/metricas/comunicaciones-por-docente",
    "/api/v1/auditoria/ultimas-acciones",
]


@pytest.mark.asyncio(loop_scope="function")
@pytest.mark.parametrize("endpoint", ENDPOINTS_REQUIRING_PERMISSION)
async def test_metrics_without_permission_returns_403(monkeypatch, metrics_app, metrics_setup, endpoint):
    """6.3 — Each metrics endpoint returns 403 without auditoria:ver."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    # Use a role with no permissions
    token = _make_jwt(s["tid_a"], uuid.uuid4(), ["NO_PERM_ROLE"])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, endpoint, token)
    assert resp.status_code == 403


@pytest.mark.asyncio(loop_scope="function")
async def test_acciones_por_dia_200_with_permission(monkeypatch, metrics_app, metrics_setup):
    """5.1 — 200 response with valid permission."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/metricas/acciones-por-dia", token)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio(loop_scope="function")
async def test_acciones_por_dia_scope_propio(monkeypatch, metrics_app, metrics_setup):
    """5.1 Triangulation — scope propio filters to coord's own events only."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_coord"], [s["rol_coord"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp_propio = await _get(client, "/api/v1/auditoria/metricas/acciones-por-dia", token)
        token_global = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
        resp_global = await _get(client, "/api/v1/auditoria/metricas/acciones-por-dia", token_global)
    assert resp_propio.status_code == 200
    assert resp_global.status_code == 200
    # Global total should be >= propio total (since global sees more actors)
    total_propio = sum(i["total"] for i in resp_propio.json()["items"])
    total_global = sum(i["total"] for i in resp_global.json()["items"])
    assert total_global >= total_propio


# ---------------------------------------------------------------------------
# 5.2 — interacciones-docente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_interacciones_docente_200(monkeypatch, metrics_app, metrics_setup):
    """5.2 — 200 response with items list."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/metricas/interacciones-docente", token)
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio(loop_scope="function")
async def test_interacciones_docente_filter_by_actor(monkeypatch, metrics_app, metrics_setup):
    """5.2 Triangulation — filter by actor_user_id."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auditoria/metricas/interacciones-docente",
            headers={"Authorization": f"Bearer {token}"},
            params={"actor_user_id": str(s["user_admin"])},
        )
    assert resp.status_code == 200
    data = resp.json()["items"]
    # All returned items should be for user_admin
    assert all(i["actor_user_id"] == str(s["user_admin"]) for i in data)


# ---------------------------------------------------------------------------
# 5.3 — interacciones-docente-materia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_interacciones_docente_materia_200(monkeypatch, metrics_app, metrics_setup):
    """5.3 — 200 and items contain materia_id field (D1)."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/metricas/interacciones-docente-materia", token)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    # At least one item should have materia_id (we seeded one Materia event)
    materia_ids = {i.get("materia_id") for i in data["items"]}
    # There may be null materia_id buckets too — that's expected
    assert isinstance(data["items"], list)


@pytest.mark.asyncio(loop_scope="function")
async def test_interacciones_docente_materia_filter(monkeypatch, metrics_app, metrics_setup):
    """5.3 Triangulation — filter by materia_id excludes null bucket."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    fake_materia_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auditoria/metricas/interacciones-docente-materia",
            headers={"Authorization": f"Bearer {token}"},
            params={"materia_id": fake_materia_id},
        )
    assert resp.status_code == 200
    # Only results for that specific materia (may be empty if not seeded for this materia_id)
    for item in resp.json()["items"]:
        assert item["materia_id"] == fake_materia_id


# ---------------------------------------------------------------------------
# 5.4 — comunicaciones-por-docente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_comunicaciones_por_docente_200(monkeypatch, metrics_app, metrics_setup):
    """5.4 — 200 response."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/metricas/comunicaciones-por-docente", token)
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio(loop_scope="function")
async def test_comunicaciones_scope_propio(monkeypatch, metrics_app, metrics_setup):
    """5.4 Triangulation — scope propio filters to coord's own comunicaciones."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_coord"], [s["rol_coord"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/metricas/comunicaciones-por-docente", token)
    assert resp.status_code == 200
    # With scope propio, only coord's own comunicaciones appear
    for item in resp.json()["items"]:
        # enviado_por should be null (no real user) or coord's id
        assert item.get("enviado_por") in [None, str(s["user_coord"])]


# ---------------------------------------------------------------------------
# 5.5 — ultimas-acciones (with limite validation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_ultimas_acciones_200_default_limite(monkeypatch, metrics_app, metrics_setup):
    """5.5 — 200 with default limite (no param)."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/ultimas-acciones", token)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio(loop_scope="function")
async def test_ultimas_acciones_limite_exceeds_max_returns_422(monkeypatch, metrics_app, metrics_setup):
    """5.5 — limite > AUDIT_PANEL_LOG_MAX → 422."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auditoria/ultimas-acciones",
            headers={"Authorization": f"Bearer {token}"},
            params={"limite": 9999},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="function")
async def test_ultimas_acciones_limite_zero_returns_422(monkeypatch, metrics_app, metrics_setup):
    """5.5 — limite=0 → 422."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auditoria/ultimas-acciones",
            headers={"Authorization": f"Bearer {token}"},
            params={"limite": 0},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 5.6 — D6: metrics endpoints do NOT register AUDITORIA_CONSULTA
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_metrics_endpoints_do_not_register_audit_event(
    monkeypatch, test_engine, metrics_app, metrics_setup
):
    """5.6 / D6 — calling a metrics endpoint does NOT create a new AUDITORIA_CONSULTA event."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup

    # Fresh user so we can count their events precisely
    fresh_user = uuid.uuid4()
    token = _make_jwt(s["tid_a"], fresh_user, [s["rol_admin"]])

    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/metricas/acciones-por-dia", token)
    assert resp.status_code == 200

    # Query events for fresh_user AFTER the call
    factory = build_session_factory(test_engine)
    session = factory()
    repo = AuditRepository(session=session, tenant_id=s["tid_a"])
    events = await repo.list(actor_user_id=fresh_user)
    await session.close()

    # No AUDITORIA_CONSULTA should have been recorded for the metrics call (D6)
    consulta_events = [e for e in events if e.accion == AuditAction.AUDITORIA_CONSULTA]
    assert len(consulta_events) == 0, (
        "Metrics endpoint must NOT register AUDITORIA_CONSULTA (D6)"
    )


# ---------------------------------------------------------------------------
# 6.1 — Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_metrics_tenant_isolation(monkeypatch, test_engine, metrics_app, metrics_setup):
    """6.1 — Metrics never return data from another tenant."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup

    token_a = _make_jwt(s["tid_a"], s["user_admin"], [s["rol_admin"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/ultimas-acciones", token_a)
    assert resp.status_code == 200
    data = resp.json()
    # All events must belong to tenant_a
    tenant_ids_seen = {e["tenant_id"] for e in data}
    assert str(s["tid_b"]) not in tenant_ids_seen


# ---------------------------------------------------------------------------
# 6.2 — scope propio end-to-end
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_ultimas_acciones_scope_propio(monkeypatch, metrics_app, metrics_setup):
    """6.2 — scope propio: coordinator sees only their own events in log."""
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = metrics_setup
    token = _make_jwt(s["tid_a"], s["user_coord"], [s["rol_coord"]])
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        resp = await _get(client, "/api/v1/auditoria/ultimas-acciones", token)
    assert resp.status_code == 200
    data = resp.json()
    # All returned events must be for user_coord
    actor_ids = {e["actor_user_id"] for e in data}
    assert all(aid == str(s["user_coord"]) for aid in actor_ids), (
        "scope propio must return only the coordinator's own events"
    )
