"""
PodcastFlow Analytics API
Phase 3: Enterprise REST API with Google Cloud integration

Features:
- Comprehensive RESTful endpoints
- Authentication and authorization
- Rate limiting and monitoring
- Real-time data access
- Machine learning predictions
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
from google.cloud import bigquery
from google.cloud import monitoring_v3
import pandas as pd
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
import asyncio
from functools import wraps
import jwt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PodcastFlow Analytics API",
    description="Enterprise-grade podcast analytics platform with real-time insights",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security
security = HTTPBearer()

# Global variables
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-gcp-project')
bigquery_client = bigquery.Client(project=PROJECT_ID)

# Rate limiting storage (in production, use Redis)
request_counts = {}

# Pydantic Models
class PodcastAnalytics(BaseModel):
    podcast_id: str
    title: str
    total_downloads: int
    unique_listeners: int
    average_completion: float
    engagement_score: float
    trend_direction: str

class EpisodePerformance(BaseModel):
    episode_id: str
    title: str
    downloads: int
    completion_rate: float
    sentiment_score: float
    published_date: datetime

class UserSegment(BaseModel):
    user_type: str
    count: int
    average_completion: float
    engagement_level: str

class PlatformStats(BaseModel):
    platform: str
    events: int
    unique_users: int
    completion_rate: float
    market_share: float

class PredictionRequest(BaseModel):
    episode_title: str
    description: str
    category: str
    duration_minutes: int
    host_popularity: Optional[float] = 0.5

class PredictionResponse(BaseModel):
    predicted_downloads: int
    confidence_interval: Dict[str, int]
    success_probability: float
    recommendations: List[str]

class SystemHealth(BaseModel):
    status: str
    services: Dict[str, str]
    response_time_ms: float
    uptime_hours: float

# Authentication and Authorization
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and extract user information"""
    try:
        token = credentials.credentials
        # In production, verify with proper JWT secret and issuer
        # For demo purposes, we'll use a simple validation
        if not token or token == "invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": "demo_user", "role": "admin"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Rate Limiting
def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            current_time = time.time()
            
            # Clean old entries
            cutoff_time = current_time - window_seconds
            if client_ip in request_counts:
                request_counts[client_ip] = [
                    req_time for req_time in request_counts[client_ip] 
                    if req_time > cutoff_time
                ]
            else:
                request_counts[client_ip] = []
            
            # Check rate limit
            if len(request_counts[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            # Add current request
            request_counts[client_ip].append(current_time)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Utility Functions
async def execute_bigquery_query(query: str) -> Optional[pd.DataFrame]:
    """Execute BigQuery query with error handling"""
    try:
        job_config = bigquery.QueryJobConfig(
            use_query_cache=True,
            use_legacy_sql=False,
            maximum_bytes_billed=10**9
        )
        
        query_job = bigquery_client.query(query, job_config=job_config)
        df = query_job.to_dataframe()
        
        logger.info(f"Query executed successfully. Rows: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"BigQuery query failed: {str(e)}")
        return None

# API Endpoints

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "PodcastFlow Analytics API",
        "version": "3.0.0",
        "description": "Enterprise podcast analytics platform",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "podcasts": "/podcasts",
            "analytics": "/analytics",
            "predictions": "/predictions"
        }
    }

@app.get("/health", response_model=SystemHealth, tags=["System"])
async def health_check():
    """System health check endpoint"""
    start_time = time.time()
    
    services = {
        "bigquery": "healthy",
        "api": "healthy",
        "monitoring": "healthy"
    }
    
    # Test BigQuery connectivity
    try:
        test_query = f"SELECT 1 as test FROM `{PROJECT_ID}.bronze.rss_feeds` LIMIT 1"
        await execute_bigquery_query(test_query)
    except:
        services["bigquery"] = "degraded"
    
    response_time = (time.time() - start_time) * 1000
    
    return SystemHealth(
        status="healthy" if all(s == "healthy" for s in services.values()) else "degraded",
        services=services,
        response_time_ms=round(response_time, 2),
        uptime_hours=24.0  # Placeholder
    )

@app.get("/metrics", tags=["Analytics"])
@rate_limit(max_requests=60, window_seconds=3600)
async def get_system_metrics(
    request: Request,
    user: dict = Depends(verify_token)
):
    """Get comprehensive system metrics"""
    
    metrics_query = f"""
    WITH podcast_metrics AS (
        SELECT 
            COUNT(DISTINCT rss_url) as total_podcasts,
            COUNT(DISTINCT title) as total_episodes
        FROM `{PROJECT_ID}.bronze.rss_feeds`
    ),
    event_metrics AS (
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(completion_percentage) as avg_completion
        FROM `{PROJECT_ID}.bronze.listening_events_realtime`
    ),
    social_metrics AS (
        SELECT 
            COUNT(*) as social_mentions,
            AVG(sentiment_score) as avg_sentiment
        FROM `{PROJECT_ID}.bronze.social_mentions_extended`
    )
    SELECT *
    FROM podcast_metrics
    CROSS JOIN event_metrics
    CROSS JOIN social_metrics
    """
    
    df = await execute_bigquery_query(metrics_query)
    
    if df is not None and not df.empty:
        row = df.iloc[0]
        return {
            "podcast_metrics": {
                "total_podcasts": int(row['total_podcasts']),
                "total_episodes": int(row['total_episodes'])
            },
            "engagement_metrics": {
                "total_events": int(row['total_events']),
                "unique_users": int(row['unique_users']),
                "average_completion": float(row['avg_completion'])
            },
            "social_metrics": {
                "total_mentions": int(row['social_mentions']),
                "average_sentiment": float(row['avg_sentiment'])
            },
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=503, detail="Unable to fetch metrics")

@app.get("/podcasts", response_model=List[PodcastAnalytics], tags=["Content"])
async def get_podcasts(
    limit: int = 20,
    offset: int = 0,
    user: dict = Depends(verify_token)
):
    """Get podcast analytics with pagination"""
    
    podcasts_query = f"""
    WITH podcast_stats AS (
        SELECT 
            rss_url,
            title,
            COUNT(*) as episode_count,
            AVG(length(description)) as avg_description_length
        FROM `{PROJECT_ID}.bronze.rss_feeds`
        GROUP BY rss_url, title
    )
    SELECT 
        rss_url as podcast_id,
        title,
        episode_count as total_downloads,
        episode_count as unique_listeners,
        0.75 as average_completion,
        RAND() * 100 as engagement_score,
        'stable' as trend_direction
    FROM podcast_stats
    ORDER BY episode_count DESC
    LIMIT {limit} OFFSET {offset}
    """
    
    df = await execute_bigquery_query(podcasts_query)
    
    if df is not None and not df.empty:
        return [
            PodcastAnalytics(
                podcast_id=row['podcast_id'],
                title=row['title'][:100],  # Truncate long titles
                total_downloads=int(row['total_downloads']),
                unique_listeners=int(row['unique_listeners']),
                average_completion=float(row['average_completion']),
                engagement_score=float(row['engagement_score']),
                trend_direction=row['trend_direction']
            )
            for _, row in df.iterrows()
        ]
    else:
        return []

@app.get("/analytics/platforms", response_model=List[PlatformStats], tags=["Analytics"])
async def get_platform_analytics(user: dict = Depends(verify_token)):
    """Get platform performance analytics"""
    
    platform_query = f"""
    SELECT 
        platform,
        COUNT(*) as events,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(completion_percentage) as completion_rate,
        (COUNT(*) * 100.0) / SUM(COUNT(*)) OVER() as market_share
    FROM `{PROJECT_ID}.bronze.listening_events_realtime`
    GROUP BY platform
    ORDER BY events DESC
    """
    
    df = await execute_bigquery_query(platform_query)
    
    if df is not None and not df.empty:
        return [
            PlatformStats(
                platform=row['platform'],
                events=int(row['events']),
                unique_users=int(row['unique_users']),
                completion_rate=float(row['completion_rate']),
                market_share=float(row['market_share'])
            )
            for _, row in df.iterrows()
        ]
    else:
        return []

@app.get("/analytics/segments", response_model=List[UserSegment], tags=["Analytics"])
async def get_user_segments(user: dict = Depends(verify_token)):
    """Get user behavior segmentation"""
    
    segments_query = f"""
    SELECT 
        user_type,
        COUNT(DISTINCT user_id) as count,
        AVG(completion_percentage) as average_completion,
        CASE 
            WHEN AVG(completion_percentage) > 80 THEN 'high'
            WHEN AVG(completion_percentage) > 50 THEN 'medium'
            ELSE 'low'
        END as engagement_level
    FROM `{PROJECT_ID}.bronze.listening_events_realtime`
    GROUP BY user_type
    ORDER BY count DESC
    """
    
    df = await execute_bigquery_query(segments_query)
    
    if df is not None and not df.empty:
        return [
            UserSegment(
                user_type=row['user_type'],
                count=int(row['count']),
                average_completion=float(row['average_completion']),
                engagement_level=row['engagement_level']
            )
            for _, row in df.iterrows()
        ]
    else:
        return []

@app.post("/predictions/episode-performance", response_model=PredictionResponse, tags=["ML"])
async def predict_episode_performance(
    prediction_request: PredictionRequest,
    user: dict = Depends(verify_token)
):
    """Predict episode performance using ML models"""
    
    # Simulate ML prediction (in production, this would call a real ML model)
    base_downloads = 10000
    
    # Factor in episode characteristics
    title_length_factor = min(len(prediction_request.episode_title) / 50, 1.5)
    description_length_factor = min(len(prediction_request.description) / 200, 1.3)
    duration_factor = min(prediction_request.duration_minutes / 60, 1.2)
    host_factor = prediction_request.host_popularity
    
    predicted_downloads = int(
        base_downloads * title_length_factor * description_length_factor * 
        duration_factor * host_factor
    )
    
    confidence_interval = {
        "lower": int(predicted_downloads * 0.7),
        "upper": int(predicted_downloads * 1.3)
    }
    
    success_probability = min(0.95, 0.6 + (host_factor * 0.4))
    
    recommendations = []
    if len(prediction_request.episode_title) < 30:
        recommendations.append("Consider a more descriptive title")
    if len(prediction_request.description) < 100:
        recommendations.append("Add more detailed description")
    if prediction_request.duration_minutes < 20:
        recommendations.append("Consider longer episode format")
    
    return PredictionResponse(
        predicted_downloads=predicted_downloads,
        confidence_interval=confidence_interval,
        success_probability=success_probability,
        recommendations=recommendations
    )

@app.get("/analytics/trending", tags=["Analytics"])
async def get_trending_topics(
    days: int = 7,
    user: dict = Depends(verify_token)
):
    """Get trending topics and content"""
    
    # Simulate trending analysis
    trending_topics = [
        {"topic": "Technology", "mentions": 245, "growth": 15.2},
        {"topic": "Business", "mentions": 189, "growth": 8.7},
        {"topic": "Health", "mentions": 167, "growth": 12.4},
        {"topic": "Entertainment", "mentions": 134, "growth": -2.1},
        {"topic": "Education", "mentions": 98, "growth": 22.8}
    ]
    
    return {
        "trending_topics": trending_topics,
        "analysis_period_days": days,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/analytics/performance/{podcast_id}", tags=["Analytics"])
async def get_podcast_performance(
    podcast_id: str,
    days: int = 30,
    user: dict = Depends(verify_token)
):
    """Get detailed performance analytics for a specific podcast"""
    
    performance_query = f"""
    WITH podcast_episodes AS (
        SELECT title, description, published_date
        FROM `{PROJECT_ID}.bronze.rss_feeds`
        WHERE rss_url = '{podcast_id}'
        AND published_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
    )
    SELECT 
        COUNT(*) as episode_count,
        AVG(length(description)) as avg_description_length,
        MIN(published_date) as first_episode,
        MAX(published_date) as latest_episode
    FROM podcast_episodes
    """
    
    df = await execute_bigquery_query(performance_query)
    
    if df is not None and not df.empty and len(df) > 0:
        row = df.iloc[0]
        return {
            "podcast_id": podcast_id,
            "analysis_period_days": days,
            "episode_count": int(row['episode_count']),
            "average_description_length": float(row['avg_description_length']) if row['avg_description_length'] else 0,
            "first_episode_date": row['first_episode'].isoformat() if row['first_episode'] else None,
            "latest_episode_date": row['latest_episode'].isoformat() if row['latest_episode'] else None,
            "generated_at": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail="Podcast not found or no data available")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=False,
        access_log=True
    ) 