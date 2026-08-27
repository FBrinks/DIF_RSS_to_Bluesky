"""News source adapters."""

from .base import NewsSource
from .rss import RssSource, parse_rss

__all__ = ["NewsSource", "RssSource", "parse_rss"]
