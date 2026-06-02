"""
Tests for TenantScopedRepository — multi-tenant isolation, soft delete,
creation enforcement and query scope.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""
import uuid
import pytest
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, delete as sa_delete, text

from app.core.database import Base
from app.models.mixins import TenantScopedBase
from app.models.tenant import Tenant, TenantEstado


# ---------------------------------------------------------------------------
# Helper: a minimal business entity for repo tests
# ---------------------------------------------------------------------------

class _Nota(Base, TenantScopedBase):
    """Minimal entity used exclusively by this test module."""
    __tablename__ = "test_notas"
    __table_args__ = {"extend_existing": True}
    titulo: Mapped[str] = mapped_column(String(128))


async def _make_tenant(db_session, nombre="Tenant Test") -> Tenant:
    t = Tenant(nombre=nombre, estado=TenantEstado.ACTIVO)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


async def _cleanup(db_session, tenant_ids):
    """Clean up test data: delete all notas for tenants, then tenants."""
    try:
        await db_session.rollback()
    except Exception:
        pass
    for tid in tenant_ids:
        await db_session.execute(
            sa_delete(_Nota).where(_Nota.tenant_id == tid)
        )
        await db_session.execute(
            sa_delete(Tenant).where(Tenant.id == tid)
        )
    await db_session.commit()


# ==============================================================================
# 6.1 RED: A repository scoped to tenant A only returns A's records
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_list_returns_only_tenant_scoped_records(db_session, create_tables):
    """
    With records for tenants A and B, a repository scoped to A returns only A's records.
    """
    from app.repositories.base import TenantScopedRepository

    tenant_a = await _make_tenant(db_session, "Tenant A list")
    tenant_b = await _make_tenant(db_session, "Tenant B list")

    try:
        repo_a = TenantScopedRepository(_Nota, db_session, tenant_a.id)
        repo_b = TenantScopedRepository(_Nota, db_session, tenant_b.id)

        await repo_a.add(_Nota(titulo="nota A1"))
        await repo_a.add(_Nota(titulo="nota A2"))
        await repo_b.add(_Nota(titulo="nota B1"))

        records = await repo_a.list()
        titulos = {r.titulo for r in records}
        assert "nota A1" in titulos
        assert "nota A2" in titulos
        assert "nota B1" not in titulos
    finally:
        await _cleanup(db_session, [tenant_a.id, tenant_b.id])


# ==============================================================================
# 6.3 TRIANGULATE: get_by_id from wrong tenant returns None
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_get_by_id_from_wrong_tenant_returns_none(db_session, create_tables):
    """
    A repository scoped to tenant A cannot retrieve a record of tenant B by ID.
    """
    from app.repositories.base import TenantScopedRepository

    tenant_a = await _make_tenant(db_session, "Tenant A getbyid")
    tenant_b = await _make_tenant(db_session, "Tenant B getbyid")

    try:
        repo_a = TenantScopedRepository(_Nota, db_session, tenant_a.id)
        repo_b = TenantScopedRepository(_Nota, db_session, tenant_b.id)

        nota_b = await repo_b.add(_Nota(titulo="nota privada B"))

        result = await repo_a.get_by_id(nota_b.id)
        assert result is None

        result_b = await repo_b.get_by_id(nota_b.id)
        assert result_b is not None
    finally:
        await _cleanup(db_session, [tenant_a.id, tenant_b.id])


# ==============================================================================
# 6.4 RED: Creating via scoped repo fixes tenant_id regardless of input
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_add_fixes_tenant_id_from_scope(db_session, create_tables):
    """
    Creating an entity via a repository scoped to A sets tenant_id=A,
    even if the entity was built with a different tenant_id.
    """
    from app.repositories.base import TenantScopedRepository

    tenant_a = await _make_tenant(db_session, "Tenant A add-fix")
    tenant_b = await _make_tenant(db_session, "Tenant B add-fix")

    try:
        repo_a = TenantScopedRepository(_Nota, db_session, tenant_a.id)

        entity = _Nota(titulo="forzado")
        entity.tenant_id = tenant_b.id

        persisted = await repo_a.add(entity)
        assert persisted.tenant_id == tenant_a.id
    finally:
        await _cleanup(db_session, [tenant_a.id, tenant_b.id])


# ==============================================================================
# 6.6 TRIANGULATE: No method accepts tenant_id as parameter
# ==============================================================================

def test_read_methods_do_not_accept_tenant_id_parameter():
    """No read method on TenantScopedRepository accepts tenant_id as a param."""
    import inspect
    from app.repositories.base import TenantScopedRepository

    for method_name in ("list", "get_by_id"):
        method = getattr(TenantScopedRepository, method_name)
        sig = inspect.signature(method)
        assert "tenant_id" not in sig.parameters, (
            f"{method_name} must not accept tenant_id parameter"
        )


# ==============================================================================
# 7.1 RED: Soft delete — deleted record not in list() by default
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_soft_delete_hides_from_default_list(db_session, create_tables):
    """
    After delete(), the record does not appear in list() by default,
    but the row still exists physically in the table.
    """
    from app.repositories.base import TenantScopedRepository

    tenant = await _make_tenant(db_session, "Tenant soft-delete")

    try:
        repo = TenantScopedRepository(_Nota, db_session, tenant.id)

        nota = await repo.add(_Nota(titulo="para borrar"))
        nota_id = nota.id

        await repo.delete(nota)

        records = await repo.list()
        ids = [r.id for r in records]
        assert nota_id not in ids

        # Row still exists physically
        result = await db_session.execute(
            text("SELECT id::text FROM test_notas WHERE id::text = :id"),
            {"id": str(nota_id)},
        )
        raw_row = result.fetchone()
        assert raw_row is not None, "Row must still exist after soft delete"
    finally:
        await _cleanup(db_session, [tenant.id])


# ==============================================================================
# 7.3 TRIANGULATE: list(include_deleted=True) returns deleted records
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_list_include_deleted_returns_deleted_records(db_session, create_tables):
    """list(include_deleted=True) returns soft-deleted records."""
    from app.repositories.base import TenantScopedRepository

    tenant = await _make_tenant(db_session, "Tenant include-deleted")

    try:
        repo = TenantScopedRepository(_Nota, db_session, tenant.id)

        nota = await repo.add(_Nota(titulo="borrada"))
        nota_id = nota.id

        await repo.delete(nota)

        default = await repo.list()
        assert nota_id not in [r.id for r in default]

        with_deleted = await repo.list(include_deleted=True)
        assert nota_id in [r.id for r in with_deleted]
    finally:
        await _cleanup(db_session, [tenant.id])
