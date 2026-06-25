# CLAUDE.md — dbt project (the working core)

BigQuery backend, medallion bronze→silver→gold. This is the real, demonstrable part of the project.

## Reality (RSS-only honest scope)
- **Full RSS star schema, all green on BigQuery.** Staging (views): `stg_rss__podcasts`,
  `stg_rss__episodes`, `stg_listening__events`. Marts (tables): `dim_podcast` (SCD2),
  `dim_episodes`, `fct_listening_events` (incremental, engagement-scored),
  `podcast_performance_metrics`. Snapshot: `podcast_snapshot` (SCD2 history). Macros:
  `calculate_engagement_score.sql`, `generate_schema_name.sql`.
- Bronze source data is **synthetic sample data** (4 podcasts, 20 episodes, 240 events) loaded
  directly into BigQuery — clearly sample, not a live feed. Spotify/Apple staging models are NOT
  built (RSS-only scope); their aspirational source defs live in `sources.aspirational.yml.bak`.
- Packages: dbt_utils, dbt_expectations, elementary (observability), audit_helper, codegen.
- `dbt build && dbt test` is green (PASS=86) with run artifacts in `target/`. Never `ref()` a
  model that doesn't exist (e.g. stg_spotify/apple) — that re-introduces the Jinja-comment bug.

## Run
- Activate the repo-root venv, then from this directory: `dbt deps && dbt debug && dbt build && dbt test`.
- See the `dbt-validate` skill or `/validate`.
- Profile `podcastflow_analytics` (BigQuery): dev→`silver`, prod→`gold`. Requires
  `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`.

## Conventions (AGENTS.md)
- snake_case; layer prefixes `stg_`/`int_`/`dim_`/`fct_`. Lower-case SQL keywords, aligned CTEs.
- Materialization: staging = view (silver), marts = table (gold).

## Guardrails
- No `--full-refresh` against prod without explicit approval (guard hook blocks it).
- Loads must be idempotent (MERGE / WRITE_TRUNCATE). Success = `target/run_results.json`
  status success — no artifacts means not done.
