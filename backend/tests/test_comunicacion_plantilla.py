"""
TDD tests for comunicacion_plantilla.py — render de plantillas puro (sin DB).

C-12 Design Decisions:
    - OQ-4: render() falla fuerte ante variable sin resolver.
      NO deja el marcador literal, NO sustituye por vacío, NO renderiza parcial.
    - render(plantilla, variables) -> str (sustituye {variable} por valores).

Tasks: 2.1 (RED), 2.3 (TRIANGULATE), 2.4 (REFACTOR verified).
"""
import pytest

from app.services.comunicacion_plantilla import (
    VariablePlantillaFaltanteError,
    render,
)


# ---------------------------------------------------------------------------
# §2.1 — RED: caso básico con una variable
# ---------------------------------------------------------------------------

def test_render_una_variable():
    """'Hola {nombre}' + nombre=Ana → 'Hola Ana'."""
    resultado = render("Hola {nombre}", {"nombre": "Ana"})
    assert resultado == "Hola Ana"


# ---------------------------------------------------------------------------
# §2.3 — TRIANGULATE: múltiples variables
# ---------------------------------------------------------------------------

def test_render_multiples_variables():
    """Reemplaza varias variables en una sola plantilla."""
    resultado = render(
        "Estimado {apellido}, {nombre}: su legajo es {legajo}.",
        {"nombre": "Carlos", "apellido": "García", "legajo": "12345"},
    )
    assert resultado == "Estimado García, Carlos: su legajo es 12345."


def test_render_sin_variables_retorna_texto_intacto():
    """Plantilla sin marcadores: retorna el texto intacto."""
    resultado = render("Texto sin variables.", {})
    assert resultado == "Texto sin variables."


def test_render_variable_repetida():
    """Una variable que aparece más de una vez se reemplaza todas las veces."""
    resultado = render("{nombre} es {nombre}", {"nombre": "Ana"})
    assert resultado == "Ana es Ana"


# ---------------------------------------------------------------------------
# §2.3 — TRIANGULATE: falla fuerte ante variable sin resolver (OQ-4)
# ---------------------------------------------------------------------------

def test_render_variable_faltante_lanza_error():
    """render('Hola {nombre}', {}) lanza VariablePlantillaFaltanteError (OQ-4)."""
    with pytest.raises(VariablePlantillaFaltanteError):
        render("Hola {nombre}", {})


def test_render_variable_faltante_no_deja_marcador():
    """La excepción se lanza antes de retornar — no hay resultado parcial."""
    raised = False
    try:
        render("Hola {nombre} y {apellido}", {"nombre": "Ana"})
    except VariablePlantillaFaltanteError as exc:
        raised = True
        # La excepción menciona la variable faltante
        assert "apellido" in str(exc)
    assert raised, "Debería haber lanzado VariablePlantillaFaltanteError"


def test_render_variable_extra_no_lanza_error():
    """Variables adicionales en el dict que no están en la plantilla son ignoradas."""
    resultado = render("Hola {nombre}", {"nombre": "Ana", "extra": "ignorado"})
    assert resultado == "Hola Ana"


def test_render_variable_faltante_con_multiples_vars():
    """Si una de varias variables falta, lanza el error (no renderiza parcial)."""
    with pytest.raises(VariablePlantillaFaltanteError):
        render(
            "{saludo} {nombre}, su materia es {materia}.",
            {"saludo": "Estimado", "nombre": "Pedro"},  # falta materia
        )
