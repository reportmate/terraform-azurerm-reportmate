#!/usr/bin/env bash
set -euo pipefail

################################################################################
# DEPRECATED - USE CI/CD PIPELINE INSTEAD
################################################################################
# This script is DEPRECATED. Use the Azure DevOps pipeline instead:
# 
#   pipelines/reportmate-deploy-infra.yml
# 
# The pipeline provides:
#   - Terraform as single source of truth
#   - Image tag variables passed to infrastructure
#   - Proper CI/CD with approval gates
#   - Audit trail of all deployments
# 
# This script is kept ONLY for emergency manual deployments.
################################################################################
#
# SYNOPSIS
#     [DEPRECATED] Deploy ReportMate FastAPI Container - Use CI/CD pipeline instead.
#     
# DESCRIPTION
#     Deploys the FastAPI container to Azure Container Apps with critical device ID standardization.
#     
#     DEPRECATED: This script is replaced by pipelines/reportmate-deploy-infra.yml
#     
#     🚨 CRITICAL FIXES IN THIS VERSION:
#     - API code moved to proper infrastructure location (modules/api)
#     - Device ID alignment standardized on serialNumber (UUIDs deprecated)
#     - No more UUID confusion throughout stack
#     - Database queries use serial_number consistently
#
# PARAMETERS
#     -e, --environment ENV    Target environment (prod, dev) [default: prod]
#     -s, --skip-build         Skip Docker build (use existing image)
#     -t, --tag TAG            Custom image tag (will auto-generate if not provided)
#     -f, --force-build        Force rebuild even if image exists
#     -h, --help               Show this help message
#
# EXAMPLES
#     ./deploy-api.sh
#     # Deploy API with device ID alignment fix
#     
#     ./deploy-api.sh --environment dev
#     # Deploy to dev environment
#     
#     ./deploy-api.sh --skip-build --tag "device-id-fix-v1"
#     # Deploy without rebuilding using specific tag
################################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

write_status() {
    echo -e "${BLUE}[INFO]${RESET} $1"
}

write_success() {
    echo -e "${GREEN}[SUCCESS]${RESET} $1"
}

write_warning() {
    echo -e "${YELLOW}[WARNING]${RESET} $1"
}

write_error() {
    echo -e "${RED}[ERROR]${RESET} $1"
}

show_help() {
    sed -n '/^# SYNOPSIS/,/^################################################################################$/p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Default values
ENVIRONMENT="prod"
SKIP_BUILD=false
TAG=""
FORCE_BUILD=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -f|--force-build)
            FORCE_BUILD=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            write_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(prod|dev)$ ]]; then
    write_error "Invalid environment: $ENVIRONMENT (must be prod or dev)"
    exit 1
fi

write_status "ReportMate API Container Deployment"
write_status "DEVICE ID ALIGNMENT FIX - Version 2.1.0"
write_status "API code now in proper location: infrastructure/modules/api"
echo ""

# Configuration
REGISTRY_NAME="reportmateacr"
IMAGE_NAME="reportmate-api"
CONTAINER_APP_NAME="reportmate-functions-api"
RESOURCE_GROUP="ReportMate"
API_SOURCE_PATH="./modules/api"

# Generate tag if not provided
if [ -z "$TAG" ]; then
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    TAG="device-id-fix-$TIMESTAMP-$GIT_HASH"
fi

FULL_IMAGE_NAME="$REGISTRY_NAME.azurecr.io/$IMAGE_NAME:$TAG"

write_status "Configuration:"
write_status "  Environment: $ENVIRONMENT"
write_status "  Image: $FULL_IMAGE_NAME"
write_status "  Container App: $CONTAINER_APP_NAME"
write_status "  API Source: $API_SOURCE_PATH"
echo ""

# Get script directory and change to infrastructure root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Validate API source exists
if [ ! -f "$INFRA_DIR/modules/api/main.py" ]; then
    write_error "API source not found at: $INFRA_DIR/modules/api/main.py"
    write_error "Script location: $SCRIPT_DIR"
    write_error "Infrastructure directory: $INFRA_DIR"
    exit 1
fi

write_success "API source found at correct location: modules/api/main.py"

# Change to infrastructure directory
cd "$INFRA_DIR"

if [ "$SKIP_BUILD" = false ]; then
    # Authenticate to ACR first
    echo -e "\n${BLUE}Authenticating to Azure Container Registry...${RESET}"
    if ! az acr login --name "$REGISTRY_NAME"; then
        write_error "ACR authentication failed. Run 'az login' first if needed."
        exit 1
    fi
    write_success "ACR authentication successful"
    
    echo -e "\n${BLUE}Building Docker image...${RESET}"
    write_status "  Image: $FULL_IMAGE_NAME"
    
    # Build the Docker image
    BUILD_ARGS=(
        "build"
        "--platform" "linux/amd64"
    )
    
    if [ "$FORCE_BUILD" = true ]; then
        BUILD_ARGS+=("--no-cache")
    fi
    
    BUILD_ARGS+=(
        "-t" "$FULL_IMAGE_NAME"
        "-f" "modules/api/Dockerfile"
        "modules/api"
    )
    
    if ! docker "${BUILD_ARGS[@]}"; then
        write_error "Docker build failed"
        exit 1
    fi
    
    write_success "Docker image built successfully"
    
    # Push to Azure Container Registry
    echo -e "\n${BLUE}Pushing image to ACR...${RESET}"
    if ! docker push "$FULL_IMAGE_NAME"; then
        write_error "Docker push failed"
        exit 1
    fi
    
    write_success "Image pushed to ACR"
    
    # Update container app with new image
    echo -e "\n${BLUE}Updating container app...${RESET}"
    
    # Read existing env vars from the live container so they are preserved.
    # az containerapp update --image replaces the entire container spec,
    # which can reset env vars that were set outside Terraform.
    write_status "Reading existing environment variables from container..."
    EXISTING_SECRET=$(az containerapp show \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.template.containers[0].env[?name=='API_INTERNAL_SECRET'].value | [0]" \
        -o tsv 2>/dev/null)
    EXISTING_PASSPHRASE=$(az containerapp show \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.template.containers[0].env[?name=='REPORTMATE_PASSPHRASE'].value | [0]" \
        -o tsv 2>/dev/null)
    
    if [ -z "$EXISTING_SECRET" ] || [ "$EXISTING_SECRET" = "None" ]; then
        write_error "API_INTERNAL_SECRET is not set on the running container."
        write_error "Set it first via Terraform (terraform apply) or manually:"
        write_error "  az containerapp update --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --set-env-vars API_INTERNAL_SECRET=<value>"
        exit 1
    fi
    
    if [ -z "$EXISTING_PASSPHRASE" ] || [ "$EXISTING_PASSPHRASE" = "None" ]; then
        write_error "REPORTMATE_PASSPHRASE is not set on the running container."
        exit 1
    fi
    
    write_success "Existing secrets read from live container (not hardcoded)"
    
    REVISION=$(az containerapp update \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$FULL_IMAGE_NAME" \
        --set-env-vars \
            "API_INTERNAL_SECRET=$EXISTING_SECRET" \
            "REPORTMATE_PASSPHRASE=$EXISTING_PASSPHRASE" \
        --query "properties.latestRevisionName" \
        -o tsv)
    
    if [ $? -ne 0 ]; then
        write_error "Container app update failed"
        exit 1
    fi
    
    write_success "Container app updated to revision: $REVISION"
else
    write_warning "Skipping Docker build (using existing image: $FULL_IMAGE_NAME)"
fi

# Test API health
echo -e "\n${BLUE}Testing API health...${RESET}"
API_URL="https://$CONTAINER_APP_NAME.blackdune-79551938.canadacentral.azurecontainerapps.io"

sleep 10  # Give container time to start

if curl -sf "$API_URL/api/health" > /dev/null; then
    write_success "API health check passed"
    echo -e "${BLUE}API URL: $API_URL${RESET}"
else
    write_warning "API health check failed, but deployment completed"
    echo -e "${YELLOW}   Try: curl $API_URL/api/health${RESET}"
fi

write_success "Deployment completed successfully"
