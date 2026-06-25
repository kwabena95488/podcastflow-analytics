#!/usr/bin/env python3
"""
Master Real Data Ingestion Orchestrator
Coordinates RSS feeds, social media, and real-time events ingestion
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['feedparser', 'requests']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing dependencies: {', '.join(missing_packages)}")
        print(f"💡 Install with: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_emulator_status():
    """Check if BigQuery emulator is running"""
    try:
        emulator_host = os.getenv('BIGQUERY_EMULATOR_HOST', 'localhost')
        emulator_port = os.getenv('BIGQUERY_EMULATOR_PORT', '9050')
        
        if emulator_host.startswith('http://'):
            emulator_host = emulator_host.replace('http://', '')
        
        # Try to connect to the emulator
        url = f"http://{emulator_host}:{emulator_port}/bigquery/v2/projects/podcastflow-analytics/queries"
        test_query = {"query": "SELECT 1 as test", "useLegacySql": False}
        
        response = requests.post(url, json=test_query, timeout=5)
        if response.status_code == 200:
            print("✅ BigQuery emulator is running")
            return True
        else:
            print(f"❌ BigQuery emulator returned error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot connect to BigQuery emulator: {e}")
        print("💡 Make sure the emulator is running on localhost:9050")
        return False

def run_script(script_name, description, env_vars=None):
    """Run a Python script with proper error handling"""
    print(f"\n🚀 Starting: {description}")
    print("=" * 60)
    
    try:
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Run the script
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=os.path.dirname(__file__),
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def run_parallel_ingestion():
    """Run social media and real-time ingestion in parallel"""
    print(f"\n🔄 Running parallel data ingestion...")
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        social_future = executor.submit(
            run_script, 
            'social_media_ingestion.py',
            'Social Media Ingestion',
            {'BIGQUERY_EMULATOR_HOST': 'localhost'}
        )
        
        realtime_future = executor.submit(
            run_script,
            'realtime_events_ingestion.py', 
            'Real-time Events Ingestion',
            {
                'BIGQUERY_EMULATOR_HOST': 'localhost',
                'REALTIME_DURATION_MINUTES': '3',
                'EVENTS_PER_MINUTE': '20'
            }
        )
        
        # Wait for completion
        social_success = social_future.result()
        realtime_success = realtime_future.result()
        
        return social_success and realtime_success

def update_transformations():
    """Update dbt transformations to include new data sources"""
    print(f"\n🔄 Updating data transformations...")
    
    # Run transformations to include new data
    return run_script(
        'run_dbt_transformations.py',
        'Updated Data Transformations',
        {'BIGQUERY_EMULATOR_HOST': 'localhost'}
    )

def run_comprehensive_analysis():
    """Run analysis on the expanded dataset"""
    print(f"\n📊 Running comprehensive analysis...")
    
    analysis_dir = os.path.join(os.path.dirname(__file__), '..', 'analysis')
    
    try:
        result = subprocess.run(
            [sys.executable, 'run_all_analysis.py'],
            cwd=analysis_dir,
            env={**os.environ, 'BIGQUERY_EMULATOR_HOST': 'localhost'},
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            print("✅ Comprehensive analysis completed")
            return True
        else:
            print(f"❌ Analysis failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return False

def generate_progress_report():
    """Generate a progress report showing data volumes"""
    print(f"\n📋 Generating progress report...")
    
    try:
        # Query data volumes
        url = "http://localhost:9050/bigquery/v2/projects/podcastflow-analytics/queries"
        
        queries = {
            'RSS Feeds': "SELECT COUNT(*) as count FROM `podcastflow-analytics.bronze.rss_feeds`",
            'Episodes': "SELECT COUNT(*) as count FROM `podcastflow-analytics.bronze.episodes`",
            'Social Mentions': "SELECT COUNT(*) as count FROM `podcastflow-analytics.bronze.social_mentions_extended`",
            'Real-time Events': "SELECT COUNT(*) as count FROM `podcastflow-analytics.bronze.listening_events_realtime`",
            'Silver Layer': "SELECT COUNT(*) as count FROM `podcastflow-analytics.silver.stg_rss_feeds`",
            'Gold Layer': "SELECT COUNT(*) as count FROM `podcastflow-analytics.gold.dim_podcasts`"
        }
        
        report = {}
        for name, query in queries.items():
            payload = {"query": query, "useLegacySql": False}
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    if 'rows' in result and result['rows']:
                        count = result['rows'][0]['f'][0]['v']
                        report[name] = int(count)
                    else:
                        report[name] = 0
                else:
                    report[name] = 'Error'
            except:
                report[name] = 'N/A'
        
        # Print report
        print("📊 Data Pipeline Status Report")
        print("=" * 40)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for layer, count in report.items():
            if isinstance(count, int):
                print(f"✅ {layer:<20}: {count:>8,} records")
            else:
                print(f"❌ {layer:<20}: {count:>8}")
        
        total_records = sum(v for v in report.values() if isinstance(v, int))
        print(f"\n🎯 Total Records: {total_records:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return False

def main():
    """Main orchestration process"""
    print("🎧 PodcastFlow Analytics - Real Data Integration")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Phase 1: Prerequisites
    print("🔍 Phase 1: Checking Prerequisites")
    print("-" * 35)
    
    if not check_dependencies():
        print("❌ Prerequisites not met. Please install missing dependencies.")
        sys.exit(1)
    
    if not check_emulator_status():
        print("❌ BigQuery emulator not available. Please start the infrastructure.")
        sys.exit(1)
    
    # Phase 2: RSS Feed Ingestion
    print("\n📡 Phase 2: RSS Feed Ingestion")
    print("-" * 35)
    
    rss_success = run_script(
        'rss_feed_ingestion.py',
        'RSS Feed Ingestion',
        {'BIGQUERY_EMULATOR_HOST': 'localhost'}
    )
    
    if not rss_success:
        print("⚠️  RSS ingestion failed, but continuing with remaining tasks...")
    
    # Phase 3: Parallel Social Media & Real-time Ingestion
    print("\n💬 Phase 3: Social & Real-time Data")
    print("-" * 40)
    
    parallel_success = run_parallel_ingestion()
    
    if not parallel_success:
        print("⚠️  Some parallel ingestion tasks failed, but continuing...")
    
    # Phase 4: Update Transformations
    print("\n🔄 Phase 4: Update Transformations")
    print("-" * 40)
    
    transform_success = update_transformations()
    
    # Phase 5: Comprehensive Analysis
    print("\n📊 Phase 5: Comprehensive Analysis")
    print("-" * 40)
    
    analysis_success = run_comprehensive_analysis()
    
    # Phase 6: Final Report
    print("\n📋 Phase 6: Final Report")
    print("-" * 30)
    
    generate_progress_report()
    
    # Summary
    print(f"\n🎉 Real Data Integration Complete!")
    print("=" * 45)
    
    success_count = sum([
        rss_success,
        parallel_success, 
        transform_success,
        analysis_success
    ])
    
    print(f"✅ Completed phases: {success_count}/4")
    
    if success_count == 4:
        print("🏆 All phases completed successfully!")
        print("📊 Your pipeline is now running with real data!")
    elif success_count >= 2:
        print("⚠️  Partial success - pipeline is functional with some limitations")
    else:
        print("❌ Multiple failures - please review error messages above")
    
    # Access information
    print(f"\n🔗 Access Points:")
    print(f"   BigQuery Emulator: http://localhost:9050")
    print(f"   Jupyter Notebooks: http://localhost:8888?token=podcastflow")
    print(f"   Streamlit Dashboard: http://localhost:8501")
    print(f"   Analysis Reports: analysis/outputs/")

if __name__ == "__main__":
    main() 