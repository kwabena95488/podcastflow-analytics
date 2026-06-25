"""
Database Query Optimization Module for PodcastFlow Analytics Platform
Implements BigQuery-specific optimizations including partitioning, clustering, and caching
"""

import time
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

from google.cloud import bigquery
from google.cloud.bigquery import job
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QueryStats:
    """Container for query performance statistics"""
    query_hash: str
    execution_time: float
    bytes_processed: int
    bytes_billed: int
    slot_time: int
    cache_hit: bool
    job_id: str
    timestamp: datetime

class ConnectionPool:
    """Thread-safe BigQuery connection pool"""
    
    def __init__(self, project_id: str, max_connections: int = 20):
        self.project_id = project_id
        self.max_connections = max_connections
        self._connections = {}
        self._lock = threading.Lock()
        
    def get_client(self) -> bigquery.Client:
        """Get or create a BigQuery client for the current thread"""
        thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._connections:
                if len(self._connections) < self.max_connections:
                    self._connections[thread_id] = bigquery.Client(project=self.project_id)
                else:
                    # Reuse oldest connection
                    oldest_thread = min(self._connections.keys())
                    self._connections[thread_id] = self._connections.pop(oldest_thread)
            
            return self._connections[thread_id]
    
    def close_all(self):
        """Close all connections"""
        with self._lock:
            self._connections.clear()

class QueryCache:
    """In-memory query result cache with TTL"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.Lock()
    
    def _generate_key(self, query: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for query"""
        content = query + str(params or {})
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, query: str, params: Optional[Dict] = None) -> Optional[Any]:
        """Get cached query result"""
        key = self._generate_key(query, params)
        
        with self._lock:
            if key in self._cache:
                # Check if cache entry is still valid
                timestamp = self._timestamps[key]
                if time.time() - timestamp < self.default_ttl:
                    return self._cache[key]
                else:
                    # Remove expired entry
                    del self._cache[key]
                    del self._timestamps[key]
        
        return None
    
    def set(self, query: str, result: Any, params: Optional[Dict] = None, ttl: Optional[int] = None):
        """Cache query result"""
        key = self._generate_key(query, params)
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Remove oldest entries if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = result
            self._timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

class OptimizedBigQueryClient:
    """Optimized BigQuery client with caching and connection pooling"""
    
    def __init__(self, project_id: str, max_connections: int = 20, cache_size: int = 1000):
        self.project_id = project_id
        self.connection_pool = ConnectionPool(project_id, max_connections)
        self.cache = QueryCache(cache_size)
        self.query_stats: List[QueryStats] = []
        
        # Performance settings
        self.default_job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            use_legacy_sql=False,
            maximum_bytes_billed=10**11  # 100GB limit
        )
    
    def execute_optimized_query(
        self, 
        query: str, 
        params: Optional[Dict] = None,
        use_cache: bool = True,
        job_config: Optional[bigquery.QueryJobConfig] = None
    ) -> pd.DataFrame:
        """Execute query with optimization and caching"""
        
        # Check cache first
        if use_cache:
            cached_result = self.cache.get(query, params)
            if cached_result is not None:
                logger.info("Query result retrieved from cache")
                return cached_result
        
        # Execute query
        client = self.connection_pool.get_client()
        config = job_config or self.default_job_config
        
        start_time = time.time()
        
        try:
            if params:
                # Parameterized query
                query_job = client.query(query, job_config=config, job_params=params)
            else:
                query_job = client.query(query, job_config=config)
            
            # Get results
            results = query_job.result()
            df = results.to_dataframe()
            
            execution_time = time.time() - start_time
            
            # Record query statistics
            stats = QueryStats(
                query_hash=hashlib.sha256(query.encode()).hexdigest()[:16],
                execution_time=execution_time,
                bytes_processed=query_job.total_bytes_processed or 0,
                bytes_billed=query_job.total_bytes_billed or 0,
                slot_time=query_job.slot_millis or 0,
                cache_hit=query_job.cache_hit or False,
                job_id=query_job.job_id,
                timestamp=datetime.utcnow()
            )
            self.query_stats.append(stats)
            
            # Cache results
            if use_cache and len(df) < 10000:  # Only cache smaller results
                self.cache.set(query, df, params)
            
            logger.info(f"Query executed in {execution_time:.2f}s, "
                       f"processed {stats.bytes_processed:,} bytes")
            
            return df
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def create_optimized_table(
        self, 
        table_id: str, 
        schema: List[bigquery.SchemaField],
        partition_field: Optional[str] = None,
        cluster_fields: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> bigquery.Table:
        """Create optimized table with partitioning and clustering"""
        
        client = self.connection_pool.get_client()
        
        # Create table reference
        table_ref = client.dataset(table_id.split('.')[0]).table(table_id.split('.')[1])
        table = bigquery.Table(table_ref, schema=schema)
        
        # Configure partitioning
        if partition_field:
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field=partition_field
            )
            logger.info(f"Configured daily partitioning on field: {partition_field}")
        
        # Configure clustering
        if cluster_fields:
            table.clustering_fields = cluster_fields
            logger.info(f"Configured clustering on fields: {cluster_fields}")
        
        # Set description
        if description:
            table.description = description
        
        # Create table
        table = client.create_table(table)
        logger.info(f"Created optimized table: {table_id}")
        
        return table
    
    def create_materialized_view(
        self,
        view_id: str,
        query: str,
        refresh_interval_minutes: int = 60,
        enable_refresh: bool = True
    ) -> bigquery.Table:
        """Create materialized view for frequently accessed data"""
        
        client = self.connection_pool.get_client()
        
        # Create materialized view
        view_sql = f"""
        CREATE MATERIALIZED VIEW `{view_id}`
        OPTIONS(
            enable_refresh = {str(enable_refresh).lower()},
            refresh_interval_minutes = {refresh_interval_minutes}
        )
        AS {query}
        """
        
        query_job = client.query(view_sql)
        query_job.result()  # Wait for completion
        
        logger.info(f"Created materialized view: {view_id} "
                   f"with {refresh_interval_minutes}min refresh interval")
        
        return client.get_table(view_id)
    
    def analyze_query_performance(self, query: str) -> Dict[str, Any]:
        """Analyze query performance and suggest optimizations"""
        
        # Dry run to get query statistics
        client = self.connection_pool.get_client()
        
        dry_run_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        dry_run_job = client.query(query, job_config=dry_run_config)
        
        analysis = {
            "estimated_bytes_processed": dry_run_job.total_bytes_processed,
            "estimated_cost_usd": (dry_run_job.total_bytes_processed / (1024**4)) * 5,  # Rough estimate
            "query_complexity": self._assess_query_complexity(query),
            "optimization_suggestions": self._generate_optimization_suggestions(query)
        }
        
        return analysis
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess query complexity level"""
        query_lower = query.lower()
        
        complexity_indicators = {
            "simple": ["select", "from", "where", "limit"],
            "medium": ["join", "group by", "order by", "having"],
            "complex": ["window", "partition", "recursive", "pivot", "unpivot"],
            "very_complex": ["array", "struct", "nested", "ml.", "regexp"]
        }
        
        score = 0
        for level, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in query_lower:
                    if level == "simple":
                        score += 1
                    elif level == "medium":
                        score += 2
                    elif level == "complex":
                        score += 3
                    elif level == "very_complex":
                        score += 4
        
        if score <= 5:
            return "simple"
        elif score <= 15:
            return "medium"
        elif score <= 25:
            return "complex"
        else:
            return "very_complex"
    
    def _generate_optimization_suggestions(self, query: str) -> List[str]:
        """Generate query optimization suggestions"""
        suggestions = []
        query_lower = query.lower()
        
        # Check for common optimization opportunities
        if "select *" in query_lower:
            suggestions.append("Consider selecting only required columns instead of SELECT *")
        
        if "where" not in query_lower and "from" in query_lower:
            suggestions.append("Consider adding WHERE clause to filter data")
        
        if "order by" in query_lower and "limit" not in query_lower:
            suggestions.append("Consider adding LIMIT when using ORDER BY")
        
        if "group by" in query_lower and "having" in query_lower:
            suggestions.append("Consider moving filters from HAVING to WHERE when possible")
        
        if "join" in query_lower:
            suggestions.append("Ensure JOIN conditions use partitioned/clustered columns")
        
        if not any(partition_hint in query_lower for partition_hint in ["_table_suffix", "date(", "timestamp("]):
            suggestions.append("Consider using partition pruning for time-based queries")
        
        return suggestions
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report from collected statistics"""
        if not self.query_stats:
            return {"message": "No query statistics available"}
        
        total_queries = len(self.query_stats)
        total_bytes_processed = sum(stat.bytes_processed for stat in self.query_stats)
        total_execution_time = sum(stat.execution_time for stat in self.query_stats)
        cache_hit_rate = sum(1 for stat in self.query_stats if stat.cache_hit) / total_queries
        
        avg_execution_time = total_execution_time / total_queries
        avg_bytes_processed = total_bytes_processed / total_queries
        
        return {
            "total_queries": total_queries,
            "total_bytes_processed": total_bytes_processed,
            "total_execution_time": total_execution_time,
            "avg_execution_time": avg_execution_time,
            "avg_bytes_processed": avg_bytes_processed,
            "cache_hit_rate": cache_hit_rate,
            "estimated_cost_usd": (total_bytes_processed / (1024**4)) * 5,
            "slowest_queries": sorted(
                self.query_stats, 
                key=lambda x: x.execution_time, 
                reverse=True
            )[:5],
            "most_expensive_queries": sorted(
                self.query_stats, 
                key=lambda x: x.bytes_processed, 
                reverse=True
            )[:5]
        }

class PodcastAnalyticsQueries:
    """Optimized queries specific to podcast analytics"""
    
    def __init__(self, client: OptimizedBigQueryClient, dataset_prefix: str = "podcastflow"):
        self.client = client
        self.bronze_dataset = f"{dataset_prefix}_bronze"
        self.silver_dataset = f"{dataset_prefix}_silver"
        self.gold_dataset = f"{dataset_prefix}_gold"
    
    def get_podcast_performance_metrics(
        self, 
        podcast_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """Get optimized podcast performance metrics"""
        
        # Build dynamic WHERE clause
        where_conditions = []
        params = {}
        
        if podcast_id:
            where_conditions.append("podcast_id = @podcast_id")
            params["podcast_id"] = podcast_id
        
        if start_date:
            where_conditions.append("published_date >= @start_date")
            params["start_date"] = start_date
        
        if end_date:
            where_conditions.append("published_date <= @end_date")
            params["end_date"] = end_date
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"""
        SELECT 
            podcast_id,
            title,
            COUNT(episode_id) as total_episodes,
            SUM(download_count) as total_downloads,
            AVG(rating) as avg_rating,
            AVG(completion_rate) as avg_completion_rate,
            SUM(total_listening_time) as total_listening_hours,
            MAX(published_date) as latest_episode_date,
            COUNTIF(published_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as episodes_last_30_days
        FROM `{self.client.project_id}.{self.gold_dataset}.podcast_episode_metrics`
        WHERE {where_clause}
        GROUP BY podcast_id, title
        ORDER BY total_downloads DESC
        LIMIT {limit}
        """
        
        return self.client.execute_optimized_query(query, params)
    
    def get_user_engagement_analytics(
        self,
        tenant_id: str,
        date_range_days: int = 30,
        segment: Optional[str] = None
    ) -> pd.DataFrame:
        """Get user engagement analytics with optimization"""
        
        params = {
            "tenant_id": tenant_id,
            "start_date": (datetime.now() - timedelta(days=date_range_days)).strftime("%Y-%m-%d")
        }
        
        segment_filter = ""
        if segment:
            segment_filter = "AND user_segment = @segment"
            params["segment"] = segment
        
        query = f"""
        WITH user_metrics AS (
            SELECT 
                user_id,
                user_segment,
                COUNT(DISTINCT session_id) as total_sessions,
                SUM(session_duration_minutes) as total_listening_minutes,
                AVG(session_duration_minutes) as avg_session_duration,
                COUNT(DISTINCT episode_id) as unique_episodes_listened,
                AVG(completion_percentage) as avg_completion_rate,
                COUNT(DISTINCT DATE(session_start_time)) as active_days
            FROM `{self.client.project_id}.{self.silver_dataset}.user_listening_sessions`
            WHERE tenant_id = @tenant_id 
                AND DATE(session_start_time) >= @start_date
                {segment_filter}
            GROUP BY user_id, user_segment
        )
        SELECT 
            user_segment,
            COUNT(*) as user_count,
            AVG(total_sessions) as avg_sessions_per_user,
            AVG(total_listening_minutes) as avg_listening_minutes,
            AVG(avg_session_duration) as avg_session_duration,
            AVG(unique_episodes_listened) as avg_unique_episodes,
            AVG(avg_completion_rate) as avg_completion_rate,
            AVG(active_days) as avg_active_days
        FROM user_metrics
        GROUP BY user_segment
        ORDER BY user_count DESC
        """
        
        return self.client.execute_optimized_query(query, params)
    
    def get_real_time_dashboard_metrics(self, tenant_id: str) -> pd.DataFrame:
        """Get real-time dashboard metrics using materialized views"""
        
        # This would use a pre-created materialized view for performance
        query = f"""
        SELECT 
            metric_name,
            metric_value,
            metric_change_24h,
            last_updated
        FROM `{self.client.project_id}.{self.gold_dataset}.dashboard_metrics_mv`
        WHERE tenant_id = @tenant_id
            AND last_updated >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        ORDER BY metric_name
        """
        
        params = {"tenant_id": tenant_id}
        return self.client.execute_optimized_query(query, params)
    
    def get_trending_content(
        self,
        tenant_id: str,
        time_window_hours: int = 24,
        min_interactions: int = 10,
        limit: int = 20
    ) -> pd.DataFrame:
        """Get trending content with optimized time-window queries"""
        
        query = f"""
        WITH recent_activity AS (
            SELECT 
                episode_id,
                podcast_id,
                COUNT(*) as interaction_count,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(completion_percentage) as avg_completion,
                SUM(session_duration_minutes) as total_minutes
            FROM `{self.client.project_id}.{self.silver_dataset}.user_listening_sessions`
            WHERE tenant_id = @tenant_id
                AND session_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @time_window_hours HOUR)
            GROUP BY episode_id, podcast_id
            HAVING interaction_count >= @min_interactions
        ),
        episode_details AS (
            SELECT 
                e.episode_id,
                e.title as episode_title,
                p.title as podcast_title,
                e.category,
                e.published_date
            FROM `{self.client.project_id}.{self.bronze_dataset}.episodes` e
            JOIN `{self.client.project_id}.{self.bronze_dataset}.podcasts` p
                ON e.podcast_id = p.podcast_id
        )
        SELECT 
            ed.episode_id,
            ed.episode_title,
            ed.podcast_title,
            ed.category,
            ra.interaction_count,
            ra.unique_users,
            ra.avg_completion,
            ra.total_minutes,
            ROUND(ra.interaction_count * ra.avg_completion * LOG(ra.unique_users + 1), 2) as trending_score
        FROM recent_activity ra
        JOIN episode_details ed ON ra.episode_id = ed.episode_id
        ORDER BY trending_score DESC
        LIMIT {limit}
        """
        
        params = {
            "tenant_id": tenant_id,
            "time_window_hours": time_window_hours,
            "min_interactions": min_interactions
        }
        
        return self.client.execute_optimized_query(query, params)

def setup_optimized_tables(client: OptimizedBigQueryClient, dataset_prefix: str = "podcastflow"):
    """Set up optimized table structure for podcast analytics"""
    
    # Define schemas with optimizations
    schemas = {
        f"{dataset_prefix}_bronze.listening_events": {
            "schema": [
                bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("episode_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("session_start_time", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("session_duration_minutes", "FLOAT"),
                bigquery.SchemaField("completion_percentage", "FLOAT"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
            ],
            "partition_field": "session_start_time",
            "cluster_fields": ["tenant_id", "user_id", "episode_id"]
        },
        
        f"{dataset_prefix}_silver.user_engagement_metrics": {
            "schema": [
                bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("metric_date", "DATE", mode="REQUIRED"),
                bigquery.SchemaField("total_listening_minutes", "FLOAT"),
                bigquery.SchemaField("session_count", "INTEGER"),
                bigquery.SchemaField("unique_episodes", "INTEGER"),
                bigquery.SchemaField("avg_completion_rate", "FLOAT"),
            ],
            "partition_field": "metric_date",
            "cluster_fields": ["tenant_id", "user_id"]
        },
        
        f"{dataset_prefix}_gold.podcast_analytics": {
            "schema": [
                bigquery.SchemaField("podcast_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("report_date", "DATE", mode="REQUIRED"),
                bigquery.SchemaField("total_downloads", "INTEGER"),
                bigquery.SchemaField("unique_listeners", "INTEGER"),
                bigquery.SchemaField("total_listening_hours", "FLOAT"),
                bigquery.SchemaField("avg_rating", "FLOAT"),
                bigquery.SchemaField("engagement_score", "FLOAT"),
            ],
            "partition_field": "report_date",
            "cluster_fields": ["tenant_id", "podcast_id"]
        }
    }
    
    # Create optimized tables
    for table_id, config in schemas.items():
        try:
            client.create_optimized_table(
                table_id=table_id,
                schema=config["schema"],
                partition_field=config.get("partition_field"),
                cluster_fields=config.get("cluster_fields"),
                description=f"Optimized table for {table_id.split('.')[-1]}"
            )
            logger.info(f"Created optimized table: {table_id}")
        except Exception as e:
            logger.warning(f"Table {table_id} may already exist: {e}")

# Example usage and testing
if __name__ == "__main__":
    # Initialize optimized client
    project_id = "your-project-id"
    client = OptimizedBigQueryClient(project_id)
    
    # Set up optimized tables
    setup_optimized_tables(client)
    
    # Initialize queries
    queries = PodcastAnalyticsQueries(client)
    
    # Example: Get performance metrics
    metrics = queries.get_podcast_performance_metrics(limit=10)
    print(f"Retrieved {len(metrics)} podcast metrics")
    
    # Generate performance report
    report = client.get_performance_report()
    print(f"Performance Report: {report}")
    
    # Clean up
    client.connection_pool.close_all() 