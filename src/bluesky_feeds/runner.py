from __future__ import annotations

import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable, Protocol

from .config import load_account_config
from .models import AccountConfig, Article, SourceConfig
from .sources.dif_football import DifFootballSource
from .sources.dif_hockey import DifHockeySource
from .sources.rss import RssSource
from .state import PublishedState


class Publisher(Protocol):
    def publish(self, article: Article, *, label: str | None = None) -> dict:
        """Publish one article or raise an exception."""


@dataclass(frozen=True, slots=True)
class RunResult:
    discovered: int
    skipped: int
    posted: int
    seeded: int
    dry_run: int


def build_source(config: SourceConfig):
    if config.type == "rss":
        return RssSource(config)
    if config.type == "dif_hockey":
        return DifHockeySource(config)
    if config.type == "dif_football":
        return DifFootballSource(config)
    raise ValueError(f"Unsupported source type {config.type!r}")


def run_account(
    config: AccountConfig,
    *,
    publisher: Publisher | None = None,
    dry_run: bool = False,
    seed: bool = False,
) -> RunResult:
    if dry_run and seed:
        raise ValueError("--dry-run and --seed cannot be used together")
    if not dry_run and not seed and publisher is None:
        raise ValueError("A publisher is required for a live run")

    sources = [build_source(source_config) for source_config in config.sources]
    articles: list[Article] = []
    worker_count = min(8, len(sources))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for fetched_articles in executor.map(lambda source: source.fetch(), sources):
            articles.extend(fetched_articles)

    state = PublishedState.load(config.state_file)
    return process_articles(
        articles,
        config=config,
        state=state,
        publisher=publisher,
        dry_run=dry_run,
        seed=seed,
    )


def process_articles(
    articles: Iterable[Article],
    *,
    config: AccountConfig,
    state: PublishedState,
    publisher: Publisher | None = None,
    dry_run: bool = False,
    seed: bool = False,
) -> RunResult:
    unique = {article.url: article for article in articles}
    ordered = sorted(unique.values(), key=lambda article: article.published_at)
    skipped = posted = seeded = dry_run_count = 0

    for article in ordered:
        if state.contains(article):
            skipped += 1
            continue

        if dry_run:
            dry_run_count += 1
            print(f"DRY RUN [{article.channel or article.source}] #{article.hashtag or '-'} {article.title}")
            continue

        if seed:
            state.mark(article, status="seeded")
            state.save()
            seeded += 1
            continue

        if publisher is None:
            raise ValueError("A publisher is required for a live run")
        publisher.publish(article, label=config.post_label)
        state.mark(article, status="posted")
        state.save()
        posted += 1

    return RunResult(
        discovered=len(ordered),
        skipped=skipped,
        posted=posted,
        seeded=seeded,
        dry_run=dry_run_count,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish configured news feeds to Bluesky")
    parser.add_argument("--config", required=True, help="Path to account TOML configuration")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="List new posts without publishing")
    mode.add_argument("--seed", action="store_true", help="Mark current posts without publishing")
    args = parser.parse_args()

    config = load_account_config(args.config)
    publisher = None
    if not args.dry_run and not args.seed:
        from .bluesky_client import BlueskyClient

        handle = os.environ.get(config.handle_env, "")
        app_password = os.environ.get(config.app_password_env, "")
        publisher = BlueskyClient(handle, app_password)

    result = run_account(
        config,
        publisher=publisher,
        dry_run=args.dry_run,
        seed=args.seed,
    )
    print(
        "Run complete: "
        f"discovered={result.discovered} skipped={result.skipped} "
        f"posted={result.posted} seeded={result.seeded} dry_run={result.dry_run}"
    )


if __name__ == "__main__":
    main()
