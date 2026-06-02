"""
AuthService — authentication business logic.

C-03: Orchestrates login, refresh token rotation, logout, 2FA TOTP, and
password recovery. No direct DB access — all queries go via repositories.

Hard rules:
    - Identity/tenant/roles ALWAYS from the verified JWT, never from request params.
    - Passwords hashed with Argon2id; secrets/PII at rest AES-256.
    - Soft delete always; never physical DELETE.
    - No SQL in this service (all DB ops via repositories).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from app.core.security import (
    email_lookup_hash,
    encode_access_token,
    encode_mfa_token,
    decode_mfa_token,
    generate_opaque_token,
    generate_totp_secret,
    build_totp_uri,
    hash_opaque_token,
    hash_password,
    verify_password,
    verify_totp,
)
from app.models.auth import AuthIdentity, RefreshSession
from app.repositories.auth_identity_repository import AuthIdentityRepository
from app.repositories.recovery_token_repository import RecoveryTokenRepository
from app.repositories.refresh_session_repository import RefreshSessionRepository


class AuthenticationError(Exception):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""


class AuthService:
    """
    Orchestrates all auth flows.

    Parameters
    ----------
    auth_identity_repo : AuthIdentityRepository
    refresh_session_repo : RefreshSessionRepository
    recovery_token_repo : RecoveryTokenRepository
    email_port : async callable(email, token) | None
        Injected port for sending recovery emails. Mockeable in tests.
    """

    def __init__(
        self,
        auth_identity_repo: AuthIdentityRepository,
        refresh_session_repo: RefreshSessionRepository,
        recovery_token_repo: RecoveryTokenRepository,
        email_port: Optional[Callable] = None,
    ) -> None:
        self._identity_repo = auth_identity_repo
        self._session_repo = refresh_session_repo
        self._recovery_repo = recovery_token_repo
        self._email_port = email_port

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        *,
        email: str,
        password: str,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Validate credentials and either issue tokens or an MFA challenge.

        Returns a dict with:
            - access_token + refresh_token + token_type  (no 2FA), OR
            - mfa_token + mfa_required=True              (2FA gate)

        Raises AuthenticationError for any failure (no user enumeration).
        """
        normalized_email = email.strip().lower()
        email_hash = email_lookup_hash(normalized_email)

        identity = await self._identity_repo.lookup_by_email_hash(
            tenant_id=tenant_id, email_hash=email_hash
        )

        # Anti-timing: run a dummy verify even when the identity is not found
        dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$X" + "A" * 43 + "$" + "B" * 43
        if identity is None:
            verify_password(password, dummy_hash)  # Constant-time dummy
            raise AuthenticationError("Invalid credentials")

        if not verify_password(password, identity.password_hash):
            raise AuthenticationError("Invalid credentials")

        if not identity.is_active:
            raise AuthenticationError("Invalid credentials")

        # 2FA gate
        if identity.totp_enabled:
            mfa_token = encode_mfa_token(user_id=identity.id, tenant_id=tenant_id)
            return {"mfa_token": mfa_token, "mfa_required": True}

        return await self._issue_session(identity)

    # ------------------------------------------------------------------
    # Session issuance (internal)
    # ------------------------------------------------------------------

    async def _issue_session(self, identity: AuthIdentity) -> Dict[str, Any]:
        """Create access + refresh tokens and persist the refresh session."""
        from app.core.config import Settings
        settings = Settings()

        access_token = encode_access_token(
            user_id=identity.id,
            tenant_id=identity.tenant_id,
            roles=identity.roles,
        )
        refresh_value = generate_opaque_token()
        refresh_hash = hash_opaque_token(refresh_value)
        family_id = uuid.uuid4()
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        session = RefreshSession(
            tenant_id=identity.tenant_id,
            auth_identity_id=identity.id,
            token_hash=refresh_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        await self._session_repo.create(session)

        return {
            "access_token": access_token,
            "refresh_token": refresh_value,
            "token_type": "bearer",
        }

    # ------------------------------------------------------------------
    # Refresh rotation
    # ------------------------------------------------------------------

    async def refresh(self, refresh_token: str) -> Dict[str, Any]:
        """
        Rotate a refresh token.

        - Valid + not revoked → mark rotated + issue new pair in same family.
        - Already rotated/revoked (reuse) → revoke whole family → raise.
        - Expired → raise.
        """
        token_hash = hash_opaque_token(refresh_token)
        session = await self._session_repo.get_by_token_hash(token_hash)

        if session is None:
            raise AuthenticationError("Invalid refresh token")

        # Reuse detection: token was already rotated/revoked
        if session.revoked_at is not None:
            await self._session_repo.revoke_family(session.family_id)
            raise AuthenticationError("Refresh token reuse detected; session revoked")

        # Expiry check
        if session.expires_at < datetime.now(tz=timezone.utc):
            raise AuthenticationError("Refresh token expired")

        # Mark old session as rotated (which also revokes it)
        await self._session_repo.mark_rotated(session)

        # Issue new session in the same family
        identity = await self._identity_repo.get_by_id(session.auth_identity_id)
        if identity is None:
            raise AuthenticationError("Identity not found")

        from app.core.config import Settings
        settings = Settings()

        access_token = encode_access_token(
            user_id=identity.id,
            tenant_id=identity.tenant_id,
            roles=identity.roles,
        )
        new_refresh_value = generate_opaque_token()
        new_refresh_hash = hash_opaque_token(new_refresh_value)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        new_session = RefreshSession(
            tenant_id=session.tenant_id,
            auth_identity_id=session.auth_identity_id,
            token_hash=new_refresh_hash,
            family_id=session.family_id,  # Same family
            expires_at=expires_at,
        )
        await self._session_repo.create(new_session)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_value,
            "token_type": "bearer",
        }

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh session associated with the given token."""
        token_hash = hash_opaque_token(refresh_token)
        session = await self._session_repo.get_by_token_hash(token_hash)
        if session is None:
            return  # Already gone — idempotent
        await self._session_repo.mark_revoked(session)

    # ------------------------------------------------------------------
    # 2FA TOTP
    # ------------------------------------------------------------------

    async def enroll_2fa(self, identity: AuthIdentity) -> Dict[str, str]:
        """
        Generate and store (encrypted) a TOTP secret.

        Sets totp_secret_encrypted (AES-256), totp_enabled remains False.
        Returns {'secret': ..., 'uri': ...} for QR display.
        """
        secret = generate_totp_secret()
        uri = build_totp_uri(
            secret=secret,
            account_name=identity.email_encrypted,  # ORM sees plaintext
            issuer="activia-trace",
        )
        identity.totp_secret_encrypted = secret  # EncryptedString stores it AES-256
        identity.totp_enabled = False
        await self._identity_repo.save(identity)
        return {"secret": secret, "uri": uri}

    async def verify_2fa_activation(
        self, identity: AuthIdentity, code: str
    ) -> None:
        """
        Validate the activation code and set totp_enabled=True.

        Raises AuthenticationError if the code is invalid.
        """
        if not identity.totp_secret_encrypted:
            raise AuthenticationError("2FA not enrolled")
        if not verify_totp(identity.totp_secret_encrypted, code):
            raise AuthenticationError("Invalid TOTP code")
        identity.totp_enabled = True
        await self._identity_repo.save(identity)

    async def complete_mfa(
        self,
        *,
        mfa_token: str,
        code: str,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Complete the 2FA login challenge.

        Decodes the mfa_token, validates the TOTP code, and issues a full session.
        Raises AuthenticationError on failure.
        """
        from jose import JWTError
        try:
            claims = decode_mfa_token(mfa_token)
        except JWTError:
            raise AuthenticationError("Invalid or expired MFA token")

        user_id = uuid.UUID(claims["sub"])
        identity = await self._identity_repo.get_by_id(user_id)
        if identity is None or not identity.is_active:
            raise AuthenticationError("Identity not found")

        if not identity.totp_secret_encrypted:
            raise AuthenticationError("2FA not enrolled")

        if not verify_totp(identity.totp_secret_encrypted, code):
            raise AuthenticationError("Invalid TOTP code")

        return await self._issue_session(identity)

    # ------------------------------------------------------------------
    # Password recovery
    # ------------------------------------------------------------------

    async def forgot(
        self,
        *,
        email: str,
        tenant_id: uuid.UUID,
    ) -> Dict[str, str]:
        """
        Initiate password recovery.

        If the email exists, creates a single-use recovery token (stored by hash)
        and calls the email port. Always returns the same uniform response.
        """
        from app.core.config import Settings
        settings = Settings()

        normalized_email = email.strip().lower()
        email_hash = email_lookup_hash(normalized_email)

        identity = await self._identity_repo.lookup_by_email_hash(
            tenant_id=tenant_id, email_hash=email_hash
        )

        if identity is not None:
            token_value = generate_opaque_token()
            token_hash = hash_opaque_token(token_value)
            expires_at = datetime.now(tz=timezone.utc) + timedelta(
                minutes=settings.RECOVERY_TOKEN_EXPIRE_MINUTES
            )
            await self._recovery_repo.create(
                tenant_id=tenant_id,
                auth_identity_id=identity.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            if self._email_port is not None:
                await self._email_port(normalized_email, token_value)

        return {"message": "If the email exists, a recovery link has been sent."}

    async def reset(
        self,
        *,
        token: str,
        new_password: str,
        tenant_id: uuid.UUID,
    ) -> None:
        """
        Reset password using a recovery token.

        Validates token hash+vigencia+not used, sets new Argon2id hash,
        marks token used, invalidates other tokens, revokes all refresh sessions.

        Raises AuthenticationError on any validation failure.
        """
        token_hash = hash_opaque_token(token)
        recovery = await self._recovery_repo.get_by_token_hash(token_hash)

        if recovery is None:
            raise AuthenticationError("Invalid recovery token")

        if recovery.used_at is not None:
            raise AuthenticationError("Recovery token already used")

        if recovery.expires_at < datetime.now(tz=timezone.utc):
            raise AuthenticationError("Recovery token expired")

        identity = await self._identity_repo.get_by_id(recovery.auth_identity_id)
        if identity is None:
            raise AuthenticationError("Identity not found")

        # Update password
        identity.password_hash = hash_password(new_password)
        await self._identity_repo.save(identity)

        # Mark token used + invalidate other tokens for this identity
        await self._recovery_repo.mark_used(recovery)
        await self._recovery_repo.invalidate_all_for_identity(identity.id)

        # Revoke all active refresh sessions (force re-login on all devices)
        await self._session_repo.revoke_all_for_identity(identity.id)
