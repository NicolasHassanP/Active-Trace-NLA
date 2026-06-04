"""
test_aviso_migration.py — TDD tests for C-15 migration 013.

Verifies the migration creates tables, enums, indexes, and seeds RBAC
as expected, without running alembic upgrade (uses SQLAlchemy metadata).

Task 1.1–1.10: Structural verification tests.
"""
import pytest


def _load_migration_013():
    """Load the migration module via importlib to bypass name-starts-with-digit issue."""
    import importlib.util
    import os
    mig_path = os.path.join(
        os.path.dirname(__file__),
        "..", "alembic", "versions", "013_create_avisos_acknowledgment.py"
    )
    spec = importlib.util.spec_from_file_location("_mig_013", mig_path)
    mod = importlib.util.module_from_spec(spec)
    # Stub out the alembic.op import so we don't need a live connection
    import sys
    import types
    # Temporarily patch 'alembic.op' if needed
    _orig = sys.modules.get("alembic.op")
    if _orig is None:
        stub = types.ModuleType("alembic.op")
        sys.modules["alembic.op"] = stub
    try:
        spec.loader.exec_module(mod)
    finally:
        if _orig is None:
            del sys.modules["alembic.op"]
    return mod


def test_migration_revision_constants():
    """1.1: migration 013 has correct revision and down_revision."""
    m = _load_migration_013()
    assert m.revision == "013"
    assert m.down_revision == "012"


def test_migration_has_upgrade_and_downgrade():
    """1.1: migration module has upgrade() and downgrade() functions."""
    m = _load_migration_013()
    assert callable(m.upgrade)
    assert callable(m.downgrade)


def test_aviso_table_in_metadata():
    """1.4: aviso table is registered in SQLAlchemy metadata."""
    import app.models  # noqa
    from app.core.database import Base
    assert "aviso" in Base.metadata.tables


def test_acknowledgment_aviso_table_in_metadata():
    """1.5: acknowledgment_aviso table is registered in SQLAlchemy metadata."""
    import app.models  # noqa
    from app.core.database import Base
    assert "acknowledgment_aviso" in Base.metadata.tables


def test_aviso_table_has_soft_delete():
    """1.4: aviso table has deleted_at column (soft delete)."""
    import app.models  # noqa
    from app.core.database import Base
    aviso_table = Base.metadata.tables["aviso"]
    assert "deleted_at" in aviso_table.c


def test_acknowledgment_table_has_fk_to_aviso():
    """1.5: acknowledgment_aviso.aviso_id has FK to aviso.id."""
    import app.models  # noqa
    from app.core.database import Base
    ack_table = Base.metadata.tables["acknowledgment_aviso"]
    aviso_id_col = ack_table.c["aviso_id"]
    fk_targets = {fk.target_fullname for fk in aviso_id_col.foreign_keys}
    assert "aviso.id" in fk_targets


def test_audit_action_enum_has_aviso_publicar():
    """1.2: AuditAction enum has AVISO_PUBLICAR value."""
    from app.models.audit import AuditAction
    assert hasattr(AuditAction, "AVISO_PUBLICAR")
    assert AuditAction.AVISO_PUBLICAR.value == "AVISO_PUBLICAR"
