"""
Tests for UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin and TenantScopedBase.
TDD: RED → GREEN → TRIANGULATE → REFACTOR
"""
import uuid
import pytest
from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ==============================================================================
# 3.1 RED: Mixin basics — id UUID, created_at, updated_at, deleted_at=None
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_uuid_mixin_sets_id_on_create(db_session, test_engine, create_tables):
    """An entity using UUIDMixin gets an id UUID on creation."""
    from app.models.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

    class _UUIDEntity(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
        __tablename__ = "test_uuid_entity"
        __table_args__ = {"extend_existing": True}
        name: Mapped[str] = mapped_column(String(64))

    async with test_engine.begin() as conn:
        await conn.run_sync(_UUIDEntity.__table__.create, checkfirst=True)

    entity = _UUIDEntity(name="test")
    db_session.add(entity)
    await db_session.flush()

    assert entity.id is not None
    assert isinstance(entity.id, uuid.UUID)
    assert entity.created_at is not None
    assert entity.updated_at is not None
    assert entity.deleted_at is None

    await db_session.rollback()


@pytest.mark.asyncio(loop_scope="session")
async def test_timestamps_set_on_create(db_session, test_engine, create_tables):
    """created_at and updated_at are set when the entity is created."""
    from app.models.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

    class _TSEntity(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
        __tablename__ = "test_ts_entity"
        __table_args__ = {"extend_existing": True}
        name: Mapped[str] = mapped_column(String(64))

    async with test_engine.begin() as conn:
        await conn.run_sync(_TSEntity.__table__.create, checkfirst=True)

    entity = _TSEntity(name="hello")
    db_session.add(entity)
    await db_session.flush()

    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)
    await db_session.rollback()


# ==============================================================================
# 3.4 TRIANGULATE: updated_at changes on modify, created_at stays
# ==============================================================================

@pytest.mark.asyncio(loop_scope="session")
async def test_updated_at_changes_on_modify(db_session, test_engine, create_tables):
    """updated_at is refreshed after modification; created_at stays the same."""
    import asyncio
    from app.models.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

    class _ModEntity(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
        __tablename__ = "test_mod_entity"
        __table_args__ = {"extend_existing": True}
        name: Mapped[str] = mapped_column(String(64))

    async with test_engine.begin() as conn:
        await conn.run_sync(_ModEntity.__table__.create, checkfirst=True)

    entity = _ModEntity(name="before")
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)

    original_created_at = entity.created_at
    original_updated_at = entity.updated_at

    await asyncio.sleep(0.01)

    entity.name = "after"
    await db_session.commit()
    await db_session.refresh(entity)

    assert entity.created_at == original_created_at
    assert entity.updated_at >= original_updated_at

    await db_session.delete(entity)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_tenant_mixin_entity_has_tenant_id(db_session, test_engine, create_tables):
    """An entity with TenantMixin has a non-null tenant_id column."""
    from app.models.mixins import TenantScopedBase
    from sqlalchemy import inspect as sa_inspect

    class _BizEntity(Base, TenantScopedBase):
        __tablename__ = "test_biz_entity_v2"
        __table_args__ = {"extend_existing": True}
        label: Mapped[str] = mapped_column(String(64))

    async with test_engine.begin() as conn:
        await conn.run_sync(_BizEntity.__table__.create, checkfirst=True)

    mapper = sa_inspect(_BizEntity)
    col_names = [c.key for c in mapper.mapper.columns]
    assert "tenant_id" in col_names
    assert "id" in col_names
    assert "created_at" in col_names
    assert "updated_at" in col_names
    assert "deleted_at" in col_names
