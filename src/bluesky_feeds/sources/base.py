from __future__ import annotations

from typing import Protocol

from ..models import Article


class NewsSource(Protocol):
    def fetch(self) -> list[Article]:
        """Return currently available articles from this source."""

