#!/bin/bash

# 🎧 PodcastFlow Analytics - BigQuery Setup Script
# This script sets up the platform for BigQuery deployment with multiple options

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup function
main() {
    echo "🎧 PodcastFlow Analytics - BigQuery Setup"
    echo "========================================"
    echo ""
    
    # Check deployment mode
    echo "Select deployment mode:"
    echo "1) Local development with BigQuery emulator"
    echo "2) Cloud deployment with Terraform + BigQuery"
    echo "3) Hybrid (emulator for dev, cloud for prod)"
    echo ""
    read -p "Enter your choice (1-3): " choice
    
    case $choice in
        1)
            setup_emulator_mode
            ;;
        2)
            setup_cloud_mode
            ;;
        3)
            setup_hybrid_mode
            ;;
        *)
            print_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac
}

# Setup emulator mode for local development
setup_emulator_mode() {
    print_status "Setting up local BigQuery emulator environment..."
    
    # Check prerequisites
    check_docker_prerequisites
    
    # Create necessary directories
    print_status "Creating required directories..."
    mkdir -p bigquery_init
    mkdir -p data
    mkdir -p notebooks
    mkdir -p bigquery_jars
    
    # Download BigQuery Spark connector
    print_status "Downloading BigQuery Spark connector..."
    if [ ! -f "bigquery_jars/spark-bigquery-latest_2.12.jar" ]; then
        curl -L -o bigquery_jars/spark-bigquery-latest_2.12.jar \
            "https://storage.googleapis.com/spark-lib/bigquery/spark-bigquery-latest_2.12.jar"
    fi
    
    # Start services with BigQuery emulator
    print_status "Starting BigQuery emulator and services..."
    docker-compose -f docker-compose.bigquery.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check service health
    check_emulator_health
    
    # Initialize dbt
    setup_dbt_emulator
    
    print_success "BigQuery emulator setup complete!"
    print_status "Services available at:"
    echo "  - BigQuery Emulator: http://localhost:9050"
    echo "  - BigQuery REST API: http://localhost:9060" 
    echo "  - Dashboard: http://localhost:8501"
    echo "  - Spark UI: http://localhost:8080"
    echo "  - Jupyter: http://localhost:8888 (token: podcastflow)"
}

# Setup cloud mode with Terraform
setup_cloud_mode() {
    print_status "Setting up cloud BigQuery deployment..."
    
    # Check prerequisites
    check_cloud_prerequisites
    
    # Get project configuration
    read -p "Enter your GCP Project ID: " PROJECT_ID
    read -p "Enter environment (dev/staging/prod): " ENVIRONMENT
    
    if [ -z "$PROJECT_ID" ]; then
        print_error "Project ID is required"
        exit 1
    fi
    
    # Create terraform variables file
    print_status "Creating Terraform configuration..."
    cat > terraform/terraform.tfvars <<EOF
project_id = "$PROJECT_ID"
environment = "$ENVIRONMENT"
region = "us-central1"
EOF
    
    # Initialize and apply Terraform
    print_status "Initializing Terraform..."
    cd terraform
    terraform init
    
    print_status "Planning Terraform deployment..."
    terraform plan -var-file=terraform.tfvars
    
    echo ""
    read -p "Do you want to apply this Terraform plan? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        print_status "Applying Terraform configuration..."
        terraform apply -var-file=terraform.tfvars -auto-approve
        
        # Extract service account keys
        print_status "Extracting service account keys..."
        terraform output -raw dbt_key_file | base64 -d > ../dbt_service_account.json
        
        # Set environment variables
        export GOOGLE_APPLICATION_CREDENTIALS="../dbt_service_account.json"
        export GCP_PROJECT_ID="$PROJECT_ID"
        
        cd ..
        
        # Setup dbt for cloud
        setup_dbt_cloud
        
        print_success "Cloud BigQuery setup complete!"
        print_status "Remember to set these environment variables:"
        echo "  export GOOGLE_APPLICATION_CREDENTIALS=\"$(pwd)/dbt_service_account.json\""
        echo "  export GCP_PROJECT_ID=\"$PROJECT_ID\""
    else
        print_warning "Terraform deployment cancelled"
        cd ..
    fi
}

# Setup hybrid mode
setup_hybrid_mode() {
    print_status "Setting up hybrid environment (emulator + cloud)..."
    
    # Setup emulator first
    setup_emulator_mode
    
    echo ""
    print_status "Now setting up cloud environment..."
    
    # Setup cloud
    setup_cloud_mode
    
    print_success "Hybrid setup complete!"
    print_status "You can switch between environments using:"
    echo "  dbt run --target emulator      # Local emulator"
    echo "  dbt run --target bigquery_dev  # Cloud development"
    echo "  dbt run --target bigquery_prod # Cloud production"
}

# Check Docker prerequisites
check_docker_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running"
        exit 1
    fi
    
    print_success "Docker prerequisites check passed"
}

# Check cloud prerequisites
check_cloud_prerequisites() {
    print_status "Checking cloud prerequisites..."
    
    if ! command_exists gcloud; then
        print_error "Google Cloud SDK is not installed"
        print_status "Install with: curl https://sdk.cloud.google.com | bash"
        exit 1
    fi
    
    if ! command_exists terraform; then
        print_error "Terraform is not installed"
        print_status "Install from: https://terraform.io/downloads"
        exit 1
    fi
    
    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 >/dev/null; then
        print_error "Not authenticated with Google Cloud"
        print_status "Run: gcloud auth login"
        exit 1
    fi
    
    print_success "Cloud prerequisites check passed"
}

# Check emulator health
check_emulator_health() {
    print_status "Checking BigQuery emulator health..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:9060/ >/dev/null 2>&1; then
            print_success "BigQuery emulator is healthy"
            return 0
        fi
        
        print_status "Waiting for emulator... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "BigQuery emulator health check failed"
    return 1
}

# Setup dbt for emulator
setup_dbt_emulator() {
    print_status "Setting up dbt for BigQuery emulator..."
    
    # Install dbt dependencies
    docker-compose -f docker-compose.bigquery.yml exec -T dbt-bigquery bash -c "
        cd /usr/app/dbt && 
        dbt deps &&
        dbt debug &&
        echo 'dbt emulator setup complete'
    "
    
    print_success "dbt emulator configuration complete"
}

# Setup dbt for cloud
setup_dbt_cloud() {
    print_status "Setting up dbt for cloud BigQuery..."
    
    # Check if dbt is installed locally
    if ! command_exists dbt; then
        print_warning "dbt not found locally, installing..."
        pip install dbt-bigquery
    fi
    
    # Navigate to dbt project
    cd dbt_podcast_analytics
    
    # Install dependencies
    print_status "Installing dbt dependencies..."
    dbt deps
    
    # Test connection
    print_status "Testing BigQuery connection..."
    dbt debug --target bigquery_dev
    
    # Run initial models
    print_status "Running initial dbt models..."
    dbt run --target bigquery_dev
    
    # Run tests
    print_status "Running dbt tests..."
    dbt test --target bigquery_dev
    
    cd ..
    
    print_success "dbt cloud configuration complete"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    
    read -p "Do you want to stop all services? (y/N): " confirm
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        docker-compose -f docker-compose.bigquery.yml down
        print_success "Services stopped"
    fi
}

# Help function
show_help() {
    echo "PodcastFlow Analytics - BigQuery Setup"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -c, --cleanup  Stop all services and cleanup"
    echo "  -e, --emulator Setup emulator mode only"
    echo "  -t, --terraform Setup cloud mode only"
    echo ""
    echo "Interactive mode (no options) will prompt for deployment choice"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -c|--cleanup)
        cleanup
        exit 0
        ;;
    -e|--emulator)
        setup_emulator_mode
        exit 0
        ;;
    -t|--terraform)
        setup_cloud_mode
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac 