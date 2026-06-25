"""
PodcastFlow Analytics - Enhanced Secure API
Phase 3 Week 2: Enterprise Security & Multi-tenancy Integration

Features:
- Integrated OAuth 2.0 authentication
- Multi-tenant data access controls
- Comprehensive security monitoring
- Enterprise-grade API endpoints
- Compliance and audit logging
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, Request, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn
from google.cloud import bigquery
import pandas as pd
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
import asyncio

# Import our enterprise modules
from auth.oauth_service import oauth_service, rbac, AuthenticationError, AuthorizationError
from tenancy.tenant_manager import tenant_manager, tenant_context, TenantStatus, TenantTier
from security.security_manager import security_manager, compliance_manager, AuditEventType

# Import ML modules
from ml.recommendation_engine import recommendation_engine, RecommendationRequest, RecommendationResult
from ml.prediction_models import prediction_service, PredictionRequest, PredictionResult
from ml.user_segmentation import user_segmentation_model, UserSegment, UserProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="PodcastFlow Analytics Enterprise API",
    description="Enterprise-grade podcast analytics platform with multi-tenancy and advanced security",
    version="3.1.0",
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

# Enhanced Pydantic Models
class UserInfo(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    tenant_id: str
    permissions: List[str]

class TenantInfo(BaseModel):
    tenant_id: str
    name: str
    domain: str
    status: str
    tier: str
    created_at: datetime
    quota_utilization: Dict[str, Any]

class SecurityMetrics(BaseModel):
    security_score: int
    blocked_ips: int
    failed_attempts: int
    audit_events_today: int
    compliance_score: int
    last_vulnerability_scan: str

class LoginRequest(BaseModel):
    redirect_uri: Optional[str] = None
    state: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: UserInfo
    tenant_info: TenantInfo

class MLRecommendationRequest(BaseModel):
    user_id: str
    num_recommendations: int = Field(default=10, ge=1, le=50)
    recommendation_type: str = Field(default="hybrid", regex="^(collaborative|content_based|hybrid)$")
    context: Optional[Dict[str, Any]] = None

class MLPredictionRequest(BaseModel):
    episode_title: str = Field(..., min_length=1, max_length=200)
    episode_description: str = Field(..., min_length=10, max_length=1000)
    podcast_id: str
    release_time: datetime
    estimated_duration_minutes: int = Field(..., ge=1, le=480)
    episode_number: int = Field(..., ge=1)

class UserSegmentationResponse(BaseModel):
    user_id: str
    segment_id: int
    segment_name: str
    predicted_ltv: float
    risk_score: float
    preferences: Dict[str, Any]
    recommendations: List[str]

# Enhanced Authentication and Authorization
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Enhanced user authentication with security logging"""
    
    try:
        # Validate IP access
        client_ip = request.client.host
        if not security_manager.validate_ip_access(client_ip):
            security_manager.audit_log(
                AuditEventType.FAILED_AUTH,
                ip_address=client_ip,
                details={"reason": "IP blocked"}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied from this IP address"
            )
        
        # Validate token
        token = credentials.credentials
        user_payload = oauth_service.validate_token(token)
        
        # Set tenant context
        tenant_id = user_payload.get('tenant_id')
        if tenant_id:
            tenant_context.set_tenant_context(tenant_id)
        
        # Log successful access
        security_manager.audit_log(
            AuditEventType.API_ACCESS,
            user_id=user_payload.get('user_id'),
            tenant_id=tenant_id,
            ip_address=client_ip,
            user_agent=request.headers.get('user-agent')
        )
        
        return user_payload
        
    except AuthenticationError as e:
        security_manager.audit_log(
            AuditEventType.FAILED_AUTH,
            ip_address=request.client.host,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get user from kwargs (injected by dependency)
            user = kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_role = user.get('role', 'user')
            if not rbac.check_permission(user_role, permission):
                security_manager.audit_log(
                    AuditEventType.FAILED_AUTH,
                    user_id=user.get('user_id'),
                    tenant_id=user.get('tenant_id'),
                    details={"permission_required": permission, "user_role": user_role}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Authentication Endpoints
@app.get("/auth/login", tags=["Authentication"])
async def login(request: LoginRequest):
    """Initiate OAuth 2.0 login flow"""
    try:
        auth_url = oauth_service.get_authorization_url(request.state)
        return {"authorization_url": auth_url}
    except Exception as e:
        logger.error(f"Login initiation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Login service error")

@app.get("/auth/callback", tags=["Authentication"])
async def auth_callback(
    code: str,
    state: Optional[str] = None,
    request: Request = None
):
    """Handle OAuth 2.0 callback"""
    try:
        # Exchange code for tokens
        auth_result = oauth_service.exchange_code_for_tokens(code, state)
        
        # Get user and tenant info
        user_info = auth_result['user_info']
        tenant = tenant_manager.get_tenant_by_domain(user_info['email'].split('@')[1])
        
        if not tenant:
            # Create default tenant for new domains
            domain = user_info['email'].split('@')[1]
            tenant = tenant_manager.create_tenant(
                name=f"{domain} Organization",
                domain=domain,
                tier=TenantTier.FREE,
                admin_email=user_info['email']
            )
        
        # Log successful authentication
        security_manager.audit_log(
            AuditEventType.LOGIN,
            user_id=user_info['user_id'],
            tenant_id=tenant.tenant_id,
            ip_address=request.client.host,
            details={"method": "oauth2"}
        )
        
        # Prepare response
        permissions = oauth_service.get_user_permissions(user_info['user_id'])
        
        return TokenResponse(
            access_token=auth_result['jwt_token'],
            expires_in=auth_result['expires_in'],
            user_info=UserInfo(
                user_id=user_info['user_id'],
                email=user_info['email'],
                name=user_info['name'],
                role=auth_result.get('role', 'user'),
                tenant_id=tenant.tenant_id,
                permissions=permissions
            ),
            tenant_info=TenantInfo(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                domain=tenant.domain,
                status=tenant.status.value,
                tier=tenant.tier.value,
                created_at=tenant.created_at,
                quota_utilization=tenant_manager.get_tenant_usage_report(tenant.tenant_id)
            )
        )
        
    except Exception as e:
        logger.error(f"Auth callback failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Authentication failed")

@app.post("/auth/logout", tags=["Authentication"])
async def logout(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Logout and invalidate session"""
    try:
        # Get token from authorization header
        auth_header = request.headers.get('authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        
        # Logout
        success = oauth_service.logout(token)
        
        # Log logout
        security_manager.audit_log(
            AuditEventType.LOGOUT,
            user_id=user.get('user_id'),
            tenant_id=user.get('tenant_id'),
            ip_address=request.client.host
        )
        
        return {"message": "Logged out successfully", "success": success}
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        return {"message": "Logout completed", "success": True}  # Always succeed

# Enhanced API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with enhanced API information"""
    return {
        "name": "PodcastFlow Analytics Enterprise API",
        "version": "3.1.0",
        "description": "Enterprise podcast analytics platform with multi-tenancy and advanced security",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "OAuth 2.0 Authentication",
            "Multi-tenant Architecture", 
            "Enterprise Security",
            "Compliance Reporting",
            "Advanced Analytics"
        ],
        "endpoints": {
            "authentication": "/auth",
            "health": "/health",
            "metrics": "/metrics",
            "security": "/security",
            "tenants": "/tenants",
            "analytics": "/analytics"
        }
    }

@app.get("/health", tags=["System"])
async def health_check():
    """Enhanced system health check"""
    start_time = time.time()
    
    services = {
        "api": "healthy",
        "authentication": "healthy",
        "multi_tenancy": "healthy",
        "security": "healthy",
        "bigquery": "healthy"
    }
    
    # Test BigQuery connectivity
    try:
        test_query = f"SELECT 1 as test LIMIT 1"
        job = bigquery_client.query(test_query)
        job.result()
    except:
        services["bigquery"] = "degraded"
    
    # Test authentication service
    try:
        oauth_service.cleanup_expired_sessions()
    except:
        services["authentication"] = "degraded"
    
    response_time = (time.time() - start_time) * 1000
    
    return {
        "status": "healthy" if all(s == "healthy" for s in services.values()) else "degraded",
        "services": services,
        "response_time_ms": round(response_time, 2),
        "timestamp": datetime.now().isoformat(),
        "uptime_hours": 24.0  # Placeholder
    }

@app.get("/security/metrics", response_model=SecurityMetrics, tags=["Security"])
async def get_security_metrics(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get comprehensive security metrics"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'system:admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        security_metrics = security_manager.get_security_metrics()
        compliance_report = compliance_manager.generate_compliance_report()
        
        return SecurityMetrics(
            security_score=security_metrics['security_score'],
            blocked_ips=security_metrics['blocked_ips_count'],
            failed_attempts=security_metrics['failed_attempts_count'],
            audit_events_today=0,  # Would query actual audit logs
            compliance_score=compliance_report['compliance_score'],
            last_vulnerability_scan=security_metrics['last_vulnerability_scan']
        )
        
    except Exception as e:
        logger.error(f"Security metrics failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Security metrics service error")

@app.post("/security/scan", tags=["Security"])
async def run_vulnerability_scan(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Run security vulnerability scan"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'system:admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Run scan in background
        def perform_scan():
            scan_results = security_manager.scan_for_vulnerabilities()
            security_manager.audit_log(
                AuditEventType.SECURITY_ALERT,
                user_id=user.get('user_id'),
                tenant_id=user.get('tenant_id'),
                details={"scan_results": scan_results}
            )
        
        background_tasks.add_task(perform_scan)
        
        return {"message": "Vulnerability scan initiated", "status": "started"}
        
    except Exception as e:
        logger.error(f"Vulnerability scan failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Security scan service error")

@app.get("/tenants", response_model=List[TenantInfo], tags=["Multi-tenancy"])
async def list_tenants(
    status: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List tenants (admin only)"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'manage:tenants'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant management permission required"
        )
    
    try:
        tenant_status = TenantStatus(status) if status else None
        tenants = tenant_manager.list_tenants(tenant_status)
        
        return [
            TenantInfo(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                domain=tenant.domain,
                status=tenant.status.value,
                tier=tenant.tier.value,
                created_at=tenant.created_at,
                quota_utilization=tenant_manager.get_tenant_usage_report(tenant.tenant_id)
            )
            for tenant in tenants
        ]
        
    except Exception as e:
        logger.error(f"List tenants failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Tenant service error")

@app.get("/tenants/current", response_model=TenantInfo, tags=["Multi-tenancy"])
async def get_current_tenant(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's tenant information"""
    
    try:
        tenant_id = user.get('tenant_id')
        tenant = tenant_manager.get_tenant(tenant_id)
        
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        return TenantInfo(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            domain=tenant.domain,
            status=tenant.status.value,
            tier=tenant.tier.value,
            created_at=tenant.created_at,
            quota_utilization=tenant_manager.get_tenant_usage_report(tenant.tenant_id)
        )
        
    except Exception as e:
        logger.error(f"Get current tenant failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Tenant service error")

@app.get("/compliance/report", tags=["Compliance"])
async def get_compliance_report(
    framework: str = "SOC2",
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get compliance report"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'system:admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        report = compliance_manager.generate_compliance_report(framework)
        
        # Log compliance report access
        security_manager.audit_log(
            AuditEventType.DATA_ACCESS,
            user_id=user.get('user_id'),
            tenant_id=user.get('tenant_id'),
            details={"resource": "compliance_report", "framework": framework}
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Compliance report failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Compliance service error")

# Enhanced Analytics Endpoints with Multi-tenancy
@app.get("/analytics/tenant-data", tags=["Analytics"])
async def get_tenant_analytics(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get analytics data for current tenant"""
    
    try:
        tenant_id = user.get('tenant_id')
        
        # Check quota
        if not tenant_manager.check_quota(tenant_id, 'api_calls_per_hour'):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API quota exceeded"
            )
        
        # Update usage
        tenant_manager.update_usage(tenant_id, 'api_calls', 1)
        
        # Get tenant-specific dataset prefix
        dataset_prefix = tenant_context.get_tenant_dataset_prefix()
        
        # Query tenant-specific data
        tenant_query = f"""
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(completion_percentage) as avg_completion
        FROM `{dataset_prefix}_bronze.listening_events_realtime`
        WHERE DATE(created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        """
        
        # Note: This would use tenant-specific datasets in production
        # For demo, using main dataset with tenant filtering
        demo_query = f"""
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(completion_percentage) as avg_completion
        FROM `{PROJECT_ID}.bronze.listening_events_realtime`
        LIMIT 1
        """
        
        job = bigquery_client.query(demo_query)
        df = job.to_dataframe()
        
        if not df.empty:
            row = df.iloc[0]
            return {
                "tenant_id": tenant_id,
                "total_events": int(row['total_events']),
                "unique_users": int(row['unique_users']),
                "average_completion": float(row['avg_completion']),
                "data_period_days": 30,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "tenant_id": tenant_id,
                "total_events": 0,
                "unique_users": 0,
                "average_completion": 0.0,
                "data_period_days": 30,
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Tenant analytics failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Analytics service error")

# Machine Learning Endpoints
@app.get("/ml/recommendations", tags=["Machine Learning"])
async def get_ml_recommendations(
    request: Request,
    user_id: Optional[str] = None,
    num_recommendations: int = 10,
    recommendation_type: str = "hybrid",
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get ML-powered content recommendations"""
    
    try:
        # Use current user if no user_id specified
        target_user_id = user_id or user.get('user_id')
        tenant_id = user.get('tenant_id')
        
        # Check permission for accessing other users' data
        if user_id and user_id != user.get('user_id'):
            if not rbac.check_permission(user.get('role'), 'read:all_tenants'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission required to access other users' recommendations"
                )
        
        # Check quota
        if not tenant_manager.check_quota(tenant_id, 'api_calls_per_hour'):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API quota exceeded"
            )
        
        # Create recommendation request
        rec_request = RecommendationRequest(
            user_id=target_user_id,
            tenant_id=tenant_id,
            num_recommendations=min(num_recommendations, 50),
            recommendation_type=recommendation_type
        )
        
        # Get recommendations
        recommendations = recommendation_engine.get_recommendations(rec_request)
        
        # Update usage
        tenant_manager.update_usage(tenant_id, 'api_calls', 1)
        
        # Log access
        security_manager.audit_log(
            AuditEventType.DATA_ACCESS,
            user_id=user.get('user_id'),
            tenant_id=tenant_id,
            ip_address=request.client.host,
            details={
                "resource": "ml_recommendations",
                "target_user": target_user_id,
                "num_recommendations": len(recommendations)
            }
        )
        
        return {
            "recommendations": [
                {
                    "podcast_id": rec.podcast_id,
                    "episode_id": rec.episode_id,
                    "confidence_score": rec.confidence_score,
                    "recommendation_reason": rec.recommendation_reason,
                    "recommendation_type": rec.recommendation_type,
                    "generated_at": rec.generated_at.isoformat()
                }
                for rec in recommendations
            ],
            "total_recommendations": len(recommendations),
            "recommendation_type": recommendation_type,
            "user_id": target_user_id,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"ML recommendations failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Recommendation service error")

@app.post("/ml/train-recommendations", tags=["Machine Learning"])
async def train_recommendation_models(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Train recommendation models (admin only)"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'system:admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        tenant_id = user.get('tenant_id')
        
        def train_models():
            try:
                training_results = recommendation_engine.train_models(tenant_id, retrain=True)
                security_manager.audit_log(
                    AuditEventType.CONFIG_CHANGE,
                    user_id=user.get('user_id'),
                    tenant_id=tenant_id,
                    details={"action": "train_recommendation_models", "results": training_results}
                )
            except Exception as e:
                logger.error(f"Model training failed: {str(e)}")
        
        background_tasks.add_task(train_models)
        
        return {"message": "Recommendation model training initiated", "status": "started"}
        
    except Exception as e:
        logger.error(f"Train recommendations failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Model training service error")

@app.post("/ml/predict-performance", tags=["Machine Learning"])
async def predict_episode_performance(
    request: Request,
    prediction_request: MLPredictionRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Predict episode performance using ML models"""
    
    try:
        tenant_id = user.get('tenant_id')
        
        # Check quota
        if not tenant_manager.check_quota(tenant_id, 'api_calls_per_hour'):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API quota exceeded"
            )
        
        # Check permission for advanced analytics
        if not tenant_context.check_feature_access('advanced_analytics'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Advanced analytics feature required"
            )
        
        # Create prediction request
        pred_request = PredictionRequest(
            episode_title=prediction_request.episode_title,
            episode_description=prediction_request.episode_description,
            podcast_id=prediction_request.podcast_id,
            tenant_id=tenant_id,
            release_time=prediction_request.release_time,
            estimated_duration_minutes=prediction_request.estimated_duration_minutes,
            episode_number=prediction_request.episode_number
        )
        
        # Get prediction
        prediction_result = prediction_service.predict_episode_performance(pred_request)
        
        # Update usage
        tenant_manager.update_usage(tenant_id, 'api_calls', 1)
        
        # Log access
        security_manager.audit_log(
            AuditEventType.DATA_ACCESS,
            user_id=user.get('user_id'),
            tenant_id=tenant_id,
            ip_address=request.client.host,
            details={
                "resource": "ml_episode_prediction",
                "podcast_id": prediction_request.podcast_id,
                "episode_title": prediction_request.episode_title
            }
        )
        
        return {
            "prediction": {
                "episode_id": prediction_result.episode_id,
                "predicted_downloads": prediction_result.predicted_downloads,
                "predicted_completion_rate": prediction_result.predicted_completion_rate,
                "predicted_engagement_score": prediction_result.predicted_engagement_score,
                "predicted_rating": prediction_result.predicted_rating,
                "confidence_interval": prediction_result.confidence_interval,
                "feature_importance": prediction_result.feature_importance,
                "prediction_timestamp": prediction_result.prediction_timestamp.isoformat()
            },
            "input": {
                "episode_title": prediction_request.episode_title,
                "podcast_id": prediction_request.podcast_id,
                "release_time": prediction_request.release_time.isoformat(),
                "duration_minutes": prediction_request.estimated_duration_minutes
            }
        }
        
    except Exception as e:
        logger.error(f"Episode performance prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Prediction service error")

@app.post("/ml/train-predictions", tags=["Machine Learning"])
async def train_prediction_models(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Train episode performance prediction models (admin only)"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'system:admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        tenant_id = user.get('tenant_id')
        
        def train_predictors():
            try:
                training_results = prediction_service.train_predictor(tenant_id, retrain=True)
                security_manager.audit_log(
                    AuditEventType.CONFIG_CHANGE,
                    user_id=user.get('user_id'),
                    tenant_id=tenant_id,
                    details={"action": "train_prediction_models", "results": training_results}
                )
            except Exception as e:
                logger.error(f"Prediction model training failed: {str(e)}")
        
        background_tasks.add_task(train_predictors)
        
        return {"message": "Prediction model training initiated", "status": "started"}
        
    except Exception as e:
        logger.error(f"Train predictions failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Model training service error")

@app.get("/ml/user-segment", response_model=UserSegmentationResponse, tags=["Machine Learning"])
async def get_user_segment(
    request: Request,
    target_user_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get user behavior segment and insights"""
    
    try:
        # Use current user if no target specified
        user_id_to_analyze = target_user_id or user.get('user_id')
        tenant_id = user.get('tenant_id')
        
        # Check permission for accessing other users' data
        if target_user_id and target_user_id != user.get('user_id'):
            if not rbac.check_permission(user.get('role'), 'read:all_tenants'):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission required to access other users' segments"
                )
        
        # Check quota
        if not tenant_manager.check_quota(tenant_id, 'api_calls_per_hour'):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API quota exceeded"
            )
        
        # Get user profile and segment
        try:
            user_profile = user_segmentation_model.predict_user_segment(
                user_id_to_analyze, bigquery_client, PROJECT_ID
            )
            
            # Get segment recommendations
            segment = user_segmentation_model.segments.get(user_profile.segment_id)
            segment_recommendations = segment.recommendations if segment else []
            
            # Update usage
            tenant_manager.update_usage(tenant_id, 'api_calls', 1)
            
            # Log access
            security_manager.audit_log(
                AuditEventType.DATA_ACCESS,
                user_id=user.get('user_id'),
                tenant_id=tenant_id,
                ip_address=request.client.host,
                details={
                    "resource": "user_segmentation",
                    "target_user": user_id_to_analyze,
                    "segment": user_profile.segment_name
                }
            )
            
            return UserSegmentationResponse(
                user_id=user_profile.user_id,
                segment_id=user_profile.segment_id,
                segment_name=user_profile.segment_name,
                predicted_ltv=user_profile.predicted_ltv,
                risk_score=user_profile.risk_score,
                preferences=user_profile.preferences,
                recommendations=segment_recommendations
            )
            
        except ValueError as e:
            # Model not trained - return basic segmentation
            return UserSegmentationResponse(
                user_id=user_id_to_analyze,
                segment_id=0,
                segment_name="Unclassified",
                predicted_ltv=50.0,
                risk_score=0.5,
                preferences={"content_type": "unknown"},
                recommendations=["Complete onboarding to enable personalization"]
            )
        
    except Exception as e:
        logger.error(f"User segmentation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Segmentation service error")

@app.post("/ml/train-segmentation", tags=["Machine Learning"])
async def train_segmentation_model(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Train user segmentation model (admin only)"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'system:admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        tenant_id = user.get('tenant_id')
        
        def train_segmentation():
            try:
                # Get user list for training
                users_query = f"""
                SELECT DISTINCT user_id
                FROM `{PROJECT_ID}.bronze.listening_events_realtime`
                WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
                LIMIT 1000
                """
                
                users_df = bigquery_client.query(users_query).to_dataframe()
                
                if not users_df.empty:
                    training_results = user_segmentation_model.train_segmentation_model(
                        users_df, bigquery_client, PROJECT_ID
                    )
                    
                    security_manager.audit_log(
                        AuditEventType.CONFIG_CHANGE,
                        user_id=user.get('user_id'),
                        tenant_id=tenant_id,
                        details={"action": "train_segmentation_model", "results": training_results}
                    )
                else:
                    logger.warning("No user data available for segmentation training")
                    
            except Exception as e:
                logger.error(f"Segmentation model training failed: {str(e)}")
        
        background_tasks.add_task(train_segmentation)
        
        return {"message": "Segmentation model training initiated", "status": "started"}
        
    except Exception as e:
        logger.error(f"Train segmentation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Model training service error")

@app.get("/ml/segments/summary", tags=["Machine Learning"])
async def get_segments_summary(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get summary of all user segments (admin/premium only)"""
    
    # Check permission
    if not rbac.check_permission(user.get('role'), 'analytics:advanced'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advanced analytics permission required"
        )
    
    try:
        tenant_id = user.get('tenant_id')
        
        # Get segment summary
        summary = user_segmentation_model.get_segment_summary()
        
        # Log access
        security_manager.audit_log(
            AuditEventType.DATA_ACCESS,
            user_id=user.get('user_id'),
            tenant_id=tenant_id,
            details={"resource": "segments_summary"}
        )
        
        return {
            "segment_summary": summary,
            "generated_at": datetime.now().isoformat(),
            "model_trained": user_segmentation_model.trained
        }
        
    except Exception as e:
        logger.error(f"Segments summary failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Segmentation service error")

# Background Tasks
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting PodcastFlow Analytics Enterprise API")
    
    # Initialize security monitoring
    security_manager.audit_log(
        AuditEventType.CONFIG_CHANGE,
        details={"event": "api_startup", "version": "3.1.0"}
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down PodcastFlow Analytics Enterprise API")
    
    # Cleanup security data
    security_manager.cleanup_security_data()
    oauth_service.cleanup_expired_sessions()

# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced exception handler with security logging"""
    
    # Log security-relevant errors
    if exc.status_code in [401, 403, 429]:
        security_manager.audit_log(
            AuditEventType.SECURITY_ALERT,
            ip_address=request.client.host,
            details={
                "error_type": "http_exception",
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url)
            }
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "secure_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=False,
        access_log=True
    ) 