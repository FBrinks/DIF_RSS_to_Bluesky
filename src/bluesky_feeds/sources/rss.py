from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ..models import Article, SourceConfig


DEFAULT_TIMEOUT = 15


class RssSource:
    """Fetch an RSS 2.0 source and normalize entries to Article."""

    def __init__(self, config: SourceConfig, *, timeout: int = DEFAULT_TIMEOUT) -> None:
        if config.type != "rss":
            raise ValueError(f"RssSource cannot handle source type {config.type!r}")
        self.config = config
        self.timeout = timeout

    def fetch(self) -> list[Article]:
        request = Request(
            self.config.url,
            headers={
                "User-Agent": "BlueskyFeeds/1.0",
                "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8",
            },
        )
        with urlopen(request, timeout=self.timeout) as response:
            document = response.read()
        return parse_rss(document, self.config)


def parse_rss(document: bytes | str, config: SourceConfig) -> list[Article]:
    """Parse RSS XML without performing network calls."""

    root = ElementTree.fromstring(document.lstrip())
    articles: list[Article] = []

    for item in root.findall("./channel/item"):
        title = _text(item, "title")
        url = _text(item, "link")
        if not title or not url:
            continue

        guid = _text(item, "guid") or url
        articles.append(
            Article(
                id=guid,
                title=title,
                url=url,
                published_at=_published_at(_text(item, "pubDate")),
                source=config.name,
                channel=config.channel,
                hashtag=config.hashtag,
                description=_text(item, "description"),
            )
        )

    return articles


def _text(element: ElementTree.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def _published_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)

    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
