from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import Article


MAX_POST_LENGTH = 300


@dataclass(frozen=True, slots=True)
class PostContent:
    text: str
    facets: tuple[dict[str, Any], ...]


def build_post_content(
    article: Article,
    *,
    label: str | None = None,
    max_length: int = MAX_POST_LENGTH,
) -> PostContent:
    """Build post text and UTF-8 byte facets while preserving link and hashtag."""

    parts = [part for part in (label, f"#{article.hashtag}" if article.hashtag else None) if part]
    suffix = "\n\n".join([*parts, article.url])
    title_budget = max_length - len(suffix) - 2
    if title_budget < 1:
        raise ValueError("Post metadata and URL leave no room for the article title")

    title = _truncate(article.title.strip(), title_budget)
    if not title:
        raise ValueError("Article title cannot be empty")

    text = f"{title}\n\n{suffix}"
    facets: list[dict[str, Any]] = []

    if article.hashtag:
        hashtag_text = f"#{article.hashtag}"
        facets.append(
            _facet(
                text,
                hashtag_text,
                {"$type": "app.bsky.richtext.facet#tag", "tag": article.hashtag},
            )
        )

    facets.append(
        _facet(
            text,
            article.url,
            {"$type": "app.bsky.richtext.facet#link", "uri": article.url},
        )
    )

    return PostContent(text=text, facets=tuple(facets))


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return "…"[:limit]
    return text[: limit - 1].rstrip() + "…"


def _facet(text: str, token: str, feature: dict[str, str]) -> dict[str, Any]:
    character_start = text.index(token)
    character_end = character_start + len(token)
    byte_start = len(text[:character_start].encode("utf-8"))
    byte_end = len(text[:character_end].encode("utf-8"))

    return {
        "$type": "app.bsky.richtext.facet",
        "index": {"byteStart": byte_start, "byteEnd": byte_end},
        "features": [feature],
    }
