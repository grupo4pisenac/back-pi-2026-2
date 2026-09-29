import os

import httpx
from dotenv import load_dotenv

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