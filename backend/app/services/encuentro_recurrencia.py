"""
encuentro_recurrencia.py — Generación de fechas recurrentes para encuentros.

C-13 Design Decision D4:
    generar_fechas avanza fecha_inicio al primer día que coincida con
    dia_semana (si ya coincide, esa es la primera). Luego genera
    cant_semanas fechas con paso semanal de 7 días.

Función pura: sin efectos secundarios, sin dependencias de red/DB.
snake_case; ≤500 LOC.
"""
from datetime import date, timedelta
from typing import List

from app.models.encuentro import DiaSemana


# Mapping from DiaSemana to Python weekday() value (0=Monday … 6=Sunday)
_DIA_A_WEEKDAY: dict[DiaSemana, int] = {
    DiaSemana.Lunes:    0,
    DiaSemana.Martes:   1,
    DiaSemana.Miercoles: 2,
    DiaSemana.Jueves:   3,
    DiaSemana.Viernes:  4,
    DiaSemana.Sabado:   5,
    DiaSemana.Domingo:  6,
}


def generar_fechas(
    fecha_inicio: date,
    dia_semana: DiaSemana,
    cant_semanas: int,
) -> List[date]:
    """
    Genera una lista de cant_semanas fechas semanales.

    Algoritmo (D4):
        1. Avanzar fecha_inicio al primer día que coincida con dia_semana.
           Si fecha_inicio ya coincide, esa es la primera fecha.
        2. Generar cant_semanas fechas con paso de 7 días.

    Args:
        fecha_inicio:  Fecha de referencia desde la que calcular.
        dia_semana:    Día de la semana deseado.
        cant_semanas:  Número de fechas a generar (0 → lista vacía).

    Returns:
        Lista de date, en orden cronológico, una por semana.
    """
    if cant_semanas <= 0:
        return []

    target_weekday = _DIA_A_WEEKDAY[dia_semana]
    current_weekday = fecha_inicio.weekday()

    # Days to advance to reach the target weekday
    days_ahead = (target_weekday - current_weekday) % 7
    primera_fecha = fecha_inicio + timedelta(days=days_ahead)

    fechas: List[date] = []
    for i in range(cant_semanas):
        fechas.append(primera_fecha + timedelta(weeks=i))

    return fechas
