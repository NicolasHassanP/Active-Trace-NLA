"""
comunicacion_worker.py — Worker de polling de comunicaciones salientes.

C-12 Design Decisions:
    D1 — OQ-1: polling sobre la tabla `comunicacion` (sin broker/Redis/Celery).
    D2 — Transición atómica Pendiente → Enviando con UPDATE ... WHERE estado='Pendiente'.
    D3 — Solo procesa mensajes con aprobado_por IS NOT NULL (habilitados).
    D4 — OQ-5: Error es TERMINAL — no re-intenta mensajes en estado Error.
    D5 — Transición: Pendiente → Enviando → Enviado (éxito) | Error (fallo).
    D6 — Protección de concurrencia: claim_for_worker() usa UPDATE atómico.

snake_case; ≤500 LOC.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comunicacion import ComunicacionEstado as ModelEstado
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.workers.email_sender import EmailSender

logger = logging.getLogger(__name__)


class ComunicacionWorker:
    """
    Worker de despacho de comunicaciones por polling de la tabla.

    Estrategia:
        1. list_pendientes_habilitados() → mensajes elegibles (Pendiente + aprobado_por IS NOT NULL).
        2. Por cada elegible: claim_for_worker() → transición atómica a Enviando.
        3. Si claim exitoso: send() → Enviado | Error.

    OQ-5: Error es TERMINAL. El worker nunca re-procesa ni reintenta un mensaje en Error.
    OQ-3: depende del EmailSender Protocol — sin SMTP real.
    """

    def __init__(self, sender: EmailSender, session: AsyncSession) -> None:
        self._sender = sender
        self._session = session

    # -----------------------------------------------------------------------
    # procesar_ciclo — un ciclo de polling para un tenant
    # -----------------------------------------------------------------------

    async def procesar_ciclo(self, tenant_id: uuid.UUID) -> int:
        """
        Ejecuta un ciclo de despacho para el tenant dado.

        Toma todos los mensajes Pendiente habilitados (aprobado_por IS NOT NULL),
        intenta enviarlos y actualiza su estado.

        Returns:
            Número de mensajes procesados en este ciclo.
        """
        repo = ComunicacionRepository(session=self._session, tenant_id=tenant_id)
        pendientes = await repo.list_pendientes_habilitados()

        procesados = 0
        for com in pendientes:
            # Transición atómica Pendiente → Enviando (protección de concurrencia)
            claimed = await repo.claim_for_worker(com.id)
            if claimed is None:
                # Otro worker ya tomó este mensaje — skip
                continue

            # Intentar envío
            try:
                await self._sender.send(
                    destinatario=claimed.destinatario,
                    asunto=claimed.asunto,
                    cuerpo=claimed.cuerpo,
                )
                # Envío exitoso → Enviado
                await repo.actualizar_estado(
                    comunicacion=claimed,
                    nuevo_estado=ModelEstado.Enviado,
                    enviado_at=datetime.now(tz=timezone.utc),
                )
                logger.info(
                    "Comunicacion %s enviada exitosamente (tenant=%s)",
                    claimed.id,
                    tenant_id,
                )
                procesados += 1

            except Exception as exc:
                # Fallo → Error (TERMINAL, sin reintento — OQ-5)
                error_detalle = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Comunicacion %s falló al enviar (tenant=%s): %s",
                    claimed.id,
                    tenant_id,
                    error_detalle,
                )
                await repo.actualizar_estado(
                    comunicacion=claimed,
                    nuevo_estado=ModelEstado.Error,
                    error_detalle=error_detalle,
                )
                procesados += 1

        return procesados


# ---------------------------------------------------------------------------
# run — entrypoint del worker (reemplaza el placeholder)
# ---------------------------------------------------------------------------

async def run(
    sender: Optional[EmailSender] = None,
    poll_interval_seconds: int = 30,
) -> None:
    """
    Entrypoint del worker de comunicaciones.

    Hace polling de la tabla comunicacion cada `poll_interval_seconds` segundos.
    En producción, el EmailSender real (SMTP/SES) se inyecta desde la configuración.
    Para testing local y CI, usa TestSender.

    Args:
        sender: implementación de EmailSender. Si None, usa TestSender.
        poll_interval_seconds: intervalo entre ciclos de polling.
    """
    from app.core.config import Settings
    from app.core.database import build_engine, build_session_factory

    if sender is None:
        from app.workers.email_sender import TestSender
        sender = TestSender()
        logger.warning(
            "ComunicacionWorker usando TestSender — no se enviarán emails reales. "
            "Configure un EmailSender real para producción."
        )

    settings = Settings()
    engine = build_engine(settings.DATABASE_URL)
    session_factory = build_session_factory(engine)

    logger.info("ComunicacionWorker iniciado (poll_interval=%ds)", poll_interval_seconds)

    try:
        while True:
            async with session_factory() as session:
                worker = ComunicacionWorker(sender=sender, session=session)

                # Obtener todos los tenants activos
                from sqlalchemy import select
                from app.models.tenant import Tenant, TenantEstado

                result = await session.execute(
                    select(Tenant).where(
                        Tenant.estado == TenantEstado.ACTIVO,
                        Tenant.deleted_at.is_(None),
                    )
                )
                tenants = list(result.scalars().all())

                for tenant in tenants:
                    try:
                        procesados = await worker.procesar_ciclo(tenant_id=tenant.id)
                        if procesados > 0:
                            logger.info(
                                "Tenant %s: %d mensajes procesados",
                                tenant.id,
                                procesados,
                            )
                    except Exception as exc:
                        logger.error(
                            "Error en ciclo de worker para tenant %s: %s",
                            tenant.id,
                            exc,
                        )

            await asyncio.sleep(poll_interval_seconds)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
