"""Entrypoint del worker de comunicaciones — placeholder.

Tecnología real de la cola (asyncio / ARQ / Celery) queda como ADR-003,
a decidir al implementar C-12 (comunicaciones-cola-worker).
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def run() -> None:
    logger.info("Worker started (no-op placeholder — ADR-003 pending)")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run())
