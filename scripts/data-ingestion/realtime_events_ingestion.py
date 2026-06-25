#!/usr/bin/env python3
"""
Real-time Listening Events Ingestion
Simulates real-time podcast listening events with realistic patterns
"""

import os
import requests
import json
from datetime import datetime, timezone, timedelta
import hashlib
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor

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

def get_available_episodes():
    """Get available episodes from the database"""
    sql = """
    SELECT episode_id, podcast_feed_url, title, duration
    FROM `podcastflow-analytics.bronze.episodes`
    LIMIT 100
    """
    
    result = execute_sql(sql)
    episodes = []
    
    if result and 'rows' in result:
        for row in result['rows']:
            fields = row['f']
            episodes.append({
                'episode_id': fields[0]['v'],
                'podcast_feed_url': fields[1]['v'],
                'title': fields[2]['v'],
                'duration': fields[3]['v']
            })
    
    # Fallback to sample episodes if none found
    if not episodes:
        for i in range(20):
            episodes.append({
                'episode_id': f'sample_ep_{i:03d}',
                'podcast_feed_url': f'https://feeds.example.com/podcast_{i%5}',
                'title': f'Sample Episode {i+1}',
                'duration': f'{random.randint(20, 90)}:00'
            })
    
    return episodes

class UserBehaviorSimulator:
    """Simulates realistic user listening behavior patterns"""
    
    def __init__(self):
        self.user_profiles = self._generate_user_profiles()
        self.platforms = ['spotify', 'apple_podcasts', 'google_podcasts', 'podcast_app']
        self.devices = ['mobile', 'desktop', 'tablet', 'smart_speaker']
        
    def _generate_user_profiles(self):
        """Generate diverse user behavior profiles"""
        profiles = []
        
        # Power Users (20%)
        for i in range(20):
            profiles.append({
                'user_id': f'power_user_{i:03d}',
                'type': 'power',
                'completion_rate_avg': random.uniform(0.8, 0.95),
                'session_frequency': random.uniform(2.0, 5.0),  # sessions per day
                'platform_loyalty': random.choice(self.platforms),
                'skip_tendency': random.uniform(0.05, 0.15),
                'binge_likelihood': 0.7
            })
        
        # Active Users (30%)
        for i in range(30):
            profiles.append({
                'user_id': f'active_user_{i:03d}',
                'type': 'active',
                'completion_rate_avg': random.uniform(0.6, 0.8),
                'session_frequency': random.uniform(1.0, 2.5),
                'platform_loyalty': random.choice(self.platforms),
                'skip_tendency': random.uniform(0.1, 0.25),
                'binge_likelihood': 0.4
            })
        
        # Regular Users (35%)
        for i in range(35):
            profiles.append({
                'user_id': f'regular_user_{i:03d}',
                'type': 'regular',
                'completion_rate_avg': random.uniform(0.4, 0.7),
                'session_frequency': random.uniform(0.5, 1.5),
                'platform_loyalty': random.choice(self.platforms),
                'skip_tendency': random.uniform(0.15, 0.35),
                'binge_likelihood': 0.2
            })
        
        # Casual Users (15%)
        for i in range(15):
            profiles.append({
                'user_id': f'casual_user_{i:03d}',
                'type': 'casual',
                'completion_rate_avg': random.uniform(0.2, 0.5),
                'session_frequency': random.uniform(0.1, 0.7),
                'platform_loyalty': None,  # Platform switchers
                'skip_tendency': random.uniform(0.25, 0.5),
                'binge_likelihood': 0.1
            })
        
        return profiles
    
    def generate_listening_session(self, user_profile, episodes):
        """Generate a realistic listening session for a user"""
        session_events = []
        
        # Determine session characteristics
        if random.random() < user_profile['binge_likelihood']:
            # Binge session - multiple episodes
            episode_count = random.randint(2, 4)
        else:
            # Regular session - single episode
            episode_count = 1
        
        # Choose platform and device
        if user_profile['platform_loyalty']:
            platform = user_profile['platform_loyalty']
        else:
            platform = random.choice(self.platforms)
        
        device = random.choice(self.devices)
        session_start = datetime.now(timezone.utc) - timedelta(seconds=random.randint(0, 3600))
        
        for ep_num in range(episode_count):
            episode = random.choice(episodes)
            
            # Generate completion percentage based on user profile
            base_completion = user_profile['completion_rate_avg']
            completion_variance = 0.2
            completion_percentage = max(0.05, min(1.0, 
                random.gauss(base_completion, completion_variance)))
            
            # Apply skip tendency
            if random.random() < user_profile['skip_tendency']:
                completion_percentage = random.uniform(0.05, 0.3)  # Early skip
            
            # Create listening event
            event_id = f"{user_profile['user_id']}_{int(time.time())}_{ep_num}"
            event_timestamp = session_start + timedelta(minutes=ep_num * 30)
            
            event = {
                'event_id': event_id,
                'user_id': user_profile['user_id'],
                'episode_id': episode['episode_id'],
                'event_type': 'play',
                'completion_percentage': round(completion_percentage * 100, 2),
                'event_timestamp': event_timestamp.isoformat(),
                'platform': platform,
                'device_type': device,
                'session_id': f"session_{user_profile['user_id']}_{int(session_start.timestamp())}",
                'user_type': user_profile['type']
            }
            
            session_events.append(event)
            
            # Add pause/resume events for realistic behavior
            if completion_percentage > 0.3 and random.random() < 0.3:
                pause_event = event.copy()
                pause_event['event_id'] = f"{event_id}_pause"
                pause_event['event_type'] = 'pause'
                pause_event['completion_percentage'] = round(
                    completion_percentage * random.uniform(0.3, 0.7) * 100, 2)
                pause_event['event_timestamp'] = (event_timestamp + 
                    timedelta(minutes=random.randint(5, 20))).isoformat()
                
                session_events.append(pause_event)
        
        return session_events

def batch_insert_events(events, batch_size=50):
    """Insert events in batches for better performance"""
    if not events:
        return True
    
    try:
        # Create table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS `podcastflow-analytics.bronze.listening_events_realtime` (
            event_id STRING,
            user_id STRING,
            episode_id STRING,
            event_type STRING,
            completion_percentage FLOAT64,
            event_timestamp TIMESTAMP,
            platform STRING,
            device_type STRING,
            session_id STRING,
            user_type STRING
        )
        """
        execute_sql(create_table_sql)
        
        # Process in batches
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            def escape_sql(value):
                if isinstance(value, str):
                    return value.replace("'", "''")
                return str(value)
            
            values = []
            for event in batch:
                values.append(f"""
                ('{escape_sql(event['event_id'])}',
                 '{escape_sql(event['user_id'])}',
                 '{escape_sql(event['episode_id'])}',
                 '{escape_sql(event['event_type'])}',
                 {event['completion_percentage']},
                 TIMESTAMP('{event['event_timestamp']}'),
                 '{escape_sql(event['platform'])}',
                 '{escape_sql(event['device_type'])}',
                 '{escape_sql(event['session_id'])}',
                 '{escape_sql(event['user_type'])}')
                """)
            
            sql = f"""
            INSERT INTO `podcastflow-analytics.bronze.listening_events_realtime`
            (event_id, user_id, episode_id, event_type, completion_percentage,
             event_timestamp, platform, device_type, session_id, user_type)
            VALUES {','.join(values)}
            """
            
            result = execute_sql(sql)
            if not result:
                print(f"❌ Failed to insert batch {i//batch_size + 1}")
                return False
            
            print(f"✅ Inserted batch {i//batch_size + 1} ({len(batch)} events)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inserting events: {e}")
        return False

def generate_realtime_events(duration_minutes=5, events_per_minute=10):
    """Generate real-time events for specified duration"""
    print(f"🚀 Generating real-time events for {duration_minutes} minutes...")
    print(f"📊 Target rate: {events_per_minute} events/minute")
    
    # Initialize
    simulator = UserBehaviorSimulator()
    episodes = get_available_episodes()
    all_events = []
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    while time.time() < end_time:
        minute_start = time.time()
        minute_events = []
        
        # Generate events for this minute
        for _ in range(events_per_minute):
            user = random.choice(simulator.user_profiles)
            
            # Check if user should have a session (based on frequency)
            daily_probability = user['session_frequency'] / (24 * 60)  # per minute
            if random.random() < daily_probability:
                session_events = simulator.generate_listening_session(user, episodes)
                minute_events.extend(session_events)
        
        # Store events if any were generated
        if minute_events:
            all_events.extend(minute_events)
            print(f"⏱️  Generated {len(minute_events)} events (total: {len(all_events)})")
        
        # Wait for next minute
        elapsed = time.time() - minute_start
        if elapsed < 60:
            time.sleep(60 - elapsed)
    
    # Batch insert all events
    if all_events:
        print(f"\n💾 Storing {len(all_events)} total events...")
        if batch_insert_events(all_events):
            print(f"✅ Successfully stored all events")
        else:
            print(f"❌ Failed to store some events")
    
    return all_events

def analyze_realtime_metrics():
    """Analyze real-time listening metrics"""
    print("\n📈 Analyzing real-time metrics...")
    
    # Platform distribution
    platform_sql = """
    SELECT 
        platform,
        COUNT(*) as event_count,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(completion_percentage) as avg_completion
    FROM `podcastflow-analytics.bronze.listening_events_realtime`
    WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    GROUP BY platform
    ORDER BY event_count DESC
    """
    
    result = execute_sql(platform_sql)
    if result and 'rows' in result:
        print("\n📱 Platform Performance (Last Hour):")
        for row in result['rows']:
            fields = row['f']
            platform = fields[0]['v']
            events = fields[1]['v']
            users = fields[2]['v']
            completion = float(fields[3]['v'])
            print(f"  {platform}: {events} events, {users} users, {completion:.1f}% avg completion")
    
    # User type analysis
    user_type_sql = """
    SELECT 
        user_type,
        COUNT(*) as event_count,
        AVG(completion_percentage) as avg_completion,
        COUNT(DISTINCT session_id) as session_count
    FROM `podcastflow-analytics.bronze.listening_events_realtime`
    WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    GROUP BY user_type
    ORDER BY event_count DESC
    """
    
    result = execute_sql(user_type_sql)
    if result and 'rows' in result:
        print("\n👥 User Type Analysis (Last Hour):")
        for row in result['rows']:
            fields = row['f']
            user_type = fields[0]['v']
            events = fields[1]['v']
            completion = float(fields[2]['v'])
            sessions = fields[3]['v']
            print(f"  {user_type.capitalize()}: {events} events, {sessions} sessions, {completion:.1f}% completion")

def main():
    """Main real-time ingestion process"""
    print("⚡ PodcastFlow Analytics - Real-time Events Ingestion")
    print("=" * 65)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    duration_minutes = int(os.getenv('REALTIME_DURATION_MINUTES', 5))
    events_per_minute = int(os.getenv('EVENTS_PER_MINUTE', 15))
    
    print(f"⚙️  Configuration:")
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Rate: {events_per_minute} events/minute")
    print(f"   Total expected: ~{duration_minutes * events_per_minute} events")
    
    # Generate real-time events
    events = generate_realtime_events(duration_minutes, events_per_minute)
    
    # Analyze the generated data
    analyze_realtime_metrics()
    
    print(f"\n🎉 Real-time Events Ingestion Complete!")
    print(f"✅ Generated {len(events)} total events")
    print(f"📊 Data available for real-time analysis")

if __name__ == "__main__":
    main() 