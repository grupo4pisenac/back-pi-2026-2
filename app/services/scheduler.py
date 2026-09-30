import asyncio
import logging

import httpx

from app.core.database import SessionLocal
from app.services.thingspeak import fetch_feeds, process_feeds

logger = logging.getLogger(__name__)


def _run_cycle() -> dict:
    feeds = fetch_feeds(100)
    with SessionLocal() as db:
        return process_feeds(db, feeds)


async def ingestion_loop(interval_seconds: int) -> None:
    while True:
        try:
            result = await asyncio.to_thread(_run_cycle)
            logger.info("Ingestão automática concluída: %s", result)
        except httpx.HTTPStatusError as exc:
            logger.error("O ThingSpeak retornou HTTP %s", exc.response.status_code)
        except httpx.HTTPError as exc:
            logger.error("Falha ao acessar o ThingSpeak: %s", type(exc).__name__)
        except Exception:
            logger.exception("Erro inesperado na ingestão automática")
        await asyncio.sleep(interval_seconds)