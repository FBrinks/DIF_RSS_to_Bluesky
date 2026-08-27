import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bluesky_feeds.models import SourceConfig  # noqa: E402
from bluesky_feeds.sources.dif_football import parse_dif_football  # noqa: E402
from bluesky_feeds.sources.dif_hockey import parse_dif_hockey  # noqa: E402


class DifSourceTests(unittest.TestCase):
    def test_parses_current_hockey_api_fields(self):
        payload = {
            "data": {
                "articleItems": [
                    {
                        "id": "c7zatkf-1lead",
                        "header": "Nytt spelarlån – junior debuterar",
                        "intro": "Djurgården har lånat in två forwards.",
                        "publishedAt": "2026-08-27T10:39:23.000Z",
                    }
                ]
            }
        }
        config = SourceConfig(
            type="dif_hockey", name="DIF Hockey", url="https://example.com/api"
        )

        articles = parse_dif_hockey(payload, config)

        self.assertEqual(articles[0].title, "Nytt spelarlån – junior debuterar")
        self.assertEqual(
            articles[0].url,
            "https://www.difhockey.se/article/c7zatkf-1lead/view",
        )
        self.assertEqual(
            articles[0].published_at,
            datetime(2026, 8, 27, 10, 39, 23, tzinfo=timezone.utc),
        )

    def test_parses_football_article_and_video_dates(self):
        payload = {
            "pages": [
                {
                    "key": "article-key",
                    "url": "/nyheter/2026/example",
                    "heading": "En artikel",
                    "preamble": "Ingress",
                    "date": "2026-08-27T07:00:00.000Z",
                    "image": {"src": "https://www.dif.se/media/example.jpg"},
                },
                {
                    "key": "video-key",
                    "url": "/video/2026/example",
                    "name": "En video",
                    "description": "Videobeskrivning",
                    "publishedOnDifPlay": "2026-08-25T08:18:00.000Z",
                    "thumbnailUrl": "https://video.example/thumbnail.jpg",
                },
            ]
        }
        config = SourceConfig(
            type="dif_football", name="DIF Fotboll", url="https://example.com/api"
        )

        articles = parse_dif_football(payload, config)

        self.assertEqual([article.title for article in articles], ["En artikel", "En video"])
        self.assertEqual(articles[0].url, "https://www.dif.se/nyheter/2026/example")
        self.assertEqual(
            articles[1].published_at,
            datetime(2026, 8, 25, 8, 18, tzinfo=timezone.utc),
        )
        self.assertEqual(articles[1].image_url, "https://video.example/thumbnail.jpg")


if __name__ == "__main__":
    unittest.main()
