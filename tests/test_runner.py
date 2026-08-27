import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bluesky_feeds.models import AccountConfig, Article  # noqa: E402
from bluesky_feeds.runner import process_articles  # noqa: E402
from bluesky_feeds.state import PublishedState  # noqa: E402


class FakePublisher:
    def __init__(self, *, fail_url=None):
        self.fail_url = fail_url
        self.articles = []

    def publish(self, article, *, label=None):
        if article.url == self.fail_url:
            raise RuntimeError("publish failed")
        self.articles.append((article, label))
        return {"uri": f"at://post/{article.id}"}


def make_article(number, published_at):
    return Article(
        id=f"article-{number}",
        title=f"Article {number}",
        url=f"https://scf.se/gravel/article-{number}/",
        published_at=published_at,
        source="Gravel",
        channel="gravel",
        hashtag="gravel",
    )


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.state_path = Path(self.temporary_directory.name) / "state.json"
        self.config = AccountConfig(
            key="scf",
            name="SCF",
            handle_env="SCF_HANDLE",
            app_password_env="SCF_PASSWORD",
            state_file=str(self.state_path),
            post_label="Svenska Cykelförbundet",
            sources=(),
        )

    def test_posts_oldest_first_and_deduplicates_urls(self):
        now = datetime.now(timezone.utc)
        older = make_article(1, now - timedelta(hours=1))
        newer = make_article(2, now)
        publisher = FakePublisher()
        state = PublishedState.load(self.state_path)

        result = process_articles(
            [newer, older, newer],
            config=self.config,
            state=state,
            publisher=publisher,
        )

        self.assertEqual([item[0].id for item in publisher.articles], ["article-1", "article-2"])
        self.assertEqual(result.discovered, 2)
        self.assertEqual(result.posted, 2)
        self.assertTrue(self.state_path.exists())

    def test_failed_post_is_not_saved(self):
        item = make_article(1, datetime.now(timezone.utc))
        publisher = FakePublisher(fail_url=item.url)
        state = PublishedState.load(self.state_path)

        with self.assertRaises(RuntimeError):
            process_articles(
                [item], config=self.config, state=state, publisher=publisher
            )

        self.assertFalse(state.contains(item))

    def test_seed_saves_without_publishing(self):
        item = make_article(1, datetime.now(timezone.utc))
        state = PublishedState.load(self.state_path)

        result = process_articles([item], config=self.config, state=state, seed=True)

        self.assertEqual(result.seeded, 1)
        self.assertTrue(state.contains(item))
        saved = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["published"][item.url]["status"], "seeded")

    def test_dry_run_does_not_change_state(self):
        item = make_article(1, datetime.now(timezone.utc))
        state = PublishedState.load(self.state_path)

        result = process_articles([item], config=self.config, state=state, dry_run=True)

        self.assertEqual(result.dry_run, 1)
        self.assertFalse(self.state_path.exists())

    def test_loads_legacy_list_state(self):
        item = make_article(1, datetime.now(timezone.utc))
        self.state_path.write_text(json.dumps([item.url]), encoding="utf-8")

        state = PublishedState.load(self.state_path)

        self.assertTrue(state.contains(item))


if __name__ == "__main__":
    unittest.main()
