#!/usr/bin/env python3
"""
Social Media Ingestion System
Pulls podcast mentions from various social media platforms
"""

import os
import requests
import json
from datetime import datetime, timezone, timedelta
import hashlib
import time
import random
from urllib.parse import quote_plus

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

def get_podcast_titles():
    """Get podcast titles from database for mention tracking"""
    sql = """
    SELECT DISTINCT podcast_title
    FROM `podcastflow-analytics.bronze.rss_feeds`
    WHERE podcast_title IS NOT NULL
    """
    
    result = execute_sql(sql)
    if result and 'rows' in result:
        return [row['f'][0]['v'] for row in result['rows']]
    return []

def simulate_twitter_mentions(podcast_titles, limit=20):
    """Simulate Twitter/X mentions (using mock data for demo)"""
    print("🐦 Simulating Twitter/X mentions...")
    
    mentions = []
    sentiment_phrases = {
        'positive': [
            "Love this podcast! Great episode on {}",
            "Just listened to {} - absolutely brilliant!",
            "Can't stop listening to {}. Highly recommended!",
            "{} is my new favorite podcast. Amazing content!",
            "Another fantastic episode from {}. Keep it up!"
        ],
        'neutral': [
            "Listening to {} right now",
            "New episode of {} is out",
            "{} covers interesting topics",
            "Just discovered {}",
            "Episode about {} was informative"
        ],
        'negative': [
            "{} was disappointing this week",
            "Not sure about the latest {} episode",
            "{} could be better",
            "Mixed feelings about {}",
            "Expected more from {}"
        ]
    }
    
    for i in range(limit):
        # Choose random podcast and sentiment
        podcast = random.choice(podcast_titles) if podcast_titles else f"Sample Podcast {i%3 + 1}"
        sentiment_type = random.choices(['positive', 'neutral', 'negative'], 
                                      weights=[0.6, 0.3, 0.1])[0]
        
        # Generate mention text
        template = random.choice(sentiment_phrases[sentiment_type])
        mention_text = template.format(podcast)
        
        # Generate sentiment score
        if sentiment_type == 'positive':
            sentiment_score = random.uniform(0.7, 1.0)
        elif sentiment_type == 'neutral':
            sentiment_score = random.uniform(0.4, 0.7)
        else:
            sentiment_score = random.uniform(0.0, 0.4)
        
        mention = {
            'mention_id': f"twitter_{hashlib.md5(f'{mention_text}_{i}'.encode()).hexdigest()[:12]}",
            'podcast_id': podcast.lower().replace(' ', '_'),
            'platform': 'twitter',
            'mention_text': mention_text,
            'sentiment_score': round(sentiment_score, 3),
            'mention_timestamp': (datetime.now(timezone.utc) - 
                                timedelta(hours=random.randint(1, 168))).isoformat(),
            'author_username': f"user_{random.randint(1000, 9999)}",
            'follower_count': random.randint(50, 10000),
            'retweet_count': random.randint(0, 100),
            'like_count': random.randint(0, 500),
            'url': f"https://twitter.com/user_{random.randint(1000, 9999)}/status/{random.randint(1000000000000000000, 9999999999999999999)}"
        }
        
        mentions.append(mention)
    
    return mentions

def simulate_reddit_mentions(podcast_titles, limit=15):
    """Simulate Reddit mentions"""
    print("🔴 Simulating Reddit mentions...")
    
    mentions = []
    subreddits = ['podcasts', 'audio', 'entertainment', 'technology', 'business', 'comedy']
    
    for i in range(limit):
        podcast = random.choice(podcast_titles) if podcast_titles else f"Sample Podcast {i%3 + 1}"
        subreddit = random.choice(subreddits)
        
        # Reddit tends to have longer, more detailed discussions
        reddit_templates = [
            f"Just finished listening to {podcast}. What did everyone think about the latest episode?",
            f"Has anyone else been following {podcast}? The quality has really improved lately.",
            f"Looking for podcast recommendations similar to {podcast}. Any suggestions?",
            f"The host of {podcast} made some interesting points about [topic]. Thoughts?",
            f"{podcast} episode discussion thread - spoilers ahead!"
        ]
        
        mention_text = random.choice(reddit_templates)
        sentiment_score = random.uniform(0.3, 0.9)  # Reddit tends to be more balanced
        
        mention = {
            'mention_id': f"reddit_{hashlib.md5(f'{mention_text}_{i}'.encode()).hexdigest()[:12]}",
            'podcast_id': podcast.lower().replace(' ', '_'),
            'platform': 'reddit',
            'mention_text': mention_text,
            'sentiment_score': round(sentiment_score, 3),
            'mention_timestamp': (datetime.now(timezone.utc) - 
                                timedelta(hours=random.randint(1, 168))).isoformat(),
            'author_username': f"u/reddit_user_{random.randint(100, 999)}",
            'follower_count': random.randint(10, 50000),  # Reddit karma
            'retweet_count': 0,  # No retweets on Reddit
            'like_count': random.randint(1, 1000),  # Upvotes
            'url': f"https://reddit.com/r/{subreddit}/comments/{random.randint(1000000, 9999999)}/discussion/"
        }
        
        mentions.append(mention)
    
    return mentions

def simulate_linkedin_mentions(podcast_titles, limit=10):
    """Simulate LinkedIn mentions (more professional tone)"""
    print("💼 Simulating LinkedIn mentions...")
    
    mentions = []
    
    for i in range(limit):
        podcast = random.choice(podcast_titles) if podcast_titles else f"Sample Podcast {i%3 + 1}"
        
        linkedin_templates = [
            f"Great insights from the latest {podcast} episode on industry trends. Worth a listen for professionals in our field.",
            f"The {podcast} interview with [Guest] provided valuable perspectives on leadership and innovation.",
            f"Sharing this excellent {podcast} episode that discusses career development and professional growth.",
            f"The business strategies discussed in {podcast} are highly relevant for our industry. Thoughts?",
            f"Professional development recommendation: {podcast} offers practical advice for career advancement."
        ]
        
        mention_text = random.choice(linkedin_templates)
        sentiment_score = random.uniform(0.6, 0.95)  # LinkedIn tends to be more positive/professional
        
        mention = {
            'mention_id': f"linkedin_{hashlib.md5(f'{mention_text}_{i}'.encode()).hexdigest()[:12]}",
            'podcast_id': podcast.lower().replace(' ', '_'),
            'platform': 'linkedin',
            'mention_text': mention_text,
            'sentiment_score': round(sentiment_score, 3),
            'mention_timestamp': (datetime.now(timezone.utc) - 
                                timedelta(hours=random.randint(1, 168))).isoformat(),
            'author_username': f"Professional User {random.randint(100, 999)}",
            'follower_count': random.randint(100, 5000),  # Professional connections
            'retweet_count': random.randint(0, 20),  # Shares
            'like_count': random.randint(5, 200),
            'url': f"https://linkedin.com/posts/user{random.randint(1000, 9999)}_activity-{random.randint(1000000000000000000, 9999999999999999999)}"
        }
        
        mentions.append(mention)
    
    return mentions

def store_social_mentions(mentions):
    """Store social media mentions in the database"""
    if not mentions:
        return True
    
    try:
        # Escape single quotes in strings
        def escape_sql(value):
            if isinstance(value, str):
                return value.replace("'", "''")
            return str(value)
        
        values = []
        for mention in mentions:
            values.append(f"""
            ('{escape_sql(mention['mention_id'])}',
             '{escape_sql(mention['podcast_id'])}',
             '{escape_sql(mention['platform'])}',
             '{escape_sql(mention['mention_text'])}',
             {mention['sentiment_score']},
             TIMESTAMP('{mention['mention_timestamp']}'),
             '{escape_sql(mention['author_username'])}',
             {mention['follower_count']},
             {mention['retweet_count']},
             {mention['like_count']},
             '{escape_sql(mention['url'])}')
            """)
        
        # Update table schema to include new fields
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `podcastflow-analytics.bronze.social_mentions_extended` (
            mention_id STRING,
            podcast_id STRING,
            platform STRING,
            mention_text STRING,
            sentiment_score FLOAT64,
            mention_timestamp TIMESTAMP,
            author_username STRING,
            follower_count INT64,
            retweet_count INT64,
            like_count INT64,
            url STRING
        )
        """
        execute_sql(create_table_sql)
        
        sql = f"""
        INSERT INTO `podcastflow-analytics.bronze.social_mentions_extended`
        (mention_id, podcast_id, platform, mention_text, sentiment_score,
         mention_timestamp, author_username, follower_count, retweet_count, like_count, url)
        VALUES {','.join(values)}
        """
        
        result = execute_sql(sql)
        if result:
            print(f"✅ Stored {len(mentions)} social mentions")
            return True
        else:
            print(f"❌ Failed to store social mentions")
            return False
            
    except Exception as e:
        print(f"❌ Error storing social mentions: {e}")
        return False

def analyze_mention_trends():
    """Analyze trending topics and sentiment patterns"""
    print("\n📈 Analyzing mention trends...")
    
    # Sentiment by platform
    sentiment_sql = """
    SELECT 
        platform,
        COUNT(*) as mention_count,
        AVG(sentiment_score) as avg_sentiment,
        MAX(sentiment_score) as max_sentiment,
        MIN(sentiment_score) as min_sentiment
    FROM `podcastflow-analytics.bronze.social_mentions_extended`
    WHERE mention_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY platform
    ORDER BY mention_count DESC
    """
    
    result = execute_sql(sentiment_sql)
    if result and 'rows' in result:
        print("\n📊 Platform Sentiment Analysis:")
        for row in result['rows']:
            fields = row['f']
            platform = fields[0]['v']
            count = fields[1]['v']
            avg_sentiment = float(fields[2]['v'])
            print(f"  {platform.capitalize()}: {count} mentions, {avg_sentiment:.3f} avg sentiment")
    
    # Top mentioned podcasts
    podcast_sql = """
    SELECT 
        podcast_id,
        COUNT(*) as mention_count,
        AVG(sentiment_score) as avg_sentiment,
        SUM(follower_count) as total_reach
    FROM `podcastflow-analytics.bronze.social_mentions_extended`
    WHERE mention_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY podcast_id
    ORDER BY mention_count DESC
    LIMIT 5
    """
    
    result = execute_sql(podcast_sql)
    if result and 'rows' in result:
        print("\n🎧 Top Mentioned Podcasts:")
        for row in result['rows']:
            fields = row['f']
            podcast = fields[0]['v']
            count = fields[1]['v']
            sentiment = float(fields[2]['v'])
            reach = int(fields[3]['v'])
            print(f"  {podcast}: {count} mentions, {sentiment:.3f} sentiment, {reach:,} total reach")

def main():
    """Main social media ingestion process"""
    print("💬 PodcastFlow Analytics - Social Media Ingestion")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get podcast titles for mention tracking
    podcast_titles = get_podcast_titles()
    if not podcast_titles:
        podcast_titles = ["Tech Talk Podcast", "Business Insights", "Data Science Deep Dive"]
        print("⚠️  Using default podcast titles (no feeds found in database)")
    else:
        print(f"📋 Tracking mentions for {len(podcast_titles)} podcasts")
    
    all_mentions = []
    
    # Simulate mentions from different platforms
    twitter_mentions = simulate_twitter_mentions(podcast_titles, 25)
    reddit_mentions = simulate_reddit_mentions(podcast_titles, 15)
    linkedin_mentions = simulate_linkedin_mentions(podcast_titles, 10)
    
    all_mentions.extend(twitter_mentions)
    all_mentions.extend(reddit_mentions)
    all_mentions.extend(linkedin_mentions)
    
    # Store all mentions
    if store_social_mentions(all_mentions):
        print(f"\n✅ Successfully ingested {len(all_mentions)} social mentions")
        print(f"   Twitter: {len(twitter_mentions)}")
        print(f"   Reddit: {len(reddit_mentions)}")
        print(f"   LinkedIn: {len(linkedin_mentions)}")
    else:
        print("❌ Failed to ingest social mentions")
    
    # Analyze trends
    analyze_mention_trends()
    
    print(f"\n🎉 Social Media Ingestion Complete!")

if __name__ == "__main__":
    main() 