"""
TDD tests for derive_aprobado (calificacion_aprobado.py).

C-10 Design Decision D4:
    derive_aprobado(nota_numerica, nota_textual, nota_maxima, umbral_pct, valores_aprobatorios) -> bool

Rules under test:
    RN-02/RN-03: numeric precedence over textual.
    RN-03: threshold is umbral_pct% of nota_maxima.
    Both null → False.

Coverage target: ≥90% of all business logic branches.
"""
import pytest

from app.services.calificacion_aprobado import derive_aprobado


# ---------------------------------------------------------------------------
# §6.1 / §6.2 — Numeric at or above threshold → True
# ---------------------------------------------------------------------------

def test_numeric_at_or_above_threshold_is_approved():
    """7/10 = 70% >= 60% → True (RN-03)."""
    assert derive_aprobado(
        nota_numerica=7,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=[],
    ) is True


# ---------------------------------------------------------------------------
# §6.3 / §6.4 — Numeric below threshold → False
# ---------------------------------------------------------------------------

def test_numeric_below_threshold_is_not_approved():
    """5/10 = 50% < 60% → False (RN-03)."""
    assert derive_aprobado(
        nota_numerica=5,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=[],
    ) is False


# ---------------------------------------------------------------------------
# §6.5 / §6.6 — Textual in approving set → True; outside → False
# ---------------------------------------------------------------------------

def test_textual_in_approving_set_is_approved():
    """nota_textual='Satisfactorio' in valores_aprobatorios → True (RN-02)."""
    assert derive_aprobado(
        nota_numerica=None,
        nota_textual="Satisfactorio",
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
    ) is True


def test_textual_outside_set_is_not_approved():
    """nota_textual='No alcanzado' not in valores_aprobatorios → False (RN-02)."""
    assert derive_aprobado(
        nota_numerica=None,
        nota_textual="No alcanzado",
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
    ) is False


# ---------------------------------------------------------------------------
# §6.7 / §6.8 — Numeric takes precedence over textual (RN-02/RN-03)
# ---------------------------------------------------------------------------

def test_numeric_takes_precedence_over_textual():
    """8/10 = 80% >= 60% AND nota_textual='No alcanzado' → True (numeric wins, RN-02)."""
    assert derive_aprobado(
        nota_numerica=8,
        nota_textual="No alcanzado",
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
    ) is True


def test_numeric_precedence_even_when_textual_would_approve():
    """3/10 = 30% < 60% AND nota_textual='Satisfactorio' → False (numeric wins below threshold)."""
    assert derive_aprobado(
        nota_numerica=3,
        nota_textual="Satisfactorio",
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=["Satisfactorio", "Supera lo esperado"],
    ) is False


# ---------------------------------------------------------------------------
# §6.9 — Both null → False
# ---------------------------------------------------------------------------

def test_both_null_is_not_approved():
    """nota_numerica=None AND nota_textual=None → False."""
    assert derive_aprobado(
        nota_numerica=None,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=["Satisfactorio"],
    ) is False


# ---------------------------------------------------------------------------
# Extra triangulation cases
# ---------------------------------------------------------------------------

def test_numeric_exactly_at_threshold_boundary():
    """6/10 = 60% == 60% → True (at boundary is approved)."""
    assert derive_aprobado(
        nota_numerica=6,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=[],
    ) is True


def test_numeric_just_below_threshold_boundary():
    """5.9/10 = 59% < 60% → False."""
    assert derive_aprobado(
        nota_numerica=5.9,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=60,
        valores_aprobatorios=[],
    ) is False


def test_umbral_100_only_perfect_score_passes():
    """umbral_pct=100 → only nota_numerica == nota_maxima passes."""
    assert derive_aprobado(
        nota_numerica=10,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=100,
        valores_aprobatorios=[],
    ) is True
    assert derive_aprobado(
        nota_numerica=9.9,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=100,
        valores_aprobatorios=[],
    ) is False


def test_umbral_0_always_passes_numerically():
    """umbral_pct=0 → any nota_numerica >= 0 is approved."""
    assert derive_aprobado(
        nota_numerica=0,
        nota_textual=None,
        nota_maxima=10.0,
        umbral_pct=0,
        valores_aprobatorios=[],
    ) is True
