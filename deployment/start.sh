#!/bin/bash

# PodcastFlow Analytics Platform Startup Script
# This script starts the entire platform following our implementation plan

set -e

echo "🎧 Starting PodcastFlow Analytics Platform..."
echo "================================================"

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

# Check if Docker is running
check_docker() {
    print_status "Checking Docker status..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services..."
    
    # Start core services (Kafka, Spark, PostgreSQL, etc.)
    docker-compose up -d zookeeper kafka schema-registry postgres redis minio
    
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if Kafka is ready
    print_status "Checking Kafka readiness..."
    timeout=60
    while ! docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; do
        sleep 5
        timeout=$((timeout - 5))
        if [ $timeout -le 0 ]; then
            print_error "Kafka failed to start within timeout"
            exit 1
        fi
    done
    print_success "Kafka is ready"
    
    # Check if PostgreSQL is ready
    print_status "Checking PostgreSQL readiness..."
    timeout=60
    while ! docker exec postgres pg_isready -U podcastflow > /dev/null 2>&1; do
        sleep 5
        timeout=$((timeout - 5))
        if [ $timeout -le 0 ]; then
            print_error "PostgreSQL failed to start within timeout"
            exit 1
        fi
    done
    print_success "PostgreSQL is ready"
    
    print_success "Infrastructure services started successfully"
}

# Create Kafka topics
create_kafka_topics() {
    print_status "Creating Kafka topics..."
    
    # Create listening events topic
    docker exec kafka kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic listening_events \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists
    
    # Create social mentions topic
    docker exec kafka kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic social_mentions \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists
    
    # Create podcast metadata topic
    docker exec kafka kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic podcast_metadata \
        --partitions 2 \
        --replication-factor 1 \
        --if-not-exists
    
    print_success "Kafka topics created"
}

# Start Spark services
start_spark() {
    print_status "Starting Spark cluster..."
    
    docker-compose up -d spark-master spark-worker
    
    print_status "Waiting for Spark to be ready..."
    sleep 20
    
    # Check if Spark master is ready
    timeout=60
    while ! curl -s http://localhost:8080 > /dev/null; do
        sleep 5
        timeout=$((timeout - 5))
        if [ $timeout -le 0 ]; then
            print_error "Spark master failed to start within timeout"
            exit 1
        fi
    done
    
    print_success "Spark cluster is ready"
}

# Initialize MinIO buckets
setup_minio() {
    print_status "Setting up MinIO buckets..."
    
    # Start MinIO if not already running
    docker-compose up -d minio
    
    # Wait for MinIO to be ready
    sleep 10
    
    # Create bucket for Delta Lake
    docker exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123
    docker exec minio mc mb local/podcastflow --ignore-existing
    
    print_success "MinIO buckets configured"
}

# Setup dbt
setup_dbt() {
    print_status "Setting up dbt..."
    
    cd dbt_podcast_analytics
    
    # Install dbt dependencies if not already installed
    if [ ! -d "dbt_packages" ]; then
        print_status "Installing dbt packages..."
        dbt deps
    fi
    
    # Test dbt connection
    print_status "Testing dbt connection..."
    if dbt debug --target prod; then
        print_success "dbt connection successful"
    else
        print_warning "dbt connection failed - will retry later"
    fi
    
    cd ..
}

# Start streaming jobs
start_streaming() {
    print_status "Starting streaming jobs..."
    
    # Submit Spark streaming job
    docker exec spark-master spark-submit \
        --master spark://spark-master:7077 \
        --packages io.delta:delta-core_2.12:2.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
        --conf "spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension" \
        --conf "spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog" \
        /opt/spark-apps/listening_events_processor.py &
    
    print_success "Streaming jobs submitted"
}

# Start additional services
start_additional_services() {
    print_status "Starting additional services..."
    
    # Start Kafka Connect
    docker-compose up -d kafka-connect
    
    # Start Jupyter for development
    docker-compose up -d jupyter
    
    print_success "Additional services started"
}

# Start dashboard
start_dashboard() {
    print_status "Starting dashboard..."
    
    cd dashboard
    
    # Install Python dependencies if needed
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Start Streamlit dashboard in background
    print_status "Launching Streamlit dashboard..."
    streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
    
    cd ..
    
    print_success "Dashboard started on http://localhost:8501"
}

# Display service URLs
show_service_urls() {
    echo ""
    echo "🌟 PodcastFlow Analytics Platform is now running!"
    echo "================================================"
    echo ""
    echo "📊 Dashboard:           http://localhost:8501"
    echo "⚡ Spark Master UI:     http://localhost:8080"
    echo "📨 Kafka UI:            http://localhost:9021 (if available)"
    echo "🗄️  MinIO Console:       http://localhost:9001"
    echo "📓 Jupyter Notebook:    http://localhost:8888 (token: podcastflow)"
    echo "🔗 Schema Registry:     http://localhost:8081"
    echo ""
    echo "Database Connection:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: podcastflow"
    echo "  User: podcastflow"
    echo "  Password: podcastflow123"
    echo ""
    echo "To stop all services: docker-compose down"
    echo "To view logs: docker-compose logs -f [service-name]"
    echo ""
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Check key services
    services=("postgres:5432" "kafka:9092" "spark-master:8080" "minio:9000")
    
    for service in "${services[@]}"; do
        IFS=':' read -r host port <<< "$service"
        if nc -z localhost "$port" 2>/dev/null; then
            print_success "$host is healthy"
        else
            print_warning "$host may not be fully ready"
        fi
    done
}

# Main execution
main() {
    echo "Starting PodcastFlow Analytics Platform..."
    echo "This will start all services including Kafka, Spark, PostgreSQL, and the dashboard."
    echo ""
    
    # Perform checks
    check_docker
    check_docker_compose
    
    # Start services in order
    start_infrastructure
    create_kafka_topics
    setup_minio
    start_spark
    start_additional_services
    
    # Setup application components
    setup_dbt
    start_streaming
    start_dashboard
    
    # Final checks and display
    health_check
    show_service_urls
    
    print_success "PodcastFlow Analytics Platform startup complete!"
    
    # Keep script running to show logs
    echo "Press Ctrl+C to stop monitoring logs..."
    docker-compose logs -f
}

# Handle script interruption
trap 'echo ""; print_warning "Shutting down..."; docker-compose down; exit 0' INT

# Run main function
main "$@" 