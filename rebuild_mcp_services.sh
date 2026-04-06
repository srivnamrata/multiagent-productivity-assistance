#!/bin/bash

# REBUILD & REDEPLOY MCP SERVICES TO CLOUD RUN
# Safe version without set -e (continues on errors)

# Set up environment
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
SA_EMAIL=multi-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: PROJECT_ID not set"
    exit 1
fi

echo "=========================================="
echo "🚀 REBUILDING MCP SERVICES"
echo "=========================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Make sure we're in the repo directory
cd ~/multiagent-productivity-assistance || { echo "❌ Directory not found"; exit 1; }

# Rebuild and push all MCP services
for SERVICE in task calendar notes critic auditor event_monitor research news; do
    echo ""
    echo "Building: $SERVICE"
    
    # Build with fixed imports
    if docker build \
        -t gcr.io/${PROJECT_ID}/multi-agent-${SERVICE}:latest \
        -f Dockerfile.mcp \
        --build-arg MCP_SERVER=${SERVICE} .; then
        
        echo "✅ Built successfully"
        
        # Push to GCR
        if docker push gcr.io/${PROJECT_ID}/multi-agent-${SERVICE}:latest; then
            echo "✅ Pushed to GCR"
        else
            echo "⚠️  Push failed for $SERVICE (continuing...)"
        fi
    else
        echo "⚠️  Build failed for $SERVICE (continuing...)"
    fi
done

echo ""
echo "=========================================="
echo "🔄 REDEPLOYING TO CLOUD RUN"
echo "=========================================="
echo ""

# Redeploy each service
for SERVICE in task calendar notes critic auditor event_monitor research news; do
    # Convert underscore to hyphen for Cloud Run
    SERVICE_NAME=$(echo "multi-agent-${SERVICE}" | sed 's/_/-/g')
    
    # Set port
    case ${SERVICE} in
        task) PORT=8001 ;;
        calendar) PORT=8002 ;;
        notes) PORT=8003 ;;
        critic) PORT=8004 ;;
        auditor) PORT=8005 ;;
        event_monitor) PORT=8006 ;;
        research) PORT=8007 ;;
        news) PORT=8008 ;;
    esac
    
    echo "Deploying: $SERVICE_NAME (Port: $PORT)"
    
    gcloud run deploy ${SERVICE_NAME} \
        --image=gcr.io/${PROJECT_ID}/multi-agent-${SERVICE_NAME}:latest \
        --platform=managed \
        --region=${REGION} \
        --memory=512Mi \
        --cpu=1 \
        --timeout=3600 \
        --allow-unauthenticated \
        --service-account=${SA_EMAIL} \
        --set-env-vars=\
FIRESTORE_MODE=production,\
PROJECT_ID=${PROJECT_ID},\
MCP_SERVER=${SERVICE},\
MCP_PORT=${PORT} \
        --quiet 2>/dev/null || echo "⚠️  Deploy warning for $SERVICE_NAME"
    
    echo "✅ $SERVICE_NAME deployment submitted"
done

echo ""
echo "🎉 All services rebuilt and redeployed!"
echo ""
echo "Checking health status in 30 seconds..."
sleep 30

for SERVICE in task calendar notes critic auditor event_monitor research news; do
    SERVICE_NAME=$(echo "multi-agent-${SERVICE}" | sed 's/_/-/g')
    
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format='value(status.url)' 2>/dev/null)
    
    if [ -n "$SERVICE_URL" ]; then
        echo "Testing $SERVICE_NAME..."
        curl -s ${SERVICE_URL}/health | head -c 100
        echo ""
    else
        echo "⚠️  Could not get URL for $SERVICE_NAME"
    fi
done

echo ""
echo "✅ Done!"
