"""
calificacion_aprobado.py — Derivación pura del campo aprobado.

C-10 Design Decision D4:
    derive_aprobado(nota_numerica, nota_textual, nota_maxima, umbral_pct, valores_aprobatorios) -> bool

Rules (RN-02/RN-03):
    1. If nota_numerica is not None and nota_maxima > 0:
         aprobado = (nota_numerica / nota_maxima) * 100 >= umbral_pct
    2. Elif nota_textual is not None:
         aprobado = nota_textual in valores_aprobatorios
    3. Else:
         aprobado = False

Numeric precedence over textual (step 1 before step 2).
Pure function — no DB, no I/O, no side effects.
Coverage target: ≥90% (this is the business logic core of C-10).

snake_case; ≤500 LOC.
"""
from typing import List, Optional, Union


def derive_aprobado(
    nota_numerica: Optional[Union[float, int]],
    nota_textual: Optional[str],
    nota_maxima: float,
    umbral_pct: int,
    valores_aprobatorios: List[str],
) -> bool:
    """
    Derive the boolean `aprobado` field from the grade and threshold.

    Args:
        nota_numerica: The numeric grade (e.g. 7.5). None if not available.
        nota_textual: The textual grade (e.g. "Satisfactorio"). None if not available.
        nota_maxima: The maximum possible numeric grade (e.g. 10.0). Must be > 0
            for numeric comparison to be meaningful.
        umbral_pct: The approval threshold as a percentage of nota_maxima (0–100).
        valores_aprobatorios: List of textual values that count as approved.

    Returns:
        True if the grade meets the approval criterion; False otherwise.

    Business rules:
        - Numeric precedence: if nota_numerica is present, it determines aprobado
          (nota_textual is ignored even if present).
        - Textual: used only when nota_numerica is None.
        - Neither present: False.
        - nota_maxima <= 0 is treated as "unable to evaluate numerically" → falls
          through to textual or False (defensive; should not occur in normal usage).
    """
    # Rule 1 — numeric branch (takes precedence over textual, RN-02/RN-03)
    if nota_numerica is not None and nota_maxima and nota_maxima > 0:
        pct = (float(nota_numerica) / nota_maxima) * 100
        return pct >= umbral_pct

    # Rule 2 — textual branch
    if nota_textual is not None:
        return nota_textual in valores_aprobatorios

    # Rule 3 — both None → not approved
    return False
