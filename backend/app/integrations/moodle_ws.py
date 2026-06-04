"""
moodle_ws.py — Cliente async para Moodle Web Services.

C-09 Design Decision D7:
    - async httpx.AsyncClient
    - Máximo 2 intentos, asyncio.sleep(2) entre ellos
    - Token NUNCA aparece en mensajes de error ni logs
    - MoodleWSError(502) si ambos intentos fallan

MoodleWSClient.get_enrolled_users(course_id) → list[dict]:
    Llama core_enrol_get_enrolled_users del WS de Moodle.
    Retorna lista de user dicts tal como los retorna Moodle.

snake_case; ≤500 LOC.
"""
import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepción de dominio
# ---------------------------------------------------------------------------

class MoodleWSError(Exception):
    """
    Error de integración con Moodle Web Services.

    status_code: 502 (upstream no disponible).
    detail: descripción del error SIN incluir el token.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# ---------------------------------------------------------------------------
# MoodleWSClient
# ---------------------------------------------------------------------------

class MoodleWSClient:
    """
    Cliente async para Moodle Web Services.

    Configuración via constructor:
        base_url: URL base de la instancia Moodle (ej. "https://moodle.example.com")
        token:    Token de autenticación (NUNCA aparece en logs o errores)

    Retry simple: 2 intentos máximo con asyncio.sleep(2) entre ellos.
    Si ambos fallan → raise MoodleWSError(502, ...) con mensaje genérico.
    """

    _WS_PATH = "/webservice/rest/server.php"
    _MAX_ATTEMPTS = 2
    _RETRY_SLEEP = 2

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    async def get_enrolled_users(self, course_id: int) -> list[dict[str, Any]]:
        """
        Obtiene usuarios matriculados en un curso de Moodle.

        Llama core_enrol_get_enrolled_users con el course_id dado.
        Retorna lista de user dicts tal como los retorna Moodle.

        Raises MoodleWSError(502) si ambos intentos fallan.
        Token NUNCA aparece en el mensaje de error.
        """
        url = f"{self._base_url}{self._WS_PATH}"
        params = {
            "wstoken": self._token,
            "wsfunction": "core_enrol_get_enrolled_users",
            "moodlewsrestformat": "json",
            "courseid": course_id,
        }

        last_exc: Exception | None = None

        async with httpx.AsyncClient() as client:
            for attempt in range(1, self._MAX_ATTEMPTS + 1):
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
                    last_exc = exc
                    logger.warning(
                        "Moodle WS attempt %d/%d failed for course_id=%s: %s",
                        attempt,
                        self._MAX_ATTEMPTS,
                        course_id,
                        # Log the error type, NOT the token
                        type(exc).__name__,
                    )
                    if attempt < self._MAX_ATTEMPTS:
                        await asyncio.sleep(self._RETRY_SLEEP)

        # Both attempts failed — raise generic error WITHOUT the token
        raise MoodleWSError(
            status_code=502,
            detail=(
                f"Moodle WS no disponible: no se pudo obtener los usuarios "
                f"del curso {course_id} tras {self._MAX_ATTEMPTS} intentos. "
                f"Verifique la conectividad con Moodle."
            ),
        )
