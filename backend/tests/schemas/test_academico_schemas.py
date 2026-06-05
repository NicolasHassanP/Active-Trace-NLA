"""
test_academico_schemas.py — TDD RED/GREEN tests for C-17 academico schemas.

Tasks 4.1–4.3:
    4.1 RED: schema de programa rechaza campos extra, exige referencia_archivo no vacía.
    4.2 GREEN: schemas implementados con extra='forbid'.
    4.3 TRIANGULATE: tipo enum válido, numero ≥ 1, periodo patrón "AAAA-N", título no vacío.

No DB needed — pure Pydantic validation.
"""
import uuid
from datetime import date

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# 4.1 RED — ProgramaCreate rejects unknown fields
# ---------------------------------------------------------------------------

def test_programa_create_rejects_unknown_fields():
    """4.1 RED: ProgramaCreate rejects unknown fields (extra='forbid')."""
    from app.schemas.academico import ProgramaCreate
    with pytest.raises(ValidationError):
        ProgramaCreate(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            titulo="Programa Test",
            referencia_archivo="blob://test",
            campo_extra="invalido",
        )


def test_programa_create_rejects_empty_referencia_archivo():
    """4.1 RED: ProgramaCreate rejects empty referencia_archivo."""
    from app.schemas.academico import ProgramaCreate
    with pytest.raises(ValidationError):
        ProgramaCreate(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            titulo="Programa Test",
            referencia_archivo="",
        )


def test_programa_create_rejects_tenant_id():
    """4.1 RED: ProgramaCreate rejects tenant_id (identity from JWT)."""
    from app.schemas.academico import ProgramaCreate
    with pytest.raises(ValidationError):
        ProgramaCreate(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            titulo="Prog",
            referencia_archivo="blob://1",
            tenant_id=uuid.uuid4(),
        )


def test_programa_create_valid_minimal():
    """4.1 RED: ProgramaCreate accepts all required fields."""
    from app.schemas.academico import ProgramaCreate
    schema = ProgramaCreate(
        materia_id=uuid.uuid4(),
        carrera_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        titulo="Programa de Matemáticas",
        referencia_archivo="blob://store/prog-mat-001",
    )
    assert schema.referencia_archivo == "blob://store/prog-mat-001"
    assert schema.titulo == "Programa de Matemáticas"


# ---------------------------------------------------------------------------
# 4.2 GREEN — schemas exist and have from_attributes
# ---------------------------------------------------------------------------

def test_programa_read_has_required_fields():
    """4.2 GREEN: ProgramaRead has all expected response fields."""
    from app.schemas.academico import ProgramaRead
    fields = ProgramaRead.model_fields.keys()
    assert "id" in fields
    assert "tenant_id" in fields
    assert "materia_id" in fields
    assert "carrera_id" in fields
    assert "cohorte_id" in fields
    assert "titulo" in fields
    assert "referencia_archivo" in fields


def test_fecha_academica_create_rejects_unknown_fields():
    """4.2 GREEN: FechaAcademicaCreate rejects unknown fields."""
    from app.schemas.academico import FechaAcademicaCreate
    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Parcial",
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 5, 10),
            titulo="Primer Parcial",
            campo_extra="invalido",
        )


def test_fecha_academica_create_valid():
    """4.2 GREEN: FechaAcademicaCreate accepts valid data."""
    from app.schemas.academico import FechaAcademicaCreate
    schema = FechaAcademicaCreate(
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        tipo="Parcial",
        numero=1,
        periodo="2026-1",
        fecha=date(2026, 5, 10),
        titulo="Primer Parcial",
    )
    assert schema.tipo.value == "Parcial"
    assert schema.numero == 1
    assert schema.periodo == "2026-1"


def test_fecha_academica_update_rejects_unknown_fields():
    """4.2 GREEN: FechaAcademicaUpdate rejects unknown fields."""
    from app.schemas.academico import FechaAcademicaUpdate
    with pytest.raises(ValidationError):
        FechaAcademicaUpdate(titulo="New", campo_extra="bad")


def test_fecha_academica_update_accepts_partial_fields():
    """4.2 GREEN: FechaAcademicaUpdate accepts partial updates."""
    from app.schemas.academico import FechaAcademicaUpdate
    schema = FechaAcademicaUpdate(titulo="Fecha Actualizada")
    assert schema.titulo == "Fecha Actualizada"
    assert schema.fecha is None


def test_fecha_academica_read_has_required_fields():
    """4.2 GREEN: FechaAcademicaRead has all expected fields."""
    from app.schemas.academico import FechaAcademicaRead
    fields = FechaAcademicaRead.model_fields.keys()
    assert "id" in fields
    assert "tenant_id" in fields
    assert "materia_id" in fields
    assert "cohorte_id" in fields
    assert "tipo" in fields
    assert "numero" in fields
    assert "periodo" in fields
    assert "fecha" in fields
    assert "titulo" in fields


# ---------------------------------------------------------------------------
# 4.3 TRIANGULATE — validations
# ---------------------------------------------------------------------------

def test_fecha_academica_create_rejects_invalid_tipo():
    """4.3 TRIANGULATE: FechaAcademicaCreate rejects tipo not in enum."""
    from app.schemas.academico import FechaAcademicaCreate
    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Examen",  # Invalid
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 5, 10),
            titulo="Test",
        )


def test_fecha_academica_create_rejects_numero_zero():
    """4.3 TRIANGULATE: numero must be ≥ 1."""
    from app.schemas.academico import FechaAcademicaCreate
    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Parcial",
            numero=0,  # Invalid: must be >= 1
            periodo="2026-1",
            fecha=date(2026, 5, 10),
            titulo="Test",
        )


def test_fecha_academica_create_rejects_invalid_periodo():
    """4.3 TRIANGULATE: periodo must match pattern AAAA-N."""
    from app.schemas.academico import FechaAcademicaCreate
    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Parcial",
            numero=1,
            periodo="primer semestre",  # Invalid pattern
            fecha=date(2026, 5, 10),
            titulo="Test",
        )


def test_fecha_academica_create_valid_periodo_formats():
    """4.3 TRIANGULATE: valid periodo patterns accepted."""
    from app.schemas.academico import FechaAcademicaCreate
    for periodo in ["2026-1", "2026-2", "2025-1"]:
        schema = FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="TP",
            numero=1,
            periodo=periodo,
            fecha=date(2026, 5, 10),
            titulo="TP Test",
        )
        assert schema.periodo == periodo


def test_fecha_academica_create_rejects_empty_titulo():
    """4.3 TRIANGULATE: empty titulo raises ValidationError."""
    from app.schemas.academico import FechaAcademicaCreate
    with pytest.raises(ValidationError):
        FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo="Parcial",
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 5, 10),
            titulo="",
        )


def test_programa_create_rejects_empty_titulo():
    """4.3 TRIANGULATE: ProgramaCreate rejects empty titulo."""
    from app.schemas.academico import ProgramaCreate
    with pytest.raises(ValidationError):
        ProgramaCreate(
            materia_id=uuid.uuid4(),
            carrera_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            titulo="",
            referencia_archivo="blob://test",
        )


def test_fecha_academica_update_rejects_empty_titulo():
    """4.3 TRIANGULATE: FechaAcademicaUpdate rejects empty titulo."""
    from app.schemas.academico import FechaAcademicaUpdate
    with pytest.raises(ValidationError):
        FechaAcademicaUpdate(titulo="")


def test_periodo_trimmed_on_validation():
    """4.3 TRIANGULATE: periodo is stripped of surrounding whitespace."""
    from app.schemas.academico import FechaAcademicaCreate
    schema = FechaAcademicaCreate(
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        tipo="Coloquio",
        numero=1,
        periodo="  2026-1  ",  # whitespace around it
        fecha=date(2026, 5, 10),
        titulo="Coloquio Test",
    )
    assert schema.periodo == "2026-1"


def test_fecha_academica_create_accepts_all_tipos():
    """4.3 TRIANGULATE: all 4 tipos are accepted."""
    from app.schemas.academico import FechaAcademicaCreate
    from app.models.academico import FechaAcademicaTipo
    for tipo in FechaAcademicaTipo:
        schema = FechaAcademicaCreate(
            materia_id=uuid.uuid4(),
            cohorte_id=uuid.uuid4(),
            tipo=tipo.value,
            numero=1,
            periodo="2026-1",
            fecha=date(2026, 5, 10),
            titulo=f"Test {tipo.value}",
        )
        assert schema.tipo == tipo
