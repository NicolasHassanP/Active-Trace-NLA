"""
test_evaluacion_models.py — TDD RED tests for C-14 evaluaciones/coloquios models.

RED phase: these tests reference production code that does NOT yet exist.
They verify:
    - Enums EvaluacionTipo and ReservaEstado exist and have correct values.
    - Evaluacion model has expected fields.
    - TurnoEvaluacion, CandidatoEvaluacion, ReservaEvaluacion, ResultadoEvaluacion models exist.
    - All models are exported from app.models.

DB real: activia_trace_test. Sin mocks.
"""
import pytest


def test_evaluacion_tipo_enum_values():
    """RED 1.1: EvaluacionTipo has Parcial, TP, Coloquio, Recuperatorio."""
    from app.models.evaluacion import EvaluacionTipo
    assert EvaluacionTipo.Parcial.value == "Parcial"
    assert EvaluacionTipo.TP.value == "TP"
    assert EvaluacionTipo.Coloquio.value == "Coloquio"
    assert EvaluacionTipo.Recuperatorio.value == "Recuperatorio"


def test_reserva_estado_enum_values():
    """RED 1.1: ReservaEstado has Activa and Cancelada."""
    from app.models.evaluacion import ReservaEstado
    assert ReservaEstado.Activa.value == "Activa"
    assert ReservaEstado.Cancelada.value == "Cancelada"


def test_evaluacion_model_tablename():
    """RED 1.2: Evaluacion model has tablename 'evaluacion'."""
    from app.models.evaluacion import Evaluacion
    assert Evaluacion.__tablename__ == "evaluacion"


def test_evaluacion_model_has_required_columns():
    """RED 1.2: Evaluacion model has materia_id, cohorte_id, tipo, instancia, dias_disponibles, cerrada."""
    from app.models.evaluacion import Evaluacion
    cols = {col.key for col in Evaluacion.__table__.columns}
    assert "materia_id" in cols
    assert "cohorte_id" in cols
    assert "tipo" in cols
    assert "instancia" in cols
    assert "dias_disponibles" in cols
    assert "cerrada" in cols
    # TenantScopedBase provides:
    assert "id" in cols
    assert "tenant_id" in cols
    assert "deleted_at" in cols


def test_evaluacion_cerrada_default_false():
    """RED 1.2: Evaluacion.cerrada column has a default of False."""
    from app.models.evaluacion import Evaluacion
    col = Evaluacion.__table__.c["cerrada"]
    # The column should have a Python-side default of False
    assert col.default is not None and col.default.arg is False


def test_turno_evaluacion_tablename():
    """RED 1.3: TurnoEvaluacion model has tablename 'turno_evaluacion'."""
    from app.models.evaluacion import TurnoEvaluacion
    assert TurnoEvaluacion.__tablename__ == "turno_evaluacion"


def test_turno_evaluacion_has_required_columns():
    """RED 1.3: TurnoEvaluacion has evaluacion_id, fecha, cupo_total, franja."""
    from app.models.evaluacion import TurnoEvaluacion
    cols = {col.key for col in TurnoEvaluacion.__table__.columns}
    assert "evaluacion_id" in cols
    assert "fecha" in cols
    assert "cupo_total" in cols
    assert "franja" in cols


def test_candidato_evaluacion_tablename():
    """RED 1.4: CandidatoEvaluacion has tablename 'candidato_evaluacion'."""
    from app.models.evaluacion import CandidatoEvaluacion
    assert CandidatoEvaluacion.__tablename__ == "candidato_evaluacion"


def test_candidato_evaluacion_has_required_columns():
    """RED 1.4: CandidatoEvaluacion has evaluacion_id and alumno_id."""
    from app.models.evaluacion import CandidatoEvaluacion
    cols = {col.key for col in CandidatoEvaluacion.__table__.columns}
    assert "evaluacion_id" in cols
    assert "alumno_id" in cols


def test_reserva_evaluacion_tablename():
    """RED 1.5: ReservaEvaluacion has tablename 'reserva_evaluacion'."""
    from app.models.evaluacion import ReservaEvaluacion
    assert ReservaEvaluacion.__tablename__ == "reserva_evaluacion"


def test_reserva_evaluacion_has_required_columns():
    """RED 1.5: ReservaEvaluacion has turno_id, evaluacion_id, alumno_id, estado."""
    from app.models.evaluacion import ReservaEvaluacion
    cols = {col.key for col in ReservaEvaluacion.__table__.columns}
    assert "turno_id" in cols
    assert "evaluacion_id" in cols
    assert "alumno_id" in cols
    assert "estado" in cols


def test_reserva_evaluacion_estado_default_activa():
    """RED 1.5: ReservaEvaluacion.estado column has default Activa."""
    from app.models.evaluacion import ReservaEvaluacion, ReservaEstado
    col = ReservaEvaluacion.__table__.c["estado"]
    assert col.default is not None and col.default.arg == ReservaEstado.Activa


def test_resultado_evaluacion_tablename():
    """RED 1.6: ResultadoEvaluacion has tablename 'resultado_evaluacion'."""
    from app.models.evaluacion import ResultadoEvaluacion
    assert ResultadoEvaluacion.__tablename__ == "resultado_evaluacion"


def test_resultado_evaluacion_has_required_columns():
    """RED 1.6: ResultadoEvaluacion has evaluacion_id, alumno_id, nota_final."""
    from app.models.evaluacion import ResultadoEvaluacion
    cols = {col.key for col in ResultadoEvaluacion.__table__.columns}
    assert "evaluacion_id" in cols
    assert "alumno_id" in cols
    assert "nota_final" in cols


def test_models_exported_from_init():
    """RED 1.7: All evaluacion models are exported from app.models."""
    import app.models  # noqa
    from app.models import (
        EvaluacionTipo,
        ReservaEstado,
        Evaluacion,
        TurnoEvaluacion,
        CandidatoEvaluacion,
        ReservaEvaluacion,
        ResultadoEvaluacion,
    )
    assert EvaluacionTipo is not None
    assert ReservaEstado is not None
    assert Evaluacion is not None
    assert TurnoEvaluacion is not None
    assert CandidatoEvaluacion is not None
    assert ReservaEvaluacion is not None
    assert ResultadoEvaluacion is not None
