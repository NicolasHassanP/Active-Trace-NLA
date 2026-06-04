"""
test_moodle_ws.py — TDD suite para C-09 MoodleWSClient.

Cubre tasks 7.1–7.8 del tasks.md.

Ciclo: RED → GREEN → TRIANGULATE → REFACTOR.

Tests puramente unitarios — mock de httpx.AsyncClient.get.
No usa DB.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx


# ---------------------------------------------------------------------------
# Helpers para construir respuestas mock de Moodle WS
# ---------------------------------------------------------------------------

def _moodle_success_response(users: list[dict]) -> MagicMock:
    """Retorna un mock de httpx.Response con JSON de usuarios."""
    resp = MagicMock(spec=httpx.Response)
    resp.raise_for_status = MagicMock()  # No levanta excepción
    resp.json.return_value = users
    resp.status_code = 200
    return resp


SAMPLE_USERS = [
    {"id": 1, "firstname": "Ana", "lastname": "García", "email": "ana@moodle.com"},
    {"id": 2, "firstname": "Bob", "lastname": "López", "email": "bob@moodle.com"},
]


# ---------------------------------------------------------------------------
# Task 7.1 [RED] → 7.2 [GREEN]: get_enrolled_users exitoso
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_enrolled_users_success():
    """
    RED: MoodleWSClient.get_enrolled_users retorna lista de user dicts en llamada exitosa.
    """
    from app.integrations.moodle_ws import MoodleWSClient

    mock_resp = _moodle_success_response(SAMPLE_USERS)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        client = MoodleWSClient(base_url="https://moodle.example.com", token="mytoken")
        result = await client.get_enrolled_users(course_id=42)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["email"] == "ana@moodle.com"
    assert result[1]["email"] == "bob@moodle.com"


@pytest.mark.asyncio
async def test_get_enrolled_users_single_user():
    """
    Triangulación: un solo usuario retornado.
    """
    from app.integrations.moodle_ws import MoodleWSClient

    single = [{"id": 99, "firstname": "Solo", "lastname": "User", "email": "solo@x.com"}]
    mock_resp = _moodle_success_response(single)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")
        result = await client.get_enrolled_users(course_id=1)

    assert len(result) == 1
    assert result[0]["firstname"] == "Solo"


# ---------------------------------------------------------------------------
# Task 7.3 [RED] → 7.4 [GREEN]: reintento en primer fallo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_on_first_failure():
    """
    RED: primer httpx.get levanta HTTPError; segundo retorna JSON válido.
    → resultado retornado, 2 intentos totales.
    """
    from app.integrations.moodle_ws import MoodleWSClient

    mock_resp = _moodle_success_response(SAMPLE_USERS)
    call_count = {"n": 0}

    async def _side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.HTTPError("connection failed")
        return mock_resp

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_side_effect):
        with patch("asyncio.sleep", new_callable=AsyncMock):  # acelerar el sleep
            client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")
            result = await client.get_enrolled_users(course_id=42)

    assert len(result) == 2
    assert call_count["n"] == 2  # 2 intentos totales


@pytest.mark.asyncio
async def test_retry_called_with_sleep():
    """
    Triangulación: asyncio.sleep(2) se llama entre el primer fallo y el reintento.
    """
    from app.integrations.moodle_ws import MoodleWSClient

    mock_resp = _moodle_success_response(SAMPLE_USERS)
    call_count = {"n": 0}

    async def _side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.HTTPError("connection failed")
        return mock_resp

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_side_effect):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")
            await client.get_enrolled_users(course_id=42)

    mock_sleep.assert_awaited_once_with(2)


# ---------------------------------------------------------------------------
# Task 7.5 [RED] → 7.6 [GREEN]: ambos intentos fallan → MoodleWSError(502)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_both_attempts_fail_raises_moodle_ws_error():
    """
    RED: ambas llamadas levantan HTTPError → MoodleWSError con status 502.
    """
    from app.integrations.moodle_ws import MoodleWSClient, MoodleWSError

    async def _always_fail(*args, **kwargs):
        raise httpx.HTTPError("moodle unavailable")

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_always_fail):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")
            with pytest.raises(MoodleWSError) as exc_info:
                await client.get_enrolled_users(course_id=42)

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_both_attempts_fail_http_status_error():
    """
    Triangulación: raise_for_status levanta HTTPStatusError en ambos intentos.
    """
    from app.integrations.moodle_ws import MoodleWSClient, MoodleWSError

    def _make_resp_error():
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
        return resp

    async def _status_error(*args, **kwargs):
        raise httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_status_error):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = MoodleWSClient(base_url="https://moodle.example.com", token="tok")
            with pytest.raises(MoodleWSError) as exc_info:
                await client.get_enrolled_users(course_id=99)

    assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Task 7.7 [RED] → 7.8 [GREEN]: token no aparece en mensaje de error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_not_in_error_message():
    """
    RED: fallo con token="SECRET_TOKEN" → MoodleWSError.detail no contiene "SECRET_TOKEN".
    """
    from app.integrations.moodle_ws import MoodleWSClient, MoodleWSError

    SECRET_TOKEN = "SECRET_TOKEN_XYZ"

    async def _always_fail(*args, **kwargs):
        raise httpx.HTTPError("failed")

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_always_fail):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = MoodleWSClient(base_url="https://moodle.example.com", token=SECRET_TOKEN)
            with pytest.raises(MoodleWSError) as exc_info:
                await client.get_enrolled_users(course_id=1)

    error = exc_info.value
    assert SECRET_TOKEN not in str(error.detail)
    assert SECRET_TOKEN not in str(error)


@pytest.mark.asyncio
async def test_token_not_in_error_message_status_error():
    """
    Triangulación: HTTPStatusError con token en URL → token no aparece en detail.
    """
    from app.integrations.moodle_ws import MoodleWSClient, MoodleWSError

    SECRET_TOKEN = "VERY_SECRET_MOODLE_TOKEN"

    async def _status_error(*args, **kwargs):
        raise httpx.HTTPStatusError(
            f"Error with token={SECRET_TOKEN}",
            request=MagicMock(),
            response=MagicMock(),
        )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=_status_error):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            client = MoodleWSClient(base_url="https://moodle.example.com", token=SECRET_TOKEN)
            with pytest.raises(MoodleWSError) as exc_info:
                await client.get_enrolled_users(course_id=1)

    assert SECRET_TOKEN not in str(exc_info.value.detail)
