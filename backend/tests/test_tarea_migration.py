"""
test_tarea_migration.py — TDD tests for C-16 migration 014.

Tasks 8.1–8.2:
    8.1 Structural verification: tables, enum, indexes, RBAC seed, audit actions
        are registered in SQLAlchemy metadata and the migration file has correct constants.
    8.2 Migration constants (revision, down_revision) and presence of downgrade logic.

NOTE: The test DB uses create_all (not alembic) for table creation.
The structural tests verify the migration SQL and model metadata are consistent.
"""
import pytest


# ---------------------------------------------------------------------------
# Load migration module (same pattern as test_aviso_migration.py)
# ---------------------------------------------------------------------------

def _load_migration_014():
    """Load migration 014 module via importlib."""
    import importlib.util
    import os
    import sys
    import types

    mig_path = os.path.join(
        os.path.dirname(__file__),
        "..", "alembic", "versions", "014_create_tareas_internas.py"
    )
    spec = importlib.util.spec_from_file_location("_mig_014", mig_path)
    mod = importlib.util.module_from_spec(spec)

    _orig = sys.modules.get("alembic.op")
    if _orig is None:
        stub = types.ModuleType("alembic.op")
        sys.modules["alembic.op"] = stub
    try:
        spec.loader.exec_module(mod)
    finally:
        if _orig is None and "alembic.op" in sys.modules:
            del sys.modules["alembic.op"]
    return mod


# ---------------------------------------------------------------------------
# 8.1 — Migration constants and structure
# ---------------------------------------------------------------------------

def test_migration_revision_constants():
    """8.1: migration 014 has revision='014' and down_revision='013'."""
    m = _load_migration_014()
    assert m.revision == "014"
    assert m.down_revision == "013"


def test_migration_has_upgrade_and_downgrade():
    """8.1: migration module has callable upgrade() and downgrade()."""
    m = _load_migration_014()
    assert callable(m.upgrade)
    assert callable(m.downgrade)


def test_tarea_table_in_metadata():
    """8.1: tarea table is registered in SQLAlchemy metadata."""
    import app.models  # noqa
    from app.core.database import Base
    assert "tarea" in Base.metadata.tables


def test_comentario_tarea_table_in_metadata():
    """8.1: comentario_tarea table is registered in SQLAlchemy metadata."""
    import app.models  # noqa
    from app.core.database import Base
    assert "comentario_tarea" in Base.metadata.tables


def test_tarea_table_has_expected_columns():
    """8.1: tarea table has all required columns."""
    import app.models  # noqa
    from app.core.database import Base
    tarea_table = Base.metadata.tables["tarea"]
    cols = {c.name for c in tarea_table.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "asignado_a" in cols
    assert "asignado_por" in cols
    assert "descripcion" in cols
    assert "estado" in cols
    assert "materia_id" in cols
    assert "contexto_id" in cols
    assert "contexto_tipo" in cols
    assert "deleted_at" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_comentario_tarea_table_has_expected_columns():
    """8.1: comentario_tarea table has all required columns."""
    import app.models  # noqa
    from app.core.database import Base
    com_table = Base.metadata.tables["comentario_tarea"]
    cols = {c.name for c in com_table.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "tarea_id" in cols
    assert "autor_id" in cols
    assert "cuerpo" in cols
    assert "es_sistema" in cols
    assert "deleted_at" in cols


def test_tarea_contexto_id_has_no_fk():
    """8.1: D4 — contexto_id has NO FK constraint."""
    import app.models  # noqa
    from app.core.database import Base
    tarea_table = Base.metadata.tables["tarea"]
    contexto_id_col = tarea_table.c["contexto_id"]
    assert len(contexto_id_col.foreign_keys) == 0, "contexto_id must NOT have FK (D4)"


def test_tarea_has_fks_to_usuario():
    """8.1: tarea.asignado_a and asignado_por have FK to usuario."""
    import app.models  # noqa
    from app.core.database import Base
    tarea_table = Base.metadata.tables["tarea"]
    for col_name in ("asignado_a", "asignado_por"):
        col = tarea_table.c[col_name]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "usuario.id" in fk_targets, f"{col_name} must have FK to usuario.id"


def test_comentario_tarea_has_fk_to_tarea():
    """8.1: comentario_tarea.tarea_id has FK to tarea.id."""
    import app.models  # noqa
    from app.core.database import Base
    com_table = Base.metadata.tables["comentario_tarea"]
    tarea_id_col = com_table.c["tarea_id"]
    fk_targets = {fk.target_fullname for fk in tarea_id_col.foreign_keys}
    assert "tarea.id" in fk_targets


def test_audit_action_enum_has_tarea_values():
    """8.1: AuditAction enum has TAREA_ASIGNAR, TAREA_DELEGAR, TAREA_CAMBIAR_ESTADO."""
    from app.models.audit import AuditAction
    assert AuditAction.TAREA_ASIGNAR.value == "TAREA_ASIGNAR"
    assert AuditAction.TAREA_DELEGAR.value == "TAREA_DELEGAR"
    assert AuditAction.TAREA_CAMBIAR_ESTADO.value == "TAREA_CAMBIAR_ESTADO"


def test_tarea_estado_enum_values():
    """8.1: TareaEstado has exactly the D2 values."""
    from app.models.tarea import TareaEstado
    values = {e.value for e in TareaEstado}
    assert values == {"Pendiente", "EnProgreso", "Resuelta", "Cancelada"}


def test_migration_creates_tarea_estado_enum():
    """8.1: migration 014 upgrade SQL creates tarea_estado enum."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.upgrade)
    assert "tarea_estado" in source
    assert "Pendiente" in source
    assert "EnProgreso" in source
    assert "Resuelta" in source
    assert "Cancelada" in source


def test_migration_creates_named_indexes():
    """8.1: migration 014 upgrade SQL has all 5 named indexes (D9)."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.upgrade)
    expected_indexes = [
        "ix_tarea_tenant_asignado_a_estado",
        "ix_tarea_tenant_asignado_por",
        "ix_tarea_tenant_materia_id",
        "ix_tarea_tenant_estado",
        "ix_comentario_tarea_tenant_tarea_id",
    ]
    for idx in expected_indexes:
        assert idx in source, f"Missing index {idx} in migration upgrade"


def test_migration_seeds_tareas_gestionar():
    """8.1: migration 014 upgrade SQL seeds tareas:gestionar permission."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.upgrade)
    assert "tareas:gestionar" in source
    assert "COORDINADOR" in source
    assert "ADMIN" in source


# ---------------------------------------------------------------------------
# 8.2 — downgrade logic
# ---------------------------------------------------------------------------

def test_migration_downgrade_drops_tables():
    """8.2: downgrade drops comentario_tarea and tarea tables."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.downgrade)
    assert "comentario_tarea" in source
    assert "tarea" in source


def test_migration_downgrade_drops_enum():
    """8.2: downgrade drops tarea_estado enum."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.downgrade)
    assert "tarea_estado" in source


def test_migration_downgrade_removes_rbac():
    """8.2: downgrade removes tareas:gestionar from rol_permiso/permiso."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.downgrade)
    assert "tareas:gestionar" in source
    assert "rol_permiso" in source
    assert "permiso" in source


def test_migration_downgrade_documents_audit_limitation():
    """8.2: downgrade documents that audit_action extension is not reversible (Postgres limitation)."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.downgrade)
    # Should have a comment about the Postgres limitation
    assert "Postgres" in source or "postgres" in source.lower()
    assert "NOT reversible" in source or "not reversible" in source.lower() or "limitación" in source.lower()


def test_migration_extends_audit_action():
    """8.1: migration 014 upgrade extends audit_action with TAREA_* values."""
    import inspect
    m = _load_migration_014()
    source = inspect.getsource(m.upgrade)
    assert "TAREA_ASIGNAR" in source
    assert "TAREA_DELEGAR" in source
    assert "TAREA_CAMBIAR_ESTADO" in source
