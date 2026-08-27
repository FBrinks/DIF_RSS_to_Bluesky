from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Article


class PublishedState:
    """Durable record of successfully handled article URLs."""

    def __init__(self, path: str | Path, published: dict[str, dict[str, Any]] | None = None) -> None:
        self.path = Path(path)
        self.published = published or {}

    @classmethod
    def load(cls, path: str | Path) -> PublishedState:
        state_path = Path(path)
        if not state_path.exists():
            return cls(state_path)

        with state_path.open(encoding="utf-8") as state_file:
            data = json.load(state_file)

        # Backwards compatibility with the current list-of-URLs state files.
        if isinstance(data, list):
            return cls(
                state_path,
                {str(url): {"migrated": True} for url in data if isinstance(url, str)},
            )
        if not isinstance(data, dict) or not isinstance(data.get("published"), dict):
            raise ValueError(f"Invalid state format in {state_path}")
        return cls(state_path, data["published"])

    def contains(self, article: Article) -> bool:
        return article.url in self.published

    def mark(self, article: Article, *, status: str) -> None:
        self.published[article.url] = {
            "article_id": article.id,
            "source": article.source,
            "channel": article.channel,
            "status": status,
            "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {"version": 1, "published": self.published}
        with temporary_path.open("w", encoding="utf-8") as state_file:
            json.dump(payload, state_file, ensure_ascii=False, indent=2, sort_keys=True)
            state_file.write("\n")
        temporary_path.replace(self.path)
