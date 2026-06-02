"""
Tests for the Tenant model (table: tenants).
TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""
import uuid
import pytest

from sqlalchemy import inspect as sa_inspect


# ==============================================================================
# 4.1 RED: Tenant creation with valid data persists with UUID and timestamps
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_tenant_creation_persists_with_uuid_and_timestamps(db_session, create_tables, test_engine):
    """Creating a Tenant persists with id UUID and timestamps."""
    from app.models.tenant import Tenant, TenantEstado

    tenant = Tenant(nombre="Academia Test", estado=TenantEstado.ACTIVO)
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    assert tenant.id is not None
    assert isinstance(tenant.id, uuid.UUID)
    assert tenant.created_at is not None
    assert tenant.updated_at is not None
    assert tenant.nombre == "Academia Test"
    assert tenant.estado == TenantEstado.ACTIVO

    await db_session.delete(tenant)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_tenant_table_has_no_tenant_id_column(db_session):
    """The tenants table does NOT have a tenant_id column (it is the root)."""
    from app.models.tenant import Tenant

    mapper = sa_inspect(Tenant)
    col_names = [c.key for c in mapper.mapper.columns]
    assert "tenant_id" not in col_names, "Tenant table must not have tenant_id (it is the root)"
    assert "id" in col_names
    assert "nombre" in col_names
    assert "estado" in col_names
    assert "created_at" in col_names
    assert "updated_at" in col_names
    assert "deleted_at" in col_names


# ==============================================================================
# 4.3 TRIANGULATE: business entity with TenantScopedBase has tenant_id
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_business_entity_has_tenant_id_asymmetry(db_session, create_tables, test_engine):
    """
    A business entity (TenantScopedBase) has tenant_id; Tenant does not.
    Confirms the root vs business entity asymmetry.
    """
    from app.models.tenant import Tenant
    from app.models.mixins import TenantScopedBase
    from app.core.database import Base
    from sqlalchemy.orm import Mapped, mapped_column
    from sqlalchemy import String

    class _SampleBizEntity(Base, TenantScopedBase):
        __tablename__ = "test_sample_biz_entity"
        __table_args__ = {"extend_existing": True}
        label: Mapped[str] = mapped_column(String(64))

    async with test_engine.begin() as conn:
        await conn.run_sync(_SampleBizEntity.__table__.create, checkfirst=True)

    # Tenant has no tenant_id
    tenant_cols = [c.key for c in sa_inspect(Tenant).mapper.columns]
    assert "tenant_id" not in tenant_cols

    # Business entity has tenant_id
    biz_cols = [c.key for c in sa_inspect(_SampleBizEntity).mapper.columns]
    assert "tenant_id" in biz_cols
