terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration - uncomment and configure after first deployment
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "productivity-assistant"
  # }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",           # Cloud Run
    "pubsub.googleapis.com",        # Pub/Sub
    "firestore.googleapis.com",     # Firestore
    "aiplatform.googleapis.com",    # Vertex AI
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",       # Cloud Logging
    "monitoring.googleapis.com",    # Cloud Monitoring
    "cloudtrace.googleapis.com",    # Cloud Trace
    "servicenetworking.googleapis.com",
    "container.googleapis.com",     # GKE (optional)
  ])

  service            = each.value
  disable_on_destroy = false
}

# Create service account for the application
resource "google_service_account" "productivity_assistant" {
  account_id   = "productivity-assistant-sa"
  display_name = "Productivity Assistant Service Account"
  disabled     = false
}

# IAM roles for Cloud Run service account
resource "google_project_iam_member" "run_ai_user" {
  project = var.gcp_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.productivity_assistant.email}"
}

resource "google_project_iam_member" "run_pubsub_editor" {
  project = var.gcp_project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.productivity_assistant.email}"
}

resource "google_project_iam_member" "run_firestore_user" {
  project = var.gcp_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.productivity_assistant.email}"
}

resource "google_project_iam_member" "run_logging_writer" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.productivity_assistant.email}"
}

resource "google_project_iam_member" "run_monitoring_writer" {
  project = var.gcp_project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.productivity_assistant.email}"
}

resource "google_project_iam_member" "run_trace_writer" {
  project = var.gcp_project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_assistant.productivity_assistant.email}"
}

# Create Pub/Sub topics
resource "google_pubsub_topic" "workflow_progress" {
  name              = "${var.pubsub_prefix}-workflow-progress"
  message_retention_duration = "86400s"  # 1 day
  depends_on        = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "workflow_replan" {
  name              = "${var.pubsub_prefix}-workflow-replan"
  message_retention_duration = "86400s"
  depends_on        = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "agent_health" {
  name              = "${var.pubsub_prefix}-agent-health"
  message_retention_duration = "3600s"  # 1 hour
  depends_on        = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "system_events" {
  name              = "${var.pubsub_prefix}-system-events"
  message_retention_duration = "86400s"
  depends_on        = [google_project_service.required_apis]
}

# ===== DEAD-LETTER QUEUE (DLQ) TOPICS =====
resource "google_pubsub_topic" "workflow_progress_dlq" {
  name              = "${var.pubsub_prefix}-workflow-progress-dlq"
  message_retention_duration = "604800s"  # 7 days retention for debugging
  depends_on        = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "workflow_replan_dlq" {
  name              = "${var.pubsub_prefix}-workflow-replan-dlq"
  message_retention_duration = "604800s"
  depends_on        = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "agent_health_dlq" {
  name              = "${var.pubsub_prefix}-agent-health-dlq"
  message_retention_duration = "604800s"
  depends_on        = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "system_events_dlq" {
  name              = "${var.pubsub_prefix}-system-events-dlq"
  message_retention_duration = "604800s"
  depends_on        = [google_project_service.required_apis]
}

# Create Pub/Sub subscriptions with dead-letter policies
resource "google_pubsub_subscription" "workflow_progress_sub" {
  name             = "${var.pubsub_prefix}-workflow-progress-sub"
  topic            = google_pubsub_topic.workflow_progress.name
  ack_deadline_seconds = 60
  
  # Dead-letter policy: after 5 delivery attempts, send to DLQ
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.workflow_progress_dlq.id
    max_delivery_attempts = 5
  }
  
  # Exponential backoff: 10s, 30s, 100s, 300s, 600s
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  depends_on       = [google_project_service.required_apis]
}

resource "google_pubsub_subscription" "workflow_replan_sub" {
  name             = "${var.pubsub_prefix}-workflow-replan-sub"
  topic            = google_pubsub_topic.workflow_replan.name
  ack_deadline_seconds = 60
  
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.workflow_replan_dlq.id
    max_delivery_attempts = 5
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  depends_on       = [google_project_service.required_apis]
}

# Agent health subscription with DLQ
resource "google_pubsub_subscription" "agent_health_sub" {
  name             = "${var.pubsub_prefix}-agent-health-sub"
  topic            = google_pubsub_topic.agent_health.name
  ack_deadline_seconds = 60
  
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.agent_health_dlq.id
    max_delivery_attempts = 5
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  depends_on       = [google_project_service.required_apis]
}

# System events subscription with DLQ
resource "google_pubsub_subscription" "system_events_sub" {
  name             = "${var.pubsub_prefix}-system-events-sub"
  topic            = google_pubsub_topic.system_events.name
  ack_deadline_seconds = 60
  
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.system_events_dlq.id
    max_delivery_attempts = 5
  }
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  depends_on       = [google_project_service.required_apis]
}

# DLQ subscriptions (for manual reprocessing)
resource "google_pubsub_subscription" "workflow_progress_dlq_sub" {
  name             = "${var.pubsub_prefix}-workflow-progress-dlq-sub"
  topic            = google_pubsub_topic.workflow_progress_dlq.name
  ack_deadline_seconds = 300  # Longer timeout for manual processing
  depends_on       = [google_project_service.required_apis]
}

resource "google_pubsub_subscription" "workflow_replan_dlq_sub" {
  name             = "${var.pubsub_prefix}-workflow-replan-dlq-sub"
  topic            = google_pubsub_topic.workflow_replan_dlq.name
  ack_deadline_seconds = 300
  depends_on       = [google_project_service.required_apis]
}

# Enable Firestore (in native mode)
resource "google_firestore_database" "database" {
  project     = var.gcp_project_id
  name        = "(default)"
  location_id = var.firestore_region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.required_apis]
}

# Cloud Run service
resource "google_cloud_run_service" "productivity_assistant" {
  name     = var.cloud_run_service_name
  location = var.gcp_region

  template {
    spec {
      service_account_name = google_service_account.productivity_assistant.email
      
      containers {
        image = var.container_image
        ports {
          container_port = 8000
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }
        env {
          name  = "GCP_REGION"
          value = var.gcp_region
        }
        env {
          name  = "LLM_MODEL"
          value = var.llm_model
        }
        env {
          name  = "VERTEX_AI_LOCATION"
          value = var.vertex_ai_location
        }
        env {
          name  = "PUBSUB_TOPIC_PREFIX"
          value = var.pubsub_prefix
        }
        env {
          name  = "USE_MOCK_LLM"
          value = var.use_mock_llm ? "true" : "false"
        }
        env {
          name  = "USE_MOCK_PUBSUB"
          value = var.use_mock_pubsub ? "true" : "false"
        }
        env {
          name  = "USE_FIRESTORE"
          value = "true"
        }
        env {
          name  = "ENABLE_CLOUD_LOGGING"
          value = "true"
        }
        env {
          name  = "ENABLE_CLOUD_MONITORING"
          value = "true"
        }
        env {
          name  = "ENABLE_CLOUD_TRACE"
          value = "true"
        }
        env {
          name  = "LOG_LEVEL"
          value = var.log_level
        }
      }

      timeout_seconds = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
        "autoscaling.knative.dev/minScale" = var.cloud_run_min_instances
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.required_apis,
    google_firestore_database.database
  ]
}

# Make Cloud Run service public (for demo purposes - use proper auth in production)
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_service.productivity_assistant.name
  location = google_cloud_run_service.productivity_assistant.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Alternative: Restrict to specific IAM identity (recommended for production)
# resource "google_cloud_run_service_iam_member" "authenticated" {
#   service  = google_cloud_run_service.productivity_assistant.name
#   location = google_cloud_run_service.productivity_assistant.location
#   role     = "roles/run.invoker"
#   member   = "serviceAccount:${google_service_account.client.email}"
# }

# Cloud Monitoring Alert Policy (optional)
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "Productivity Assistant - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error Rate > 5%"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_service.productivity_assistant.name}\" AND metric.type=\"run.googleapis.com/request_count\" AND resource.labels.revision_name=~\"${google_cloud_run_service.productivity_assistant.name}-*\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
    }
  }

  notification_channels = var.notification_channels
  alert_strategy {
    auto_close = "1800s"
  }
}

# ===== DLQ MONITORING =====
# Alert on messages in DLQ (indicates failures)
resource "google_monitoring_alert_policy" "dlq_messages_alert" {
  display_name = "Productivity Assistant - Messages in Dead Letter Queue"
  combiner     = "OR"

  conditions {
    display_name = "DLQ has messages waiting"
    condition_threshold {
      filter          = "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
    }
  }

  notification_channels = var.notification_channels
  alert_strategy {
    auto_close = "1800s"
  }
}

# Outputs
output "cloud_run_url" {
  description = "The URL of the Cloud Run service"
  value       = google_cloud_run_service.productivity_assistant.status[0].url
}

output "service_account_email" {
  description = "The service account email"
  value       = google_service_account.productivity_assistant.email
}

output "pubsub_topics" {
  description = "Created Pub/Sub topics"
  value = {
    workflow_progress = google_pubsub_topic.workflow_progress.name
    workflow_replan   = google_pubsub_topic.workflow_replan.name
    agent_health      = google_pubsub_topic.agent_health.name
    system_events     = google_pubsub_topic.system_events.name
  }
}

output "pubsub_dlq_topics" {
  description = "Dead-Letter Queue topics for failed messages"
  value = {
    workflow_progress_dlq = google_pubsub_topic.workflow_progress_dlq.name
    workflow_replan_dlq   = google_pubsub_topic.workflow_replan_dlq.name
    agent_health_dlq      = google_pubsub_topic.agent_health_dlq.name
    system_events_dlq     = google_pubsub_topic.system_events_dlq.name
  }
}

output "pubsub_subscriptions" {
  description = "Created Pub/Sub subscriptions"
  value = {
    workflow_progress = google_pubsub_subscription.workflow_progress_sub.name
    workflow_replan   = google_pubsub_subscription.workflow_replan_sub.name
    agent_health      = google_pubsub_subscription.agent_health_sub.name
    system_events     = google_pubsub_subscription.system_events_sub.name
  }
}

output "pubsub_dlq_subscriptions" {
  description = "DLQ subscriptions for manual reprocessing"
  value = {
    workflow_progress_dlq = google_pubsub_subscription.workflow_progress_dlq_sub.name
    workflow_replan_dlq   = google_pubsub_subscription.workflow_replan_dlq_sub.name
  }
}

output "firestore_database" {
  description = "Firestore database information"
  value = {
    name     = google_firestore_database.database.name
    location = google_firestore_database.database.location_id
    type     = google_firestore_database.database.type
  }
}
