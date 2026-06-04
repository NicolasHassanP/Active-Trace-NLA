"""
TDD tests for calificacion_parser.py (parse_calificaciones_file).

C-10 Design Decision D6:
    Column classification rules:
        - Numeric: header ends with '(Real)' (case-insensitive, strip) → RN-01
        - Textual: column values fall in the configured textual scale set → RN-02
        - Identity/metadata: 'Nombre', 'Apellido(s)', 'Dirección de correo', etc. → ignored
        - Rest: ignored

    parse_calificaciones_file(file_bytes, filename, escala_textual) -> PreviewCalificaciones

Coverage: detection logic for RN-01 and RN-02.
"""
import csv
import io

import openpyxl
import pytest

from app.services.calificacion_parser import (
    CalificacionValidationError,
    parse_calificaciones_file,
)
from app.schemas.calificacion import PreviewCalificaciones, ActividadDetectada


# ---------------------------------------------------------------------------
# Helpers to build test files in memory
# ---------------------------------------------------------------------------

def _make_csv_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    """Build a minimal CSV file in memory."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def _make_xlsx_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    """Build a minimal xlsx file in memory."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


_ESCALA_TEXTUAL = ["Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado"]
_IDENTITY_HEADERS = ["Nombre", "Apellido(s)", "Dirección de correo"]


# ---------------------------------------------------------------------------
# §7.1 / §7.2 — Numeric column detected by (Real) suffix
# ---------------------------------------------------------------------------

def test_detects_numeric_column_by_real_suffix():
    """Header 'Tarea 1 (Real)' → activity 'Tarea 1', escala numerica (RN-01)."""
    headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
    rows = [
        ["Ana García", "García", "ana@example.com", "8"],
        ["Luis Pérez", "Pérez", "luis@example.com", "6"],
    ]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    assert isinstance(result, PreviewCalificaciones)
    assert len(result.actividades) == 1
    act = result.actividades[0]
    assert act.actividad == "Tarea 1"
    assert act.escala == "numerica"


# ---------------------------------------------------------------------------
# §7.3 — Column without (Real) suffix is NOT numeric
# ---------------------------------------------------------------------------

def test_column_without_real_suffix_not_numeric():
    """Header 'Tarea 1' without '(Real)' → NOT detected as numeric."""
    headers = _IDENTITY_HEADERS + ["Tarea 1", "Tarea 2 (Real)"]
    rows = [
        ["Ana García", "García", "ana@example.com", "8", "9"],
    ]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    activity_names = [a.actividad for a in result.actividades]
    # Only 'Tarea 2' from '(Real)' suffix; 'Tarea 1' is ignored
    assert "Tarea 2" in activity_names
    assert "Tarea 1" not in activity_names


# ---------------------------------------------------------------------------
# §7.4 — Textual column detected by scale values
# ---------------------------------------------------------------------------

def test_detects_textual_column_by_scale_values():
    """Column with 'Satisfactorio'/'No alcanzado' → escala textual (RN-02)."""
    headers = _IDENTITY_HEADERS + ["TP 1"]
    rows = [
        ["Ana García", "García", "ana@example.com", "Satisfactorio"],
        ["Luis Pérez", "Pérez", "luis@example.com", "No alcanzado"],
    ]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    assert any(a.actividad == "TP 1" and a.escala == "textual" for a in result.actividades)


def test_column_with_mixed_scale_values_is_textual():
    """Column with some cells from textual scale (and some empty) → detected as textual."""
    headers = _IDENTITY_HEADERS + ["TP 2"]
    rows = [
        ["Ana García", "García", "ana@example.com", "Supera lo esperado"],
        ["Luis Pérez", "Pérez", "luis@example.com", ""],
    ]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    assert any(a.actividad == "TP 2" and a.escala == "textual" for a in result.actividades)


# ---------------------------------------------------------------------------
# §7.5 — Identity columns are NOT detected as activities
# ---------------------------------------------------------------------------

def test_identity_columns_ignored_as_activities():
    """'Nombre', 'Apellido(s)', 'Dirección de correo' are NOT activities."""
    headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
    rows = [["Ana García", "García", "ana@example.com", "7"]]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    activity_names = [a.actividad for a in result.actividades]
    assert "Nombre" not in activity_names
    assert "Apellido(s)" not in activity_names
    assert "Dirección de correo" not in activity_names


# ---------------------------------------------------------------------------
# §7.6 — Missing identity column raises CalificacionValidationError (422)
# ---------------------------------------------------------------------------

def test_missing_identity_column_raises_422():
    """File without any email/name column → CalificacionValidationError(422)."""
    headers = ["Tarea 1 (Real)", "TP 1"]
    rows = [["7", "Satisfactorio"]]
    file_bytes = _make_csv_bytes(headers, rows)

    with pytest.raises(CalificacionValidationError) as exc_info:
        parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Extra: xlsx support
# ---------------------------------------------------------------------------

def test_detects_numeric_column_in_xlsx():
    """xlsx file with 'Tarea 1 (Real)' header → activity 'Tarea 1', escala numerica."""
    headers = _IDENTITY_HEADERS + ["Tarea 1 (Real)"]
    rows = [["Ana", "García", "ana@example.com", 8]]
    file_bytes = _make_xlsx_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.xlsx", escala_textual=_ESCALA_TEXTUAL)

    assert any(a.actividad == "Tarea 1" and a.escala == "numerica" for a in result.actividades)


def test_both_numeric_and_textual_columns_detected():
    """File with both types → each detected with correct scale."""
    headers = _IDENTITY_HEADERS + ["Examen (Real)", "TP 1"]
    rows = [
        ["Ana García", "García", "ana@example.com", "9", "Satisfactorio"],
        ["Luis Pérez", "Pérez", "luis@example.com", "5", "No alcanzado"],
    ]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    act_map = {a.actividad: a.escala for a in result.actividades}
    assert act_map.get("Examen") == "numerica"
    assert act_map.get("TP 1") == "textual"


def test_no_activities_detected_returns_empty_list():
    """File with only identity columns → empty actividades list."""
    headers = _IDENTITY_HEADERS
    rows = [["Ana García", "García", "ana@example.com"]]
    file_bytes = _make_csv_bytes(headers, rows)
    result = parse_calificaciones_file(file_bytes, "notas.csv", escala_textual=_ESCALA_TEXTUAL)

    assert result.actividades == []
