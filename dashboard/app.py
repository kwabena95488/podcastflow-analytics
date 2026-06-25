"""
PodcastFlow Analytics Dashboard

Streamlit dashboard rendering the dbt **gold** layer directly from BigQuery
(project resolved from GCP_PROJECT_ID, default your-gcp-project). Uses
Application Default Credentials (run `gcloud auth application-default login`).

Honest scope: this shows only what the dbt project actually builds today —
the RSS-only star schema (podcasts, episodes, listening events, engagement
metrics). It does not invent social/sentiment data the pipeline doesn't have.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import bigquery

PROJECT = (
    os.getenv("GCP_PROJECT_ID")
    or os.getenv("GOOGLE_CLOUD_PROJECT")
    or "your-gcp-project"
)
GOLD = f"`{PROJECT}.gold`"

st.set_page_config(
    page_title="PodcastFlow Analytics",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .dashboard-header {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
        color: white; padding: 1.5rem 2rem; border-radius: 0.5rem; margin-bottom: 1.5rem;
      }
      .dashboard-header h1 { margin: 0; font-size: 1.8rem; }
      .dashboard-header p { margin: 0.25rem 0 0; opacity: 0.9; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


@st.cache_data(ttl=120)
def run_query(sql: str) -> pd.DataFrame:
    return get_client().query(sql).to_dataframe()


def gold(table: str) -> str:
    return f"`{PROJECT}.gold.{table}`"


# ---- Header --------------------------------------------------------------
st.markdown(
    f"""
    <div class="dashboard-header">
      <h1>🎧 PodcastFlow Analytics</h1>
      <p>dbt + BigQuery gold layer · project <code>{PROJECT}</code> · RSS sample data</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("About")
    st.caption(
        "Live view of the dbt gold star schema in BigQuery. Data is clearly-"
        "synthetic RSS sample data used to demonstrate the medallion pipeline."
    )
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

try:
    metrics = run_query(f"SELECT * FROM {gold('podcast_performance_metrics')} ORDER BY avg_engagement_score DESC")
except Exception as exc:  # noqa: BLE001
    st.error(
        f"Could not read {gold('podcast_performance_metrics')}.\n\n"
        f"Check that you've run `gcloud auth application-default login`, that "
        f"`{PROJECT}` is correct, and that `dbt build` has materialized the gold layer.\n\n{exc}"
    )
    st.stop()

if metrics.empty:
    st.warning("The gold tables are empty. Run `dbt build` after loading the sample data.")
    st.stop()

# ---- KPI row -------------------------------------------------------------
totals = run_query(
    f"""
    SELECT
      (SELECT COUNT(*) FROM {gold('dim_podcast')} WHERE is_current) AS podcasts,
      (SELECT COUNT(*) FROM {gold('dim_episodes')}) AS episodes,
      (SELECT COUNT(*) FROM {gold('fct_listening_events')}) AS events,
      (SELECT ROUND(AVG(engagement_score), 1) FROM {gold('fct_listening_events')}) AS avg_engagement
    """
).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Podcasts", int(totals["podcasts"]))
c2.metric("Episodes", int(totals["episodes"]))
c3.metric("Listening events", int(totals["events"]))
c4.metric("Avg engagement", f"{totals['avg_engagement']:.1f}")

st.divider()

# ---- Per-podcast performance --------------------------------------------
left, right = st.columns(2)
with left:
    st.subheader("Engagement by podcast")
    fig = px.bar(
        metrics, x="avg_engagement_score", y="podcast_title", orientation="h",
        color="avg_engagement_score", color_continuous_scale="Purples",
        labels={"avg_engagement_score": "Avg engagement", "podcast_title": ""},
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Listeners & completion")
    fig = px.scatter(
        metrics, x="avg_completion_rate", y="unique_listeners", size="total_listening_events",
        color="podcast_title", hover_name="podcast_title",
        labels={"avg_completion_rate": "Avg completion rate", "unique_listeners": "Unique listeners"},
    )
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

# ---- Platform & event-type breakdown ------------------------------------
left, right = st.columns(2)
with left:
    st.subheader("Engagement by platform")
    plat = run_query(
        f"""
        SELECT platform, COUNT(*) AS events, ROUND(AVG(engagement_score), 1) AS avg_engagement
        FROM {gold('fct_listening_events')} GROUP BY platform ORDER BY avg_engagement DESC
        """
    )
    fig = px.bar(plat, x="platform", y="avg_engagement", color="platform", text="events")
    fig.update_layout(showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Event mix")
    etype = run_query(
        f"SELECT event_type, COUNT(*) AS events FROM {gold('fct_listening_events')} GROUP BY event_type ORDER BY events DESC"
    )
    fig = px.pie(etype, names="event_type", values="events", hole=0.45)
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ---- Top episodes --------------------------------------------------------
st.subheader("Top episodes by engagement")
top_eps = run_query(
    f"""
    SELECT d.podcast_title, d.episode_title, d.duration_bucket,
           COUNT(*) AS events, ROUND(AVG(f.engagement_score), 1) AS avg_engagement
    FROM {gold('fct_listening_events')} f
    JOIN {gold('dim_episodes')} d USING (episode_key)
    GROUP BY d.podcast_title, d.episode_title, d.duration_bucket
    ORDER BY avg_engagement DESC
    LIMIT 10
    """
)
st.dataframe(top_eps, use_container_width=True, hide_index=True)

# ---- Raw metrics table ---------------------------------------------------
with st.expander("Full podcast_performance_metrics (gold)"):
    st.dataframe(metrics, use_container_width=True, hide_index=True)
