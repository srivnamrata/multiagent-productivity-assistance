# GCP Deployment Script for Multi-Agent Productivity Assistant (PowerShell)
# This script automates the deployment process to Google Cloud Platform

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "staging",
    
    [Parameter(Mandatory=$false)]
    [string]$ImageTag = "latest",
    
    [Parameter(Mandatory=$false)]
    [switch]$BuildImage,
    
    [Parameter(Mandatory=$false)]
    [switch]$Deploy,
    
    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Color functions
function Write-InfoMessage {
    Write-Host "ℹ️  $args" -ForegroundColor Cyan
}

function Write-SuccessMessage {
    Write-Host "✅ $args" -ForegroundColor Green
}

function Write-WarningMessage {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

function Write-ErrorMessage {
    Write-Host "❌ $args" -ForegroundColor Red
}

# Display help
if ($Help) {
    Write-Host @"
GCP Deployment Script for Multi-Agent Productivity Assistant

Usage:
    .\gcp-deploy.ps1 -ProjectId <project-id> [Options]

Options:
    -ProjectId       GCP Project ID (required)
    -Region          GCP Region (default: us-central1)
    -Environment     Environment: dev, staging, prod (default: staging)
    -ImageTag        Docker image tag (default: latest)
    -BuildImage      Build Docker image before deploying
    -Deploy          Deploy using Terraform
    -Help            Display this help message

Examples:
    # Build and deploy to staging
    .\gcp-deploy.ps1 -ProjectId my-gcp-project -Environment staging -BuildImage -Deploy

    # Deploy only to production
    .\gcp-deploy.ps1 -ProjectId my-gcp-project -Environment prod -Deploy

"@
    exit 0
}

# Validate parameters
Write-InfoMessage "Deployment Configuration"
Write-Host "  Project ID:  $ProjectId"
Write-Host "  Region:      $Region"
Write-Host "  Environment: $Environment"
Write-Host "  Image Tag:   $ImageTag"

# Check prerequisites
Write-InfoMessage "Checking prerequisites..."

$requiredTools = @("gcloud", "docker")
if ($Deploy) {
    $requiredTools += "terraform"
}

foreach ($tool in $requiredTools) {
    if ((Get-Command $tool -ErrorAction SilentlyContinue) -eq $null) {
        Write-ErrorMessage "$tool is not installed"
        exit 1
    }
    Write-SuccessMessage "$tool found"
}

# Set project
Write-InfoMessage "Setting GCP project..."
& gcloud config set project $ProjectId
Write-SuccessMessage "GCP project set to $ProjectId"

# Enable APIs
Write-InfoMessage "Enabling required GCP APIs..."
$apis = @(
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com"
)

foreach ($api in $apis) {
    & gcloud services enable $api --quiet
}
Write-SuccessMessage "APIs enabled"

# Build Docker image
if ($BuildImage) {
    Write-InfoMessage "Building Docker image..."
    
    $repoName = "productivity-assistant"
    
    # Check if repository exists
    $repoExists = & gcloud artifacts repositories describe $repoName `
        --location=$Region --format="value(name)" 2>$null
    
    if (-not $repoExists) {
        Write-InfoMessage "Creating Artifact Registry repository..."
        & gcloud artifacts repositories create $repoName `
            --repository-format=docker `
            --location=$Region `
            --quiet
        Write-SuccessMessage "Repository created"
    }
    
    # Build and push image
    $imageUrl = "${Region}-docker.pkg.dev/${ProjectId}/${repoName}/productivity-assistant:${ImageTag}"
    
    Write-InfoMessage "Building image: $imageUrl"
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
    
    & docker build -t $imageUrl $projectRoot
    
    Write-InfoMessage "Pushing image to Artifact Registry..."
    & gcloud auth configure-docker "${Region}-docker.pkg.dev" --quiet
    & docker push $imageUrl
    
    Write-SuccessMessage "Image pushed: $imageUrl"
    $containerImage = $imageUrl
} else {
    Write-WarningMessage "Skipping Docker build"
    $containerImage = "${Region}-docker.pkg.dev/${ProjectId}/productivity-assistant/productivity-assistant:${ImageTag}"
}

# Deploy using Terraform
if ($Deploy) {
    Write-InfoMessage "Deploying using Terraform..."
    
    $terraformDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
    $terraformDir = Join-Path $terraformDir "terraform"
    
    Push-Location $terraformDir
    
    $tfvarsFile = "${Environment}.tfvars"
    if (-not (Test-Path $tfvarsFile)) {
        Write-ErrorMessage "Terraform variables file not found: $tfvarsFile"
        Pop-Location
        exit 1
    }
    
    # Update container image in tfvars
    Write-InfoMessage "Updating container image in Terraform variables..."
    $tfvarsContent = Get-Content $tfvarsFile
    $tfvarsContent = $tfvarsContent -replace 'container_image = .*', "container_image = `"$containerImage`""
    Set-Content $tfvarsFile $tfvarsContent
    
    # Initialize Terraform
    Write-InfoMessage "Initializing Terraform..."
    & terraform init
    
    # Plan
    Write-InfoMessage "Running Terraform plan..."
    & terraform plan -var-file=$tfvarsFile -out=tfplan
    
    # Apply
    Write-InfoMessage "Applying Terraform configuration..."
    $response = Read-Host "Do you want to proceed with deployment? (yes/no)"
    
    if ($response -eq "yes") {
        & terraform apply tfplan
        Write-SuccessMessage "Deployment completed!"
        
        # Get outputs
        Write-InfoMessage "Deployment outputs:"
        & terraform output -json | ConvertFrom-Json | ConvertTo-Json
        
        # Extract Cloud Run URL
        try {
            $cloudRunUrl = & terraform output -raw cloud_run_url 2>$null
            if ($cloudRunUrl) {
                Write-SuccessMessage "Cloud Run URL: $cloudRunUrl"
                
                # Test the deployment
                Write-InfoMessage "Testing deployment (waiting for service to be ready)..."
                for ($i = 1; $i -le 30; $i++) {
                    try {
                        $response = Invoke-WebRequest -Uri "$cloudRunUrl/health" -ErrorAction SilentlyContinue
                        Write-SuccessMessage "Service is healthy!"
                        break
                    } catch {
                        Write-InfoMessage "Attempt $i/30: Waiting for service to be ready..."
                        Start-Sleep -Seconds 10
                    }
                }
            }
        } catch {
            Write-WarningMessage "Could not extract Cloud Run URL"
        }
    } else {
        Write-WarningMessage "Deployment cancelled"
        Pop-Location
        exit 1
    }
    
    Pop-Location
} else {
    Write-WarningMessage "Skipping Terraform deployment"
    Write-InfoMessage "To deploy, run with -Deploy flag"
}

Write-SuccessMessage "Deployment process completed!"
