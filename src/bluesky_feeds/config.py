from __future__ import annotations

import re
import tomllib
from pathlib import Path

from .models import AccountConfig, SourceConfig


HASHTAG_PATTERN = re.compile(r"^[^#\s-]+$", re.UNICODE)


def load_account_config(path: str | Path) -> AccountConfig:
    """Load and validate one account configuration from TOML."""

    config_path = Path(path)
    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    account = data["account"]
    sources = tuple(_load_source(source) for source in data.get("sources", []))
    if not sources:
        raise ValueError(f"No sources configured in {config_path}")

    return AccountConfig(
        key=_required_text(account, "key"),
        name=_required_text(account, "name"),
        handle_env=_required_text(account, "handle_env"),
        app_password_env=_required_text(account, "app_password_env"),
        state_file=_required_text(account, "state_file"),
        sources=sources,
    )


def _load_source(data: dict) -> SourceConfig:
    hashtag = _optional_text(data, "hashtag")
    if hashtag and not HASHTAG_PATTERN.fullmatch(hashtag):
        raise ValueError(
            f"Invalid hashtag {hashtag!r}; omit #, spaces and hyphens"
        )

    return SourceConfig(
        type=_required_text(data, "type"),
        name=_required_text(data, "name"),
        url=_required_text(data, "url"),
        channel=_optional_text(data, "channel"),
        hashtag=hashtag,
    )


def _required_text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected a non-empty string for {key!r}")
    return value.strip()


def _optional_text(data: dict, key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected a non-empty string for {key!r}")
    return value.strip()
