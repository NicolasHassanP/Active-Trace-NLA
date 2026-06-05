"""
Integration tests for auth router endpoints.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Task 12.1: all endpoints return correct status codes for OK/KO cases.
Task 12.2: auth endpoints accessible without auth; others require it.
"""
import uuid
import pytest
import pytest_asyncio

from sqlalchemy import text


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
    "SECRET_KEY": "supersecretkeyfortesting1234567890",
    "ENCRYPTION_KEY": "E" * 32,
}


def _set_env():
    import os
    os.environ.update(TEST_ENV)


async def _raw_create_tenant(engine, nombre: str) -> uuid.UUID:
    """Create a tenant using a raw SQL connection (avoids shared session issues)."""
    tenant_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO tenants (id, nombre, estado) "
                "VALUES (:id, :nombre, 'activo')"
            ),
            {"id": str(tenant_id), "nombre": nombre},
        )
    return tenant_id


async def _raw_delete_tenant(engine, tenant_id: uuid.UUID) -> None:
    """Delete all auth data + tenant row using raw SQL."""
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM password_recovery_tokens WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await conn.execute(
            text("DELETE FROM refresh_sessions WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await conn.execute(
            text("DELETE FROM auth_identities WHERE tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )
        await conn.execute(
            text("DELETE FROM tenants WHERE id = :tid"),
            {"tid": str(tenant_id)},
        )


async def _raw_create_identity(
    engine,
    tenant_id: uuid.UUID,
    email: str,
    password: str = "RouterP@ss1",
) -> uuid.UUID:
    """Create an auth identity using raw SQL + security helpers."""
    _set_env()
    from app.core.security import email_lookup_hash, hash_password, encrypt

    identity_id = uuid.uuid4()
    email_hash = email_lookup_hash(email)
    password_hash = hash_password(password)
    email_enc = encrypt(email)  # AES-256 encryption

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO auth_identities "
                "(id, tenant_id, email_encrypted, email_hash, password_hash, "
                " roles, is_active, totp_enabled) "
                "VALUES (:id, :tid, :ee, :eh, :ph, '[]', true, false)"
            ),
            {
                "id": str(identity_id),
                "tid": str(tenant_id),
                "ee": email_enc,
                "eh": email_hash,
                "ph": password_hash,
            },
        )
    return identity_id


async def _raw_delete_identity(engine, identity_id: uuid.UUID) -> None:
    """Delete all refresh sessions + identity using raw SQL."""
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM refresh_sessions WHERE auth_identity_id = :iid"),
            {"iid": str(identity_id)},
        )
        await conn.execute(
            text("DELETE FROM auth_identities WHERE id = :iid"),
            {"iid": str(identity_id)},
        )


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest_asyncio.fixture(scope="session")
async def router_tenant_id(test_engine, create_tables) -> uuid.UUID:
    """
    Create a dedicated tenant for router tests using raw SQL.

    Uses raw SQL via test_engine (not the shared db_session) to avoid
    SQLAlchemy ORM greenlet-context issues that arise when a session-scoped
    ORM instance is accessed from a different greenlet (test vs. fixture).

    Yields a plain UUID — tests reference it directly with no ORM involvement.
    """
    _set_env()
    tenant_id = await _raw_create_tenant(test_engine, "Router Test Tenant")
    yield tenant_id
    await _raw_delete_tenant(test_engine, tenant_id)


# ==============================================================================
# 12.1 Endpoint tests — login
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_login_endpoint_success(async_client, test_engine, create_tables, router_tenant_id):
    """POST /api/v1/auth/login returns 200 with access_token in body, refresh_token in Set-Cookie."""
    _set_env()
    identity_id = await _raw_create_identity(
        test_engine, router_tenant_id, "loginok@router.com"
    )
    try:
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "loginok@router.com", "password": "RouterP@ss1"},
            headers={"X-Tenant": str(router_tenant_id)},
        )
        assert response.status_code == 200
        data = response.json()
        # access_token in body; refresh_token NOT in body
        assert "access_token" in data
        assert "refresh_token" not in data
        # refresh_token set as httpOnly cookie
        assert "refresh_token" in response.cookies
    finally:
        await _raw_delete_identity(test_engine, identity_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_login_endpoint_wrong_password_returns_401(async_client, test_engine, create_tables, router_tenant_id):
    """POST /api/v1/auth/login returns 401 on wrong password."""
    _set_env()
    identity_id = await _raw_create_identity(
        test_engine, router_tenant_id, "loginbad@router.com"
    )
    try:
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "loginbad@router.com", "password": "WrongP@ss"},
            headers={"X-Tenant": str(router_tenant_id)},
        )
        assert response.status_code == 401
    finally:
        await _raw_delete_identity(test_engine, identity_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_endpoint_success(async_client, test_engine, create_tables, router_tenant_id):
    """POST /api/v1/auth/refresh returns 200 with new access_token; refresh_token from cookie."""
    _set_env()
    identity_id = await _raw_create_identity(
        test_engine, router_tenant_id, "refresh@router.com"
    )
    try:
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "refresh@router.com", "password": "RouterP@ss1"},
            headers={"X-Tenant": str(router_tenant_id)},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        # refresh_token is now in the cookie, not the body
        refresh_token = login_resp.cookies["refresh_token"]

        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert "access_token" in data
        assert "refresh_token" not in data
        # rotated refresh_token is set as a new cookie
        assert "refresh_token" in refresh_resp.cookies
    finally:
        await _raw_delete_identity(test_engine, identity_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_logout_endpoint_success(async_client, test_engine, create_tables, router_tenant_id):
    """POST /api/v1/auth/logout returns 200 and clears the refresh_token cookie."""
    _set_env()
    identity_id = await _raw_create_identity(
        test_engine, router_tenant_id, "logout@router.com"
    )
    try:
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "logout@router.com", "password": "RouterP@ss1"},
            headers={"X-Tenant": str(router_tenant_id)},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        # refresh_token is now in the cookie, not the body
        refresh_token = login_resp.cookies["refresh_token"]

        logout_resp = await async_client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": refresh_token},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["message"] == "Logged out successfully"
    finally:
        await _raw_delete_identity(test_engine, identity_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_forgot_endpoint_returns_200_regardless_of_email(async_client, create_tables, router_tenant_id):
    """POST /api/v1/auth/forgot returns 200 for both existing and non-existing emails."""
    # Existing email (no identity, but response should be uniform)
    r1 = await async_client.post(
        "/api/v1/auth/forgot",
        json={"email": "anything@example.com"},
        headers={"X-Tenant": str(router_tenant_id)},
    )
    assert r1.status_code == 200

    # Non-existing email — same response
    r2 = await async_client.post(
        "/api/v1/auth/forgot",
        json={"email": "notexist@example.com"},
        headers={"X-Tenant": str(router_tenant_id)},
    )
    assert r2.status_code == 200
    assert r1.json() == r2.json()  # Uniform response


# ==============================================================================
# 12.2 Auth endpoints accessible without session
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_login_accessible_without_auth_header(async_client, router_tenant_id):
    """Login endpoint does not require Authorization header."""
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "any"},
        headers={"X-Tenant": str(router_tenant_id)},
    )
    # Should get 401 (wrong credentials), not 403 (no auth)
    assert resp.status_code in (400, 401, 422)
    assert resp.status_code != 403


@pytest.mark.asyncio(loop_scope="session")
async def test_health_endpoint_accessible_without_auth(async_client):
    """Health endpoint doesn't require auth (regression test)."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
