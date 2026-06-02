"""
RecoveryTokenRepository — queries for password_recovery_tokens.

C-03: Handles the password recovery token lifecycle:
    - create: store a new recovery token with the hash.
    - get_by_token_hash: lookup an unused, unexpired token.
    - mark_used: consume the token (single-use).
    - invalidate_all_for_identity: consume all remaining tokens for a user.

No business logic here — only DB queries.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import PasswordRecoveryToken


class RecoveryTokenRepository:
    """Repository for PasswordRecoveryToken lifecycle management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        auth_identity_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordRecoveryToken:
        """Create and persist a new recovery token."""
        token = PasswordRecoveryToken(
            tenant_id=tenant_id,
            auth_identity_id=auth_identity_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.commit()
        await self._session.refresh(token)
        return token

    async def get_by_token_hash(self, token_hash: str) -> Optional[PasswordRecoveryToken]:
        """
        Find a recovery token by its hash.

        Returns the row regardless of used_at — caller checks validity.
        Excludes soft-deleted rows.
        """
        stmt = select(PasswordRecoveryToken).where(
            PasswordRecoveryToken.token_hash == token_hash,
            PasswordRecoveryToken.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordRecoveryToken) -> None:
        """Mark a recovery token as used (single-use enforcement)."""
        token.used_at = datetime.now(tz=timezone.utc)
        await self._session.commit()

    async def invalidate_all_for_identity(self, auth_identity_id: uuid.UUID) -> None:
        """
        Mark all unused recovery tokens for an identity as used.

        Called after a successful reset to prevent reuse of any other tokens
        that may have been issued.
        """
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(PasswordRecoveryToken)
            .where(
                PasswordRecoveryToken.auth_identity_id == auth_identity_id,
                PasswordRecoveryToken.used_at.is_(None),
                PasswordRecoveryToken.deleted_at.is_(None),
            )
            .values(used_at=now)
        )
        await self._session.execute(stmt)
        await self._session.commit()
