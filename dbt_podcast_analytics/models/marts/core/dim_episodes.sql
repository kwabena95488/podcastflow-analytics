{{
  config(
    materialized='table',
    schema='gold',
    tags=['marts', 'core', 'dimensions']
  )
}}

with episodes as (
    select * from {{ ref('stg_rss__episodes') }}
),

podcasts as (
    select podcast_id, podcast_title, category, author
    from {{ ref('stg_rss__podcasts') }}
)

select
    e.episode_key,
    e.episode_id,
    e.podcast_id,
    p.podcast_title,
    p.category as podcast_category,
    p.author as podcast_author,
    e.episode_title,
    e.episode_description,
    e.episode_number,
    e.duration_seconds,
    e.duration_minutes,
    case
        when e.duration_seconds >= 3600 then 'long'
        when e.duration_seconds >= 1800 then 'medium'
        else 'short'
    end as duration_bucket,
    e.published_date,
    e.audio_url,
    current_timestamp as dbt_loaded_at
from episodes e
left join podcasts p on e.podcast_id = p.podcast_id
