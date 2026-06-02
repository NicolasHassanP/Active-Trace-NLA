"""
Tests for auth models: AuthIdentity, RefreshSession, PasswordRecoveryToken.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
Tasks 3.1-3.3: model persistence, encryption, isolation, soft delete.
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


# ==============================================================================
# 3.1 AuthIdentity — persist, read, encryption, uniqueness constraint
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_auth_identity_persist_and_read(db_session, create_tables, monkeypatch):
    """AuthIdentity can be created and read back; email round-trips via EncryptedString."""
    setup_env(monkeypatch)
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity
    from app.core.security import email_lookup_hash, hash_password

    # Create a tenant first
    tenant = Tenant(nombre="Test Tenant Auth", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    email = "user@example.com"
    identity = AuthIdentity(
        tenant_id=tenant.id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        password_hash=hash_password("MyP@ssw0rd!"),
        roles=["COORDINADOR"],
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    assert identity.id is not None
    assert identity.email_encrypted == email  # ORM sees plaintext
    assert identity.email_hash == email_lookup_hash(email)
    assert identity.roles == ["COORDINADOR"]
    assert identity.is_active is True
    assert identity.totp_enabled is False
    assert identity.totp_secret_encrypted is None
    assert identity.deleted_at is None

    # Cleanup
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_identity_email_encrypted_in_db(db_session, create_tables, test_engine, monkeypatch):
    """Raw column value in DB is NOT the plaintext email (encrypted at rest)."""
    setup_env(monkeypatch)
    from sqlalchemy import text
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity
    from app.core.security import email_lookup_hash, hash_password

    tenant = Tenant(nombre="Enc Test Tenant", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    email = "encrypted@example.com"
    identity = AuthIdentity(
        tenant_id=tenant.id,
        email_encrypted=email,
        email_hash=email_lookup_hash(email),
        password_hash=hash_password("pwd"),
        roles=[],
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    result = await db_session.execute(
        text("SELECT email_encrypted FROM auth_identities WHERE id = :id"),
        {"id": str(identity.id)},
    )
    raw_email = result.scalar()
    assert raw_email != email  # Must be ciphertext, not plaintext
    assert raw_email is not None

    # Cleanup
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_identity_unique_email_hash_per_tenant(test_engine, create_tables, monkeypatch):
    """(tenant_id, email_hash) unique constraint prevents duplicates within a tenant.
    Uses an independent session to avoid poisoning the shared session fixture."""
    setup_env(monkeypatch)
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import build_session_factory
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity
    from app.core.security import email_lookup_hash, hash_password

    # Use a fresh connection to avoid poisoning the shared session on IntegrityError
    tenant_id_saved = None
    async with test_engine.begin() as conn:
        # Create tenant
        result = await conn.execute(
            __import__('sqlalchemy').text(
                "INSERT INTO tenants (id, nombre, estado) "
                "VALUES (gen_random_uuid(), 'Unique Test Tenant', 'activo') RETURNING id"
            )
        )
        tenant_id_saved = result.scalar()

    email = "same@example.com"
    ehash = email_lookup_hash(email)

    async with test_engine.begin() as conn:
        # Insert first identity (should succeed)
        await conn.execute(
            __import__('sqlalchemy').text(
                "INSERT INTO auth_identities "
                "(id, tenant_id, email_encrypted, email_hash, password_hash, roles, is_active, totp_enabled) "
                "VALUES (gen_random_uuid(), :t, :ee, :eh, :ph, '[]', true, false)"
            ),
            {"t": str(tenant_id_saved), "ee": "enc1", "eh": ehash, "ph": hash_password("pwd1")},
        )

    # Insert second identity with same (tenant_id, email_hash) — should violate unique constraint
    constraint_violated = False
    try:
        async with test_engine.begin() as conn:
            await conn.execute(
                __import__('sqlalchemy').text(
                    "INSERT INTO auth_identities "
                    "(id, tenant_id, email_encrypted, email_hash, password_hash, roles, is_active, totp_enabled) "
                    "VALUES (gen_random_uuid(), :t, :ee, :eh, :ph, '[]', true, false)"
                ),
                {"t": str(tenant_id_saved), "ee": "enc2", "eh": ehash, "ph": hash_password("pwd2")},
            )
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower() or "UniqueViolation" in type(e).__name__:
            constraint_violated = True
        else:
            raise

    assert constraint_violated, "Expected UniqueViolation for duplicate (tenant_id, email_hash)"

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.execute(
            __import__('sqlalchemy').text("DELETE FROM auth_identities WHERE tenant_id = :t"),
            {"t": str(tenant_id_saved)},
        )
        await conn.execute(
            __import__('sqlalchemy').text("DELETE FROM tenants WHERE id = :t"),
            {"t": str(tenant_id_saved)},
        )


# ==============================================================================
# 3.2 RefreshSession — persist, read, revoked/rotated states
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_session_persist_and_read(db_session, create_tables, monkeypatch):
    """RefreshSession can be created and read back."""
    setup_env(monkeypatch)
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity, RefreshSession
    from app.core.security import email_lookup_hash, hash_password, generate_opaque_token, hash_opaque_token

    tenant = Tenant(nombre="RS Tenant", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    identity = AuthIdentity(
        tenant_id=tenant.id,
        email_encrypted="rs@example.com",
        email_hash=email_lookup_hash("rs@example.com"),
        password_hash=hash_password("pwd"),
        roles=[],
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    token = generate_opaque_token()
    token_hash = hash_opaque_token(token)
    family_id = uuid.uuid4()
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=14)

    session = RefreshSession(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=token_hash,
        family_id=family_id,
        expires_at=expires_at,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.token_hash == token_hash
    assert session.revoked_at is None
    assert session.rotated_at is None
    assert session.deleted_at is None

    # Cleanup
    await db_session.delete(session)
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_refresh_session_revoked_state(db_session, create_tables, monkeypatch):
    """RefreshSession revoked_at can be set (soft revocation, no physical delete)."""
    setup_env(monkeypatch)
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity, RefreshSession
    from app.core.security import email_lookup_hash, hash_password, generate_opaque_token, hash_opaque_token

    tenant = Tenant(nombre="RS Revoke Tenant", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    identity = AuthIdentity(
        tenant_id=tenant.id,
        email_encrypted="rev@example.com",
        email_hash=email_lookup_hash("rev@example.com"),
        password_hash=hash_password("pwd"),
        roles=[],
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    session = RefreshSession(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=hash_opaque_token(generate_opaque_token()),
        family_id=uuid.uuid4(),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=14),
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Revoke
    session.revoked_at = datetime.now(tz=timezone.utc)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.revoked_at is not None

    # Cleanup
    await db_session.delete(session)
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()


# ==============================================================================
# 3.3 PasswordRecoveryToken — persist, read, used_at state
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_password_recovery_token_persist_and_read(db_session, create_tables, monkeypatch):
    """PasswordRecoveryToken can be created and read back."""
    setup_env(monkeypatch)
    from app.models.tenant import Tenant, TenantEstado
    from app.models.auth import AuthIdentity, PasswordRecoveryToken
    from app.core.security import email_lookup_hash, hash_password, generate_opaque_token, hash_opaque_token

    tenant = Tenant(nombre="PRT Tenant", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    identity = AuthIdentity(
        tenant_id=tenant.id,
        email_encrypted="prt@example.com",
        email_hash=email_lookup_hash("prt@example.com"),
        password_hash=hash_password("pwd"),
        roles=[],
        is_active=True,
        totp_enabled=False,
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    token_hash = hash_opaque_token(generate_opaque_token())
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=30)

    recovery_token = PasswordRecoveryToken(
        tenant_id=tenant.id,
        auth_identity_id=identity.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db_session.add(recovery_token)
    await db_session.commit()
    await db_session.refresh(recovery_token)

    assert recovery_token.id is not None
    assert recovery_token.token_hash == token_hash
    assert recovery_token.used_at is None

    # Mark used
    recovery_token.used_at = datetime.now(tz=timezone.utc)
    await db_session.commit()
    await db_session.refresh(recovery_token)
    assert recovery_token.used_at is not None

    # Cleanup
    await db_session.delete(recovery_token)
    await db_session.delete(identity)
    await db_session.delete(tenant)
    await db_session.commit()
