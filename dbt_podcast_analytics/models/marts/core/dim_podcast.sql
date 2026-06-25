{{
  config(
    materialized='table',
    schema='gold',
    tags=['marts', 'core', 'dimensions'],
    indexes=[
      {'columns': ['podcast_id'], 'unique': True},
      {'columns': ['is_current']},
      {'columns': ['category']},
      {'columns': ['author']}
    ]
  )
}}

with source_data as (
    -- Union data from multiple sources
    select 
        podcast_id,
        podcast_title,
        podcast_description,
        category,
        language,
        author,
        website_url,
        feed_url as rss_feed_url,
        image_url,
        explicit_flag,
        total_episodes,
        'rss' as source_system,
        ingestion_timestamp as source_updated_at
    from {{ ref('stg_rss__podcasts') }}

    {# TODO (Workstream 1, if Spotify/Apple sources are added): union the Spotify and Apple
       staging models here. Kept as a JINJA comment, not a SQL `--` comment, so dbt does not
       register a dependency on models that don't exist yet. RSS-only is the honest scope today.
       union all  select ... from ref('stg_spotify__podcasts')
       union all  select ... from ref('stg_apple__podcasts') #}
),

-- Deduplicate and select best record per podcast
deduplicated as (
    select 
        *,
        row_number() over (
            partition by podcast_id 
            order by source_updated_at desc, 
                     case when source_system = 'rss' then 1 
                          when source_system = 'spotify' then 2 
                          when source_system = 'apple' then 3 
                          else 4 end
        ) as rn
    from source_data
),

current_records as (
    select 
        podcast_id,
        podcast_title,
        podcast_description,
        category,
        language,
        author,
        website_url,
        rss_feed_url,
        image_url,
        explicit_flag,
        total_episodes,
        source_system,
        source_updated_at
    from deduplicated 
    where rn = 1
),

-- Get existing records for SCD Type 2 comparison
{% if is_incremental() %}
existing_records as (
    select 
        podcast_key,
        podcast_id,
        podcast_title,
        podcast_description,
        category,
        language,
        author,
        website_url,
        rss_feed_url,
        image_url,
        explicit_flag,
        total_episodes,
        source_system,
        effective_date,
        expiry_date,
        is_current,
        created_timestamp,
        updated_timestamp,
        -- Create hash of SCD attributes for comparison
        {{ dbt_utils.generate_surrogate_key([
            'podcast_title',
            'podcast_description', 
            'category',
            'author',
            'website_url',
            'explicit_flag'
        ]) }} as scd_hash
    from {{ this }}
    where is_current = true
),

-- Identify changed records
changed_records as (
    select 
        c.*,
        e.podcast_key,
        e.scd_hash as existing_scd_hash,
        {{ dbt_utils.generate_surrogate_key([
            'c.podcast_title',
            'c.podcast_description', 
            'c.category',
            'c.author',
            'c.website_url',
            'c.explicit_flag'
        ]) }} as new_scd_hash,
        case when e.podcast_id is null then 'INSERT'
             when e.scd_hash != {{ dbt_utils.generate_surrogate_key([
                'c.podcast_title',
                'c.podcast_description', 
                'c.category',
                'c.author',
                'c.website_url',
                'c.explicit_flag'
             ]) }} then 'UPDATE'
             else 'NO_CHANGE'
        end as change_type
    from current_records c
    left join existing_records e on c.podcast_id = e.podcast_id
),
{% endif %}

final as (
    select
        {% if is_incremental() %}
        case 
            when change_type = 'INSERT' then {{ dbt_utils.generate_surrogate_key(['podcast_id', 'current_timestamp']) }}
            when change_type = 'UPDATE' then {{ dbt_utils.generate_surrogate_key(['podcast_id', 'current_timestamp']) }}
            else podcast_key
        end as podcast_key,
        {% else %}
        {{ dbt_utils.generate_surrogate_key(['podcast_id', 'current_timestamp']) }} as podcast_key,
        {% endif %}
        
        podcast_id,
        podcast_title,
        podcast_description,
        category,
        language,
        author,
        website_url,
        rss_feed_url,
        image_url,
        explicit_flag,
        total_episodes,
        
        -- SCD Type 2 attributes
        {% if is_incremental() %}
        case 
            when change_type in ('INSERT', 'UPDATE') then current_date
            else effective_date
        end as effective_date,
        {% else %}
        current_date as effective_date,
        {% endif %}
        
        date('9999-12-31') as expiry_date,
        true as is_current,
        
        -- Metadata
        {% if is_incremental() %}
        case 
            when change_type = 'INSERT' then current_timestamp
            else created_timestamp
        end as created_timestamp,
        {% else %}
        current_timestamp as created_timestamp,
        {% endif %}
        
        current_timestamp as updated_timestamp,
        source_system,
        source_updated_at
        
    from 
    {% if is_incremental() %}
        changed_records
    where change_type in ('INSERT', 'UPDATE')
    {% else %}
        current_records
    {% endif %}
)

{% if is_incremental() %}
-- First, expire old records that have changed
select 
    podcast_key,
    podcast_id,
    podcast_title,
    podcast_description,
    category,
    language,
    author,
    website_url,
    rss_feed_url,
    image_url,
    explicit_flag,
    total_episodes,
    effective_date,
    current_date as expiry_date,  -- Expire the old record
    false as is_current,          -- Mark as not current
    created_timestamp,
    current_timestamp as updated_timestamp,
    source_system,
    source_updated_at
from existing_records e
where exists (
    select 1 from changed_records c 
    where c.podcast_id = e.podcast_id 
    and c.change_type = 'UPDATE'
)

union all
{% endif %}

-- Insert new/updated records
select * from final 