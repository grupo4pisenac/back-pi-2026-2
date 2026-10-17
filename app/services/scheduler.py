import asyncio
import logging
import httpx

from app.core.database import SessionLocal
from app.services.thingspeak import buscar_leituras, processar_leituras

logger = logging.getLogger(__name__)


def _executar_ciclo() -> dict:
    leituras = buscar_leituras(100)
    with SessionLocal() as db:
        return processar_leituras(db, leituras)


async def loop_ingestao(intervalo_segundos: int) -> None:
    while True:
        try:
            resultado = await asyncio.to_thread(_executar_ciclo)
            logger.info("Ingestão automática concluída: %s", resultado)
        except httpx.HTTPStatusError as exc:
            logger.error("O ThingSpeak retornou HTTP %s", exc.response.status_code)
        except httpx.HTTPError as exc:
            logger.error("Falha ao acessar o ThingSpeak: %s", type(exc).__name__)
        except Exception:
            logger.exception("Erro inesperado na ingestão automática")
        await asyncio.sleep(intervalo_segundos)


# Aliases para compatibilidade entre módulos
_run_cycle = _executar_ciclo
ingestion_loop = loop_ingestao