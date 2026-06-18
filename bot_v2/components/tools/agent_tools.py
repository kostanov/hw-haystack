"""Инструменты Haystack-агента bot_v2."""

from __future__ import annotations

import base64
import json
import os
import random
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from ddgs import DDGS
from haystack.tools import tool
from openai import OpenAI

from bot_v2.bot.config import Settings
from bot_v2.components.media.storage import save_media_file

MAX_CAT_PHOTO_DOWNLOAD_ATTEMPTS = 5
REQUEST_ID_ENV = "BOT_V2_REQUEST_ID"
CAT_IMAGE_QUERIES = [
    "cute cat photo",
    "cat breed portrait",
    "random cat image",
]
USER_AGENT = "Mozilla/5.0 (compatible; hw-haystack-bot-v2/1.0)"
METNO_USER_AGENT = "hw-haystack-bot-v2/1.0 (zerocode homework)"
_pending_photos: dict[str, CatPhoto] = {}
_photo_lock = threading.Lock()
_settings: Settings | None = None


@dataclass(frozen=True)
class CatPhoto:
    path: Path


def configure_tools(settings: Settings) -> None:
    global _settings
    _settings = settings


def begin_agent_request() -> str:
    request_id = uuid.uuid4().hex
    os.environ[REQUEST_ID_ENV] = request_id
    return request_id


def end_agent_request(request_id: str) -> None:
    os.environ.pop(REQUEST_ID_ENV, None)
    with _photo_lock:
        _pending_photos.pop(request_id, None)


def _store_pending_cat_photo(photo: CatPhoto) -> None:
    request_id = os.getenv(REQUEST_ID_ENV)
    if not request_id:
        return
    with _photo_lock:
        _pending_photos[request_id] = photo


def consume_pending_cat_photo() -> CatPhoto | None:
    request_id = os.getenv(REQUEST_ID_ENV)
    if not request_id:
        return None
    with _photo_lock:
        return _pending_photos.pop(request_id, None)


def _openai_client() -> OpenAI:
    if _settings is None:
        raise RuntimeError("configure_tools() не вызван")
    return OpenAI(
        api_key=_settings.openai_api_key,
        base_url=_settings.openai_base_url,
    )


@tool
def get_random_cat_fact() -> str:
    """Получить случайный факт о кошках с сайта catfact.ninja."""
    with httpx.Client(timeout=15.0) as client:
        response = client.get("https://catfact.ninja/fact")
        response.raise_for_status()
        data = response.json()
    return data.get("fact", "Факт не найден.")


@tool
def describe_random_cat_breed() -> str:
    """Найти случайное фото кошки через DuckDuckGo и описать породу с краткой историей."""
    downloaded = _download_cat_image_with_retries()
    if downloaded is None:
        return "Не удалось загрузить фото кошки после нескольких попыток."

    image_bytes, mime_type = downloaded
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"

    client = _openai_client()
    completion = client.chat.completions.create(
        model=_settings.openai_chat_model if _settings else "gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Определи породу кошки на фото. "
                            "Ответь на русском: название породы и краткая история её происхождения."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=500,
    )
    description = completion.choices[0].message.content or "Не удалось описать породу."
    extension = "png" if mime_type == "image/png" else "jpg"
    photos_dir = _settings.cat_photos_dir if _settings else Path("./data_v2/cat_photos")
    file_path = save_media_file(image_bytes, photos_dir, extension)
    _store_pending_cat_photo(CatPhoto(path=file_path))
    return description


def _collect_cat_image_urls() -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    with DDGS() as ddgs:
        for query in CAT_IMAGE_QUERIES:
            for item in ddgs.images(query, max_results=10):
                url = item.get("image") or item.get("url")
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)

    random.shuffle(urls)
    return urls


def _download_cat_image(
    client: httpx.Client,
    image_url: str,
) -> tuple[bytes, str] | None:
    try:
        response = client.get(image_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    if content_type and not content_type.startswith("image/"):
        return None

    image_bytes = response.content
    if len(image_bytes) < 1024:
        return None

    mime_type = content_type if content_type.startswith("image/") else "image/jpeg"
    return image_bytes, mime_type


def _download_cat_image_with_retries(
    max_attempts: int = MAX_CAT_PHOTO_DOWNLOAD_ATTEMPTS,
) -> tuple[bytes, str] | None:
    candidates = _collect_cat_image_urls()
    if not candidates:
        return None

    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(
        timeout=15.0,
        follow_redirects=True,
        headers=headers,
    ) as client:
        for image_url in candidates[:max_attempts]:
            downloaded = _download_cat_image(client, image_url)
            if downloaded is not None:
                return downloaded
    return None


@tool
def get_weather(city: str) -> str:
    """Получить текущую погоду для указанного города."""
    with httpx.Client(timeout=20.0) as client:
        geo_response = client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ru", "format": "json"},
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()

    results = geo_data.get("results") or []
    if not results:
        return f"Город «{city}» не найден."

    place = results[0]
    latitude = place["latitude"]
    longitude = place["longitude"]
    location_name = place.get("name", city)
    country = place.get("country", "")

    with httpx.Client(
        timeout=20.0,
        headers={"User-Agent": METNO_USER_AGENT},
    ) as client:
        weather_response = client.get(
            "https://api.met.no/weatherapi/locationforecast/2.0/compact",
            params={"lat": latitude, "lon": longitude},
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()

    timeseries = weather_data["properties"]["timeseries"]
    if not timeseries:
        return f"Не удалось получить погоду для «{location_name}»."

    point = timeseries[0]
    instant = point["data"]["instant"]["details"]
    conditions = ""
    for period in ("next_1_hours", "next_6_hours", "next_12_hours"):
        block = point["data"].get(period)
        if block and "summary" in block:
            conditions = block["summary"].get("symbol_code", "")
            break

    payload = {
        "city": location_name,
        "country": country,
        "temperature_c": instant.get("air_temperature"),
        "humidity_percent": instant.get("relative_humidity"),
        "wind_speed_ms": instant.get("wind_speed"),
        "wind_from_direction_deg": instant.get("wind_from_direction"),
        "pressure_hpa": instant.get("air_pressure_at_sea_level"),
        "conditions": conditions,
        "observation_time": point.get("time"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def get_agent_tools() -> list:
    return [get_random_cat_fact, describe_random_cat_breed, get_weather]
