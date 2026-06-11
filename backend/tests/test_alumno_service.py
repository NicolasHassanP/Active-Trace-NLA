"""
test_alumno_service.py — TDD task 3.5.

Tests unitarios de las funciones puras de AlumnoService:
    clasificar_estado_entrega — 3 escenarios (aprobada, con_nota, sin_entrega)
    calcular_avance — edge cases (0 total, parcial, completo)

La identidad del alumno SIEMPRE viene de CurrentUser; validado con test de integración
del router (test_alumno_router.py). Aquí solo se testean las funciones puras.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.calificacion import Calificacion
from app.schemas.alumno import EstadoEntregaAlumno
from app.services.alumno_service import calcular_avance, clasificar_estado_entrega


# ---------------------------------------------------------------------------
# Helper — construye un mock de Calificacion con los campos relevantes
# ---------------------------------------------------------------------------

def _make_cal(aprobado: bool, nota_numerica=None, nota_textual=None) -> Calificacion:
    mock = MagicMock(spec=Calificacion)
    mock.aprobado = aprobado
    mock.nota_numerica = nota_numerica
    mock.nota_textual = nota_textual
    return mock


# ---------------------------------------------------------------------------
# clasificar_estado_entrega
# ---------------------------------------------------------------------------

class TestClasificarEstadoEntrega:
    def test_aprobado_true_retorna_aprobada(self):
        cal = _make_cal(aprobado=True, nota_numerica=Decimal("8"))
        assert clasificar_estado_entrega(cal) == EstadoEntregaAlumno.aprobada

    def test_con_nota_numerica_y_no_aprobado_retorna_con_nota(self):
        cal = _make_cal(aprobado=False, nota_numerica=Decimal("4.0"))
        assert clasificar_estado_entrega(cal) == EstadoEntregaAlumno.con_nota

    def test_con_nota_textual_y_no_aprobado_retorna_con_nota(self):
        cal = _make_cal(aprobado=False, nota_textual="Ausente")
        assert clasificar_estado_entrega(cal) == EstadoEntregaAlumno.con_nota

    def test_sin_nota_retorna_sin_entrega(self):
        cal = _make_cal(aprobado=False)
        assert clasificar_estado_entrega(cal) == EstadoEntregaAlumno.sin_entrega

    def test_aprobado_true_prioriza_sobre_nota(self):
        """aprobado=True siempre retorna aprobada, incluso con nota."""
        cal = _make_cal(aprobado=True, nota_numerica=Decimal("7"))
        assert clasificar_estado_entrega(cal) == EstadoEntregaAlumno.aprobada


# ---------------------------------------------------------------------------
# calcular_avance
# ---------------------------------------------------------------------------

class TestCalcularAvance:
    def test_total_cero_retorna_cero(self):
        assert calcular_avance(0, 0) == 0

    def test_ninguna_aprobada(self):
        assert calcular_avance(0, 5) == 0

    def test_todas_aprobadas(self):
        assert calcular_avance(5, 5) == 100

    def test_parcial_redondea_correctamente(self):
        assert calcular_avance(1, 3) == 33

    def test_parcial_redondea_hacia_arriba(self):
        assert calcular_avance(2, 3) == 67

    def test_decimales_redondeados(self):
        assert calcular_avance(1, 4) == 25
