# Production environment configuration for Terraform
# Usage: terraform apply -var-file="prod.tfvars"

gcp_project_id         = "your-gcp-project-id"
gcp_region             = "us-central1"
vertex_ai_location     = "us-central1"
firestore_region       = "us-central1"
cloud_run_service_name = "productivity-assistant"
environment            = "production"

# Use real GCP services in production
use_mock_llm   = false
use_mock_pubsub = false

# Container image from Google Cloud Artifact Registry
container_image = "us-central1-docker.pkg.dev/your-gcp-project-id/productivity-assistant/productivity-assistant:latest"

# Performance settings for production
cloud_run_min_instances = 1
cloud_run_max_instances = 100
cloud_run_memory        = "2Gi"
cloud_run_cpu           = "2"

# Vertex AI model
llm_model = "gemini-1.5-pro"

# Logging
log_level = "INFO"

# Labels
labels = {
  application = "productivity-assistant"
  environment = "production"
  managed_by  = "terraform"
}
