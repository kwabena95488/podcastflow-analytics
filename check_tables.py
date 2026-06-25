#!/usr/bin/env python3
"""
Check Available Tables and Schemas
"""
import requests
import json

def query_bigquery(sql):
    """Execute query against BigQuery emulator"""
    url = 'http://localhost:9050/bigquery/v2/projects/podcastflow-analytics/queries'
    try:
        response = requests.post(url, json={'query': sql, 'useLegacySql': False})
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

# Tables to check
tables_to_check = [
    'podcastflow-analytics.bronze.rss_feeds',
    'podcastflow-analytics.bronze.listening_events',
    'podcastflow-analytics.bronze.listening_events_realtime', 
    'podcastflow-analytics.bronze.social_mentions',
    'podcastflow-analytics.bronze.social_mentions_extended'
]

print("🔍 Checking Available Tables:")
print("=" * 50)

for table in tables_to_check:
    print(f"\n📊 Table: {table}")
    
    # Check if table exists and count records
    count_result = query_bigquery(f"SELECT COUNT(*) FROM `{table}`")
    if count_result and 'rows' in count_result:
        count = count_result['rows'][0]['f'][0]['v']
        print(f"   ✅ Records: {count}")
        
        # If table has data, show sample
        if int(count) > 0:
            sample_result = query_bigquery(f"SELECT * FROM `{table}` LIMIT 3")
            if sample_result and 'rows' in sample_result:
                print(f"   📋 Schema fields: {len(sample_result.get('schema', {}).get('fields', []))} columns")
                if 'schema' in sample_result:
                    fields = sample_result['schema']['fields']
                    print(f"   🏷️  Columns: {[f['name'] for f in fields]}")
    else:
        print(f"   ❌ Table not found or inaccessible")

print("\n" + "=" * 50)
print("✅ Table check complete!") 