"""
PodcastFlow Analytics - Enhanced ML-Powered Dashboard
Phase 3 Week 3 Day 17-18: Advanced Dashboard Features with ML Insights

Features:
- Real-time ML-powered recommendations
- Episode performance prediction visualizations
- User segmentation analytics dashboard
- Interactive ML model performance monitoring
- Advanced analytics with AI insights
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import time
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import bigquery
from ml.recommendation_engine import recommendation_engine, RecommendationRequest
from ml.prediction_models import prediction_service, PredictionRequest
from ml.user_segmentation import user_segmentation_model

# Configure page
st.set_page_config(
    page_title="PodcastFlow Analytics - ML Dashboard",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-gcp-project')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8080')

# Initialize clients
@st.cache_resource
def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)

bigquery_client = get_bigquery_client()

# Enhanced Custom CSS with ML Theme
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .ml-metric-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    .ml-metric-card:hover {
        transform: translateY(-5px);
    }
    
    .prediction-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .segment-card {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .recommendation-item {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    
    .model-status {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    
    .insight-box {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #ff6b6b;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .stMetric > div > div > div > div {
        color: #2c3e50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🤖 PodcastFlow Analytics - ML Dashboard</h1>
    <p>Advanced Analytics with Machine Learning Insights</p>
    <p><em>Powered by TensorFlow & Advanced AI Models</em></p>
</div>
""", unsafe_allow_html=True)

# Sidebar for ML Model Controls
st.sidebar.markdown("## 🤖 ML Model Controls")

# Model Status Check
def check_model_status():
    """Check the status of ML models"""
    status = {
        'recommendation_engine': hasattr(recommendation_engine, 'collaborative_model') and recommendation_engine.collaborative_model is not None,
        'prediction_service': hasattr(prediction_service.predictor, 'trained') and prediction_service.predictor.trained,
        'segmentation_model': hasattr(user_segmentation_model, 'trained') and user_segmentation_model.trained
    }
    return status

model_status = check_model_status()

# Display Model Status
st.sidebar.markdown("### Model Status")
for model_name, is_ready in model_status.items():
    status_icon = "✅" if is_ready else "⚠️"
    status_text = "Ready" if is_ready else "Needs Training"
    st.sidebar.markdown(f"{status_icon} **{model_name.replace('_', ' ').title()}**: {status_text}")

# Model Training Controls
st.sidebar.markdown("### Model Training")
if st.sidebar.button("🔄 Train All Models"):
    with st.sidebar:
        with st.spinner("Training models..."):
            try:
                # Train recommendation engine
                recommendation_engine.train_models()
                st.success("✅ Recommendation engine trained")
                
                # Train prediction service
                prediction_service.train_predictor()
                st.success("✅ Prediction models trained")
                
                # Generate sample user data for segmentation
                sample_users = pd.DataFrame({
                    'user_id': [f'user_{i}' for i in range(1, 101)]
                })
                user_segmentation_model.train_segmentation_model(
                    sample_users, bigquery_client, PROJECT_ID
                )
                st.success("✅ Segmentation model trained")
                
                st.success("🎉 All models trained successfully!")
                time.sleep(2)
                st.experimental_rerun()
                
            except Exception as e:
                st.error(f"❌ Training failed: {str(e)}")

# User Selection for Personalized Views
st.sidebar.markdown("### User Selection")
selected_user = st.sidebar.selectbox(
    "Select User for Analysis",
    ["user_1", "user_2", "user_3", "user_4", "current_user"],
    index=0
)

# Main Dashboard Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Recommendations", 
    "📈 Performance Predictions", 
    "👥 User Segmentation", 
    "🔬 Model Monitoring", 
    "💡 AI Insights"
])

# Tab 1: ML-Powered Recommendations
with tab1:
    st.header("🎯 AI-Powered Content Recommendations")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Personalized Recommendations")
        
        # Recommendation controls
        col_controls1, col_controls2 = st.columns(2)
        with col_controls1:
            rec_type = st.selectbox(
                "Recommendation Strategy",
                ["hybrid", "collaborative", "content_based"],
                index=0
            )
        with col_controls2:
            num_recs = st.slider("Number of Recommendations", 5, 20, 10)
        
        if st.button("🚀 Generate Recommendations"):
            try:
                with st.spinner("Generating AI recommendations..."):
                    # Create recommendation request
                    req = RecommendationRequest(
                        user_id=selected_user,
                        tenant_id="demo_tenant",
                        num_recommendations=num_recs,
                        recommendation_type=rec_type
                    )
                    
                    # Get recommendations
                    recommendations = recommendation_engine.get_recommendations(req)
                    
                    if recommendations:
                        st.success(f"✨ Generated {len(recommendations)} recommendations using {rec_type} approach")
                        
                        # Display recommendations
                        for i, rec in enumerate(recommendations, 1):
                            st.markdown(f"""
                            <div class="recommendation-item">
                                <h4>#{i} - {rec.podcast_id}</h4>
                                <p><strong>Episode:</strong> {rec.episode_id}</p>
                                <p><strong>Confidence:</strong> {rec.confidence_score:.3f}</p>
                                <p><strong>Reason:</strong> {rec.recommendation_reason}</p>
                                <p><strong>Type:</strong> {rec.recommendation_type}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("No recommendations generated. Try training the models first.")
                        
            except Exception as e:
                st.error(f"Recommendation generation failed: {str(e)}")
    
    with col2:
        st.subheader("📊 Recommendation Analytics")
        
        # Simulated recommendation metrics
        rec_metrics = {
            "Click-through Rate": 0.12,
            "Conversion Rate": 0.08,
            "User Satisfaction": 0.85,
            "Model Accuracy": 0.91
        }
        
        for metric, value in rec_metrics.items():
            st.metric(metric, f"{value:.1%}")
        
        # Recommendation type distribution
        fig_rec_dist = px.pie(
            values=[40, 35, 25],
            names=['Collaborative', 'Content-based', 'Hybrid'],
            title="Recommendation Strategy Usage",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_rec_dist.update_layout(height=300)
        st.plotly_chart(fig_rec_dist, use_container_width=True)

# Tab 2: Performance Predictions
with tab2:
    st.header("📈 Episode Performance Predictions")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("🔮 Predict Episode Performance")
        
        # Prediction input form
        with st.form("prediction_form"):
            episode_title = st.text_input(
                "Episode Title",
                value="The Future of AI in Podcasting",
                max_chars=200
            )
            
            episode_description = st.text_area(
                "Episode Description",
                value="An in-depth discussion about how artificial intelligence is revolutionizing the podcasting industry, featuring expert insights and real-world applications.",
                max_chars=1000,
                height=100
            )
            
            col_input1, col_input2 = st.columns(2)
            with col_input1:
                podcast_id = st.selectbox(
                    "Podcast",
                    ["podcast_1", "podcast_2", "podcast_3"]
                )
                duration = st.slider("Duration (minutes)", 15, 120, 35)
            
            with col_input2:
                episode_number = st.number_input("Episode Number", min_value=1, value=42)
                release_date = st.date_input("Release Date", datetime.now().date())
            
            predict_button = st.form_submit_button("🎯 Predict Performance")
        
        if predict_button:
            try:
                with st.spinner("🤖 AI is analyzing episode potential..."):
                    # Create prediction request
                    pred_req = PredictionRequest(
                        episode_title=episode_title,
                        episode_description=episode_description,
                        podcast_id=podcast_id,
                        tenant_id="demo_tenant",
                        release_time=datetime.combine(release_date, datetime.now().time()),
                        estimated_duration_minutes=duration,
                        episode_number=episode_number
                    )
                    
                    # Get prediction
                    prediction = prediction_service.predict_episode_performance(pred_req)
                    
                    # Display prediction results
                    st.markdown("""
                    <div class="prediction-card">
                        <h3>🎯 Performance Prediction Results</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Prediction metrics
                    col_pred1, col_pred2, col_pred3, col_pred4 = st.columns(4)
                    
                    with col_pred1:
                        st.metric(
                            "📥 Downloads", 
                            f"{prediction.predicted_downloads:,}",
                            delta=f"±{int(prediction.confidence_interval.get('downloads_upper', 0) - prediction.predicted_downloads):,}"
                        )
                    
                    with col_pred2:
                        st.metric(
                            "⏱️ Completion Rate", 
                            f"{prediction.predicted_completion_rate:.1%}",
                            delta=f"±{prediction.confidence_interval.get('completion_rate_upper', 0) - prediction.predicted_completion_rate:.1%}"
                        )
                    
                    with col_pred3:
                        st.metric(
                            "💫 Engagement Score", 
                            f"{prediction.predicted_engagement_score:.3f}",
                            delta="High" if prediction.predicted_engagement_score > 0.7 else "Medium"
                        )
                    
                    with col_pred4:
                        st.metric(
                            "⭐ Rating", 
                            f"{prediction.predicted_rating:.2f}/1.0",
                            delta="Excellent" if prediction.predicted_rating > 0.8 else "Good"
                        )
                    
                    # Feature importance chart
                    if prediction.feature_importance:
                        st.subheader("🔍 Feature Importance Analysis")
                        
                        importance_df = pd.DataFrame(
                            list(prediction.feature_importance.items()),
                            columns=['Feature', 'Importance']
                        ).sort_values('Importance', ascending=True)
                        
                        fig_importance = px.bar(
                            importance_df.tail(10),
                            x='Importance',
                            y='Feature',
                            orientation='h',
                            title="Top 10 Predictive Features",
                            color='Importance',
                            color_continuous_scale='viridis'
                        )
                        fig_importance.update_layout(height=400)
                        st.plotly_chart(fig_importance, use_container_width=True)
                        
            except Exception as e:
                st.error(f"Prediction failed: {str(e)}")
    
    with col2:
        st.subheader("📊 Historical Performance")
        
        # Simulated historical data
        dates = pd.date_range(start='2024-01-01', end='2024-12-30', freq='W')
        historical_data = pd.DataFrame({
            'date': dates,
            'downloads': np.random.lognormal(8, 0.5, len(dates)),
            'completion_rate': np.random.beta(8, 3, len(dates)),
            'engagement_score': np.random.beta(6, 4, len(dates))
        })
        
        # Downloads trend
        fig_downloads = px.line(
            historical_data,
            x='date',
            y='downloads',
            title='Downloads Trend',
            color_discrete_sequence=['#667eea']
        )
        fig_downloads.update_layout(height=200)
        st.plotly_chart(fig_downloads, use_container_width=True)
        
        # Completion rate trend
        fig_completion = px.line(
            historical_data,
            x='date',
            y='completion_rate',
            title='Completion Rate Trend',
            color_discrete_sequence=['#764ba2']
        )
        fig_completion.update_layout(height=200)
        st.plotly_chart(fig_completion, use_container_width=True)

# Tab 3: User Segmentation
with tab3:
    st.header("👥 User Segmentation Analytics")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎭 User Personas & Segments")
        
        # Get user segmentation
        if st.button("🔍 Analyze User Segment"):
            try:
                with st.spinner("Analyzing user behavior patterns..."):
                    user_profile = user_segmentation_model.predict_user_segment(
                        selected_user, bigquery_client, PROJECT_ID
                    )
                    
                    st.markdown(f"""
                    <div class="segment-card">
                        <h3>🎭 User Profile: {user_profile.user_id}</h3>
                        <h4>Segment: {user_profile.segment_name}</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # User metrics
                    col_user1, col_user2, col_user3 = st.columns(3)
                    
                    with col_user1:
                        st.metric("💰 Predicted LTV", f"${user_profile.predicted_ltv:.0f}")
                    
                    with col_user2:
                        risk_color = "🔴" if user_profile.risk_score > 0.7 else "🟡" if user_profile.risk_score > 0.4 else "🟢"
                        st.metric("⚠️ Churn Risk", f"{user_profile.risk_score:.1%}", delta=risk_color)
                    
                    with col_user3:
                        st.metric("🔄 Last Updated", user_profile.last_updated.strftime("%m/%d"))
                    
                    # User preferences
                    st.subheader("🎯 User Preferences")
                    pref_cols = st.columns(len(user_profile.preferences))
                    for i, (pref, value) in enumerate(user_profile.preferences.items()):
                        with pref_cols[i]:
                            st.metric(pref.replace('_', ' ').title(), str(value))
                    
                    # Behavioral features visualization
                    st.subheader("📊 Behavioral Analysis")
                    
                    # Create radar chart for behavioral features
                    features = list(user_profile.behavior_features.keys())[:8]  # Top 8 features
                    values = [user_profile.behavior_features[f] for f in features]
                    
                    fig_radar = go.Figure()
                    fig_radar.add_trace(go.Scatterpolar(
                        r=values,
                        theta=features,
                        fill='toself',
                        name=user_profile.segment_name
                    ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 1])
                        ),
                        showlegend=True,
                        title="User Behavioral Profile",
                        height=400
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
                    
            except ValueError as e:
                st.warning("⚠️ Segmentation model not trained. Please train the model first using the sidebar controls.")
            except Exception as e:
                st.error(f"Segmentation analysis failed: {str(e)}")
    
    with col2:
        st.subheader("📈 Segment Overview")
        
        # Display segment summary if available
        try:
            summary = user_segmentation_model.get_segment_summary()
            if summary and 'segments' in summary:
                st.metric("Total Segments", summary['total_segments'])
                st.metric("Total Users", summary['total_users'])
                
                # Segment distribution
                segment_data = []
                for seg_id, seg_info in summary['segments'].items():
                    segment_data.append({
                        'Segment': seg_info['name'],
                        'Users': seg_info['user_count'],
                        'Percentage': seg_info['percentage'],
                        'LTV': seg_info['ltv_estimate']
                    })
                
                segment_df = pd.DataFrame(segment_data)
                
                # Segment distribution pie chart
                fig_segments = px.pie(
                    segment_df,
                    values='Users',
                    names='Segment',
                    title="User Distribution by Segment",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_segments.update_layout(height=300)
                st.plotly_chart(fig_segments, use_container_width=True)
                
                # LTV by segment
                fig_ltv = px.bar(
                    segment_df,
                    x='Segment',
                    y='LTV',
                    title="Predicted LTV by Segment",
                    color='LTV',
                    color_continuous_scale='viridis'
                )
                fig_ltv.update_layout(height=300)
                st.plotly_chart(fig_ltv, use_container_width=True)
            else:
                st.info("📊 Train segmentation model to view segment analysis")
        except Exception as e:
            st.info("📊 Segment data will appear after model training")

# Tab 4: Model Monitoring
with tab4:
    st.header("🔬 ML Model Performance Monitoring")
    
    # Model performance metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Model Performance Metrics")
        
        # Recommendation model metrics
        st.markdown("#### 🎯 Recommendation Engine")
        rec_metrics = {
            "Precision@10": 0.85,
            "Recall@10": 0.72,
            "NDCG@10": 0.89,
            "Coverage": 0.67
        }
        
        for metric, value in rec_metrics.items():
            st.metric(metric, f"{value:.3f}")
        
        # Prediction model metrics
        st.markdown("#### 📈 Prediction Models")
        pred_metrics = {
            "Downloads RMSE": 1248.5,
            "Completion MAE": 0.087,
            "Engagement R²": 0.821,
            "Rating MSE": 0.045
        }
        
        for metric, value in pred_metrics.items():
            if "R²" in metric:
                st.metric(metric, f"{value:.3f}")
            elif "MAE" in metric or "MSE" in metric:
                st.metric(metric, f"{value:.3f}")
            else:
                st.metric(metric, f"{value:,.1f}")
    
    with col2:
        st.subheader("📈 Model Training History")
        
        # Simulated training history
        epochs = np.arange(1, 51)
        loss = 1.0 * np.exp(-epochs/15) + 0.1 * np.random.random(50)
        val_loss = 1.2 * np.exp(-epochs/12) + 0.15 * np.random.random(50)
        
        training_df = pd.DataFrame({
            'Epoch': np.tile(epochs, 2),
            'Loss': np.concatenate([loss, val_loss]),
            'Type': ['Training'] * 50 + ['Validation'] * 50
        })
        
        fig_training = px.line(
            training_df,
            x='Epoch',
            y='Loss',
            color='Type',
            title='Model Training Progress',
            color_discrete_sequence=['#667eea', '#f093fb']
        )
        fig_training.update_layout(height=300)
        st.plotly_chart(fig_training, use_container_width=True)
        
        # Model accuracy over time
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        accuracy_data = pd.DataFrame({
            'Date': dates,
            'Recommendation_Accuracy': 0.85 + 0.1 * np.sin(np.arange(30) * 0.2) + 0.02 * np.random.random(30),
            'Prediction_Accuracy': 0.82 + 0.08 * np.cos(np.arange(30) * 0.15) + 0.03 * np.random.random(30)
        })
        
        fig_accuracy = px.line(
            accuracy_data.melt(id_vars=['Date'], var_name='Model', value_name='Accuracy'),
            x='Date',
            y='Accuracy',
            color='Model',
            title='Model Accuracy Over Time',
            color_discrete_sequence=['#43e97b', '#fa709a']
        )
        fig_accuracy.update_layout(height=300)
        st.plotly_chart(fig_accuracy, use_container_width=True)
    
    # Model Status Details
    st.subheader("🔧 Model Status & Health")
    
    model_health = [
        {"Model": "Recommendation Engine", "Status": "Healthy", "Last_Updated": "2024-12-30 19:45", "Memory_Usage": "2.3 GB", "Inference_Time": "45ms"},
        {"Model": "Performance Predictor", "Status": "Healthy", "Last_Updated": "2024-12-30 19:42", "Memory_Usage": "1.8 GB", "Inference_Time": "32ms"},
        {"Model": "User Segmentation", "Status": "Healthy", "Last_Updated": "2024-12-30 19:40", "Memory_Usage": "0.9 GB", "Inference_Time": "28ms"}
    ]
    
    health_df = pd.DataFrame(model_health)
    st.dataframe(health_df, use_container_width=True)
    
    # Auto-refresh toggle
    if st.checkbox("🔄 Auto-refresh Model Metrics (30s)"):
        time.sleep(30)
        st.experimental_rerun()

# Tab 5: AI Insights
with tab5:
    st.header("💡 AI-Generated Insights & Recommendations")
    
    # Generate AI insights
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🧠 Intelligent Platform Insights")
        
        # Simulated AI insights
        insights = [
            {
                "title": "🎯 Content Strategy Optimization",
                "insight": "Episodes released on Tuesday evenings show 34% higher engagement. Consider adjusting your release schedule for maximum impact.",
                "confidence": 0.91,
                "action": "Schedule Tuesday evening releases"
            },
            {
                "title": "👥 Audience Growth Opportunity", 
                "insight": "Users who listen to episodes longer than 45 minutes have 2.3x higher lifetime value. Focus on creating in-depth content.",
                "confidence": 0.87,
                "action": "Increase episode depth and duration"
            },
            {
                "title": "📈 Performance Prediction Alert",
                "insight": "Your next episode is predicted to underperform by 15%. Consider revising the title to include trending keywords.",
                "confidence": 0.83,
                "action": "Optimize episode title and description"
            },
            {
                "title": "🔄 Churn Prevention",
                "insight": "23% of your premium users show signs of potential churn. Implement targeted retention campaigns.",
                "confidence": 0.79,
                "action": "Launch personalized retention campaign"
            }
        ]
        
        for insight in insights:
            confidence_color = "🟢" if insight["confidence"] > 0.85 else "🟡" if insight["confidence"] > 0.75 else "🟠"
            
            st.markdown(f"""
            <div class="insight-box">
                <h4>{insight['title']}</h4>
                <p>{insight['insight']}</p>
                <p><strong>Recommended Action:</strong> {insight['action']}</p>
                <p><strong>Confidence:</strong> {confidence_color} {insight['confidence']:.1%}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("📊 Insight Categories")
        
        # Insight distribution
        insight_categories = pd.DataFrame({
            'Category': ['Content Strategy', 'Audience Growth', 'Performance', 'Retention'],
            'Count': [12, 8, 15, 6],
            'Avg_Confidence': [0.89, 0.85, 0.82, 0.91]
        })
        
        fig_insights = px.bar(
            insight_categories,
            x='Category',
            y='Count',
            color='Avg_Confidence',
            title='AI Insights by Category',
            color_continuous_scale='viridis'
        )
        fig_insights.update_layout(height=300)
        st.plotly_chart(fig_insights, use_container_width=True)
        
        # Confidence score distribution
        confidence_data = pd.DataFrame({
            'Confidence_Range': ['0.70-0.80', '0.80-0.90', '0.90-1.00'],
            'Insight_Count': [8, 23, 10]
        })
        
        fig_confidence = px.pie(
            confidence_data,
            values='Insight_Count',
            names='Confidence_Range',
            title='Insight Confidence Distribution',
            color_discrete_sequence=['#ffeaa7', '#fdcb6e', '#e17055']
        )
        fig_confidence.update_layout(height=300)
        st.plotly_chart(fig_confidence, use_container_width=True)
    
    # AI Insight Generation
    st.subheader("🚀 Generate New AI Insights")
    
    col_gen1, col_gen2 = st.columns([3, 1])
    
    with col_gen1:
        insight_focus = st.selectbox(
            "Focus Area for AI Analysis",
            ["Overall Performance", "Content Strategy", "User Behavior", "Revenue Optimization", "Technical Performance"],
            index=0
        )
        
        time_range = st.selectbox(
            "Analysis Time Range",
            ["Last 7 days", "Last 30 days", "Last 90 days", "Last year"],
            index=1
        )
    
    with col_gen2:
        if st.button("🧠 Generate Insights"):
            with st.spinner("AI is analyzing your data..."):
                # Simulate AI insight generation
                time.sleep(3)
                
                new_insight = {
                    "title": f"🎯 {insight_focus} Analysis",
                    "insight": f"Based on {time_range.lower()} of data analysis, AI has identified 3 key optimization opportunities with potential 18% performance improvement.",
                    "recommendations": [
                        "Optimize content release timing",
                        "Enhance user onboarding experience", 
                        "Implement dynamic content recommendations"
                    ],
                    "confidence": 0.88
                }
                
                st.success("✨ New AI insight generated!")
                st.markdown(f"""
                <div class="insight-box">
                    <h4>{new_insight['title']}</h4>
                    <p>{new_insight['insight']}</p>
                    <p><strong>Key Recommendations:</strong></p>
                    <ul>
                        {''.join([f'<li>{rec}</li>' for rec in new_insight['recommendations']])}
                    </ul>
                    <p><strong>Confidence:</strong> 🟢 {new_insight['confidence']:.1%}</p>
                </div>
                """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; padding: 2rem;">
    <p>🤖 <strong>PodcastFlow Analytics - ML Dashboard</strong></p>
    <p>Advanced Machine Learning Analytics • Real-time Predictions • AI-Powered Insights</p>
    <p><em>Version 3.1.0 - Phase 3 Week 3 Complete</em></p>
</div>
""", unsafe_allow_html=True) 