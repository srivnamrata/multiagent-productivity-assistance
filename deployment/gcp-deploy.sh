#!/bin/bash

# GCP Deployment Script for Multi-Agent Productivity Assistant
# This script automates the deployment process to Google Cloud Platform

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$SCRIPT_DIR"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -p, --project    GCP Project ID (required)
    -r, --region     GCP Region (default: us-central1)
    -e, --env        Environment: dev, staging, prod (default: staging)
    -t, --tag        Docker image tag (default: latest)
    -b, --build      Build Docker image before deploying
    -d, --deploy     Deploy using Terraform
    -h, --help       Display this help message

Examples:
    # Build and deploy to staging
    $0 --project my-gcp-project --env staging --build --deploy

    # Deploy only to production
    $0 --project my-gcp-project --env prod --deploy

EOF
    exit 1
}

# Parse command line arguments
PROJECT_ID=""
REGION="us-central1"
ENVIRONMENT="staging"
IMAGE_TAG="latest"
BUILD_IMAGE=false
DEPLOY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -b|--build)
            BUILD_IMAGE=true
            shift
            ;;
        -d|--deploy)
            DEPLOY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$PROJECT_ID" ]; then
    print_error "GCP Project ID is required"
    usage
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    usage
fi

print_info "Deployment Configuration"
echo "  Project ID:  $PROJECT_ID"
echo "  Region:      $REGION"
echo "  Environment: $ENVIRONMENT"
echo "  Image Tag:   $IMAGE_TAG"

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed"
    exit 1
fi
print_success "gcloud CLI found"

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_success "Docker found"

if [ "$DEPLOY" = true ] && ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed"
    exit 1
fi
[ "$DEPLOY" = true ] && print_success "Terraform found"

# Authenticate with GCP
print_info "Authenticating with GCP..."
gcloud auth login || print_warning "Authentication skipped (already authenticated)"
gcloud config set project "$PROJECT_ID"
print_success "GCP project set to $PROJECT_ID"

# Enable required APIs
print_info "Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    pubsub.googleapis.com \
    firestore.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    cloudtrace.googleapis.com
print_success "APIs enabled"

# Build Docker image
if [ "$BUILD_IMAGE" = true ]; then
    print_info "Building Docker image..."
    
    # Create Artifact Registry repository if it doesn't exist
    REPO_NAME="productivity-assistant"
    
    if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &> /dev/null; then
        print_info "Creating Artifact Registry repository..."
        gcloud artifacts repositories create "$REPO_NAME" \
            --repository-format=docker \
            --location="$REGION"
        print_success "Repository created"
    fi
    
    # Build and push image
    IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/productivity-assistant:${IMAGE_TAG}"
    
    print_info "Building image: $IMAGE_URL"
    docker build -t "$IMAGE_URL" "$PROJECT_ROOT"
    
    print_info "Pushing image to Artifact Registry..."
    # Configure Docker authentication
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"
    docker push "$IMAGE_URL"
    
    print_success "Image pushed: $IMAGE_URL"
    
    CONTAINER_IMAGE="$IMAGE_URL"
else
    print_warning "Skipping Docker build"
    CONTAINER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/productivity-assistant/productivity-assistant:${IMAGE_TAG}"
fi

# Deploy using Terraform
if [ "$DEPLOY" = true ]; then
    print_info "Deploying using Terraform..."
    
    cd "$DEPLOYMENT_DIR/terraform"
    
    # Select tfvars file based on environment
    TFVARS_FILE="${ENVIRONMENT}.tfvars"
    if [ ! -f "$TFVARS_FILE" ]; then
        print_error "Terraform variables file not found: $TFVARS_FILE"
        exit 1
    fi
    
    # Update container image in tfvars
    print_info "Updating container image in Terraform variables..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|container_image = .*|container_image = \"${CONTAINER_IMAGE}\"|" "$TFVARS_FILE"
    else
        # Linux
        sed -i "s|container_image = .*|container_image = \"${CONTAINER_IMAGE}\"|" "$TFVARS_FILE"
    fi
    
    # Initialize Terraform
    print_info "Initializing Terraform..."
    terraform init
    
    # Plan
    print_info "Running Terraform plan..."
    terraform plan -var-file="$TFVARS_FILE" -out=tfplan
    
    # Apply
    print_info "Applying Terraform configuration..."
    read -p "Do you want to proceed with deployment? (yes/no): " -r
    echo
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        terraform apply tfplan
        print_success "Deployment completed!"
        
        # Get outputs
        print_info "Deployment outputs:"
        terraform output -json | jq '.' 2>/dev/null || terraform output
        
        # Extract Cloud Run URL
        CLOUD_RUN_URL=$(terraform output -raw cloud_run_url 2>/dev/null)
        if [ -n "$CLOUD_RUN_URL" ]; then
            print_success "Cloud Run URL: $CLOUD_RUN_URL"
            
            # Test the deployment
            print_info "Testing deployment (waiting for service to be ready)..."
            for i in {1..30}; do
                if curl -s "$CLOUD_RUN_URL/health" &> /dev/null; then
                    print_success "Service is healthy!"
                    break
                fi
                print_info "Attempt $i/30: Waiting for service to be ready..."
                sleep 10
            done
        fi
    else
        print_warning "Deployment cancelled"
        exit 1
    fi
    
    cd - > /dev/null
else
    print_warning "Skipping Terraform deployment"
    print_info "To deploy, run with --deploy flag"
fi

print_success "Deployment process completed!"
