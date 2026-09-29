import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.thingspeak import fetch_feeds, parse_feed

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

@router.get("/preview")
def preview_feeds(results: int = Query(10, ge=1, le=100)):
    return _fetch_or_raise(results)

@router.get("/preview-clean")
def preview_clean_feeds(results: int = Query(10, ge=1, le=100)):
    feeds = _fetch_or_raise(results)

    valid = []
    discarded = 0
    for feed in feeds:
        record = parse_feed(feed)
        if record is None:
            discarded += 1
        else:
            valid.append(record)

    return {"fetched": len(feeds), "valid": valid, "discarded": discarded}