"""
test_alumno_schemas.py — TDD task 1.2.

RED: schemas rechazan extra fields, validan estado_entrega enum, mapean desde ORM.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.schemas.alumno import (
    CalificacionAlumnoRead,
    ColoquioReservadoRead,
    EstadoAcademicoRead,
    EstadoEntregaAlumno,
    MateriaCursadaRead,
)


# ---------------------------------------------------------------------------
# EstadoEntregaAlumno
# ---------------------------------------------------------------------------

class TestEstadoEntregaAlumno:
    def test_valores_validos(self):
        assert EstadoEntregaAlumno.aprobada == "aprobada"
        assert EstadoEntregaAlumno.con_nota == "con_nota"
        assert EstadoEntregaAlumno.sin_entrega == "sin_entrega"

    def test_str_enum(self):
        assert isinstance(EstadoEntregaAlumno.aprobada, str)


# ---------------------------------------------------------------------------
# CalificacionAlumnoRead
# ---------------------------------------------------------------------------

class TestCalificacionAlumnoRead:
    def test_acepta_payload_valido_aprobada(self):
        obj = CalificacionAlumnoRead(
            actividad="TP1",
            nota_numerica=Decimal("8.5"),
            nota_textual=None,
            aprobado=True,
            estado_entrega=EstadoEntregaAlumno.aprobada,
        )
        assert obj.estado_entrega == EstadoEntregaAlumno.aprobada

    def test_acepta_payload_sin_nota(self):
        obj = CalificacionAlumnoRead(
            actividad="TP2",
            nota_numerica=None,
            nota_textual=None,
            aprobado=False,
            estado_entrega=EstadoEntregaAlumno.sin_entrega,
        )
        assert obj.nota_numerica is None
        assert obj.estado_entrega == EstadoEntregaAlumno.sin_entrega

    def test_rechaza_campo_extra(self):
        with pytest.raises(Exception):
            CalificacionAlumnoRead(
                actividad="TP1",
                aprobado=True,
                estado_entrega="aprobada",
                campo_intruso="hack",
            )

    def test_from_attributes_disponible(self):
        """Verifica que el config tiene from_attributes=True para ORM mapping."""
        assert CalificacionAlumnoRead.model_config.get("from_attributes") is True

    def test_estado_entrega_string_valido(self):
        obj = CalificacionAlumnoRead(
            actividad="TP3",
            aprobado=False,
            estado_entrega="con_nota",
            nota_numerica=Decimal("4.0"),
        )
        assert obj.estado_entrega == EstadoEntregaAlumno.con_nota


# ---------------------------------------------------------------------------
# MateriaCursadaRead
# ---------------------------------------------------------------------------

class TestMateriaCursadaRead:
    def test_acepta_payload_completo(self):
        obj = MateriaCursadaRead(
            materia_id=uuid.uuid4(),
            materia_nombre="Matemáticas",
            avance_pct=75,
            total_actividades=4,
            aprobadas=3,
            calificaciones=[],
        )
        assert obj.avance_pct == 75

    def test_calificaciones_default_vacio(self):
        obj = MateriaCursadaRead(
            materia_id=uuid.uuid4(),
            materia_nombre="Física",
            avance_pct=0,
            total_actividades=0,
            aprobadas=0,
        )
        assert obj.calificaciones == []

    def test_rechaza_campo_extra(self):
        with pytest.raises(Exception):
            MateriaCursadaRead(
                materia_id=uuid.uuid4(),
                materia_nombre="X",
                avance_pct=0,
                total_actividades=0,
                aprobadas=0,
                campo_extra="hack",
            )


# ---------------------------------------------------------------------------
# ColoquioReservadoRead
# ---------------------------------------------------------------------------

class TestColoquioReservadoRead:
    def test_acepta_payload_con_franja(self):
        obj = ColoquioReservadoRead(
            evaluacion_id=uuid.uuid4(),
            materia_nombre="Historia",
            instancia="1",
            tipo="Coloquio",
            fecha=date(2026, 7, 15),
            franja="Mañana",
        )
        assert obj.franja == "Mañana"

    def test_franja_opcional(self):
        obj = ColoquioReservadoRead(
            evaluacion_id=uuid.uuid4(),
            materia_nombre="Historia",
            instancia="1",
            tipo="Coloquio",
            fecha=date(2026, 7, 15),
        )
        assert obj.franja is None

    def test_rechaza_campo_extra(self):
        with pytest.raises(Exception):
            ColoquioReservadoRead(
                evaluacion_id=uuid.uuid4(),
                materia_nombre="X",
                instancia="1",
                tipo="Coloquio",
                fecha=date(2026, 7, 15),
                hack="x",
            )


# ---------------------------------------------------------------------------
# EstadoAcademicoRead
# ---------------------------------------------------------------------------

class TestEstadoAcademicoRead:
    def test_acepta_payload_completo(self):
        obj = EstadoAcademicoRead(
            avance_global_pct=60,
            total_actividades=10,
            aprobadas=6,
            materias=[],
            coloquios_reservados=[],
        )
        assert obj.avance_global_pct == 60

    def test_listas_default_vacias(self):
        obj = EstadoAcademicoRead(
            avance_global_pct=0,
            total_actividades=0,
            aprobadas=0,
        )
        assert obj.materias == []
        assert obj.coloquios_reservados == []

    def test_rechaza_campo_extra(self):
        with pytest.raises(Exception):
            EstadoAcademicoRead(
                avance_global_pct=0,
                total_actividades=0,
                aprobadas=0,
                hack="x",
            )
