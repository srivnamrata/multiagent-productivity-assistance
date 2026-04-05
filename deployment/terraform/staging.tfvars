# Staging environment configuration for Terraform
# Usage: terraform apply -var-file="staging.tfvars"

gcp_project_id         = "your-gcp-project-id-staging"
gcp_region             = "us-central1"
vertex_ai_location     = "us-central1"
firestore_region       = "us-central1"
cloud_run_service_name = "productivity-assistant-staging"
environment            = "staging"

# Use real GCP services in staging
use_mock_llm   = false
use_mock_pubsub = false

# Container image from Google Cloud Artifact Registry
container_image = "us-central1-docker.pkg.dev/your-gcp-project-id-staging/productivity-assistant/productivity-assistant:latest"

# Performance settings for staging
cloud_run_min_instances = 1
cloud_run_max_instances = 20
cloud_run_memory        = "1Gi"
cloud_run_cpu           = "1"

# Vertex AI model
llm_model = "gemini-1.5-flash"

# Logging
log_level = "DEBUG"

# Labels
labels = {
  application = "productivity-assistant"
  environment = "staging"
  managed_by  = "terraform"
}
