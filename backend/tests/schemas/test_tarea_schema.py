"""
test_tarea_schema.py — TDD RED/GREEN tests for C-16 Tarea schemas.

Tasks 2.1–2.5:
    2.1 RED: create schema rejects unknown fields / identity fields.
    2.3 RED: contexto coherence — only-one rejects, both-null and both-present accept.
    2.5 TRIANGULATE: edge cases — empty descripcion, invalid estado value.

No DB needed — pure Pydantic validation.
"""
import uuid

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# 2.1 RED — TareaCreate rejects unknown and identity fields
# ---------------------------------------------------------------------------

def test_tarea_create_rejects_unknown_fields():
    """2.1 RED: TareaCreate rejects unknown fields (extra='forbid')."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError):
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="Test",
            campo_extra="invalido",
        )


def test_tarea_create_rejects_tenant_id():
    """2.1 RED: TareaCreate rejects tenant_id (identity field from JWT only)."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError):
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="Test",
            tenant_id=uuid.uuid4(),
        )


def test_tarea_create_rejects_asignado_por():
    """2.1 RED: TareaCreate rejects asignado_por (identity field from JWT only)."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError):
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="Test",
            asignado_por=uuid.uuid4(),
        )


def test_tarea_create_rejects_autor_id():
    """2.1 RED: TareaCreate rejects autor_id (identity field)."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError):
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="Test",
            autor_id=uuid.uuid4(),
        )


def test_tarea_create_accepts_asignado_a():
    """2.1 RED: TareaCreate ACCEPTS asignado_a (target of assignment, not identity)."""
    from app.schemas.tarea import TareaCreate
    uid = uuid.uuid4()
    schema = TareaCreate(asignado_a=uid, descripcion="Tarea válida")
    assert schema.asignado_a == uid
    assert schema.descripcion == "Tarea válida"


def test_tarea_create_minimal_valid():
    """2.2 GREEN: TareaCreate with only required fields is valid."""
    from app.schemas.tarea import TareaCreate
    schema = TareaCreate(
        asignado_a=uuid.uuid4(),
        descripcion="Descripción válida",
    )
    assert schema.contexto_id is None
    assert schema.contexto_tipo is None
    assert schema.materia_id is None


# ---------------------------------------------------------------------------
# 2.3 RED — Contexto coherence
# ---------------------------------------------------------------------------

def test_tarea_create_rejects_contexto_id_without_tipo():
    """2.3 RED: contexto_id present but contexto_tipo absent → ValidationError."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError) as exc_info:
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="Test",
            contexto_id=uuid.uuid4(),
            contexto_tipo=None,
        )
    assert "contexto" in str(exc_info.value).lower()


def test_tarea_create_rejects_contexto_tipo_without_id():
    """2.3 RED: contexto_tipo present but contexto_id absent → ValidationError."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError) as exc_info:
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="Test",
            contexto_id=None,
            contexto_tipo="Encuentro",
        )
    assert "contexto" in str(exc_info.value).lower()


def test_tarea_create_accepts_both_contexto_present():
    """2.4 GREEN: both contexto_id and contexto_tipo present → valid."""
    from app.schemas.tarea import TareaCreate
    cid = uuid.uuid4()
    schema = TareaCreate(
        asignado_a=uuid.uuid4(),
        descripcion="Test",
        contexto_id=cid,
        contexto_tipo="Encuentro",
    )
    assert schema.contexto_id == cid
    assert schema.contexto_tipo == "Encuentro"


def test_tarea_create_accepts_both_contexto_null():
    """2.4 GREEN: both contexto_id and contexto_tipo null → valid."""
    from app.schemas.tarea import TareaCreate
    schema = TareaCreate(
        asignado_a=uuid.uuid4(),
        descripcion="Test",
        contexto_id=None,
        contexto_tipo=None,
    )
    assert schema.contexto_id is None
    assert schema.contexto_tipo is None


# ---------------------------------------------------------------------------
# 2.5 TRIANGULATE — edge cases
# ---------------------------------------------------------------------------

def test_tarea_create_rejects_empty_descripcion():
    """2.5 TRIANGULATE: empty descripcion → ValidationError."""
    from app.schemas.tarea import TareaCreate
    with pytest.raises(ValidationError):
        TareaCreate(
            asignado_a=uuid.uuid4(),
            descripcion="",
        )


def test_tarea_update_estado_rejects_invalid_value():
    """2.5 TRIANGULATE: TareaUpdateEstado with invalid estado → ValidationError."""
    from app.schemas.tarea import TareaUpdateEstado
    with pytest.raises(ValidationError):
        TareaUpdateEstado(estado="Invalido")


def test_tarea_update_estado_valid_values():
    """2.5 TRIANGULATE: TareaUpdateEstado accepts valid TareaEstado values."""
    from app.schemas.tarea import TareaUpdateEstado
    from app.models.tarea import TareaEstado
    for estado in TareaEstado:
        schema = TareaUpdateEstado(estado=estado.value)
        assert schema.estado == estado


def test_tarea_delegar_rejects_identity_fields():
    """2.5 TRIANGULATE: TareaDelegar rejects identity fields."""
    from app.schemas.tarea import TareaDelegar
    with pytest.raises(ValidationError):
        TareaDelegar(asignado_a=uuid.uuid4(), tenant_id=uuid.uuid4())


def test_tarea_delegar_accepts_asignado_a():
    """2.5 TRIANGULATE: TareaDelegar accepts asignado_a."""
    from app.schemas.tarea import TareaDelegar
    uid = uuid.uuid4()
    schema = TareaDelegar(asignado_a=uid)
    assert schema.asignado_a == uid


def test_comentario_tarea_create_rejects_autor_id():
    """2.5 TRIANGULATE: ComentarioTareaCreate rejects autor_id (from JWT only)."""
    from app.schemas.tarea import ComentarioTareaCreate
    with pytest.raises(ValidationError):
        ComentarioTareaCreate(cuerpo="Texto", autor_id=uuid.uuid4())


def test_comentario_tarea_create_valid():
    """2.5 TRIANGULATE: ComentarioTareaCreate with only cuerpo is valid."""
    from app.schemas.tarea import ComentarioTareaCreate
    schema = ComentarioTareaCreate(cuerpo="Un comentario")
    assert schema.cuerpo == "Un comentario"


def test_comentario_tarea_create_rejects_empty_cuerpo():
    """2.5 TRIANGULATE: ComentarioTareaCreate rejects empty cuerpo."""
    from app.schemas.tarea import ComentarioTareaCreate
    with pytest.raises(ValidationError):
        ComentarioTareaCreate(cuerpo="")


def test_tarea_read_has_required_fields():
    """2.5 TRIANGULATE: TareaRead has all expected response fields."""
    from app.schemas.tarea import TareaRead
    import inspect
    fields = TareaRead.model_fields.keys()
    assert "id" in fields
    assert "tenant_id" in fields
    assert "asignado_a" in fields
    assert "asignado_por" in fields
    assert "descripcion" in fields
    assert "estado" in fields


def test_comentario_tarea_read_has_required_fields():
    """2.5 TRIANGULATE: ComentarioTareaRead has all expected response fields."""
    from app.schemas.tarea import ComentarioTareaRead
    fields = ComentarioTareaRead.model_fields.keys()
    assert "id" in fields
    assert "tarea_id" in fields
    assert "autor_id" in fields
    assert "cuerpo" in fields
    assert "es_sistema" in fields
