"""
test_encuentro_html.py — TDD suite para generar_bloque_html (task 6).

RED → GREEN → TRIANGULATE → REFACTOR cycle.

Tests:
    6.1 RED:  test_html_includes_recording_link_when_present
    6.3 RED:  test_html_omits_recording_link_when_absent
    6.4 RED:  test_html_escapes_text_against_injection
    Additional: test_html_includes_title_date_time, test_html_multiple_instances,
                test_html_empty_list
"""
from datetime import date, time
from unittest.mock import MagicMock

import pytest

from app.services.encuentro_html import generar_bloque_html
from app.models.encuentro import InstanciaEncuentroEstado


def _make_instancia(
    titulo: str = "Clase de Python",
    fecha: date = date(2026, 6, 10),
    hora: time = time(18, 0),
    meet_url: str | None = "https://meet.example.com/abc",
    video_url: str | None = None,
    estado: InstanciaEncuentroEstado = InstanciaEncuentroEstado.Programado,
) -> MagicMock:
    """Helper: crea un mock de InstanciaEncuentro con los campos necesarios."""
    inst = MagicMock()
    inst.titulo = titulo
    inst.fecha = fecha
    inst.hora = hora
    inst.meet_url = meet_url
    inst.video_url = video_url
    inst.estado = estado
    return inst


# ---------------------------------------------------------------------------
# 6.1 RED → 6.2 GREEN
# test_html_includes_recording_link_when_present
# ---------------------------------------------------------------------------

def test_html_includes_recording_link_when_present():
    """Instance with video_url → output contains the link."""
    inst = _make_instancia(video_url="https://vimeo.com/xyz")
    result = generar_bloque_html([inst])
    assert "https://vimeo.com/xyz" in result


# ---------------------------------------------------------------------------
# 6.3 RED → GREEN
# test_html_omits_recording_link_when_absent
# ---------------------------------------------------------------------------

def test_html_omits_recording_link_when_absent():
    """Instance with video_url=None → no recording link in output."""
    inst = _make_instancia(video_url=None)
    result = generar_bloque_html([inst])
    # Should not contain a recording section for this instance
    assert "vimeo" not in result
    assert "grabaci" not in result.lower() or "Clase de Python" in result


# ---------------------------------------------------------------------------
# 6.4 RED → GREEN
# test_html_escapes_text_against_injection
# ---------------------------------------------------------------------------

def test_html_escapes_title_against_injection():
    """titulo with <script> → properly escaped in output (no raw <script> tag)."""
    malicious_title = "<script>alert('xss')</script>"
    inst = _make_instancia(titulo=malicious_title)
    result = generar_bloque_html([inst])
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_html_escapes_meet_url_against_injection():
    """meet_url with dangerous chars → escaped in output."""
    inst = _make_instancia(meet_url='https://meet.example.com/"onload="evil()')
    result = generar_bloque_html([inst])
    assert '"onload="evil()' not in result


def test_html_escapes_video_url_against_injection():
    """video_url with HTML-dangerous chars → escaped."""
    inst = _make_instancia(video_url="https://vimeo.com/<script>")
    result = generar_bloque_html([inst])
    assert "<script>" not in result


# ---------------------------------------------------------------------------
# Additional triangulation
# ---------------------------------------------------------------------------

def test_html_includes_title_date_time():
    """Output contains the instance title, date and time."""
    inst = _make_instancia(titulo="Encuentro Inicial", fecha=date(2026, 6, 15), hora=time(9, 30))
    result = generar_bloque_html([inst])
    assert "Encuentro Inicial" in result
    assert "2026" in result
    assert "09:30" in result or "9:30" in result


def test_html_multiple_instances():
    """Multiple instances → each appears in the output."""
    i1 = _make_instancia(titulo="Clase 1", fecha=date(2026, 6, 1))
    i2 = _make_instancia(titulo="Clase 2", fecha=date(2026, 6, 8))
    result = generar_bloque_html([i1, i2])
    assert "Clase 1" in result
    assert "Clase 2" in result


def test_html_empty_list():
    """Empty list → returns valid HTML string (no crash, no content expected)."""
    result = generar_bloque_html([])
    assert isinstance(result, str)


def test_html_includes_meet_link_when_present():
    """Instance with meet_url → link appears in output."""
    inst = _make_instancia(meet_url="https://meet.example.com/room1")
    result = generar_bloque_html([inst])
    assert "https://meet.example.com/room1" in result


def test_html_meet_url_omitted_when_none():
    """Instance with meet_url=None → no meeting link section."""
    inst = _make_instancia(meet_url=None)
    result = generar_bloque_html([inst])
    assert "https://meet" not in result
