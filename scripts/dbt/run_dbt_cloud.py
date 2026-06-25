#!/usr/bin/env python3
"""
Cloud dbt Runner for Production BigQuery
Executes dbt transformations against real BigQuery for production validation
"""

import os
import subprocess
import sys
from datetime import datetime

def check_dbt_installation():
    """Check if dbt is installed and configured"""
    try:
        result = subprocess.run(['dbt', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ dbt found: {result.stdout.strip()}")
            return True
        else:
            print("❌ dbt not found")
            return False
    except FileNotFoundError:
        print("❌ dbt not installed")
        return False

def check_cloud_credentials():
    """Check if cloud credentials are available"""
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("✅ Service account credentials found")
        return True
    elif os.getenv('GCLOUD_PROJECT'):
        print("✅ gcloud project configured")
        return True
    else:
        print("❌ No cloud credentials found")
        print("   Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'")
        return False

def run_dbt_cloud(target='prod'):
    """Run dbt against cloud BigQuery"""
    print(f"\n🚀 Running dbt transformations against {target} environment")
    
    # Change to dbt project directory
    dbt_dir = os.path.join(os.path.dirname(__file__), '..', 'dbt_podcast_analytics')
    os.chdir(dbt_dir)
    
    commands = [
        ('dbt deps', 'Installing dependencies'),
        ('dbt seed', 'Loading seed data'),
        ('dbt run', 'Running transformations'),
        ('dbt test', 'Running tests'),
        ('dbt docs generate', 'Generating documentation')
    ]
    
    for cmd, description in commands:
        print(f"\n📋 {description}...")
        result = subprocess.run(f"{cmd} --target {target}", shell=True)
        
        if result.returncode != 0:
            print(f"❌ Failed: {cmd}")
            return False
        else:
            print(f"✅ Success: {description}")
    
    return True

def compare_environments():
    """Compare local emulator results with cloud results"""
    print("\n🔍 Environment Comparison (TODO)")
    print("   This would compare row counts and sample data between:")
    print("   - Local emulator transformations")
    print("   - Cloud BigQuery transformations")
    # TODO: Implement comparison logic

def main():
    print("🎧 PodcastFlow Analytics - Cloud dbt Runner")
    print("=" * 55)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Validate prerequisites
    if not check_dbt_installation():
        sys.exit(1)
    
    if not check_cloud_credentials():
        sys.exit(1)
    
    # Get target environment
    target = sys.argv[1] if len(sys.argv) > 1 else 'prod'
    print(f"🎯 Target environment: {target}")
    
    # Run dbt
    if run_dbt_cloud(target):
        print(f"\n🎉 Cloud dbt run completed successfully!")
        print(f"📊 Transformations available in BigQuery project")
        
        # Optional: Compare with emulator results
        compare_environments()
    else:
        print(f"\n❌ Cloud dbt run failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 