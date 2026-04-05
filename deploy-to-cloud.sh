#!/bin/bash

# Deploy to Google Cloud Run
# Usage: ./deploy-to-cloud.sh [project-id] [region]

set -e

PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}
IMAGE_REGISTRY="gcr.io"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Multi-Agent Productivity System - Cloud Run Deployment${NC}"
echo -e "${YELLOW}================================================${NC}"

# Validate project ID
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: Project ID is required${NC}"
    echo "Usage: ./deploy-to-cloud.sh [project-id] [region]"
    exit 1
fi

# Validate region
case $REGION in
    us-central1|us-east1|us-west1|europe-west1|asia-northeast1)
        echo -e "${GREEN}✅ Region: $REGION${NC}"
        ;;
    *)
        echo -e "${YELLOW}⚠️  Warning: Non-standard region specified: $REGION${NC}"
        ;;
esac

# Set project
echo -e "${YELLOW}Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Build and push Docker images
echo -e "${YELLOW}📦 Building Docker images...${NC}"

# Build images for each service
SERVICES=("orchestrator" "task" "calendar" "notes" "critic" "auditor" "event_monitor" "research" "news")

for SERVICE in "${SERVICES[@]}"; do
    IMAGE_NAME="$IMAGE_REGISTRY/$PROJECT_ID/multi-agent-$SERVICE"
    TAG="latest"
    FULL_IMAGE="$IMAGE_NAME:$TAG"
    
    echo -e "${YELLOW}  Building: $SERVICE...${NC}"
    
    if [ "$SERVICE" == "orchestrator" ]; then
        docker build -t $FULL_IMAGE -f Dockerfile .
    else
        docker build \
            -t $FULL_IMAGE \
            -f Dockerfile.mcp \
            --build-arg MCP_SERVER=$SERVICE .
    fi
    
    echo -e "${GREEN}  ✅ Built: $FULL_IMAGE${NC}"
    
    # Push to Container Registry
    echo -e "${YELLOW}  Pushing to GCR...${NC}"
    docker push $FULL_IMAGE
    echo -e "${GREEN}  ✅ Pushed: $FULL_IMAGE${NC}"
done

# Deploy services to Cloud Run
echo -e "${YELLOW}🚀 Deploying services to Cloud Run...${NC}"

# Deploy Orchestrator
echo -e "${YELLOW}  Deploying Orchestrator...${NC}"
gcloud run deploy multi-agent-orchestrator \
    --image="$IMAGE_REGISTRY/$PROJECT_ID/multi-agent-orchestrator:latest" \
    --platform managed \
    --region $REGION \
    --memory 1Gi \
    --cpu 1 \
    --timeout 3600 \
    --allow-unauthenticated \
    --set-env-vars="FIRESTORE_MODE=production,PROJECT_ID=$PROJECT_ID,MCP_TASK_HOST=multi-agent-task,MCP_CALENDAR_HOST=multi-agent-calendar,MCP_NOTES_HOST=multi-agent-notes,MCP_CRITIC_HOST=multi-agent-critic,MCP_AUDITOR_HOST=multi-agent-auditor,MCP_EVENT_MONITOR_HOST=multi-agent-event-monitor,MCP_RESEARCH_HOST=multi-agent-research,MCP_NEWS_HOST=multi-agent-news"

echo -e "${GREEN}✅ Orchestrator deployed${NC}"

# Deploy MCP Servers
MCP_SERVICES=("task" "calendar" "notes" "critic" "auditor" "event_monitor" "research" "news")
PORTS=(8001 8002 8003 8004 8005 8006 8007 8008)

for i in "${!MCP_SERVICES[@]}"; do
    SERVICE="${MCP_SERVICES[$i]}"
    PORT="${PORTS[$i]}"
    
    echo -e "${YELLOW}  Deploying $SERVICE MCP Server...${NC}"
    
    gcloud run deploy multi-agent-$SERVICE \
        --image="$IMAGE_REGISTRY/$PROJECT_ID/multi-agent-$SERVICE:latest" \
        --platform managed \
        --region $REGION \
        --memory 512Mi \
        --cpu 0.5 \
        --timeout 1800 \
        --allow-unauthenticated \
        --set-env-vars="MCP_SERVER=$SERVICE,MCP_PORT=$PORT,FIRESTORE_MODE=production,PROJECT_ID=$PROJECT_ID" \
        --no-gen2
    
    echo -e "${GREEN}✅ $SERVICE MCP Server deployed${NC}"
done

# Create load balancer configuration
echo -e "${YELLOW}📋 Creating load balancer configuration...${NC}"

# Get service URLs
ORCHESTRATOR_URL=$(gcloud run services describe multi-agent-orchestrator --region=$REGION --format='value(status.url)')

echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${YELLOW}════════════════════════════════════${NC}"
echo -e "${GREEN}Orchestrator URL: $ORCHESTRATOR_URL${NC}"
echo -e "${YELLOW}════════════════════════════════════${NC}"

echo ""
echo "Next steps:"
echo "1. Test the system: curl $ORCHESTRATOR_URL/health"
echo "2. View logs: gcloud run logs read multi-agent-orchestrator"
echo "3. Scale services: gcloud run services update multi-agent-orchestrator --min-instances=1"
echo ""
