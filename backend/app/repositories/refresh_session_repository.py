"""
RefreshSessionRepository — queries for refresh_sessions.

C-03: Handles refresh token lifecycle:
    - create: store a new session with the token hash.
    - get_by_token_hash: lookup a session (including revoked/rotated).
    - mark_rotated: consume the current token (rotation).
    - mark_revoked: hard-revoke a session (logout).
    - revoke_family: revoke all sessions sharing a family_id (reuse detection).

No business logic here — only DB queries.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import RefreshSession


class RefreshSessionRepository:
    """Repository for RefreshSession lifecycle management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, refresh_session: RefreshSession) -> RefreshSession:
        """Persist a new RefreshSession and return it refreshed."""
        self._session.add(refresh_session)
        await self._session.commit()
        await self._session.refresh(refresh_session)
        return refresh_session

    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshSession]:
        """
        Find a RefreshSession by its token hash.

        Returns the session regardless of revocation status — the caller
        decides whether revoked/rotated tokens trigger reuse detection.
        Excludes soft-deleted rows.
        """
        stmt = select(RefreshSession).where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_rotated(self, session: RefreshSession) -> None:
        """Mark a session as rotated (consumed) during token rotation."""
        now = datetime.now(tz=timezone.utc)
        session.rotated_at = now
        session.revoked_at = now  # also revoke so reuse detection fires correctly
        await self._session.commit()

    async def mark_revoked(self, session: RefreshSession) -> None:
        """Revoke a session (e.g., on logout). Row is NOT physically deleted."""
        session.revoked_at = datetime.now(tz=timezone.utc)
        await self._session.commit()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        """
        Revoke ALL sessions in the given family_id.

        Called when reuse is detected (a consumed token is presented again).
        """
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.deleted_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def revoke_all_for_identity(self, auth_identity_id: uuid.UUID) -> None:
        """
        Revoke ALL active sessions for a given auth identity.

        Called on password reset to force re-login on all devices.
        """
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.auth_identity_id == auth_identity_id,
                RefreshSession.revoked_at.is_(None),
                RefreshSession.deleted_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self._session.execute(stmt)
        await self._session.commit()
