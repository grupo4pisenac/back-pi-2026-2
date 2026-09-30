import os

import httpx
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.climate import ClimateDataCreate
from app.models.climate import ClimateData

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


def save_new(db: Session, records: list[ClimateDataCreate]) -> tuple[int, int]:
    if not records:
        return 0, 0

    ids = [record.entry_id for record in records]
    existing = set(
        db.scalars(select(ClimateData.entry_id).where(ClimateData.entry_id.in_(ids)))
    )

    new_rows = [
        ClimateData(
            entry_id=record.entry_id,
            temperature=record.temperature,
            humidity=record.humidity,
            recorded_at=record.recorded_at,
        )
        for record in records
        if record.entry_id not in existing
    ]

    db.add_all(new_rows)
    db.commit()
    return len(new_rows), len(records) - len(new_rows)


def process_feeds(db: Session, feeds: list[dict]) -> dict:
    records = []
    discarded = 0
    for feed in feeds:
        record = parse_feed(feed)
        if record is None:
            discarded += 1
        else:
            records.append(record)

    saved, duplicates = save_new(db, records)
    return {"fetched": len(feeds), "saved": saved, "duplicates": duplicates, "discarded": discarded}