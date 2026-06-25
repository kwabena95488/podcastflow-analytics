#!/bin/bash

# 🎧 PodcastFlow Analytics - BigQuery Emulator Setup with Terraform
# This script sets up the complete local development environment using Terraform

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
    echo "🎧 PodcastFlow Analytics - Emulator Setup with Terraform"
    echo "========================================================="
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! command_exists terraform; then
        print_error "Terraform is not installed. Please install Terraform first."
        echo "Visit: https://terraform.io/downloads"
        exit 1
    fi
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker ps >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Prerequisites check passed!"
    
    # Navigate to terraform-emulator directory
    cd terraform-emulator
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Plan the deployment
    print_status "Planning Terraform deployment..."
    terraform plan -var-file=terraform.tfvars
    
    # Apply the configuration
    print_status "Deploying emulator infrastructure..."
    terraform apply -var-file=terraform.tfvars -auto-approve
    
    # Wait a moment for services to start
    print_status "Waiting for services to start..."
    sleep 30
    
    # Display outputs
    print_status "Deployment complete! Here are your service URLs:"
    terraform output
    
    # Test connectivity
    print_status "Testing service connectivity..."
    
    # Test BigQuery emulator
    if curl -s http://localhost:9060 >/dev/null; then
        print_success "✅ BigQuery emulator is responding"
    else
        print_warning "⚠️  BigQuery emulator may still be starting up"
    fi
    
    # Check container status
    print_status "Container status:"
    docker ps --filter "label=project=podcastflow-analytics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    print_success "🎉 Local development environment is ready!"
    echo ""
    echo "📋 Available Services:"
    echo "  • BigQuery Emulator: http://localhost:9060"
    echo "  • Jupyter Notebooks: http://localhost:8888?token=podcastflow"
    echo "  • Streamlit Dashboard: http://localhost:8501"
    echo ""
    echo "🛠️  Useful Commands:"
    echo "  • Check logs: terraform-emulator/logs.sh <service-name>"
    echo "  • Stop environment: terraform destroy"
    echo "  • Restart service: docker restart <container-name>"
    echo ""
    echo "🗄️  Sample Queries to try:"
    echo "  SELECT * FROM \`podcastflow-analytics.bronze.rss_feeds\`"
    echo "  SELECT platform, COUNT(*) FROM \`podcastflow-analytics.bronze.listening_events\` GROUP BY platform"
}

# Cleanup function for graceful exit
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Setup failed! Check the logs above for details."
        print_status "To clean up, run: cd terraform-emulator && terraform destroy"
    fi
}

trap cleanup EXIT

# Run main function
main "$@" 