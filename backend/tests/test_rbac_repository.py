"""
test_rbac_repository.py — Tasks 3.1, 3.3 RED/TRIANGULATE

Tests for RbacRepository.get_roles_with_permissions():
- Returns RolPermiso objects for requested role names, scoped to tenant.
- Tenant isolation: tenant A does not see tenant B's rows.
- Missing role names return empty result.
"""
import uuid
import pytest
import pytest_asyncio
from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope
from app.models.tenant import Tenant, TenantEstado


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def repo_tenant_a(test_engine):
    """Tenant A for repository tests."""
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Repo Tenant A", estado=TenantEstado.ACTIVO))
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def repo_tenant_b(test_engine):
    """Tenant B for isolation tests."""
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    session.add(Tenant(id=tid, nombre="Repo Tenant B", estado=TenantEstado.ACTIVO))
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def seeded_tenants(test_engine, create_tables, repo_tenant_a, repo_tenant_b):
    """
    Seed minimal RBAC data for two tenants.
    Returns dict {tenant_id: {role_name: rol_id, ...}, ...}
    """
    from app.core.database import build_session_factory
    factory = build_session_factory(test_engine)
    session = factory()

    data = {repo_tenant_a: {}, repo_tenant_b: {}}

    for tid in [repo_tenant_a, repo_tenant_b]:
        # Create PROFESOR role
        rol_prof = Rol(tenant_id=tid, nombre="PROFESOR_REPO")
        rol_coord = Rol(tenant_id=tid, nombre="COORDINADOR_REPO")
        session.add(rol_prof)
        session.add(rol_coord)
        await session.flush()

        # Create permissions
        perm_calc = Permiso(
            tenant_id=tid, codigo="repo_test:calificaciones",
            modulo="repo_test", accion="calificaciones",
        )
        perm_comun = Permiso(
            tenant_id=tid, codigo="repo_test:comunicacion",
            modulo="repo_test", accion="comunicacion",
        )
        session.add(perm_calc)
        session.add(perm_comun)
        await session.flush()

        # Assign: PROFESOR_REPO → calificaciones (propio), COORDINADOR_REPO → comunicacion (global)
        rp1 = RolPermiso(
            tenant_id=tid, rol_id=rol_prof.id,
            permiso_id=perm_calc.id, scope=PermisoScope.propio,
        )
        rp2 = RolPermiso(
            tenant_id=tid, rol_id=rol_coord.id,
            permiso_id=perm_comun.id, scope=PermisoScope.global_,
        )
        session.add(rp1)
        session.add(rp2)

        data[tid]["PROFESOR_REPO"] = rol_prof.id
        data[tid]["COORDINADOR_REPO"] = rol_coord.id

    await session.commit()
    await session.close()
    return data


# ---------------------------------------------------------------------------
# Task 3.1 — RED: RbacRepository doesn't exist yet
# ---------------------------------------------------------------------------

class TestRbacRepositoryHappyPath:
    """Task 3.1 → 3.2: basic query returns correct RolPermiso objects."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_roles_with_permissions_returns_rol_permiso(
        self, test_engine, create_tables, seeded_tenants, repo_tenant_a
    ):
        """Happy: get_roles_with_permissions returns RolPermiso for requested roles."""
        from app.core.database import build_session_factory
        from app.repositories.rbac_repository import RbacRepository

        factory = build_session_factory(test_engine)
        session = factory()
        try:
            repo = RbacRepository(session=session, tenant_id=repo_tenant_a)
            results = await repo.get_roles_with_permissions(["PROFESOR_REPO"])
            assert len(results) >= 1
            scopes = {rp.scope for rp in results}
            # PROFESOR_REPO has calificaciones propio
            assert PermisoScope.propio in scopes
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_roles_with_permissions_includes_permiso(
        self, test_engine, create_tables, seeded_tenants, repo_tenant_a
    ):
        """Happy: each RolPermiso result has a loaded permiso with codigo."""
        from app.core.database import build_session_factory
        from app.repositories.rbac_repository import RbacRepository

        factory = build_session_factory(test_engine)
        session = factory()
        try:
            repo = RbacRepository(session=session, tenant_id=repo_tenant_a)
            results = await repo.get_roles_with_permissions(["PROFESOR_REPO"])
            assert any(rp.permiso.codigo == "repo_test:calificaciones" for rp in results)
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_multiple_roles_union(
        self, test_engine, create_tables, seeded_tenants, repo_tenant_a
    ):
        """Happy: multiple role names returns union of permissions."""
        from app.core.database import build_session_factory
        from app.repositories.rbac_repository import RbacRepository

        factory = build_session_factory(test_engine)
        session = factory()
        try:
            repo = RbacRepository(session=session, tenant_id=repo_tenant_a)
            results = await repo.get_roles_with_permissions(
                ["PROFESOR_REPO", "COORDINADOR_REPO"]
            )
            codigos = {rp.permiso.codigo for rp in results}
            assert "repo_test:calificaciones" in codigos
            assert "repo_test:comunicacion" in codigos
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Task 3.3 — TRIANGULATE: tenant isolation and missing roles
# ---------------------------------------------------------------------------

class TestRbacRepositoryIsolation:
    """Task 3.3: tenant A cannot see tenant B's rows; missing roles return empty."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_tenant_isolation(
        self, test_engine, create_tables, seeded_tenants, repo_tenant_a, repo_tenant_b
    ):
        """Edge: RbacRepository for tenant A never returns tenant B's RolPermiso."""
        from app.core.database import build_session_factory
        from app.repositories.rbac_repository import RbacRepository

        factory = build_session_factory(test_engine)
        session = factory()
        try:
            # Query tenant A
            repo_a = RbacRepository(session=session, tenant_id=repo_tenant_a)
            results_a = await repo_a.get_roles_with_permissions(["PROFESOR_REPO"])
            tenant_ids = {rp.tenant_id for rp in results_a}
            assert repo_tenant_b not in tenant_ids, "Tenant B data leaked into tenant A results"
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unknown_role_returns_empty(
        self, test_engine, create_tables, seeded_tenants, repo_tenant_a
    ):
        """Edge: unknown role name returns empty list — fail-closed."""
        from app.core.database import build_session_factory
        from app.repositories.rbac_repository import RbacRepository

        factory = build_session_factory(test_engine)
        session = factory()
        try:
            repo = RbacRepository(session=session, tenant_id=repo_tenant_a)
            results = await repo.get_roles_with_permissions(["SUPERUSER_UNKNOWN"])
            assert results == [], f"Unknown role should return [], got {results}"
        finally:
            await session.close()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_empty_role_list_returns_empty(
        self, test_engine, create_tables, seeded_tenants, repo_tenant_a
    ):
        """Edge: empty role list returns empty result."""
        from app.core.database import build_session_factory
        from app.repositories.rbac_repository import RbacRepository

        factory = build_session_factory(test_engine)
        session = factory()
        try:
            repo = RbacRepository(session=session, tenant_id=repo_tenant_a)
            results = await repo.get_roles_with_permissions([])
            assert results == []
        finally:
            await session.close()
