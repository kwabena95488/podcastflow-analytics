{{
  config(
    materialized='view',
    tags=['staging', 'rss', 'episodes']
  )
}}

with source_data as (
    select * from {{ source('bronze_rss', 'rss_episodes') }}
),

cleaned as (
    select
        {{ dbt_utils.generate_surrogate_key(['episode_id']) }} as episode_key,
        episode_id,
        -- Surrogate key matches stg_rss__podcasts / dim_podcast (both keyed on feed_url)
        {{ dbt_utils.generate_surrogate_key(['feed_url']) }} as podcast_id,
        feed_url,
        trim(title) as episode_title,
        trim(description) as episode_description,
        duration_seconds,
        round(duration_seconds / 60.0, 1) as duration_minutes,
        episode_number,
        published_date,
        audio_url,
        ingestion_timestamp,
        source_type,
        case
            when title is null or trim(title) = '' then false
            when episode_id is null then false
            else true
        end as is_valid_record
    from source_data
    where ingestion_timestamp >= '{{ var("start_date") }}'
)

select * from cleaned where is_valid_record = true
