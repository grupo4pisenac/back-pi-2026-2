import asyncio
import logging
import httpx

from app.core.database import SessionLocal
from app.services.thingspeak import LIMITE_RESULTADOS, buscar_leituras, processar_leituras

logger = logging.getLogger(__name__)

# Ciclos seguintes só precisam das leituras novas desde a última sincronização
RESULTADOS_POR_CICLO = 100


def _executar_ciclo(quantidade: int = RESULTADOS_POR_CICLO) -> dict:
    leituras = buscar_leituras(quantidade)
    with SessionLocal() as db:
        return processar_leituras(db, leituras)


async def loop_ingestao(intervalo_segundos: int) -> None:
    # 1º ciclo importa o histórico disponível no canal (limite do ThingSpeak); duplicados são ignorados
    quantidade = LIMITE_RESULTADOS
    while True:
        try:
            resultado = await asyncio.to_thread(_executar_ciclo, quantidade)
            quantidade = RESULTADOS_POR_CICLO
            if resultado["saved"]:
                logger.info("Ingestão automática concluída: %s", resultado)
            else:
                logger.debug("Ingestão automática sem leituras novas: %s", resultado)
        except RuntimeError as exc:
            logger.error("Ingestão automática desativada nesta rodada: %s", exc)
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
