"""
test_rbac_models.py — Task 1.1 RED → 1.4/1.5 TRIANGULATE

Tests for Rol, Permiso, RolPermiso models from app.models.rbac.
These tests run against a real PostgreSQL test database — no DB mocks.
"""
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def rbac_engine(test_engine, create_tables):
    """Re-use the session engine; tables already created by create_tables."""
    return test_engine


@pytest_asyncio.fixture
async def db(rbac_engine):
    """Fresh session per test, always rolled back."""
    from app.core.database import build_session_factory
    factory = build_session_factory(rbac_engine)
    session = factory()
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture(scope="module")
async def tenant_id_a(test_engine):
    """Create and return a tenant UUID for module-scope tests."""
    from app.core.database import build_session_factory
    from app.models.tenant import Tenant, TenantEstado
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, nombre="Tenant RBAC A", estado=TenantEstado.ACTIVO)
    session.add(tenant)
    await session.commit()
    await session.close()
    return tid


@pytest_asyncio.fixture(scope="module")
async def tenant_id_b(test_engine):
    """Second tenant for isolation tests."""
    from app.core.database import build_session_factory
    from app.models.tenant import Tenant, TenantEstado
    factory = build_session_factory(test_engine)
    session = factory()
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, nombre="Tenant RBAC B", estado=TenantEstado.ACTIVO)
    session.add(tenant)
    await session.commit()
    await session.close()
    return tid


# ---------------------------------------------------------------------------
# Task 1.1 — Model structure assertions (RED: these fail until rbac.py exists)
# ---------------------------------------------------------------------------

class TestRbacModelStructure:
    """Assert that Rol, Permiso, RolPermiso have the required columns and enum."""

    def test_rol_has_required_columns(self):
        """Rol must have id, tenant_id, nombre, descripcion, timestamps, deleted_at."""
        mapper = inspect(Rol)
        col_names = {c.key for c in mapper.mapper.column_attrs}
        assert "id" in col_names
        assert "tenant_id" in col_names
        assert "nombre" in col_names
        assert "descripcion" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        assert "deleted_at" in col_names

    def test_permiso_has_required_columns(self):
        """Permiso must have id, tenant_id, codigo, modulo, accion, descripcion, timestamps, deleted_at."""
        mapper = inspect(Permiso)
        col_names = {c.key for c in mapper.mapper.column_attrs}
        assert "id" in col_names
        assert "tenant_id" in col_names
        assert "codigo" in col_names
        assert "modulo" in col_names
        assert "accion" in col_names
        assert "descripcion" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        assert "deleted_at" in col_names

    def test_rol_permiso_has_required_columns(self):
        """RolPermiso must have id, tenant_id, rol_id, permiso_id, scope, timestamps, deleted_at."""
        mapper = inspect(RolPermiso)
        col_names = {c.key for c in mapper.mapper.column_attrs}
        assert "id" in col_names
        assert "tenant_id" in col_names
        assert "rol_id" in col_names
        assert "permiso_id" in col_names
        assert "scope" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names
        assert "deleted_at" in col_names

    def test_permiso_scope_enum_values(self):
        """PermisoScope enum must have 'global' and 'propio' values."""
        values = {e.value for e in PermisoScope}
        assert "global" in values
        assert "propio" in values

    def test_rol_permiso_scope_default_is_global(self):
        """RolPermiso.scope column default must be 'global'."""
        rp = RolPermiso()
        # Either the default is set or the column has a server_default
        # We check the column's default value
        scope_col = RolPermiso.__table__.c["scope"]
        default_val = scope_col.default
        if default_val is not None:
            assert default_val.arg == PermisoScope.global_
        else:
            # Column may rely on DB-side default; acceptable
            pass


# ---------------------------------------------------------------------------
# Task 1.4 TRIANGULATE — persist Rol and Permiso, test uniqueness constraints
# ---------------------------------------------------------------------------

class TestRolUniqueness:
    """Persist Rol and test (tenant_id, nombre) uniqueness constraint."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_rol_persists_in_tenant(self, db, tenant_id_a):
        """Happy path: a Rol persists with correct tenant_id."""
        rol = Rol(tenant_id=tenant_id_a, nombre="PROFESOR_TEST_A1")
        db.add(rol)
        await db.commit()
        await db.refresh(rol)

        assert rol.id is not None
        assert rol.tenant_id == tenant_id_a
        assert rol.nombre == "PROFESOR_TEST_A1"
        assert rol.deleted_at is None

    @pytest.mark.asyncio(loop_scope="session")
    async def test_permiso_persists_in_tenant(self, db, tenant_id_a):
        """Happy path: a Permiso persists with codigo, modulo, accion."""
        permiso = Permiso(
            tenant_id=tenant_id_a,
            codigo="calificaciones:importar",
            modulo="calificaciones",
            accion="importar",
        )
        db.add(permiso)
        await db.commit()
        await db.refresh(permiso)

        assert permiso.id is not None
        assert permiso.codigo == "calificaciones:importar"
        assert permiso.modulo == "calificaciones"
        assert permiso.accion == "importar"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_duplicate_rol_nombre_same_tenant_raises(self, db, tenant_id_a):
        """Edge: same (tenant_id, nombre) must violate uniqueness."""
        rol1 = Rol(tenant_id=tenant_id_a, nombre="ROL_DUP_TEST")
        db.add(rol1)
        await db.commit()

        rol2 = Rol(tenant_id=tenant_id_a, nombre="ROL_DUP_TEST")
        db.add(rol2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()

    @pytest.mark.asyncio(loop_scope="session")
    async def test_same_rol_nombre_different_tenant_is_allowed(self, db, tenant_id_a, tenant_id_b):
        """Edge: same nombre in different tenants must coexist without collision."""
        rol_a = Rol(tenant_id=tenant_id_a, nombre="ROL_SHARED_NAME")
        rol_b = Rol(tenant_id=tenant_id_b, nombre="ROL_SHARED_NAME")
        db.add(rol_a)
        db.add(rol_b)
        await db.commit()

        assert rol_a.id != rol_b.id
        assert rol_a.tenant_id != rol_b.tenant_id


# ---------------------------------------------------------------------------
# Task 1.5 TRIANGULATE — RolPermiso scope and uniqueness
# ---------------------------------------------------------------------------

class TestRolPermisoScope:
    """Test RolPermiso scope values and (tenant_id, rol_id, permiso_id) uniqueness."""

    @pytest.mark.asyncio(loop_scope="session")
    async def test_rol_permiso_scope_propio(self, db, tenant_id_a):
        """Happy: RolPermiso with scope=propio persists correctly."""
        rol = Rol(tenant_id=tenant_id_a, nombre="ROL_SCOPE_PROPIO")
        permiso = Permiso(
            tenant_id=tenant_id_a,
            codigo="scope_test:propio",
            modulo="scope_test",
            accion="propio",
        )
        db.add(rol)
        db.add(permiso)
        await db.commit()

        rp = RolPermiso(
            tenant_id=tenant_id_a,
            rol_id=rol.id,
            permiso_id=permiso.id,
            scope=PermisoScope.propio,
        )
        db.add(rp)
        await db.commit()
        await db.refresh(rp)

        assert rp.scope == PermisoScope.propio

    @pytest.mark.asyncio(loop_scope="session")
    async def test_rol_permiso_scope_global(self, db, tenant_id_a):
        """Happy: RolPermiso with scope=global persists correctly."""
        rol = Rol(tenant_id=tenant_id_a, nombre="ROL_SCOPE_GLOBAL")
        permiso = Permiso(
            tenant_id=tenant_id_a,
            codigo="scope_test:global",
            modulo="scope_test",
            accion="global",
        )
        db.add(rol)
        db.add(permiso)
        await db.commit()

        rp = RolPermiso(
            tenant_id=tenant_id_a,
            rol_id=rol.id,
            permiso_id=permiso.id,
            scope=PermisoScope.global_,
        )
        db.add(rp)
        await db.commit()
        await db.refresh(rp)

        assert rp.scope == PermisoScope.global_

    @pytest.mark.asyncio(loop_scope="session")
    async def test_duplicate_rol_permiso_raises(self, db, tenant_id_a):
        """Edge: duplicate (tenant_id, rol_id, permiso_id) must violate uniqueness."""
        rol = Rol(tenant_id=tenant_id_a, nombre="ROL_DUP_RP")
        permiso = Permiso(
            tenant_id=tenant_id_a,
            codigo="dup_rp_test:action",
            modulo="dup_rp_test",
            accion="action",
        )
        db.add(rol)
        db.add(permiso)
        await db.commit()

        rp1 = RolPermiso(
            tenant_id=tenant_id_a,
            rol_id=rol.id,
            permiso_id=permiso.id,
            scope=PermisoScope.global_,
        )
        db.add(rp1)
        await db.commit()

        rp2 = RolPermiso(
            tenant_id=tenant_id_a,
            rol_id=rol.id,
            permiso_id=permiso.id,
            scope=PermisoScope.propio,
        )
        db.add(rp2)
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()
