# 🎧 PodcastFlow Analytics - Local Emulator with Terraform

This directory contains the Terraform configuration for setting up a complete local development environment using the BigQuery emulator and supporting services.

## 🚀 Quick Start

### Prerequisites
- **Docker**: Ensure Docker Desktop is running
- **Terraform**: Version 1.0 or higher
- **Python 3.8+**: For data loading scripts

### One-Command Setup
```bash
# From the podcastflow-analytics directory
./setup_emulator_terraform.sh
```

### Manual Setup
```bash
cd terraform-emulator

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -var-file=terraform.tfvars

# Deploy the environment
terraform apply -var-file=terraform.tfvars
```

## 📦 What Gets Deployed

### Core Services
- **BigQuery Emulator**: Full BigQuery-compatible API for local development
- **Data Initialization**: Automatically loads sample podcast analytics data
- **dbt Runner**: Executes dbt transformations against the emulator
- **Jupyter Notebooks**: Interactive data exploration environment
- **Streamlit Dashboard**: Real-time analytics dashboard

### Infrastructure
- **Docker Network**: Isolated network for all services
- **Volume Mounts**: Live code updates without rebuilds
- **Health Checks**: Automatic service monitoring
- **Port Management**: Configurable port assignments

## 🌐 Service URLs

After deployment, access these services:

| Service | URL | Description |
|---------|-----|-------------|
| BigQuery Emulator API | http://localhost:9050 | Direct BigQuery API access |
| BigQuery Emulator REST | http://localhost:9060 | REST API for queries |
| Jupyter Notebooks | http://localhost:8888?token=podcastflow | Interactive development |
| Streamlit Dashboard | http://localhost:8501 | Analytics dashboard |

## 🛠️ Management Commands

### Status and Monitoring
```bash
# Check status of all services
./status.sh

# View logs for a specific service
./logs.sh bigquery-emulator
./logs.sh streamlit-dashboard
./logs.sh jupyter-podcastflow

# Check Docker containers
docker ps --filter "label=project=podcastflow-analytics"
```

### Service Management
```bash
# Stop all services
terraform destroy

# Restart a specific service
docker restart bigquery-emulator

# Rebuild and restart
terraform apply -replace="docker_container.bigquery_emulator"
```

## 🗄️ Sample Data

The environment automatically loads sample data including:

- **RSS Feeds**: 4 podcast feeds (bronze.rss_feeds)
- **Listening Events**: 500 user interaction events (bronze.listening_events)  
- **Social Mentions**: 50 social media mentions (bronze.social_mentions)

### Query Examples
```sql
-- Top podcasts by episode count
SELECT podcast_title, episode_count 
FROM `podcastflow-analytics.bronze.rss_feeds` 
ORDER BY episode_count DESC;

-- Listening behavior by platform
SELECT platform, COUNT(*) as events, 
       AVG(completion_percentage) as avg_completion
FROM `podcastflow-analytics.bronze.listening_events` 
GROUP BY platform;

-- Sentiment analysis
SELECT podcast_id, AVG(sentiment_score) as avg_sentiment
FROM `podcastflow-analytics.bronze.social_mentions` 
GROUP BY podcast_id;
```

## ⚙️ Configuration

### Port Customization
Edit `terraform.tfvars` to change default ports:

```hcl
emulator_host_port = 9055  # if 9050 is taken
emulator_rest_port = 9065  # if 9060 is taken
jupyter_port       = 8889  # if 8888 is taken
streamlit_port     = 8502  # if 8501 is taken
```

### Local Overrides
Create `terraform.tfvars.local` for personal settings:

```hcl
# Your local port preferences
emulator_host_port = 9055
jupyter_port       = 8889

# Override project name if needed
project_name = "my-podcast-analytics"
```

## 🔧 Development Workflow

### 1. Start Environment
```bash
./setup_emulator_terraform.sh
```

### 2. Develop with Jupyter
- Open http://localhost:8888?token=podcastflow
- Explore notebooks in the `work` directory
- Experiment with BigQuery queries and pandas

### 3. Run dbt Transformations
```bash
# Connect to dbt container
docker exec -it dbt-emulator bash

# Run dbt commands
dbt run --target emulator
dbt test --target emulator
dbt docs generate --target emulator
```

### 4. View Dashboard
- Open http://localhost:8501
- Explore real-time analytics
- Modify dashboard code with live reloading

### 5. Stop Environment
```bash
terraform destroy
```

## 🎯 Development Benefits

### vs Docker Compose
- **Infrastructure as Code**: Version controlled configuration
- **Dependency Management**: Automatic service orchestration
- **Resource Management**: Proper cleanup and lifecycle management
- **State Tracking**: Know exactly what's deployed

### vs Cloud Development
- **No Costs**: Completely free local development
- **Fast Iteration**: No network latency or quotas
- **Offline Development**: Work without internet connection
- **Data Privacy**: All data stays local

## 🔍 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Check what's using a port
lsof -i :9050

# Update ports in terraform.tfvars
emulator_host_port = 9055
```

#### Service Not Starting
```bash
# Check container logs
./logs.sh bigquery-emulator

# Force recreation
terraform apply -replace="docker_container.bigquery_emulator"
```

#### Data Not Loading
```bash
# Check data initialization logs
./logs.sh data-init

# Manually reload data
docker exec data-init python /scripts/load_sample_data_emulator.py
```

#### Connection Issues
```bash
# Test BigQuery emulator connectivity
curl http://localhost:9060

# Check network connectivity
docker network inspect podcastflow-dev
```

### Reset Environment
```bash
# Complete reset
terraform destroy
docker system prune -f
terraform apply -var-file=terraform.tfvars
```

## 📊 Resource Usage

### Typical Resource Consumption
- **CPU**: ~2 cores during startup, ~0.5 cores steady state
- **Memory**: ~4GB total across all containers
- **Disk**: ~2GB for images and data
- **Network**: Internal only (no external traffic)

### Performance Optimization
- **SSD Storage**: Recommended for better I/O performance
- **Memory**: 8GB+ RAM recommended for smooth operation
- **CPU**: Multi-core processor for parallel service startup

## 🔗 Integration

### With IDEs
- **VS Code**: Use Docker extension to attach to containers
- **PyCharm**: Configure remote interpreter in containers
- **DataGrip**: Connect to BigQuery emulator as BigQuery instance

### With CI/CD
```yaml
# Example GitHub Actions integration
- name: Setup Local BigQuery
  run: |
    cd terraform-emulator
    terraform init
    terraform apply -auto-approve
    
- name: Run Tests
  run: |
    docker exec dbt-emulator dbt test --target emulator
```

## 📚 Next Steps

1. **Explore Jupyter**: Start with the sample notebooks
2. **Customize Data**: Modify the data loading scripts
3. **Extend dbt**: Add your own transformation models
4. **Enhance Dashboard**: Build custom visualizations
5. **Add Services**: Extend Terraform with additional tools

---

*This emulator environment provides a complete replica of the cloud BigQuery setup, enabling rapid development and testing without any cloud costs or complexity.* 