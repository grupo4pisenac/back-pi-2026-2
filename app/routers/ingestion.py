import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import exigir_permissao
from app.core.database import get_sync_db
from app.services.thingspeak import LIMITE_RESULTADOS, buscar_leituras, processar_leituras

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _buscar_ou_lancar_erro(quantidade: int) -> list[dict]:
    try:
        return buscar_leituras(quantidade)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"O ThingSpeak retornou HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Não foi possível acessar o ThingSpeak")


@router.post("/run", dependencies=[Depends(exigir_permissao("sensors:write"))])
def executar_ingestao(
    results: int = Query(100, ge=1, le=LIMITE_RESULTADOS, description="Quantidade de leituras buscadas no canal"),
    db: Session = Depends(get_sync_db),
):
    """Sincroniza manualmente o canal do ThingSpeak (Apenas Administrador)."""
    leituras = _buscar_ou_lancar_erro(results)
    return processar_leituras(db, leituras)
