import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bluesky_feeds.config import load_account_config  # noqa: E402


class AccountConfigTests(unittest.TestCase):
    def test_scf_has_all_channels_and_explicit_hashtags(self):
        config = load_account_config(ROOT / "config" / "scf.toml")

        self.assertEqual(config.key, "scf")
        self.assertEqual(len(config.sources), 10)
        self.assertEqual(
            {source.hashtag for source in config.sources},
            {
                "bancykel",
                "bmx",
                "cykelcross",
                "ecycling",
                "gravel",
                "landsväg",
                "mountainbike",
                "paracykel",
                "trial",
                "förbundet",
            },
        )

    def test_ecycling_hashtag_does_not_contain_hyphen(self):
        config = load_account_config(ROOT / "config" / "scf.toml")
        source = next(source for source in config.sources if source.channel == "e-cycling")

        self.assertEqual(source.hashtag, "ecycling")


if __name__ == "__main__":
    unittest.main()
