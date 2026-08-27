from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin

from ..models import Article, SourceConfig
from .json_http import DEFAULT_TIMEOUT, fetch_json


SITE_URL = "https://www.dif.se"


class DifFootballSource:
    def __init__(self, config: SourceConfig, *, timeout: int = DEFAULT_TIMEOUT) -> None:
        if config.type != "dif_football":
            raise ValueError(f"DifFootballSource cannot handle source type {config.type!r}")
        self.config = config
        self.timeout = timeout

    def fetch(self) -> list[Article]:
        return parse_dif_football(fetch_json(self.config.url, timeout=self.timeout), self.config)


def parse_dif_football(payload: dict, config: SourceConfig) -> list[Article]:
    items = payload.get("pages", [])
    if not isinstance(items, list):
        raise ValueError("DIF Fotboll response is missing pages")

    articles: list[Article] = []
    for item in items:
        article_id = _text(item, "key")
        path = _text(item, "url")
        title = _text(item, "heading") or _text(item, "name")
        published = _text(item, "date") or _text(item, "publishedOnDifPlay")
        if not article_id or not path or not title:
            continue

        image = item.get("image")
        image_url = image.get("src") if isinstance(image, dict) else None
        image_url = image_url or _text(item, "thumbnailUrl")

        articles.append(
            Article(
                id=article_id,
                title=title,
                url=urljoin(SITE_URL, path),
                published_at=_iso_datetime(published),
                source=config.name,
                channel=config.channel,
                hashtag=config.hashtag,
                description=_text(item, "preamble") or _text(item, "description"),
                image_url=image_url,
            )
        )

    return articles


def _text(data: dict, key: str) -> str | None:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _iso_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
