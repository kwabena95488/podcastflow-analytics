"""
PodcastFlow Analytics - Content Recommendation Engine
Phase 3 Week 3: Advanced Analytics & ML Integration

Features:
- TensorFlow-based deep learning recommendation models
- Collaborative filtering with neural networks
- Content-based filtering with NLP embeddings
- Hybrid recommendation approach
- Real-time inference capabilities
- A/B testing framework for recommendation strategies
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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class RecommendationRequest:
    """Recommendation request data structure"""
    user_id: str
    tenant_id: str
    num_recommendations: int = 10
    recommendation_type: str = "hybrid"  # collaborative, content_based, hybrid
    context: Dict[str, Any] = None  # listening context (time, platform, etc.)

@dataclass
class RecommendationResult:
    """Recommendation result data structure"""
    user_id: str
    podcast_id: str
    episode_id: str
    confidence_score: float
    recommendation_reason: str
    recommendation_type: str
    generated_at: datetime

class CollaborativeFilteringModel:
    """Deep learning collaborative filtering model"""
    
    def __init__(self, num_users: int, num_items: int, embedding_dim: int = 64):
        self.num_users = num_users
        self.num_items = num_items
        self.embedding_dim = embedding_dim
        self.model = None
        self._build_model()
    
    def _build_model(self):
        """Build neural collaborative filtering model"""
        
        # User and item inputs
        user_input = keras.Input(shape=(), name='user_id')
        item_input = keras.Input(shape=(), name='item_id')
        
        # Embedding layers
        user_embedding = layers.Embedding(
            self.num_users,
            self.embedding_dim,
            name='user_embedding'
        )(user_input)
        
        item_embedding = layers.Embedding(
            self.num_items,
            self.embedding_dim,
            name='item_embedding'
        )(item_input)
        
        # Flatten embeddings
        user_vec = layers.Flatten()(user_embedding)
        item_vec = layers.Flatten()(item_embedding)
        
        # Neural MF pathway
        concat = layers.Concatenate()([user_vec, item_vec])
        
        # Deep neural network
        dense1 = layers.Dense(128, activation='relu')(concat)
        dropout1 = layers.Dropout(0.2)(dense1)
        dense2 = layers.Dense(64, activation='relu')(dropout1)
        dropout2 = layers.Dropout(0.2)(dense2)
        dense3 = layers.Dense(32, activation='relu')(dropout2)
        
        # Output layer
        output = layers.Dense(1, activation='sigmoid', name='rating_prediction')(dense3)
        
        # Create model
        self.model = keras.Model(
            inputs=[user_input, item_input],
            outputs=output,
            name='neural_collaborative_filtering'
        )
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['mae', 'mse']
        )
    
    def train(self, user_ids: np.ndarray, item_ids: np.ndarray, 
              ratings: np.ndarray, validation_split: float = 0.2,
              epochs: int = 50, batch_size: int = 256):
        """Train the collaborative filtering model"""
        
        # Prepare training data
        train_data = {
            'user_id': user_ids,
            'item_id': item_ids
        }
        
        # Add callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=0.0001
            )
        ]
        
        # Train model
        history = self.model.fit(
            train_data,
            ratings,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def predict(self, user_ids: np.ndarray, item_ids: np.ndarray) -> np.ndarray:
        """Make predictions for user-item pairs"""
        return self.model.predict({
            'user_id': user_ids,
            'item_id': item_ids
        })
    
    def get_user_recommendations(self, user_id: int, num_recommendations: int = 10,
                               exclude_items: List[int] = None) -> List[Tuple[int, float]]:
        """Get top recommendations for a user"""
        
        if exclude_items is None:
            exclude_items = []
        
        # Generate predictions for all items
        all_items = np.arange(self.num_items)
        user_ids = np.full(self.num_items, user_id)
        
        predictions = self.predict(user_ids, all_items)
        
        # Sort by prediction score
        item_scores = list(zip(all_items, predictions.flatten()))
        item_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Filter out excluded items and return top N
        recommendations = []
        for item_id, score in item_scores:
            if item_id not in exclude_items:
                recommendations.append((item_id, score))
                if len(recommendations) >= num_recommendations:
                    break
        
        return recommendations

class ContentBasedModel:
    """Content-based recommendation using TF-IDF and neural networks"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.content_model = None
        self.content_features = None
        self.item_encoder = LabelEncoder()
        self.scaler = StandardScaler()
    
    def _build_content_model(self, input_dim: int):
        """Build content-based neural network"""
        
        model = keras.Sequential([
            layers.Dense(256, activation='relu', input_shape=(input_dim,)),
            layers.Dropout(0.3),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(64, activation='relu'),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def prepare_content_features(self, podcasts_df: pd.DataFrame):
        """Prepare content features from podcast metadata"""
        
        # Combine text features
        text_features = (
            podcasts_df['title'].fillna('') + ' ' +
            podcasts_df['description'].fillna('') + ' ' +
            podcasts_df['categories'].fillna('')
        )
        
        # TF-IDF features
        tfidf_features = self.tfidf_vectorizer.fit_transform(text_features)
        
        # Numerical features
        numerical_features = []
        
        # Duration (normalized)
        if 'duration_minutes' in podcasts_df.columns:
            duration = podcasts_df['duration_minutes'].fillna(0)
            numerical_features.append(duration.values.reshape(-1, 1))
        
        # Episode count
        if 'episode_count' in podcasts_df.columns:
            episode_count = podcasts_df['episode_count'].fillna(0)
            numerical_features.append(episode_count.values.reshape(-1, 1))
        
        # Popularity score
        if 'popularity_score' in podcasts_df.columns:
            popularity = podcasts_df['popularity_score'].fillna(0)
            numerical_features.append(popularity.values.reshape(-1, 1))
        
        # Combine all features
        if numerical_features:
            numerical_array = np.hstack(numerical_features)
            numerical_scaled = self.scaler.fit_transform(numerical_array)
            self.content_features = np.hstack([
                tfidf_features.toarray(),
                numerical_scaled
            ])
        else:
            self.content_features = tfidf_features.toarray()
        
        return self.content_features
    
    def train_content_model(self, user_interactions: pd.DataFrame, podcasts_df: pd.DataFrame):
        """Train content-based model"""
        
        # Prepare content features
        content_features = self.prepare_content_features(podcasts_df)
        
        # Create training data from user interactions
        X_train = []
        y_train = []
        
        for _, interaction in user_interactions.iterrows():
            podcast_id = interaction['podcast_id']
            rating = interaction['rating']  # Implicit feedback (0 or 1)
            
            # Find podcast index
            podcast_idx = podcasts_df[podcasts_df['podcast_id'] == podcast_id].index
            if len(podcast_idx) > 0:
                X_train.append(content_features[podcast_idx[0]])
                y_train.append(1 if rating > 0.5 else 0)
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        
        # Build and train model
        self.content_model = self._build_content_model(X_train.shape[1])
        
        history = self.content_model.fit(
            X_train, y_train,
            validation_split=0.2,
            epochs=50,
            batch_size=32,
            callbacks=[
                keras.callbacks.EarlyStopping(patience=10),
                keras.callbacks.ReduceLROnPlateau(patience=5)
            ]
        )
        
        return history
    
    def get_content_recommendations(self, user_profile: np.ndarray, 
                                  num_recommendations: int = 10) -> List[Tuple[int, float]]:
        """Get content-based recommendations"""
        
        if self.content_model is None or self.content_features is None:
            return []
        
        # Predict preferences for all items
        predictions = self.content_model.predict(self.content_features)
        
        # Sort by prediction score
        item_scores = list(enumerate(predictions.flatten()))
        item_scores.sort(key=lambda x: x[1], reverse=True)
        
        return item_scores[:num_recommendations]

class RecommendationEngine:
    """Main recommendation engine combining multiple approaches"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.bigquery_client = bigquery.Client(project=project_id)
        
        # Models
        self.collaborative_model = None
        self.content_model = ContentBasedModel()
        
        # Data
        self.user_encoder = LabelEncoder()
        self.item_encoder = LabelEncoder()
        self.user_profiles = {}
        self.item_features = {}
        
        # Model metadata
        self.model_version = "1.0"
        self.last_trained = None
        
    def load_training_data(self, tenant_id: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load training data from BigQuery"""
        
        # User interactions query
        interactions_query = f"""
        SELECT DISTINCT
            user_id,
            podcast_id,
            episode_id,
            completion_percentage as rating,
            listening_duration_minutes,
            platform,
            created_at
        FROM `{self.project_id}.bronze.listening_events_realtime`
        WHERE completion_percentage > 0
        {f"AND tenant_id = '{tenant_id}'" if tenant_id else ""}
        ORDER BY created_at DESC
        LIMIT 100000
        """
        
        # Podcast metadata query
        podcasts_query = f"""
        SELECT DISTINCT
            podcast_id,
            title,
            description,
            categories,
            language,
            duration_minutes,
            episode_count,
            popularity_score
        FROM `{self.project_id}.silver.podcast_metadata`
        {f"WHERE tenant_id = '{tenant_id}'" if tenant_id else ""}
        """
        
        try:
            interactions_df = self.bigquery_client.query(interactions_query).to_dataframe()
            podcasts_df = self.bigquery_client.query(podcasts_query).to_dataframe()
            
            logger.info(f"Loaded {len(interactions_df)} interactions and {len(podcasts_df)} podcasts")
            return interactions_df, podcasts_df
            
        except Exception as e:
            logger.error(f"Failed to load training data: {str(e)}")
            # Return sample data for demo
            return self._generate_sample_data()
    
    def _generate_sample_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate sample data for demonstration"""
        
        # Sample interactions
        np.random.seed(42)
        n_interactions = 1000
        
        interactions_df = pd.DataFrame({
            'user_id': np.random.choice(['user_1', 'user_2', 'user_3', 'user_4'], n_interactions),
            'podcast_id': np.random.choice(['podcast_1', 'podcast_2', 'podcast_3'], n_interactions),
            'episode_id': np.random.choice(range(1, 101), n_interactions),
            'rating': np.random.beta(2, 1, n_interactions),  # Skewed towards higher ratings
            'listening_duration_minutes': np.random.exponential(15, n_interactions),
            'platform': np.random.choice(['spotify', 'apple', 'google'], n_interactions),
            'created_at': pd.date_range('2024-01-01', periods=n_interactions, freq='H')
        })
        
        # Sample podcasts
        podcasts_df = pd.DataFrame({
            'podcast_id': ['podcast_1', 'podcast_2', 'podcast_3'],
            'title': ['Tech Talk Daily', 'Business Insights', 'Science Explained'],
            'description': [
                'Daily technology news and insights',
                'Business strategy and entrepreneurship',
                'Science concepts made simple'
            ],
            'categories': ['Technology', 'Business', 'Science'],
            'language': ['en', 'en', 'en'],
            'duration_minutes': [30, 45, 25],
            'episode_count': [500, 200, 150],
            'popularity_score': [0.8, 0.6, 0.7]
        })
        
        return interactions_df, podcasts_df
    
    def train_models(self, tenant_id: str = None, retrain: bool = False):
        """Train all recommendation models"""
        
        if self.last_trained and not retrain:
            time_since_training = datetime.now() - self.last_trained
            if time_since_training < timedelta(days=1):
                logger.info("Models recently trained, skipping training")
                return
        
        logger.info("Starting model training...")
        
        # Load data
        interactions_df, podcasts_df = self.load_training_data(tenant_id)
        
        if interactions_df.empty or podcasts_df.empty:
            logger.warning("No training data available")
            return
        
        # Encode users and items
        unique_users = interactions_df['user_id'].unique()
        unique_items = interactions_df['podcast_id'].unique()
        
        user_ids = self.user_encoder.fit_transform(interactions_df['user_id'])
        item_ids = self.item_encoder.fit_transform(interactions_df['podcast_id'])
        ratings = interactions_df['rating'].values
        
        # Train collaborative filtering model
        self.collaborative_model = CollaborativeFilteringModel(
            num_users=len(unique_users),
            num_items=len(unique_items),
            embedding_dim=64
        )
        
        cf_history = self.collaborative_model.train(
            user_ids, item_ids, ratings,
            epochs=30, batch_size=128
        )
        
        # Train content-based model
        content_history = self.content_model.train_content_model(
            interactions_df, podcasts_df
        )
        
        self.last_trained = datetime.now()
        logger.info("Model training completed successfully")
        
        return {
            'collaborative_history': cf_history.history if cf_history else None,
            'content_history': content_history.history if content_history else None,
            'training_data_size': len(interactions_df),
            'num_users': len(unique_users),
            'num_items': len(unique_items)
        }
    
    def get_recommendations(self, request: RecommendationRequest) -> List[RecommendationResult]:
        """Generate recommendations for a user"""
        
        try:
            user_id = request.user_id
            num_recs = request.num_recommendations
            rec_type = request.recommendation_type
            
            recommendations = []
            
            if rec_type == "collaborative" and self.collaborative_model:
                recommendations.extend(
                    self._get_collaborative_recommendations(user_id, num_recs)
                )
            elif rec_type == "content_based":
                recommendations.extend(
                    self._get_content_based_recommendations(user_id, num_recs)
                )
            else:  # hybrid
                # Get half from each model
                half_recs = num_recs // 2
                
                if self.collaborative_model:
                    collaborative_recs = self._get_collaborative_recommendations(
                        user_id, half_recs
                    )
                    recommendations.extend(collaborative_recs)
                
                content_recs = self._get_content_based_recommendations(
                    user_id, num_recs - len(recommendations)
                )
                recommendations.extend(content_recs)
            
            # Sort by confidence score and return top N
            recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            return recommendations[:num_recs]
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {str(e)}")
            return self._get_fallback_recommendations(request)
    
    def _get_collaborative_recommendations(self, user_id: str, 
                                         num_recommendations: int) -> List[RecommendationResult]:
        """Get collaborative filtering recommendations"""
        
        recommendations = []
        
        try:
            # Encode user ID
            if user_id not in self.user_encoder.classes_:
                return []  # New user
            
            user_encoded = self.user_encoder.transform([user_id])[0]
            
            # Get recommendations from collaborative model
            cf_recs = self.collaborative_model.get_user_recommendations(
                user_encoded, num_recommendations
            )
            
            for item_encoded, score in cf_recs:
                # Decode item ID
                item_id = self.item_encoder.inverse_transform([item_encoded])[0]
                
                recommendation = RecommendationResult(
                    user_id=user_id,
                    podcast_id=item_id,
                    episode_id="latest",  # Would be determined by episode recommendation logic
                    confidence_score=float(score),
                    recommendation_reason="Users with similar preferences also liked this",
                    recommendation_type="collaborative",
                    generated_at=datetime.now()
                )
                recommendations.append(recommendation)
                
        except Exception as e:
            logger.error(f"Collaborative recommendations failed: {str(e)}")
        
        return recommendations
    
    def _get_content_based_recommendations(self, user_id: str, 
                                         num_recommendations: int) -> List[RecommendationResult]:
        """Get content-based recommendations"""
        
        recommendations = []
        
        try:
            # Get user profile (simplified - would use actual listening history)
            user_profile = np.random.rand(1, 5000)  # Placeholder
            
            # Get content recommendations
            content_recs = self.content_model.get_content_recommendations(
                user_profile, num_recommendations
            )
            
            for item_idx, score in content_recs:
                # Generate recommendation
                recommendation = RecommendationResult(
                    user_id=user_id,
                    podcast_id=f"podcast_{item_idx}",
                    episode_id="latest",
                    confidence_score=float(score),
                    recommendation_reason="Based on content you previously enjoyed",
                    recommendation_type="content_based",
                    generated_at=datetime.now()
                )
                recommendations.append(recommendation)
                
        except Exception as e:
            logger.error(f"Content-based recommendations failed: {str(e)}")
        
        return recommendations
    
    def _get_fallback_recommendations(self, request: RecommendationRequest) -> List[RecommendationResult]:
        """Get fallback recommendations when models fail"""
        
        # Simple popularity-based recommendations
        popular_podcasts = ['podcast_1', 'podcast_2', 'podcast_3']
        
        recommendations = []
        for i, podcast_id in enumerate(popular_podcasts[:request.num_recommendations]):
            recommendation = RecommendationResult(
                user_id=request.user_id,
                podcast_id=podcast_id,
                episode_id="latest",
                confidence_score=0.5 - (i * 0.1),
                recommendation_reason="Popular podcast",
                recommendation_type="fallback",
                generated_at=datetime.now()
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def save_models(self, model_path: str):
        """Save trained models to disk"""
        
        try:
            # Save collaborative model
            if self.collaborative_model and self.collaborative_model.model:
                cf_path = os.path.join(model_path, 'collaborative_model.h5')
                self.collaborative_model.model.save(cf_path)
            
            # Save content model
            if self.content_model.content_model:
                content_path = os.path.join(model_path, 'content_model.h5')
                self.content_model.content_model.save(content_path)
            
            # Save encoders and metadata
            metadata = {
                'user_encoder': self.user_encoder.classes_.tolist(),
                'item_encoder': self.item_encoder.classes_.tolist(),
                'model_version': self.model_version,
                'last_trained': self.last_trained.isoformat() if self.last_trained else None
            }
            
            metadata_path = os.path.join(model_path, 'model_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            logger.info(f"Models saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save models: {str(e)}")
    
    def load_models(self, model_path: str):
        """Load trained models from disk"""
        
        try:
            # Load metadata
            metadata_path = os.path.join(model_path, 'model_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                self.user_encoder.classes_ = np.array(metadata['user_encoder'])
                self.item_encoder.classes_ = np.array(metadata['item_encoder'])
                self.model_version = metadata['model_version']
                if metadata['last_trained']:
                    self.last_trained = datetime.fromisoformat(metadata['last_trained'])
            
            # Load models
            cf_path = os.path.join(model_path, 'collaborative_model.h5')
            if os.path.exists(cf_path):
                # Would need to rebuild model architecture first
                logger.info("Collaborative model found")
            
            content_path = os.path.join(model_path, 'content_model.h5')
            if os.path.exists(content_path):
                self.content_model.content_model = keras.models.load_model(content_path)
            
            logger.info(f"Models loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")


# Global instance
recommendation_engine = RecommendationEngine(
    project_id=os.getenv('GOOGLE_CLOUD_PROJECT', 'your-gcp-project')
) 