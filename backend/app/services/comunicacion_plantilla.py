"""
comunicacion_plantilla.py — Render de plantillas puro (sin DB).

C-12 Design Decisions:
    - OQ-4: falla fuerte ante variable sin resolver.
      No deja el marcador literal, no sustituye por vacío, no renderiza parcial.
    - Formato de marcadores: {nombre_variable} (estilo str.format_map).

snake_case; ≤500 LOC. Sin efectos secundarios.
"""
import re
import string
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Excepción de variable faltante (OQ-4)
# ---------------------------------------------------------------------------

class VariablePlantillaFaltanteError(Exception):
    """
    Se lanza cuando render() encuentra un marcador sin valor en el dict de variables.

    Attributes:
        variable: nombre de la variable faltante.
        plantilla: la plantilla original (para contexto de diagnóstico).
    """

    def __init__(self, variable: str, plantilla: str) -> None:
        self.variable = variable
        self.plantilla = plantilla
        super().__init__(
            f"Variable de plantilla sin resolver: '{variable}'. "
            f"Verifique que todas las variables estén provistas."
        )


# ---------------------------------------------------------------------------
# Regex para detectar marcadores {nombre_variable}
# ---------------------------------------------------------------------------

# Detecta {variable} donde variable es alfanumérico/underscore
_MARCADOR_RE = re.compile(r"\{(\w+)\}")


# ---------------------------------------------------------------------------
# render — sustituye marcadores en la plantilla con los valores dados
# ---------------------------------------------------------------------------

def render(plantilla: str, variables: Dict[str, Any]) -> str:
    """
    Reemplaza los marcadores {variable} en *plantilla* con los valores de *variables*.

    Falla fuerte (OQ-4): si algún marcador no tiene valor en *variables*,
    lanza VariablePlantillaFaltanteError inmediatamente.
    No retorna resultados parciales.

    Args:
        plantilla: texto con marcadores {variable}.
        variables: dict de nombre → valor a sustituir.

    Returns:
        Texto con todos los marcadores reemplazados.

    Raises:
        VariablePlantillaFaltanteError: si hay algún marcador sin valor.
    """
    # Primero validar que TODAS las variables estén presentes (fail-fast).
    for match in _MARCADOR_RE.finditer(plantilla):
        nombre = match.group(1)
        if nombre not in variables:
            raise VariablePlantillaFaltanteError(variable=nombre, plantilla=plantilla)

    # Todas las variables están presentes — sustituir.
    return _MARCADOR_RE.sub(lambda m: str(variables[m.group(1)]), plantilla)
