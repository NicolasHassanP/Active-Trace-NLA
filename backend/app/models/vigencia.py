"""
Helper de vigencia temporal para Asignacion.

C-07 Design Decision D4:
    estado_vigencia es DERIVADO en runtime, NO una columna de DB.
    Este módulo expone la función pura `estado_vigencia` y el enum `EstadoVigencia`.

OQ-4 RESUELTA: este helper es SOLO de dominio; NO se integra en `require_permission`
ni en la resolución de permisos efectivos — eso es un change posterior.
"""
import enum
from datetime import date
from typing import Optional


class EstadoVigencia(str, enum.Enum):
    """Estado de vigencia temporal de una asignación."""
    vigente = "vigente"
    vencida = "vencida"
    no_iniciada = "no_iniciada"


def estado_vigencia(
    desde: date,
    hasta: Optional[date],
    hoy: Optional[date] = None,
) -> EstadoVigencia:
    """
    Calcula el estado de vigencia de una asignación.

    Reglas:
        - vigente:     desde <= hoy AND (hasta IS NULL OR hasta >= hoy)
        - vencida:     hasta IS NOT NULL AND hasta < hoy
        - no_iniciada: desde > hoy

    Args:
        desde:  fecha de inicio de la asignación (NOT NULL).
        hasta:  fecha de fin de la asignación (nullable = abierta).
        hoy:    fecha de referencia (default: date.today() UTC).

    Returns:
        EstadoVigencia — nunca None, nunca levanta excepción.
    """
    if hoy is None:
        hoy = date.today()

    if desde > hoy:
        return EstadoVigencia.no_iniciada

    if hasta is not None and hasta < hoy:
        return EstadoVigencia.vencida

    return EstadoVigencia.vigente
