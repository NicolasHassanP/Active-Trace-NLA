"""
Tests for AuthService: login, refresh rotation, 2FA, password recovery.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Tasks 6.1-9.2
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
    "SECRET_KEY": "supersecretkeyfortesting1234567890",
    "ENCRYPTION_KEY": "E" * 32,
}


def setup_env(monkeypatch):
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)


async def make_tenant_and_identity(db_session, email="svc@example.com", is_active=True, totp_enabled=False):
    """Helper to create a Tenant + AuthIdentity with known credentials."""
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity
    from app.core.security import email_lookup_hash, hash_password

    tenant = Tenant(nombre=f"SvcTenant-{uuid.uuid4().hex[:6]}", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    identity = AuthIdentity(
        tenant_id=tenant.id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        password_hash=hash_password("CorrectP@ss1"),
        roles=["COORDINADOR"],
        is_active=is_active,
        totp_enabled=totp_enabled,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)
    return tenant, identity


# ==============================================================================
# 6.1 login — credential validation
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_login_success_returns_token_pair(db_session, create_tables, monkeypatch):
    """Successful login returns access_token + refresh_token."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "login_ok@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    result = await svc.login(
        email="login_ok@example.com", password="CorrectP@ss1", tenant_id=tenant.id
    )
    assert result["access_token"] is not None
    assert result["refresh_token"] is not None
    assert result["token_type"] == "bearer"

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession, AuthIdentity
    await db_session.execute(delete(RefreshSession).where(RefreshSession.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_login_wrong_password_raises(db_session, create_tables, monkeypatch):
    """Wrong password raises AuthenticationError."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService, AuthenticationError
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "login_bad@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    with pytest.raises(AuthenticationError):
        await svc.login(email="login_bad@example.com", password="WrongP@ss", tenant_id=tenant.id)

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import AuthIdentity
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_login_nonexistent_email_raises(db_session, create_tables, monkeypatch):
    """Nonexistent email raises AuthenticationError (no user enumeration)."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService, AuthenticationError
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "login_exists@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    with pytest.raises(AuthenticationError):
        await svc.login(email="noexist@example.com", password="AnyP@ss", tenant_id=tenant.id)

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import AuthIdentity
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_login_inactive_user_raises(db_session, create_tables, monkeypatch):
    """Inactive user raises AuthenticationError even with correct password."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService, AuthenticationError
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "login_inactive@example.com", is_active=False)
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    with pytest.raises(AuthenticationError):
        await svc.login(email="login_inactive@example.com", password="CorrectP@ss1", tenant_id=tenant.id)

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import AuthIdentity
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


# ==============================================================================
# 7.1-7.4 refresh rotation + logout
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_rotation_returns_new_pair(db_session, create_tables, monkeypatch):
    """refresh() returns a new token pair and marks old session as rotated."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "refresh_ok@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    login_result = await svc.login(
        email="refresh_ok@example.com", password="CorrectP@ss1", tenant_id=tenant.id
    )
    old_refresh = login_result["refresh_token"]

    new_pair = await svc.refresh(old_refresh)
    assert new_pair["access_token"] is not None
    assert new_pair["refresh_token"] != old_refresh

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession, AuthIdentity
    await db_session.execute(delete(RefreshSession).where(RefreshSession.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_reuse_revokes_family(db_session, create_tables, monkeypatch):
    """Reusing a consumed refresh token revokes the whole family → 401."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService, AuthenticationError
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "reuse_test@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    login_result = await svc.login(
        email="reuse_test@example.com", password="CorrectP@ss1", tenant_id=tenant.id
    )
    old_refresh = login_result["refresh_token"]

    # Use it once (legitimate rotation)
    new_pair = await svc.refresh(old_refresh)

    # Try to reuse the old refresh → should revoke family and raise
    with pytest.raises(AuthenticationError):
        await svc.refresh(old_refresh)

    # The new refresh from legitimate rotation is also now invalid (family revoked)
    with pytest.raises(AuthenticationError):
        await svc.refresh(new_pair["refresh_token"])

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession, AuthIdentity
    await db_session.execute(delete(RefreshSession).where(RefreshSession.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_logout_revokes_session(db_session, create_tables, monkeypatch):
    """logout() marks the session revoked; subsequent refresh raises."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService, AuthenticationError
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "logout_test@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    login_result = await svc.login(
        email="logout_test@example.com", password="CorrectP@ss1", tenant_id=tenant.id
    )
    refresh_token = login_result["refresh_token"]

    await svc.logout(refresh_token)

    with pytest.raises(AuthenticationError):
        await svc.refresh(refresh_token)

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession, AuthIdentity
    await db_session.execute(delete(RefreshSession).where(RefreshSession.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


# ==============================================================================
# 8.1-8.4 2FA
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_enroll_2fa_stores_encrypted_secret(db_session, create_tables, monkeypatch):
    """enroll_2fa stores encrypted TOTP secret, totp_enabled stays False."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository
    from sqlalchemy import text

    tenant, identity = await make_tenant_and_identity(db_session, "enroll2fa@example.com")
    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    result = await svc.enroll_2fa(identity)
    assert "secret" in result
    assert "uri" in result
    assert result["uri"].startswith("otpauth://")

    # Reload and check
    await db_session.refresh(identity)
    assert identity.totp_enabled is False
    assert identity.totp_secret_encrypted is not None  # ORM: plaintext (transparent decrypt)

    # Raw DB value should be different from plaintext secret
    raw = await db_session.execute(
        text("SELECT totp_secret_encrypted FROM auth_identities WHERE id = :id"),
        {"id": str(identity.id)},
    )
    raw_val = raw.scalar()
    assert raw_val != result["secret"]

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import AuthIdentity
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_login_with_2fa_returns_mfa_challenge(db_session, create_tables, monkeypatch):
    """Login with totp_enabled=True returns mfa_token, not a token pair."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "login2fa@example.com", totp_enabled=True)
    # Need to set a totp_secret
    from app.core.security import generate_totp_secret
    identity.totp_secret_encrypted = generate_totp_secret()
    await db_session.commit()
    await db_session.refresh(identity)

    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    result = await svc.login(
        email="login2fa@example.com", password="CorrectP@ss1", tenant_id=tenant.id
    )
    assert result.get("mfa_required") is True
    assert "mfa_token" in result
    assert "access_token" not in result
    assert "refresh_token" not in result

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import AuthIdentity
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_complete_mfa_with_valid_code_returns_session(db_session, create_tables, monkeypatch):
    """complete_mfa with valid code emits access + refresh pair."""
    setup_env(monkeypatch)
    import pyotp
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository
    from app.core.security import generate_totp_secret, encode_mfa_token

    tenant, identity = await make_tenant_and_identity(db_session, "mfa_complete@example.com", totp_enabled=True)
    secret = generate_totp_secret()
    identity.totp_secret_encrypted = secret
    await db_session.commit()
    await db_session.refresh(identity)

    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=None,
    )
    mfa_token = encode_mfa_token(user_id=identity.id, tenant_id=tenant.id)
    code = pyotp.TOTP(secret).now()
    result = await svc.complete_mfa(mfa_token=mfa_token, code=code, tenant_id=tenant.id)

    assert "access_token" in result
    assert "refresh_token" in result

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession, AuthIdentity
    await db_session.execute(delete(RefreshSession).where(RefreshSession.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


# ==============================================================================
# 9.1-9.2 Password recovery
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_forgot_existing_email_creates_token(db_session, create_tables, monkeypatch):
    """forgot() for existing email creates a recovery token and calls email port."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "forgot_ok@example.com")

    sent_tokens = []
    async def fake_email_port(email, token):
        sent_tokens.append(token)

    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=fake_email_port,
    )
    result = await svc.forgot(email="forgot_ok@example.com", tenant_id=tenant.id)
    assert result["message"] is not None  # uniform response
    assert len(sent_tokens) == 1  # email port was called

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import PasswordRecoveryToken, AuthIdentity
    await db_session.execute(delete(PasswordRecoveryToken).where(PasswordRecoveryToken.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_forgot_nonexistent_email_returns_same_message(db_session, create_tables, monkeypatch):
    """forgot() for nonexistent email returns same uniform response, no token created."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "forgot_exists@example.com")

    sent_tokens = []
    async def fake_email_port(email, token):
        sent_tokens.append(token)

    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=fake_email_port,
    )
    result = await svc.forgot(email="noexist_forgot@example.com", tenant_id=tenant.id)
    assert result["message"] is not None
    assert len(sent_tokens) == 0  # no email sent

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import AuthIdentity
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_reset_with_valid_token_changes_password(db_session, create_tables, monkeypatch):
    """reset() with valid token updates password hash and revokes sessions."""
    setup_env(monkeypatch)
    from app.services.auth_service import AuthService, AuthenticationError
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.repositories.recovery_token_repository import RecoveryTokenRepository

    tenant, identity = await make_tenant_and_identity(db_session, "reset_ok@example.com")

    sent_tokens = []
    async def fake_email_port(email, token):
        sent_tokens.append(token)

    svc = AuthService(
        auth_identity_repo=AuthIdentityRepository(db_session),
        refresh_session_repo=RefreshSessionRepository(db_session),
        recovery_token_repo=RecoveryTokenRepository(db_session),
        email_port=fake_email_port,
    )
    # First login to get a refresh session
    login_result = await svc.login(
        email="reset_ok@example.com", password="CorrectP@ss1", tenant_id=tenant.id
    )

    # Request recovery
    await svc.forgot(email="reset_ok@example.com", tenant_id=tenant.id)
    assert len(sent_tokens) == 1
    recovery_token = sent_tokens[0]

    # Reset password
    await svc.reset(token=recovery_token, new_password="NewP@ss2!", tenant_id=tenant.id)

    # Old password no longer works
    with pytest.raises(AuthenticationError):
        await svc.login(email="reset_ok@example.com", password="CorrectP@ss1", tenant_id=tenant.id)

    # Old refresh session is revoked
    with pytest.raises(AuthenticationError):
        await svc.refresh(login_result["refresh_token"])

    # New password works
    new_login = await svc.login(
        email="reset_ok@example.com", password="NewP@ss2!", tenant_id=tenant.id
    )
    assert "access_token" in new_login

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession, PasswordRecoveryToken, AuthIdentity
    await db_session.execute(delete(RefreshSession).where(RefreshSession.auth_identity_id == identity.id))
    await db_session.execute(delete(PasswordRecoveryToken).where(PasswordRecoveryToken.auth_identity_id == identity.id))
    await db_session.execute(delete(AuthIdentity).where(AuthIdentity.id == identity.id))
    from app.models.tenant import Tenant
    await db_session.delete(tenant)
    await db_session.commit()
