from __future__ import annotations

from datetime import datetime, timezone

from ..models import Article, SourceConfig
from .json_http import DEFAULT_TIMEOUT, fetch_json


ARTICLE_BASE_URL = "https://www.difhockey.se/article"


class DifHockeySource:
    def __init__(self, config: SourceConfig, *, timeout: int = DEFAULT_TIMEOUT) -> None:
        if config.type != "dif_hockey":
            raise ValueError(f"DifHockeySource cannot handle source type {config.type!r}")
        self.config = config
        self.timeout = timeout

    def fetch(self) -> list[Article]:
        return parse_dif_hockey(fetch_json(self.config.url, timeout=self.timeout), self.config)


def parse_dif_hockey(payload: dict, config: SourceConfig) -> list[Article]:
    items = payload.get("data", {}).get("articleItems", [])
    if not isinstance(items, list):
        raise ValueError("DIF Hockey response is missing data.articleItems")

    articles: list[Article] = []
    for item in items:
        article_id = _text(item, "id")
        title = _text(item, "header")
        if not article_id or not title:
            continue

        articles.append(
            Article(
                id=article_id,
                title=title,
                url=f"{ARTICLE_BASE_URL}/{article_id}/view",
                published_at=_iso_datetime(_text(item, "publishedAt")),
                source=config.name,
                channel=config.channel,
                hashtag=config.hashtag,
                description=_text(item, "intro") or _text(item, "introRawText"),
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
