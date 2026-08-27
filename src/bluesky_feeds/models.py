from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Article:
    """A source-independent article ready for filtering and publishing."""

    id: str
    title: str
    url: str
    published_at: datetime
    source: str
    channel: str | None = None
    hashtag: str | None = None
    description: str | None = None
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Configuration for one news source."""

    type: str
    name: str
    url: str
    channel: str | None = None
    hashtag: str | None = None
    headers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AccountConfig:
    """One Bluesky account and all news sources published by it."""

    key: str
    name: str
    handle_env: str
    app_password_env: str
    state_file: str
    post_label: str | None
    sources: tuple[SourceConfig, ...]
