import os

import httpx
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional

from app.schemas.climate import ClimateDataCreate

load_dotenv()

BASE_URL = "https://api.thingspeak.com"


def fetch_feeds(results: int = 10) -> list[dict]:
    """Fetches the latest readings from the ThingSpeak channel."""
    channel_id = os.getenv("THINGSPEAK_CHANNEL_ID")
    read_key = os.getenv("THINGSPEAK_READ_KEY")
    if not channel_id or not read_key:
        raise RuntimeError("THINGSPEAK_CHANNEL_ID and THINGSPEAK_READ_KEY must be set in .env")

    response = httpx.get(
        f"{BASE_URL}/channels/{channel_id}/feeds.json",
        params={"api_key": read_key, "results": results},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json().get("feeds", [])


TEMPERATURE_RANGE = (-40.0, 100.0)
HUMIDITY_RANGE = (0.0, 100.0)


def parse_feed(feed: dict) -> Optional[ClimateDataCreate]:
    try:
        entry_id = int(feed.get("entry_id"))
        temperature = float(feed.get("field1"))
        humidity = float(feed.get("field2"))
        recorded_at = datetime.fromisoformat(feed.get("created_at").replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        return None

    if not (TEMPERATURE_RANGE[0] <= temperature <= TEMPERATURE_RANGE[1]):
        return None
    if not (HUMIDITY_RANGE[0] <= humidity <= HUMIDITY_RANGE[1]):
        return None

    return ClimateDataCreate(
        entry_id=entry_id,
        temperature=temperature,
        humidity=humidity,
        recorded_at=recorded_at,
    )