import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bluesky_feeds.models import SourceConfig  # noqa: E402
from bluesky_feeds.sources.rss import parse_rss  # noqa: E402


RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>SCF Landsväg</title>
    <item>
      <title>Åkare klar för mästerskap</title>
      <link>https://scf.se/landsvag/akare-klar/</link>
      <guid isPermaLink="false">https://scf.se/landsvag/?p=123</guid>
      <pubDate>Wed, 26 Aug 2026 14:02:23 +0000</pubDate>
      <description><![CDATA[En svensk cyklist är klar för start.]]></description>
    </item>
  </channel>
</rss>
"""


class RssParserTests(unittest.TestCase):
    def test_normalizes_scf_item_and_preserves_channel_hashtag(self):
        config = SourceConfig(
            type="rss",
            name="Landsväg",
            url="https://scf.se/landsvag/feed/",
            channel="landsväg",
            hashtag="landsväg",
        )

        articles = parse_rss(RSS, config)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].id, "https://scf.se/landsvag/?p=123")
        self.assertEqual(articles[0].channel, "landsväg")
        self.assertEqual(articles[0].hashtag, "landsväg")
        self.assertEqual(
            articles[0].published_at,
            datetime(2026, 8, 26, 14, 2, 23, tzinfo=timezone.utc),
        )

    def test_skips_item_without_title_or_link(self):
        broken_rss = """<rss><channel><item><title>Incomplete</title></item></channel></rss>"""
        config = SourceConfig(type="rss", name="Test", url="https://example.com/feed")

        self.assertEqual(parse_rss(broken_rss, config), [])

    def test_accepts_whitespace_before_xml_declaration_used_by_scf(self):
        config = SourceConfig(type="rss", name="Test", url="https://example.com/feed")

        articles = parse_rss("\n  " + RSS, config)

        self.assertEqual(len(articles), 1)


if __name__ == "__main__":
    unittest.main()
