# CLAUDE.md — ml (EXPERIMENTAL — unwired)

TensorFlow model code is real but orphaned; HuggingFace + MLflow are declared but never
imported. Never present the ML layer as wired without a real artifact.

## Known reality (verified 2026-06-25)
- `recommendation_engine.py`, `prediction_models.py`: real Keras models, BUT they fall back to
  `np.random` synthetic data, persist no weights, never write predictions back to BigQuery, and
  are referenced by no dbt model.
- Sentiment is a hardcoded positive/negative word-list (`prediction_models.py:169`) — not
  HuggingFace, despite `transformers`/`sentence-transformers` in requirements.
- MLflow: declared in requirements, **zero usage**. GPU explicitly disabled "for demo".

## To wire it (Workstream 3)
Run real HuggingFace sentiment over social mentions; train TF on real BigQuery data; persist a
SavedModel; write predictions back to BigQuery; add a dbt model (e.g. `fct_recommendations`)
consuming them so "ML feeds analytics" is true. Drop the MLflow claim unless it is actually used.
