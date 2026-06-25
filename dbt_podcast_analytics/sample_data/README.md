# Sample data (synthetic)

These scripts seed the **bronze** layer with small, clearly-synthetic sample data so the dbt
models build end-to-end without external API access. This is **sample data, not a live feed**.

- `01_seed_rss_feeds.sql` — 4 podcasts (`bronze.rss_feeds`) with realistic RSS XML in `raw_content`.
- `02_seed_episodes_events.sql` — 20 episodes (`bronze.rss_episodes`) + 240 listening events
  (`bronze.listening_events`), generated deterministically from fingerprints.

## Load (requires gcloud auth + a BigQuery project)

```bash
export GCP_PROJECT_ID=<your-project-id>
bq query --use_legacy_sql=false --project_id="$GCP_PROJECT_ID" < sample_data/01_seed_rss_feeds.sql
bq query --use_legacy_sql=false --project_id="$GCP_PROJECT_ID" < sample_data/02_seed_episodes_events.sql
```

(The project id is hard-coded to `your-gcp-project` in the scripts — change it for a different project.)
Then `dbt build` materializes silver views and the gold star schema + snapshot.
