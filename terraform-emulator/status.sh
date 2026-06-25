#!/bin/bash

# Utility script to check status of all emulator services

echo "🎧 PodcastFlow Analytics - Service Status"
echo "=========================================="

# Check if any containers are running
CONTAINERS=$(docker ps --filter "label=project=podcastflow-analytics" --format "{{.Names}}")

if [ -z "$CONTAINERS" ]; then
    echo "❌ No services are currently running"
    echo ""
    echo "To start the environment, run:"
    echo "  terraform apply -var-file=terraform.tfvars"
    exit 1
fi

echo "📋 Container Status:"
docker ps --filter "label=project=podcastflow-analytics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🌐 Service URLs:"

# Check each service and provide URLs
for service in bigquery-emulator streamlit-dashboard jupyter-podcastflow; do
    if docker ps --filter "name=$service" --filter "label=project=podcastflow-analytics" --format "{{.Names}}" | grep -q "^$service$"; then
        case $service in
            "bigquery-emulator")
                echo "  • BigQuery Emulator API: http://localhost:9050"
                echo "  • BigQuery Emulator REST: http://localhost:9060"
                ;;
            "streamlit-dashboard")
                echo "  • Streamlit Dashboard: http://localhost:8501"
                ;;
            "jupyter-podcastflow")
                echo "  • Jupyter Notebooks: http://localhost:8888?token=podcastflow"
                ;;
        esac
    fi
done

echo ""
echo "🔍 Health Checks:"

# Test BigQuery emulator
if curl -s http://localhost:9060 >/dev/null 2>&1; then
    echo "  ✅ BigQuery emulator is responding"
else
    echo "  ❌ BigQuery emulator is not responding"
fi

# Test Streamlit (may take time to start)
if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "  ✅ Streamlit dashboard is responding"
else
    echo "  ⚠️  Streamlit dashboard is starting up or not ready"
fi

# Test Jupyter
if curl -s http://localhost:8888 >/dev/null 2>&1; then
    echo "  ✅ Jupyter notebook is responding"
else
    echo "  ⚠️  Jupyter notebook is starting up or not ready"
fi

echo ""
echo "📊 Quick Data Check:"

# Try to query sample data
if command -v docker >/dev/null && docker ps --filter "name=bigquery-emulator" --filter "label=project=podcastflow-analytics" --format "{{.Names}}" | grep -q "bigquery-emulator"; then
    # Simple query to check if data exists
    if timeout 10 python3 -c "
from google.cloud import bigquery
import os
os.environ['BIGQUERY_EMULATOR_HOST'] = 'http://localhost:9050'
client = bigquery.Client(project='podcastflow-analytics')
try:
    result = list(client.query('SELECT COUNT(*) as count FROM \`podcastflow-analytics.bronze.rss_feeds\`'))
    print(f'  ✅ Sample data loaded: {result[0].count} RSS feeds')
except Exception as e:
    print('  ⚠️  Sample data not yet loaded or accessible')
" 2>/dev/null; then
        :  # Success message already printed
    else
        echo "  ⚠️  Unable to check sample data (may still be loading)"
    fi
fi

echo ""
echo "🛠️  Management Commands:"
echo "  • View logs: ./logs.sh <service-name>"
echo "  • Stop all: terraform destroy"
echo "  • Restart service: docker restart <container-name>" 