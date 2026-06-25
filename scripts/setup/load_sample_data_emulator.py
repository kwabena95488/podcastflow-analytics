#!/usr/bin/env python3
"""
BigQuery Sample Data Loader - FREE TIER OPTIMIZED
Loads minimal sample podcast analytics data optimized for Google Cloud Free Tier
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound
    import pandas as pd
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Install with: pip install google-cloud-bigquery pandas")
    exit(1)

class BigQueryFreeTierLoader:
    def __init__(self):
        # Configure for BigQuery (cloud or emulator)
        self.project_id = os.getenv('GCP_PROJECT_ID', 'podcastflow-analytics')
        
        # Check if we're using the emulator
        emulator_host = os.getenv('BIGQUERY_EMULATOR_HOST')
        if emulator_host:
            # For emulator, set the environment variable and use anonymous credentials
            os.environ['BIGQUERY_EMULATOR_HOST'] = f'http://{emulator_host}:{os.getenv("BIGQUERY_EMULATOR_PORT", "9050")}'
            print(f"🎯 Using BigQuery emulator at {emulator_host}")
            
            # Create client without authentication for emulator
            from google.auth.credentials import AnonymousCredentials
            self.client = bigquery.Client(
                project=self.project_id,
                credentials=AnonymousCredentials()
            )
        else:
            print(f"☁️ Using Google Cloud BigQuery for project: {self.project_id}")
            self.client = bigquery.Client(project=self.project_id)

    def load_all_sample_data(self):
        """Load minimal sample data optimized for free tier"""
        print("🎧 Loading PodcastFlow Analytics sample data (FREE TIER OPTIMIZED)...")
        
        try:
            # Load bronze layer data with smaller datasets
            self.load_rss_feeds_data()
            self.load_listening_events_data()
            self.load_social_mentions_data()
            
            print("✅ All sample data loaded successfully!")
            print("📊 Free Tier Usage Summary:")
            print("   - RSS Feeds: 4 records (~1KB)")
            print("   - Listening Events: 500 records (~50KB)")
            print("   - Social Mentions: 50 records (~10KB)")
            print("   - Total Storage: <100KB (well under 10GB limit)")
            
            # Display summary
            self.display_data_summary()
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            raise

    def load_rss_feeds_data(self):
        """Load minimal RSS feeds data for free tier"""
        print("📡 Loading RSS feeds data (minimal for free tier)...")
        
        # Minimal podcast data to stay well under storage limits
        rss_data = [
            {
                'feed_url': 'https://feeds.example.com/tech-talk',
                'raw_content': '<?xml version="1.0"?><rss><channel><title>Tech Talk Podcast</title><description>Weekly tech discussions</description></channel></rss>',
                'ingestion_timestamp': datetime.now() - timedelta(hours=2),
                'podcast_title': 'Tech Talk Podcast',
                'episode_count': 25  # Reduced from 125
            },
            {
                'feed_url': 'https://feeds.example.com/business-insights',
                'raw_content': '<?xml version="1.0"?><rss><channel><title>Business Insights</title><description>Business strategy and insights</description></channel></rss>',
                'ingestion_timestamp': datetime.now() - timedelta(hours=1),
                'podcast_title': 'Business Insights',
                'episode_count': 18  # Reduced from 89
            },
            {
                'feed_url': 'https://feeds.example.com/data-science',
                'raw_content': '<?xml version="1.0"?><rss><channel><title>Data Science Deep Dive</title><description>Data science concepts</description></channel></rss>',
                'ingestion_timestamp': datetime.now() - timedelta(minutes=30),
                'podcast_title': 'Data Science Deep Dive',
                'episode_count': 12  # Reduced from 67
            },
            {
                'feed_url': 'https://feeds.example.com/startup-stories',
                'raw_content': '<?xml version="1.0"?><rss><channel><title>Startup Stories</title><description>Entrepreneurship journeys</description></channel></rss>',
                'ingestion_timestamp': datetime.now() - timedelta(minutes=15),
                'podcast_title': 'Startup Stories',
                'episode_count': 15  # Reduced from 156
            }
        ]
        
        df = pd.DataFrame(rss_data)
        table_id = f"{self.project_id}.bronze.rss_feeds"
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE"
        )
        
        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        print(f"✅ Loaded {len(rss_data)} RSS feed records (~1KB)")

    def load_listening_events_data(self):
        """Load minimal listening events data for free tier"""
        print("🎵 Loading listening events data (500 events for free tier)...")
        
        # Generate realistic but minimal listening events
        events_data = []
        base_time = datetime.now() - timedelta(days=7)  # Only 7 days instead of 30
        
        podcasts = ['tech-talk', 'business-insights', 'data-science', 'startup-stories']
        platforms = ['spotify', 'apple_podcasts', 'google_podcasts']
        device_types = ['mobile', 'desktop']
        event_types = ['play', 'pause', 'skip', 'complete']
        
        # Reduced from 5000 to 500 events for free tier
        for i in range(500):
            podcast = random.choice(podcasts)
            platform = random.choice(platforms)
            device = random.choice(device_types)
            event_type = random.choice(event_types)
            
            # Generate realistic completion percentages
            if event_type == 'complete':
                completion = random.uniform(80, 100)
            elif event_type == 'skip':
                completion = random.uniform(5, 40)
            elif event_type == 'pause':
                completion = random.uniform(20, 80)
            else:
                completion = random.uniform(0, 100)
            
            event_time = base_time + timedelta(
                minutes=random.randint(0, 10080)  # Random time in last 7 days
            )
            
            events_data.append({
                'event_id': f'evt_{i:04d}',
                'user_id': f'user_{random.randint(1, 50):03d}',  # Reduced users
                'episode_id': f'ep_{podcast}_{random.randint(1, 10):02d}',  # Fewer episodes
                'event_type': event_type,
                'completion_percentage': round(completion, 2),
                'event_timestamp': event_time,
                'platform': platform,
                'device_type': device
            })
        
        df = pd.DataFrame(events_data)
        table_id = f"{self.project_id}.bronze.listening_events"
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE"
        )
        
        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        print(f"✅ Loaded {len(events_data)} listening event records (~50KB)")

    def load_social_mentions_data(self):
        """Load minimal social mentions data for free tier"""
        print("💬 Loading social mentions data (50 mentions for free tier)...")
        
        # Minimal social mentions with realistic content
        mentions_templates = [
            "Just listened to {podcast} - great insights!",
            "Love the latest {podcast} episode! 🎧",
            "Binge-listening to {podcast} while working.",
            "The {podcast} episode changed my perspective.",
            "Highly recommend {podcast}!",
        ]
        
        podcasts_topics = {
            'Tech Talk Podcast': 'technology',
            'Business Insights': 'business',
            'Data Science Deep Dive': 'data science',
            'Startup Stories': 'entrepreneurship'
        }
        
        platforms = ['twitter', 'linkedin', 'reddit']
        
        mentions_data = []
        base_time = datetime.now() - timedelta(days=7)  # Only 7 days of mentions
        
        # Reduced from 500 to 50 mentions for free tier
        for i in range(50):
            podcast_title = random.choice(list(podcasts_topics.keys()))
            template = random.choice(mentions_templates)
            
            mention_text = template.format(podcast=podcast_title)
            
            # Generate sentiment score
            sentiment = random.uniform(0.4, 0.9)  # Generally positive
            
            mention_time = base_time + timedelta(
                minutes=random.randint(0, 10080)
            )
            
            mentions_data.append({
                'mention_id': f'mention_{i:04d}',
                'podcast_id': podcast_title.lower().replace(' ', '_'),
                'platform': random.choice(platforms),
                'mention_text': mention_text,
                'sentiment_score': round(sentiment, 3),
                'mention_timestamp': mention_time,
                'follower_count': random.randint(50, 5000)  # Smaller influencers
            })
        
        df = pd.DataFrame(mentions_data)
        table_id = f"{self.project_id}.bronze.social_mentions"
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE"
        )
        
        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        print(f"✅ Loaded {len(mentions_data)} social mention records (~10KB)")

    def display_data_summary(self):
        """Display summary of loaded data with free tier context"""
        print("\n📊 Data Summary (Free Tier Optimized):")
        print("=" * 60)
        
        datasets = ['bronze', 'silver', 'gold', 'dbt_artifacts']
        total_rows = 0
        
        for dataset_id in datasets:
            try:
                dataset_ref = self.client.dataset(dataset_id)
                tables = list(self.client.list_tables(dataset_ref))
                
                print(f"\n📁 Dataset: {dataset_id}")
                
                for table in tables:
                    try:
                        table_ref = dataset_ref.table(table.table_id)
                        table_obj = self.client.get_table(table_ref)
                        
                        # Get row count
                        query = f"SELECT COUNT(*) as row_count FROM `{self.project_id}.{dataset_id}.{table.table_id}`"
                        result = list(self.client.query(query))
                        row_count = result[0].row_count if result else 0
                        total_rows += row_count
                        
                        print(f"  📋 {table.table_id}: {row_count:,} rows")
                        
                    except Exception as e:
                        print(f"  📋 {table.table_id}: Unable to count rows ({e})")
                        
            except NotFound:
                print(f"\n📁 Dataset: {dataset_id} (not found)")
        
        print(f"\n🎯 Free Tier Compliance:")
        print(f"   Total rows loaded: {total_rows:,}")
        print(f"   Estimated storage: <100KB")
        print(f"   BigQuery limit: 10GB (using <0.001%)")
        print(f"   Query limit: 1TB/month (sample queries use <1MB)")
        
        # Display sample queries optimized for free tier
        print(f"\n🔍 Sample Queries (Free Tier Optimized):")
        print("=" * 60)
        print("-- Top podcasts by episode count")
        print(f"SELECT podcast_title, episode_count FROM `{self.project_id}.bronze.rss_feeds` ORDER BY episode_count DESC;")
        print("")
        print("-- Recent listening events (last 7 days)")
        print(f"SELECT platform, COUNT(*) as events FROM `{self.project_id}.bronze.listening_events` WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) GROUP BY platform;")
        print("")
        print("-- Average sentiment by podcast")
        print(f"SELECT podcast_id, AVG(sentiment_score) as avg_sentiment FROM `{self.project_id}.bronze.social_mentions` GROUP BY podcast_id;")

    def verify_connection(self):
        """Verify connection to BigQuery"""
        try:
            # Test basic connectivity
            datasets = list(self.client.list_datasets())
            print(f"✅ Connected to BigQuery. Found {len(datasets)} datasets.")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to BigQuery: {e}")
            return False

def main():
    """Main execution function"""
    print("🎧 PodcastFlow Analytics - BigQuery Sample Data Loader (FREE TIER)")
    print("=" * 70)
    
    loader = BigQueryFreeTierLoader()
    
    # Verify connection
    if not loader.verify_connection():
        print("Please ensure BigQuery is accessible with proper authentication")
        exit(1)
    
    # Load sample data
    loader.load_all_sample_data()
    
    print("\n🎉 Sample data loading complete!")
    print("💰 Free tier optimized: All data fits comfortably within GCP limits")
    print("🚀 You can now run dbt models and explore the dashboard.")

if __name__ == "__main__":
    main() 