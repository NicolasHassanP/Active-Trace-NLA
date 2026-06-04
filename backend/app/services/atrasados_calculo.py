"""
atrasados_calculo.py — Cálculo puro de alumnos atrasados.

C-11 Design Decision D2:
    calcular_atrasados es una función pura (sin DB, sin I/O) que implementa RN-06.
    El servicio arma la entrada (mapa alumno→calificaciones) desde el repositorio
    y delega el cómputo aquí. Mismo patrón que calificacion_aprobado.derive_aprobado.

RN-06: Un alumno es atrasado si:
    (a) tiene al menos una actividad seleccionada sin calificación registrada (faltante)
    (b) tiene al menos una calificación con aprobado=False (reprobada)

Funciones puras — sin side effects, 100% testeable sin DB.
snake_case; ≤500 LOC.
"""
import uuid
from typing import Dict, List

from app.schemas.analisis import AlumnoAtrasado


# ---------------------------------------------------------------------------
# Helpers de clasificación (D2, REFACTOR 2.4)
# ---------------------------------------------------------------------------

def _actividades_faltantes(
    actividades_seleccionadas: List[str],
    calificaciones: List[dict],
) -> List[str]:
    """
    Retorna actividades seleccionadas que no tienen calificación registrada.

    Una actividad es "faltante" si no existe ninguna calificación del alumno
    para esa actividad entre las seleccionadas.
    """
    actividades_con_cal = {c["actividad"] for c in calificaciones}
    return [a for a in actividades_seleccionadas if a not in actividades_con_cal]


def _actividades_no_aprobadas(
    actividades_seleccionadas: List[str],
    calificaciones: List[dict],
) -> List[str]:
    """
    Retorna actividades seleccionadas que tienen calificación con aprobado=False.

    Solo considera actividades que SÍ tienen calificación pero están reprobadas.
    Las faltantes se reportan por separado.
    """
    reprobadas: List[str] = []
    actividades_set = set(actividades_seleccionadas)
    for c in calificaciones:
        if c["actividad"] in actividades_set and not c["aprobado"]:
            if c["actividad"] not in reprobadas:
                reprobadas.append(c["actividad"])
    return reprobadas


# ---------------------------------------------------------------------------
# calcular_atrasados — función pura principal (D2, RN-06)
# ---------------------------------------------------------------------------

def calcular_atrasados(
    actividades_seleccionadas: List[str],
    calificaciones_por_alumno: Dict[uuid.UUID, List[dict]],
) -> List[AlumnoAtrasado]:
    """
    Computa la lista de alumnos atrasados dado un conjunto de actividades seleccionadas
    y el mapa de calificaciones por alumno.

    Args:
        actividades_seleccionadas: lista de nombres de actividades a evaluar.
        calificaciones_por_alumno: mapa { entrada_padron_id → [calificaciones] }.
            Cada calificación es un dict con claves:
            - entrada_padron_id: UUID
            - actividad: str
            - aprobado: bool
            - nota_numerica: Optional[float]
            - nota_textual: Optional[str]

    Returns:
        Lista de AlumnoAtrasado — solo alumnos que cumplen al menos (a) o (b).
        Lista vacía si no hay actividades seleccionadas o ningún alumno está atrasado.

    Pure function — no DB access, no I/O, deterministic.
    """
    if not actividades_seleccionadas:
        return []

    atrasados: List[AlumnoAtrasado] = []

    for alumno_id, calificaciones in calificaciones_por_alumno.items():
        faltantes = _actividades_faltantes(actividades_seleccionadas, calificaciones)
        no_aprobadas = _actividades_no_aprobadas(actividades_seleccionadas, calificaciones)

        if faltantes or no_aprobadas:
            atrasados.append(
                AlumnoAtrasado(
                    entrada_padron_id=alumno_id,
                    actividades_faltantes=faltantes,
                    actividades_no_aprobadas=no_aprobadas,
                )
            )

    return atrasados
