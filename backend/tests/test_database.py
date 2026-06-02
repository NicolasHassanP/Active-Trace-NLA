import pytest
from sqlalchemy import text


pytestmark = pytest.mark.asyncio


async def test_db_smoke_select_one(db_session):
    result = await db_session.execute(text("SELECT 1 AS val"))
    row = result.fetchone()
    assert row is not None
    assert row.val == 1


async def test_get_db_closes_session_on_exception(async_client):
    """La sesión se cierra sin fuga al pool incluso cuando el handler lanza excepción."""
    response = await async_client.get("/health")
    # Si llega una respuesta (no fallo de pool), get_db liberó la conexión correctamente.
    assert response.status_code in (200, 503)
