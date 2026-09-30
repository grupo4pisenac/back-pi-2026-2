import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.thingspeak import fetch_feeds, process_feeds

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


def _fetch_or_raise(results: int) -> list[dict]:
    try:
        return fetch_feeds(results)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"O ThingSpeak retornou HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Não foi possível acessar o ThingSpeak")


@router.post("/run")
def run_ingestion(results: int = Query(100, ge=1, le=100), db: Session = Depends(get_db)):
    feeds = _fetch_or_raise(results)
    return process_feeds(db, feeds)