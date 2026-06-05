"""
test_fecha_academica_html.py — TDD RED/GREEN tests for C-17 fecha_academica_html.

Tasks 5.1–5.3:
    5.1 RED: generar_fragmento_calendario([]) devuelve fragmento vacío bien formado.
    5.2 GREEN: función pura implementada que escapa con html.escape (D6).
    5.3 TRIANGULATE: test XSS — titulo con <script> se emite escapado.

No DB needed — pure function tests.
"""
import html

import pytest


# ---------------------------------------------------------------------------
# 5.1 RED — empty list returns well-formed fragment
# ---------------------------------------------------------------------------

def test_fragmento_vacio_bien_formado():
    """5.1 RED: generar_fragmento_calendario([]) returns well-formed empty fragment."""
    from app.services.fecha_academica_html import generar_fragmento_calendario
    result = generar_fragmento_calendario([])
    assert isinstance(result, str)
    # Must be some HTML wrapping (non-empty string, even if no items)
    assert len(result) > 0
    # Must not raise an error — a div-like structure expected
    assert "<" in result and ">" in result


# ---------------------------------------------------------------------------
# 5.2 GREEN — fragment with fechas lists tipo/numero/fecha/titulo
# ---------------------------------------------------------------------------

def test_fragmento_con_fechas():
    """5.2 GREEN: fragment with fechas lists tipo, numero, fecha, titulo."""
    from app.services.fecha_academica_html import generar_fragmento_calendario
    from datetime import date

    class FechaFake:
        def __init__(self, tipo, numero, fecha, titulo):
            self.tipo = tipo
            self.numero = numero
            self.fecha = fecha
            self.titulo = titulo

    fechas = [
        FechaFake("Parcial", 1, date(2026, 5, 10), "Primer Parcial"),
        FechaFake("TP", 2, date(2026, 6, 15), "TP Final"),
    ]

    result = generar_fragmento_calendario(fechas)
    # Should contain relevant data
    assert "Parcial" in result
    assert "Primer Parcial" in result
    assert "2026-05-10" in result or "2026" in result
    assert "TP" in result
    assert "TP Final" in result


def test_fragmento_numero_aparece():
    """5.2 GREEN: fragment includes numero for each fecha."""
    from app.services.fecha_academica_html import generar_fragmento_calendario
    from datetime import date

    class FechaFake:
        def __init__(self, tipo, numero, fecha, titulo):
            self.tipo = tipo
            self.numero = numero
            self.fecha = fecha
            self.titulo = titulo

    fechas = [FechaFake("Coloquio", 1, date(2026, 7, 20), "Coloquio Especial")]
    result = generar_fragmento_calendario(fechas)
    assert "1" in result  # numero appears
    assert "Coloquio" in result


# ---------------------------------------------------------------------------
# 5.3 TRIANGULATE — XSS escaping
# ---------------------------------------------------------------------------

def test_xss_en_titulo_escapado():
    """5.3 TRIANGULATE: titulo with <script>alert(1)</script> is escaped, not executed."""
    from app.services.fecha_academica_html import generar_fragmento_calendario
    from datetime import date

    class FechaFake:
        def __init__(self, tipo, numero, fecha, titulo):
            self.tipo = tipo
            self.numero = numero
            self.fecha = fecha
            self.titulo = titulo

    malicious_titulo = "<script>alert(1)</script>"
    fechas = [FechaFake("Parcial", 1, date(2026, 5, 10), malicious_titulo)]
    result = generar_fragmento_calendario(fechas)

    # The raw script tag should NOT appear
    assert "<script>" not in result
    assert "</script>" not in result
    # The escaped version should appear
    assert "&lt;script&gt;" in result


def test_xss_en_tipo_escapado():
    """5.3 TRIANGULATE: tipo with HTML special chars is escaped."""
    from app.services.fecha_academica_html import generar_fragmento_calendario
    from datetime import date

    class FechaFake:
        def __init__(self, tipo, numero, fecha, titulo):
            self.tipo = tipo
            self.numero = numero
            self.fecha = fecha
            self.titulo = titulo

    malicious_tipo = '<img src=x onerror=alert(1)>'
    fechas = [FechaFake(malicious_tipo, 1, date(2026, 5, 10), "Test")]
    result = generar_fragmento_calendario(fechas)

    # Raw tag should not appear
    assert "<img" not in result
    # Escaped entities should appear
    assert "&lt;" in result


def test_fragmento_vacio_no_tiene_items():
    """5.3 TRIANGULATE: empty fragment has no item elements."""
    from app.services.fecha_academica_html import generar_fragmento_calendario
    result = generar_fragmento_calendario([])
    # Should be a well-formed wrapper without date item entries
    # (checking for class patterns used in the actual implementation)
    assert "fecha-item" not in result or result.count("fecha-item") == 0
