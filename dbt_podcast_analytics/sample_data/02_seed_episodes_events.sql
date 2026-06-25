-- Synthetic RSS episodes: 5 per podcast (20 total), derived from the 4 seeded feeds.
CREATE OR REPLACE TABLE `your-gcp-project.bronze.rss_episodes` AS
WITH feeds AS (
  SELECT feed_url, title AS podcast_title FROM `your-gcp-project.bronze.rss_feeds`
),
ep AS (
  SELECT f.feed_url, f.podcast_title, n AS episode_number,
         REGEXP_REPLACE(f.feed_url, r'^https?://[^/]+/', '') AS slug
  FROM feeds f, UNNEST(GENERATE_ARRAY(1, 5)) AS n
)
SELECT
  CONCAT(slug, '-ep-', CAST(episode_number AS STRING)) AS episode_id,
  feed_url,
  CONCAT(podcast_title, ' — Episode ', CAST(episode_number AS STRING)) AS title,
  CONCAT('Episode ', CAST(episode_number AS STRING), ' of ', podcast_title,
         '. In-depth discussion, interviews, and analysis for listeners.') AS description,
  -- duration 20-75 min, deterministic from a fingerprint
  1200 + MOD(ABS(FARM_FINGERPRINT(CONCAT(feed_url, CAST(episode_number AS STRING)))), 3300) AS duration_seconds,
  DATE_ADD(DATE '2024-01-15', INTERVAL episode_number * 7 DAY) AS published_date,
  episode_number,
  CONCAT('https://cdn.example.com/', slug, '/ep', CAST(episode_number AS STRING), '.mp3') AS audio_url,
  TIMESTAMP_ADD(TIMESTAMP '2024-01-15 12:00:00 UTC', INTERVAL episode_number DAY) AS ingestion_timestamp,
  'rss' AS source_type
FROM ep;

-- Synthetic listening events: 12 per episode (240 total).
CREATE OR REPLACE TABLE `your-gcp-project.bronze.listening_events` AS
WITH eps AS (
  SELECT episode_id, duration_seconds FROM `your-gcp-project.bronze.rss_episodes`
),
ev AS (
  SELECT e.episode_id, e.duration_seconds, n AS evnum,
         ABS(FARM_FINGERPRINT(CONCAT(e.episode_id, '#', CAST(n AS STRING)))) AS h
  FROM eps e, UNNEST(GENERATE_ARRAY(1, 12)) AS n
)
SELECT
  CONCAT(episode_id, '-evt-', CAST(evnum AS STRING)) AS event_id,
  CONCAT('user_', CAST(MOD(h, 60) AS STRING)) AS user_id,
  episode_id,
  CONCAT('sess_', CAST(MOD(h, 200) AS STRING)) AS session_id,
  CASE MOD(h, 5)
    WHEN 0 THEN 'play' WHEN 1 THEN 'pause' WHEN 2 THEN 'skip'
    WHEN 3 THEN 'complete' ELSE 'download' END AS event_type,
  TIMESTAMP_ADD(TIMESTAMP '2024-02-01 00:00:00 UTC', INTERVAL MOD(h, 1200) HOUR) AS `timestamp`,
  MOD(h, duration_seconds) AS position_seconds,
  MOD(h, 101) AS completion_percentage,
  CASE MOD(h, 4)
    WHEN 0 THEN 'ios' WHEN 1 THEN 'android' WHEN 2 THEN 'web' ELSE 'smart_speaker' END AS platform,
  CASE MOD(h, 4)
    WHEN 0 THEN 'mobile' WHEN 1 THEN 'desktop' WHEN 2 THEN 'tablet' ELSE 'speaker' END AS device_type,
  CASE MOD(h, 5)
    WHEN 0 THEN 'US' WHEN 1 THEN 'GB' WHEN 2 THEN 'CA' WHEN 3 THEN 'AU' ELSE 'DE' END AS location_country,
  TIMESTAMP_ADD(TIMESTAMP '2024-02-01 00:00:00 UTC', INTERVAL MOD(h, 1200) HOUR) AS ingestion_timestamp
FROM ev;
