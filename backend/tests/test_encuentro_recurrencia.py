"""
test_encuentro_recurrencia.py — TDD suite para generar_fechas (task 5).

RED → GREEN → TRIANGULATE → REFACTOR cycle.

Tests:
    5.1 RED:  test_generates_one_date_per_week — fecha_inicio Tuesday, Martes, 4 semanas
    5.3 RED:  test_first_instance_snaps_to_day_of_week — Monday start, Jueves requested
    5.5 RED:  test_cant_semanas_zero_returns_empty + test_cant_semanas_one_returns_single
    Additional: test_weekly_step_is_exactly_7_days, test_start_date_already_correct
"""
from datetime import date, timedelta

import pytest

from app.services.encuentro_recurrencia import generar_fechas
from app.models.encuentro import DiaSemana


# ---------------------------------------------------------------------------
# 5.1 GREEN (after 5.2 implements module)
# test_generates_one_date_per_week
# ---------------------------------------------------------------------------

def test_generates_one_date_per_week():
    """
    fecha_inicio on a Tuesday, dia_semana=Martes, cant_semanas=4
    → 4 dates each 7 days apart, starting from that Tuesday.
    """
    # 2026-06-02 is a Tuesday
    fecha_inicio = date(2026, 6, 2)
    result = generar_fechas(fecha_inicio, DiaSemana.Martes, 4)
    assert len(result) == 4
    for i in range(1, 4):
        delta = result[i] - result[i - 1]
        assert delta == timedelta(days=7), f"Gap between dates {i-1} and {i} is {delta}, expected 7 days"


# ---------------------------------------------------------------------------
# 5.3 RED → 5.4 GREEN
# test_first_instance_snaps_to_day_of_week
# ---------------------------------------------------------------------------

def test_first_instance_snaps_to_day_of_week():
    """
    fecha_inicio Monday (2026-06-01), dia_semana=Jueves, cant_semanas=2
    → first date is next Thursday (2026-06-04), second is +7 days (2026-06-11).
    """
    # 2026-06-01 is a Monday
    fecha_inicio = date(2026, 6, 1)
    result = generar_fechas(fecha_inicio, DiaSemana.Jueves, 2)
    assert len(result) == 2
    # First Thursday on or after 2026-06-01
    assert result[0] == date(2026, 6, 4), f"Expected 2026-06-04, got {result[0]}"
    assert result[1] == date(2026, 6, 11), f"Expected 2026-06-11, got {result[1]}"


# ---------------------------------------------------------------------------
# 5.5 RED → GREEN: boundary counts
# ---------------------------------------------------------------------------

def test_cant_semanas_zero_returns_empty():
    """cant_semanas=0 → empty list."""
    result = generar_fechas(date(2026, 6, 1), DiaSemana.Lunes, 0)
    assert result == []


def test_cant_semanas_one_returns_single():
    """cant_semanas=1 → exactly one date."""
    # 2026-06-03 is a Wednesday
    fecha_inicio = date(2026, 6, 3)
    result = generar_fechas(fecha_inicio, DiaSemana.Miercoles, 1)
    assert len(result) == 1
    assert result[0] == date(2026, 6, 3)


# ---------------------------------------------------------------------------
# Additional triangulation
# ---------------------------------------------------------------------------

def test_start_date_already_matches():
    """If fecha_inicio already matches dia_semana, it is the first date."""
    # 2026-06-05 is a Friday
    fecha_inicio = date(2026, 6, 5)
    result = generar_fechas(fecha_inicio, DiaSemana.Viernes, 3)
    assert result[0] == date(2026, 6, 5)
    assert result[1] == date(2026, 6, 12)
    assert result[2] == date(2026, 6, 19)


def test_snap_wraps_correctly_to_next_week():
    """
    fecha_inicio Friday (2026-06-05), dia_semana=Lunes, cant_semanas=2
    → first Monday on or after Friday → next Monday 2026-06-08, then 2026-06-15.
    """
    fecha_inicio = date(2026, 6, 5)  # Friday
    result = generar_fechas(fecha_inicio, DiaSemana.Lunes, 2)
    assert result[0] == date(2026, 6, 8), f"Expected 2026-06-08, got {result[0]}"
    assert result[1] == date(2026, 6, 15)


def test_generates_52_weeks():
    """cant_semanas=52 → exactly 52 dates."""
    fecha_inicio = date(2026, 1, 5)  # Monday
    result = generar_fechas(fecha_inicio, DiaSemana.Lunes, 52)
    assert len(result) == 52


def test_domingo_dia_semana():
    """DiaSemana.Domingo snaps to next Sunday correctly."""
    # 2026-06-01 is Monday, next Sunday is 2026-06-07
    result = generar_fechas(date(2026, 6, 1), DiaSemana.Domingo, 2)
    assert result[0] == date(2026, 6, 7)
    assert result[1] == date(2026, 6, 14)
