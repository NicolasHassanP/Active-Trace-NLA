"""
analisis_calculo.py — Cálculo puro de ranking y nota final.

C-11 Design Decisions:
    D7 — Nota final = promedio simple de nota_numerica de actividades seleccionadas
         (OQ-C11-1: promedio simple confirmado). Función pura y determinista.
    RN-09 — Ranking ordena desc por cantidad de aprobadas entre actividades seleccionadas;
             excluye alumnos sin ninguna aprobada.

Funciones puras — sin side effects, 100% testeable sin DB.
snake_case; ≤500 LOC.
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from app.schemas.analisis import NotaFinalAlumno, RankingFila


# ---------------------------------------------------------------------------
# Helpers de agregación
# ---------------------------------------------------------------------------

def _count_aprobadas_seleccionadas(
    actividades_seleccionadas: List[str],
    calificaciones: List[dict],
) -> int:
    """
    Cuenta cuántas actividades seleccionadas tienen aprobado=True.

    Solo considera actividades que están en la lista seleccionada.
    """
    actividades_set = set(actividades_seleccionadas)
    return sum(
        1
        for c in calificaciones
        if c["actividad"] in actividades_set and c["aprobado"]
    )


def _notas_numericas_seleccionadas(
    actividades_seleccionadas: List[str],
    calificaciones: List[dict],
) -> List[Decimal]:
    """
    Extrae nota_numerica de actividades seleccionadas, ignorando nulls.
    """
    actividades_set = set(actividades_seleccionadas)
    notas: List[Decimal] = []
    for c in calificaciones:
        if c["actividad"] in actividades_set and c["nota_numerica"] is not None:
            notas.append(Decimal(str(c["nota_numerica"])))
    return notas


# ---------------------------------------------------------------------------
# calcular_ranking — función pura (RN-09)
# ---------------------------------------------------------------------------

def calcular_ranking(
    actividades_seleccionadas: List[str],
    calificaciones_por_alumno: Dict[uuid.UUID, List[dict]],
) -> List[RankingFila]:
    """
    Computa el ranking de alumnos por cantidad de actividades aprobadas.

    RN-09: Solo alumnos con al menos una actividad aprobada entre las seleccionadas.
    Orden: descendente por cantidad_aprobadas.

    Args:
        actividades_seleccionadas: actividades a considerar.
        calificaciones_por_alumno: mapa { entrada_padron_id → [calificaciones] }.

    Returns:
        Lista de RankingFila ordenada desc por cantidad_aprobadas.
        Solo alumnos con al menos 1 aprobada (RN-09).

    Pure function — no DB access, no I/O, deterministic.
    """
    filas: List[RankingFila] = []

    for alumno_id, calificaciones in calificaciones_por_alumno.items():
        cantidad = _count_aprobadas_seleccionadas(actividades_seleccionadas, calificaciones)
        if cantidad > 0:
            filas.append(
                RankingFila(
                    entrada_padron_id=alumno_id,
                    cantidad_aprobadas=cantidad,
                )
            )

    # Ordenar descendente por cantidad_aprobadas (RN-09)
    filas.sort(key=lambda f: f.cantidad_aprobadas, reverse=True)
    return filas


# ---------------------------------------------------------------------------
# calcular_nota_final — función pura, determinista (D7, F2.5)
# ---------------------------------------------------------------------------

def calcular_nota_final(
    actividades_seleccionadas: List[str],
    calificaciones_por_alumno: Dict[uuid.UUID, List[dict]],
) -> List[NotaFinalAlumno]:
    """
    Calcula la nota final por alumno como promedio simple de nota_numerica.

    OQ-C11-1 (resuelto): promedio simple de nota_numerica de actividades seleccionadas.
    Si el alumno no tiene nota_numerica en ninguna actividad seleccionada → nota_final=None.

    Args:
        actividades_seleccionadas: actividades a considerar.
        calificaciones_por_alumno: mapa { entrada_padron_id → [calificaciones] }.

    Returns:
        Lista de NotaFinalAlumno con nota_final y actividades_consideradas.
        Un elemento por alumno, aunque no tenga calificaciones.

    Pure function — no DB access, no I/O, deterministic.
    """
    resultado: List[NotaFinalAlumno] = []

    for alumno_id, calificaciones in calificaciones_por_alumno.items():
        notas = _notas_numericas_seleccionadas(actividades_seleccionadas, calificaciones)

        if notas:
            promedio = sum(notas) / len(notas)
            # Redondear a 2 decimales para consistencia
            nota_final: Optional[Decimal] = Decimal(str(promedio)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            actividades_consideradas = len(notas)
        else:
            nota_final = None
            actividades_consideradas = 0

        resultado.append(
            NotaFinalAlumno(
                entrada_padron_id=alumno_id,
                nota_final=nota_final,
                actividades_consideradas=actividades_consideradas,
            )
        )

    return resultado
