"""
Tests for auth repositories: AuthIdentityRepository, RefreshSessionRepository,
PasswordRecoveryTokenRepository.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest


TEST_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://postgres@localhost:5432/activia_trace_test",
    "SECRET_KEY": "supersecretkeyfortesting1234567890",
    "ENCRYPTION_KEY": "E" * 32,
}


def setup_env(monkeypatch):
    for k, v in TEST_ENV.items():
        monkeypatch.setenv(k, v)


async def make_tenant(db_session, nombre="Repo Test Tenant"):
    from app.models.tenant import Tenant, TenantEstado
    tenant = Tenant(nombre=nombre, estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


async def make_identity(db_session, tenant_id, email="repo@example.com"):
    from app.models.auth import AuthIdentity
    from app.core.security import email_lookup_hash, hash_password
    identity = AuthIdentity(
        tenant_id=tenant_id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        password_hash=hash_password("testpwd"),
        roles=["COORDINADOR"],
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)
    return identity


# ==============================================================================
# 4.1 AuthIdentityRepository
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_auth_identity_repo_lookup_by_email_hash(db_session, create_tables, monkeypatch):
    """lookup_by_email_hash finds the correct identity by (tenant_id, email_hash)."""
    setup_env(monkeypatch)
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.core.security import email_lookup_hash

    tenant = await make_tenant(db_session, "AIR Lookup Tenant")
    identity = await make_identity(db_session, tenant.id, "lookup@example.com")

    repo = AuthIdentityRepository(db_session)
    email_hash = email_lookup_hash("lookup@example.com")
    found = await repo.lookup_by_email_hash(tenant_id=tenant.id, email_hash=email_hash)

    assert found is not None
    assert found.id == identity.id

    # Cleanup
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_identity_repo_lookup_wrong_hash_returns_none(db_session, create_tables, monkeypatch):
    """lookup_by_email_hash returns None for an email hash not in the tenant."""
    setup_env(monkeypatch)
    from app.repositories.auth_identity_repository import AuthIdentityRepository

    tenant = await make_tenant(db_session, "AIR Miss Tenant")
    identity = await make_identity(db_session, tenant.id, "miss@example.com")

    repo = AuthIdentityRepository(db_session)
    found = await repo.lookup_by_email_hash(
        tenant_id=tenant.id, email_hash="nonexistenthashabcdef1234567890" + "x" * 33
    )
    assert found is None

    # Cleanup
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_identity_repo_tenant_isolation(db_session, create_tables, monkeypatch):
    """Identity of tenant A is NOT returned when scoped to tenant B."""
    setup_env(monkeypatch)
    from app.repositories.auth_identity_repository import AuthIdentityRepository
    from app.core.security import email_lookup_hash

    tenant_a = await make_tenant(db_session, "Isolation Tenant A")
    tenant_b = await make_tenant(db_session, "Isolation Tenant B")
    email = "shared@example.com"
    identity_a = await make_identity(db_session, tenant_a.id, email)

    repo = AuthIdentityRepository(db_session)
    email_hash = email_lookup_hash(email)

    # Found in tenant A
    assert await repo.lookup_by_email_hash(tenant_id=tenant_a.id, email_hash=email_hash) is not None
    # NOT found in tenant B
    assert await repo.lookup_by_email_hash(tenant_id=tenant_b.id, email_hash=email_hash) is None

    # Cleanup
    await db_session.delete(identity_a)
    await db_session.delete(tenant_b)
    await db_session.delete(tenant_a)
    await db_session.commit()


# ==============================================================================
# 4.2 RefreshSessionRepository
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_session_repo_get_by_token_hash(db_session, create_tables, monkeypatch):
    """get_by_token_hash finds the session by token hash."""
    setup_env(monkeypatch)
    from app.models.auth import RefreshSession
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.core.security import generate_opaque_token, hash_opaque_token

    tenant = await make_tenant(db_session, "RSR Get Tenant")
    identity = await make_identity(db_session, tenant.id, "rsr@example.com")

    token = generate_opaque_token()
    token_hash = hash_opaque_token(token)
    session = RefreshSession(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=token_hash,
        family_id=uuid.uuid4(),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=14),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    repo = RefreshSessionRepository(db_session)
    found = await repo.get_by_token_hash(token_hash)
    assert found is not None
    assert found.id == session.id

    # Cleanup
    db_session.expunge(session)
    from sqlalchemy import delete
    from app.models.auth import RefreshSession as RS
    await db_session.execute(delete(RS).where(RS.id == session.id))
    await db_session.commit()
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_session_repo_revoke_soft_delete(db_session, create_tables, monkeypatch):
    """mark_revoked sets revoked_at; the row still exists (no physical delete)."""
    setup_env(monkeypatch)
    from app.models.auth import RefreshSession
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.core.security import generate_opaque_token, hash_opaque_token
    from sqlalchemy import select

    tenant = await make_tenant(db_session, "RSR Revoke Tenant")
    identity = await make_identity(db_session, tenant.id, "rsrrev@example.com")

    token = generate_opaque_token()
    token_hash = hash_opaque_token(token)
    session = RefreshSession(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=token_hash,
        family_id=uuid.uuid4(),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=14),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    repo = RefreshSessionRepository(db_session)
    await repo.mark_revoked(session)

    # Row still exists (soft delete philosophy)
    result = await db_session.execute(
        select(RefreshSession).where(RefreshSession.id == session.id)
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.revoked_at is not None

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession as RS
    await db_session.execute(delete(RS).where(RS.id == session.id))
    await db_session.commit()
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_session_repo_revoke_family_only_affects_family(db_session, create_tables, monkeypatch):
    """revoke_family revokes all sessions in the family; other families unaffected."""
    setup_env(monkeypatch)
    from app.models.auth import RefreshSession
    from app.repositories.refresh_session_repository import RefreshSessionRepository
    from app.core.security import generate_opaque_token, hash_opaque_token
    from sqlalchemy import select

    tenant = await make_tenant(db_session, "RSR Family Tenant")
    identity = await make_identity(db_session, tenant.id, "rsrfam@example.com")

    family_a = uuid.uuid4()
    family_b = uuid.uuid4()

    def make_session(family_id):
        token = generate_opaque_token()
        return RefreshSession(
            tenant_id=tenant.id,
            auth_identity_id=identity.id,
            token_hash=hash_opaque_token(token),
            family_id=family_id,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=14),
        )

    s1 = make_session(family_a)
    s2 = make_session(family_a)
    s3 = make_session(family_b)

    for s in [s1, s2, s3]:
        db_session.add(s)
    await db_session.commit()
    for s in [s1, s2, s3]:
        await db_session.refresh(s)

    repo = RefreshSessionRepository(db_session)
    await repo.revoke_family(family_a)

    # s1 and s2 should be revoked
    for s_id in [s1.id, s2.id]:
        result = await db_session.execute(
            select(RefreshSession).where(RefreshSession.id == s_id)
        )
        row = result.scalar_one()
        assert row.revoked_at is not None

    # s3 (different family) should NOT be revoked
    result = await db_session.execute(
        select(RefreshSession).where(RefreshSession.id == s3.id)
    )
    row = result.scalar_one()
    assert row.revoked_at is None

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import RefreshSession as RS
    await db_session.execute(delete(RS).where(RS.auth_identity_id == identity.id))
    await db_session.commit()
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


# ==============================================================================
# 4.3 PasswordRecoveryTokenRepository
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_recovery_token_repo_create_and_get(db_session, create_tables, monkeypatch):
    """create stores token; get_by_token_hash retrieves it."""
    setup_env(monkeypatch)
    from app.repositories.recovery_token_repository import RecoveryTokenRepository
    from app.core.security import generate_opaque_token, hash_opaque_token

    tenant = await make_tenant(db_session, "RTR Create Tenant")
    identity = await make_identity(db_session, tenant.id, "rtr@example.com")

    repo = RecoveryTokenRepository(db_session)
    token = generate_opaque_token()
    token_hash = hash_opaque_token(token)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=30)

    recovery = await repo.create(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    assert recovery.id is not None
    assert recovery.used_at is None

    found = await repo.get_by_token_hash(token_hash)
    assert found is not None
    assert found.id == recovery.id

    # Cleanup
    from sqlalchemy import delete
    from app.models.auth import PasswordRecoveryToken
    await db_session.execute(delete(PasswordRecoveryToken).where(PasswordRecoveryToken.id == recovery.id))
    await db_session.commit()
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_recovery_token_repo_mark_used(db_session, create_tables, monkeypatch):
    """mark_used sets used_at timestamp."""
    setup_env(monkeypatch)
    from app.repositories.recovery_token_repository import RecoveryTokenRepository
    from app.core.security import generate_opaque_token, hash_opaque_token
    from sqlalchemy import select
    from app.models.auth import PasswordRecoveryToken

    tenant = await make_tenant(db_session, "RTR Used Tenant")
    identity = await make_identity(db_session, tenant.id, "rtrused@example.com")

    repo = RecoveryTokenRepository(db_session)
    token = generate_opaque_token()
    token_hash = hash_opaque_token(token)
    recovery = await repo.create(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=token_hash,
        expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=30),
    )

    await repo.mark_used(recovery)

    result = await db_session.execute(
        select(PasswordRecoveryToken).where(PasswordRecoveryToken.id == recovery.id)
    )
    row = result.scalar_one()
    assert row.used_at is not None

    # Cleanup
    from sqlalchemy import delete
    await db_session.execute(delete(PasswordRecoveryToken).where(PasswordRecoveryToken.id == recovery.id))
    await db_session.commit()
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_recovery_token_repo_invalidate_all_for_identity(db_session, create_tables, monkeypatch):
    """invalidate_all_for_identity marks all tokens for an identity as used."""
    setup_env(monkeypatch)
    from app.repositories.recovery_token_repository import RecoveryTokenRepository
    from app.core.security import generate_opaque_token, hash_opaque_token
    from sqlalchemy import select
    from app.models.auth import PasswordRecoveryToken

    tenant = await make_tenant(db_session, "RTR Invalidate Tenant")
    identity = await make_identity(db_session, tenant.id, "rtrinv@example.com")

    repo = RecoveryTokenRepository(db_session)
    # Create two tokens
    t1 = await repo.create(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=hash_opaque_token(generate_opaque_token()),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=30),
    )
    t2 = await repo.create(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=hash_opaque_token(generate_opaque_token()),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=30),
    )

    await repo.invalidate_all_for_identity(identity.id)

    for token_id in [t1.id, t2.id]:
        result = await db_session.execute(
            select(PasswordRecoveryToken).where(PasswordRecoveryToken.id == token_id)
        )
        row = result.scalar_one()
        assert row.used_at is not None

    # Cleanup
    from sqlalchemy import delete
    await db_session.execute(delete(PasswordRecoveryToken).where(
        PasswordRecoveryToken.auth_identity_id == identity.id
    ))
    await db_session.commit()
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()
