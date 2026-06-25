"""
Pytest configuration and shared fixtures for PodcastFlow Analytics Platform
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from google.cloud import bigquery
import pandas as pd
import numpy as np

# Add project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def test_config():
    """Test configuration settings"""
    return {
        'project_id': 'test-project',
        'dataset_bronze': 'test_bronze',
        'dataset_silver': 'test_silver',
        'dataset_gold': 'test_gold',
        'region': 'us-central1',
        'environment': 'test'
    }

@pytest.fixture(scope="session")
def mock_bigquery_client():
    """Mock BigQuery client for testing"""
    with patch('google.cloud.bigquery.Client') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_podcast_data():
    """Sample podcast data for testing"""
    return pd.DataFrame({
        'podcast_id': ['POD001', 'POD002', 'POD003'],
        'title': ['Tech Talk Daily', 'Business Insights', 'Health & Wellness'],
        'description': ['Daily tech news', 'Business strategies', 'Health tips'],
        'category': ['Technology', 'Business', 'Health'],
        'total_episodes': [150, 89, 234],
        'average_rating': [4.5, 4.2, 4.7],
        'subscriber_count': [50000, 25000, 75000],
        'created_at': pd.to_datetime(['2022-01-15', '2022-03-10', '2021-12-05'])
    })

@pytest.fixture
def sample_episode_data():
    """Sample episode data for testing"""
    return pd.DataFrame({
        'episode_id': ['EP001', 'EP002', 'EP003'],
        'podcast_id': ['POD001', 'POD001', 'POD002'],
        'title': ['AI Revolution', 'Cloud Computing Trends', 'Marketing Strategies'],
        'duration_minutes': [45, 52, 38],
        'download_count': [5000, 4200, 3100],
        'completion_rate': [0.85, 0.78, 0.92],
        'rating': [4.6, 4.3, 4.5],
        'published_at': pd.to_datetime(['2024-12-01', '2024-12-15', '2024-12-20'])
    })

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return pd.DataFrame({
        'user_id': ['USER001', 'USER002', 'USER003'],
        'subscription_tier': ['premium', 'free', 'enterprise'],
        'listening_hours_monthly': [25.5, 12.3, 45.2],
        'favorite_categories': [['Technology'], ['Business', 'Health'], ['Technology', 'Business']],
        'engagement_score': [8.5, 6.2, 9.1],
        'churn_risk': [0.15, 0.45, 0.08],
        'created_at': pd.to_datetime(['2023-06-15', '2024-01-10', '2022-11-22'])
    })

@pytest.fixture
def sample_listening_events():
    """Sample listening event data for testing"""
    return pd.DataFrame({
        'event_id': ['EVT001', 'EVT002', 'EVT003'],
        'user_id': ['USER001', 'USER002', 'USER001'],
        'episode_id': ['EP001', 'EP002', 'EP001'],
        'session_duration_minutes': [42, 35, 45],
        'completion_percentage': [0.93, 0.67, 1.0],
        'skip_count': [2, 1, 0],
        'replay_count': [0, 1, 0],
        'timestamp': pd.to_datetime(['2024-12-30 10:00:00', '2024-12-30 11:30:00', '2024-12-30 14:15:00'])
    })

@pytest.fixture
def mock_ml_models():
    """Mock ML models for testing"""
    mock_recommendation_engine = Mock()
    mock_recommendation_engine.generate_recommendations.return_value = [
        {'episode_id': 'EP001', 'score': 0.95, 'reason': 'High user affinity'},
        {'episode_id': 'EP002', 'score': 0.87, 'reason': 'Similar content preferences'},
        {'episode_id': 'EP003', 'score': 0.82, 'reason': 'Popular in category'}
    ]
    
    mock_prediction_model = Mock()
    mock_prediction_model.predict_performance.return_value = {
        'predicted_downloads': 4500,
        'predicted_completion_rate': 0.83,
        'predicted_rating': 4.4,
        'confidence_interval': [0.78, 0.88]
    }
    
    mock_segmentation_model = Mock()
    mock_segmentation_model.segment_users.return_value = {
        'segments': ['Power Listeners', 'Casual Browsers', 'Focused Enthusiasts'],
        'user_segments': ['Power Listeners', 'Casual Browsers', 'Power Listeners']
    }
    
    return {
        'recommendation_engine': mock_recommendation_engine,
        'prediction_model': mock_prediction_model,
        'segmentation_model': mock_segmentation_model
    }

@pytest.fixture
def mock_authentication():
    """Mock authentication for testing"""
    with patch('auth.google_auth.GoogleAuthenticator') as mock_auth:
        mock_instance = Mock()
        mock_instance.validate_token.return_value = {
            'user_id': 'test_user',
            'email': 'test@example.com',
            'tenant_id': 'test_tenant',
            'roles': ['user'],
            'permissions': ['read', 'write']
        }
        mock_auth.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_tenant_context():
    """Mock tenant context for multi-tenancy testing"""
    return {
        'tenant_id': 'test_tenant',
        'tenant_name': 'Test Organization',
        'subscription_tier': 'premium',
        'max_users': 100,
        'max_storage_gb': 1000,
        'features_enabled': ['analytics', 'ml', 'api_access'],
        'created_at': '2024-01-01T00:00:00Z'
    }

@pytest.fixture
def mock_security_context():
    """Mock security context for testing"""
    return {
        'user_id': 'test_user',
        'tenant_id': 'test_tenant',
        'session_id': 'test_session_123',
        'permissions': ['read:podcasts', 'write:analytics', 'admin:tenant'],
        'ip_address': '127.0.0.1',
        'user_agent': 'Mozilla/5.0 Test Browser',
        'login_timestamp': '2024-12-30T20:00:00Z'
    }

@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing"""
    np.random.seed(42)
    n_records = 10000
    
    return pd.DataFrame({
        'podcast_id': [f'POD{i:05d}' for i in range(n_records)],
        'episode_count': np.random.randint(10, 500, n_records),
        'total_downloads': np.random.randint(1000, 100000, n_records),
        'average_rating': np.random.uniform(3.0, 5.0, n_records),
        'engagement_score': np.random.uniform(0.1, 10.0, n_records),
        'category_id': np.random.randint(1, 20, n_records)
    })

@pytest.fixture(scope="function")
def temp_test_files(tmp_path):
    """Create temporary test files"""
    test_files = {
        'config': tmp_path / "test_config.yaml",
        'data': tmp_path / "test_data.json",
        'logs': tmp_path / "test_logs.txt"
    }
    
    # Create test files with sample content
    test_files['config'].write_text("""
    project_id: test-project
    environment: test
    debug: true
    """)
    
    test_files['data'].write_text('{"test": "data"}')
    test_files['logs'].write_text('Test log entry\n')
    
    return test_files

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables"""
    test_env_vars = {
        'ENVIRONMENT': 'test',
        'PROJECT_ID': 'test-project',
        'BIGQUERY_PROJECT': 'test-project',
        'DATASET_BRONZE': 'test_bronze',
        'DATASET_SILVER': 'test_silver',
        'DATASET_GOLD': 'test_gold',
        'ML_MODEL_BUCKET': 'test-ml-models',
        'JWT_SECRET_KEY': 'test-secret-key',
        'ENCRYPTION_KEY': 'test-encryption-key'
    }
    
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

@pytest.fixture
def api_client():
    """Test client for API testing"""
    from fastapi.testclient import TestClient
    from api.secure_main import app
    
    return TestClient(app)

@pytest.fixture
def mock_streamlit():
    """Mock Streamlit components for dashboard testing"""
    with patch('streamlit.sidebar') as mock_sidebar, \
         patch('streamlit.columns') as mock_columns, \
         patch('streamlit.metric') as mock_metric, \
         patch('streamlit.plotly_chart') as mock_chart:
        
        yield {
            'sidebar': mock_sidebar,
            'columns': mock_columns,
            'metric': mock_metric,
            'plotly_chart': mock_chart
        }

# Performance testing markers
pytest.mark.performance = pytest.mark.slow
pytest.mark.integration = pytest.mark.slow
pytest.mark.e2e = pytest.mark.slow

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "ml: Machine learning tests")
    config.addinivalue_line("markers", "slow: Slow running tests")

def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on file location"""
    for item in items:
        # Mark tests based on directory structure
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        # Mark ML-related tests
        if "ml" in str(item.fspath) or "recommendation" in item.name or "prediction" in item.name:
            item.add_marker(pytest.mark.ml)
        
        # Mark security tests
        if "security" in str(item.fspath) or "auth" in item.name or "tenant" in item.name:
            item.add_marker(pytest.mark.security) 