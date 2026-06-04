"""
calificacion_parser.py — Parser de archivos de calificaciones del LMS (xlsx/csv).

C-10 Design Decision D6:
    Column classification:
        - Identity: Nombre, Apellido(s), Dirección de correo (and common variants).
          These are used to link rows to EntradaPadron but are NOT activities.
        - Numeric: header ends with '(Real)' (case-insensitive, strip). RN-01.
          Activity name = header stripped of the '(Real)' suffix.
        - Textual: column values (non-empty) are a subset of the configured
          escala_textual set. RN-02.
        - Rest: ignored (e.g. course metadata columns).

    parse_calificaciones_file(file_bytes, filename, escala_textual) -> PreviewCalificaciones

CalificacionValidationError(status_code, detail): mapped to 422 in the router.

No DB writes — pure in-memory parse.
snake_case; ≤500 LOC.
"""
import csv
import io
import re
from typing import Any, Dict, List, Optional, Set

from app.schemas.calificacion import ActividadDetectada, PreviewCalificaciones


# ---------------------------------------------------------------------------
# Domain exception
# ---------------------------------------------------------------------------

class CalificacionValidationError(Exception):
    """
    Error de validación del archivo de calificaciones.

    status_code: código HTTP a retornar (típicamente 422).
    detail: descripción del error.
    """

    def __init__(self, status_code: int, detail: object) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# Identity column detection
# ---------------------------------------------------------------------------

# Normalized patterns for identity/metadata headers (case-insensitive strip).
# These columns are used to identify the student row but are NOT activities.
_IDENTITY_PATTERNS: List[re.Pattern] = [
    re.compile(r"^nombre$", re.IGNORECASE),
    re.compile(r"^apellido", re.IGNORECASE),          # apellido, apellido(s), apellidos
    re.compile(r"^direcci[oó]n de correo$", re.IGNORECASE),
    re.compile(r"^email$", re.IGNORECASE),
    re.compile(r"^correo$", re.IGNORECASE),
    re.compile(r"^correo electr[oó]nico$", re.IGNORECASE),
    re.compile(r"^id\s*n[uú]mero$", re.IGNORECASE),
    re.compile(r"^id$", re.IGNORECASE),
    re.compile(r"^instituc", re.IGNORECASE),
    re.compile(r"^departamento$", re.IGNORECASE),
    re.compile(r"^calificaci[oó]n$", re.IGNORECASE),  # Total/summary row
]

# These column names are treated as the email field for identity linking (D7)
_EMAIL_PATTERNS: List[re.Pattern] = [
    re.compile(r"^direcci[oó]n de correo$", re.IGNORECASE),
    re.compile(r"^email$", re.IGNORECASE),
    re.compile(r"^correo$", re.IGNORECASE),
    re.compile(r"^correo electr[oó]nico$", re.IGNORECASE),
]


def _is_identity_header(h: str) -> bool:
    """Return True if the header represents an identity/metadata column."""
    stripped = h.strip()
    return any(pat.match(stripped) for pat in _IDENTITY_PATTERNS)


def _is_email_header(h: str) -> bool:
    """Return True if the header is an email column."""
    stripped = h.strip()
    return any(pat.match(stripped) for pat in _EMAIL_PATTERNS)


def _is_name_header(h: str) -> bool:
    """Return True if the header is a name/nombre column."""
    stripped = h.strip()
    return bool(re.match(r"^nombre$", stripped, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Numeric column detection (RN-01)
# ---------------------------------------------------------------------------

_REAL_SUFFIX_PATTERN = re.compile(r"\(Real\)\s*$", re.IGNORECASE)


def _is_numeric_header(h: str) -> bool:
    """Return True if header ends with '(Real)' (case-insensitive)."""
    return bool(_REAL_SUFFIX_PATTERN.search(h.strip()))


def _strip_real_suffix(h: str) -> str:
    """Return the activity name by removing the '(Real)' suffix."""
    return _REAL_SUFFIX_PATTERN.sub("", h.strip()).strip()


# ---------------------------------------------------------------------------
# Textual column detection (RN-02)
# ---------------------------------------------------------------------------

def _is_textual_column(values: List[str], escala_textual: Set[str]) -> bool:
    """
    Return True if the column's non-empty values are a subset of escala_textual.

    A column is textual when at least one of its non-empty values matches the
    configured textual scale. Empty cells are allowed (student may not have submitted).
    """
    non_empty = [v.strip() for v in values if v and v.strip()]
    if not non_empty:
        return False
    return all(v in escala_textual for v in non_empty)


# ---------------------------------------------------------------------------
# Identity validation
# ---------------------------------------------------------------------------

def _find_email_column(headers: List[str]) -> Optional[int]:
    """Return the index of the email column, or None if not found."""
    for i, h in enumerate(headers):
        if _is_email_header(h):
            return i
    return None


def _find_name_column(headers: List[str]) -> Optional[int]:
    """Return the index of the name column, or None if not found."""
    for i, h in enumerate(headers):
        if _is_name_header(h):
            return i
    return None


# ---------------------------------------------------------------------------
# Core parse logic
# ---------------------------------------------------------------------------

def _classify_columns(
    headers: List[str],
    column_values: Dict[int, List[str]],
    escala_textual: Set[str],
) -> List[ActividadDetectada]:
    """
    Classify each header into: identity, numeric, textual, or ignored.

    Returns a list of ActividadDetectada for numeric and textual columns.
    """
    activities: List[ActividadDetectada] = []

    for i, h in enumerate(headers):
        h_stripped = h.strip()

        # Skip identity/metadata columns
        if _is_identity_header(h_stripped):
            continue

        # Numeric: ends with (Real) — RN-01
        if _is_numeric_header(h_stripped):
            activity_name = _strip_real_suffix(h_stripped)
            activities.append(
                ActividadDetectada(actividad=activity_name, escala="numerica")
            )
            continue

        # Textual: values in escala set — RN-02
        col_vals = column_values.get(i, [])
        if _is_textual_column(col_vals, escala_textual):
            activities.append(
                ActividadDetectada(actividad=h_stripped, escala="textual")
            )
            # Fall through to ignore everything else

    return activities


def _rows_to_preview(
    headers: List[str],
    data_rows: List[List[Any]],
    escala_textual: Set[str],
) -> PreviewCalificaciones:
    """
    Build PreviewCalificaciones from headers + data rows.

    Validates that at least one identity column (email or name) is present.
    """
    # Validate identity column presence
    email_idx = _find_email_column(headers)
    name_idx = _find_name_column(headers)
    if email_idx is None and name_idx is None:
        raise CalificacionValidationError(
            status_code=422,
            detail=(
                "El archivo no contiene ninguna columna de identidad reconocible "
                "(se esperan 'Dirección de correo', 'Email', 'Nombre' u otra columna "
                "de identidad para vincular las notas con el padrón)."
            ),
        )

    # Build per-column value lists for textual detection
    column_values: Dict[int, List[str]] = {i: [] for i in range(len(headers))}
    filas: List[Dict[str, Any]] = []

    for row in data_rows:
        # Skip completely empty rows
        if all(v is None or str(v).strip() == "" for v in row):
            continue

        row_dict: Dict[str, Any] = {}
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else None
            row_dict[h.strip()] = val
            column_values[i].append(str(val) if val is not None else "")

        filas.append(row_dict)

    # Classify columns
    activities = _classify_columns(headers, column_values, escala_textual)

    return PreviewCalificaciones(
        actividades=activities,
        filas=filas,
        no_en_padron=[],  # Populated during importar (requires DB lookup)
    )


# ---------------------------------------------------------------------------
# Format-specific parsers
# ---------------------------------------------------------------------------

def _parse_xlsx(
    file_bytes: bytes,
    escala_textual: Set[str],
) -> PreviewCalificaciones:
    """Parse an xlsx file and return PreviewCalificaciones."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)

    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise CalificacionValidationError(
            status_code=422,
            detail="El archivo está vacío o no tiene encabezados.",
        )

    headers = [str(h) if h is not None else "" for h in header_row]
    data_rows = [list(row) for row in rows_iter]
    wb.close()

    return _rows_to_preview(headers, data_rows, escala_textual)


def _parse_csv(
    file_bytes: bytes,
    escala_textual: Set[str],
) -> PreviewCalificaciones:
    """Parse a CSV file and return PreviewCalificaciones."""
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    reader = csv.reader(io.StringIO(content))

    try:
        headers = next(reader)
    except StopIteration:
        raise CalificacionValidationError(
            status_code=422,
            detail="El archivo CSV está vacío o no tiene encabezados.",
        )

    data_rows = list(reader)
    return _rows_to_preview(headers, data_rows, escala_textual)


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def parse_calificaciones_file(
    file_bytes: bytes,
    filename: str,
    *,
    escala_textual: Optional[List[str]] = None,
) -> PreviewCalificaciones:
    """
    Parse a grades file (xlsx or csv) and return a PreviewCalificaciones.

    Detects the format by file extension. Classifies columns into:
        - Numeric activities: header ends with '(Real)' (RN-01).
        - Textual activities: column values fall in escala_textual (RN-02).
        - Identity/metadata: ignored as activities but used for student linkage.

    Does NOT write to DB — pure in-memory.

    Args:
        file_bytes: raw file content.
        filename:   original filename (used to detect extension).
        escala_textual: list of textual grade values that define the textual scale
            (e.g. ["Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado"]).
            Defaults to VALORES_APROBATORIOS_DEFECTO + non-approving values from config.

    Returns:
        PreviewCalificaciones with detected activities and student rows.

    Raises:
        CalificacionValidationError(422): missing identity column, unsupported format.
    """
    if escala_textual is None:
        from app.core.config import Settings
        s = Settings()
        escala_textual = s.VALORES_APROBATORIOS_DEFECTO + [
            "No satisfactorio", "No alcanzado"
        ]

    escala_set: Set[str] = set(escala_textual)
    lower_name = filename.strip().lower()

    if lower_name.endswith(".xlsx"):
        return _parse_xlsx(file_bytes, escala_set)
    elif lower_name.endswith(".csv"):
        return _parse_csv(file_bytes, escala_set)
    else:
        raise CalificacionValidationError(
            status_code=422,
            detail=(
                f"Formato de archivo no soportado: '{filename}'. "
                "Solo se aceptan archivos .xlsx y .csv."
            ),
        )
