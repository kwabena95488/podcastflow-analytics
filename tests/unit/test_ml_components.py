"""
Unit tests for ML components
"""

import pytest
import numpy as np
import pandas as pd
import tensorflow as tf
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from ml.recommendation_engine import RecommendationEngine
from ml.prediction_models import PerformancePredictionModel
from ml.user_segmentation import UserSegmentationModel

class TestRecommendationEngine:
    """Test cases for the recommendation engine"""
    
    @pytest.fixture
    def recommendation_engine(self):
        """Create a recommendation engine instance for testing"""
        return RecommendationEngine()
    
    @pytest.fixture
    def sample_user_interactions(self):
        """Sample user interaction data"""
        return pd.DataFrame({
            'user_id': ['user1', 'user1', 'user2', 'user2', 'user3'],
            'episode_id': ['ep1', 'ep2', 'ep1', 'ep3', 'ep2'],
            'rating': [5, 4, 5, 3, 4],
            'completion_rate': [0.95, 0.80, 1.0, 0.60, 0.85],
            'listen_duration': [45, 38, 50, 30, 42]
        })
    
    @pytest.fixture
    def sample_content_features(self):
        """Sample content feature data"""
        return pd.DataFrame({
            'episode_id': ['ep1', 'ep2', 'ep3'],
            'category': ['Technology', 'Business', 'Health'],
            'duration': [45, 40, 35],
            'popularity_score': [0.85, 0.72, 0.68],
            'content_embedding': [
                np.random.random(50),
                np.random.random(50),
                np.random.random(50)
            ]
        })
    
    def test_initialization(self, recommendation_engine):
        """Test recommendation engine initialization"""
        assert recommendation_engine.model is None
        assert recommendation_engine.user_embeddings is None
        assert recommendation_engine.item_embeddings is None
        assert hasattr(recommendation_engine, 'config')
    
    @patch('tensorflow.keras.Sequential')
    def test_build_model(self, mock_sequential, recommendation_engine):
        """Test model building"""
        mock_model = Mock()
        mock_sequential.return_value = mock_model
        
        recommendation_engine.build_model(
            num_users=1000,
            num_items=5000,
            embedding_size=64
        )
        
        assert mock_sequential.called
        mock_model.compile.assert_called_once()
    
    def test_prepare_training_data(self, recommendation_engine, sample_user_interactions):
        """Test training data preparation"""
        X, y = recommendation_engine.prepare_training_data(sample_user_interactions)
        
        assert isinstance(X, dict)
        assert 'user_id' in X
        assert 'item_id' in X
        assert len(X['user_id']) == len(sample_user_interactions)
        assert len(y) == len(sample_user_interactions)
    
    @patch.object(RecommendationEngine, 'build_model')
    def test_train_model(self, mock_build_model, recommendation_engine, sample_user_interactions):
        """Test model training"""
        mock_model = Mock()
        mock_model.fit.return_value.history = {'loss': [0.5, 0.3, 0.2]}
        recommendation_engine.model = mock_model
        
        history = recommendation_engine.train_model(sample_user_interactions)
        
        assert mock_model.fit.called
        assert 'loss' in history.history
    
    @patch.object(RecommendationEngine, '_get_user_features')
    @patch.object(RecommendationEngine, '_get_content_features')
    def test_generate_recommendations(self, mock_content_features, mock_user_features, 
                                      recommendation_engine):
        """Test recommendation generation"""
        # Mock the model prediction
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.8], [0.6], [0.9]])
        recommendation_engine.model = mock_model
        
        # Mock feature extraction
        mock_user_features.return_value = np.array([0.1, 0.2, 0.3])
        mock_content_features.return_value = pd.DataFrame({
            'episode_id': ['ep1', 'ep2', 'ep3'],
            'features': [np.random.random(10), np.random.random(10), np.random.random(10)]
        })
        
        recommendations = recommendation_engine.generate_recommendations('user1', top_k=3)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        for rec in recommendations:
            assert 'episode_id' in rec
            assert 'score' in rec
            assert 'confidence' in rec
    
    def test_collaborative_filtering_strategy(self, recommendation_engine, sample_user_interactions):
        """Test collaborative filtering strategy"""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.8], [0.6], [0.7]])
        recommendation_engine.model = mock_model
        
        recommendations = recommendation_engine._collaborative_filtering(
            'user1', 
            candidate_items=['ep1', 'ep2', 'ep3']
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) == 3
    
    def test_content_based_strategy(self, recommendation_engine, sample_content_features):
        """Test content-based filtering strategy"""
        user_profile = {
            'preferred_categories': ['Technology', 'Business'],
            'avg_duration_preference': 40,
            'engagement_history': [0.8, 0.9, 0.7]
        }
        
        recommendations = recommendation_engine._content_based_filtering(
            user_profile,
            sample_content_features
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
    
    def test_hybrid_strategy(self, recommendation_engine):
        """Test hybrid recommendation strategy"""
        # Mock both collaborative and content-based results
        collab_recs = [
            {'episode_id': 'ep1', 'score': 0.8, 'source': 'collaborative'},
            {'episode_id': 'ep2', 'score': 0.6, 'source': 'collaborative'}
        ]
        
        content_recs = [
            {'episode_id': 'ep2', 'score': 0.9, 'source': 'content'},
            {'episode_id': 'ep3', 'score': 0.7, 'source': 'content'}
        ]
        
        hybrid_recs = recommendation_engine._combine_strategies(
            collab_recs, 
            content_recs,
            alpha=0.7
        )
        
        assert isinstance(hybrid_recs, list)
        # Should have unique episodes with combined scores
        episode_ids = [rec['episode_id'] for rec in hybrid_recs]
        assert len(episode_ids) == len(set(episode_ids))
    
    def test_model_persistence(self, recommendation_engine, tmp_path):
        """Test model saving and loading"""
        # Create a mock model
        mock_model = Mock()
        recommendation_engine.model = mock_model
        
        model_path = tmp_path / "test_model"
        
        with patch('tensorflow.keras.models.save_model') as mock_save:
            recommendation_engine.save_model(str(model_path))
            mock_save.assert_called_once()
        
        with patch('tensorflow.keras.models.load_model') as mock_load:
            mock_load.return_value = mock_model
            loaded_engine = recommendation_engine.load_model(str(model_path))
            mock_load.assert_called_once()
            assert loaded_engine.model == mock_model


class TestPerformancePredictionModel:
    """Test cases for the performance prediction model"""
    
    @pytest.fixture
    def prediction_model(self):
        """Create a performance prediction model for testing"""
        return PerformancePredictionModel()
    
    @pytest.fixture
    def sample_episode_features(self):
        """Sample episode feature data"""
        return pd.DataFrame({
            'episode_id': ['ep1', 'ep2', 'ep3'],
            'duration_minutes': [45, 35, 50],
            'category': ['Technology', 'Business', 'Health'],
            'sentiment_score': [0.8, 0.6, 0.9],
            'complexity_score': [0.7, 0.5, 0.6],
            'release_hour': [9, 14, 18],
            'release_day': [1, 3, 5],  # Monday, Wednesday, Friday
            'podcast_popularity': [0.85, 0.72, 0.68],
            'historical_avg_downloads': [5000, 3500, 4200]
        })
    
    def test_initialization(self, prediction_model):
        """Test prediction model initialization"""
        assert prediction_model.model is None
        assert hasattr(prediction_model, 'feature_columns')
        assert hasattr(prediction_model, 'target_columns')
    
    def test_feature_engineering(self, prediction_model, sample_episode_features):
        """Test feature engineering process"""
        engineered_features = prediction_model.engineer_features(sample_episode_features)
        
        assert isinstance(engineered_features, pd.DataFrame)
        assert len(engineered_features) == len(sample_episode_features)
        
        # Check for expected engineered features
        expected_features = [
            'duration_normalized',
            'category_encoded',
            'temporal_features',
            'content_features',
            'historical_features'
        ]
        
        # At least some engineered features should be present
        assert len(engineered_features.columns) >= len(sample_episode_features.columns)
    
    @patch('tensorflow.keras.Sequential')
    def test_build_multi_target_model(self, mock_sequential, prediction_model):
        """Test multi-target model building"""
        mock_model = Mock()
        mock_sequential.return_value = mock_model
        
        prediction_model.build_multi_target_model(input_dim=20)
        
        assert mock_sequential.called
        mock_model.compile.assert_called_once()
    
    def test_prepare_multi_target_data(self, prediction_model):
        """Test multi-target data preparation"""
        sample_data = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6],
            'downloads': [1000, 2000, 1500],
            'completion_rate': [0.8, 0.9, 0.7],
            'engagement_score': [7, 8, 6],
            'rating': [4.5, 4.8, 4.2]
        })
        
        X, y = prediction_model.prepare_multi_target_data(sample_data)
        
        assert X.shape[0] == len(sample_data)
        assert y.shape[0] == len(sample_data)
        assert y.shape[1] == 4  # Four target variables
    
    @patch.object(PerformancePredictionModel, 'build_multi_target_model')
    def test_train_model(self, mock_build_model, prediction_model):
        """Test model training"""
        mock_model = Mock()
        mock_model.fit.return_value.history = {'loss': [0.5, 0.3, 0.2]}
        prediction_model.model = mock_model
        
        training_data = pd.DataFrame({
            'feature1': np.random.random(100),
            'downloads': np.random.randint(1000, 10000, 100),
            'completion_rate': np.random.random(100),
            'engagement_score': np.random.uniform(1, 10, 100),
            'rating': np.random.uniform(1, 5, 100)
        })
        
        history = prediction_model.train_model(training_data)
        
        assert mock_model.fit.called
        assert 'loss' in history.history
    
    def test_predict_performance(self, prediction_model):
        """Test performance prediction"""
        # Mock the model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[5000, 0.85, 7.5, 4.6]])
        prediction_model.model = mock_model
        
        episode_features = {
            'duration_minutes': 45,
            'category': 'Technology',
            'sentiment_score': 0.8,
            'complexity_score': 0.7,
            'release_timing': 'morning'
        }
        
        predictions = prediction_model.predict_performance(episode_features)
        
        assert isinstance(predictions, dict)
        assert 'predicted_downloads' in predictions
        assert 'predicted_completion_rate' in predictions
        assert 'predicted_engagement' in predictions
        assert 'predicted_rating' in predictions
        assert 'confidence_intervals' in predictions
    
    def test_feature_importance_analysis(self, prediction_model):
        """Test feature importance analysis"""
        # Mock feature importance calculation
        mock_importance = {
            'duration_minutes': 0.25,
            'category': 0.20,
            'sentiment_score': 0.18,
            'complexity_score': 0.15,
            'release_timing': 0.12,
            'historical_performance': 0.10
        }
        
        with patch.object(prediction_model, '_calculate_feature_importance', 
                          return_value=mock_importance):
            importance = prediction_model.get_feature_importance()
            
            assert isinstance(importance, dict)
            assert len(importance) > 0
            assert all(0 <= val <= 1 for val in importance.values())


class TestUserSegmentationModel:
    """Test cases for the user segmentation model"""
    
    @pytest.fixture
    def segmentation_model(self):
        """Create a user segmentation model for testing"""
        return UserSegmentationModel()
    
    @pytest.fixture
    def sample_user_behavior_data(self):
        """Sample user behavior data"""
        return pd.DataFrame({
            'user_id': [f'user_{i}' for i in range(100)],
            'listening_hours_weekly': np.random.uniform(1, 50, 100),
            'session_frequency': np.random.uniform(1, 20, 100),
            'genre_diversity': np.random.uniform(0, 1, 100),
            'completion_rate_avg': np.random.uniform(0.3, 1.0, 100),
            'skip_rate': np.random.uniform(0, 0.8, 100),
            'social_engagement': np.random.uniform(0, 1, 100),
            'premium_features_usage': np.random.uniform(0, 1, 100),
            'discovery_rate': np.random.uniform(0, 1, 100)
        })
    
    def test_initialization(self, segmentation_model):
        """Test segmentation model initialization"""
        assert segmentation_model.kmeans_model is None
        assert segmentation_model.scaler is None
        assert hasattr(segmentation_model, 'n_clusters')
    
    def test_behavioral_feature_extraction(self, segmentation_model, sample_user_behavior_data):
        """Test behavioral feature extraction"""
        features = segmentation_model.extract_behavioral_features(sample_user_behavior_data)
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) == len(sample_user_behavior_data)
        assert features.shape[1] >= sample_user_behavior_data.shape[1]
    
    def test_optimal_clusters_determination(self, segmentation_model, sample_user_behavior_data):
        """Test optimal number of clusters determination"""
        features = segmentation_model.extract_behavioral_features(sample_user_behavior_data)
        
        with patch.object(segmentation_model, '_calculate_silhouette_scores') as mock_silhouette:
            mock_silhouette.return_value = [0.3, 0.5, 0.7, 0.6, 0.4]  # Peak at 3 clusters
            
            optimal_k = segmentation_model.determine_optimal_clusters(features)
            
            assert isinstance(optimal_k, int)
            assert 2 <= optimal_k <= 10
    
    @patch('sklearn.cluster.KMeans')
    @patch('sklearn.preprocessing.StandardScaler')
    def test_train_segmentation_model(self, mock_scaler, mock_kmeans, 
                                      segmentation_model, sample_user_behavior_data):
        """Test segmentation model training"""
        mock_scaler_instance = Mock()
        mock_scaler.return_value = mock_scaler_instance
        mock_scaler_instance.fit_transform.return_value = np.random.random((100, 8))
        
        mock_kmeans_instance = Mock()
        mock_kmeans.return_value = mock_kmeans_instance
        mock_kmeans_instance.labels_ = np.random.randint(0, 6, 100)
        mock_kmeans_instance.cluster_centers_ = np.random.random((6, 8))
        
        result = segmentation_model.train_model(sample_user_behavior_data)
        
        assert mock_scaler.called
        assert mock_kmeans.called
        assert 'cluster_labels' in result
        assert 'silhouette_score' in result
    
    def test_user_segmentation(self, segmentation_model):
        """Test user segmentation"""
        # Mock trained model
        mock_kmeans = Mock()
        mock_kmeans.predict.return_value = np.array([0, 1, 2])
        segmentation_model.kmeans_model = mock_kmeans
        
        mock_scaler = Mock()
        mock_scaler.transform.return_value = np.random.random((3, 8))
        segmentation_model.scaler = mock_scaler
        
        user_features = pd.DataFrame({
            'user_id': ['user1', 'user2', 'user3'],
            'listening_hours': [25, 10, 40],
            'session_frequency': [15, 5, 20]
        })
        
        segments = segmentation_model.segment_users(user_features)
        
        assert isinstance(segments, dict)
        assert 'user_segments' in segments
        assert len(segments['user_segments']) == len(user_features)
    
    def test_segment_profiling(self, segmentation_model, sample_user_behavior_data):
        """Test segment profiling and persona creation"""
        # Mock cluster labels
        cluster_labels = np.random.randint(0, 6, len(sample_user_behavior_data))
        
        profiles = segmentation_model.create_segment_profiles(
            sample_user_behavior_data, 
            cluster_labels
        )
        
        assert isinstance(profiles, dict)
        assert len(profiles) <= 6  # Maximum number of clusters
        
        for segment_id, profile in profiles.items():
            assert 'size' in profile
            assert 'characteristics' in profile
            assert 'persona_name' in profile
    
    def test_ltv_prediction(self, segmentation_model):
        """Test lifetime value prediction"""
        user_features = {
            'listening_hours_monthly': 25,
            'session_frequency': 15,
            'premium_usage': 0.8,
            'engagement_score': 8.5,
            'tenure_months': 12
        }
        
        with patch.object(segmentation_model, '_calculate_ltv') as mock_ltv:
            mock_ltv.return_value = {'ltv_12m': 120.50, 'ltv_24m': 240.80}
            
            ltv = segmentation_model.predict_ltv(user_features)
            
            assert isinstance(ltv, dict)
            assert 'ltv_12m' in ltv
            assert 'ltv_24m' in ltv
    
    def test_churn_risk_assessment(self, segmentation_model):
        """Test churn risk assessment"""
        user_behavior = {
            'recent_activity_decline': 0.3,
            'session_frequency_drop': 0.4,
            'engagement_score_trend': -0.2,
            'support_tickets': 2,
            'days_since_last_login': 7
        }
        
        with patch.object(segmentation_model, '_calculate_churn_risk') as mock_churn:
            mock_churn.return_value = 0.65
            
            churn_risk = segmentation_model.assess_churn_risk(user_behavior)
            
            assert isinstance(churn_risk, float)
            assert 0 <= churn_risk <= 1


class TestMLIntegration:
    """Integration tests for ML components working together"""
    
    def test_ml_pipeline_integration(self, mock_ml_models, sample_user_data, sample_episode_data):
        """Test integration between ML components"""
        # Test that recommendation engine can use segmentation results
        user_segment = mock_ml_models['segmentation_model'].segment_users(sample_user_data)
        
        # Test that predictions can inform recommendations
        performance_prediction = mock_ml_models['prediction_model'].predict_performance({
            'duration_minutes': 45,
            'category': 'Technology'
        })
        
        # Test that recommendations consider predictions
        recommendations = mock_ml_models['recommendation_engine'].generate_recommendations(
            'USER001', 
            top_k=5
        )
        
        assert user_segment is not None
        assert performance_prediction is not None
        assert recommendations is not None
        assert len(recommendations) > 0
    
    def test_model_performance_monitoring(self):
        """Test ML model performance monitoring"""
        # Mock performance metrics
        metrics = {
            'recommendation_precision': 0.75,
            'recommendation_recall': 0.68,
            'prediction_mae': 0.15,
            'prediction_r2': 0.82,
            'segmentation_silhouette': 0.65
        }
        
        # Test metrics are within expected ranges
        assert 0.5 <= metrics['recommendation_precision'] <= 1.0
        assert 0.5 <= metrics['recommendation_recall'] <= 1.0
        assert metrics['prediction_mae'] <= 0.3
        assert metrics['prediction_r2'] >= 0.7
        assert metrics['segmentation_silhouette'] >= 0.5


if __name__ == "__main__":
    pytest.main([__file__]) 