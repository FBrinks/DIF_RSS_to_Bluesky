import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bluesky_feeds.models import Article  # noqa: E402
from bluesky_feeds.post_content import build_post_content  # noqa: E402


def article(**overrides):
    values = {
        "id": "scf-1",
        "title": "Svenska cyklister klara för mästerskap",
        "url": "https://scf.se/landsvag/example/",
        "published_at": datetime(2026, 8, 27, tzinfo=timezone.utc),
        "source": "SCF",
        "channel": "landsväg",
        "hashtag": "landsväg",
    }
    values.update(overrides)
    return Article(**values)


def facet_text(post, facet):
    encoded = post.text.encode("utf-8")
    index = facet["index"]
    return encoded[index["byteStart"] : index["byteEnd"]].decode("utf-8")


class PostContentTests(unittest.TestCase):
    def test_creates_link_and_unicode_hashtag_facets(self):
        post = build_post_content(article(), label="Svenska Cykelförbundet")

        self.assertEqual(len(post.facets), 2)
        self.assertEqual(facet_text(post, post.facets[0]), "#landsväg")
        self.assertEqual(
            post.facets[0]["features"][0],
            {"$type": "app.bsky.richtext.facet#tag", "tag": "landsväg"},
        )
        self.assertEqual(facet_text(post, post.facets[1]), article().url)
        self.assertEqual(
            post.facets[1]["features"][0]["$type"],
            "app.bsky.richtext.facet#link",
        )

    def test_truncates_title_but_preserves_hashtag_and_url(self):
        post = build_post_content(article(title="Å" * 400))

        self.assertLessEqual(len(post.text), 300)
        self.assertIn("#landsväg", post.text)
        self.assertTrue(post.text.endswith(article().url))
        self.assertIn("…", post.text)

    def test_post_without_channel_has_only_link_facet(self):
        post = build_post_content(article(channel=None, hashtag=None))

        self.assertEqual(len(post.facets), 1)
        self.assertEqual(facet_text(post, post.facets[0]), article().url)


if __name__ == "__main__":
    unittest.main()
