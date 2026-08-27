from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .models import Article
from .post_content import build_post_content


BSKY_SERVICE = "https://bsky.social"
MAX_THUMBNAIL_BYTES = 1_000_000
REQUEST_TIMEOUT = 15


class BlueskyError(RuntimeError):
    """Raised when Bluesky authentication or publishing fails."""


class BlueskyClient:
    """Minimal AT Protocol client for publishing articles with link cards."""

    def __init__(
        self,
        handle: str,
        app_password: str,
        *,
        service: str = BSKY_SERVICE,
        session: requests.Session | None = None,
    ) -> None:
        if not handle.strip() or not app_password.strip():
            raise ValueError("Bluesky handle and app password are required")

        self.handle = handle.strip()
        self.app_password = app_password.strip()
        self.service = service.rstrip("/")
        self.session = session or requests.Session()
        self.access_token: str | None = None
        self.repo: str | None = None

    def authenticate(self) -> None:
        response = self.session.post(
            f"{self.service}/xrpc/com.atproto.server.createSession",
            json={"identifier": self.handle, "password": self.app_password},
            timeout=REQUEST_TIMEOUT,
        )
        self._raise_for_status(response, "Bluesky authentication failed")
        payload = response.json()
        self.access_token = payload["accessJwt"]
        self.repo = payload.get("did", self.handle)

    def publish(self, article: Article, *, label: str | None = None) -> dict[str, Any]:
        if not self.access_token or not self.repo:
            self.authenticate()

        metadata = self._metadata(article)
        post = build_post_content(article, label=label)
        external: dict[str, Any] = {
            "uri": article.url,
            "title": metadata["title"],
            "description": metadata["description"],
        }

        if metadata["image_url"]:
            thumbnail = self._upload_thumbnail(metadata["image_url"])
            if thumbnail:
                external["thumb"] = thumbnail

        payload = {
            "repo": self.repo,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": post.text,
                "facets": list(post.facets),
                "embed": {
                    "$type": "app.bsky.embed.external",
                    "external": external,
                },
                "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        }
        response = self.session.post(
            f"{self.service}/xrpc/com.atproto.repo.createRecord",
            headers=self._auth_headers("application/json"),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        self._raise_for_status(response, f"Failed to publish {article.url}")
        return response.json()

    def _metadata(self, article: Article) -> dict[str, str | None]:
        title = article.title
        description = article.description
        image_url = article.image_url
        if description and image_url:
            return {"title": title, "description": description, "image_url": image_url}

        try:
            response = self.session.get(
                article.url,
                headers={"User-Agent": "BlueskyFeeds/1.0"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            return {
                "title": title,
                "description": description or "",
                "image_url": image_url,
            }

        soup = BeautifulSoup(response.text, "html.parser")
        og_description = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        if not description and og_description and og_description.get("content"):
            description = str(og_description["content"]).strip()
        if not image_url and og_image and og_image.get("content"):
            image_url = urljoin(article.url, str(og_image["content"]).strip())

        return {
            "title": title,
            "description": description or "",
            "image_url": image_url,
        }

    def _upload_thumbnail(self, image_url: str) -> dict[str, Any] | None:
        try:
            response = self.session.get(
                image_url,
                headers={"User-Agent": "BlueskyFeeds/1.0", "Accept": "image/*"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
        if not content_type.startswith("image/"):
            return None
        if len(response.content) > MAX_THUMBNAIL_BYTES:
            return None

        upload = self.session.post(
            f"{self.service}/xrpc/com.atproto.repo.uploadBlob",
            headers=self._auth_headers(content_type),
            data=response.content,
            timeout=REQUEST_TIMEOUT,
        )
        self._raise_for_status(upload, f"Failed to upload thumbnail {image_url}")
        return upload.json()["blob"]

    def _auth_headers(self, content_type: str) -> dict[str, str]:
        if not self.access_token:
            raise BlueskyError("Client is not authenticated")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": content_type,
        }

    @staticmethod
    def _raise_for_status(response: requests.Response, message: str) -> None:
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            detail = response.text[:500] if response.text else str(error)
            raise BlueskyError(f"{message}: {detail}") from error
