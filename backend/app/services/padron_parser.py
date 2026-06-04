"""
padron_parser.py — Parser de archivos de padrón (xlsx/csv).

C-09 Design Decision D5: importación en dos pasos (preview sin escritura + confirm).

parse_padron_file(file_bytes, filename) → list[PadronRowDTO]:
    - Detecta formato por extensión (.xlsx, .csv).
    - Valida columnas requeridas (nombre, apellidos, email).
    - Valida límite de filas (PADRON_MAX_ROWS, default 5000).
    - Retorna lista de PadronRowDTO.

PadronValidationError(status_code, detail): excepción de dominio mapeada a 422 en el router.

No escribe en DB — parseo en memoria puro.
snake_case; ≤500 LOC.
"""
import csv
import io
from typing import Optional

from app.schemas.padron import PadronRowDTO


# ---------------------------------------------------------------------------
# Excepción de dominio
# ---------------------------------------------------------------------------

class PadronValidationError(Exception):
    """
    Error de validación del archivo de padrón.

    status_code: código HTTP a retornar (típicamente 422).
    detail: descripción del error o lista de errores.
    """

    def __init__(self, status_code: int, detail: object) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# Columnas requeridas y opcionales
# ---------------------------------------------------------------------------

_REQUIRED_COLUMNS = {"nombre", "apellidos", "email"}
_ALL_COLUMNS = {"nombre", "apellidos", "email", "comision", "regional"}


def _normalize_header(h: str) -> str:
    """Normaliza el header: strip + lower."""
    return h.strip().lower()


def _validate_columns(headers: list[str]) -> None:
    """
    Verifica que todas las columnas requeridas estén presentes.

    Raises PadronValidationError(422) si falta alguna columna requerida.
    """
    normalized = {_normalize_header(h) for h in headers}
    missing = _REQUIRED_COLUMNS - normalized
    if missing:
        missing_sorted = sorted(missing)
        raise PadronValidationError(
            status_code=422,
            detail=f"Columnas requeridas faltantes: {', '.join(missing_sorted)}",
        )


def _validate_row_count(count: int, max_rows: int) -> None:
    """
    Verifica que el número de filas no supere el límite configurado.

    Raises PadronValidationError(422) si se supera el límite.
    """
    if count > max_rows:
        raise PadronValidationError(
            status_code=422,
            detail=(
                f"El archivo supera el límite máximo de {max_rows} filas "
                f"(se encontraron {count} filas). "
                f"Divida el archivo en partes más pequeñas."
            ),
        )


def _row_to_dto(row: dict[str, str]) -> PadronRowDTO:
    """Convierte una fila de diccionario (headers normalizados) a PadronRowDTO."""
    # Normalizar valores: strip y convertir vacíos a None para opcionales
    def _val(key: str) -> Optional[str]:
        v = row.get(key, "").strip()
        return v if v else None

    return PadronRowDTO(
        nombre=row.get("nombre", "").strip(),
        apellidos=row.get("apellidos", "").strip(),
        email=row.get("email", "").strip(),
        comision=_val("comision"),
        regional=_val("regional"),
    )


# ---------------------------------------------------------------------------
# Parsers por formato
# ---------------------------------------------------------------------------

def _parse_xlsx(file_bytes: bytes, max_rows: int) -> list[PadronRowDTO]:
    """
    Parsea un archivo xlsx y retorna lista de PadronRowDTO.

    Usa openpyxl en modo read-only para eficiencia.
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)

    # Primera fila = headers
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise PadronValidationError(
            status_code=422,
            detail="El archivo está vacío o no tiene encabezados.",
        )

    headers = [str(h) if h is not None else "" for h in header_row]
    _validate_columns(headers)
    normalized_headers = [_normalize_header(h) for h in headers]

    # Leer filas de datos
    dtos: list[PadronRowDTO] = []
    for row_values in rows_iter:
        # Saltar filas completamente vacías
        if all(v is None or str(v).strip() == "" for v in row_values):
            continue
        row_dict = {
            normalized_headers[i]: str(row_values[i]) if row_values[i] is not None else ""
            for i in range(len(normalized_headers))
        }
        dtos.append(_row_to_dto(row_dict))

    wb.close()

    _validate_row_count(len(dtos), max_rows)
    return dtos


def _parse_csv(file_bytes: bytes, max_rows: int) -> list[PadronRowDTO]:
    """
    Parsea un archivo csv y retorna lista de PadronRowDTO.

    Usa csv.DictReader de la stdlib.
    """
    # Detectar encoding — intentar utf-8, fallback latin-1
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(content))

    # Validar columnas desde los fieldnames del reader
    if reader.fieldnames is None:
        raise PadronValidationError(
            status_code=422,
            detail="El archivo CSV está vacío o no tiene encabezados.",
        )

    _validate_columns(list(reader.fieldnames))
    normalized_map = {_normalize_header(h): h for h in reader.fieldnames}

    dtos: list[PadronRowDTO] = []
    for raw_row in reader:
        # Construir dict con headers normalizados
        row_dict = {
            norm: raw_row.get(orig, "")
            for norm, orig in normalized_map.items()
        }
        dtos.append(_row_to_dto(row_dict))

    _validate_row_count(len(dtos), max_rows)
    return dtos


# ---------------------------------------------------------------------------
# Función pública
# ---------------------------------------------------------------------------

def parse_padron_file(
    file_bytes: bytes,
    filename: str,
    *,
    max_rows: Optional[int] = None,
) -> list[PadronRowDTO]:
    """
    Parsea un archivo de padrón (xlsx o csv) y retorna lista de PadronRowDTO.

    Detecta el formato por extensión del filename.
    Valida columnas requeridas y límite de filas.
    No escribe nada en DB — puramente en memoria.

    Args:
        file_bytes: contenido del archivo como bytes.
        filename:   nombre original del archivo (usado para detectar extensión).
        max_rows:   límite de filas (defecto: lee PADRON_MAX_ROWS de Settings).

    Returns:
        Lista de PadronRowDTO.

    Raises:
        PadronValidationError(422): columnas faltantes, límite de filas superado,
                                    formato no soportado.
    """
    if max_rows is None:
        from app.core.config import Settings
        max_rows = Settings().PADRON_MAX_ROWS

    lower_name = filename.strip().lower()

    if lower_name.endswith(".xlsx"):
        return _parse_xlsx(file_bytes, max_rows)
    elif lower_name.endswith(".csv"):
        return _parse_csv(file_bytes, max_rows)
    else:
        raise PadronValidationError(
            status_code=422,
            detail=(
                f"Formato de archivo no soportado: '{filename}'. "
                "Solo se aceptan archivos .xlsx y .csv."
            ),
        )
