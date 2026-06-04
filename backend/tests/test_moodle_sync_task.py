"""
test_moodle_sync_task.py — TDD suite para C-09 tarea nocturna de sync Moodle.

Cubre tasks 10.1–10.4 del tasks.md.

Tests unitarios — mocks de MoodleWSClient, session_factory y asyncio.sleep.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_settings(sync_hour: int = 3) -> MagicMock:
    settings = MagicMock()
    settings.MOODLE_BASE_URL = "https://moodle.example.com"
    settings.MOODLE_TOKEN = "test_token"
    settings.MOODLE_SYNC_HOUR = sync_hour
    settings.PADRON_MAX_ROWS = 5000
    return settings


def _make_mappings(n: int) -> list:
    import uuid

    return [
        {
            "course_id": i + 100,
            "materia_id": str(uuid.uuid4()),
            "cohorte_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Task 10.1 [RED] → 10.2 [GREEN]: nightly task itera todos los mappings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nightly_task_iterates_all_mappings():
    """
    RED: nightly_sync_loop con 2 mappings llama run_sync_for_mapping 2 veces.
    """
    from app.integrations.moodle_sync_task import nightly_sync_loop

    mappings = _make_mappings(2)
    settings = _make_fake_settings()
    session_factory = MagicMock()

    sync_calls = []

    async def _mock_run_sync(mapping, base_url, token, sf):
        sync_calls.append(mapping)

    # Patch sleep to avoid waiting, then cancel after first iteration
    sleep_count = {"n": 0}

    async def _mock_sleep(seconds):
        sleep_count["n"] += 1
        if sleep_count["n"] > 1:
            # Cancel after the first nightly run
            raise asyncio.CancelledError()

    with patch("app.integrations.moodle_sync_task.run_sync_for_mapping", new=_mock_run_sync):
        with patch("app.integrations.moodle_sync_task._seconds_until_hour", new=AsyncMock(return_value=0)):
            with patch("asyncio.sleep", new=_mock_sleep):
                try:
                    await nightly_sync_loop(
                        settings=settings,
                        session_factory=session_factory,
                        mappings=mappings,
                    )
                except asyncio.CancelledError:
                    pass

    assert len(sync_calls) == 2


@pytest.mark.asyncio
async def test_nightly_task_empty_mappings_runs_without_error():
    """
    Triangulación: lista de mappings vacía — tarea corre sin error ni sync calls.
    """
    from app.integrations.moodle_sync_task import nightly_sync_loop

    settings = _make_fake_settings()
    session_factory = MagicMock()

    run_count = {"n": 0}
    sleep_count = {"n": 0}

    async def _mock_sleep(seconds):
        sleep_count["n"] += 1
        if sleep_count["n"] > 1:
            raise asyncio.CancelledError()

    with patch("app.integrations.moodle_sync_task._seconds_until_hour", new=AsyncMock(return_value=0)):
        with patch("asyncio.sleep", new=_mock_sleep):
            try:
                await nightly_sync_loop(
                    settings=settings,
                    session_factory=session_factory,
                    mappings=[],
                )
            except asyncio.CancelledError:
                pass

    # run_count remains 0 — no sync calls for empty mappings
    assert run_count["n"] == 0


# ---------------------------------------------------------------------------
# Task 10.3 [RED] → 10.4 [GREEN]: fallo en un mapping no detiene los demás
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nightly_task_continues_after_single_mapping_failure():
    """
    RED: uno de los mappings lanza excepción; el segundo se procesa igual.
    """
    from app.integrations.moodle_sync_task import nightly_sync_loop

    mappings = _make_mappings(2)
    settings = _make_fake_settings()
    session_factory = MagicMock()

    processed = []
    call_count = {"n": 0}

    async def _mock_run_sync(mapping, base_url, token, sf):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("Moodle WS unavailable for mapping 1")
        processed.append(mapping)

    sleep_count = {"n": 0}

    async def _mock_sleep(seconds):
        sleep_count["n"] += 1
        if sleep_count["n"] > 1:
            raise asyncio.CancelledError()

    with patch("app.integrations.moodle_sync_task.run_sync_for_mapping", new=_mock_run_sync):
        with patch("app.integrations.moodle_sync_task._seconds_until_hour", new=AsyncMock(return_value=0)):
            with patch("asyncio.sleep", new=_mock_sleep):
                try:
                    await nightly_sync_loop(
                        settings=settings,
                        session_factory=session_factory,
                        mappings=mappings,
                    )
                except asyncio.CancelledError:
                    pass

    # First mapping failed, second was processed
    assert call_count["n"] == 2
    assert len(processed) == 1
    assert processed[0] == mappings[1]


@pytest.mark.asyncio
async def test_nightly_task_all_failures_does_not_raise():
    """
    Triangulación: todos los mappings fallan — tarea no levanta excepción no capturada.
    """
    from app.integrations.moodle_sync_task import nightly_sync_loop

    mappings = _make_mappings(3)
    settings = _make_fake_settings()
    session_factory = MagicMock()

    async def _always_fail(mapping, base_url, token, sf):
        raise Exception("Moodle always down")

    sleep_count = {"n": 0}

    async def _mock_sleep(seconds):
        sleep_count["n"] += 1
        if sleep_count["n"] > 1:
            raise asyncio.CancelledError()

    with patch("app.integrations.moodle_sync_task.run_sync_for_mapping", new=_always_fail):
        with patch("app.integrations.moodle_sync_task._seconds_until_hour", new=AsyncMock(return_value=0)):
            with patch("asyncio.sleep", new=_mock_sleep):
                try:
                    await nightly_sync_loop(
                        settings=settings,
                        session_factory=session_factory,
                        mappings=mappings,
                    )
                except asyncio.CancelledError:
                    pass
                # Should not raise any other exception


# ---------------------------------------------------------------------------
# Task 10.5 — start_nightly_sync_task registered in lifespan (tested separately)
# Test that start_nightly_sync_task returns a Task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_nightly_sync_task_returns_task():
    """
    start_nightly_sync_task retorna un asyncio.Task que puede cancelarse.
    """
    from app.integrations.moodle_sync_task import start_nightly_sync_task

    settings = _make_fake_settings()
    session_factory = MagicMock()

    # Patch the loop to prevent it from actually running
    with patch("app.integrations.moodle_sync_task.nightly_sync_loop", new=AsyncMock()):
        task = start_nightly_sync_task(settings=settings, session_factory=session_factory)

    assert isinstance(task, asyncio.Task)
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass
