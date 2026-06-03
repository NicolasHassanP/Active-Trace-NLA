"""
AuthorizationService — resolves effective permissions for a CurrentUser.

C-04: Server-side permission resolution, per-request.

Design decisions (design.md D3, D4, D5):
    - Roles come EXCLUSIVELY from current_user.roles (the JWT claim).
      NEVER from request params, body, or headers.
    - Queries the RbacRepository (no direct DB access from service).
    - Returns a set of PermissionGrant objects (codigo, scope).
    - Unknown role names are silently ignored — fail-closed (D3).
    - When same permission code appears in multiple roles with different
      scopes, 'global' takes precedence over 'propio' (D4).

Usage::

    repo = RbacRepository(session=session, tenant_id=current_user.tenant_id)
    svc = AuthorizationService(repository=repo)
    grants = await svc.resolve_effective_permissions(current_user)
"""
from dataclasses import dataclass
from typing import Set

from app.core.dependencies import CurrentUser
from app.models.rbac import PermisoScope
from app.repositories.rbac_repository import RbacRepository


# ---------------------------------------------------------------------------
# PermissionGrant — value object returned by the service
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PermissionGrant:
    """
    Immutable grant: a permission code with its effective scope.

    scope = 'global'  — the user may operate on all tenant data.
    scope = 'propio'  — the user may only operate on their own data.
                        The endpoint consumer is responsible for applying
                        the row-level filter when scope == propio.
    """
    codigo: str
    scope: PermisoScope


# ---------------------------------------------------------------------------
# Scope resolution helper (pure function — tested in isolation)
# ---------------------------------------------------------------------------

def resolve_scope(existing: PermisoScope, incoming: PermisoScope) -> PermisoScope:
    """
    Return the most permissive scope between two values.

    Rule (D4): 'global' always wins over 'propio'.
    If either scope is global, the result is global.
    """
    if existing == PermisoScope.global_ or incoming == PermisoScope.global_:
        return PermisoScope.global_
    return PermisoScope.propio


# ---------------------------------------------------------------------------
# AuthorizationService
# ---------------------------------------------------------------------------

class AuthorizationService:
    """
    Resolves the effective permission set for a CurrentUser by tenant.

    Depends on RbacRepository for all DB access — no direct queries here.
    """

    def __init__(self, repository: RbacRepository) -> None:
        self._repo = repository

    async def resolve_effective_permissions(
        self, current_user: CurrentUser
    ) -> Set[PermissionGrant]:
        """
        Resolve the effective permission set for *current_user*.

        Algorithm:
        1. Fetch all active RolPermiso rows for current_user.roles from the
           tenant catalog (via repository — single JOIN query).
        2. For each (codigo, scope) pair, merge using the resolve_scope rule:
           global wins over propio when the same code appears in multiple roles.
        3. Return a frozenset of PermissionGrant objects.

        Roles in the claim that have no matching Rol in the tenant catalog
        contribute nothing (fail-closed, D3).
        """
        # Identity comes ONLY from the verified JWT (current_user.roles).
        role_names = list(current_user.roles)
        if not role_names:
            return set()

        rol_permisos = await self._repo.get_roles_with_permissions(role_names)

        # Merge: codigo → most-permissive scope
        effective: dict[str, PermisoScope] = {}
        for rp in rol_permisos:
            codigo = rp.permiso.codigo
            scope = rp.scope
            if codigo in effective:
                effective[codigo] = resolve_scope(effective[codigo], scope)
            else:
                effective[codigo] = scope

        return {PermissionGrant(codigo=c, scope=s) for c, s in effective.items()}
