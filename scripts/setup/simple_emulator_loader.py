#!/usr/bin/env python3
"""
Simple BigQuery Emulator Data Loader
Uses direct SQL inserts instead of the BigQuery client upload methods
"""

import os
import requests
import json
from datetime import datetime, timedelta
import random

def execute_sql(sql_query, project_id="podcastflow-analytics"):
    """Execute SQL query against BigQuery emulator"""
    emulator_host = os.getenv('BIGQUERY_EMULATOR_HOST', 'bigquery-emulator')
    emulator_port = os.getenv('BIGQUERY_EMULATOR_PORT', '9050')
    
    url = f"http://{emulator_host}:{emulator_port}/bigquery/v2/projects/{project_id}/queries"
    
    payload = {
        "query": sql_query,
        "useLegacySql": False
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ SQL Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def create_tables():
    """Create the bronze layer tables"""
    print("🏗️  Creating bronze layer tables...")
    
    # Create RSS feeds table
    rss_feeds_sql = """
    CREATE TABLE IF NOT EXISTS `podcastflow-analytics.bronze.rss_feeds` (
        feed_url STRING,
        raw_content STRING,
        ingestion_timestamp TIMESTAMP,
        podcast_title STRING,
        episode_count INT64
    )
    """
    
    # Create listening events table
    listening_events_sql = """
    CREATE TABLE IF NOT EXISTS `podcastflow-analytics.bronze.listening_events` (
        event_id STRING,
        user_id STRING,
        episode_id STRING,
        event_type STRING,
        completion_percentage FLOAT64,
        event_timestamp TIMESTAMP,
        platform STRING,
        device_type STRING
    )
    """
    
    # Create social mentions table
    social_mentions_sql = """
    CREATE TABLE IF NOT EXISTS `podcastflow-analytics.bronze.social_mentions` (
        mention_id STRING,
        podcast_id STRING,
        platform STRING,
        mention_text STRING,
        sentiment_score FLOAT64,
        mention_timestamp TIMESTAMP,
        follower_count INT64
    )
    """
    
    tables = [
        ("rss_feeds", rss_feeds_sql),
        ("listening_events", listening_events_sql),
        ("social_mentions", social_mentions_sql)
    ]
    
    for table_name, sql in tables:
        print(f"  Creating {table_name}...")
        result = execute_sql(sql)
        if result:
            print(f"  ✅ {table_name} created successfully")
        else:
            print(f"  ❌ Failed to create {table_name}")

def load_rss_feeds():
    """Load sample RSS feeds data"""
    print("📡 Loading RSS feeds data...")
    
    sql = """
    INSERT INTO `podcastflow-analytics.bronze.rss_feeds` 
    (feed_url, raw_content, ingestion_timestamp, podcast_title, episode_count)
    VALUES
    ('https://feeds.example.com/tech-talk', 
     '<?xml version="1.0"?><rss><channel><title>Tech Talk Podcast</title></channel></rss>',
     CURRENT_TIMESTAMP(), 'Tech Talk Podcast', 25),
    ('https://feeds.example.com/business-insights',
     '<?xml version="1.0"?><rss><channel><title>Business Insights</title></channel></rss>',
     CURRENT_TIMESTAMP(), 'Business Insights', 18),
    ('https://feeds.example.com/data-science',
     '<?xml version="1.0"?><rss><channel><title>Data Science Deep Dive</title></channel></rss>',
     CURRENT_TIMESTAMP(), 'Data Science Deep Dive', 12),
    ('https://feeds.example.com/startup-stories',
     '<?xml version="1.0"?><rss><channel><title>Startup Stories</title></channel></rss>',
     CURRENT_TIMESTAMP(), 'Startup Stories', 15)
    """
    
    result = execute_sql(sql)
    if result:
        print("✅ RSS feeds data loaded successfully")
    else:
        print("❌ Failed to load RSS feeds data")

def load_listening_events():
    """Load sample listening events data"""
    print("🎵 Loading listening events data...")
    
    # Generate some sample events
    events = []
    for i in range(50):  # Smaller sample for emulator
        events.append(f"""
        ('evt_{i:04d}', 'user_{random.randint(1, 20):03d}', 
         'ep_tech_{random.randint(1, 5):02d}', 'play',
         {random.uniform(10, 95):.2f}, 
         TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {random.randint(1, 168)} HOUR),
         '{random.choice(['spotify', 'apple_podcasts', 'google_podcasts'])}',
         '{random.choice(['mobile', 'desktop'])}')
        """)
    
    sql = f"""
    INSERT INTO `podcastflow-analytics.bronze.listening_events`
    (event_id, user_id, episode_id, event_type, completion_percentage, 
     event_timestamp, platform, device_type)
    VALUES {','.join(events)}
    """
    
    result = execute_sql(sql)
    if result:
        print("✅ Listening events data loaded successfully")
    else:
        print("❌ Failed to load listening events data")

def load_social_mentions():
    """Load sample social mentions data"""
    print("💬 Loading social mentions data...")
    
    mentions = []
    for i in range(20):  # Small sample for emulator
        mentions.append(f"""
        ('mention_{i:04d}', 'tech_talk_podcast', 
         '{random.choice(['twitter', 'linkedin', 'reddit'])}',
         'Great podcast episode! Really enjoyed it.',
         {random.uniform(0.6, 0.9):.3f},
         TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {random.randint(1, 168)} HOUR),
         {random.randint(100, 5000)})
        """)
    
    sql = f"""
    INSERT INTO `podcastflow-analytics.bronze.social_mentions`
    (mention_id, podcast_id, platform, mention_text, sentiment_score,
     mention_timestamp, follower_count)
    VALUES {','.join(mentions)}
    """
    
    result = execute_sql(sql)
    if result:
        print("✅ Social mentions data loaded successfully")
    else:
        print("❌ Failed to load social mentions data")

def verify_data():
    """Verify that data was loaded correctly"""
    print("🔍 Verifying loaded data...")
    
    tables = [
        "podcastflow-analytics.bronze.rss_feeds",
        "podcastflow-analytics.bronze.listening_events", 
        "podcastflow-analytics.bronze.social_mentions"
    ]
    
    for table in tables:
        sql = f"SELECT COUNT(*) as count FROM `{table}`"
        result = execute_sql(sql)
        if result and 'rows' in result:
            count = result['rows'][0]['f'][0]['v']
            print(f"  ✅ {table}: {count} records")
        else:
            print(f"  ❌ {table}: Failed to verify")

def main():
    print("🎧 PodcastFlow Analytics - Simple Emulator Data Loader")
    print("=" * 60)
    
    # Create tables
    create_tables()
    
    # Load sample data
    load_rss_feeds()
    load_listening_events()
    load_social_mentions()
    
    # Verify data
    verify_data()
    
    print("\n🎉 Sample data loading complete!")
    print("📊 Ready for dbt transformations and dashboard queries")

if __name__ == "__main__":
    main() 