"""
RbacRepository — tenant-scoped repository for RBAC catalog queries.

C-04: Resolves rol→permiso grants for a given set of role names, always
scoped to the tenant bound at construction time. No direct DB access from
services — all RBAC queries go through this repository.

Design decisions (design.md D3, D5):
    - Built on TenantScopedRepository pattern (tenant_id bound in constructor).
    - Primary query: get_roles_with_permissions(role_names) returns the list
      of active RolPermiso records (with loaded Permiso) for the named roles
      within the tenant. This is the one JOIN the AuthorizationService needs.
    - Empty or unknown role names return [] — fail-closed by construction.
    - Soft-deleted rows are excluded (deleted_at IS NULL).
"""
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Permiso, Rol, RolPermiso


class RbacRepository:
    """
    Tenant-scoped repository for RBAC catalog reads.

    Usage::

        repo = RbacRepository(session=session, tenant_id=current_user.tenant_id)
        grants = await repo.get_roles_with_permissions(current_user.roles)
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def get_roles_with_permissions(
        self, role_names: List[str]
    ) -> List[RolPermiso]:
        """
        Return all active RolPermiso records (with loaded Permiso) for the
        given role names, scoped to this tenant.

        Unknown role names contribute no results — fail-closed.
        An empty role_names list returns [].

        Each RolPermiso in the result has rp.permiso pre-loaded (via
        selectinload) so callers can access rp.permiso.codigo without
        triggering lazy-load errors in async context.
        """
        if not role_names:
            return []

        stmt = (
            select(RolPermiso)
            .join(Rol, RolPermiso.rol_id == Rol.id)
            .join(Permiso, RolPermiso.permiso_id == Permiso.id)
            .where(
                Rol.tenant_id == self._tenant_id,
                Rol.nombre.in_(role_names),
                Rol.deleted_at.is_(None),
                RolPermiso.tenant_id == self._tenant_id,
                RolPermiso.deleted_at.is_(None),
                Permiso.tenant_id == self._tenant_id,
                Permiso.deleted_at.is_(None),
            )
            .options(selectinload(RolPermiso.permiso))
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
