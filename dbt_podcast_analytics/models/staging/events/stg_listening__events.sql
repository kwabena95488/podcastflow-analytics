{{
  config(
    materialized='view',
    tags=['staging', 'events']
  )
}}

with source_data as (
    select * from {{ source('bronze_events', 'listening_events') }}
),

cleaned as (
    select
        event_id,
        user_id,
        episode_id,
        {{ dbt_utils.generate_surrogate_key(['episode_id']) }} as episode_key,
        session_id,
        event_type,
        `timestamp` as event_timestamp,
        position_seconds,
        completion_percentage,
        completion_percentage / 100.0 as completion_fraction,
        platform,
        device_type,
        location_country,
        ingestion_timestamp
    from source_data
    where ingestion_timestamp >= '{{ var("start_date") }}'
)

select * from cleaned
