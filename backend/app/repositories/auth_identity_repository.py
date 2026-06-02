"""
AuthIdentityRepository — queries for auth_identity.

C-03 Design note (D1/OQ-1): The login lookup must resolve the tenant BEFORE
a session exists. This is the documented exception to scope-by-construction:
the `tenant_id` is provided explicitly from the public request context
(subdomain / X-Tenant header), NOT from a JWT. Only the lookup for login uses
this pattern — all other auth operations happen after the token is issued.

No business logic here — only DB queries.
"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuthIdentity


class AuthIdentityRepository:
    """Repository for AuthIdentity lookups and creation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lookup_by_email_hash(
        self,
        *,
        tenant_id: uuid.UUID,
        email_hash: str,
    ) -> Optional[AuthIdentity]:
        """
        Find an active AuthIdentity by (tenant_id, email_hash).

        This is the login lookup path. The tenant_id MUST come from the public
        request context (subdomain / X-Tenant header), NOT from a JWT.

        Returns None if not found or soft-deleted.
        """
        stmt = (
            select(AuthIdentity)
            .where(
                AuthIdentity.tenant_id == tenant_id,
                AuthIdentity.email_hash == email_hash,
                AuthIdentity.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, identity_id: uuid.UUID) -> Optional[AuthIdentity]:
        """Return an active AuthIdentity by PK. Returns None if not found."""
        stmt = select(AuthIdentity).where(
            AuthIdentity.id == identity_id,
            AuthIdentity.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, identity: AuthIdentity) -> AuthIdentity:
        """Persist a new AuthIdentity and return it refreshed."""
        self._session.add(identity)
        await self._session.commit()
        await self._session.refresh(identity)
        return identity

    async def save(self, identity: AuthIdentity) -> AuthIdentity:
        """Persist changes to an existing AuthIdentity."""
        await self._session.commit()
        await self._session.refresh(identity)
        return identity
