import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_sync_db
from app.services.thingspeak import buscar_leituras, processar_leituras

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


def _buscar_ou_lancar_erro(quantidade: int) -> list[dict]:
    try:
        return buscar_leituras(quantidade)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"O ThingSpeak retornou HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Não foi possível acessar o ThingSpeak")


@router.post("/run")
def executar_ingestao(results: int = Query(100, ge=1, le=100), db: Session = Depends(get_sync_db)):
    leituras = _buscar_ou_lancar_erro(results)
    return processar_leituras(db, leituras)