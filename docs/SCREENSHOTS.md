# Screenshot shot list

Capture these four images and save them into `docs/img/` with the **exact filenames** below.
The README already references them; once saved, they render automatically.

All commands run from `podcastflow-analytics/` unless noted. The dbt commands need a BigQuery
project + OAuth (`gcloud auth application-default login`, `export GCP_PROJECT_ID=<project>`).

---

## 1. `dbt-lineage.png` — dbt docs lineage graph

1. Generate + serve the docs:
   ```bash
   cd dbt_podcast_analytics
   dbt docs generate
   dbt docs serve --port 8080
   ```
2. Open **http://localhost:8080**.
3. Click the **lineage graph** icon (bottom-right of the page).
4. In the graph, set the selector to `+gold,gold+` or just expand the full graph so you can
   see Bronze sources → `stg_*` (silver) → `dim_*` / `fct_*` (gold).
5. Capture the graph. **Save as:** `docs/img/dbt-lineage.png`

> What "good" looks like: sources on the left, three `stg_` views in the middle, the four
> gold marts + the snapshot on the right, edges flowing left→right.

---

## 2. `gold-sample-rows.png` — sample rows from a gold mart

Run one query against the gold layer and screenshot the result grid. Easiest via `bq`:

```bash
bq query --use_legacy_sql=false --project_id=$GCP_PROJECT_ID \
'SELECT podcast_title, total_episodes, total_listening_events,
        ROUND(avg_engagement_score,1) AS avg_engagement
 FROM `'"$GCP_PROJECT_ID"'.gold.podcast_performance_metrics`
 ORDER BY total_listening_events DESC
 LIMIT 10'
```

Alternatively open the **BigQuery Studio** console, run the same query, and screenshot the
results table. **Save as:** `docs/img/gold-sample-rows.png`

> If column names differ from the snippet above, open
> `dbt_podcast_analytics/models/marts/analytics/podcast_performance_metrics.sql` and pick the
> real output columns. Do **not** hand-edit numbers into the screenshot — capture the live grid.

---

## 3. `dashboard-overview.png` — Streamlit dashboard

```bash
streamlit run dashboard/app.py     # opens http://localhost:8501
```

Capture the **main overview page** showing the KPI metric cards + the top listening-trend
chart. **Save as:** `docs/img/dashboard-overview.png`

---

## 4. `dbt-build-green.png` — proof of a green run

```bash
cd dbt_podcast_analytics
dbt build
```

Screenshot the **final summary line** of the terminal, e.g.
`Done. PASS=86 WARN=0 ERROR=0 SKIP=0 TOTAL=86`.
**Save as:** `docs/img/dbt-build-green.png`

---

## Optional — architecture PNG

The README has an inline Mermaid diagram (GitHub renders it natively), so a PNG is optional.
To export one (requires Node/npx; installs the Mermaid CLI on first run):

```bash
# from podcastflow-analytics/
npx -y @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/img/architecture.png
```

If you want this, copy the ```mermaid``` block from `README.md` into `docs/architecture.mmd`
first. (Not generated automatically here — no Mermaid renderer was installed.)
