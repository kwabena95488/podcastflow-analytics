#!/bin/bash

# PodcastFlow Analytics - Cloud Run Deployment Script
# Phase 3: Cloud Migration & Enterprise Features

set -e  # Exit on any error

# Configuration
PROJECT_ID="your-gcp-project"
SERVICE_NAME="podcastflow-analytics"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed. Please install Google Cloud SDK."
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker."
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        error "Not authenticated with gcloud. Run 'gcloud auth login'"
    fi
    
    # Set project
    log "Setting project to ${PROJECT_ID}..."
    gcloud config set project $PROJECT_ID
    
    success "Prerequisites check completed"
}

# Enable required APIs
enable_apis() {
    log "Enabling required Google Cloud APIs..."
    
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        bigquery.googleapis.com \
        storage.googleapis.com \
        pubsub.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com
    
    success "APIs enabled successfully"
}

# Build and push Docker image
build_and_push() {
    log "Building Docker image..."
    
    # Build the image
    docker build -f Dockerfile.cloud -t $IMAGE_NAME .
    
    log "Pushing image to Google Container Registry..."
    docker push $IMAGE_NAME
    
    success "Image built and pushed successfully"
}

# Deploy to Cloud Run
deploy_service() {
    log "Deploying to Cloud Run..."
    
    gcloud run deploy $SERVICE_NAME \
        --image=$IMAGE_NAME \
        --region=$REGION \
        --platform=managed \
        --port=$PORT \
        --memory=2Gi \
        --cpu=2 \
        --min-instances=0 \
        --max-instances=10 \
        --concurrency=100 \
        --timeout=300 \
        --allow-unauthenticated \
        --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
        --set-env-vars="ENVIRONMENT=production" \
        --service-account="podcastflow-dbt-dev@${PROJECT_ID}.iam.gserviceaccount.com"
    
    success "Service deployed successfully"
}

# Configure custom domain (optional)
configure_domain() {
    local domain=$1
    if [ -n "$domain" ]; then
        log "Configuring custom domain: $domain"
        
        # Map domain to service
        gcloud run domain-mappings create \
            --service=$SERVICE_NAME \
            --domain=$domain \
            --region=$REGION
        
        success "Domain mapping created for $domain"
    fi
}

# Set up monitoring and alerting
setup_monitoring() {
    log "Setting up monitoring and alerting..."
    
    # Create notification channels (email)
    # This would typically be done through the Console or with specific email
    warning "Manual step required: Set up notification channels in Cloud Monitoring"
    
    # Create basic alerting policies
    cat > alerting-policy.json << EOF
{
  "displayName": "PodcastFlow High Error Rate",
  "conditions": [
    {
      "displayName": "Error rate above 5%",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 0.05,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE",
            "crossSeriesReducer": "REDUCE_MEAN"
          }
        ]
      }
    }
  ],
  "enabled": true
}
EOF
    
    # Create the alerting policy
    gcloud alpha monitoring policies create --policy-from-file=alerting-policy.json
    
    # Clean up
    rm alerting-policy.json
    
    success "Basic monitoring setup completed"
}

# Get service URL
get_service_url() {
    local url=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    success "Service deployed at: $url"
    echo ""
    echo "🎉 PodcastFlow Analytics is now running on Google Cloud Run!"
    echo "🔗 Dashboard URL: $url"
    echo "📊 Monitor the service in the Google Cloud Console"
    echo "📱 The service will auto-scale based on traffic"
}

# Main deployment function
main() {
    log "Starting PodcastFlow Analytics Cloud Deployment..."
    echo ""
    
    check_prerequisites
    enable_apis
    build_and_push
    deploy_service
    setup_monitoring
    get_service_url
    
    echo ""
    success "Deployment completed successfully! 🚀"
    
    # Optional: Configure custom domain
    if [ "$1" = "--domain" ] && [ -n "$2" ]; then
        configure_domain $2
    fi
}

# Help function
show_help() {
    echo "PodcastFlow Analytics - Cloud Run Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --domain DOMAIN    Configure custom domain mapping"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Deploy with default settings"
    echo "  $0 --domain analytics.example.com  # Deploy with custom domain"
}

# Handle command line arguments
case "${1:-}" in
    --help)
        show_help
        exit 0
        ;;
    --domain)
        if [ -z "$2" ]; then
            error "Domain name required when using --domain option"
        fi
        main "$@"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1. Use --help for usage information."
        ;;
esac 