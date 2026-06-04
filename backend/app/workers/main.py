"""Entrypoint del worker de comunicaciones — C-12 comunicaciones-cola-worker.

Reemplaza el placeholder de ADR-003 con el worker de polling real.
La tecnología de cola elegida (OQ-1) es: polling sobre la tabla `comunicacion`.

Para producción: inyectar un EmailSender real (SMTP/SES) vía configuración.
Para desarrollo y CI: usa TestSender (no envía emails reales).
"""

import asyncio
import logging

from app.workers.comunicacion_worker import run

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger.info("Iniciando worker de comunicaciones...")
    asyncio.run(run())
