# Configuration-driven Bluesky feeds

## Goal

Run DIF Hockey, DIF Fotboll and SCF from one scheduled GitHub Actions job without
duplicating publishing logic. Existing DIF behavior must remain intact while SCF
gets ten RSS channels and an explicit channel hashtag on every post.

## SCF channel mapping

| Channel | RSS feed | Hashtag |
| --- | --- | --- |
| Bancykel | `https://scf.se/bancykel/feed/` | `#bancykel` |
| BMX | `https://scf.se/bmx/feed/` | `#bmx` |
| Cykelcross | `https://scf.se/cykelcross/feed/` | `#cykelcross` |
| E-cycling | `https://scf.se/e-cycling/feed/` | `#ecycling` |
| Gravel | `https://scf.se/gravel/feed/` | `#gravel` |
| Landsväg | `https://scf.se/landsvag/feed/` | `#landsväg` |
| Mountainbike | `https://scf.se/mountainbike/feed/` | `#mountainbike` |
| Paracykel | `https://scf.se/paracykel/feed/` | `#paracykel` |
| Trial | `https://scf.se/trial/feed/` | `#trial` |
| Förbundet | `https://scf.se/forbundet/feed/` | `#förbundet` |

The mapping is explicit rather than derived from the URL. This prevents
`e-cycling` from becoming a broken hashtag containing a hyphen.

## Delivery phases

1. **Foundation**
   - Add shared `Article`, `SourceConfig` and `AccountConfig` models.
   - Load account and source configuration from TOML.
   - Validate SCF channel and hashtag configuration.
2. **Publishing client**
   - Replace the two account-specific Bluesky modules with one client.
   - Generate correct byte-based facets for links and hashtags.
   - Enforce Bluesky text and image limits.
3. **Source adapters**
   - Add a reusable RSS adapter.
   - Move DIF Hockey and DIF Fotboll JSON parsing into separate adapters.
   - Normalize all source results to `Article`.
4. **State and runner**
   - Persist only confirmed posts.
   - Save state after each successful post.
   - Add `--dry-run` and `--seed` modes.
5. **Workflow migration**
   - Run all accounts sequentially in one scheduled job.
   - Install dependencies once and commit all state once.
   - Prevent overlapping scheduled runs with a concurrency group.
6. **Verification and rollout**
   - Run tests and SCF dry-run.
   - Seed current SCF items without posting them.
   - Add SCF GitHub Secrets.
   - Manually dispatch one controlled live run before enabling the schedule.

## Required SCF secrets

- `SCF_BLUESKY_HANDLE`
- `SCF_BLUESKY_APP_PASSWORD`

Use a Bluesky app password. Never store the account password in the repository
or GitHub Actions configuration.

## Acceptance criteria

- Existing DIF Hockey and DIF Fotboll posts retain their current content.
- One scheduled job handles every configured account.
- Every SCF post contains exactly one configured channel hashtag.
- Links and Unicode hashtags such as `#landsväg` have valid byte facets.
- A failed post is retried and is not marked as published.
- A successful post cannot be published again on the next run.
- SCF can be seeded and dry-run without access to live Bluesky credentials.
