from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT = 15


def fetch_json(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "BlueskyFeeds/1.0",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object from {url}")
    return payload
