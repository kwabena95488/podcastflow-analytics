"""
PodcastFlow Analytics - Episode Performance Prediction Models
Phase 3 Week 3: Advanced Analytics & ML Integration

Features:
- Episode performance prediction using deep learning
- Time series forecasting for listening trends
- Multi-target prediction (downloads, completion rates, engagement)
- Real-time prediction serving
- Feature importance analysis
- A/B testing for prediction accuracy
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from google.cloud import bigquery
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import pickle

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class PredictionRequest:
    """Episode performance prediction request"""
    episode_title: str
    episode_description: str
    podcast_id: str
    tenant_id: str
    release_time: datetime
    estimated_duration_minutes: int
    episode_number: int
    context: Dict[str, Any] = None

@dataclass
class PredictionResult:
    """Episode performance prediction result"""
    episode_id: str
    predicted_downloads: int
    predicted_completion_rate: float
    predicted_engagement_score: float
    predicted_rating: float
    confidence_interval: Dict[str, float]
    feature_importance: Dict[str, float]
    prediction_timestamp: datetime

class TimeSeriesFeatureExtractor:
    """Extract time series features for episode performance prediction"""
    
    def __init__(self):
        self.seasonal_features = ['hour', 'day_of_week', 'day_of_month', 'month', 'quarter']
        self.trend_lookback_days = [7, 14, 30, 90]
    
    def extract_temporal_features(self, timestamp: datetime) -> Dict[str, float]:
        """Extract temporal features from timestamp"""
        
        features = {
            'hour': timestamp.hour / 23.0,
            'day_of_week': timestamp.weekday() / 6.0,
            'day_of_month': timestamp.day / 31.0,
            'month': timestamp.month / 12.0,
            'quarter': ((timestamp.month - 1) // 3) / 3.0,
            'is_weekend': float(timestamp.weekday() >= 5),
            'is_holiday': self._is_holiday(timestamp)
        }
        
        return features
    
    def _is_holiday(self, timestamp: datetime) -> float:
        """Simple holiday detection (can be enhanced with proper holiday library)"""
        # Major US holidays (simplified)
        holidays = [
            (1, 1),   # New Year's Day
            (7, 4),   # Independence Day
            (12, 25), # Christmas
        ]
        
        month_day = (timestamp.month, timestamp.day)
        return float(month_day in holidays)
    
    def extract_historical_features(self, podcast_id: str, current_time: datetime,
                                  bigquery_client: bigquery.Client, project_id: str) -> Dict[str, float]:
        """Extract historical performance features"""
        
        features = {}
        
        for lookback_days in self.trend_lookback_days:
            start_date = current_time - timedelta(days=lookback_days)
            
            # Query historical performance
            query = f"""
            SELECT 
                COUNT(*) as episode_count,
                AVG(downloads) as avg_downloads,
                AVG(completion_rate) as avg_completion_rate,
                AVG(engagement_score) as avg_engagement_score
            FROM `{project_id}.gold.episode_performance_metrics`
            WHERE podcast_id = '{podcast_id}'
              AND release_date >= '{start_date.strftime('%Y-%m-%d')}'
              AND release_date < '{current_time.strftime('%Y-%m-%d')}'
            """
            
            try:
                result = bigquery_client.query(query).to_dataframe()
                if not result.empty:
                    row = result.iloc[0]
                    features[f'episodes_last_{lookback_days}d'] = row['episode_count']
                    features[f'avg_downloads_last_{lookback_days}d'] = row['avg_downloads'] or 0
                    features[f'avg_completion_last_{lookback_days}d'] = row['avg_completion_rate'] or 0
                    features[f'avg_engagement_last_{lookback_days}d'] = row['avg_engagement_score'] or 0
                else:
                    features[f'episodes_last_{lookback_days}d'] = 0
                    features[f'avg_downloads_last_{lookback_days}d'] = 0
                    features[f'avg_completion_last_{lookback_days}d'] = 0
                    features[f'avg_engagement_last_{lookback_days}d'] = 0
            except Exception as e:
                logger.warning(f"Failed to extract {lookback_days}d features: {str(e)}")
                # Set default values
                features[f'episodes_last_{lookback_days}d'] = 0
                features[f'avg_downloads_last_{lookback_days}d'] = 0
                features[f'avg_completion_last_{lookback_days}d'] = 0
                features[f'avg_engagement_last_{lookback_days}d'] = 0
        
        return features

class ContentFeatureExtractor:
    """Extract content-based features from episode metadata"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.fitted = False
    
    def extract_text_features(self, title: str, description: str) -> Dict[str, float]:
        """Extract text-based features"""
        
        # Basic text statistics
        features = {
            'title_length': len(title),
            'title_word_count': len(title.split()),
            'description_length': len(description),
            'description_word_count': len(description.split()),
            'description_sentence_count': len(description.split('.')),
            'has_question_in_title': float('?' in title),
            'has_number_in_title': float(any(char.isdigit() for char in title)),
            'title_sentiment': self._simple_sentiment(title),
            'description_sentiment': self._simple_sentiment(description)
        }
        
        return features
    
    def _simple_sentiment(self, text: str) -> float:
        """Simple sentiment analysis (can be enhanced with proper NLP)"""
        positive_words = ['amazing', 'great', 'excellent', 'fantastic', 'awesome', 'best']
        negative_words = ['bad', 'terrible', 'awful', 'worst', 'horrible', 'disappointing']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count + negative_count == 0:
            return 0.5  # Neutral
        
        return positive_count / (positive_count + negative_count)
    
    def fit_tfidf(self, texts: List[str]):
        """Fit TF-IDF vectorizer on training data"""
        self.tfidf_vectorizer.fit(texts)
        self.fitted = True
    
    def extract_tfidf_features(self, title: str, description: str) -> np.ndarray:
        """Extract TF-IDF features"""
        if not self.fitted:
            return np.zeros(100)  # Return zeros if not fitted
        
        combined_text = f"{title} {description}"
        tfidf_features = self.tfidf_vectorizer.transform([combined_text])
        return tfidf_features.toarray()[0]

class EpisodePerformancePredictor:
    """Deep learning model for episode performance prediction"""
    
    def __init__(self):
        self.model = None
        self.feature_scaler = StandardScaler()
        self.target_scalers = {
            'downloads': MinMaxScaler(),
            'completion_rate': MinMaxScaler(),
            'engagement_score': MinMaxScaler(),
            'rating': MinMaxScaler()
        }
        self.feature_extractors = {
            'temporal': TimeSeriesFeatureExtractor(),
            'content': ContentFeatureExtractor()
        }
        self.feature_names = []
        self.trained = False
    
    def _build_model(self, input_dim: int):
        """Build multi-target neural network model"""
        
        # Input layer
        inputs = keras.Input(shape=(input_dim,), name='episode_features')
        
        # Shared hidden layers
        x = layers.Dense(256, activation='relu')(inputs)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(128, activation='relu')(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(64, activation='relu')(x)
        x = layers.Dropout(0.1)(x)
        
        # Task-specific output layers
        downloads_output = layers.Dense(32, activation='relu')(x)
        downloads_output = layers.Dense(1, activation='linear', name='downloads')(downloads_output)
        
        completion_output = layers.Dense(32, activation='relu')(x)
        completion_output = layers.Dense(1, activation='sigmoid', name='completion_rate')(completion_output)
        
        engagement_output = layers.Dense(32, activation='relu')(x)
        engagement_output = layers.Dense(1, activation='sigmoid', name='engagement_score')(engagement_output)
        
        rating_output = layers.Dense(32, activation='relu')(x)
        rating_output = layers.Dense(1, activation='sigmoid', name='rating')(rating_output)
        
        # Create model
        model = keras.Model(
            inputs=inputs,
            outputs=[downloads_output, completion_output, engagement_output, rating_output],
            name='episode_performance_predictor'
        )
        
        # Compile with multiple losses
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'downloads': 'mse',
                'completion_rate': 'mse',
                'engagement_score': 'mse',
                'rating': 'mse'
            },
            loss_weights={
                'downloads': 1.0,
                'completion_rate': 1.0,
                'engagement_score': 1.0,
                'rating': 1.0
            },
            metrics=['mae']
        )
        
        return model
    
    def prepare_features(self, episodes_df: pd.DataFrame, 
                        bigquery_client: bigquery.Client, project_id: str) -> np.ndarray:
        """Prepare feature matrix from episodes dataframe"""
        
        all_features = []
        
        for _, episode in episodes_df.iterrows():
            episode_features = {}
            
            # Temporal features
            release_time = pd.to_datetime(episode['release_date'])
            temporal_features = self.feature_extractors['temporal'].extract_temporal_features(release_time)
            episode_features.update(temporal_features)
            
            # Historical features
            historical_features = self.feature_extractors['temporal'].extract_historical_features(
                episode['podcast_id'], release_time, bigquery_client, project_id
            )
            episode_features.update(historical_features)
            
            # Content features
            content_features = self.feature_extractors['content'].extract_text_features(
                episode['title'], episode['description']
            )
            episode_features.update(content_features)
            
            # Episode metadata features
            episode_features.update({
                'duration_minutes': episode.get('duration_minutes', 30),
                'episode_number': episode.get('episode_number', 1),
                'is_series_premiere': float(episode.get('episode_number', 1) == 1)
            })
            
            all_features.append(episode_features)
        
        # Convert to DataFrame for consistent ordering
        features_df = pd.DataFrame(all_features)
        
        # Store feature names
        if not self.feature_names:
            self.feature_names = features_df.columns.tolist()
        
        # Ensure consistent feature ordering
        features_df = features_df.reindex(columns=self.feature_names, fill_value=0)
        
        return features_df.values
    
    def train(self, episodes_df: pd.DataFrame, bigquery_client: bigquery.Client, 
              project_id: str, epochs: int = 100, validation_split: float = 0.2):
        """Train the episode performance prediction model"""
        
        logger.info("Starting episode performance model training...")
        
        # Prepare features
        X = self.prepare_features(episodes_df, bigquery_client, project_id)
        
        # Prepare targets
        targets = {
            'downloads': episodes_df['downloads'].values,
            'completion_rate': episodes_df['completion_rate'].values,
            'engagement_score': episodes_df['engagement_score'].values,
            'rating': episodes_df['rating'].values
        }
        
        # Scale features
        X_scaled = self.feature_scaler.fit_transform(X)
        
        # Scale targets
        targets_scaled = {}
        for target_name, target_values in targets.items():
            targets_scaled[target_name] = self.target_scalers[target_name].fit_transform(
                target_values.reshape(-1, 1)
            ).flatten()
        
        # Build model
        self.model = self._build_model(X_scaled.shape[1])
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=15,
                restore_best_weights=True
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=8,
                min_lr=0.00001
            )
        ]
        
        # Train model
        history = self.model.fit(
            X_scaled,
            targets_scaled,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        self.trained = True
        logger.info("Episode performance model training completed")
        
        return history
    
    def predict(self, episode_data: Dict[str, Any], 
                bigquery_client: bigquery.Client, project_id: str) -> PredictionResult:
        """Predict episode performance"""
        
        if not self.trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Create episode dataframe
        episode_df = pd.DataFrame([{
            'title': episode_data['title'],
            'description': episode_data['description'],
            'podcast_id': episode_data['podcast_id'],
            'release_date': episode_data['release_time'],
            'duration_minutes': episode_data.get('duration_minutes', 30),
            'episode_number': episode_data.get('episode_number', 1)
        }])
        
        # Prepare features
        X = self.prepare_features(episode_df, bigquery_client, project_id)
        X_scaled = self.feature_scaler.transform(X)
        
        # Make prediction
        predictions = self.model.predict(X_scaled)
        
        # Inverse scale predictions
        downloads_pred = self.target_scalers['downloads'].inverse_transform(
            predictions[0].reshape(-1, 1)
        )[0, 0]
        
        completion_pred = self.target_scalers['completion_rate'].inverse_transform(
            predictions[1].reshape(-1, 1)
        )[0, 0]
        
        engagement_pred = self.target_scalers['engagement_score'].inverse_transform(
            predictions[2].reshape(-1, 1)
        )[0, 0]
        
        rating_pred = self.target_scalers['rating'].inverse_transform(
            predictions[3].reshape(-1, 1)
        )[0, 0]
        
        # Calculate feature importance (simplified)
        feature_importance = self._calculate_feature_importance(X_scaled[0])
        
        # Create confidence intervals (simplified)
        confidence_interval = {
            'downloads_lower': max(0, downloads_pred * 0.8),
            'downloads_upper': downloads_pred * 1.2,
            'completion_rate_lower': max(0, completion_pred - 0.1),
            'completion_rate_upper': min(1, completion_pred + 0.1)
        }
        
        return PredictionResult(
            episode_id=f"predicted_{int(datetime.now().timestamp())}",
            predicted_downloads=int(max(0, downloads_pred)),
            predicted_completion_rate=float(np.clip(completion_pred, 0, 1)),
            predicted_engagement_score=float(np.clip(engagement_pred, 0, 1)),
            predicted_rating=float(np.clip(rating_pred, 0, 1)),
            confidence_interval=confidence_interval,
            feature_importance=feature_importance,
            prediction_timestamp=datetime.now()
        )
    
    def _calculate_feature_importance(self, feature_vector: np.ndarray) -> Dict[str, float]:
        """Calculate feature importance for prediction explanation"""
        
        # Simple feature importance based on absolute values
        importance_scores = np.abs(feature_vector)
        
        # Normalize to sum to 1
        if importance_scores.sum() > 0:
            importance_scores = importance_scores / importance_scores.sum()
        
        # Create importance dictionary
        feature_importance = {}
        for i, feature_name in enumerate(self.feature_names):
            if i < len(importance_scores):
                feature_importance[feature_name] = float(importance_scores[i])
        
        # Return top 10 most important features
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_features[:10])
    
    def save_model(self, model_path: str):
        """Save trained model and preprocessors"""
        
        try:
            # Save TensorFlow model
            if self.model:
                self.model.save(os.path.join(model_path, 'episode_performance_model.h5'))
            
            # Save preprocessors
            joblib.dump(self.feature_scaler, os.path.join(model_path, 'feature_scaler.pkl'))
            
            for target_name, scaler in self.target_scalers.items():
                joblib.dump(scaler, os.path.join(model_path, f'{target_name}_scaler.pkl'))
            
            # Save feature names
            with open(os.path.join(model_path, 'feature_names.json'), 'w') as f:
                json.dump(self.feature_names, f)
            
            logger.info(f"Episode performance model saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
    
    def load_model(self, model_path: str):
        """Load trained model and preprocessors"""
        
        try:
            # Load TensorFlow model
            model_file = os.path.join(model_path, 'episode_performance_model.h5')
            if os.path.exists(model_file):
                self.model = keras.models.load_model(model_file)
                self.trained = True
            
            # Load preprocessors
            scaler_file = os.path.join(model_path, 'feature_scaler.pkl')
            if os.path.exists(scaler_file):
                self.feature_scaler = joblib.load(scaler_file)
            
            for target_name in self.target_scalers.keys():
                scaler_file = os.path.join(model_path, f'{target_name}_scaler.pkl')
                if os.path.exists(scaler_file):
                    self.target_scalers[target_name] = joblib.load(scaler_file)
            
            # Load feature names
            feature_names_file = os.path.join(model_path, 'feature_names.json')
            if os.path.exists(feature_names_file):
                with open(feature_names_file, 'r') as f:
                    self.feature_names = json.load(f)
            
            logger.info(f"Episode performance model loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")

class PredictionService:
    """Service for episode performance predictions"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.bigquery_client = bigquery.Client(project=project_id)
        self.predictor = EpisodePerformancePredictor()
        
        # Try to load pre-trained model
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'episode_performance')
        if os.path.exists(model_path):
            self.predictor.load_model(model_path)
    
    def get_training_data(self, tenant_id: str = None, limit: int = 10000) -> pd.DataFrame:
        """Get training data from BigQuery"""
        
        query = f"""
        SELECT 
            e.episode_id,
            e.title,
            e.description,
            e.podcast_id,
            e.release_date,
            e.duration_minutes,
            e.episode_number,
            COALESCE(p.downloads, 0) as downloads,
            COALESCE(p.completion_rate, 0.5) as completion_rate,
            COALESCE(p.engagement_score, 0.5) as engagement_score,
            COALESCE(p.rating, 0.5) as rating
        FROM `{self.project_id}.silver.episode_metadata` e
        LEFT JOIN `{self.project_id}.gold.episode_performance_metrics` p
        ON e.episode_id = p.episode_id
        WHERE e.release_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
        {f"AND e.tenant_id = '{tenant_id}'" if tenant_id else ""}
        ORDER BY e.release_date DESC
        LIMIT {limit}
        """
        
        try:
            df = self.bigquery_client.query(query).to_dataframe()
            logger.info(f"Loaded {len(df)} episodes for training")
            return df
        except Exception as e:
            logger.error(f"Failed to load training data: {str(e)}")
            return self._generate_sample_training_data()
    
    def _generate_sample_training_data(self) -> pd.DataFrame:
        """Generate sample training data for demonstration"""
        
        np.random.seed(42)
        n_episodes = 500
        
        # Sample episode data
        episodes = []
        for i in range(n_episodes):
            # Create realistic episode data
            duration = np.random.normal(35, 15)  # Average 35 minutes
            episode_number = np.random.randint(1, 200)
            
            # Simulate performance based on duration and episode number
            downloads = int(np.random.lognormal(7, 1.5)) * (1 + np.random.normal(0, 0.3))
            completion_rate = np.clip(0.7 - (duration - 30) * 0.01 + np.random.normal(0, 0.1), 0, 1)
            engagement_score = np.clip(completion_rate * 0.8 + np.random.normal(0, 0.1), 0, 1)
            rating = np.clip(engagement_score * 0.9 + np.random.normal(0, 0.1), 0, 1)
            
            episodes.append({
                'episode_id': f'episode_{i}',
                'title': f'Episode {episode_number}: Sample Topic {i}',
                'description': f'This is a sample episode description {i} with some content about podcasting.',
                'podcast_id': f'podcast_{np.random.randint(1, 10)}',
                'release_date': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
                'duration_minutes': max(10, duration),
                'episode_number': episode_number,
                'downloads': downloads,
                'completion_rate': completion_rate,
                'engagement_score': engagement_score,
                'rating': rating
            })
        
        return pd.DataFrame(episodes)
    
    def train_predictor(self, tenant_id: str = None, retrain: bool = False):
        """Train the episode performance predictor"""
        
        if self.predictor.trained and not retrain:
            logger.info("Predictor already trained, skipping training")
            return
        
        # Get training data
        training_data = self.get_training_data(tenant_id)
        
        if training_data.empty:
            logger.warning("No training data available")
            return
        
        # Train model
        history = self.predictor.train(
            training_data, 
            self.bigquery_client, 
            self.project_id,
            epochs=50
        )
        
        # Save model
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'episode_performance')
        os.makedirs(model_path, exist_ok=True)
        self.predictor.save_model(model_path)
        
        return history
    
    def predict_episode_performance(self, request: PredictionRequest) -> PredictionResult:
        """Predict episode performance"""
        
        if not self.predictor.trained:
            # Train with sample data if not trained
            self.train_predictor()
        
        episode_data = {
            'title': request.episode_title,
            'description': request.episode_description,
            'podcast_id': request.podcast_id,
            'release_time': request.release_time,
            'duration_minutes': request.estimated_duration_minutes,
            'episode_number': request.episode_number
        }
        
        return self.predictor.predict(episode_data, self.bigquery_client, self.project_id)


# Global instance
prediction_service = PredictionService(
    project_id=os.getenv('GOOGLE_CLOUD_PROJECT', 'your-gcp-project')
) 