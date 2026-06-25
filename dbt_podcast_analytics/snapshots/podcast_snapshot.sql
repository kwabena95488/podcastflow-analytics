{% snapshot podcast_snapshot %}
{{
  config(
    target_schema='gold',
    unique_key='podcast_id',
    strategy='check',
    check_cols=['podcast_title', 'category', 'author', 'total_episodes', 'explicit_flag']
  )
}}

-- SCD Type 2 history of podcast attributes. On each run, dbt records a new version
-- row whenever any of check_cols changes for a given podcast_id.
select
    podcast_id,
    feed_url,
    podcast_title,
    category,
    author,
    total_episodes,
    explicit_flag
from {{ ref('stg_rss__podcasts') }}

{% endsnapshot %}
