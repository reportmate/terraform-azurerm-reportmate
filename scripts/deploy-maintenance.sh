#!/usr/bin/env bash
set -euo pipefail

################################################################################
# SYNOPSIS
#     Build and deploy ReportMate database maintenance container
#
# DESCRIPTION
#     Builds the maintenance container image, pushes to ACR, and optionally 
#     triggers a manual test run.
#
# PARAMETERS
#     -s, --skip-build     Skip building the container image (use existing image)
#     -p, --skip-push      Skip pushing to ACR (test build only)
#     -r, --test-run       Trigger a manual test execution after deployment
#     -t, --tag TAG        Custom image tag [default: latest]
#     -h, --help           Show this help message
#
# EXAMPLES
#     ./deploy-maintenance.sh
#     Build, push, and deploy maintenance container
#
#     ./deploy-maintenance.sh --test-run
#     Deploy and trigger manual test execution
#
#     ./deploy-maintenance.sh --skip-build --test-run
#     Use existing image and test
################################################################################

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
GRAY='\033[0;37m'
WHITE='\033[1;37m'
RESET='\033[0m'

show_help() {
    sed -n '/^# SYNOPSIS/,/^################################################################################$/p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Default values
SKIP_BUILD=false
SKIP_PUSH=false
TEST_RUN=false
TAG="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -p|--skip-push)
            SKIP_PUSH=true
            shift
            ;;
        -r|--test-run)
            TEST_RUN=true
            shift
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${RESET}"
            show_help
            ;;
    esac
done

# Configuration
ACR_NAME="reportmateacr"
IMAGE_NAME="reportmate-maintenance"
RESOURCE_GROUP="ReportMate"
JOB_NAME="reportmate-db-maintenance"

echo -e "${CYAN}========================================${RESET}"
echo -e "${CYAN}ReportMate Maintenance Container Deploy${RESET}"
echo -e "${CYAN}========================================${RESET}\n"

# Change to maintenance module directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AZURE_INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MAINTENANCE_MODULE_DIR="$AZURE_INFRA_DIR/modules/maintenance"

if [ ! -d "$MAINTENANCE_MODULE_DIR" ]; then
    echo -e "${RED}ERROR: Maintenance module directory not found at: $MAINTENANCE_MODULE_DIR${RESET}"
    echo -e "${RED}Script dir: $SCRIPT_DIR${RESET}"
    echo -e "${RED}Azure infra dir: $AZURE_INFRA_DIR${RESET}"
    exit 1
fi

cd "$MAINTENANCE_MODULE_DIR"

# Verify Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}ERROR: Azure CLI not found. Please install: https://aka.ms/InstallAzureCLIDirect${RESET}"
    exit 1
fi

# Verify Docker is running
if [ "$SKIP_BUILD" = false ] && ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found. Please install Docker Desktop.${RESET}"
    exit 1
fi

# Check Azure login
echo -e "${YELLOW}Checking Azure authentication...${RESET}"
ACCOUNT_JSON=$(az account show 2>/dev/null || echo "")
if [ -z "$ACCOUNT_JSON" ]; then
    echo -e "${RED}ERROR: Not logged in to Azure. Run: az login${RESET}"
    exit 1
fi

ACCOUNT_USER=$(echo "$ACCOUNT_JSON" | jq -r '.user.name')
ACCOUNT_NAME=$(echo "$ACCOUNT_JSON" | jq -r '.name')
echo -e "  ${GREEN}Logged in as: $ACCOUNT_USER${RESET}"
echo -e "  ${GREEN}Subscription: $ACCOUNT_NAME${RESET}\n"

# Build container image
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${YELLOW}Building container image...${RESET}"
    
    IMAGE_FULL="$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"
    
    if ! docker build -t "$IMAGE_FULL" . --no-cache; then
        echo -e "${RED}ERROR: Docker build failed${RESET}"
        exit 1
    fi
    
    echo -e "  ${GREEN}Built: $IMAGE_FULL${RESET}\n"
else
    echo -e "${YELLOW}Skipping build (using existing image)${RESET}\n"
fi

# Push to ACR
if [ "$SKIP_PUSH" = false ]; then
    echo -e "${YELLOW}Logging in to Azure Container Registry...${RESET}"
    if ! az acr login --name "$ACR_NAME"; then
        echo -e "${RED}ERROR: ACR login failed${RESET}"
        exit 1
    fi
    
    echo -e "  ${GREEN}Logged in to $ACR_NAME.azurecr.io${RESET}\n"

    echo -e "${YELLOW}Pushing image to ACR...${RESET}"
    IMAGE_FULL="$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"
    
    if ! docker push "$IMAGE_FULL"; then
        echo -e "${RED}ERROR: Docker push failed${RESET}"
        exit 1
    fi
    
    echo -e "  ${GREEN}Pushed: $IMAGE_FULL${RESET}\n"
else
    echo -e "${YELLOW}Skipping push to ACR${RESET}\n"
fi

# Verify job exists
echo -e "${YELLOW}Verifying Container App Job...${RESET}"
JOB_JSON=$(az containerapp job show \
    --name "$JOB_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    2>/dev/null || echo "")

if [ -z "$JOB_JSON" ]; then
    echo -e "  ${RED}Job not found. Run terraform apply to create it.${RESET}"
    echo -e "\n${YELLOW}To create the job:${RESET}"
    echo -e "  ${GRAY}cd ../../${RESET}"
    echo -e "  ${GRAY}terraform init${RESET}"
    echo -e "  ${GRAY}terraform apply${RESET}\n"
    JOB_EXISTS=false
else
    JOB_NAME_FOUND=$(echo "$JOB_JSON" | jq -r '.name')
    SCHEDULE=$(echo "$JOB_JSON" | jq -r '.properties.configuration.scheduleTriggerConfig.cronExpression // "N/A"')
    echo -e "  ${GREEN}Job found: $JOB_NAME_FOUND${RESET}"
    echo -e "  ${GREEN}Schedule: $SCHEDULE${RESET}\n"
    JOB_EXISTS=true
fi

# Trigger test run
if [ "$TEST_RUN" = true ]; then
    if [ "$JOB_EXISTS" = false ]; then
        echo -e "${RED}ERROR: Cannot run test - job does not exist${RESET}"
        exit 1
    fi

    echo -e "${YELLOW}Triggering manual test execution...${RESET}"
    
    EXECUTION_JSON=$(az containerapp job start \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --output json)
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Failed to start job execution${RESET}"
        exit 1
    fi
    
    EXECUTION_NAME=$(echo "$EXECUTION_JSON" | jq -r '.name')
    echo -e "  ${GREEN}Started: $EXECUTION_NAME${RESET}"
    echo -e "\n${YELLOW}Waiting for execution to complete...${RESET}"
    
    # Wait for completion (max 5 minutes)
    TIMEOUT=300
    ELAPSED=0
    INTERVAL=5
    
    while [ $ELAPSED -lt $TIMEOUT ]; do
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
        
        STATUS_JSON=$(az containerapp job execution show \
            --name "$JOB_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --job-execution-name "$EXECUTION_NAME" \
            --output json 2>/dev/null || echo "")
        
        if [ -n "$STATUS_JSON" ]; then
            STATUS=$(echo "$STATUS_JSON" | jq -r '.properties.status')
            
            if [ "$STATUS" = "Succeeded" ]; then
                echo -e "\n  ${GREEN}Execution completed successfully!${RESET}"
                break
            elif [ "$STATUS" = "Failed" ]; then
                echo -e "\n  ${RED}Execution failed!${RESET}"
                break
            fi
        fi
        
        echo -n "."
    done
    
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo -e "\n  ${YELLOW}Execution timed out after $TIMEOUT seconds${RESET}"
    fi
    
    echo -e "\n${YELLOW}Fetching logs...${RESET}"
    echo -e "${GRAY}========================================${RESET}\n"
    
    az containerapp job logs show \
        --name "$JOB_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --format text \
        2>/dev/null || true
    
    echo -e "\n${GRAY}========================================${RESET}"
fi

echo -e "\n${CYAN}Deployment Summary:${RESET}"
echo -e "  ${WHITE}Image: $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG${RESET}"
echo -e "  ${WHITE}Job: $JOB_NAME${RESET}"
echo -e "  ${WHITE}Resource Group: $RESOURCE_GROUP${RESET}"

if [ "$JOB_EXISTS" = true ]; then
    echo -e "  ${WHITE}Next scheduled run: (check Azure Portal)${RESET}"
fi

echo -e "\n${CYAN}Useful Commands:${RESET}"
echo -e "  ${GRAY}Manual run:  ${WHITE}az containerapp job start --name $JOB_NAME --resource-group $RESOURCE_GROUP${RESET}"
echo -e "  ${GRAY}View logs:   ${WHITE}az containerapp job logs show --name $JOB_NAME --resource-group $RESOURCE_GROUP --follow${RESET}"
echo -e "  ${GRAY}List runs:   ${WHITE}az containerapp job execution list --name $JOB_NAME --resource-group $RESOURCE_GROUP${RESET}"

echo -e "\n${GREEN}Done!${RESET}\n"
