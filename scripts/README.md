# Scripts Directory

This directory contains all operational scripts for the PodcastFlow Analytics platform, organized by functionality for better maintainability and ease of use.

## 📁 Directory Structure

### 📊 `/data-ingestion/`
Scripts for ingesting data from various sources:

- **`rss_feed_ingestion.py`** - Automated RSS feed crawling and parsing
- **`social_media_ingestion.py`** - Social media mentions and sentiment data collection
- **`realtime_events_ingestion.py`** - Real-time listening events simulation and processing

### 🏗️ `/dbt/`
dbt-related operation scripts:

- **`run_dbt_transformations.py`** - Execute dbt models and transformations
- **`run_dbt_cloud.py`** - dbt Cloud integration and remote execution

### 🧪 `/testing/`
Testing, validation, and demonstration scripts:

- **`demo_system.py`** - End-to-end system demonstration
- **`performance_benchmark.py`** - Platform performance testing and benchmarking
- **`final_verification.py`** - Comprehensive system validation

### ⚙️ `/setup/`
Initial setup and configuration scripts:

- **`init-db.sql`** - Database schema initialization
- **`load_sample_data_emulator.py`** - Sample data loading for development
- **`run_real_data_ingestion.py`** - Production data ingestion workflow
- **`simple_emulator_loader.py`** - Simplified data loading for testing

## 🚀 Usage Guide

### Data Ingestion Workflow

**RSS Feed Processing**:
```bash
python scripts/data-ingestion/rss_feed_ingestion.py
```

**Social Media Data Collection**:
```bash
python scripts/data-ingestion/social_media_ingestion.py
```

**Real-time Events Simulation**:
```bash
python scripts/data-ingestion/realtime_events_ingestion.py
```

### dbt Operations

**Run Transformations**:
```bash
python scripts/dbt/run_dbt_transformations.py
```

**Cloud Integration**:
```bash
python scripts/dbt/run_dbt_cloud.py
```

### Testing & Validation

**System Demo**:
```bash
python scripts/testing/demo_system.py
```

**Performance Testing**:
```bash
python scripts/testing/performance_benchmark.py
```

**Final Validation**:
```bash
python scripts/testing/final_verification.py
```

### Initial Setup

**Database Initialization**:
```bash
# Run SQL initialization
psql -f scripts/setup/init-db.sql

# Or use Python wrapper
python scripts/setup/load_sample_data_emulator.py
```

## 📋 Script Dependencies

### Common Requirements
All scripts require:
- Python 3.8+
- Dependencies from `requirements.txt`
- Proper environment variable configuration

### Environment Variables
Ensure these are set before running scripts:

```bash
# Database Configuration
POSTGRES_PASSWORD=your_password
BIGQUERY_EMULATOR_HOST=localhost
BIGQUERY_EMULATOR_PORT=9050

# Google Cloud (for production)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# Application Settings
ENVIRONMENT=development|staging|production
```

### Service Dependencies

**Data Ingestion Scripts**:
- BigQuery Emulator or Google BigQuery
- Network access to external data sources
- Sufficient storage space for data

**dbt Scripts**:
- dbt Core installation
- Valid dbt profiles configuration
- Database connectivity

**Testing Scripts**:
- All platform services running
- Sample data loaded
- Network connectivity

## 🔧 Development Guidelines

### Adding New Scripts

1. **Choose appropriate directory** based on script functionality
2. **Follow naming conventions**: `verb_noun_description.py`
3. **Include proper documentation** and error handling
4. **Add dependencies** to requirements.txt if needed
5. **Update this README** with script description

### Script Structure Template

```python
#!/usr/bin/env python3
"""
Script Description: Brief description of what this script does

Usage:
    python script_name.py [arguments]

Dependencies:
    - List required services
    - List environment variables
    - List Python packages

Author: Your Name
Date: Creation Date
"""

import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main script execution"""
    try:
        # Script logic here
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Error Handling Best Practices

1. **Use proper logging** instead of print statements
2. **Handle exceptions gracefully** with informative error messages
3. **Validate environment** before script execution
4. **Provide clear exit codes** for automation integration
5. **Include retry logic** for network-dependent operations

## 📊 Monitoring & Logging

### Script Execution Tracking

All scripts should:
- Log start and completion times
- Record processing metrics (rows processed, files created, etc.)
- Report any errors or warnings
- Provide execution summaries

### Performance Monitoring

For long-running scripts:
- Include progress indicators
- Monitor memory usage
- Track execution time
- Implement timeouts for external calls

### Log Management

Logs are written to:
- Console output (for interactive execution)
- Application logs (for automated execution)
- Platform monitoring systems (in production)

## 🔄 Automation Integration

### Scheduled Execution

Scripts designed for automated execution:
- **Data Ingestion**: Hourly/daily schedules
- **dbt Transformations**: After data ingestion completion
- **Validation**: Daily health checks

### CI/CD Integration

Scripts used in deployment pipelines:
- **Testing Scripts**: Automated quality assurance
- **Setup Scripts**: Environment preparation
- **Validation Scripts**: Deployment verification

## 🆘 Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Database Connection Issues**:
```bash
# Check environment variables
echo $POSTGRES_PASSWORD
echo $BIGQUERY_EMULATOR_HOST

# Test connectivity
python -c "import psycopg2; print('PostgreSQL module available')"
```

**Permission Issues**:
```bash
# Make scripts executable
chmod +x scripts/**/*.py

# Check file permissions
ls -la scripts/
```

### Script-Specific Help

Each script includes:
- `--help` argument for usage information
- Built-in error messages for common issues
- Logging output for debugging

**Example**:
```bash
python scripts/data-ingestion/rss_feed_ingestion.py --help
```

---

**Scripts Last Updated**: September 2025
**Total Scripts**: 13 organized scripts
**Next Review**: After Phase 3 implementation