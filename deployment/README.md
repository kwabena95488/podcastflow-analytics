# Deployment Scripts

This directory contains all deployment and infrastructure setup scripts for the PodcastFlow Analytics platform.

## 📁 Deployment Scripts

### 🚀 **`start.sh`** - Main Platform Startup
**Purpose**: Complete platform initialization and startup

**Usage**:
```bash
./deployment/start.sh
```

**What it does**:
- Starts all infrastructure services (Kafka, Spark, PostgreSQL, MinIO, Redis)
- Creates Kafka topics for real-time streaming
- Initializes database schemas
- Launches streaming jobs
- Starts the analytics dashboard
- Performs health checks on all services

**Services Started**:
- 📊 Dashboard: http://localhost:8501
- ⚡ Spark UI: http://localhost:8080
- 🗄️ MinIO Console: http://localhost:9001
- 📓 Jupyter: http://localhost:8888 (token: podcastflow)

### ☁️ **`setup_bigquery.sh`** - Google BigQuery Integration
**Purpose**: Configure platform for Google BigQuery backend

**Usage**:
```bash
./deployment/setup_bigquery.sh
```

**What it does**:
- Configures BigQuery emulator for local development
- Sets up BigQuery datasets and tables
- Initializes dbt profiles for BigQuery
- Creates service account configurations
- Validates BigQuery connectivity

**Prerequisites**:
- Google Cloud Project with BigQuery API enabled
- Service account with BigQuery permissions
- `gcloud` CLI installed and authenticated

### 🏗️ **`setup_emulator_terraform.sh`** - Infrastructure as Code
**Purpose**: Deploy infrastructure using Terraform

**Usage**:
```bash
./deployment/setup_emulator_terraform.sh
```

**What it does**:
- Initializes Terraform configuration
- Deploys BigQuery emulator infrastructure
- Sets up networking and security groups
- Configures monitoring and logging
- Validates infrastructure deployment

**Prerequisites**:
- Terraform installed (version 1.0+)
- Appropriate cloud provider credentials
- Network access for infrastructure deployment

### ☁️ **`deploy-cloud-run.sh`** - Cloud Deployment
**Purpose**: Deploy platform to Google Cloud Run

**Usage**:
```bash
./deployment/deploy-cloud-run.sh
```

**What it does**:
- Builds Docker containers for cloud deployment
- Pushes images to Google Container Registry
- Deploys services to Cloud Run
- Configures environment variables and secrets
- Sets up load balancing and auto-scaling
- Validates cloud deployment

**Prerequisites**:
- Google Cloud Project with Cloud Run API enabled
- Docker installed and configured
- Cloud Run deployment permissions

## 🔧 Configuration Requirements

### Environment Variables

**Required for all deployments**:
```bash
# Database Configuration
POSTGRES_PASSWORD=your_secure_password
POSTGRES_USER=podcastflow
POSTGRES_DB=podcastflow

# BigQuery Configuration (for BigQuery integration)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Application Configuration
ENVIRONMENT=development|staging|production
DEBUG=true|false
```

**Cloud-specific variables**:
```bash
# Google Cloud Run
CLOUD_RUN_REGION=us-central1
CLOUD_RUN_SERVICE_NAME=podcastflow-analytics

# Terraform
TF_VAR_project_id=your-project-id
TF_VAR_region=us-central1
```

### Prerequisites Check

Before running deployment scripts, ensure:

1. **Docker & Docker Compose** installed
2. **Python 3.8+** available
3. **Required cloud CLI tools** installed (`gcloud`, `terraform`)
4. **Network connectivity** to external services
5. **Sufficient system resources** (8GB RAM recommended)

## 🚀 Deployment Workflows

### Local Development Deployment

```bash
# 1. Standard local deployment
./deployment/start.sh

# 2. With BigQuery integration
./deployment/setup_bigquery.sh
./deployment/start.sh
```

### Cloud Staging Deployment

```bash
# 1. Set up infrastructure
./deployment/setup_emulator_terraform.sh

# 2. Configure BigQuery
./deployment/setup_bigquery.sh

# 3. Deploy to cloud
./deployment/deploy-cloud-run.sh
```

### Production Deployment

```bash
# 1. Infrastructure deployment
export ENVIRONMENT=production
./deployment/setup_emulator_terraform.sh

# 2. Production BigQuery setup
./deployment/setup_bigquery.sh

# 3. Production cloud deployment
./deployment/deploy-cloud-run.sh

# 4. Health validation
curl https://your-cloud-run-url/health
```

## 📊 Deployment Validation

### Health Checks

After deployment, validate these endpoints:

**Local Deployment**:
- Dashboard: http://localhost:8501
- Spark UI: http://localhost:8080
- API Health: http://localhost:8000/health
- Database: Connection test via scripts

**Cloud Deployment**:
- Cloud Run Service: https://your-service-url/health
- BigQuery: Data query validation
- Monitoring: Cloud Monitoring dashboards

### Service Validation

**Database Services**:
```bash
# PostgreSQL connectivity
docker exec postgres pg_isready -U podcastflow

# BigQuery connectivity
bq query "SELECT 1"
```

**Application Services**:
```bash
# Dashboard availability
curl -f http://localhost:8501

# Spark cluster health
curl -f http://localhost:8080
```

**Data Pipeline**:
```bash
# Test data ingestion
python scripts/testing/final_verification.py

# Validate dbt models
dbt test --profile bigquery
```

## 🔒 Security Considerations

### Credential Management

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive configuration
3. **Rotate service account keys** regularly
4. **Apply least privilege** principles

### Network Security

1. **Configure firewalls** appropriately for cloud deployment
2. **Use HTTPS** for all external communication
3. **Implement proper authentication** for dashboard access
4. **Monitor access logs** for suspicious activity

### Production Hardening

1. **Remove debug flags** in production
2. **Configure resource limits** for containers
3. **Set up monitoring and alerting**
4. **Implement backup and recovery procedures**

## 🔧 Troubleshooting

### Common Deployment Issues

**Docker Issues**:
```bash
# Check Docker daemon
docker info

# Clean up resources
docker system prune -a

# Restart Docker service
sudo systemctl restart docker
```

**Network Issues**:
```bash
# Check port availability
netstat -tulpn | grep :8501

# Test external connectivity
curl -I https://api.github.com
```

**Cloud Deployment Issues**:
```bash
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision"

# Validate service configuration
gcloud run services describe your-service-name
```

### Script-Specific Help

Each deployment script includes:
- `--help` for usage information
- `--dry-run` for validation without execution
- Detailed error messages with resolution steps

**Example**:
```bash
./deployment/start.sh --help
./deployment/deploy-cloud-run.sh --dry-run
```

## 📈 Performance Considerations

### Resource Requirements

**Local Development**:
- CPU: 4+ cores recommended
- RAM: 8GB minimum, 16GB recommended
- Storage: 10GB available space
- Network: Broadband internet connection

**Cloud Production**:
- Cloud Run: 2-4 vCPUs, 4-8GB RAM per service
- BigQuery: Standard pricing tier
- Storage: 100GB+ for data lake
- Network: High-throughput for real-time processing

### Scaling Configuration

**Horizontal Scaling**:
- Cloud Run auto-scaling based on request volume
- Kafka partitioning for parallel processing
- dbt model parallelization

**Vertical Scaling**:
- Container resource limits based on workload
- Database connection pooling
- Memory optimization for large datasets

---

**Deployment Scripts Last Updated**: September 2025
**Supported Environments**: Local, Google Cloud, Docker
**Next Review**: After Phase 3 cloud deployment