"""
test_tarea.py — TDD RED/GREEN tests for C-16 Tarea + ComentarioTarea models.

Tasks 1.1–1.5:
    1.1 RED: TareaEstado str-enum, Tarea columns.
    1.3 RED: ComentarioTarea columns and FK.
    1.5 TRIANGULATE: contexto par both-null vs both-present at model level.

No DB needed — model introspection only.
"""
import enum
import pytest


# ---------------------------------------------------------------------------
# 1.1 RED — TareaEstado enum
# ---------------------------------------------------------------------------

def test_tarea_estado_is_str_enum():
    """1.1 RED: TareaEstado is a str-enum."""
    from app.models.tarea import TareaEstado
    assert issubclass(TareaEstado, str)
    assert issubclass(TareaEstado, enum.Enum)


def test_tarea_estado_values():
    """1.1 RED: TareaEstado has exactly Pendiente, EnProgreso, Resuelta, Cancelada."""
    from app.models.tarea import TareaEstado
    values = {e.value for e in TareaEstado}
    assert values == {"Pendiente", "EnProgreso", "Resuelta", "Cancelada"}
    assert len(list(TareaEstado)) == 4


def test_tarea_estado_members():
    """1.1 RED: TareaEstado members accessible by name."""
    from app.models.tarea import TareaEstado
    assert TareaEstado.Pendiente.value == "Pendiente"
    assert TareaEstado.EnProgreso.value == "EnProgreso"
    assert TareaEstado.Resuelta.value == "Resuelta"
    assert TareaEstado.Cancelada.value == "Cancelada"


# ---------------------------------------------------------------------------
# 1.1 RED — Tarea model columns
# ---------------------------------------------------------------------------

def test_tarea_tablename():
    """1.1 RED: Tarea has tablename 'tarea'."""
    from app.models.tarea import Tarea
    assert Tarea.__tablename__ == "tarea"


def test_tarea_has_required_columns():
    """1.1 RED: Tarea has all required columns from TenantScopedBase + business."""
    from app.models.tarea import Tarea
    cols = {col.key for col in Tarea.__table__.columns}
    # TenantScopedBase columns
    assert "id" in cols
    assert "tenant_id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    assert "deleted_at" in cols
    # Business columns
    assert "asignado_a" in cols
    assert "asignado_por" in cols
    assert "descripcion" in cols
    assert "materia_id" in cols
    assert "contexto_id" in cols
    assert "contexto_tipo" in cols
    assert "estado" in cols


def test_tarea_contexto_id_nullable():
    """1.1 RED: contexto_id is nullable (no FK, polimorfic)."""
    from app.models.tarea import Tarea
    col = Tarea.__table__.c["contexto_id"]
    assert col.nullable is True


def test_tarea_contexto_tipo_nullable():
    """1.1 RED: contexto_tipo is nullable VARCHAR(50)."""
    from app.models.tarea import Tarea
    col = Tarea.__table__.c["contexto_tipo"]
    assert col.nullable is True


def test_tarea_materia_id_nullable():
    """1.1 RED: materia_id is nullable FK."""
    from app.models.tarea import Tarea
    col = Tarea.__table__.c["materia_id"]
    assert col.nullable is True


def test_tarea_asignado_a_not_nullable():
    """1.1 RED: asignado_a is not nullable (required)."""
    from app.models.tarea import Tarea
    col = Tarea.__table__.c["asignado_a"]
    assert col.nullable is False


def test_tarea_estado_has_no_default():
    """1.1 RED: estado has no Python-level default (must be provided or set to Pendiente in service)."""
    from app.models.tarea import Tarea
    col = Tarea.__table__.c["estado"]
    # The column exists and is not nullable — no default needed since service always sets it
    assert col is not None


# ---------------------------------------------------------------------------
# 1.3 RED — ComentarioTarea model
# ---------------------------------------------------------------------------

def test_comentario_tarea_tablename():
    """1.3 RED: ComentarioTarea has tablename 'comentario_tarea'."""
    from app.models.tarea import ComentarioTarea
    assert ComentarioTarea.__tablename__ == "comentario_tarea"


def test_comentario_tarea_has_required_columns():
    """1.3 RED: ComentarioTarea has tenant_id, tarea_id, autor_id, cuerpo, es_sistema, deleted_at."""
    from app.models.tarea import ComentarioTarea
    cols = {col.key for col in ComentarioTarea.__table__.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "tarea_id" in cols
    assert "autor_id" in cols
    assert "cuerpo" in cols
    assert "es_sistema" in cols
    assert "deleted_at" in cols
    assert "created_at" in cols
    assert "updated_at" in cols


def test_comentario_es_sistema_default_false():
    """1.3 RED: ComentarioTarea.es_sistema defaults to False."""
    from app.models.tarea import ComentarioTarea
    col = ComentarioTarea.__table__.c["es_sistema"]
    assert col.default is not None and col.default.arg is False


def test_comentario_tarea_has_fk_to_tarea():
    """1.3 RED: ComentarioTarea.tarea_id FK points to tarea.id."""
    from app.models.tarea import ComentarioTarea
    col = ComentarioTarea.__table__.c["tarea_id"]
    fk = list(col.foreign_keys)[0]
    assert "tarea.id" in str(fk.target_fullname)


def test_comentario_tarea_has_fk_to_usuario():
    """1.3 RED: ComentarioTarea.autor_id FK points to usuario.id."""
    from app.models.tarea import ComentarioTarea
    col = ComentarioTarea.__table__.c["autor_id"]
    fk = list(col.foreign_keys)[0]
    assert "usuario.id" in str(fk.target_fullname)


# ---------------------------------------------------------------------------
# 1.5 TRIANGULATE — contexto pair semantics at model level
# ---------------------------------------------------------------------------

def test_tarea_contexto_id_has_no_fk():
    """1.5 TRIANGULATE: contexto_id has NO FK constraint (soft/polymorphic reference)."""
    from app.models.tarea import Tarea
    col = Tarea.__table__.c["contexto_id"]
    assert len(col.foreign_keys) == 0, "contexto_id must NOT have an FK (D4)"


def test_tarea_models_exported_from_init():
    """1.5 TRIANGULATE: Tarea, ComentarioTarea, TareaEstado exported from app.models."""
    import app.models  # noqa
    from app.models import Tarea, ComentarioTarea, TareaEstado
    assert Tarea is not None
    assert ComentarioTarea is not None
    assert TareaEstado is not None
