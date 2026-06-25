#!/usr/bin/env python3
"""
RSS Feed Ingestion System
Automatically pulls and processes real podcast RSS feeds
"""

import os
import requests
import feedparser
import json
from datetime import datetime, timezone
from urllib.parse import urlparse
import hashlib
import time

def execute_sql(sql_query, project_id="podcastflow-analytics"):
    """Execute SQL query against BigQuery emulator"""
    emulator_host = os.getenv('BIGQUERY_EMULATOR_HOST', 'localhost')
    emulator_port = os.getenv('BIGQUERY_EMULATOR_PORT', '9050')
    
    # Clean host URL
    if emulator_host.startswith('http://'):
        emulator_host = emulator_host.replace('http://', '')
    
    url = f"http://{emulator_host}:{emulator_port}/bigquery/v2/projects/{project_id}/queries"
    
    payload = {
        "query": sql_query,
        "useLegacySql": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ SQL Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

def fetch_rss_feed(feed_url, timeout=30):
    """Fetch and parse RSS feed"""
    try:
        print(f"📡 Fetching: {feed_url}")
        
        # Set user agent to avoid blocking
        headers = {
            'User-Agent': 'PodcastFlow Analytics Bot 1.0 (https://podcastflow.analytics)'
        }
        
        response = requests.get(feed_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Parse the feed
        feed = feedparser.parse(response.content)
        
        if feed.bozo:
            print(f"⚠️  Warning: Feed has parsing issues: {feed_url}")
        
        return feed, response.content
        
    except requests.RequestException as e:
        print(f"❌ Failed to fetch {feed_url}: {e}")
        return None, None
    except Exception as e:
        print(f"❌ Error parsing {feed_url}: {e}")
        return None, None

def extract_podcast_info(feed, raw_content, feed_url):
    """Extract podcast information from parsed feed"""
    if not feed or not hasattr(feed, 'feed'):
        return None
    
    try:
        podcast_info = {
            'feed_url': feed_url,
            'title': getattr(feed.feed, 'title', 'Unknown Podcast'),
            'description': getattr(feed.feed, 'description', ''),
            'author': getattr(feed.feed, 'author', getattr(feed.feed, 'managingEditor', '')),
            'language': getattr(feed.feed, 'language', 'en'),
            'category': '',
            'episode_count': len(feed.entries),
            'last_updated': getattr(feed.feed, 'updated', ''),
            'image_url': '',
            'website_url': getattr(feed.feed, 'link', ''),
            'raw_content': raw_content.decode('utf-8', errors='ignore')[:50000],  # Limit size
            'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Extract category if available
        if hasattr(feed.feed, 'tags'):
            podcast_info['category'] = ', '.join([tag.term for tag in feed.feed.tags[:3]])
        elif hasattr(feed.feed, 'itunes_category'):
            podcast_info['category'] = feed.feed.itunes_category
        
        # Extract image URL
        if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
            podcast_info['image_url'] = feed.feed.image.href
        elif hasattr(feed.feed, 'itunes_image'):
            podcast_info['image_url'] = feed.feed.itunes_image
        
        return podcast_info
        
    except Exception as e:
        print(f"❌ Error extracting podcast info: {e}")
        return None

def extract_episodes(feed, feed_url):
    """Extract episode information from parsed feed"""
    if not feed or not hasattr(feed, 'entries'):
        return []
    
    episodes = []
    
    for i, entry in enumerate(feed.entries[:50]):  # Limit to recent 50 episodes
        try:
            episode = {
                'episode_id': hashlib.md5(f"{feed_url}_{entry.get('id', i)}".encode()).hexdigest(),
                'podcast_feed_url': feed_url,
                'title': entry.get('title', f'Episode {i+1}'),
                'description': entry.get('description', entry.get('summary', '')),
                'pub_date': entry.get('published', ''),
                'duration': entry.get('itunes_duration', ''),
                'episode_number': entry.get('itunes_episode', i+1),
                'season_number': entry.get('itunes_season', 1),
                'audio_url': '',
                'file_size': 0,
                'ingestion_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Extract audio URL and file size
            if hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    if 'audio' in enclosure.get('type', '').lower():
                        episode['audio_url'] = enclosure.get('href', '')
                        episode['file_size'] = int(enclosure.get('length', 0))
                        break
            
            episodes.append(episode)
            
        except Exception as e:
            print(f"⚠️  Error extracting episode {i}: {e}")
            continue
    
    return episodes

def store_podcast_data(podcast_info):
    """Store podcast information in the database"""
    try:
        # Escape single quotes in strings
        def escape_sql(value):
            if isinstance(value, str):
                return value.replace("'", "''")
            return str(value)
        
        sql = f"""
        INSERT INTO `podcastflow-analytics.bronze.rss_feeds` 
        (feed_url, raw_content, ingestion_timestamp, podcast_title, episode_count,
         description, author, language, category, last_updated, image_url, website_url)
        VALUES
        ('{escape_sql(podcast_info['feed_url'])}',
         '{escape_sql(podcast_info['raw_content'])}',
         TIMESTAMP('{podcast_info['ingestion_timestamp']}'),
         '{escape_sql(podcast_info['title'])}',
         {podcast_info['episode_count']},
         '{escape_sql(podcast_info['description'])}',
         '{escape_sql(podcast_info['author'])}',
         '{escape_sql(podcast_info['language'])}',
         '{escape_sql(podcast_info['category'])}',
         '{escape_sql(podcast_info['last_updated'])}',
         '{escape_sql(podcast_info['image_url'])}',
         '{escape_sql(podcast_info['website_url'])}')
        """
        
        result = execute_sql(sql)
        if result:
            print(f"✅ Stored podcast: {podcast_info['title']}")
            return True
        else:
            print(f"❌ Failed to store podcast: {podcast_info['title']}")
            return False
            
    except Exception as e:
        print(f"❌ Error storing podcast data: {e}")
        return False

def store_episodes_data(episodes):
    """Store episode information in the database"""
    if not episodes:
        return True
    
    try:
        # Create episodes table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `podcastflow-analytics.bronze.episodes` (
            episode_id STRING,
            podcast_feed_url STRING,
            title STRING,
            description STRING,
            pub_date STRING,
            duration STRING,
            episode_number INT64,
            season_number INT64,
            audio_url STRING,
            file_size INT64,
            ingestion_timestamp TIMESTAMP
        )
        """
        execute_sql(create_table_sql)
        
        # Prepare batch insert
        def escape_sql(value):
            if isinstance(value, str):
                return value.replace("'", "''")
            return str(value)
        
        values = []
        for episode in episodes:
            values.append(f"""
            ('{escape_sql(episode['episode_id'])}',
             '{escape_sql(episode['podcast_feed_url'])}',
             '{escape_sql(episode['title'])}',
             '{escape_sql(episode['description'])}',
             '{escape_sql(episode['pub_date'])}',
             '{escape_sql(episode['duration'])}',
             {episode['episode_number']},
             {episode['season_number']},
             '{escape_sql(episode['audio_url'])}',
             {episode['file_size']},
             TIMESTAMP('{episode['ingestion_timestamp']}'))
            """)
        
        sql = f"""
        INSERT INTO `podcastflow-analytics.bronze.episodes`
        (episode_id, podcast_feed_url, title, description, pub_date, duration,
         episode_number, season_number, audio_url, file_size, ingestion_timestamp)
        VALUES {','.join(values)}
        """
        
        result = execute_sql(sql)
        if result:
            print(f"✅ Stored {len(episodes)} episodes")
            return True
        else:
            print(f"❌ Failed to store episodes")
            return False
            
    except Exception as e:
        print(f"❌ Error storing episodes: {e}")
        return False

def ingest_podcast_feed(feed_url):
    """Complete ingestion process for a single podcast feed"""
    print(f"\n🎧 Processing: {feed_url}")
    
    # Fetch and parse feed
    feed, raw_content = fetch_rss_feed(feed_url)
    if not feed:
        return False
    
    # Extract podcast information
    podcast_info = extract_podcast_info(feed, raw_content, feed_url)
    if not podcast_info:
        return False
    
    # Extract episodes
    episodes = extract_episodes(feed, feed_url)
    
    # Store data
    podcast_stored = store_podcast_data(podcast_info)
    episodes_stored = store_episodes_data(episodes) if episodes else True
    
    if podcast_stored and episodes_stored:
        print(f"✅ Successfully ingested: {podcast_info['title']} ({len(episodes)} episodes)")
        return True
    else:
        print(f"❌ Failed to ingest: {feed_url}")
        return False

def main():
    """Main ingestion process"""
    print("🎧 PodcastFlow Analytics - RSS Feed Ingestion")
    print("=" * 55)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Popular podcast RSS feeds for testing
    test_feeds = [
        "https://feeds.simplecast.com/54nAGcIl",  # The Daily (NY Times)
        "https://feeds.megaphone.fm/HSW8285310456",  # Stuff You Should Know
        "https://feeds.npr.org/510208/podcast.xml",  # NPR Up First
        "https://feeds.megaphone.fm/WWO3519750118",  # Conan O'Brien Needs a Friend
        "https://rss.cnn.com/rss/cnn_topstories.rss"  # CNN Top Stories (for testing)
    ]
    
    success_count = 0
    
    for feed_url in test_feeds:
        try:
            if ingest_podcast_feed(feed_url):
                success_count += 1
            time.sleep(2)  # Be respectful to servers
        except Exception as e:
            print(f"❌ Unexpected error with {feed_url}: {e}")
    
    print(f"\n🎉 RSS Ingestion Complete!")
    print(f"✅ Successfully processed: {success_count}/{len(test_feeds)} feeds")
    
    # Verify data
    verification_sql = """
    SELECT 
        COUNT(*) as podcast_count,
        SUM(episode_count) as total_episodes
    FROM `podcastflow-analytics.bronze.rss_feeds`
    WHERE ingestion_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    """
    
    result = execute_sql(verification_sql)
    if result and 'rows' in result:
        row = result['rows'][0]['f']
        podcast_count = row[0]['v']
        total_episodes = row[1]['v']
        print(f"📊 New data: {podcast_count} podcasts, {total_episodes} episodes")

if __name__ == "__main__":
    main() 