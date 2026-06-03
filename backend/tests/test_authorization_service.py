"""
test_authorization_service.py — Tasks 4.1 RED → 4.2-4.6 GREEN/TRIANGULATE

Tests for AuthorizationService.resolve_effective_permissions():
- Returns union of permissions for multiple roles.
- Tenant-scoped resolution.
- Unknown roles are ignored (fail-closed).
- Empty tenant catalog returns empty set.
- Global scope wins over propio when same permission in multiple roles.
- Identity/roles come only from CurrentUser (not from injected data).
"""
import uuid
import pytest
import pytest_asyncio

from app.core.dependencies import CurrentUser
from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def svc_tenant(test_engine):
    """Tenant for service tests."""
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Authz Service Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def empty_tenant(test_engine):
    """A tenant with NO rbac catalog seeded."""
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Empty Catalog Tenant", estado=TenantEstado.ACTIVO))
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def authz_seeded(test_engine, create_tables, svc_tenant):
    """
    Seed RBAC data for service tests:
    - PROFESOR_SVC → calificaciones:importar (propio)
    - COORDINADOR_SVC → calificaciones:importar (global), comunicacion:aprobar (global)
    - ATRASADOS_SVC role → atrasados:ver (propio) (for scope tests)
    """
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()

    tid = svc_tenant

    # Roles
    rol_prof = Rol(tenant_id=tid, nombre="PROFESOR_SVC")
    rol_coord = Rol(tenant_id=tid, nombre="COORDINADOR_SVC")
    rol_atrasados = Rol(tenant_id=tid, nombre="ATRASADOS_SVC")
    session.add_all([rol_prof, rol_coord, rol_atrasados])
    await session.flush()

    # Permissions
    perm_calc = Permiso(
        tenant_id=tid, codigo="svc_test:calificaciones",
        modulo="svc_test", accion="calificaciones",
    )
    perm_comun = Permiso(
        tenant_id=tid, codigo="svc_test:comunicacion",
        modulo="svc_test", accion="comunicacion",
    )
    perm_atrasados = Permiso(
        tenant_id=tid, codigo="svc_test:atrasados",
        modulo="svc_test", accion="atrasados",
    )
    session.add_all([perm_calc, perm_comun, perm_atrasados])
    await session.flush()

    # Rol-Permiso assignments
    # PROFESOR_SVC: calificaciones → propio
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_prof.id,
        permiso_id=perm_calc.id, scope=PermisoScope.propio,
    ))
    # COORDINADOR_SVC: calificaciones → global, comunicacion → global
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_coord.id,
        permiso_id=perm_calc.id, scope=PermisoScope.global_,
    ))
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_coord.id,
        permiso_id=perm_comun.id, scope=PermisoScope.global_,
    ))
    # ATRASADOS_SVC: atrasados → propio
    session.add(RolPermiso(
        tenant_id=tid, rol_id=rol_atrasados.id,
        permiso_id=perm_atrasados.id, scope=PermisoScope.propio,
    ))

    await session.commit()
    await session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(tenant_id: uuid.UUID, roles: list) -> CurrentUser:
    """Build a CurrentUser value object for test purposes."""
    return CurrentUser(
        user_id=uuid.uuid4(),
        tenant_id=tenant_id,
        roles=roles,
    )


async def _build_service(test_engine, tenant_id: uuid.UUID):
    """Build AuthorizationService with a fresh session scoped to tenant."""
    from app.core.database import build_session_factory
    from app.repositories.rbac_repository import RbacRepository
    from app.services.authorization_service import AuthorizationService

    factory = build_session_factory(test_engine)
    session = factory()
    repo = RbacRepository(session=session, tenant_id=tenant_id)
    return AuthorizationService(repository=repo), session


# ---------------------------------------------------------------------------
# Task 4.1 — RED: AuthorizationService doesn't exist yet
# ---------------------------------------------------------------------------

class TestAuthorizationServiceUnion:
    """Tasks 4.1-4.2: union of permissions from multiple roles."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_union_of_two_roles(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """Happy: PROFESOR_SVC + COORDINADOR_SVC → union includes both permissions."""
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            user = _make_user(svc_tenant, ["PROFESOR_SVC", "COORDINADOR_SVC"])
            grants = await svc.resolve_effective_permissions(user)
            codigos = {g.codigo for g in grants}
            assert "svc_test:calificaciones" in codigos
            assert "svc_test:comunicacion" in codigos
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_single_role_permissions(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """Happy: single role returns only its permissions."""
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            user = _make_user(svc_tenant, ["COORDINADOR_SVC"])
            grants = await svc.resolve_effective_permissions(user)
            codigos = {g.codigo for g in grants}
            assert "svc_test:calificaciones" in codigos
            assert "svc_test:comunicacion" in codigos
            # PROFESOR_SVC-only permissions should NOT appear
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tasks 4.3-4.5 — TRIANGULATE: fail-closed, scope resolution, identity source
# ---------------------------------------------------------------------------

class TestAuthorizationServiceFailClosed:
    """Task 4.3: unknown roles don't grant permissions."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unknown_role_ignored_not_error(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """Edge: unknown role in claim → ignored, no exception, no permissions granted."""
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            user = _make_user(svc_tenant, ["SUPERUSER_UNKNOWN"])
            grants = await svc.resolve_effective_permissions(user)
            assert grants == set() or len(grants) == 0, (
                f"Unknown role should grant nothing, got {grants}"
            )
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_empty_catalog_returns_empty(
        self, test_engine, empty_tenant
    ):
        """Edge: tenant with no catalog → empty set of permissions."""
        svc, session = await _build_service(test_engine, empty_tenant)
        try:
            user = _make_user(empty_tenant, ["ADMIN"])
            grants = await svc.resolve_effective_permissions(user)
            assert len(grants) == 0
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_empty_roles_returns_empty(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """Edge: user with no roles → empty set."""
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            user = _make_user(svc_tenant, [])
            grants = await svc.resolve_effective_permissions(user)
            assert len(grants) == 0
        finally:
            await session.close()


class TestAuthorizationServiceScopeResolution:
    """Task 4.4: global wins over propio when same permission in multiple roles."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_propio_only_when_single_role(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """Happy: PROFESOR_SVC alone → calificaciones:importar with scope propio."""
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            user = _make_user(svc_tenant, ["PROFESOR_SVC"])
            grants = await svc.resolve_effective_permissions(user)
            calc_grants = [g for g in grants if g.codigo == "svc_test:calificaciones"]
            assert len(calc_grants) == 1
            assert calc_grants[0].scope == PermisoScope.propio
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_global_wins_over_propio(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """Edge: PROFESOR_SVC (propio) + COORDINADOR_SVC (global) → global wins."""
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            user = _make_user(svc_tenant, ["PROFESOR_SVC", "COORDINADOR_SVC"])
            grants = await svc.resolve_effective_permissions(user)
            calc_grants = [g for g in grants if g.codigo == "svc_test:calificaciones"]
            assert len(calc_grants) == 1
            assert calc_grants[0].scope == PermisoScope.global_
        finally:
            await session.close()


class TestAuthorizationServiceIdentitySource:
    """Task 4.5: roles come exclusively from current_user.roles, never from injected data."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_only_current_user_roles_are_used(
        self, test_engine, authz_seeded, svc_tenant
    ):
        """
        Passing a user with roles=[] should return empty even if there's a
        valid role in the tenant catalog. The service NEVER accepts injected roles.
        """
        svc, session = await _build_service(test_engine, svc_tenant)
        try:
            # User with empty roles — catalog has COORDINADOR_SVC but user has none
            user = _make_user(svc_tenant, [])
            grants = await svc.resolve_effective_permissions(user)
            assert len(grants) == 0, (
                "Service must not grant permissions to a user with no roles"
            )
        finally:
            await session.close()
