{{
  config(
    materialized='incremental',
    unique_key='event_id',
    schema='gold',
    tags=['marts', 'core', 'facts'],
    on_schema_change='append_new_columns'
  )
}}

with events as (
    select * from {{ ref('stg_listening__events') }}
    {% if is_incremental() %}
    -- Only process events newer than what we've already loaded
    where ingestion_timestamp > (
        select coalesce(max(ingestion_timestamp), timestamp('1900-01-01'))
        from {{ this }}
    )
    {% endif %}
),

episodes as (
    select episode_key, episode_id, podcast_id, duration_seconds
    from {{ ref('dim_episodes') }}
),

joined as (
    select
        ev.event_id,
        ev.user_id,
        ev.session_id,
        ev.episode_id,
        ep.episode_key,
        ep.podcast_id,
        ev.event_type,
        ev.event_timestamp,
        ev.position_seconds,
        ev.completion_percentage,
        ev.completion_fraction,
        ev.platform,
        ev.device_type,
        ev.location_country,
        ev.ingestion_timestamp,
        coalesce(ep.duration_seconds, 0) as episode_duration_seconds,
        -- Platform engagement weights
        case ev.platform
            when 'ios' then 1.10
            when 'android' then 1.00
            when 'web' then 0.90
            else 1.05
        end as platform_weight
    from events ev
    left join episodes ep on ev.episode_id = ep.episode_id
)

select
    event_id,
    user_id,
    session_id,
    episode_id,
    episode_key,
    podcast_id,
    event_type,
    event_timestamp,
    position_seconds,
    completion_percentage,
    completion_fraction,
    platform,
    device_type,
    location_country,
    episode_duration_seconds,
    platform_weight,
    -- Engagement score via the custom macro (0-100)
    round(
        {{ calculate_engagement_score('completion_fraction', 'episode_duration_seconds', 'platform_weight', 0, 0) }}
    , 1) as engagement_score,
    ingestion_timestamp,
    current_timestamp as dbt_loaded_at
from joined
