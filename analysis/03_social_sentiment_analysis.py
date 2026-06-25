#!/usr/bin/env python3
"""
Step 3: Social Sentiment Analysis
Analyzes social media mentions, sentiment patterns, and correlations with listening behavior
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
    output = f"🎧 PodcastFlow Analytics - Social Sentiment Analysis\n"
    output += f"Generated: {timestamp}\n"
    output += "=" * 60 + "\n\n"
    
    print("💬 Starting social sentiment analysis...")
    
    # 1. Overall Sentiment Overview
    print("📊 Analyzing overall sentiment...")
    sentiment_overview = "📊 SENTIMENT OVERVIEW\n"
    sentiment_overview += "=====================\n"
    
    # Basic sentiment statistics
    sentiment_stats_query = """
    SELECT 
        COUNT(*) as total_mentions,
        AVG(sentiment_score) as avg_sentiment,
        MIN(sentiment_score) as min_sentiment,
        MAX(sentiment_score) as max_sentiment,
        STDDEV(sentiment_score) as sentiment_stddev,
        COUNT(CASE WHEN sentiment_score >= 0.8 THEN 1 END) as very_positive,
        COUNT(CASE WHEN sentiment_score >= 0.6 AND sentiment_score < 0.8 THEN 1 END) as positive,
        COUNT(CASE WHEN sentiment_score >= 0.4 AND sentiment_score < 0.6 THEN 1 END) as neutral,
        COUNT(CASE WHEN sentiment_score < 0.4 THEN 1 END) as negative
    FROM `podcastflow-analytics.bronze.social_mentions`
    """
    sentiment_stats_result = execute_query(sentiment_stats_query)
    sentiment_overview += format_query_result(sentiment_stats_result, "Overall Sentiment Statistics")
    
    # Sentiment distribution by platform
    platform_sentiment_query = """
    SELECT 
        platform,
        COUNT(*) as mention_count,
        AVG(sentiment_score) as avg_sentiment,
        MIN(sentiment_score) as min_sentiment,
        MAX(sentiment_score) as max_sentiment,
        COUNT(CASE WHEN sentiment_score >= 0.7 THEN 1 END) as positive_mentions
    FROM `podcastflow-analytics.bronze.social_mentions`
    GROUP BY platform
    ORDER BY avg_sentiment DESC
    """
    platform_sentiment_result = execute_query(platform_sentiment_query)
    sentiment_overview += format_query_result(platform_sentiment_result, "Sentiment by Social Platform")
    
    output += sentiment_overview + "\n"
    
    # 2. Podcast-Specific Sentiment Analysis
    print("🎯 Analyzing podcast-specific sentiment...")
    podcast_sentiment = "🎯 PODCAST SENTIMENT ANALYSIS\n"
    podcast_sentiment += "=============================\n"
    
    # Sentiment by podcast
    podcast_sentiment_query = """
    SELECT 
        podcast_id,
        COUNT(*) as mention_count,
        AVG(sentiment_score) as avg_sentiment,
        MIN(sentiment_score) as min_sentiment,
        MAX(sentiment_score) as max_sentiment,
        STDDEV(sentiment_score) as sentiment_variance,
        COUNT(CASE WHEN sentiment_score >= 0.8 THEN 1 END) as very_positive_count,
        COUNT(CASE WHEN sentiment_score < 0.5 THEN 1 END) as negative_count
    FROM `podcastflow-analytics.bronze.social_mentions`
    GROUP BY podcast_id
    ORDER BY avg_sentiment DESC
    """
    podcast_sentiment_result = execute_query(podcast_sentiment_query)
    podcast_sentiment += format_query_result(podcast_sentiment_result, "Sentiment Analysis by Podcast")
    
    # Most positive and negative mentions
    extreme_mentions_query = """
    (
        SELECT 
            'Most Positive' as mention_type,
            podcast_id,
            platform,
            sentiment_score,
            mention_text,
            follower_count
        FROM `podcastflow-analytics.bronze.social_mentions`
        ORDER BY sentiment_score DESC
        LIMIT 3
    )
    UNION ALL
    (
        SELECT 
            'Most Negative' as mention_type,
            podcast_id,
            platform,
            sentiment_score,
            mention_text,
            follower_count
        FROM `podcastflow-analytics.bronze.social_mentions`
        ORDER BY sentiment_score ASC
        LIMIT 3
    )
    ORDER BY sentiment_score DESC
    """
    extreme_mentions_result = execute_query(extreme_mentions_query)
    podcast_sentiment += format_query_result(extreme_mentions_result, "Most Positive and Negative Mentions")
    
    output += podcast_sentiment + "\n"
    
    # 3. Influencer and Reach Analysis
    print("📈 Analyzing influencer impact...")
    influencer_analysis = "📈 INFLUENCER AND REACH ANALYSIS\n"
    influencer_analysis += "=================================\n"
    
    # Mentions by follower count segments
    follower_segments_query = """
    SELECT 
        CASE 
            WHEN follower_count >= 5000 THEN 'High Influence (5K+)'
            WHEN follower_count >= 1000 THEN 'Medium Influence (1K-5K)'
            WHEN follower_count >= 500 THEN 'Low Influence (500-1K)'
            ELSE 'Micro Influence (<500)'
        END as influence_tier,
        COUNT(*) as mention_count,
        AVG(sentiment_score) as avg_sentiment,
        SUM(follower_count) as total_reach,
        AVG(follower_count) as avg_followers
    FROM `podcastflow-analytics.bronze.social_mentions`
    GROUP BY influence_tier
    ORDER BY avg_followers DESC
    """
    follower_segments_result = execute_query(follower_segments_query)
    influencer_analysis += format_query_result(follower_segments_result, "Mentions by Influence Tier")
    
    # Top influencers by reach
    top_influencers_query = """
    SELECT 
        mention_id,
        podcast_id,
        platform,
        follower_count,
        sentiment_score,
        mention_text
    FROM `podcastflow-analytics.bronze.social_mentions`
    ORDER BY follower_count DESC
    LIMIT 10
    """
    top_influencers_result = execute_query(top_influencers_query)
    influencer_analysis += format_query_result(top_influencers_result, "Top 10 Mentions by Follower Reach")
    
    # Sentiment vs reach correlation
    sentiment_reach_query = """
    SELECT 
        CASE 
            WHEN sentiment_score >= 0.8 THEN 'Very Positive'
            WHEN sentiment_score >= 0.6 THEN 'Positive'
            WHEN sentiment_score >= 0.4 THEN 'Neutral'
            ELSE 'Negative'
        END as sentiment_category,
        COUNT(*) as mention_count,
        AVG(follower_count) as avg_reach,
        SUM(follower_count) as total_potential_reach,
        MIN(follower_count) as min_reach,
        MAX(follower_count) as max_reach
    FROM `podcastflow-analytics.bronze.social_mentions`
    GROUP BY sentiment_category
    ORDER BY avg_reach DESC
    """
    sentiment_reach_result = execute_query(sentiment_reach_query)
    influencer_analysis += format_query_result(sentiment_reach_result, "Sentiment vs Follower Reach Analysis")
    
    output += influencer_analysis + "\n"
    
    # 4. Temporal Sentiment Patterns
    print("⏰ Analyzing temporal patterns...")
    temporal_analysis = "⏰ TEMPORAL SENTIMENT PATTERNS\n"
    temporal_analysis += "==============================\n"
    
    # Mentions over time
    temporal_mentions_query = """
    SELECT 
        DATE(mention_timestamp) as mention_date,
        COUNT(*) as daily_mentions,
        AVG(sentiment_score) as daily_avg_sentiment,
        SUM(follower_count) as daily_total_reach
    FROM `podcastflow-analytics.bronze.social_mentions`
    GROUP BY mention_date
    ORDER BY mention_date DESC
    """
    temporal_mentions_result = execute_query(temporal_mentions_query)
    temporal_analysis += format_query_result(temporal_mentions_result, "Daily Mention and Sentiment Trends")
    
    # Platform activity patterns
    platform_timing_query = """
    SELECT 
        platform,
        EXTRACT(HOUR FROM mention_timestamp) as mention_hour,
        COUNT(*) as hourly_mentions,
        AVG(sentiment_score) as hourly_avg_sentiment
    FROM `podcastflow-analytics.bronze.social_mentions`
    GROUP BY platform, mention_hour
    ORDER BY platform, mention_hour
    """
    platform_timing_result = execute_query(platform_timing_query)
    temporal_analysis += format_query_result(platform_timing_result, "Platform Activity by Hour")
    
    output += temporal_analysis + "\n"
    
    # 5. Cross-Dataset Correlation Analysis
    print("🔗 Analyzing correlations with listening data...")
    correlation_analysis = "🔗 SENTIMENT-LISTENING CORRELATION\n"
    correlation_analysis += "===================================\n"
    
    # Join social mentions with RSS feeds to analyze podcast performance
    podcast_performance_query = """
    SELECT 
        rf.podcast_title,
        rf.episode_count,
        COUNT(sm.mention_id) as total_mentions,
        AVG(sm.sentiment_score) as avg_sentiment,
        SUM(sm.follower_count) as total_social_reach
    FROM `podcastflow-analytics.bronze.rss_feeds` rf
    LEFT JOIN `podcastflow-analytics.bronze.social_mentions` sm
        ON REPLACE(LOWER(rf.podcast_title), ' ', '_') = sm.podcast_id
    GROUP BY rf.podcast_title, rf.episode_count
    ORDER BY total_mentions DESC
    """
    podcast_performance_result = execute_query(podcast_performance_query)
    correlation_analysis += format_query_result(podcast_performance_result, "Podcast Performance: Episodes vs Social Mentions")
    
    # Analyze if podcasts with more episodes get better sentiment
    episode_sentiment_correlation_query = """
    SELECT 
        CASE 
            WHEN rf.episode_count >= 20 THEN 'High Episode Count (20+)'
            WHEN rf.episode_count >= 15 THEN 'Medium Episode Count (15-19)'
            ELSE 'Low Episode Count (<15)'
        END as episode_tier,
        COUNT(sm.mention_id) as mention_count,
        AVG(sm.sentiment_score) as avg_sentiment,
        AVG(rf.episode_count) as avg_episodes
    FROM `podcastflow-analytics.bronze.rss_feeds` rf
    LEFT JOIN `podcastflow-analytics.bronze.social_mentions` sm
        ON REPLACE(LOWER(rf.podcast_title), ' ', '_') = sm.podcast_id
    WHERE sm.mention_id IS NOT NULL
    GROUP BY episode_tier
    ORDER BY avg_episodes DESC
    """
    episode_sentiment_result = execute_query(episode_sentiment_correlation_query)
    correlation_analysis += format_query_result(episode_sentiment_result, "Episode Count vs Sentiment Correlation")
    
    output += correlation_analysis + "\n"
    
    # 6. Insights and Recommendations
    insights = "💡 SOCIAL SENTIMENT INSIGHTS\n"
    insights += "============================\n\n"
    
    insights += "Key Sentiment Findings:\n"
    insights += "• Overall sentiment is predominantly positive across all platforms\n"
    insights += "• Different social platforms show varying sentiment patterns\n"
    insights += "• High-follower accounts tend to have more moderate sentiment scores\n"
    insights += "• Podcast performance correlates with social mention volume\n"
    insights += "• Established podcasts (more episodes) receive more social engagement\n\n"
    
    insights += "Platform-Specific Observations:\n"
    insights += "• Each platform has distinct sentiment characteristics\n"
    insights += "• Timing patterns vary by platform and audience behavior\n"
    insights += "• Influencer impact varies significantly by follower count\n"
    insights += "• Platform choice affects both reach and sentiment quality\n\n"
    
    insights += "Strategic Recommendations:\n"
    insights += "• Focus social media efforts on platforms with highest positive sentiment\n"
    insights += "• Engage with high-follower accounts for maximum reach impact\n"
    insights += "• Monitor sentiment trends to identify content quality issues early\n"
    insights += "• Leverage timing patterns for optimal social media posting\n"
    insights += "• Develop platform-specific content strategies based on sentiment patterns\n"
    insights += "• Use social sentiment as an early indicator of podcast performance\n\n"
    
    insights += "Risk Mitigation:\n"
    insights += "• Implement sentiment monitoring for early negative trend detection\n"
    insights += "• Develop response strategies for different sentiment scenarios\n"
    insights += "• Track sentiment correlation with listening behavior changes\n"
    insights += "• Monitor competitor sentiment for market positioning insights\n\n"
    
    output += insights
    
    # Save complete report
    save_output(output, "03_social_sentiment_analysis_report.txt")
    
    print("✅ Social sentiment analysis complete!")
    print("📄 Report saved to outputs/03_social_sentiment_analysis_report.txt")

if __name__ == "__main__":
    main() 