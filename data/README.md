# Data — provenance & regeneration

**All data in this project is synthetic / demo data.** Nothing here is personal,
proprietary, or scraped at scale. The repo intentionally commits **no large data files** —
only a small deterministic seed set and the generator scripts, so the pipeline runs without
any download.

## What's committed (the green path)

| Source | Rows | Provenance | Location |
|---|---|---|---|
| `01_seed_rss_feeds.sql` | 4 podcasts | 100% synthetic (hard-coded `example.com` feeds + mock RSS XML) | `dbt_podcast_analytics/sample_data/` |
| `02_seed_episodes_events.sql` | 20 episodes + 240 listening events | 100% synthetic, **deterministic** via `GENERATE_ARRAY` + `FARM_FINGERPRINT` | `dbt_podcast_analytics/sample_data/` |

~264 rows total — small enough to commit, enough to build every model and pass all tests.
These seed the **bronze** layer; `dbt build` then produces silver views and the gold marts.

## What is NOT committed (generated at runtime, into BigQuery)

The ingestion scripts write **directly to BigQuery** (bronze tables); their output is never
persisted to git:

| Script | Data | Source |
|---|---|---|
| `scripts/data-ingestion/rss_feed_ingestion.py` | RSS feeds/episodes | **Real public RSS** (NPR, Simplecast, Megaphone, etc.) via `requests` + `feedparser` |
| `scripts/data-ingestion/realtime_events_ingestion.py` | Listening events | **Synthetic** — `UserBehaviorSimulator` (`random.*`) |
| `scripts/data-ingestion/social_media_ingestion.py` | Social mentions | **Synthetic** — templated text + random sentiment |

## Regenerate

```bash
export GCP_PROJECT_ID=<your-gcp-project>
gcloud auth application-default login

# Option A — committed seeds (covers the green path; no internet needed)
cd dbt_podcast_analytics
bq query --use_legacy_sql=false --project_id="$GCP_PROJECT_ID" < sample_data/01_seed_rss_feeds.sql
bq query --use_legacy_sql=false --project_id="$GCP_PROJECT_ID" < sample_data/02_seed_episodes_events.sql

# Option B — free-tier-sized synthetic mix (4 feeds, ~500 events, 50 mentions)
python scripts/setup/load_sample_data_emulator.py

# Option C — fuller mix: real public RSS + synthetic events/social
python scripts/setup/run_real_data_ingestion.py
```

Then `cd dbt_podcast_analytics && dbt build` to materialize silver + gold.

> **Note — hard-coded project id.** The seed `.sql` files currently hard-code the BigQuery
> project `your-gcp-project` in their `CREATE OR REPLACE TABLE` statements. Change it to
> your own project before loading (e.g. `sed 's/your-gcp-project/<your-project>/g'`), or
> parameterize the seeds. Tracked as a cleanup item in the repo's pre-public checklist.

## What's gitignored

Raw/large/generated artifacts are excluded by the root `.gitignore`: `*.log`, `logs/`,
dbt `target/`, `dbt_packages/`, Terraform state/vars, `.env`, and credential files. The
`data/` directory itself is intentionally empty on the green path.
