{{
  config(
    materialized='table',
    schema='gold',
    tags=['marts', 'analytics']
  )
}}

with events as (
    select * from {{ ref('fct_listening_events') }}
),

episodes as (
    select * from {{ ref('dim_episodes') }}
),

podcasts as (
    select * from {{ ref('dim_podcast') }}
),

event_agg as (
    select
        podcast_id,
        count(*) as total_listening_events,
        count(distinct user_id) as unique_listeners,
        count(distinct session_id) as total_sessions,
        countif(event_type = 'complete') as completions,
        avg(completion_fraction) as avg_completion_rate,
        avg(engagement_score) as avg_engagement_score
    from events
    group by podcast_id
),

episode_agg as (
    select
        podcast_id,
        count(*) as total_episodes,
        avg(duration_minutes) as avg_episode_minutes
    from episodes
    group by podcast_id
)

select
    p.podcast_id,
    p.podcast_title,
    p.category,
    p.author,
    coalesce(c.total_episodes, 0) as total_episodes,
    round(coalesce(c.avg_episode_minutes, 0), 1) as avg_episode_minutes,
    coalesce(a.total_listening_events, 0) as total_listening_events,
    coalesce(a.unique_listeners, 0) as unique_listeners,
    coalesce(a.total_sessions, 0) as total_sessions,
    coalesce(a.completions, 0) as completions,
    round(coalesce(a.avg_completion_rate, 0), 3) as avg_completion_rate,
    round(coalesce(a.avg_engagement_score, 0), 1) as avg_engagement_score,
    current_timestamp as dbt_loaded_at
from podcasts p
left join event_agg a on p.podcast_id = a.podcast_id
left join episode_agg c on p.podcast_id = c.podcast_id
where p.is_current = true
