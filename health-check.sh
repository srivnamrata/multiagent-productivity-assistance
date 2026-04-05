#!/bin/bash

# Multi-Agent System - Health Check and Monitoring Script
# Monitors deployment health and provides diagnostics

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATOR_URL="${1:-http://localhost:8000}"
SERVICES=(
    "orchestrator:8000"
    "task:8001"
    "calendar:8002"
    "notes:8003"
    "critic:8004"
    "auditor:8005"
    "event-monitor:8006"
)

TIMEOUT=5
CHECK_INTERVAL=30
RETRY_COUNT=3

# Function to print headers
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check service health
check_service_health() {
    local service=$1
    local port=$2
    local url="http://$service:$port/health"
    
    for attempt in $(seq 1 $RETRY_COUNT); do
        if curl -s --max-time $TIMEOUT "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service (port $port)${NC} - Healthy"
            return 0
        fi
        
        if [ $attempt -lt $RETRY_COUNT ]; then
            sleep 2
        fi
    done
    
    echo -e "${RED}❌ $service (port $port)${NC} - Unhealthy"
    return 1
}

# Function to check service response time
check_service_latency() {
    local service=$1
    local port=$2
    local url="http://$service:$port/health"
    
    response_time=$(curl -s -w "%{time_total}" -o /dev/null --max-time $TIMEOUT "$url" 2>/dev/null || echo "N/A")
    
    if [ "$response_time" = "N/A" ]; then
        echo -e "${RED}  Latency: N/A (Timeout)${NC}"
    else
        # Convert to milliseconds
        latency_ms=$(echo "$response_time * 1000" | bc)
        
        if (( $(echo "$latency_ms < 100" | bc -l) )); then
            echo -e "${GREEN}  Latency: ${latency_ms}ms (Excellent)${NC}"
        elif (( $(echo "$latency_ms < 500" | bc -l) )); then
            echo -e "${YELLOW}  Latency: ${latency_ms}ms (Good)${NC}"
        else
            echo -e "${RED}  Latency: ${latency_ms}ms (Poor)${NC}"
        fi
    fi
}

# Function to get service info
get_service_info() {
    local service=$1
    local port=$2
    
    echo -e "${YELLOW}Service: $service (Port $port)${NC}"
    check_service_health "$service" "$port"
    check_service_latency "$service" "$port"
    echo ""
}

# Function to check orchestrator endpoints
check_endpoints() {
    print_header "Checking API Endpoints"
    
    endpoints=(
        "/health"
        "/ready"
        "/tasks"
        "/events"
        "/notes"
    )
    
    for endpoint in "${endpoints[@]}"; do
        url="$ORCHESTRATOR_URL$endpoint"
        status=$(curl -s -w "%{http_code}" -o /dev/null --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
        
        if [ "$status" = "200" ] || [ "$status" = "302" ]; then
            echo -e "${GREEN}✅ $endpoint${NC} - Status: $status"
        else
            echo -e "${RED}❌ $endpoint${NC} - Status: $status"
        fi
    done
    echo ""
}

# Function to get container stats (Docker)
check_container_stats() {
    print_header "Container Statistics (Docker)"
    
    if ! command -v docker &> /dev/null; then
        echo "Docker not installed or not running"
        return
    fi
    
    containers=(
        "multi-agent-productivity-orchestrator-1"
        "multi-agent-productivity-task-mcp-1"
        "multi-agent-productivity-calendar-mcp-1"
        "multi-agent-productivity-notes-mcp-1"
        "multi-agent-productivity-critic-mcp-1"
        "multi-agent-productivity-auditor-mcp-1"
        "multi-agent-productivity-event_monitor-mcp-1"
    )
    
    for container in "${containers[@]}"; do
        if docker inspect "$container" > /dev/null 2>&1; then
            status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            
            if [ "$status" = "running" ]; then
                cpu=$(docker stats --no-stream --format "{{.CPUPerc}}" "$container" 2>/dev/null || echo "N/A")
                memory=$(docker stats --no-stream --format "{{.MemUsage}}" "$container" 2>/dev/null || echo "N/A")
                echo -e "${GREEN}✅ $container${NC}"
                echo "   Status: $status | CPU: $cpu | Memory: $memory"
            else
                echo -e "${YELLOW}⚠️  $container${NC}"
                echo "   Status: $status"
            fi
        else
            echo -e "${RED}❌ $container${NC} - Not found"
        fi
    done
    echo ""
}

# Function to get system metrics
check_system_metrics() {
    print_header "System Metrics"
    
    echo "System Memory Usage:"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        free -h | head -2 | tail -1
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        vm_stat | head -1
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /value
    fi
    
    echo ""
    echo "Disk Usage:"
    df -h / | tail -1
    echo ""
}

# Function to run continuous monitoring
continuous_monitoring() {
    print_header "Continuous Monitoring (Press Ctrl+C to stop)"
    
    iteration=1
    while true; do
        clear
        echo "Multi-Agent Productivity System - Health Monitor"
        echo "Iteration: $iteration | Last check: $(date)"
        echo ""
        
        for service_info in "${SERVICES[@]}"; do
            IFS=':' read -r service port <<< "$service_info"
            get_service_info "$service" "$port"
        done
        
        echo -e "${YELLOW}Next check in $CHECK_INTERVAL seconds...${NC}"
        sleep $CHECK_INTERVAL
        ((iteration++))
    done
}

# Main execution
main() {
    print_header "Multi-Agent Productivity System - Health Check"
    
    echo "Starting health checks at $(date)"
    echo "Orchestrator URL: $ORCHESTRATOR_URL"
    echo ""
    
    # Run checks
    for service_info in "${SERVICES[@]}"; do
        IFS=':' read -r service port <<< "$service_info"
        get_service_info "$service" "$port"
    done
    
    check_endpoints
    check_container_stats
    check_system_metrics
    
    # Summary
    print_header "Summary"
    echo "All checks completed at $(date)"
    echo ""
    echo "To run continuous monitoring, use:"
    echo "  ./health-check.sh -m"
    echo ""
    echo "To specify orchestrator URL, use:"
    echo "  ./health-check.sh http://your-orchestrator-url:8000"
}

# Parse command line arguments
if [ "$1" = "-m" ] || [ "$1" = "--monitor" ]; then
    continuous_monitoring
else
    main
fi
