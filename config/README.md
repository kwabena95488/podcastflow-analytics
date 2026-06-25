# Configuration Directory

This directory contains all configuration files for the PodcastFlow Analytics platform, organized by service and environment.

## 📁 Directory Structure

### 🗄️ `/bigquery/`
Google BigQuery and dbt configuration files:
- `dbt_profiles_bigquery.yml` - dbt profile configuration for BigQuery connections

### 🐳 `/docker/`
Docker and container orchestration configuration:
- `docker-compose.yml` - Main Docker Compose configuration for local development
- `docker-compose.bigquery.yml` - BigQuery-specific Docker configuration

### 🔐 `/credentials/`
⚠️ **Sensitive credential files** (see security warning in directory)
- `dbt_service_account.json` - Google Cloud service account for dbt operations
- **Security Note**: Files in this directory should never be committed to version control

### 🔧 `/configs/`
Application-specific configuration files by environment:
- `development/` - Local development configurations
- `staging/` - Staging environment configurations
- `production/` - Production environment configurations

## 🚀 Usage Guide

### Local Development Setup

1. **Docker Configuration**:
   ```bash
   # Use main Docker Compose file for local development
   docker-compose -f config/docker/docker-compose.yml up
   ```

2. **BigQuery Integration**:
   ```bash
   # Use BigQuery-specific configuration
   docker-compose -f config/docker/docker-compose.bigquery.yml up
   ```

3. **dbt Configuration**:
   ```bash
   # Copy dbt profiles to user directory
   cp config/bigquery/dbt_profiles_bigquery.yml ~/.dbt/profiles.yml
   ```

### Environment-Specific Configurations

**Development Environment**:
- Uses local services and emulated cloud services
- Configuration files in `configs/development/`

**Staging Environment**:
- Mirrors production with test data
- Configuration files in `configs/staging/`

**Production Environment**:
- Live cloud services and production data
- Configuration files in `configs/production/`

## 🔒 Security Best Practices

### Credential Management
1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive configuration
3. **Rotate service account keys** regularly
4. **Apply principle of least privilege** to service accounts

### Configuration Validation
Before deploying, ensure:
- All required environment variables are set
- Service account permissions are properly configured
- Network access rules are appropriate for environment
- Monitoring and logging are configured

## 📋 Configuration Reference

### Required Environment Variables

**Database Configuration**:
```bash
POSTGRES_PASSWORD=your_secure_password
POSTGRES_USER=podcastflow
POSTGRES_DB=podcastflow
```

**Google Cloud Configuration**:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

**Application Configuration**:
```bash
ENVIRONMENT=development|staging|production
DEBUG=true|false
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
```

### Service Configuration Files

**dbt Profiles** (`bigquery/dbt_profiles_bigquery.yml`):
- BigQuery connection settings
- Authentication configuration
- Dataset and schema settings

**Docker Compose** (`docker/docker-compose.yml`):
- Service definitions
- Network configuration
- Volume mounts
- Environment variables

## 🔧 Troubleshooting

### Common Configuration Issues

1. **dbt Connection Failures**:
   - Verify service account credentials
   - Check BigQuery project permissions
   - Validate profiles.yml syntax

2. **Docker Service Issues**:
   - Ensure proper port availability
   - Check volume mount permissions
   - Verify environment variable settings

3. **Environment Variable Issues**:
   - Confirm all required variables are set
   - Check variable formatting and values
   - Validate credential file paths

### Configuration Validation

Run these commands to validate configuration:

```bash
# Test dbt connection
dbt debug --profile bigquery

# Validate Docker Compose
docker-compose -f config/docker/docker-compose.yml config

# Check environment variables
env | grep -E "(POSTGRES|GOOGLE|DBT)_"
```

## 📈 Configuration Monitoring

### Health Checks
- Service connectivity validation
- Credential expiration monitoring
- Configuration drift detection
- Performance impact assessment

### Maintenance Schedule
- **Weekly**: Environment variable validation
- **Monthly**: Service account key rotation
- **Quarterly**: Configuration security review
- **Annually**: Architecture configuration review

---

**Configuration Last Updated**: September 2025
**Security Review**: Required every 90 days
**Next Review**: December 2025