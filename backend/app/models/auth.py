"""
Auth models — minimum identity for authentication.

C-03: auth_identity is the auth-owned subconjunto required to authenticate.
It does NOT represent the complete Usuario (that is C-07). Designed to be
reconciled/absorbed by Usuario in C-07.

Tables:
    auth_identities          — login credentials, email (encrypted+hash), TOTP, roles
    refresh_sessions         — opaque refresh tokens stored by SHA-256 hash
    password_recovery_tokens — single-use recovery tokens stored by SHA-256 hash
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.security import EncryptedString
from app.models.mixins import TenantScopedBase


# ---------------------------------------------------------------------------
# AuthIdentity — minimum identity for auth; reconciled by Usuario in C-07
# ---------------------------------------------------------------------------

class AuthIdentity(Base, TenantScopedBase):
    """
    Auth-owned identity record.

    Stores encrypted email (for display/recovery) + HMAC-SHA256 email hash
    (for fast, secure lookup), Argon2id password hash, optional TOTP secret
    (encrypted), role snapshot, and active flag.

    Unique constraint: (tenant_id, email_hash) — same email allowed across
    different tenants, but unique within a tenant.
    """
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email_hash", name="uq_auth_identity_tenant_email"),
    )

    # Email: encrypted at rest (non-searchable) + deterministic hash for lookup
    email_encrypted: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Password hashed with Argon2id — NEVER plaintext
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)

    # Roles snapshot — JSONB array of role name strings.
    # Fine-grained permission resolution deferred to C-04.
    roles: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)

    # User lifecycle flag
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Optional TOTP 2FA — secret stored encrypted; enabled flag tracks activation
    totp_secret_encrypted: Mapped[Optional[str]] = mapped_column(
        EncryptedString, nullable=True, default=None
    )
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuthIdentity id={self.id} tenant_id={self.tenant_id}>"


# ---------------------------------------------------------------------------
# RefreshSession — opaque refresh token stored by SHA-256 hash
# ---------------------------------------------------------------------------

class RefreshSession(Base, TenantScopedBase):
    """
    Stateful refresh session.

    The refresh token VALUE is held by the client. The server only stores its
    SHA-256 hash. Token rotation: on use, this row is marked rotated and a new
    RefreshSession is created in the same family_id. Reuse of a consumed token
    triggers revocation of the entire family.
    """
    __tablename__ = "refresh_sessions"

    # FK to the owning auth_identity
    auth_identity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hash of the opaque refresh token value
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Rotation family — groups all tokens in the same rotation chain
    family_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Soft lifecycle markers (not deleted_at — these are additional state flags)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshSession id={self.id} family={self.family_id}>"


# ---------------------------------------------------------------------------
# PasswordRecoveryToken — single-use recovery token stored by SHA-256 hash
# ---------------------------------------------------------------------------

class PasswordRecoveryToken(Base, TenantScopedBase):
    """
    Single-use password recovery token.

    Generated on `forgot`, stored by SHA-256 hash. Expires after a short TTL
    (default 30 min). Once used, `used_at` is set and all other tokens for the
    same identity are invalidated.
    """
    __tablename__ = "password_recovery_tokens"

    # FK to the owning auth_identity
    auth_identity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hash of the opaque recovery token value
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Single-use marker — set when consumed
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PasswordRecoveryToken id={self.id}>"
