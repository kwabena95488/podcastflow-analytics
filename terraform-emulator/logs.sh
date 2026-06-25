#!/bin/bash

# Utility script to view logs for emulator services

SERVICE_NAME=${1:-}

if [ -z "$SERVICE_NAME" ]; then
    echo "🎧 PodcastFlow Analytics - Service Logs"
    echo "Usage: $0 <service-name>"
    echo ""
    echo "Available services:"
    docker ps --filter "label=project=podcastflow-analytics" --format "  • {{.Names}}"
    echo ""
    echo "Examples:"
    echo "  $0 bigquery-emulator"
    echo "  $0 streamlit-dashboard"
    echo "  $0 jupyter-podcastflow"
    exit 1
fi

# Check if service exists
if ! docker ps --filter "name=$SERVICE_NAME" --filter "label=project=podcastflow-analytics" --format "{{.Names}}" | grep -q "^$SERVICE_NAME$"; then
    echo "❌ Service '$SERVICE_NAME' not found or not part of podcastflow-analytics project"
    echo ""
    echo "Available services:"
    docker ps --filter "label=project=podcastflow-analytics" --format "  • {{.Names}}"
    exit 1
fi

echo "📋 Showing logs for: $SERVICE_NAME"
echo "Press Ctrl+C to exit"
echo "=================================="

docker logs -f "$SERVICE_NAME" 