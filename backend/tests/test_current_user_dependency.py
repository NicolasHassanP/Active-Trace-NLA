"""
Tests for get_current_user dependency and tenancy factory.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Tasks 11.1-11.3
"""
import uuid
import pytest


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
    "SECRET_KEY": "supersecretkeyfortesting1234567890",
    "ENCRYPTION_KEY": "E" * 32,
}


def setup_env(monkeypatch):
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)


# ==============================================================================
# 11.1 get_current_user — resolves CurrentUser from valid JWT
# ==============================================================================

@pytest.mark.asyncio(loop_scope="function")
async def test_get_current_user_valid_token(monkeypatch):
    """Valid access token returns CurrentUser with correct user_id, tenant_id, roles."""
    setup_env(monkeypatch)
    from fastapi import Request
    from app.core.dependencies import get_current_user
    from app.core.security import encode_access_token

    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    roles = ["COORDINADOR"]
    token = encode_access_token(user_id=user_id, tenant_id=tenant_id, roles=roles)

    # Build a mock request with the Authorization header
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    request = Request(scope)

    current_user = await get_current_user(request)
    assert current_user.user_id == user_id
    assert current_user.tenant_id == tenant_id
    assert current_user.roles == roles


@pytest.mark.asyncio(loop_scope="function")
async def test_get_current_user_missing_header_raises_401(monkeypatch):
    """Missing Authorization header raises HTTPException 401."""
    setup_env(monkeypatch)
    from fastapi import Request
    from fastapi.exceptions import HTTPException
    from app.core.dependencies import get_current_user

    scope = {"type": "http", "headers": []}
    request = Request(scope)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_get_current_user_expired_token_raises_401(monkeypatch):
    """Expired access token raises HTTPException 401."""
    setup_env(monkeypatch)
    from fastapi import Request
    from fastapi.exceptions import HTTPException
    from app.core.dependencies import get_current_user
    from app.core.security import encode_access_token

    token = encode_access_token(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=[], expires_minutes=-1
    )
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    request = Request(scope)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio(loop_scope="function")
async def test_get_current_user_wrong_type_raises_401(monkeypatch):
    """MFA token (type='mfa') passed as access token raises 401."""
    setup_env(monkeypatch)
    from fastapi import Request
    from fastapi.exceptions import HTTPException
    from app.core.dependencies import get_current_user
    from app.core.security import encode_mfa_token

    token = encode_mfa_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    request = Request(scope)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request)
    assert exc_info.value.status_code == 401


# ==============================================================================
# 11.2 Immutable identity — parameters in body/header are ignored
# ==============================================================================

def test_current_user_value_object_is_immutable(monkeypatch):
    """CurrentUser fields cannot be modified (frozen dataclass/NamedTuple)."""
    setup_env(monkeypatch)
    from app.core.dependencies import CurrentUser

    user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), roles=["ADMIN"])
    with pytest.raises((AttributeError, TypeError)):
        user.user_id = uuid.uuid4()  # type: ignore


# ==============================================================================
# 11.3 Tenancy factory — builds scoped repo from CurrentUser
# ==============================================================================

def test_build_scoped_repository_uses_current_user_tenant(monkeypatch):
    """build_scoped_repository uses the tenant_id from CurrentUser, not request."""
    setup_env(monkeypatch)
    from unittest.mock import MagicMock
    from app.core.tenancy import build_scoped_repository
    from app.core.dependencies import CurrentUser
    from app.models.auth import AuthIdentity

    session = MagicMock()
    tenant_id = uuid.uuid4()
    current_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=tenant_id, roles=[])

    repo = build_scoped_repository(AuthIdentity, session, current_user.tenant_id)
    assert repo._tenant_id == tenant_id
