# PRODUCTION DEPLOYMENT GUIDE
**PodcastFlow Analytics Enterprise Platform**  
**Version**: 3.0.0  
**Last Updated**: 2024-12-30  
**Environment**: Production

---

## 📋 DEPLOYMENT OVERVIEW

### Platform Architecture
The PodcastFlow Analytics Platform is designed as a cloud-native, enterprise-ready solution with the following key components:

```
Production Architecture:
├── Google Cloud Platform (Core Infrastructure)
├── Multi-tenant Security Framework (OAuth 2.0 + RBAC)
├── Advanced Analytics Engine (ML-powered insights)
├── Real-time Processing Pipeline (BigQuery + Streaming)
├── Interactive Dashboard (Streamlit + Enhanced UI)
├── Enterprise API Layer (FastAPI + Security)
└── Monitoring & Observability (Cloud Monitoring)
```

### Deployment Strategy
- **Zero-downtime deployment** with rolling updates
- **Multi-environment support** (development, staging, production)
- **Auto-scaling** based on demand
- **Disaster recovery** with automated backups
- **Security-first** approach with comprehensive threat protection

---

## 🚀 PRE-DEPLOYMENT REQUIREMENTS

### Infrastructure Prerequisites
- **Google Cloud Project** with billing enabled
- **Domain name** for production access (optional but recommended)
- **SSL certificates** for HTTPS endpoints
- **Database instances** with appropriate sizing
- **Service accounts** with least-privilege access

### Required GCP Services
```bash
# Enable required Google Cloud services
gcloud services enable \
    compute.googleapis.com \
    bigquery.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    container.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    secretmanager.googleapis.com \
    iamcredentials.googleapis.com
```

### Environment Variables
Create production environment configuration:
```bash
# Core Platform Configuration
export PROJECT_ID="podcastflow-prod"
export REGION="us-central1"
export ENVIRONMENT="production"

# Database Configuration
export BIGQUERY_PROJECT_ID="${PROJECT_ID}"
export BIGQUERY_DATASET_BRONZE="podcastflow_bronze"
export BIGQUERY_DATASET_SILVER="podcastflow_silver"
export BIGQUERY_DATASET_GOLD="podcastflow_gold"

# Security Configuration
export OAUTH_CLIENT_ID="your-oauth-client-id"
export OAUTH_CLIENT_SECRET="your-oauth-client-secret"
export JWT_SECRET_KEY="your-jwt-secret-key"
export ENCRYPTION_KEY="your-encryption-key"

# ML Configuration
export ML_MODEL_BUCKET="podcastflow-ml-models"
export FEATURE_STORE_PROJECT="${PROJECT_ID}"
```

---

## 🏗️ DEPLOYMENT STEPS

### Step 1: Infrastructure Setup

#### 1.1 Create GCP Project and Configure Billing
```bash
# Create new project
gcloud projects create ${PROJECT_ID} --name="PodcastFlow Analytics Production"

# Set default project
gcloud config set project ${PROJECT_ID}

# Link billing account (replace with your billing account ID)
gcloud billing projects link ${PROJECT_ID} --billing-account=YOUR_BILLING_ACCOUNT_ID
```

#### 1.2 Enable APIs and Create Service Accounts
```bash
# Enable required APIs
gcloud services enable \
    bigquery.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com

# Create service account for the application
gcloud iam service-accounts create podcastflow-app \
    --description="PodcastFlow Application Service Account" \
    --display-name="PodcastFlow App"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:podcastflow-app@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:podcastflow-app@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### Step 2: Database Setup

#### 2.1 Create BigQuery Datasets
```bash
# Create datasets for medallion architecture
bq mk --dataset --location=US ${PROJECT_ID}:${BIGQUERY_DATASET_BRONZE}
bq mk --dataset --location=US ${PROJECT_ID}:${BIGQUERY_DATASET_SILVER}
bq mk --dataset --location=US ${PROJECT_ID}:${BIGQUERY_DATASET_GOLD}

# Create additional datasets for ML and monitoring
bq mk --dataset --location=US ${PROJECT_ID}:ml_models
bq mk --dataset --location=US ${PROJECT_ID}:monitoring
```

#### 2.2 Initialize Database Schema
```bash
# Run schema initialization scripts
cd scripts/
python initialize_production_schema.py --project-id=${PROJECT_ID}
```

### Step 3: Application Deployment

#### 3.1 Build and Deploy Dashboard
```bash
# Build container image
gcloud builds submit --tag gcr.io/${PROJECT_ID}/podcastflow-dashboard:latest .

# Deploy to Cloud Run
gcloud run deploy podcastflow-dashboard \
    --image gcr.io/${PROJECT_ID}/podcastflow-dashboard:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --set-env-vars "ENVIRONMENT=production,PROJECT_ID=${PROJECT_ID}"
```

#### 3.2 Deploy API Services
```bash
# Build and deploy secure API
gcloud builds submit --tag gcr.io/${PROJECT_ID}/podcastflow-api:latest ./api/

gcloud run deploy podcastflow-api \
    --image gcr.io/${PROJECT_ID}/podcastflow-api:latest \
    --platform managed \
    --region ${REGION} \
    --port 8000 \
    --memory 4Gi \
    --cpu 2 \
    --min-instances 2 \
    --max-instances 20 \
    --set-env-vars "ENVIRONMENT=production,PROJECT_ID=${PROJECT_ID}"
```

### Step 4: ML Model Deployment

#### 4.1 Deploy ML Models to Vertex AI
```bash
# Upload trained models to Cloud Storage
gsutil -m cp -r ml/models/ gs://${ML_MODEL_BUCKET}/models/

# Deploy recommendation engine
gcloud ai models upload \
    --region=${REGION} \
    --display-name="recommendation-engine" \
    --container-image-uri="gcr.io/${PROJECT_ID}/ml-recommendation:latest"

# Deploy prediction models
gcloud ai models upload \
    --region=${REGION} \
    --display-name="performance-predictor" \
    --container-image-uri="gcr.io/${PROJECT_ID}/ml-prediction:latest"
```

### Step 5: Security Configuration

#### 5.1 Configure OAuth 2.0
```bash
# Store OAuth credentials in Secret Manager
echo -n "${OAUTH_CLIENT_ID}" | gcloud secrets create oauth-client-id --data-file=-
echo -n "${OAUTH_CLIENT_SECRET}" | gcloud secrets create oauth-client-secret --data-file=-
echo -n "${JWT_SECRET_KEY}" | gcloud secrets create jwt-secret-key --data-file=-
```

#### 5.2 Set Up VPC and Firewall Rules
```bash
# Create VPC network
gcloud compute networks create podcastflow-vpc --subnet-mode regional

# Create subnet
gcloud compute networks subnets create podcastflow-subnet \
    --network podcastflow-vpc \
    --range 10.1.0.0/24 \
    --region ${REGION}

# Configure firewall rules
gcloud compute firewall-rules create allow-internal \
    --network podcastflow-vpc \
    --allow tcp,udp,icmp \
    --source-ranges 10.1.0.0/24
```

---

## 🔍 MONITORING & OBSERVABILITY

### Cloud Monitoring Setup
```bash
# Create monitoring workspace
gcloud alpha monitoring dashboards create \
    --config-from-file=configs/production/monitoring-dashboard.json

# Set up alerting policies
gcloud alpha monitoring policies create \
    --policy-from-file=configs/production/alerting-policies.yaml
```

### Log Management
```bash
# Configure log retention
gcloud logging sinks create podcastflow-logs \
    bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/logs \
    --log-filter='resource.type="cloud_run_revision"'
```

---

## 🚦 HEALTH CHECKS & VALIDATION

### Deployment Validation Checklist
- [ ] All Cloud Run services are healthy and responding
- [ ] BigQuery datasets are accessible and contain expected data
- [ ] ML models are deployed and serving predictions
- [ ] Authentication and authorization are working correctly
- [ ] Monitoring dashboards are displaying metrics
- [ ] Alerting policies are configured and functional
- [ ] SSL certificates are valid and HTTPS is enforced

### Health Check Endpoints
```bash
# Dashboard health check
curl https://podcastflow-dashboard-${PROJECT_ID}.a.run.app/health

# API health check
curl https://podcastflow-api-${PROJECT_ID}.a.run.app/api/v1/health

# Database connectivity check
curl https://podcastflow-api-${PROJECT_ID}.a.run.app/api/v1/db/health
```

---

## 🔧 MAINTENANCE & OPERATIONS

### Regular Maintenance Tasks
1. **Weekly**: Review monitoring dashboards and alerts
2. **Monthly**: Update dependencies and security patches
3. **Quarterly**: Performance optimization and cost analysis
4. **Annually**: Security audit and compliance review

### Backup Strategy
```bash
# Automated BigQuery backups
bq mk --transfer_config \
    --project_id=${PROJECT_ID} \
    --data_source=bigquery_dts \
    --display_name="Daily Backup" \
    --target_dataset=backups \
    --schedule="0 2 * * *"
```

### Scaling Configuration
```yaml
# Cloud Run auto-scaling configuration
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  annotations:
    run.googleapis.com/cpu-throttling: "false"
    autoscaling.knative.dev/minScale: "2"
    autoscaling.knative.dev/maxScale: "100"
    autoscaling.knative.dev/target: "70"
```

---

## 🚨 TROUBLESHOOTING

### Common Issues and Solutions

#### Issue: Cloud Run Cold Start Latency
**Solution**: Configure minimum instances and CPU allocation
```bash
gcloud run services update podcastflow-dashboard \
    --min-instances=2 \
    --cpu=2 \
    --memory=2Gi
```

#### Issue: BigQuery Query Timeouts
**Solution**: Optimize queries and increase timeout limits
```python
# Configure BigQuery client with extended timeout
client = bigquery.Client()
job_config = bigquery.QueryJobConfig(
    job_timeout_ms=300000,  # 5 minutes
    use_query_cache=True,
    use_legacy_sql=False
)
```

#### Issue: ML Model Serving Errors
**Solution**: Check model endpoints and retry logic
```bash
# Check model deployment status
gcloud ai models list --region=${REGION}

# Test model endpoint
curl -X POST \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/endpoints/ENDPOINT_ID:predict
```

---

## 📞 SUPPORT & CONTACT

### Emergency Contacts
- **Technical Lead**: [Your Contact Information]
- **DevOps Team**: [Team Contact Information]
- **Security Team**: [Security Contact Information]

### Support Channels
- **Documentation**: https://docs.podcastflow.analytics
- **Status Page**: https://status.podcastflow.analytics
- **Support Email**: support@podcastflow.analytics

---

**Deployment Guide Version**: 3.0.0  
**Last Updated**: 2024-12-30  
**Next Review**: 2025-01-30 