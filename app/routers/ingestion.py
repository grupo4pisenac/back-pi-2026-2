import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.thingspeak import fetch_feeds

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.get("/preview")
def preview_feeds(results: int = Query(10, ge=1, le=100)):
    """Temporary endpoint: shows raw ThingSpeak data without saving anything."""
    try:
        return fetch_feeds(results)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"ThingSpeak returned HTTP {exc.response.status_code}")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach ThingSpeak")