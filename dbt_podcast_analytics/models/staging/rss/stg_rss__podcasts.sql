{{
  config(
    materialized='view',
    tags=['staging', 'rss', 'podcasts']
  )
}}

with source_data as (
    select * from {{ source('bronze_rss', 'rss_feeds') }}
),

cleaned_data as (
    select
        -- Primary identifiers
        {{ dbt_utils.generate_surrogate_key(['feed_url']) }} as podcast_id,
        feed_url,
        
        -- Podcast metadata
        trim(title) as podcast_title,
        trim(description) as podcast_description,
        
        -- Extract language from RSS if available (default to 'en')
        coalesce(
            regexp_extract(raw_content, r'<language>([^<]+)</language>', 1),
            'en'
        ) as language,
        
        -- Extract category from RSS
        coalesce(
            regexp_extract(raw_content, r'<category>([^<]+)</category>', 1),
            'General'
        ) as category,
        
        -- Extract author/creator
        coalesce(
            regexp_extract(raw_content, r'<itunes:author>([^<]+)</itunes:author>', 1),
            regexp_extract(raw_content, r'<author>([^<]+)</author>', 1),
            'Unknown'
        ) as author,
        
        -- Extract website URL
        regexp_extract(raw_content, r'<link>([^<]+)</link>', 1) as website_url,
        
        -- Extract image URL
        coalesce(
            regexp_extract(raw_content, r'<itunes:image href="([^"]+)"', 1),
            regexp_extract(raw_content, r'<image><url>([^<]+)</url></image>', 1)
        ) as image_url,
        
        -- Extract explicit flag
        case 
            when regexp_extract(raw_content, r'<itunes:explicit>([^<]+)</itunes:explicit>', 1) = 'true' then true
            when regexp_extract(raw_content, r'<itunes:explicit>([^<]+)</itunes:explicit>', 1) = 'yes' then true
            else false
        end as explicit_flag,
        
        -- Extract episode count if available
        cast(
            regexp_extract(raw_content, r'<itunes:episode>(\d+)</itunes:episode>', 1) as integer
        ) as total_episodes,
        
        -- Metadata fields
        published_date,
        ingestion_timestamp,
        source_type,
        
        -- Data quality indicators
        case 
            when title is null or trim(title) = '' then false
            when feed_url is null or trim(feed_url) = '' then false
            else true
        end as is_valid_record,
        
        -- Calculate content richness score
        case 
            when description is not null and length(trim(description)) > 100 then 3
            when description is not null and length(trim(description)) > 50 then 2
            when description is not null and length(trim(description)) > 0 then 1
            else 0
        end as content_richness_score
        
    from source_data
    where ingestion_timestamp >= '{{ var("start_date") }}'
),

final as (
    select
        podcast_id,
        feed_url,
        podcast_title,
        podcast_description,
        language,
        category,
        author,
        website_url,
        image_url,
        explicit_flag,
        total_episodes,
        published_date,
        ingestion_timestamp,
        source_type,
        is_valid_record,
        content_richness_score,
        
        -- Add row quality hash for change detection
        {{ dbt_utils.generate_surrogate_key([
            'podcast_title', 
            'podcast_description', 
            'category', 
            'author'
        ]) }} as content_hash,
        
        -- Add processing metadata
        current_timestamp as processed_at,
        '{{ this.name }}' as processed_by
        
    from cleaned_data
    where is_valid_record = true
)

select * from final 