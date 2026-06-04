"""
moodle_sync_task.py — Tarea nocturna de sincronización automática desde Moodle.

C-09 Design Decision D7:
    - asyncio.create_task en el lifespan de FastAPI.
    - Solo se lanza cuando MOODLE_BASE_URL está configurado.
    - Cada mapping = {"course_id": int, "materia_id": str, "cohorte_id": str, "tenant_id": str}.
    - Corre a MOODLE_SYNC_HOUR UTC (defecto 3am).
    - Error en un mapping → log y continúa con el resto.

NOTAS:
    En C-09 los mappings vienen de configuración (settings.MOODLE_COURSE_MAPPINGS, una
    lista de dicts). En producción, esto se lee de la tabla tenant_moodle_config
    (change posterior). Por ahora, la tarea acepta el parámetro externamente.

snake_case; ≤500 LOC.
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def _seconds_until_hour(target_hour: int) -> float:
    """
    Calcula los segundos hasta la próxima ocurrencia de target_hour UTC.
    """
    import datetime

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


async def run_sync_for_mapping(
    mapping: dict[str, Any],
    base_url: str,
    token: str,
    session_factory,
) -> None:
    """
    Ejecuta la sincronización de un único mapping (course → materia×cohorte).

    Raises nada — errores deben capturarse en el loop principal.
    """
    import uuid

    from app.integrations.moodle_ws import MoodleWSClient
    from app.repositories.padron_repository import PadronRepository
    from app.repositories.audit_repository import AuditRepository
    from app.services.padron_service import PadronService
    from app.core.dependencies import CurrentUser

    course_id = int(mapping["course_id"])
    materia_id = uuid.UUID(str(mapping["materia_id"]))
    cohorte_id = uuid.UUID(str(mapping["cohorte_id"]))
    tenant_id = uuid.UUID(str(mapping["tenant_id"]))

    # Sistema como actor (nightly sync no tiene usuario real)
    system_user = CurrentUser(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        tenant_id=tenant_id,
        roles=["ADMIN"],
    )

    client = MoodleWSClient(base_url=base_url, token=token)

    async with session_factory() as session:
        repo = PadronRepository(session=session, tenant_id=tenant_id)
        audit_repo = AuditRepository(session=session, tenant_id=tenant_id)
        svc = PadronService(repo=repo, db=session, audit_repo=audit_repo)

        await svc.sync_from_moodle(
            course_id=course_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            current_user=system_user,
            moodle_client=client,
        )


async def nightly_sync_loop(
    settings,
    session_factory,
    mappings: list[dict[str, Any]] | None = None,
) -> None:
    """
    Tarea asyncio que espera hasta MOODLE_SYNC_HOUR UTC y ejecuta la sync.

    Itera indefinidamente (un ciclo por día). Errores en mappings individuales
    se logean y no detienen el procesamiento del resto (spec: nightly task failure
    for one mapping does not stop others).

    Args:
        settings: Settings de la aplicación.
        session_factory: factory de sesiones DB async.
        mappings: lista de dicts con course_id/materia_id/cohorte_id/tenant_id.
                  Si None → vacía (nightly task no hace nada sin mappings).
    """
    if mappings is None:
        mappings = []

    base_url = settings.MOODLE_BASE_URL
    token = settings.MOODLE_TOKEN

    while True:
        try:
            wait_secs = await _seconds_until_hour(settings.MOODLE_SYNC_HOUR)
            logger.info("Nightly Moodle sync scheduled in %.0f seconds.", wait_secs)
            await asyncio.sleep(wait_secs)
        except asyncio.CancelledError:
            logger.info("Nightly Moodle sync task cancelled.")
            return

        logger.info("Starting nightly Moodle sync for %d mappings.", len(mappings))

        for mapping in mappings:
            try:
                await run_sync_for_mapping(mapping, base_url, token, session_factory)
                logger.info(
                    "Nightly sync OK: course_id=%s materia=%s cohorte=%s",
                    mapping.get("course_id"),
                    mapping.get("materia_id"),
                    mapping.get("cohorte_id"),
                )
            except Exception as exc:
                logger.error(
                    "Nightly sync FAILED for mapping %s: %s",
                    mapping,
                    exc,
                    exc_info=True,
                )
                # Continue with remaining mappings (spec: nightly task continues after failure)


def start_nightly_sync_task(settings, session_factory) -> asyncio.Task:
    """
    Lanza la tarea nocturna de sync como asyncio.Task.

    Solo llamar desde el lifespan de FastAPI cuando MOODLE_BASE_URL está configurado.

    Returns the Task object (for cancellation on shutdown).
    """
    task = asyncio.create_task(
        nightly_sync_loop(settings=settings, session_factory=session_factory),
        name="moodle_nightly_sync",
    )
    logger.info("Moodle nightly sync task started (MOODLE_SYNC_HOUR=%s UTC).", settings.MOODLE_SYNC_HOUR)
    return task
