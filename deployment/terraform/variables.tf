variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  validation {
    condition     = length(var.gcp_project_id) > 0
    error_message = "GCP Project ID must not be empty"
  }
}

variable "gcp_region" {
  description = "GCP region for Cloud Run and other resources"
  type        = string
  default     = "us-central1"
  validation {
    condition     = contains(["us-central1", "us-east1", "us-west1", "europe-west1", "asia-northeast1"], var.gcp_region)
    error_message = "Region must be a valid GCP region"
  }
}

variable "vertex_ai_location" {
  description = "Location for Vertex AI (Gemini) model"
  type        = string
  default     = "us-central1"
}

variable "firestore_region" {
  description = "Region for Firestore database"
  type        = string
  default     = "us-central1"
}

variable "cloud_run_service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "productivity-assistant"
}

variable "environment" {
  description = "Environment (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production"
  }
}

variable "container_image" {
  description = "Container image URL (e.g., gcr.io/project-id/productivity-assistant:latest)"
  type        = string
  validation {
    condition     = length(var.container_image) > 0
    error_message = "Container image URL must not be empty"
  }
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
  validation {
    condition     = var.cloud_run_min_instances >= 0
    error_message = "Min instances must be >= 0"
  }
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
  validation {
    condition     = var.cloud_run_max_instances <= 1000
    error_message = "Max instances must be <= 1000"
  }
}

variable "cloud_run_memory" {
  description = "Memory for Cloud Run (e.g., 512Mi, 1Gi, 2Gi)"
  type        = string
  default     = "1Gi"
}

variable "cloud_run_cpu" {
  description = "CPU for Cloud Run (e.g., 1, 2, 4)"
  type        = string
  default     = "1"
}

variable "llm_model" {
  description = "Vertex AI model to use (e.g., gemini-1.5-pro, gemini-1.5-flash)"
  type        = string
  default     = "gemini-1.5-pro"
}

variable "pubsub_prefix" {
  description = "Prefix for Pub/Sub topics and subscriptions"
  type        = string
  default     = "productivity-assistant"
}

variable "use_mock_llm" {
  description = "Use mock LLM service (for testing)"
  type        = bool
  default     = false
}

variable "use_mock_pubsub" {
  description = "Use mock Pub/Sub service (for testing)"
  type        = bool
  default     = false
}

variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be DEBUG, INFO, WARNING, or ERROR"
  }
}

variable "notification_channels" {
  description = "Monitoring notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Labels to add to all resources"
  type        = map(string)
  default = {
    application = "productivity-assistant"
    managed_by  = "terraform"
  }
}
