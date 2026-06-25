# CLAUDE.md — streaming (EXPERIMENTAL — does not run)

Kafka/Spark streaming is scaffolding. Never present it as functional without a real run artifact.

## Known landmines (verified 2026-06-25)
- `listening_events_processor.py:45` calls undefined `configure_delta_tables()` → crashes on
  startup. `from delta import *` is also wrong.
- **No Kafka producer exists** anywhere in the repo; `start.sh` creates topics that are never
  populated.
- Real ingestion (`../scripts/data-ingestion/*`) writes DIRECT to BigQuery, bypassing
  Kafka/Spark entirely.
- `start.sh` has a compose-path bug (missing `-f config/docker/docker-compose.yml`).
- `../docker/` is empty.

## To make it demonstrable (Workstream 2)
Fix the undefined function + Delta import; add one Kafka producer; fix the compose path; then
prove one end-to-end run (advancing consumer offsets + sink row count > 0). Requires Docker
Desktop. Until that proof exists, label streaming "experimental" everywhere.
