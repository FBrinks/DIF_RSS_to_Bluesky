# DIF RSS to Bluesky

Automatically posts news about Djurgårdens IF (DIF) to Bluesky. Two bots run from this repo:

| Bot | Sources | Script | State file |
|-----|---------|--------|------------|
| Hockey | [difhockey.se](https://www.difhockey.se) API + [SvenskaFans RSS](https://www.svenskafans.com/rss/team/251) | `news_fetcher.py` | `posted_news.json` |
| Football | [dif.se](https://www.dif.se) news feed + [SvenskaFans RSS](https://www.svenskafans.com/rss/team/46) | `news_fetcher_diffotboll.py` | `posted_news_football.json` |

## How it works

1. A GitHub Actions workflow (`.github/workflows/rss_to_bluesky.yml`) runs every 30 minutes (and can be triggered manually).
2. Each fetcher collects the latest articles from the club site and the SvenskaFans RSS feed.
3. Articles not already listed in the state file are posted to Bluesky as link cards (OpenGraph title, description and image).
4. The state file (last 100 links) is committed back to the repo so duplicates are not posted.

## Files

- `news_fetcher.py` / `news_fetcher_diffotboll.py` – fetch news and decide what to post (hockey / football)
- `post_to_bluesky.py` / `post_to_bluesky_diffotboll.py` – Bluesky authentication, OpenGraph scraping, image upload and posting
- `rss_to_bluesky.py` – earlier standalone RSS-only script
- `posted_news*.json` – already-posted articles

## Setup

Requires Python 3.11.

```bash
pip install -r requirements.txt
```

Create a `.env` file (or set environment variables) using Bluesky [app passwords](https://bsky.app/settings/app-passwords):

```env
BLUESKY_USERNAME=your-hockey-handle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
BLUESKY_USERNAME_FOOTBALL=your-football-handle.bsky.social
BLUESKY_APP_PASSWORD_FOOTBALL=xxxx-xxxx-xxxx-xxxx
```

Run locally:

```bash
python news_fetcher.py             # hockey
python news_fetcher_diffotboll.py  # football
```

## GitHub Actions

Add these repository secrets (Settings → Secrets and variables → Actions):

- `BLUESKY_USERNAME`, `BLUESKY_APP_PASSWORD`
- `BLUESKY_USERNAME_FOOTBALL`, `BLUESKY_APP_PASSWORD_FOOTBALL`

The workflow needs `contents: write` permission to commit the state files.
