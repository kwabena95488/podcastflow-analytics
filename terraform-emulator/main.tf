# BigQuery Emulator Infrastructure with Terraform
# This configuration sets up the complete local development environment
# using the BigQuery emulator and supporting services

terraform {
  required_version = ">= 1.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Variables
variable "project_name" {
  description = "Project name for labeling"
  type        = string
  default     = "podcastflow-analytics"
}

variable "emulator_host_port" {
  description = "Host port for BigQuery emulator API"
  type        = number
  default     = 9050
}

variable "emulator_rest_port" {
  description = "Host port for BigQuery emulator REST API"
  type        = number
  default     = 9060
}

variable "jupyter_port" {
  description = "Host port for Jupyter notebook"
  type        = number
  default     = 8888
}

variable "streamlit_port" {
  description = "Host port for Streamlit dashboard"
  type        = number
  default     = 8501
}

# Provider configuration
provider "docker" {
  # Use default connection - Docker Desktop should handle the socket automatically
}

# Network for all services
resource "docker_network" "podcastflow_network" {
  name = "podcastflow-dev"
  driver = "bridge"
  
  labels {
    label = "project"
    value = var.project_name
  }
}

# BigQuery Emulator Container
resource "docker_container" "bigquery_emulator" {
  image = "ghcr.io/goccy/bigquery-emulator:latest"
  name  = "bigquery-emulator"
  hostname = "bigquery-emulator"

  networks_advanced {
    name = docker_network.podcastflow_network.name
    aliases = ["bigquery-emulator"]
  }

  ports {
    internal = 9050
    external = var.emulator_host_port
  }

  ports {
    internal = 9060
    external = var.emulator_rest_port
  }

  env = [
    "BIGQUERY_EMULATOR_PROJECT=podcastflow-analytics",
    "BIGQUERY_EMULATOR_HOST=0.0.0.0",
    "BIGQUERY_EMULATOR_PORT=9050"
  ]

  command = [
    "/bigquery-emulator",
    "--project=podcastflow-analytics",
    "--dataset=bronze,silver,gold,dbt_artifacts",
    "--port=9050"
  ]

  labels {
    label = "project"
    value = var.project_name
  }

  labels {
    label = "service"
    value = "bigquery-emulator"
  }

  # Health check
  healthcheck {
    test = ["CMD", "curl", "-f", "http://localhost:9050"]
    interval = "30s"
    timeout = "10s"
    retries = 3
    start_period = "30s"
  }

  restart = "unless-stopped"
}

# Data Initialization Container
resource "docker_container" "data_init" {
  image = "python:3.10-slim"
  name  = "data-init"
  
  networks_advanced {
    name = docker_network.podcastflow_network.name
  }

  depends_on = [docker_container.bigquery_emulator]

  volumes {
    host_path      = "${path.cwd}/../scripts"
    container_path = "/scripts"
    read_only      = true
  }

  volumes {
    host_path      = "${path.cwd}/../bigquery_init"
    container_path = "/bigquery_init"
    read_only      = true
  }

  env = [
    "BIGQUERY_EMULATOR_HOST=bigquery-emulator",
    "BIGQUERY_EMULATOR_PORT=9050",
    "GCP_PROJECT_ID=podcastflow-analytics"
  ]

  command = [
    "sh", "-c", 
    "pip install requests && sleep 60 && python /scripts/simple_emulator_loader.py"
  ]

  labels {
    label = "project"
    value = var.project_name
  }

  labels {
    label = "service"
    value = "data-init"
  }

  restart = "no"  # Run once and exit
}

# dbt Container for transformations
resource "docker_container" "dbt_emulator" {
  image = "ghcr.io/dbt-labs/dbt-bigquery:latest"
  name  = "dbt-emulator"
  
  networks_advanced {
    name = docker_network.podcastflow_network.name
  }

  depends_on = [docker_container.bigquery_emulator, docker_container.data_init]

  volumes {
    host_path      = "${path.cwd}/../dbt_podcast_analytics"
    container_path = "/usr/app/dbt"
  }

  volumes {
    host_path      = "${path.cwd}/../dbt_profiles_bigquery.yml"
    container_path = "/root/.dbt/profiles.yml"
    read_only      = true
  }

  env = [
    "BIGQUERY_EMULATOR_HOST=http://bigquery-emulator:9050",
    "GCP_PROJECT_ID=podcastflow-analytics"
  ]

  working_dir = "/usr/app/dbt"

  command = [
    "sh", "-c",
    "sleep 120 && dbt debug --target emulator && dbt run --target emulator && dbt test --target emulator"
  ]

  labels {
    label = "project"
    value = var.project_name
  }

  labels {
    label = "service"
    value = "dbt"
  }

  restart = "no"  # Run once for initial setup
}

# Jupyter Notebook for development
resource "docker_container" "jupyter" {
  image = "jupyter/datascience-notebook:latest"
  name  = "jupyter-podcastflow"
  
  networks_advanced {
    name = docker_network.podcastflow_network.name
  }

  ports {
    internal = 8888
    external = var.jupyter_port
  }

  volumes {
    host_path      = "${path.cwd}/../notebooks"
    container_path = "/home/jovyan/work"
  }

  volumes {
    host_path      = "${path.cwd}/../scripts"
    container_path = "/home/jovyan/scripts"
    read_only      = true
  }

  env = [
    "JUPYTER_ENABLE_LAB=yes",
    "JUPYTER_TOKEN=podcastflow",
    "BIGQUERY_EMULATOR_HOST=http://bigquery-emulator:9050",
    "GCP_PROJECT_ID=podcastflow-analytics"
  ]

  command = [
    "start-notebook.sh",
    "--NotebookApp.token=podcastflow",
    "--NotebookApp.password=",
    "--NotebookApp.allow_root=True"
  ]

  labels {
    label = "project"
    value = var.project_name
  }

  labels {
    label = "service"
    value = "jupyter"
  }

  restart = "unless-stopped"
}

# Streamlit Dashboard
resource "docker_container" "streamlit_dashboard" {
  image = "python:3.10-slim"
  name  = "streamlit-dashboard"
  
  networks_advanced {
    name = docker_network.podcastflow_network.name
  }

  depends_on = [docker_container.bigquery_emulator, docker_container.data_init]

  ports {
    internal = 8501
    external = var.streamlit_port
  }

  volumes {
    host_path      = "${path.cwd}/../dashboard"
    container_path = "/app"
  }

  env = [
    "BIGQUERY_EMULATOR_HOST=http://bigquery-emulator:9050",
    "GCP_PROJECT_ID=podcastflow-analytics",
    "STREAMLIT_SERVER_PORT=8501",
    "STREAMLIT_SERVER_ADDRESS=0.0.0.0"
  ]

  working_dir = "/app"

  command = [
    "sh", "-c",
    "pip install streamlit plotly pandas google-cloud-bigquery && sleep 180 && streamlit run app.py"
  ]

  labels {
    label = "project"
    value = var.project_name
  }

  labels {
    label = "service"
    value = "streamlit"
  }

  restart = "unless-stopped"
}

# Outputs
output "bigquery_emulator_url" {
  description = "BigQuery emulator REST API URL"
  value       = "http://localhost:${var.emulator_rest_port}"
}

output "jupyter_url" {
  description = "Jupyter notebook URL"
  value       = "http://localhost:${var.jupyter_port}?token=podcastflow"
}

output "dashboard_url" {
  description = "Streamlit dashboard URL"
  value       = "http://localhost:${var.streamlit_port}"
}

output "emulator_info" {
  description = "BigQuery emulator connection information"
  value = {
    project_id = "podcastflow-analytics"
    host       = "localhost"
    port       = var.emulator_host_port
    rest_port  = var.emulator_rest_port
    datasets   = ["bronze", "silver", "gold", "dbt_artifacts"]
  }
}

output "service_status" {
  description = "Status of all services"
  value = {
    bigquery_emulator = "Running on port ${var.emulator_rest_port}"
    jupyter          = "Running on port ${var.jupyter_port} (token: podcastflow)"
    dashboard        = "Running on port ${var.streamlit_port}"
    network          = docker_network.podcastflow_network.name
  }
} 