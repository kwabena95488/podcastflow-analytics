# BigQuery Infrastructure Setup with Terraform - FREE TIER OPTIMIZED
# This configuration creates the complete BigQuery infrastructure for PodcastFlow Analytics
# Optimized for Google Cloud Free Tier limits

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"  # Free tier region
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "bigquery_api" {
  service = "bigquery.googleapis.com"
}

resource "google_project_service" "storage_api" {
  service = "storage.googleapis.com"
}

resource "google_project_service" "resource_manager_api" {
  service = "cloudresourcemanager.googleapis.com"
}

# BigQuery Datasets - Medallion Architecture (FREE TIER OPTIMIZED)
resource "google_bigquery_dataset" "bronze" {
  dataset_id    = "bronze"
  friendly_name = "Bronze Layer - Raw Data"
  description   = "Raw data ingestion layer for podcast analytics"
  location      = "US"

  # FREE TIER: Shorter expiration to stay under 10GB limit
  default_table_expiration_ms = 2592000000 # 30 days (instead of 90)
  
  labels = {
    environment = var.environment
    layer       = "bronze"
    project     = "podcastflow-analytics"
    tier        = "free"
  }

  access {
    role          = "OWNER"
    user_by_email = google_service_account.dbt_service_account.email
  }

  access {
    role          = "WRITER"
    user_by_email = google_service_account.streaming_service_account.email
  }
}

resource "google_bigquery_dataset" "silver" {
  dataset_id    = "silver"
  friendly_name = "Silver Layer - Cleaned Data"
  description   = "Cleaned and validated data layer"
  location      = "US"

  # FREE TIER: Shorter expiration for intermediate data
  default_table_expiration_ms = 5184000000 # 60 days

  labels = {
    environment = var.environment
    layer       = "silver"
    project     = "podcastflow-analytics"
    tier        = "free"
  }

  access {
    role          = "OWNER"
    user_by_email = google_service_account.dbt_service_account.email
  }
}

resource "google_bigquery_dataset" "gold" {
  dataset_id    = "gold"
  friendly_name = "Gold Layer - Analytics Ready"
  description   = "Analytics-ready aggregated data layer"
  location      = "US"

  # No expiration for gold layer (most important data)
  labels = {
    environment = var.environment
    layer       = "gold"
    project     = "podcastflow-analytics"
    tier        = "free"
  }

  access {
    role          = "OWNER"
    user_by_email = google_service_account.dbt_service_account.email
  }

  access {
    role          = "READER"
    user_by_email = google_service_account.dashboard_service_account.email
  }
}

resource "google_bigquery_dataset" "dbt_artifacts" {
  dataset_id    = "dbt_artifacts"
  friendly_name = "dbt Metadata"
  description   = "dbt metadata and lineage tracking"
  location      = "US"

  # FREE TIER: Short expiration for metadata
  default_table_expiration_ms = 1296000000 # 15 days

  labels = {
    environment = var.environment
    layer       = "metadata"
    project     = "podcastflow-analytics"
    tier        = "free"
  }

  access {
    role          = "OWNER"
    user_by_email = google_service_account.dbt_service_account.email
  }
}

# Service Accounts
resource "google_service_account" "dbt_service_account" {
  account_id   = "podcastflow-dbt-${var.environment}"
  display_name = "PodcastFlow dbt Service Account"
  description  = "Service account for dbt transformations"
}

resource "google_service_account" "streaming_service_account" {
  account_id   = "podcastflow-streaming-${var.environment}"
  display_name = "PodcastFlow Streaming Service Account"
  description  = "Service account for real-time data ingestion"
}

resource "google_service_account" "dashboard_service_account" {
  account_id   = "podcastflow-dashboard-${var.environment}"
  display_name = "PodcastFlow Dashboard Service Account"
  description  = "Service account for dashboard access"
}

# IAM Bindings for dbt Service Account
resource "google_project_iam_member" "dbt_bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.dbt_service_account.email}"
}

resource "google_project_iam_member" "dbt_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.dbt_service_account.email}"
}

# IAM Bindings for Streaming Service Account
resource "google_project_iam_member" "streaming_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.streaming_service_account.email}"
}

resource "google_project_iam_member" "streaming_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.streaming_service_account.email}"
}

# IAM Bindings for Dashboard Service Account
resource "google_project_iam_member" "dashboard_bigquery_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.dashboard_service_account.email}"
}

resource "google_project_iam_member" "dashboard_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dashboard_service_account.email}"
}

# GCS Bucket for temporary BigQuery operations (FREE TIER OPTIMIZED)
resource "google_storage_bucket" "bigquery_temp" {
  name     = "${var.project_id}-bigquery-temp-${var.environment}"
  location = "US-CENTRAL1"  # Free tier region

  # FREE TIER: Aggressive lifecycle to stay under 5GB
  lifecycle_rule {
    condition {
      age = 1  # Delete after 1 day
    }
    action {
      type = "Delete"
    }
  }

  # Additional lifecycle rule for multipart uploads
  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }

  labels = {
    environment = var.environment
    project     = "podcastflow-analytics"
    purpose     = "bigquery-temp"
    tier        = "free"
  }
}

# Sample Tables in Bronze Layer (FREE TIER OPTIMIZED)
resource "google_bigquery_table" "rss_feeds" {
  dataset_id          = google_bigquery_dataset.bronze.dataset_id
  table_id            = "rss_feeds"
  description         = "Raw RSS feed data (free tier optimized)"
  deletion_protection = false

  schema = jsonencode([
    {
      name = "feed_url"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "raw_content"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "ingestion_timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "podcast_title"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "episode_count"
      type = "INTEGER"
      mode = "NULLABLE"
    }
  ])

  time_partitioning {
    type  = "DAY"
    field = "ingestion_timestamp"
    # FREE TIER: Only keep 30 days of partitions
    expiration_ms = 2592000000  # 30 days
  }

  clustering = ["podcast_title"]
}

resource "google_bigquery_table" "listening_events" {
  dataset_id          = google_bigquery_dataset.bronze.dataset_id
  table_id            = "listening_events"
  description         = "User listening behavior events (free tier optimized)"
  deletion_protection = false

  schema = jsonencode([
    {
      name = "event_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "user_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "episode_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "event_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "completion_percentage"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "event_timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "platform"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "device_type"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])

  time_partitioning {
    type  = "DAY"
    field = "event_timestamp"
    # FREE TIER: Only keep 30 days of partitions
    expiration_ms = 2592000000  # 30 days
  }

  clustering = ["user_id", "episode_id", "event_type"]
}

# Service Account Keys (for local development)
resource "google_service_account_key" "dbt_key" {
  service_account_id = google_service_account.dbt_service_account.name
}

resource "google_service_account_key" "streaming_key" {
  service_account_id = google_service_account.streaming_service_account.name
}

resource "google_service_account_key" "dashboard_key" {
  service_account_id = google_service_account.dashboard_service_account.name
}

# Outputs
output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "bigquery_datasets" {
  description = "Created BigQuery datasets"
  value = {
    bronze       = google_bigquery_dataset.bronze.dataset_id
    silver       = google_bigquery_dataset.silver.dataset_id
    gold         = google_bigquery_dataset.gold.dataset_id
    dbt_artifacts = google_bigquery_dataset.dbt_artifacts.dataset_id
  }
}

output "service_accounts" {
  description = "Created service accounts"
  value = {
    dbt_service_account       = google_service_account.dbt_service_account.email
    streaming_service_account = google_service_account.streaming_service_account.email
    dashboard_service_account = google_service_account.dashboard_service_account.email
  }
}

output "temp_bucket" {
  description = "Temporary GCS bucket for BigQuery operations"
  value       = google_storage_bucket.bigquery_temp.name
}

output "dbt_key_file" {
  description = "dbt service account key (base64 encoded)"
  value       = google_service_account_key.dbt_key.private_key
  sensitive   = true
}

# FREE TIER USAGE SUMMARY
output "free_tier_info" {
  description = "Free tier optimization summary"
  value = {
    bigquery_storage_limit = "10 GB/month"
    bigquery_query_limit   = "1 TB/month"
    gcs_storage_limit      = "5 GB/month"
    table_expiration_days  = "30 days (bronze), 60 days (silver), unlimited (gold)"
    cost_controls          = "Enabled with aggressive lifecycle policies"
  }
} 