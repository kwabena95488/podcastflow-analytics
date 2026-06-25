#!/usr/bin/env python3
"""
Master Analysis Runner
Executes all analysis scripts and creates a comprehensive summary report
"""

import subprocess
import sys
import os
from datetime import datetime

def run_script(script_name):
    """Run a Python script and capture its output"""
    print(f"\n🚀 Running {script_name}...")
    print("=" * 50)
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully")
            if result.stdout:
                print("Output:")
                print(result.stdout)
        else:
            print(f"❌ {script_name} failed with error:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False
    
    return True

def create_summary_report():
    """Create a comprehensive summary report from all analyses"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    summary = f"""
🎧 PodcastFlow Analytics - Comprehensive Analysis Summary
Generated: {timestamp}
================================================================

ANALYSIS OVERVIEW
=================

This comprehensive analysis suite provides insights across multiple dimensions
of podcast analytics data, combining listening behavior, user engagement, 
and social sentiment analysis.

ANALYSIS COMPONENTS
===================

1. DATA EXPLORATION (01_data_exploration.py)
   • Basic data structure and quality assessment
   • Table-level statistics and sample data review
   • Cross-table relationship analysis
   • Data completeness and integrity validation

2. USER BEHAVIOR ANALYSIS (02_user_behavior_analysis.py)
   • User engagement metrics and segmentation
   • Listening pattern analysis by platform and device
   • Content preference identification
   • Behavioral insights and user classification

3. SOCIAL SENTIMENT ANALYSIS (03_social_sentiment_analysis.py)
   • Overall sentiment trends across platforms
   • Podcast-specific sentiment analysis
   • Influencer impact and reach analysis
   • Temporal sentiment patterns
   • Cross-dataset correlation analysis

BUSINESS VALUE
==============

Content Strategy Insights:
• Identify high-performing content types and formats
• Understand audience engagement patterns
• Optimize content for different platforms and devices
• Track social media impact on podcast performance

User Experience Optimization:
• Segment users for personalized experiences
• Identify platform-specific behavior patterns
• Understand content consumption preferences
• Track user journey and engagement lifecycle

Social Media Strategy:
• Monitor brand sentiment across platforms
• Identify influencer opportunities
• Track social media ROI and reach
• Understand platform-specific audience behavior

Performance Monitoring:
• Establish baseline metrics for podcast performance
• Track trends in user engagement and satisfaction
• Monitor social media impact on listenership
• Identify early warning signs for content issues

TECHNICAL IMPLEMENTATION
=========================

Data Architecture:
• Bronze layer: Raw data ingestion (RSS feeds, events, mentions)
• Silver layer: Cleaned and transformed data (ready for dbt)
• Gold layer: Business-ready aggregated insights

Analysis Framework:
• Modular Python scripts for different analysis dimensions
• Standardized output format for easy consumption
• Automated report generation with timestamps
• Scalable architecture for additional analysis types

BigQuery Integration:
• Direct SQL analysis against emulator
• Optimized queries for performance
• Structured output for downstream processing
• Free-tier optimized data volumes

NEXT STEPS
==========

1. Jupyter Notebook Integration:
   • Interactive data exploration
   • Advanced visualization capabilities
   • Ad-hoc analysis and hypothesis testing
   • Collaborative analysis environment

2. Dashboard Development:
   • Real-time metrics visualization
   • Executive summary dashboards
   • Operational monitoring interfaces
   • Automated alerting systems

3. Advanced Analytics:
   • Machine learning models for churn prediction
   • Content recommendation algorithms
   • Sentiment prediction models
   • User lifetime value analysis

4. Data Pipeline Enhancement:
   • Real-time data ingestion
   • Automated data quality monitoring
   • Advanced transformation logic
   • Data lineage tracking

OUTPUT FILES
============

The following analysis reports have been generated:
• 01_data_exploration_report.txt - Basic data structure and quality
• 02_user_behavior_analysis_report.txt - User engagement and patterns
• 03_social_sentiment_analysis_report.txt - Social media insights
• master_analysis_summary.txt - This comprehensive summary

ACCESS INFORMATION
==================

BigQuery Emulator: http://localhost:9050
Jupyter Notebooks: http://localhost:8888?token=podcastflow
Streamlit Dashboard: http://localhost:8501

For detailed analysis results, please review the individual report files
in the outputs/ directory.

================================================================
Analysis Framework - PodcastFlow Analytics Platform
"""
    
    # Save summary report
    with open("outputs/master_analysis_summary.txt", "w") as f:
        f.write(summary)
    
    print("📋 Comprehensive summary report created!")
    print("📄 Saved to outputs/master_analysis_summary.txt")

def main():
    """Main execution function"""
    print("🎧 PodcastFlow Analytics - Master Analysis Runner")
    print("=================================================")
    
    # Ensure outputs directory exists
    os.makedirs("outputs", exist_ok=True)
    
    # Analysis scripts to run in order
    scripts = [
        "01_data_exploration.py",
        "02_user_behavior_analysis.py", 
        "03_social_sentiment_analysis.py"
    ]
    
    # Track success/failure
    successful_scripts = []
    failed_scripts = []
    
    # Run each analysis script
    for script in scripts:
        if run_script(script):
            successful_scripts.append(script)
        else:
            failed_scripts.append(script)
    
    # Report results
    print("\n📊 ANALYSIS EXECUTION SUMMARY")
    print("=" * 40)
    
    if successful_scripts:
        print(f"✅ Successful ({len(successful_scripts)}):")
        for script in successful_scripts:
            print(f"   • {script}")
    
    if failed_scripts:
        print(f"❌ Failed ({len(failed_scripts)}):")
        for script in failed_scripts:
            print(f"   • {script}")
    
    # Create comprehensive summary if at least one script succeeded
    if successful_scripts:
        print("\n📋 Creating comprehensive summary report...")
        create_summary_report()
        
        print("\n🎉 Analysis suite completed!")
        print(f"📄 {len(successful_scripts)} analysis reports generated")
        print("📁 All outputs saved to outputs/ directory")
        
        # List generated files
        print("\n📂 Generated Files:")
        try:
            output_files = os.listdir("outputs")
            for file in sorted(output_files):
                print(f"   • outputs/{file}")
        except:
            print("   • Could not list output files")
            
    else:
        print("\n❌ No analysis scripts completed successfully")
        print("Please check BigQuery emulator connectivity and try again")

if __name__ == "__main__":
    main() 