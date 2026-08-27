"""News source adapters."""

from .base import NewsSource
from .dif_football import DifFootballSource, parse_dif_football
from .dif_hockey import DifHockeySource, parse_dif_hockey
from .rss import RssSource, parse_rss

__all__ = [
    "DifFootballSource",
    "DifHockeySource",
    "NewsSource",
    "RssSource",
    "parse_dif_football",
    "parse_dif_hockey",
    "parse_rss",
]
