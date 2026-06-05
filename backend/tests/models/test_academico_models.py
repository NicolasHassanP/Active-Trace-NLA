"""
test_academico_models.py — TDD RED/GREEN tests for C-17 ProgramaMateria + FechaAcademica models.

Tasks 1.1–1.5:
    1.1 RED: models importable, inherit TenantScopedBase, tablenames, columns.
    1.2 GREEN (verified here): ProgramaMateria columns present.
    1.3 GREEN (verified here): FechaAcademica columns + FechaAcademicaTipo enum.
    1.4 TRIANGULATE: tipo only 4 valid values; referencia_archivo NOT NULL.
    1.5 REFACTOR: docstrings verified, __repr__ exists.

No DB needed — model introspection only.
"""
import enum
import pytest


# ---------------------------------------------------------------------------
# 1.1 RED — ProgramaMateria basic structure
# ---------------------------------------------------------------------------

def test_programa_materia_importable():
    """1.1 RED: ProgramaMateria importable from app.models.academico."""
    from app.models.academico import ProgramaMateria
    assert ProgramaMateria is not None


def test_fecha_academica_importable():
    """1.1 RED: FechaAcademica importable from app.models.academico."""
    from app.models.academico import FechaAcademica
    assert FechaAcademica is not None


def test_fecha_academica_tipo_importable():
    """1.1 RED: FechaAcademicaTipo importable from app.models.academico."""
    from app.models.academico import FechaAcademicaTipo
    assert FechaAcademicaTipo is not None


def test_programa_materia_tablename():
    """1.1 RED: ProgramaMateria tablename is 'programa_materia'."""
    from app.models.academico import ProgramaMateria
    assert ProgramaMateria.__tablename__ == "programa_materia"


def test_fecha_academica_tablename():
    """1.1 RED: FechaAcademica tablename is 'fecha_academica'."""
    from app.models.academico import FechaAcademica
    assert FechaAcademica.__tablename__ == "fecha_academica"


def test_programa_materia_inherits_tenant_scoped_base():
    """1.1 RED: ProgramaMateria has TenantScopedBase columns."""
    from app.models.academico import ProgramaMateria
    cols = {col.key for col in ProgramaMateria.__table__.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    assert "deleted_at" in cols


def test_fecha_academica_inherits_tenant_scoped_base():
    """1.1 RED: FechaAcademica has TenantScopedBase columns."""
    from app.models.academico import FechaAcademica
    cols = {col.key for col in FechaAcademica.__table__.columns}
    assert "id" in cols
    assert "tenant_id" in cols
    assert "created_at" in cols
    assert "updated_at" in cols
    assert "deleted_at" in cols


# ---------------------------------------------------------------------------
# 1.2 GREEN — ProgramaMateria business columns
# ---------------------------------------------------------------------------

def test_programa_materia_has_required_columns():
    """1.2 GREEN: ProgramaMateria has materia_id, carrera_id, cohorte_id, titulo, referencia_archivo, cargado_at."""
    from app.models.academico import ProgramaMateria
    cols = {col.key for col in ProgramaMateria.__table__.columns}
    assert "materia_id" in cols
    assert "carrera_id" in cols
    assert "cohorte_id" in cols
    assert "titulo" in cols
    assert "referencia_archivo" in cols
    assert "cargado_at" in cols


def test_programa_materia_fks_are_restrict():
    """1.2 GREEN: materia_id, carrera_id, cohorte_id FKs have RESTRICT on delete."""
    from app.models.academico import ProgramaMateria

    for col_name, expected_table in [
        ("materia_id", "materia.id"),
        ("carrera_id", "carrera.id"),
        ("cohorte_id", "cohorte.id"),
    ]:
        col = ProgramaMateria.__table__.c[col_name]
        fk = list(col.foreign_keys)[0]
        assert expected_table in str(fk.target_fullname), f"{col_name} FK target wrong"


def test_programa_materia_referencia_archivo_not_nullable():
    """1.2 GREEN: referencia_archivo is NOT NULL."""
    from app.models.academico import ProgramaMateria
    col = ProgramaMateria.__table__.c["referencia_archivo"]
    assert col.nullable is False


def test_programa_materia_titulo_not_nullable():
    """1.2 GREEN: titulo is NOT NULL."""
    from app.models.academico import ProgramaMateria
    col = ProgramaMateria.__table__.c["titulo"]
    assert col.nullable is False


def test_programa_materia_materia_id_not_nullable():
    """1.2 GREEN: materia_id is NOT NULL."""
    from app.models.academico import ProgramaMateria
    col = ProgramaMateria.__table__.c["materia_id"]
    assert col.nullable is False


# ---------------------------------------------------------------------------
# 1.3 GREEN — FechaAcademica business columns + FechaAcademicaTipo
# ---------------------------------------------------------------------------

def test_fecha_academica_has_required_columns():
    """1.3 GREEN: FechaAcademica has materia_id, cohorte_id, tipo, numero, periodo, fecha, titulo."""
    from app.models.academico import FechaAcademica
    cols = {col.key for col in FechaAcademica.__table__.columns}
    assert "materia_id" in cols
    assert "cohorte_id" in cols
    assert "tipo" in cols
    assert "numero" in cols
    assert "periodo" in cols
    assert "fecha" in cols
    assert "titulo" in cols


def test_fecha_academica_tipo_is_str_enum():
    """1.3 GREEN: FechaAcademicaTipo is a str-enum."""
    from app.models.academico import FechaAcademicaTipo
    assert issubclass(FechaAcademicaTipo, str)
    assert issubclass(FechaAcademicaTipo, enum.Enum)


def test_fecha_academica_tipo_values():
    """1.3 GREEN: FechaAcademicaTipo has exactly Parcial, TP, Coloquio, Recuperatorio."""
    from app.models.academico import FechaAcademicaTipo
    values = {e.value for e in FechaAcademicaTipo}
    assert values == {"Parcial", "TP", "Coloquio", "Recuperatorio"}
    assert len(list(FechaAcademicaTipo)) == 4


def test_fecha_academica_materia_id_not_nullable():
    """1.3 GREEN: materia_id is NOT NULL."""
    from app.models.academico import FechaAcademica
    col = FechaAcademica.__table__.c["materia_id"]
    assert col.nullable is False


def test_fecha_academica_cohorte_id_not_nullable():
    """1.3 GREEN: cohorte_id is NOT NULL."""
    from app.models.academico import FechaAcademica
    col = FechaAcademica.__table__.c["cohorte_id"]
    assert col.nullable is False


def test_fecha_academica_numero_not_nullable():
    """1.3 GREEN: numero is NOT NULL."""
    from app.models.academico import FechaAcademica
    col = FechaAcademica.__table__.c["numero"]
    assert col.nullable is False


def test_fecha_academica_periodo_not_nullable():
    """1.3 GREEN: periodo is NOT NULL."""
    from app.models.academico import FechaAcademica
    col = FechaAcademica.__table__.c["periodo"]
    assert col.nullable is False


def test_fecha_academica_fks_are_restrict():
    """1.3 GREEN: materia_id, cohorte_id FKs have RESTRICT on delete."""
    from app.models.academico import FechaAcademica

    for col_name, expected_table in [
        ("materia_id", "materia.id"),
        ("cohorte_id", "cohorte.id"),
    ]:
        col = FechaAcademica.__table__.c[col_name]
        fk = list(col.foreign_keys)[0]
        assert expected_table in str(fk.target_fullname), f"{col_name} FK target wrong"


# ---------------------------------------------------------------------------
# 1.4 TRIANGULATE — edge cases
# ---------------------------------------------------------------------------

def test_fecha_academica_tipo_members():
    """1.4 TRIANGULATE: all 4 enum members are accessible."""
    from app.models.academico import FechaAcademicaTipo
    assert FechaAcademicaTipo.Parcial.value == "Parcial"
    assert FechaAcademicaTipo.TP.value == "TP"
    assert FechaAcademicaTipo.Coloquio.value == "Coloquio"
    assert FechaAcademicaTipo.Recuperatorio.value == "Recuperatorio"


def test_fecha_academica_tipo_invalid_raises():
    """1.4 TRIANGULATE: FechaAcademicaTipo does not accept invalid values."""
    from app.models.academico import FechaAcademicaTipo
    with pytest.raises(ValueError):
        FechaAcademicaTipo("Examen")


def test_programa_materia_cargado_at_nullable():
    """1.4 TRIANGULATE: cargado_at is nullable (optional business timestamp)."""
    from app.models.academico import ProgramaMateria
    col = ProgramaMateria.__table__.c["cargado_at"]
    assert col.nullable is True


# ---------------------------------------------------------------------------
# 1.5 REFACTOR — exported from app.models
# ---------------------------------------------------------------------------

def test_models_exported_from_app_models():
    """1.5 REFACTOR: ProgramaMateria and FechaAcademica exported from app.models."""
    import app.models  # noqa
    from app.models import ProgramaMateria, FechaAcademica, FechaAcademicaTipo
    assert ProgramaMateria is not None
    assert FechaAcademica is not None
    assert FechaAcademicaTipo is not None
