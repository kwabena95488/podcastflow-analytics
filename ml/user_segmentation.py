"""
PodcastFlow Analytics - User Behavior Clustering & Segmentation
Phase 3 Week 3: Advanced Analytics & ML Integration

Features:
- Advanced user behavior clustering using K-means and DBSCAN
- User persona identification and segmentation
- Behavioral pattern analysis and insights
- Dynamic user segment updates
- Segment-specific recommendation strategies
- Cohort analysis and user lifetime value prediction
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from google.cloud import bigquery
import joblib

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class UserSegment:
    """User segment data structure"""
    segment_id: int
    segment_name: str
    description: str
    user_count: int
    characteristics: Dict[str, float]
    recommendations: List[str]
    ltv_estimate: float

@dataclass
class UserProfile:
    """Individual user profile"""
    user_id: str
    segment_id: int
    segment_name: str
    behavior_features: Dict[str, float]
    preferences: Dict[str, Any]
    predicted_ltv: float
    risk_score: float  # Churn risk
    last_updated: datetime

class BehavioralFeatureExtractor:
    """Extract behavioral features for user segmentation"""
    
    def __init__(self):
        self.feature_groups = {
            'engagement': ['listening_frequency', 'session_duration', 'completion_rate', 'skip_rate'],
            'content': ['genre_diversity', 'episode_length_preference', 'recency_preference'],
            'platform': ['platform_usage', 'device_diversity', 'time_of_day_patterns'],
            'social': ['sharing_frequency', 'review_activity', 'subscription_behavior']
        }
    
    def extract_user_features(self, user_id: str, bigquery_client: bigquery.Client, 
                            project_id: str, lookback_days: int = 90) -> Dict[str, float]:
        """Extract comprehensive behavioral features for a user"""
        
        # Time window for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        features = {}
        
        # Engagement features
        engagement_features = self._extract_engagement_features(
            user_id, bigquery_client, project_id, start_date, end_date
        )
        features.update(engagement_features)
        
        # Content preference features
        content_features = self._extract_content_features(
            user_id, bigquery_client, project_id, start_date, end_date
        )
        features.update(content_features)
        
        # Platform usage features
        platform_features = self._extract_platform_features(
            user_id, bigquery_client, project_id, start_date, end_date
        )
        features.update(platform_features)
        
        # Social behavior features
        social_features = self._extract_social_features(
            user_id, bigquery_client, project_id, start_date, end_date
        )
        features.update(social_features)
        
        return features
    
    def _extract_engagement_features(self, user_id: str, bigquery_client: bigquery.Client,
                                   project_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Extract engagement-related features"""
        
        query = f"""
        SELECT 
            COUNT(DISTINCT DATE(created_at)) as active_days,
            COUNT(*) as total_sessions,
            AVG(listening_duration_minutes) as avg_session_duration,
            AVG(completion_percentage) as avg_completion_rate,
            SUM(CASE WHEN completion_percentage < 0.1 THEN 1 ELSE 0 END) / COUNT(*) as skip_rate,
            COUNT(DISTINCT podcast_id) as unique_podcasts,
            COUNT(DISTINCT episode_id) as unique_episodes
        FROM `{project_id}.bronze.listening_events_realtime`
        WHERE user_id = '{user_id}'
          AND created_at >= '{start_date.strftime('%Y-%m-%d')}'
          AND created_at < '{end_date.strftime('%Y-%m-%d')}'
        """
        
        try:
            result = bigquery_client.query(query).to_dataframe()
            if not result.empty:
                row = result.iloc[0]
                lookback_days = (end_date - start_date).days
                
                return {
                    'listening_frequency': row['active_days'] / lookback_days if lookback_days > 0 else 0,
                    'sessions_per_day': row['total_sessions'] / lookback_days if lookback_days > 0 else 0,
                    'avg_session_duration': row['avg_session_duration'] or 0,
                    'avg_completion_rate': row['avg_completion_rate'] or 0,
                    'skip_rate': row['skip_rate'] or 0,
                    'content_diversity': (row['unique_podcasts'] or 0) / max(1, row['total_sessions'] or 1),
                    'episode_exploration': (row['unique_episodes'] or 0) / max(1, row['total_sessions'] or 1)
                }
        except Exception as e:
            logger.warning(f"Failed to extract engagement features for {user_id}: {str(e)}")
        
        # Return default values
        return {
            'listening_frequency': 0,
            'sessions_per_day': 0,
            'avg_session_duration': 0,
            'avg_completion_rate': 0,
            'skip_rate': 0,
            'content_diversity': 0,
            'episode_exploration': 0
        }
    
    def _extract_content_features(self, user_id: str, bigquery_client: bigquery.Client,
                                project_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Extract content preference features"""
        
        # Get genre preferences
        genre_query = f"""
        SELECT 
            pm.categories as genre,
            COUNT(*) as listen_count,
            AVG(le.completion_percentage) as avg_completion
        FROM `{project_id}.bronze.listening_events_realtime` le
        JOIN `{project_id}.silver.podcast_metadata` pm ON le.podcast_id = pm.podcast_id
        WHERE le.user_id = '{user_id}'
          AND le.created_at >= '{start_date.strftime('%Y-%m-%d')}'
          AND le.created_at < '{end_date.strftime('%Y-%m-%d')}'
          AND pm.categories IS NOT NULL
        GROUP BY pm.categories
        ORDER BY listen_count DESC
        """
        
        # Get episode length preferences
        duration_query = f"""
        SELECT 
            AVG(listening_duration_minutes) as avg_listened_duration,
            STDDEV(listening_duration_minutes) as duration_variance,
            AVG(CASE WHEN listening_duration_minutes < 15 THEN 1 ELSE 0 END) as short_episode_preference,
            AVG(CASE WHEN listening_duration_minutes > 60 THEN 1 ELSE 0 END) as long_episode_preference
        FROM `{project_id}.bronze.listening_events_realtime`
        WHERE user_id = '{user_id}'
          AND created_at >= '{start_date.strftime('%Y-%m-%d')}'
          AND created_at < '{end_date.strftime('%Y-%m-%d')}'
        """
        
        try:
            # Get genre diversity
            genre_result = bigquery_client.query(genre_query).to_dataframe()
            genre_diversity = len(genre_result) if not genre_result.empty else 0
            
            # Get duration preferences
            duration_result = bigquery_client.query(duration_query).to_dataframe()
            if not duration_result.empty:
                duration_row = duration_result.iloc[0]
                return {
                    'genre_diversity': min(genre_diversity / 10.0, 1.0),  # Normalize to 0-1
                    'avg_episode_duration': duration_row['avg_listened_duration'] or 0,
                    'duration_consistency': 1.0 / (1.0 + (duration_row['duration_variance'] or 1)),
                    'short_episode_preference': duration_row['short_episode_preference'] or 0,
                    'long_episode_preference': duration_row['long_episode_preference'] or 0
                }
        except Exception as e:
            logger.warning(f"Failed to extract content features for {user_id}: {str(e)}")
        
        return {
            'genre_diversity': 0,
            'avg_episode_duration': 0,
            'duration_consistency': 0,
            'short_episode_preference': 0,
            'long_episode_preference': 0
        }
    
    def _extract_platform_features(self, user_id: str, bigquery_client: bigquery.Client,
                                 project_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Extract platform usage features"""
        
        query = f"""
        SELECT 
            platform,
            COUNT(*) as session_count,
            AVG(listening_duration_minutes) as avg_duration,
            EXTRACT(HOUR FROM created_at) as hour
        FROM `{project_id}.bronze.listening_events_realtime`
        WHERE user_id = '{user_id}'
          AND created_at >= '{start_date.strftime('%Y-%m-%d')}'
          AND created_at < '{end_date.strftime('%Y-%m-%d')}'
        GROUP BY platform, EXTRACT(HOUR FROM created_at)
        """
        
        try:
            result = bigquery_client.query(query).to_dataframe()
            if not result.empty:
                # Platform diversity
                unique_platforms = result['platform'].nunique()
                
                # Time of day patterns
                hour_distribution = result.groupby('hour')['session_count'].sum()
                peak_hours = hour_distribution.nlargest(3).index.tolist()
                
                # Primary platform usage
                platform_usage = result.groupby('platform')['session_count'].sum()
                primary_platform_ratio = platform_usage.max() / platform_usage.sum() if platform_usage.sum() > 0 else 0
                
                return {
                    'platform_diversity': min(unique_platforms / 3.0, 1.0),  # Normalize
                    'primary_platform_loyalty': primary_platform_ratio,
                    'morning_listening': float(any(h in range(6, 12) for h in peak_hours)),
                    'evening_listening': float(any(h in range(18, 24) for h in peak_hours)),
                    'weekend_listening': 0.5  # Placeholder - would need date analysis
                }
        except Exception as e:
            logger.warning(f"Failed to extract platform features for {user_id}: {str(e)}")
        
        return {
            'platform_diversity': 0,
            'primary_platform_loyalty': 0,
            'morning_listening': 0,
            'evening_listening': 0,
            'weekend_listening': 0
        }
    
    def _extract_social_features(self, user_id: str, bigquery_client: bigquery.Client,
                               project_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Extract social behavior features"""
        
        # For demo purposes, return placeholder values
        # In a real implementation, this would query social media interactions,
        # sharing behavior, reviews, etc.
        
        return {
            'sharing_frequency': np.random.random() * 0.1,  # Low sharing frequency
            'review_activity': np.random.random() * 0.05,   # Low review activity
            'social_engagement': np.random.random() * 0.2,  # Low social engagement
            'subscription_loyalty': np.random.random() * 0.8 + 0.2  # Higher loyalty
        }

class UserSegmentationModel:
    """Machine learning model for user segmentation"""
    
    def __init__(self):
        self.feature_extractor = BehavioralFeatureExtractor()
        self.scaler = StandardScaler()
        self.clustering_model = None
        self.pca_model = None
        self.feature_names = []
        self.segments = {}
        self.trained = False
    
    def prepare_user_features(self, users_df: pd.DataFrame, bigquery_client: bigquery.Client,
                            project_id: str) -> Tuple[np.ndarray, List[str]]:
        """Prepare feature matrix for all users"""
        
        all_features = []
        user_ids = []
        
        for _, user_row in users_df.iterrows():
            user_id = user_row['user_id']
            
            # Extract features for this user
            user_features = self.feature_extractor.extract_user_features(
                user_id, bigquery_client, project_id
            )
            
            all_features.append(user_features)
            user_ids.append(user_id)
        
        # Convert to DataFrame for consistent ordering
        features_df = pd.DataFrame(all_features)
        
        # Store feature names
        if not self.feature_names:
            self.feature_names = features_df.columns.tolist()
        
        # Handle missing values
        features_df = features_df.fillna(0)
        
        return features_df.values, user_ids
    
    def find_optimal_clusters(self, X: np.ndarray, max_clusters: int = 10) -> int:
        """Find optimal number of clusters using silhouette score and elbow method"""
        
        silhouette_scores = []
        inertias = []
        
        for k in range(2, max_clusters + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(X)
            
            silhouette_avg = silhouette_score(X, cluster_labels)
            silhouette_scores.append(silhouette_avg)
            inertias.append(kmeans.inertia_)
        
        # Find optimal k using silhouette score
        optimal_k = np.argmax(silhouette_scores) + 2
        
        logger.info(f"Optimal number of clusters: {optimal_k} (silhouette score: {max(silhouette_scores):.3f})")
        
        return optimal_k
    
    def train_segmentation_model(self, users_df: pd.DataFrame, bigquery_client: bigquery.Client,
                                project_id: str, n_clusters: int = None):
        """Train user segmentation model"""
        
        logger.info("Starting user segmentation model training...")
        
        # Prepare features
        X, user_ids = self.prepare_user_features(users_df, bigquery_client, project_id)
        
        if X.shape[0] < 10:
            logger.warning("Insufficient data for segmentation")
            return
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Apply PCA for dimensionality reduction and visualization
        self.pca_model = PCA(n_components=min(10, X_scaled.shape[1]))
        X_pca = self.pca_model.fit_transform(X_scaled)
        
        # Find optimal number of clusters if not specified
        if n_clusters is None:
            n_clusters = self.find_optimal_clusters(X_scaled)
        
        # Train clustering model
        self.clustering_model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = self.clustering_model.fit_predict(X_scaled)
        
        # Analyze segments
        self._analyze_segments(X, cluster_labels, user_ids)
        
        self.trained = True
        logger.info("User segmentation model training completed")
        
        return {
            'n_clusters': n_clusters,
            'silhouette_score': silhouette_score(X_scaled, cluster_labels),
            'feature_importance': self._calculate_feature_importance(X_scaled, cluster_labels)
        }
    
    def _analyze_segments(self, X: np.ndarray, cluster_labels: np.ndarray, user_ids: List[str]):
        """Analyze and characterize user segments"""
        
        features_df = pd.DataFrame(X, columns=self.feature_names)
        features_df['cluster'] = cluster_labels
        features_df['user_id'] = user_ids
        
        # Analyze each segment
        for cluster_id in np.unique(cluster_labels):
            cluster_data = features_df[features_df['cluster'] == cluster_id]
            
            # Calculate segment characteristics
            characteristics = {}
            for feature in self.feature_names:
                characteristics[feature] = float(cluster_data[feature].mean())
            
            # Generate segment description and recommendations
            segment_info = self._generate_segment_insights(cluster_id, characteristics)
            
            # Create segment object
            segment = UserSegment(
                segment_id=cluster_id,
                segment_name=segment_info['name'],
                description=segment_info['description'],
                user_count=len(cluster_data),
                characteristics=characteristics,
                recommendations=segment_info['recommendations'],
                ltv_estimate=segment_info['ltv_estimate']
            )
            
            self.segments[cluster_id] = segment
            
            logger.info(f"Segment {cluster_id} ({segment.segment_name}): {segment.user_count} users")
    
    def _generate_segment_insights(self, cluster_id: int, characteristics: Dict[str, float]) -> Dict[str, Any]:
        """Generate insights and recommendations for a segment"""
        
        # Analyze key characteristics
        engagement_score = (
            characteristics.get('listening_frequency', 0) +
            characteristics.get('avg_completion_rate', 0) +
            characteristics.get('sessions_per_day', 0) / 5  # Normalize sessions
        ) / 3
        
        diversity_score = (
            characteristics.get('genre_diversity', 0) +
            characteristics.get('content_diversity', 0) +
            characteristics.get('platform_diversity', 0)
        ) / 3
        
        # Determine segment type
        if engagement_score > 0.7:
            if diversity_score > 0.6:
                name = "Power Listeners"
                description = "Highly engaged users with diverse content preferences"
                ltv_estimate = 150.0
                recommendations = [
                    "Premium subscription offers",
                    "Early access to new content",
                    "Personalized playlists",
                    "Community features"
                ]
            else:
                name = "Focused Enthusiasts"
                description = "Highly engaged users with specific content preferences"
                ltv_estimate = 120.0
                recommendations = [
                    "Specialized content recommendations",
                    "Deep-dive series",
                    "Genre-specific features",
                    "Expert content access"
                ]
        elif engagement_score > 0.4:
            if diversity_score > 0.5:
                name = "Casual Explorers"
                description = "Moderately engaged users who explore different content"
                ltv_estimate = 80.0
                recommendations = [
                    "Content discovery features",
                    "Trending recommendations",
                    "Social sharing tools",
                    "Flexible subscription plans"
                ]
            else:
                name = "Regular Listeners"
                description = "Consistently engaged users with routine listening habits"
                ltv_estimate = 90.0
                recommendations = [
                    "Habit-building features",
                    "Consistent content schedules",
                    "Loyalty rewards",
                    "Routine-based recommendations"
                ]
        else:
            if characteristics.get('skip_rate', 0) > 0.7:
                name = "Selective Samplers"
                description = "Users who sample content but rarely complete episodes"
                ltv_estimate = 30.0
                recommendations = [
                    "Shorter content formats",
                    "Highlight reels",
                    "Quick discovery features",
                    "Engagement incentives"
                ]
            else:
                name = "Infrequent Users"
                description = "Low engagement users at risk of churning"
                ltv_estimate = 25.0
                recommendations = [
                    "Re-engagement campaigns",
                    "Personalized onboarding",
                    "Free premium trials",
                    "Push notification optimization"
                ]
        
        return {
            'name': name,
            'description': description,
            'ltv_estimate': ltv_estimate,
            'recommendations': recommendations
        }
    
    def _calculate_feature_importance(self, X: np.ndarray, cluster_labels: np.ndarray) -> Dict[str, float]:
        """Calculate feature importance for segmentation"""
        
        from sklearn.ensemble import RandomForestClassifier
        
        # Train a classifier to predict clusters
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, cluster_labels)
        
        # Get feature importance
        importance_scores = rf.feature_importances_
        
        feature_importance = {}
        for i, feature_name in enumerate(self.feature_names):
            feature_importance[feature_name] = float(importance_scores[i])
        
        return feature_importance
    
    def predict_user_segment(self, user_id: str, bigquery_client: bigquery.Client,
                           project_id: str) -> UserProfile:
        """Predict segment for a single user"""
        
        if not self.trained:
            raise ValueError("Model not trained. Call train_segmentation_model() first.")
        
        # Extract user features
        user_features = self.feature_extractor.extract_user_features(
            user_id, bigquery_client, project_id
        )
        
        # Convert to array and scale
        feature_vector = np.array([user_features[name] for name in self.feature_names]).reshape(1, -1)
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # Predict segment
        segment_id = self.clustering_model.predict(feature_vector_scaled)[0]
        segment = self.segments.get(segment_id)
        
        # Calculate risk score (simplified churn prediction)
        risk_score = self._calculate_churn_risk(user_features)
        
        return UserProfile(
            user_id=user_id,
            segment_id=segment_id,
            segment_name=segment.segment_name if segment else f"Segment {segment_id}",
            behavior_features=user_features,
            preferences=self._extract_preferences(user_features),
            predicted_ltv=segment.ltv_estimate if segment else 50.0,
            risk_score=risk_score,
            last_updated=datetime.now()
        )
    
    def _calculate_churn_risk(self, user_features: Dict[str, float]) -> float:
        """Calculate churn risk score for a user"""
        
        # Simple churn risk based on engagement metrics
        engagement_indicators = [
            user_features.get('listening_frequency', 0),
            user_features.get('avg_completion_rate', 0),
            1 - user_features.get('skip_rate', 1)  # Lower skip rate = lower risk
        ]
        
        engagement_score = np.mean(engagement_indicators)
        
        # Risk is inverse of engagement
        risk_score = 1 - engagement_score
        
        return float(np.clip(risk_score, 0, 1))
    
    def _extract_preferences(self, user_features: Dict[str, float]) -> Dict[str, Any]:
        """Extract user preferences from features"""
        
        preferences = {
            'content_type': 'varied' if user_features.get('genre_diversity', 0) > 0.5 else 'focused',
            'episode_length': 'short' if user_features.get('short_episode_preference', 0) > 0.5 else 'long',
            'listening_time': 'morning' if user_features.get('morning_listening', 0) > 0.5 else 'evening',
            'platform_preference': 'multi-platform' if user_features.get('platform_diversity', 0) > 0.5 else 'single-platform'
        }
        
        return preferences
    
    def get_segment_summary(self) -> Dict[str, Any]:
        """Get summary of all segments"""
        
        if not self.segments:
            return {}
        
        summary = {
            'total_segments': len(self.segments),
            'segments': {},
            'total_users': sum(segment.user_count for segment in self.segments.values())
        }
        
        for segment_id, segment in self.segments.items():
            summary['segments'][segment_id] = {
                'name': segment.segment_name,
                'description': segment.description,
                'user_count': segment.user_count,
                'percentage': (segment.user_count / summary['total_users']) * 100,
                'ltv_estimate': segment.ltv_estimate,
                'top_characteristics': self._get_top_characteristics(segment.characteristics)
            }
        
        return summary
    
    def _get_top_characteristics(self, characteristics: Dict[str, float], top_n: int = 3) -> List[str]:
        """Get top characteristics for a segment"""
        
        sorted_chars = sorted(characteristics.items(), key=lambda x: x[1], reverse=True)
        return [char[0] for char in sorted_chars[:top_n]]


# Global instance
user_segmentation_model = UserSegmentationModel() 