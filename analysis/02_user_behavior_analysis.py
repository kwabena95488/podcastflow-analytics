#!/usr/bin/env python3
"""
Step 2: User Behavior Analysis
Analyzes user listening patterns, engagement metrics, and behavior segmentation
"""

import requests
from datetime import datetime

def execute_query(sql_query, project_id="podcastflow-analytics"):
    """Execute SQL query against BigQuery emulator"""
    emulator_host = "localhost"
    emulator_port = "9050"
    
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

def format_query_result(result, title="Query Result"):
    """Format query result for readable output"""
    if not result or 'rows' not in result:
        return f"{title}: No data returned\n"
    
    output = f"\n{title}\n" + "=" * len(title) + "\n"
    
    # Get column names from schema
    if 'schema' in result and 'fields' in result['schema']:
        columns = [field['name'] for field in result['schema']['fields']]
        output += " | ".join(columns) + "\n"
        output += "-" * (len(" | ".join(columns))) + "\n"
        
        # Format rows
        for row in result['rows']:
            values = [field['v'] for field in row['f']]
            output += " | ".join(str(v) for v in values) + "\n"
    
    output += f"\nTotal rows: {result.get('totalRows', 'Unknown')}\n"
    return output

def save_output(content, filename):
    """Save output to file"""
    filepath = f"outputs/{filename}"
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"📄 Saved output to {filepath}")

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = f"🎧 PodcastFlow Analytics - User Behavior Analysis\n"
    output += f"Generated: {timestamp}\n"
    output += "=" * 60 + "\n\n"
    
    print("👥 Starting user behavior analysis...")
    
    # 1. User Engagement Metrics
    print("📊 Analyzing user engagement...")
    engagement_analysis = "📊 USER ENGAGEMENT METRICS\n"
    engagement_analysis += "===========================\n"
    
    # User activity levels
    user_activity_query = """
    SELECT 
        user_id,
        COUNT(*) as total_events,
        COUNT(DISTINCT episode_id) as unique_episodes,
        AVG(completion_percentage) as avg_completion,
        MAX(completion_percentage) as max_completion,
        MIN(completion_percentage) as min_completion,
        COUNT(DISTINCT platform) as platforms_used,
        COUNT(DISTINCT device_type) as device_types_used
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY user_id
    ORDER BY total_events DESC
    LIMIT 10
    """
    user_activity_result = execute_query(user_activity_query)
    engagement_analysis += format_query_result(user_activity_result, "Top 10 Most Active Users")
    
    # User engagement segmentation
    engagement_segment_query = """
    WITH user_metrics AS (
        SELECT 
            user_id,
            COUNT(*) as total_events,
            AVG(completion_percentage) as avg_completion
        FROM `podcastflow-analytics.bronze.listening_events`
        GROUP BY user_id
    )
    SELECT 
        CASE 
            WHEN total_events >= 3 AND avg_completion >= 70 THEN 'High Engagement'
            WHEN total_events >= 2 AND avg_completion >= 50 THEN 'Medium Engagement'
            WHEN total_events >= 1 AND avg_completion >= 30 THEN 'Low Engagement'
            ELSE 'Very Low Engagement'
        END as engagement_segment,
        COUNT(*) as user_count,
        AVG(total_events) as avg_events_per_user,
        AVG(avg_completion) as avg_completion_rate
    FROM user_metrics
    GROUP BY engagement_segment
    ORDER BY user_count DESC
    """
    engagement_segment_result = execute_query(engagement_segment_query)
    engagement_analysis += format_query_result(engagement_segment_result, "User Engagement Segmentation")
    
    output += engagement_analysis + "\n"
    
    # 2. Listening Patterns Analysis
    print("🕐 Analyzing listening patterns...")
    patterns_analysis = "🕐 LISTENING PATTERNS ANALYSIS\n"
    patterns_analysis += "==============================\n"
    
    # Completion rate by event type
    completion_by_type_query = """
    SELECT 
        event_type,
        COUNT(*) as event_count,
        AVG(completion_percentage) as avg_completion,
        MIN(completion_percentage) as min_completion,
        MAX(completion_percentage) as max_completion,
        STDDEV(completion_percentage) as completion_stddev
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY event_type
    ORDER BY avg_completion DESC
    """
    completion_by_type_result = execute_query(completion_by_type_query)
    patterns_analysis += format_query_result(completion_by_type_result, "Completion Rates by Event Type")
    
    # Platform preferences by user
    platform_preferences_query = """
    SELECT 
        platform,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as total_events,
        AVG(completion_percentage) as avg_completion,
        COUNT(*) / COUNT(DISTINCT user_id) as events_per_user
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY platform
    ORDER BY unique_users DESC
    """
    platform_preferences_result = execute_query(platform_preferences_query)
    patterns_analysis += format_query_result(platform_preferences_result, "Platform Usage and Engagement")
    
    # Device usage patterns
    device_patterns_query = """
    SELECT 
        device_type,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as total_events,
        AVG(completion_percentage) as avg_completion,
        COUNT(CASE WHEN completion_percentage >= 80 THEN 1 END) as high_completion_events
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY device_type
    ORDER BY total_events DESC
    """
    device_patterns_result = execute_query(device_patterns_query)
    patterns_analysis += format_query_result(device_patterns_result, "Device Usage Patterns")
    
    output += patterns_analysis + "\n"
    
    # 3. Content Preference Analysis
    print("🎯 Analyzing content preferences...")
    content_analysis = "🎯 CONTENT PREFERENCE ANALYSIS\n"
    content_analysis += "===============================\n"
    
    # Episode popularity
    episode_popularity_query = """
    SELECT 
        episode_id,
        COUNT(*) as total_listens,
        COUNT(DISTINCT user_id) as unique_listeners,
        AVG(completion_percentage) as avg_completion,
        COUNT(CASE WHEN completion_percentage >= 90 THEN 1 END) as complete_listens
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY episode_id
    ORDER BY total_listens DESC
    LIMIT 10
    """
    episode_popularity_result = execute_query(episode_popularity_query)
    content_analysis += format_query_result(episode_popularity_result, "Most Popular Episodes")
    
    # User content diversity
    content_diversity_query = """
    SELECT 
        user_id,
        COUNT(DISTINCT episode_id) as unique_episodes,
        COUNT(*) as total_events,
        COUNT(DISTINCT episode_id) * 1.0 / COUNT(*) as diversity_ratio
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY user_id
    HAVING COUNT(*) >= 2
    ORDER BY diversity_ratio DESC
    LIMIT 10
    """
    content_diversity_result = execute_query(content_diversity_query)
    content_analysis += format_query_result(content_diversity_result, "Users with Highest Content Diversity")
    
    output += content_analysis + "\n"
    
    # 4. Behavioral Insights
    print("🧠 Generating behavioral insights...")
    insights_analysis = "🧠 BEHAVIORAL INSIGHTS\n"
    insights_analysis += "======================\n"
    
    # Skip behavior analysis
    skip_behavior_query = """
    SELECT 
        CASE 
            WHEN completion_percentage < 10 THEN 'Immediate Skip (0-10%)'
            WHEN completion_percentage < 25 THEN 'Early Skip (10-25%)'
            WHEN completion_percentage < 50 THEN 'Mid Skip (25-50%)'
            WHEN completion_percentage < 75 THEN 'Late Skip (50-75%)'
            WHEN completion_percentage < 90 THEN 'Near Complete (75-90%)'
            ELSE 'Complete (90%+)'
        END as listening_behavior,
        COUNT(*) as event_count,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(completion_percentage) as avg_completion_in_range
    FROM `podcastflow-analytics.bronze.listening_events`
    GROUP BY listening_behavior
    ORDER BY 
        CASE listening_behavior
            WHEN 'Immediate Skip (0-10%)' THEN 1
            WHEN 'Early Skip (10-25%)' THEN 2
            WHEN 'Mid Skip (25-50%)' THEN 3
            WHEN 'Late Skip (50-75%)' THEN 4
            WHEN 'Near Complete (75-90%)' THEN 5
            ELSE 6
        END
    """
    skip_behavior_result = execute_query(skip_behavior_query)
    insights_analysis += format_query_result(skip_behavior_result, "Listening Behavior Distribution")
    
    # Power users identification
    power_users_query = """
    WITH user_stats AS (
        SELECT 
            user_id,
            COUNT(*) as total_events,
            AVG(completion_percentage) as avg_completion,
            COUNT(DISTINCT episode_id) as unique_episodes,
            COUNT(DISTINCT platform) as platforms_used
        FROM `podcastflow-analytics.bronze.listening_events`
        GROUP BY user_id
    )
    SELECT 
        user_id,
        total_events,
        unique_episodes,
        platforms_used,
        avg_completion,
        CASE 
            WHEN total_events >= 4 AND avg_completion >= 60 THEN 'Power User'
            WHEN total_events >= 3 OR avg_completion >= 70 THEN 'Active User'
            WHEN total_events >= 2 OR avg_completion >= 50 THEN 'Regular User'
            ELSE 'Casual User'
        END as user_type
    FROM user_stats
    ORDER BY total_events DESC, avg_completion DESC
    """
    power_users_result = execute_query(power_users_query)
    insights_analysis += format_query_result(power_users_result, "User Classification by Behavior")
    
    output += insights_analysis + "\n"
    
    # 5. Summary and Recommendations
    summary = "📋 BEHAVIORAL ANALYSIS SUMMARY\n"
    summary += "==============================\n\n"
    
    summary += "Key Behavioral Insights:\n"
    summary += "• User engagement varies significantly across the user base\n"
    summary += "• Platform choice influences completion rates\n"
    summary += "• Device type affects listening behavior patterns\n"
    summary += "• Content diversity indicates user preferences\n"
    summary += "• Skip patterns reveal content quality indicators\n\n"
    
    summary += "Segmentation Findings:\n"
    summary += "• Users can be classified into distinct engagement tiers\n"
    summary += "• Power users show consistent high completion rates\n"
    summary += "• Platform loyalty varies among user segments\n"
    summary += "• Device preferences correlate with engagement levels\n\n"
    
    summary += "Recommendations for Content Strategy:\n"
    summary += "• Focus on content that drives high completion rates\n"
    summary += "• Optimize for platforms with highest engagement\n"
    summary += "• Consider device-specific content optimization\n"
    summary += "• Develop retention strategies for different user segments\n"
    summary += "• Monitor skip patterns to improve content quality\n\n"
    
    output += summary
    
    # Save complete report
    save_output(output, "02_user_behavior_analysis_report.txt")
    
    print("✅ User behavior analysis complete!")
    print("📄 Report saved to outputs/02_user_behavior_analysis_report.txt")

if __name__ == "__main__":
    main() 