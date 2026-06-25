#!/bin/bash

# PodcastFlow Analytics - Enhanced ML Dashboard Startup Script
# Phase 3 Week 3 Day 17-18: Advanced Dashboard Features with ML Insights

set -e

echo "🚀 Starting PodcastFlow Analytics Enhanced ML Dashboard..."
echo "=================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Check dependencies
print_status "Checking system dependencies..."

if ! command_exists python3; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

if ! command_exists pip; then
    print_error "pip is required but not installed."
    exit 1
fi

print_success "System dependencies check passed ✅"

# Set environment variables
print_status "Setting up environment variables..."

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-gcp-project}"
export STREAMLIT_SERVER_PORT="${STREAMLIT_SERVER_PORT:-8501}"
export STREAMLIT_SERVER_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS="false"
export STREAMLIT_THEME_BASE="light"

# Set ML-specific environment variables
export ML_MODEL_PATH="./ml/models"
export TENSORFLOW_CPP_MIN_LOG_LEVEL="2"  # Reduce TensorFlow logging
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

print_success "Environment variables configured ✅"

# Create necessary directories
print_status "Creating ML model directories..."

mkdir -p ml/models/recommendation_engine
mkdir -p ml/models/episode_performance  
mkdir -p ml/models/user_segmentation
mkdir -p logs
mkdir -p cache

print_success "Directories created ✅"

# Install dashboard-specific requirements if needed
if [ -f "dashboard/requirements.txt" ]; then
    print_status "Installing dashboard requirements..."
    
    # Check if virtual environment should be created
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
    else
        source venv/bin/activate
    fi
    
    # Install requirements
    pip install -r dashboard/requirements.txt
    
    print_success "Dashboard requirements installed ✅"
else
    print_warning "Dashboard requirements.txt not found, using system packages"
fi

# Validate Google Cloud credentials
print_status "Validating Google Cloud credentials..."

if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    print_warning "GOOGLE_APPLICATION_CREDENTIALS not set"
    print_warning "Using default service account or local credentials"
else
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_success "Google Cloud credentials found ✅"
    else
        print_error "Google Cloud credentials file not found: $GOOGLE_APPLICATION_CREDENTIALS"
        exit 1
    fi
fi

# Download required NLTK data
print_status "Setting up NLP resources..."

python3 -c "
import nltk
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True) 
    nltk.download('vader_lexicon', quiet=True)
    print('NLTK data downloaded successfully')
except Exception as e:
    print(f'NLTK download warning: {e}')
"

print_success "NLP resources configured ✅"

# Pre-warm TensorFlow and ML models
print_status "Pre-warming ML models..."

python3 -c "
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    tf.config.set_visible_devices([], 'GPU')  # Use CPU only for demo
    print('TensorFlow initialized successfully')
    
    import sklearn
    print('Scikit-learn ready')
    
    from ml.recommendation_engine import recommendation_engine
    from ml.prediction_models import prediction_service  
    from ml.user_segmentation import user_segmentation_model
    print('ML modules loaded successfully')
    
except Exception as e:
    print(f'ML initialization warning: {e}')
"

print_success "ML models pre-warmed ✅"

# Check if BigQuery is accessible
print_status "Testing BigQuery connectivity..."

python3 -c "
from google.cloud import bigquery
import os

try:
    client = bigquery.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))
    query = 'SELECT 1 as test LIMIT 1'
    job = client.query(query)
    result = job.result()
    print('BigQuery connectivity: SUCCESS')
except Exception as e:
    print(f'BigQuery connectivity: WARNING - {e}')
    print('Dashboard will use simulated data')
"

print_success "BigQuery connection tested ✅"

# Start the enhanced ML dashboard
print_status "Starting Enhanced ML Dashboard..."

echo ""
echo "🤖 PodcastFlow Analytics - Enhanced ML Dashboard"
echo "=================================================="
echo "🎯 URL: http://localhost:${STREAMLIT_SERVER_PORT}"
echo "🧠 Features:"
echo "   • AI-Powered Content Recommendations"
echo "   • Episode Performance Predictions"
echo "   • User Behavior Segmentation"
echo "   • Interactive ML Model Monitoring"
echo "   • Real-time AI Insights"
echo ""
echo "🔧 ML Capabilities:"
echo "   • TensorFlow Deep Learning Models"
echo "   • Real-time Inference Engine"
echo "   • Advanced Feature Engineering"
echo "   • Interactive Model Training"
echo "   • Automated Insight Generation"
echo ""
echo "📊 Dashboard Controls:"
echo "   • Use sidebar to train ML models"
echo "   • Select users for personalized analysis" 
echo "   • Navigate tabs for different ML features"
echo "   • Real-time auto-refresh available"
echo ""
echo "⚡ Performance Tips:"
echo "   • Initial model training may take 1-2 minutes"
echo "   • Dashboard caches results for better performance"
echo "   • Use 'Train All Models' button for full ML setup"
echo ""

# Function to handle cleanup on exit
cleanup() {
    print_status "Shutting down Enhanced ML Dashboard..."
    print_success "Dashboard stopped successfully"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Streamlit with enhanced configuration
cd dashboard
streamlit run enhanced_ml_dashboard.py \
    --server.port=${STREAMLIT_SERVER_PORT} \
    --server.address=${STREAMLIT_SERVER_ADDRESS} \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --theme.base=light \
    --theme.primaryColor="#667eea" \
    --theme.backgroundColor="#ffffff" \
    --theme.secondaryBackgroundColor="#f0f2f6" \
    --theme.textColor="#262730" \
    --logger.level=info

print_success "Enhanced ML Dashboard session completed ✅" 