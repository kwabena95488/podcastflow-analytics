"""
Integration tests for API endpoints and services
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sys
import os

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from api.secure_main import app

class TestAPIAuthentication:
    """Test API authentication and authorization"""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing"""
        return TestClient(app)
    
    @pytest.fixture
    def valid_token(self):
        """Mock valid JWT token"""
        return "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_token"
    
    @pytest.fixture
    def invalid_token(self):
        """Mock invalid JWT token"""
        return "Bearer invalid_token"
    
    def test_health_endpoint_no_auth(self, client):
        """Test health endpoint that doesn't require authentication"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_protected_endpoint_no_token(self, client):
        """Test protected endpoint without token returns 401"""
        response = client.get("/api/v1/podcasts")
        assert response.status_code == 401
    
    def test_protected_endpoint_invalid_token(self, client, invalid_token):
        """Test protected endpoint with invalid token returns 401"""
        headers = {"Authorization": invalid_token}
        response = client.get("/api/v1/podcasts", headers=headers)
        assert response.status_code == 401
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    def test_protected_endpoint_valid_token(self, mock_validate, client, valid_token):
        """Test protected endpoint with valid token returns data"""
        # Mock successful token validation
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        headers = {"Authorization": valid_token}
        response = client.get("/api/v1/podcasts", headers=headers)
        assert response.status_code == 200
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    def test_admin_endpoint_requires_admin_role(self, mock_validate, client, valid_token):
        """Test admin endpoint requires admin role"""
        # Mock user without admin role
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        headers = {"Authorization": valid_token}
        response = client.post("/api/v1/admin/users", headers=headers, json={})
        assert response.status_code == 403
        
        # Mock user with admin role
        mock_validate.return_value['roles'] = ['admin']
        response = client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 200


class TestMultiTenancy:
    """Test multi-tenant functionality"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def tenant_a_token(self):
        return "Bearer tenant_a_token"
    
    @pytest.fixture
    def tenant_b_token(self):
        return "Bearer tenant_b_token"
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('tenancy.tenant_manager.TenantManager.get_tenant_context')
    def test_tenant_data_isolation(self, mock_tenant_context, mock_validate, 
                                   client, tenant_a_token, tenant_b_token):
        """Test that tenants can only access their own data"""
        
        # Mock Tenant A user
        mock_validate.return_value = {
            'user_id': 'user_a',
            'tenant_id': 'tenant_a',
            'email': 'user_a@tenant_a.com',
            'roles': ['user']
        }
        mock_tenant_context.return_value = {
            'tenant_id': 'tenant_a',
            'name': 'Tenant A',
            'subscription_tier': 'premium'
        }
        
        headers_a = {"Authorization": tenant_a_token}
        response_a = client.get("/api/v1/podcasts", headers=headers_a)
        assert response_a.status_code == 200
        
        # Mock Tenant B user
        mock_validate.return_value = {
            'user_id': 'user_b',
            'tenant_id': 'tenant_b',
            'email': 'user_b@tenant_b.com',
            'roles': ['user']
        }
        mock_tenant_context.return_value = {
            'tenant_id': 'tenant_b',
            'name': 'Tenant B',
            'subscription_tier': 'free'
        }
        
        headers_b = {"Authorization": tenant_b_token}
        response_b = client.get("/api/v1/podcasts", headers=headers_b)
        assert response_b.status_code == 200
        
        # Verify responses are different (tenant isolation)
        assert response_a.json() != response_b.json()
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('tenancy.tenant_manager.TenantManager.check_resource_quota')
    def test_tenant_resource_quotas(self, mock_quota_check, mock_validate, client, tenant_a_token):
        """Test tenant resource quota enforcement"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        # Mock quota exceeded
        mock_quota_check.return_value = False
        
        headers = {"Authorization": tenant_a_token}
        response = client.post("/api/v1/podcasts", headers=headers, json={
            "title": "Test Podcast",
            "description": "Test Description"
        })
        assert response.status_code == 429  # Too Many Requests
        
        # Mock quota available
        mock_quota_check.return_value = True
        response = client.post("/api/v1/podcasts", headers=headers, json={
            "title": "Test Podcast",
            "description": "Test Description"
        })
        assert response.status_code == 201


class TestMLEndpoints:
    """Test ML-powered API endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer valid_token"}
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('ml.recommendation_engine.RecommendationEngine.generate_recommendations')
    def test_recommendation_endpoint(self, mock_recommendations, mock_validate, 
                                     client, auth_headers):
        """Test content recommendation endpoint"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        mock_recommendations.return_value = [
            {
                'episode_id': 'ep1',
                'title': 'AI Revolution',
                'score': 0.95,
                'confidence': 0.88,
                'reason': 'High user affinity for technology content'
            },
            {
                'episode_id': 'ep2',
                'title': 'Machine Learning Basics',
                'score': 0.87,
                'confidence': 0.82,
                'reason': 'Similar content preferences'
            }
        ]
        
        response = client.get("/api/v1/recommendations/test_user", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'recommendations' in data
        assert len(data['recommendations']) == 2
        assert data['recommendations'][0]['score'] == 0.95
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('ml.prediction_models.PerformancePredictionModel.predict_performance')
    def test_performance_prediction_endpoint(self, mock_prediction, mock_validate, 
                                             client, auth_headers):
        """Test episode performance prediction endpoint"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        mock_prediction.return_value = {
            'predicted_downloads': 4500,
            'predicted_completion_rate': 0.83,
            'predicted_engagement_score': 7.8,
            'predicted_rating': 4.4,
            'confidence_intervals': {
                'downloads': [4000, 5000],
                'completion_rate': [0.78, 0.88],
                'engagement_score': [7.2, 8.4],
                'rating': [4.0, 4.8]
            }
        }
        
        episode_data = {
            'title': 'Future of AI',
            'duration_minutes': 45,
            'category': 'Technology',
            'description': 'Discussion about artificial intelligence trends',
            'release_schedule': 'morning'
        }
        
        response = client.post("/api/v1/predictions/episode-performance", 
                              headers=auth_headers, json=episode_data)
        assert response.status_code == 200
        
        data = response.json()
        assert 'predicted_downloads' in data
        assert 'confidence_intervals' in data
        assert data['predicted_downloads'] == 4500
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('ml.user_segmentation.UserSegmentationModel.segment_users')
    def test_user_segmentation_endpoint(self, mock_segmentation, mock_validate, 
                                        client, auth_headers):
        """Test user segmentation endpoint"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['admin']
        }
        
        mock_segmentation.return_value = {
            'segments': [
                {
                    'segment_id': 0,
                    'name': 'Power Listeners',
                    'size': 150,
                    'characteristics': {
                        'avg_listening_hours': 35.2,
                        'completion_rate': 0.89,
                        'engagement_score': 8.7
                    }
                },
                {
                    'segment_id': 1,
                    'name': 'Casual Browsers',
                    'size': 320,
                    'characteristics': {
                        'avg_listening_hours': 8.5,
                        'completion_rate': 0.65,
                        'engagement_score': 5.2
                    }
                }
            ],
            'total_users': 470
        }
        
        response = client.get("/api/v1/analytics/user-segments", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'segments' in data
        assert len(data['segments']) == 2
        assert data['total_users'] == 470


class TestAnalyticsEndpoints:
    """Test analytics and dashboard endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        return {"Authorization": "Bearer valid_token"}
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('google.cloud.bigquery.Client')
    def test_podcast_analytics_endpoint(self, mock_bigquery, mock_validate, 
                                        client, auth_headers):
        """Test podcast analytics endpoint"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        # Mock BigQuery response
        mock_client = Mock()
        mock_bigquery.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            {
                'podcast_id': 'POD001',
                'title': 'Tech Talk Daily',
                'total_downloads': 50000,
                'average_rating': 4.5,
                'completion_rate': 0.85,
                'engagement_score': 8.2
            }
        ]
        
        response = client.get("/api/v1/analytics/podcasts/POD001", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'podcast_id' in data
        assert data['title'] == 'Tech Talk Daily'
        assert data['total_downloads'] == 50000
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('google.cloud.bigquery.Client')
    def test_dashboard_metrics_endpoint(self, mock_bigquery, mock_validate, 
                                        client, auth_headers):
        """Test dashboard metrics endpoint"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        # Mock BigQuery response
        mock_client = Mock()
        mock_bigquery.return_value = mock_client
        mock_client.query.return_value.result.return_value = [
            {
                'metric_name': 'total_podcasts',
                'metric_value': 25,
                'metric_change': 0.15
            },
            {
                'metric_name': 'total_downloads',
                'metric_value': 125000,
                'metric_change': 0.08
            }
        ]
        
        response = client.get("/api/v1/dashboard/metrics", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'metrics' in data
        assert len(data['metrics']) == 2


class TestSecurityIntegration:
    """Test security features integration"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set"""
        response = client.options("/api/v1/health")
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
    
    def test_security_headers(self, client):
        """Test security headers are present"""
        response = client.get("/api/v1/health")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    def test_rate_limiting(self, mock_validate, client):
        """Test rate limiting functionality"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # Make many requests to trigger rate limiting
        responses = []
        for i in range(100):
            response = client.get("/api/v1/podcasts", headers=headers)
            responses.append(response.status_code)
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert 429 in responses
    
    @patch('security.audit_logger.AuditLogger.log_event')
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    def test_audit_logging(self, mock_validate, mock_audit_log, client):
        """Test audit logging for sensitive operations"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['admin']
        }
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # Perform sensitive operation
        response = client.get("/api/v1/admin/users", headers=headers)
        
        # Verify audit log was called
        mock_audit_log.assert_called()
        args, kwargs = mock_audit_log.call_args
        assert 'admin_access' in str(args) or 'admin_access' in str(kwargs)


class TestPerformanceIntegration:
    """Test API performance under load"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    def test_concurrent_requests(self, mock_validate, client):
        """Test handling of concurrent requests"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # Simulate concurrent requests (simplified test)
        import concurrent.futures
        import time
        
        def make_request():
            start_time = time.time()
            response = client.get("/api/v1/health", headers=headers)
            end_time = time.time()
            return response.status_code, end_time - start_time
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        status_codes = [result[0] for result in results]
        assert all(code == 200 for code in status_codes)
        
        # Average response time should be reasonable
        response_times = [result[1] for result in results]
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 1.0  # Less than 1 second average
    
    @patch('auth.google_auth.GoogleAuthenticator.validate_token')
    @patch('google.cloud.bigquery.Client')
    def test_database_connection_pooling(self, mock_bigquery, mock_validate, client):
        """Test database connection pooling under load"""
        mock_validate.return_value = {
            'user_id': 'test_user',
            'tenant_id': 'test_tenant',
            'email': 'test@example.com',
            'roles': ['user']
        }
        
        # Mock BigQuery client to track connection usage
        mock_client = Mock()
        mock_bigquery.return_value = mock_client
        mock_client.query.return_value.result.return_value = []
        
        headers = {"Authorization": "Bearer valid_token"}
        
        # Make multiple database-dependent requests
        for i in range(20):
            response = client.get("/api/v1/podcasts", headers=headers)
            assert response.status_code == 200
        
        # Verify BigQuery client was reused (connection pooling)
        assert mock_bigquery.call_count < 20  # Should reuse connections


if __name__ == "__main__":
    pytest.main([__file__]) 