"""
test_impersonacion_router.py — TDD tests for impersonación endpoints.

Dominio: CRÍTICO (auth + auditoría).

Coverage:
  1. ADMIN puede impersonar → recibe token con impersonated_user_id en claims.
  2. Non-ADMIN no puede impersonar → 403.
  3. Impersonar usuario de otro tenant → 404.
  4. Impersonar a sí mismo → 400.
  5. Finalizar sin sesión activa → 400.
  6. Finalizar con sesión activa → token limpio sin impersonated_user_id.
  7. Auditoría registrada en inicio y fin.

Reglas duras:
  - DB real (activia_trace_test). Sin mocks de DB (regla #4).
  - Identidad SIEMPRE desde JWT. Nunca desde parámetros.
  - Multi-tenancy: target en el mismo tenant que actor.
  - create_usuario_con_identidad (conftest helper) para crear usuarios de test.

Ciclo TDD: Safety Net → RED → GREEN → TRIANGULATE → REFACTOR.
"""
import datetime
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt
from sqlalchemy import text

from app.core.database import build_session_factory
from app.models.rbac import Permiso, PermisoScope, Rol, RolPermiso
from app.models.tenant import Tenant, TenantEstado

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "supersecretkeyfortesting1234567890"
TEST_ENCRYPTION_KEY = "E" * 32


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _make_jwt(
    tenant_id: uuid.UUID,
    auth_identity_id: uuid.UUID,
    roles: list,
    *,
    impersonated_user_id: uuid.UUID | None = None,
    impersonated_name: str | None = None,
) -> str:
    """Build a valid access JWT for tests. Includes optional impersonation claims."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    exp = now + datetime.timedelta(minutes=30)
    payload = {
        "sub": str(auth_identity_id),
        "tenant_id": str(tenant_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
    }
    if impersonated_user_id is not None:
        payload["impersonated_user_id"] = str(impersonated_user_id)
        payload["impersonated_name"] = impersonated_name or ""
    return jose_jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")


def _decode_jwt(token: str) -> dict:
    """Decode a JWT without verification (for test assertions)."""
    return jose_jwt.decode(
        token,
        TEST_SECRET_KEY,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def imp_setup(test_engine, create_tables):
    """
    Set up two tenants with RBAC for impersonation tests.

    tenant_main:
      - admin_usuario    → ADMIN (has impersonacion:usar + usuarios:gestionar)
      - target_usuario   → PROFESOR (is the user to impersonate)
      - nonadmin_usuario → PROFESOR (no impersonacion:usar)

    tenant_other:
      - other_usuario  → any role (for cross-tenant 404 test)

    Returns dict with all relevant IDs for test use.
    """
    import os
    os.environ.update({
        "SECRET_KEY": TEST_SECRET_KEY,
        "ENCRYPTION_KEY": TEST_ENCRYPTION_KEY,
    })

    from tests.conftest import create_usuario_con_identidad

    factory = build_session_factory(test_engine)
    session = factory()

    # --- tenant_main ---
    tid_main = uuid.uuid4()
    session.add(Tenant(id=tid_main, nombre="Imp Main Tenant", estado=TenantEstado.ACTIVO))
    await session.flush()

    # --- tenant_other ---
    tid_other = uuid.uuid4()
    session.add(Tenant(id=tid_other, nombre="Imp Other Tenant", estado=TenantEstado.ACTIVO))
    await session.flush()
    await session.commit()

    # Create users in tenant_main
    admin_usuario = await create_usuario_con_identidad(
        session, tid_main, nombre="Admin", apellidos="User", roles=["ADMIN"]
    )
    target_usuario = await create_usuario_con_identidad(
        session, tid_main, nombre="Target", apellidos="User", roles=["PROFESOR"]
    )
    nonadmin_usuario = await create_usuario_con_identidad(
        session, tid_main, nombre="NonAdmin", apellidos="User", roles=["PROFESOR"]
    )
    # Create user in tenant_other (for cross-tenant test)
    other_usuario = await create_usuario_con_identidad(
        session, tid_other, nombre="Other", apellidos="User", roles=["PROFESOR"]
    )
    await session.commit()

    # --- Seed RBAC for tenant_main ---
    # Roles
    rol_admin = Rol(tenant_id=tid_main, nombre="IMP_ADMIN")
    rol_prof = Rol(tenant_id=tid_main, nombre="IMP_PROFESOR")
    session.add_all([rol_admin, rol_prof])
    await session.flush()

    # Permissions
    perm_imp = Permiso(
        tenant_id=tid_main,
        codigo="impersonacion:usar",
        modulo="impersonacion",
        accion="usar",
    )
    session.add(perm_imp)
    await session.flush()

    # Grant impersonacion:usar to ADMIN only
    session.add(RolPermiso(
        tenant_id=tid_main,
        rol_id=rol_admin.id,
        permiso_id=perm_imp.id,
        scope=PermisoScope.global_,
    ))
    await session.commit()
    await session.close()

    yield {
        "tid_main": tid_main,
        "tid_other": tid_other,
        "admin_usuario": admin_usuario,
        "target_usuario": target_usuario,
        "nonadmin_usuario": nonadmin_usuario,
        "other_usuario": other_usuario,
    }

    # Teardown — cleanup in reverse FK order
    factory2 = build_session_factory(test_engine)
    session2 = factory2()
    from tests.conftest import delete_audit_events_for_tenant
    await delete_audit_events_for_tenant(session2, tid_main)
    await delete_audit_events_for_tenant(session2, tid_other)
    await session2.execute(text("DELETE FROM rol_permiso WHERE tenant_id = :tid"), {"tid": str(tid_main)})
    await session2.execute(text("DELETE FROM permiso WHERE tenant_id = :tid"), {"tid": str(tid_main)})
    await session2.execute(text("DELETE FROM rol WHERE tenant_id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.execute(text("DELETE FROM asignacion WHERE tenant_id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.execute(text("DELETE FROM usuario WHERE tenant_id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.execute(text("DELETE FROM refresh_sessions WHERE tenant_id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.execute(text("DELETE FROM password_recovery_tokens WHERE tenant_id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.execute(text("DELETE FROM auth_identities WHERE tenant_id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.execute(text("DELETE FROM tenants WHERE id IN (:tid1, :tid2)"),
                           {"tid1": str(tid_main), "tid2": str(tid_other)})
    await session2.commit()
    await session2.close()


@pytest_asyncio.fixture(scope="module")
async def imp_client(test_app, imp_setup) -> AsyncClient:
    """AsyncClient wired to the test app for impersonation tests."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _admin_token(s: dict) -> str:
    """JWT for the ADMIN user in tenant_main."""
    return _make_jwt(
        s["tid_main"],
        s["admin_usuario"].auth_identity_id,
        ["IMP_ADMIN"],
    )


def _nonadmin_token(s: dict) -> str:
    """JWT for the non-ADMIN user in tenant_main (no impersonacion:usar)."""
    return _make_jwt(
        s["tid_main"],
        s["nonadmin_usuario"].auth_identity_id,
        ["IMP_PROFESOR"],
    )


# ==============================================================================
# Safety Net — run before touching impersonation code
# (these use auth test fixtures and verify existing tests still pass)
# ==============================================================================
# The actual safety net is to run test_auth_router.py first.
# Here we verify the app starts and health is ok.

@pytest.mark.asyncio(loop_scope="session")
async def test_safety_net_health(imp_client):
    """Verify app health endpoint is reachable (safety net)."""
    resp = await imp_client.get("/health")
    assert resp.status_code == 200


# ==============================================================================
# Task 1 — RED → GREEN: ADMIN puede impersonar, recibe token con claims
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_admin_puede_impersonar_token_con_claims(imp_client, imp_setup):
    """
    RED → GREEN: ADMIN con impersonacion:usar recibe token con impersonated_user_id.

    Verifica:
      - status 200
      - access_token presente en respuesta
      - impersonated_name presente
      - el JWT emitido contiene impersonated_user_id == target_usuario.id
      - el JWT emitido preserva sub == admin.auth_identity_id (actor real)
    """
    s = imp_setup
    token = _admin_token(s)
    target_id = s["target_usuario"].id

    resp = await imp_client.post(
        f"/api/v1/usuarios/{target_id}/impersonar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"Missing access_token: {data}"
    assert "impersonated_name" in data, f"Missing impersonated_name: {data}"

    # Decode the emitted token and verify claims
    emitted_claims = _decode_jwt(data["access_token"])
    assert emitted_claims["sub"] == str(s["admin_usuario"].auth_identity_id), (
        "sub must be the real actor's auth_identity_id"
    )
    assert "impersonated_user_id" in emitted_claims, (
        f"Expected impersonated_user_id in claims: {emitted_claims}"
    )
    assert emitted_claims["impersonated_user_id"] == str(target_id), (
        f"Expected {target_id}, got {emitted_claims['impersonated_user_id']}"
    )
    assert "Target" in data["impersonated_name"], (
        f"Expected target name in impersonated_name: {data['impersonated_name']}"
    )


# ==============================================================================
# Task 2 — TRIANGULATE: Non-ADMIN no puede impersonar → 403
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_nonadmin_no_puede_impersonar_403(imp_client, imp_setup):
    """
    TRIANGULATE: usuario sin impersonacion:usar → 403 fail-closed.
    """
    s = imp_setup
    token = _nonadmin_token(s)
    target_id = s["target_usuario"].id

    resp = await imp_client.post(
        f"/api/v1/usuarios/{target_id}/impersonar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio(loop_scope="session")
async def test_no_jwt_impersonar_401(imp_client, imp_setup):
    """
    TRIANGULATE: sin JWT → 401 (identity check before permission check).
    """
    s = imp_setup
    target_id = s["target_usuario"].id

    resp = await imp_client.post(f"/api/v1/usuarios/{target_id}/impersonar")

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


# ==============================================================================
# Task 3 — TRIANGULATE: Impersonar usuario de otro tenant → 404
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_impersonar_otro_tenant_404(imp_client, imp_setup):
    """
    TRIANGULATE: actor en tenant_main intenta impersonar usuario en tenant_other → 404.

    El UsuarioRepository está scoped al tenant del actor, por lo que el usuario
    de otro tenant es invisible → UsuarioNoEncontrado → 404.
    """
    s = imp_setup
    token = _admin_token(s)
    other_id = s["other_usuario"].id  # belongs to tid_other

    resp = await imp_client.post(
        f"/api/v1/usuarios/{other_id}/impersonar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ==============================================================================
# Task 4 — TRIANGULATE: Impersonar a sí mismo → 400
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_impersonar_si_mismo_400(imp_client, imp_setup):
    """
    TRIANGULATE: ADMIN intenta impersonarse a sí mismo → 400.

    El endpoint compara auth_identity_id del target con el sub del actor.
    Si coinciden → AutoImpersonacionProhibida → 400.
    """
    s = imp_setup
    # admin_usuario.auth_identity_id is the actor's user_id in the JWT
    # We need the domain usuario.id of the admin
    admin_domain_id = s["admin_usuario"].id
    token = _admin_token(s)

    resp = await imp_client.post(
        f"/api/v1/usuarios/{admin_domain_id}/impersonar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "impersonars" in resp.text.lower() or "sí mismo" in resp.text.lower() or "mismo" in resp.text.lower(), (
        f"Expected self-impersonation message: {resp.text}"
    )


# ==============================================================================
# Task 5 — TRIANGULATE: Finalizar sin sesión activa → 400
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_finalizar_sin_sesion_400(imp_client, imp_setup):
    """
    TRIANGULATE: token sin impersonated_user_id claim → 400.

    Un token normal (sin impersonación) no puede finalizar algo que no existe.
    """
    s = imp_setup
    # Normal admin token — no impersonation claims
    token = _admin_token(s)

    resp = await imp_client.post(
        "/api/v1/auth/impersonacion/finalizar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "impersonaci" in resp.text.lower() or "activa" in resp.text.lower(), (
        f"Expected 'no session active' message: {resp.text}"
    )


# ==============================================================================
# Task 6 — TRIANGULATE: Finalizar con sesión activa → token limpio
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_finalizar_con_sesion_activa_token_limpio(imp_client, imp_setup):
    """
    TRIANGULATE: token con impersonated_user_id claim → token limpio emitido.

    Verifica:
      - status 200
      - access_token en respuesta
      - el JWT emitido NO contiene impersonated_user_id
      - el JWT emitido preserva sub == actor real (admin.auth_identity_id)
    """
    s = imp_setup
    target_id = s["target_usuario"].id

    # Build an impersonation token manually (as if returned by /impersonar)
    imp_token = _make_jwt(
        s["tid_main"],
        s["admin_usuario"].auth_identity_id,
        ["PROFESOR"],  # impersonated user's roles
        impersonated_user_id=target_id,
        impersonated_name="Target User",
    )

    resp = await imp_client.post(
        "/api/v1/auth/impersonacion/finalizar",
        headers={"Authorization": f"Bearer {imp_token}"},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"Missing access_token: {data}"

    # Verify the returned token is clean (no impersonation claims)
    clean_claims = _decode_jwt(data["access_token"])
    assert "impersonated_user_id" not in clean_claims, (
        f"Clean token must NOT contain impersonated_user_id: {clean_claims}"
    )
    assert clean_claims["sub"] == str(s["admin_usuario"].auth_identity_id), (
        "sub must be the real actor's auth_identity_id"
    )


# ==============================================================================
# Task 7 — TRIANGULATE: Auditoría registrada en inicio y fin
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_auditoria_registrada_inicio(imp_client, imp_setup, db_session):
    """
    TRIANGULATE: IMPERSONACION_INICIO auditado al impersonar.

    Verifica que se inserta un AuditEvent con accion=IMPERSONACION_INICIO
    y entidad_id == str(target_usuario.id) en el tenant del actor.
    """
    from sqlalchemy import select
    from app.models.audit import AuditAction, AuditEvent

    s = imp_setup
    token = _admin_token(s)
    target_id = s["target_usuario"].id

    # Count events before
    result_before = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == s["tid_main"],
            AuditEvent.accion == AuditAction.IMPERSONACION_INICIO,
            AuditEvent.entidad_id == str(target_id),
        )
    )
    count_before = len(list(result_before.scalars().all()))

    # Perform impersonation
    resp = await imp_client.post(
        f"/api/v1/usuarios/{target_id}/impersonar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Impersonation failed: {resp.text}"

    # Verify audit event created
    result_after = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == s["tid_main"],
            AuditEvent.accion == AuditAction.IMPERSONACION_INICIO,
            AuditEvent.entidad_id == str(target_id),
        )
    )
    events_after = list(result_after.scalars().all())
    assert len(events_after) > count_before, (
        f"Expected IMPERSONACION_INICIO audit event, got {len(events_after)} (was {count_before})"
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_auditoria_registrada_fin(imp_client, imp_setup, db_session):
    """
    TRIANGULATE: IMPERSONACION_FIN auditado al finalizar.

    Verifica que se inserta un AuditEvent con accion=IMPERSONACION_FIN
    en el tenant del actor.
    """
    from sqlalchemy import select
    from app.models.audit import AuditAction, AuditEvent

    s = imp_setup
    target_id = s["target_usuario"].id

    # Count events before
    result_before = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == s["tid_main"],
            AuditEvent.accion == AuditAction.IMPERSONACION_FIN,
        )
    )
    count_before = len(list(result_before.scalars().all()))

    # Use an impersonation token to finalize
    imp_token = _make_jwt(
        s["tid_main"],
        s["admin_usuario"].auth_identity_id,
        ["PROFESOR"],
        impersonated_user_id=target_id,
        impersonated_name="Target User",
    )
    resp = await imp_client.post(
        "/api/v1/auth/impersonacion/finalizar",
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 200, f"Finalizar failed: {resp.text}"

    # Verify audit event created
    result_after = await db_session.execute(
        select(AuditEvent).where(
            AuditEvent.tenant_id == s["tid_main"],
            AuditEvent.accion == AuditAction.IMPERSONACION_FIN,
        )
    )
    events_after = list(result_after.scalars().all())
    assert len(events_after) > count_before, (
        f"Expected IMPERSONACION_FIN audit event, got {len(events_after)} (was {count_before})"
    )


# ==============================================================================
# Task 8 — TRIANGULATE: Roles del target en el token de impersonación
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_impersonacion_token_lleva_roles_del_target(imp_client, imp_setup):
    """
    TRIANGULATE: el token de impersonación lleva los roles del usuario target,
    no los del actor.

    El target_usuario tiene roles=["PROFESOR"] en su AuthIdentity.
    El actor (admin) tiene roles=["ADMIN"]. El token emitido debe tener
    los roles del target.
    """
    s = imp_setup
    token = _admin_token(s)
    target_id = s["target_usuario"].id

    resp = await imp_client.post(
        f"/api/v1/usuarios/{target_id}/impersonar",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    emitted_claims = _decode_jwt(data["access_token"])

    # The token should carry the TARGET's roles, not ADMIN
    emitted_roles = emitted_claims.get("roles", [])
    assert "PROFESOR" in emitted_roles, (
        f"Expected target roles (PROFESOR) in impersonation token, got {emitted_roles}"
    )
    # ADMIN role should NOT be in the impersonation token (it belongs to the actor)
    assert "ADMIN" not in emitted_roles, (
        f"Actor's ADMIN role must not be present in impersonation token: {emitted_roles}"
    )
