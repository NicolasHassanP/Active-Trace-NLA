"""
test_evaluacion_schemas.py — TDD tests for C-14 Pydantic schemas.

Task 4.2: extra='forbid' enforcement + ReservaRequest doesn't accept alumno_id.

Sync tests — no DB needed.
"""
import uuid
from datetime import date

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# 4.2: extra='forbid' enforcement
# ---------------------------------------------------------------------------

def test_crear_convocatoria_request_rechaza_campos_extra():
    """4.2 RED: CrearConvocatoriaRequest rejects undeclared fields."""
    from app.schemas.evaluacion import CrearConvocatoriaRequest, TurnoRequest
    from app.models.evaluacion import EvaluacionTipo

    with pytest.raises(ValidationError):
        CrearConvocatoriaRequest(
            materia_id=uuid.uuid4(), cohorte_id=uuid.uuid4(),
            tipo=EvaluacionTipo.Coloquio, instancia="test",
            turnos=[TurnoRequest(fecha=date(2026, 9, 1), cupo_total=5)],
            campo_extra="no permitido",  # type: ignore
        )


def test_reserva_request_no_acepta_alumno_id():
    """4.2 RED: ReservaRequest does not accept alumno_id (identity from JWT only)."""
    from app.schemas.evaluacion import ReservaRequest

    with pytest.raises((ValidationError, TypeError)):
        ReservaRequest(
            turno_id=uuid.uuid4(),
            evaluacion_id=uuid.uuid4(),
            alumno_id=uuid.uuid4(),  # type: ignore — should be rejected
        )


def test_reserva_request_rechaza_campos_extra():
    """4.2 TRIANGULATE: ReservaRequest rejects any undeclared field."""
    from app.schemas.evaluacion import ReservaRequest

    with pytest.raises(ValidationError):
        ReservaRequest(
            turno_id=uuid.uuid4(),
            evaluacion_id=uuid.uuid4(),
            extra_field="forbidden",  # type: ignore
        )


def test_resultado_request_rechaza_campos_extra():
    """4.2: ResultadoRequest rejects undeclared fields."""
    from app.schemas.evaluacion import ResultadoRequest

    with pytest.raises(ValidationError):
        ResultadoRequest(
            evaluacion_id=uuid.uuid4(),
            alumno_id=uuid.uuid4(),
            nota_final="8",
            campo_extra="no",  # type: ignore
        )


def test_turno_request_cupo_positivo():
    """4.2: TurnoRequest requires cupo_total > 0."""
    from app.schemas.evaluacion import TurnoRequest

    with pytest.raises(ValidationError):
        TurnoRequest(fecha=date(2026, 9, 1), cupo_total=0)

    # Valid case
    t = TurnoRequest(fecha=date(2026, 9, 1), cupo_total=1)
    assert t.cupo_total == 1


def test_importar_candidatos_request_rechaza_extra():
    """4.2: ImportarCandidatosRequest rejects undeclared fields."""
    from app.schemas.evaluacion import ImportarCandidatosRequest

    with pytest.raises(ValidationError):
        ImportarCandidatosRequest(
            evaluacion_id=uuid.uuid4(),
            alumno_ids=[uuid.uuid4()],
            extra="not allowed",  # type: ignore
        )
