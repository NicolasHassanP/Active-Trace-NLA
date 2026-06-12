"""
test_auditoria_enriquecimiento.py — TDD enrichment tests for actor_nombre / entidad_nombre.

Tasks:
    E.1 RED/GREEN — AuditEvent with known actor (auth_identity_id) + entidad_tipo='Materia'
        → endpoint returns actor_nombre and entidad_nombre correctly.
    E.2 TRIANGULATE — actor auth_identity is orphan (no matching usuario)
        → actor_nombre is None (not an error).
    E.3 TRIANGULATE — entidad_tipo not resolvable (e.g. 'AuditEvent')
        → entidad_nombre is None.
    E.4 RED/GREEN — interacciones-docente metric → actor_nombre resolved.
    E.5 TRIANGULATE — interacciones-docente-materia → actor_nombre + materia_nombre resolved.

KEY INVARIANT (C-28): actor_user_id in AuditEvent = JWT sub = auth_identity.id.
    NOT usuario.id. The join is usuario.auth_identity_id = actor_user_id.
    Using create_usuario_con_identidad guarantees a real AuthIdentity FK.

Identity from JWT. Real DB (native Postgres on localhost:5432).
"""
import uuid
import datetime
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.core.database import build_session_factory
from app.models.audit import AuditAction, AuditEvent, AuditResultado
from app.models.estructura import Materia, EstadoEstructura
from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado
from app.repositories.audit_repository import AuditRepository

# ---------------------------------------------------------------------------
# JWT helpers (same pattern as other router tests)
# ---------------------------------------------------------------------------

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
# Module-level fixture: one tenant, one admin user, one materia, RBAC wired.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def enrich_setup(test_engine, create_tables):
    """
    Set up:
        - tenant_id
        - usuario with real auth_identity_id (create_usuario_con_identidad)
        - materia with known nombre
        - ADMIN role with auditoria:ver (global scope)
    Returns dict with all relevant IDs.
    """
    from tests.conftest import create_usuario_con_identidad

    factory = build_session_factory(test_engine)
    session = factory()

    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Enrich Test Tenant", estado=TenantEstado.ACTIVO))
    await session.flush()

    # Create domain user with real auth_identity (C-28 pattern)
    usuario = await create_usuario_con_identidad(
        session,
        tid,
        nombre="Ana",
        apellidos="García",
    )
    await session.flush()

    # Create a Materia so entidad_nombre can be resolved
    materia = Materia(
        tenant_id=tid,
        nombre="Legislación 1",
        codigo="LEG1",
        estado=EstadoEstructura.activa,
    )
    session.add(materia)
    await session.flush()

    # RBAC: ADMIN with auditoria:ver global
    rol = Rol(tenant_id=tid, nombre="ENRICH_ADMIN")
    session.add(rol)
    await session.flush()

    perm = Permiso(tenant_id=tid, codigo="auditoria:ver", modulo="auditoria", accion="ver")
    session.add(perm)
    await session.flush()

    session.add(RolPermiso(
        tenant_id=tid,
        rol_id=rol.id,
        permiso_id=perm.id,
        scope=PermisoScope.global_,
    ))
    await session.commit()
    await session.close()

    return {
        "tid": tid,
        "usuario_id": usuario.id,
        "auth_identity_id": usuario.auth_identity_id,  # JWT sub
        "nombre_completo": "Ana García",
        "materia_id": materia.id,
        "materia_nombre": "Legislación 1",
        "rol_nombre": "ENRICH_ADMIN",
    }


@pytest_asyncio.fixture(scope="module")
def enrich_app(test_engine, enrich_setup):
    """FastAPI app wired to the test engine."""
    from app.main import create_app

    app = create_app()
    factory = build_session_factory(test_engine)
    app.state.session_factory = factory
    return app


# ---------------------------------------------------------------------------
# E.1 RED→GREEN: actor_nombre and entidad_nombre resolved for known user + Materia
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_enrich_actor_nombre_y_entidad_nombre(
    monkeypatch, test_engine, enrich_app, enrich_setup
):
    """
    E.1: An AuditEvent whose actor_user_id = usuario.auth_identity_id and
    entidad_tipo='Materia' with a valid materia.id → endpoint returns
    actor_nombre='Ana García' and entidad_nombre='Legislación 1'.

    C-28 invariant verified: actor_user_id is auth_identity.id, NOT usuario.id.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = enrich_setup

    # Seed the event: actor_user_id = auth_identity_id (JWT sub)
    factory = build_session_factory(test_engine)
    session = factory()
    repo = AuditRepository(session=session, tenant_id=s["tid"])
    await repo.record(AuditEvent(
        tenant_id=s["tid"],
        actor_user_id=s["auth_identity_id"],   # <-- auth_identity.id, not usuario.id
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="Materia",
        entidad_id=str(s["materia_id"]),
        resultado=AuditResultado.ok,
    ))
    await session.commit()
    await session.close()

    # JWT sub is auth_identity_id
    token = _make_jwt(s["tid"], s["auth_identity_id"], [s["rol_nombre"]])

    async with AsyncClient(
        transport=ASGITransport(app=enrich_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Find the Materia event we seeded (ignore AUDITORIA_CONSULTA auto-events)
    materia_events = [e for e in data if e["entidad_tipo"] == "Materia"]
    assert materia_events, "Expected at least one Materia event in response"

    event = materia_events[0]
    assert event["actor_nombre"] == s["nombre_completo"], (
        f"Expected actor_nombre='{s['nombre_completo']}', got '{event['actor_nombre']}'"
    )
    assert event["entidad_nombre"] == s["materia_nombre"], (
        f"Expected entidad_nombre='{s['materia_nombre']}', got '{event['entidad_nombre']}'"
    )


# ---------------------------------------------------------------------------
# E.2 TRIANGULATE: orphan auth_identity → actor_nombre is None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_enrich_orphan_actor_returns_none(
    monkeypatch, test_engine, enrich_app, enrich_setup
):
    """
    E.2: An AuditEvent whose actor_user_id has no corresponding domain user
    (orphan auth identity) → actor_nombre is None, not an error.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = enrich_setup

    # Seed event with a random UUID that has no matching usuario.auth_identity_id
    orphan_actor_id = uuid.uuid4()

    factory = build_session_factory(test_engine)
    session = factory()
    repo = AuditRepository(session=session, tenant_id=s["tid"])
    await repo.record(AuditEvent(
        tenant_id=s["tid"],
        actor_user_id=orphan_actor_id,
        accion=AuditAction.ESTRUCTURA_GESTIONAR,
        modulo="estructura",
        entidad_tipo="Carrera",
        entidad_id=None,
        resultado=AuditResultado.ok,
    ))
    await session.commit()
    await session.close()

    # Authenticate as known admin (auth_identity_id)
    token = _make_jwt(s["tid"], s["auth_identity_id"], [s["rol_nombre"]])

    async with AsyncClient(
        transport=ASGITransport(app=enrich_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Find the orphan event
    orphan_events = [
        e for e in data
        if e["actor_user_id"] == str(orphan_actor_id)
    ]
    assert orphan_events, "Expected orphan event in response"
    assert orphan_events[0]["actor_nombre"] is None, (
        "Orphan actor (no matching usuario) must return actor_nombre=None"
    )


# ---------------------------------------------------------------------------
# E.3 TRIANGULATE: unresolvable entidad_tipo → entidad_nombre is None
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_enrich_unresolvable_entidad_tipo_returns_none(
    monkeypatch, test_engine, enrich_app, enrich_setup
):
    """
    E.3: An AuditEvent with entidad_tipo='AuditEvent' (not Materia/Carrera/Cohorte)
    → entidad_nombre is None.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = enrich_setup

    # Seed event with an unresolvable entidad_tipo
    factory = build_session_factory(test_engine)
    session = factory()
    repo = AuditRepository(session=session, tenant_id=s["tid"])
    await repo.record(AuditEvent(
        tenant_id=s["tid"],
        actor_user_id=s["auth_identity_id"],
        accion=AuditAction.AUDITORIA_CONSULTA,
        modulo="auditoria",
        entidad_tipo="AuditEvent",
        entidad_id=str(uuid.uuid4()),
        resultado=AuditResultado.ok,
    ))
    await session.commit()
    await session.close()

    token = _make_jwt(s["tid"], s["auth_identity_id"], [s["rol_nombre"]])

    async with AsyncClient(
        transport=ASGITransport(app=enrich_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # All AuditEvent-tipo events must have entidad_nombre=None
    audit_events = [e for e in data if e["entidad_tipo"] == "AuditEvent"]
    assert audit_events, "Expected at least one AuditEvent-tipo event"
    for e in audit_events:
        assert e["entidad_nombre"] is None, (
            f"Unresolvable entidad_tipo should return entidad_nombre=None, got {e['entidad_nombre']}"
        )


# ---------------------------------------------------------------------------
# E.4 RED→GREEN: interacciones-docente metric → actor_nombre resolved
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_enrich_interacciones_docente_actor_nombre(
    monkeypatch, test_engine, enrich_app, enrich_setup
):
    """
    E.4: GET /metricas/interacciones-docente returns actor_nombre for known actor.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = enrich_setup

    token = _make_jwt(s["tid"], s["auth_identity_id"], [s["rol_nombre"]])

    async with AsyncClient(
        transport=ASGITransport(app=enrich_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria/metricas/interacciones-docente",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Find the item for our known actor
    known_items = [
        item for item in data["items"]
        if item["actor_user_id"] == str(s["auth_identity_id"])
    ]
    assert known_items, "Expected at least one metric item for the known actor"
    assert known_items[0]["actor_nombre"] == s["nombre_completo"], (
        f"Expected actor_nombre='{s['nombre_completo']}', got '{known_items[0]['actor_nombre']}'"
    )


# ---------------------------------------------------------------------------
# E.5 TRIANGULATE: interacciones-docente-materia → actor_nombre + materia_nombre
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="function")
async def test_enrich_interacciones_docente_materia_nombres(
    monkeypatch, test_engine, enrich_app, enrich_setup
):
    """
    E.5: GET /metricas/interacciones-docente-materia returns both actor_nombre
    and materia_nombre for known actor + materia combination.
    """
    monkeypatch.setattr("app.core.security.tokens._settings", _fake_settings)
    s = enrich_setup

    token = _make_jwt(s["tid"], s["auth_identity_id"], [s["rol_nombre"]])

    async with AsyncClient(
        transport=ASGITransport(app=enrich_app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auditoria/metricas/interacciones-docente-materia",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Find item for our known actor + materia
    materia_id_str = str(s["materia_id"])
    known_items = [
        item for item in data["items"]
        if item["actor_user_id"] == str(s["auth_identity_id"])
        and item["materia_id"] == materia_id_str
    ]
    assert known_items, (
        f"Expected an item for actor={s['auth_identity_id']} materia={materia_id_str}"
    )
    item = known_items[0]
    assert item["actor_nombre"] == s["nombre_completo"], (
        f"Expected actor_nombre='{s['nombre_completo']}', got '{item['actor_nombre']}'"
    )
    assert item["materia_nombre"] == s["materia_nombre"], (
        f"Expected materia_nombre='{s['materia_nombre']}', got '{item['materia_nombre']}'"
    )
