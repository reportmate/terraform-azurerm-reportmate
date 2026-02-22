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
#   - Automatic Front Door cache purge
# 
# This script is kept ONLY for emergency manual deployments.
################################################################################
#
# SYNOPSIS
#     [DEPRECATED] Deploy the ReportMate Next.js frontend - Use CI/CD pipeline instead.
#
# DESCRIPTION
#     DEPRECATED: This script is replaced by pipelines/reportmate-deploy-infra.yml
#     
#     Builds (optionally forced) and deploys the ReportMate frontend container, updates environment
#     variables to keep build metadata accurate, and purges Azure Front Door so users always see the
#     latest UI.
#
# PARAMETERS
#     -e, --environment ENV    Target environment (prod) [default: prod]
#     -f, --force-build        Force rebuild without Docker cache
#     -s, --skip-build         Skip Docker build/push and only update container
#     -t, --tag TAG            Custom image tag (auto-generated if not provided)
#     -p, --purge-only         Only purge Azure Front Door cache
#     -h, --help               Show this help message
#
# EXAMPLES
#     ./deploy-app.sh
#     # Standard deployment using Docker layer cache
#
#     ./deploy-app.sh --force-build
#     # Rebuild from scratch (no Docker cache) and deploy
#
#     ./deploy-app.sh --skip-build
#     # Re-use the existing image but resync environment variables and purge CDN
#
#     ./deploy-app.sh --purge-only
#     # Only purge the Front Door cache, no build or deploy
################################################################################

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'

write_section() {
    echo -e "\n${CYAN}$1${RESET}"
}

write_info() {
    echo -e "   ${CYAN}$1${RESET}"
}

write_success() {
    echo -e "   ${GREEN}$1${RESET}"
}

write_warning() {
    echo -e "   ${YELLOW}$1${RESET}"
}

write_error() {
    echo -e "   ${RED}$1${RESET}"
}

show_help() {
    sed -n '/^# SYNOPSIS/,/^################################################################################$/p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Default values
ENVIRONMENT="prod"
FORCE_BUILD=false
SKIP_BUILD=false
TAG=""
AUTO_SSO=false
PURGE_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -f|--force-build)
            FORCE_BUILD=true
            shift
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--purge-only)
            PURGE_ONLY=true
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
if [[ ! "$ENVIRONMENT" =~ ^(prod)$ ]]; then
    write_error "Invalid environment: $ENVIRONMENT (must be prod)"
    exit 1
fi

# Configuration based on environment
RESOURCE_GROUP="ReportMate"
CONTAINER_APP="reportmate-web-app-prod"
REGISTRY_HOST="reportmateacr.azurecr.io"
IMAGE_NAME="reportmate"
DOMAIN="reportmate.ecuad.ca"
API_BASE_URL="http://reportmate-functions-api"
PUBLIC_API_BASE_URL="https://reportmate-functions-api.blackdune-79551938.canadacentral.azurecontainerapps.io"
FRONT_DOOR_PROFILE="reportmate-frontdoor"
FRONT_DOOR_ENDPOINT="reportmate-endpoint"

REGISTRY_NAME="${REGISTRY_HOST%%.*}"

# Resolve directory structure
# Script is in infrastructure/azure/scripts, need to go up 3 levels to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AZURE_INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$(cd "$AZURE_INFRA_DIR/.." && pwd)"
REPO_ROOT="$(cd "$INFRA_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/apps/www"

if [ ! -d "$FRONTEND_DIR" ]; then
    write_error "Unable to locate frontend directory at '$FRONTEND_DIR'."
    write_error "Script dir: $SCRIPT_DIR"
    write_error "Azure infra dir: $AZURE_INFRA_DIR"
    write_error "Infra dir: $INFRA_DIR"
    write_error "Repo root: $REPO_ROOT"
    exit 1
fi

# PurgeOnly fast path
if [ "$PURGE_ONLY" = true ]; then
    write_section "🗑️  Purging Azure Front Door cache (purge-only mode)..."
    
    az afd endpoint purge \
        --resource-group "$RESOURCE_GROUP" \
        --profile-name "$FRONT_DOOR_PROFILE" \
        --endpoint-name "$FRONT_DOOR_ENDPOINT" \
        --content-paths "/*" \
        --domains "$DOMAIN" \
        --no-wait \
        --output none 2>&1 || true

    if [ $? -eq 0 ]; then
        write_success "Front Door cache purge triggered (async)"
        write_info "Domain: https://$DOMAIN"
    else
        write_error "Front Door purge command failed"
    fi
    exit $?
fi

# Capture git hash from submodule first (before generating tag)
pushd "$FRONTEND_DIR" > /dev/null
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
popd > /dev/null

if [ -z "$TAG" ]; then
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    TAG="$TIMESTAMP-$GIT_HASH"
fi

BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
FULL_IMAGE="$REGISTRY_HOST/$IMAGE_NAME:$TAG"

write_section "Frontend Container Deployment Configuration:"
write_info "Environment: $ENVIRONMENT"
write_info "Target Container: $CONTAINER_APP"
write_info "Registry: $REGISTRY_HOST"
write_info "Image Name: $IMAGE_NAME"
write_info "Tag: $TAG"
write_info "Force Build: $FORCE_BUILD"
write_info "Skip Build: $SKIP_BUILD"
write_info "Auto SSO: $AUTO_SSO"
write_info "Build Directory: $FRONTEND_DIR"
write_info "API Base URL (internal): $API_BASE_URL"
write_info "API Base URL (public): $PUBLIC_API_BASE_URL"
write_info "SignalR Enabled: true (build-time)"

# Prerequisite validation
write_section "Validating prerequisites..."

if ! command -v docker &> /dev/null; then
    write_error "Docker CLI is not installed. Install Docker Desktop and retry."
    exit 1
fi

if ! docker info &> /dev/null; then
    write_warning "Docker daemon not running. Attempting to start Docker Desktop..."
    open -a Docker
    write_info "Waiting for Docker daemon to start (up to 60 seconds)..."
    for i in $(seq 1 12); do
        sleep 5
        if docker info &> /dev/null; then
            break
        fi
        if [ "$i" -eq 12 ]; then
            write_error "Docker daemon did not start within 60 seconds. Start Docker Desktop manually and retry."
            exit 1
        fi
        write_info "Still waiting... (${i}/12)"
    done
fi

write_success "Docker daemon available"

if ! az account show &> /dev/null; then
    write_error "Not logged into Azure CLI. Run 'az login' before deploying."
    exit 1
fi

ACCOUNT_INFO=$(az account show --output json)
ACCOUNT_USER=$(echo "$ACCOUNT_INFO" | jq -r '.user.name')
write_success "Azure CLI authenticated as $ACCOUNT_USER"

# Load current container metadata
CONTAINER_JSON=$(az containerapp show \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --output json)

if [ $? -ne 0 ]; then
    write_error "Failed to fetch container app '$CONTAINER_APP'. Ensure it exists and you have permissions."
    exit 1
fi

CURRENT_IMAGE=$(echo "$CONTAINER_JSON" | jq -r '.properties.template.containers[0].image')
EXISTING_ENV=$(echo "$CONTAINER_JSON" | jq -r '.properties.template.containers[0].env')

if [ "$SKIP_BUILD" = true ] && [ -z "$TAG" ]; then
    TAG=$(echo "$CURRENT_IMAGE" | grep -oP '(?<=:)[^:]+$' || echo "")
    if [ -z "$TAG" ]; then
        write_error "Unable to infer currently deployed image tag; specify -t/--tag when using --skip-build."
        exit 1
    fi
    write_warning "SkipBuild requested without tag - reusing deployed tag '$TAG'."
    FULL_IMAGE="$REGISTRY_HOST/$IMAGE_NAME:$TAG"
fi

write_info "Resolved image reference: $FULL_IMAGE"

# Docker build & push
if [ "$SKIP_BUILD" = false ]; then
    write_section "Authenticating and building image..."
    
    az acr login --name "$REGISTRY_NAME" > /dev/null
    if [ $? -ne 0 ]; then
        write_error "ACR authentication failed for '$REGISTRY_NAME'."
        exit 1
    fi
    write_success "Authenticated to Azure Container Registry"

    pushd "$FRONTEND_DIR" > /dev/null
    
    BUILD_ARGS=(
        "build"
        "--platform" "linux/amd64"
        "--build-arg" "IMAGE_TAG=$TAG"
        "--build-arg" "BUILD_TIME=$BUILD_TIME"
        "--build-arg" "BUILD_ID=$GIT_HASH"
        "--build-arg" "ENABLE_SIGNALR=true"
        "--build-arg" "API_BASE_URL=$API_BASE_URL"
        "--build-arg" "NEXT_PUBLIC_API_BASE_URL=$PUBLIC_API_BASE_URL"
    )

    if [ "$FORCE_BUILD" = true ]; then
        BUILD_ARGS+=("--no-cache" "--pull")
    fi

    BUILD_ARGS+=("-t" "$FULL_IMAGE" "-f" "Dockerfile" ".")

    write_info "Building Docker image (force build: $FORCE_BUILD)..."
    if ! docker "${BUILD_ARGS[@]}"; then
        write_error "Docker build failed."
        exit 1
    fi
    write_success "Image built successfully"

    write_info "Pushing image to $REGISTRY_HOST..."
    if ! docker push "$FULL_IMAGE"; then
        write_error "Docker push failed."
        exit 1
    fi
    write_success "Image pushed to registry"
    
    popd > /dev/null
else
    write_section "Skipping Docker build/push per request"
fi

# Environment variable reconciliation
write_section "Updating container configuration..."

declare -a ENV_PAIRS=()

# Keys to replace (not preserve from existing env)
KEYS_TO_SKIP="CONTAINER_IMAGE_TAG BUILD_TIME BUILD_ID API_BASE_URL API_INTERNAL_SECRET NEXT_PUBLIC_API_BASE_URL NEXT_PUBLIC_VERSION NEXT_PUBLIC_BUILD_ID NEXT_PUBLIC_BUILD_TIME"

# Parse existing environment variables
SEEN_KEYS_STRING=" "
if [ "$EXISTING_ENV" != "null" ] && [ "$EXISTING_ENV" != "[]" ]; then
    while IFS= read -r env_item; do
        ENV_NAME=$(echo "$env_item" | jq -r '.name // empty')
        [ -z "$ENV_NAME" ] && continue
        # Check if key should be skipped (will be replaced)
        if echo " $KEYS_TO_SKIP " | grep -q " $ENV_NAME "; then
            continue
        fi
        # Check if key already seen
        if echo "$SEEN_KEYS_STRING" | grep -q " $ENV_NAME "; then
            continue
        fi
        SEEN_KEYS_STRING="$SEEN_KEYS_STRING$ENV_NAME "
        
        SECRET_REF=$(echo "$env_item" | jq -r '.secretRef // empty')
        if [ -n "$SECRET_REF" ]; then
            ENV_PAIRS+=("$ENV_NAME=secretref:$SECRET_REF")
        else
            ENV_VALUE=$(echo "$env_item" | jq -r '.value // empty')
            [ -n "$ENV_VALUE" ] && ENV_PAIRS+=("$ENV_NAME=$ENV_VALUE")
        fi
    done < <(echo "$EXISTING_ENV" | jq -c '.[]')
fi

# Add/update required environment variables
ENV_PAIRS+=("CONTAINER_IMAGE_TAG=$TAG")
ENV_PAIRS+=("BUILD_TIME=$BUILD_TIME")
ENV_PAIRS+=("BUILD_ID=$GIT_HASH")
ENV_PAIRS+=("NEXT_PUBLIC_VERSION=$TAG")
ENV_PAIRS+=("NEXT_PUBLIC_BUILD_ID=$GIT_HASH")
ENV_PAIRS+=("NEXT_PUBLIC_BUILD_TIME=$BUILD_TIME")

# Set API URLs
INTERNAL_API_URL="$API_BASE_URL"
PUBLIC_API_URL="$PUBLIC_API_BASE_URL"

if [ -z "$INTERNAL_API_URL" ] && [ "$EXISTING_ENV" != "null" ]; then
    INTERNAL_API_URL=$(echo "$EXISTING_ENV" | jq -r '.[] | select(.name == "API_BASE_URL") | .value // empty' | head -n1)
fi
if [ -z "$PUBLIC_API_URL" ] && [ "$EXISTING_ENV" != "null" ]; then
    PUBLIC_API_URL=$(echo "$EXISTING_ENV" | jq -r '.[] | select(.name == "NEXT_PUBLIC_API_BASE_URL") | .value // empty' | head -n1)
fi

[ -n "$INTERNAL_API_URL" ] && ENV_PAIRS+=("API_BASE_URL=$INTERNAL_API_URL")
[ -n "$PUBLIC_API_URL" ] && ENV_PAIRS+=("NEXT_PUBLIC_API_BASE_URL=$PUBLIC_API_URL")

# Set API_INTERNAL_SECRET
KEY_VAULT_NAME="reportmate-keyvault"
INTERNAL_SECRET=""

write_info "Fetching API_INTERNAL_SECRET from Key Vault..."
INTERNAL_SECRET=$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "api-internal-secret" --query "value" -o tsv 2>/dev/null || echo "")

if [ -n "$INTERNAL_SECRET" ]; then
    write_success "API_INTERNAL_SECRET loaded from Key Vault"
elif [ "$EXISTING_ENV" != "null" ]; then
    INTERNAL_SECRET=$(echo "$EXISTING_ENV" | jq -r '.[] | select(.name == "API_INTERNAL_SECRET") | .value // empty' | head -n1)
    [ -n "$INTERNAL_SECRET" ] && write_info "Using existing API_INTERNAL_SECRET from container"
fi

if [ -z "$INTERNAL_SECRET" ]; then
    write_error "API_INTERNAL_SECRET could not be loaded from Key Vault or existing container."
    write_error "Set it via Terraform (terraform apply) or manually before deploying."
    exit 1
fi

ENV_PAIRS+=("API_INTERNAL_SECRET=$INTERNAL_SECRET")

# Build update command
UPDATE_ARGS=(
    "containerapp" "update"
    "--name" "$CONTAINER_APP"
    "--resource-group" "$RESOURCE_GROUP"
    "--image" "$FULL_IMAGE"
)

if [ ${#ENV_PAIRS[@]} -gt 0 ]; then
    UPDATE_ARGS+=("--set-env-vars")
    for env_pair in "${ENV_PAIRS[@]}"; do
        UPDATE_ARGS+=("$env_pair")
    done
fi

az "${UPDATE_ARGS[@]}" > /dev/null
if [ $? -ne 0 ]; then
    write_error "Container app update failed."
    exit 1
fi
write_success "Container app updated with new image and metadata"

write_info "Waiting 30 seconds for the new revision to warm up..."
sleep 30

REVISION_JSON=$(az containerapp revision list \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    -o json 2>/dev/null || echo "[]")

if [ "$REVISION_JSON" != "[]" ]; then
    ACTIVE_REVISION=$(echo "$REVISION_JSON" | jq -r '.[] | select(.properties.active == true and .properties.trafficWeight == 100) | .name' | head -n1)
    if [ -n "$ACTIVE_REVISION" ]; then
        write_success "Active revision: $ACTIVE_REVISION"
    fi
else
    write_warning "Unable to determine active revision."
fi

# CDN purge
write_section "🗑️  Purging Azure Front Door cache..."

az afd endpoint purge \
    --resource-group "$RESOURCE_GROUP" \
    --profile-name "$FRONT_DOOR_PROFILE" \
    --endpoint-name "$FRONT_DOOR_ENDPOINT" \
    --content-paths "/*" \
    --domains "$DOMAIN" \
    --no-wait \
    --output none 2>&1 || true

if [ $? -eq 0 ]; then
    write_success "Front Door cache purge triggered (async)"
else
    write_warning "Front Door purge command failed"
fi

# Summary
write_section "════════════════ DEPLOYMENT SUMMARY ════════════════"
write_success "Image: $FULL_IMAGE"
write_success "Build Time (UTC): $BUILD_TIME"
write_success "Build ID (git): $GIT_HASH"
write_success "Container: $CONTAINER_APP"
write_success "Domain: https://$DOMAIN"
write_section "Next steps:"
write_info "• Open https://$DOMAIN in an incognito window to verify"
write_info "• Visit /settings → check CONTAINER_IMAGE_TAG matches $TAG"
write_info "• If browser shows cached content, hard refresh (Ctrl+F5)"
write_section "Done."
