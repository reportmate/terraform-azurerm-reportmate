#!/bin/bash

# ReportMate Container Update Script
# This script handles the complete process of updating the production container
# including building, pushing, deploying, and verifying the update
# Configuration is dynamically loaded from Terraform outputs and Azure resources

set -e  # Exit on any error

# Global variables (loaded dynamically)
RESOURCE_GROUP=""
CONTAINER_APP_NAME=""
ACR_NAME=""
IMAGE_NAME=""  # Dynamically determined from current Container App image
FRONTDOOR_PROFILE=""
FRONTDOOR_ENDPOINT=""
PRODUCTION_URL=""
CONTAINER_FQDN=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled by user"
        exit 0
    fi
}

load_configuration() {
    log_info "Loading configuration from Terraform and Azure..."
    
    # Check if we're in the infrastructure directory
    if [[ ! -f "terraform.tfvars" ]]; then
        log_error "Must run from infrastructure directory"
        exit 1
    fi
    
    # Load Terraform outputs
    if ! terraform output &> /dev/null; then
        log_error "Terraform state not found or not initialized. Run 'terraform init' and 'terraform apply' first"
        exit 1
    fi
    
    # Get values from Terraform outputs
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
    PRODUCTION_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "")
    
    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_error "Could not get resource group from Terraform outputs"
        exit 1
    fi
    
    if [[ -z "$PRODUCTION_URL" ]]; then
        log_error "Could not get production URL from Terraform outputs"
        exit 1
    fi
    
    log_success "Terraform configuration loaded:"
    log_info "  Resource Group: $RESOURCE_GROUP"
    log_info "  Production URL: $PRODUCTION_URL"
    
    # Discover Azure resources dynamically
    log_info "Discovering Azure resources..."
    
    # Find Container App
    CONTAINER_APP_NAME=$(az containerapp list --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(tags.Service, 'reportmate')].name | [0]" --output tsv 2>/dev/null || echo "")
    
    if [[ -z "$CONTAINER_APP_NAME" ]]; then
        # Fallback: find any container app in the resource group
        CONTAINER_APP_NAME=$(az containerapp list --resource-group "$RESOURCE_GROUP" \
            --query "[0].name" --output tsv 2>/dev/null || echo "")
    fi
    
    if [[ -z "$CONTAINER_APP_NAME" ]]; then
        log_error "Could not find Container App in resource group $RESOURCE_GROUP"
        exit 1
    fi
    
    # Get Container App FQDN
    CONTAINER_FQDN=$(az containerapp show --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_NAME" \
        --query "properties.configuration.ingress.fqdn" --output tsv 2>/dev/null || echo "")
    
    if [[ -z "$CONTAINER_FQDN" ]]; then
        log_error "Could not get Container App FQDN"
        exit 1
    fi
    
    # Find Azure Container Registry
    ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(tags.Service, 'reportmate')].name | [0]" --output tsv 2>/dev/null || echo "")
    
    if [[ -z "$ACR_NAME" ]]; then
        # Fallback: find any ACR in the resource group
        ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" \
            --query "[0].name" --output tsv 2>/dev/null || echo "")
    fi
    
    if [[ -z "$ACR_NAME" ]]; then
        log_error "Could not find Azure Container Registry in resource group $RESOURCE_GROUP"
        exit 1
    fi
    
    # Extract IMAGE_NAME from current Container App configuration
    local current_image=$(az containerapp show --resource-group "$RESOURCE_GROUP" \
        --name "$CONTAINER_APP_NAME" \
        --query "properties.template.containers[0].image" --output tsv 2>/dev/null || echo "")
    
    if [[ -n "$current_image" ]]; then
        # Extract image name from full image path (e.g., "reportmateacr.azurecr.io/reportmate-web:latest" -> "reportmate-web")
        IMAGE_NAME=$(echo "$current_image" | sed 's|.*/\([^:]*\):.*|\1|')
        if [[ -z "$IMAGE_NAME" ]]; then
            # Fallback: extract from simple image name (e.g., "reportmate-web:latest" -> "reportmate-web")
            IMAGE_NAME=$(echo "$current_image" | sed 's|:.*||')
        fi
    fi
    
    if [[ -z "$IMAGE_NAME" ]]; then
        # Final fallback to standard naming convention
        IMAGE_NAME="reportmate-web"
        log_warning "Could not determine IMAGE_NAME from Container App, using fallback: $IMAGE_NAME"
    fi
    
    # Find Front Door Profile and Endpoint
    FRONTDOOR_PROFILE=$(az afd profile list --resource-group "$RESOURCE_GROUP" \
        --query "[?contains(tags.Service, 'reportmate')].name | [0]" --output tsv 2>/dev/null || echo "")
    
    if [[ -z "$FRONTDOOR_PROFILE" ]]; then
        # Fallback: find any Front Door profile in the resource group
        FRONTDOOR_PROFILE=$(az afd profile list --resource-group "$RESOURCE_GROUP" \
            --query "[0].name" --output tsv 2>/dev/null || echo "")
    fi
    
    if [[ -n "$FRONTDOOR_PROFILE" ]]; then
        FRONTDOOR_ENDPOINT=$(az afd endpoint list --resource-group "$RESOURCE_GROUP" \
            --profile-name "$FRONTDOOR_PROFILE" \
            --query "[0].name" --output tsv 2>/dev/null || echo "")
    fi
    
    # Log discovered configuration
    log_success "Azure resources discovered:"
    log_info "  Container App: $CONTAINER_APP_NAME"
    log_info "  Container FQDN: $CONTAINER_FQDN"
    log_info "  Container Registry: $ACR_NAME"
    log_info "  Image Name: $IMAGE_NAME"
    
    if [[ -n "$FRONTDOOR_PROFILE" ]]; then
        log_info "  Front Door Profile: $FRONTDOOR_PROFILE"
        log_info "  Front Door Endpoint: $FRONTDOOR_ENDPOINT"
    else
        log_warning "  Front Door not found - cache purging will be skipped"
    fi
    
    log_success "Configuration loaded successfully"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if we're in the correct directory
    if [[ ! -f "terraform.tfvars" ]]; then
        log_error "Must run from infrastructure directory"
        exit 1
    fi
    
    if [[ ! -f "../apps/www/Dockerfile" ]]; then
        log_error "Dockerfile not found at ../apps/www/Dockerfile"
        exit 1
    fi
    
    # Check required tools
    local missing_tools=()
    
    if ! command -v az &> /dev/null; then
        missing_tools+=("Azure CLI")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_tools+=("Docker")
    fi
    
    if ! command -v terraform &> /dev/null; then
        missing_tools+=("Terraform")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools and try again"
        exit 1
    fi
    
    # Check if logged into Azure
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure CLI. Run 'az login'"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

generate_tag() {
    local timestamp=$(date +"%Y%m%d%H%M%S")
    local git_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")
    echo "${timestamp}-${git_hash}"
}

build_and_push_image() {
    local tag=$1
    log_info "Building and pushing container image with tag: $tag"
    
    # Login to ACR
    log_info "Logging into Azure Container Registry..."
    az acr login --name $ACR_NAME
    
    # Build the image
    log_info "Building Docker image..."
    cd ../apps/www
    docker build -t ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${tag} .
    
    # Push the image
    log_info "Pushing image to registry..."
    docker push ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${tag}
    
    # Return to infrastructure directory
    cd ../../infrastructure
    
    log_success "Image built and pushed successfully"
}

update_container_app() {
    local tag=$1
    log_info "Updating Container App to use new image..."
    
    # Update the container app
    az containerapp update \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_APP_NAME \
        --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${tag}
    
    # Wait for deployment to complete
    log_info "Waiting for deployment to complete..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local status=$(az containerapp revision list \
            --resource-group $RESOURCE_GROUP \
            --name $CONTAINER_APP_NAME \
            --query "reverse(sort_by([?active], &createdTime))[0].provisioningState" \
            --output tsv)
        
        if [ "$status" = "Provisioned" ]; then
            log_success "Container App deployment completed"
            break
        elif [ "$status" = "Failed" ]; then
            log_error "Container App deployment failed"
            exit 1
        fi
        
        log_info "Deployment status: $status (attempt $((attempt + 1))/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log_error "Deployment timeout after $((max_attempts * 10)) seconds"
        exit 1
    fi
}

verify_container_health() {
    log_info "Verifying container health..."
    
    # Test direct container access
    log_info "Testing direct container access..."
    local direct_response=$(curl -s "https://${CONTAINER_FQDN}/api/version" | jq -r '.success // false' 2>/dev/null || echo "false")
    
    if [ "$direct_response" = "true" ]; then
        log_success "Direct container access working"
    else
        log_error "Direct container access failed"
        return 1
    fi
    
    # Get current revision info
    local revision=$(az containerapp revision list \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_APP_NAME \
        --query "reverse(sort_by([?active], &createdTime))[0].name" \
        --output tsv)
    
    log_success "Active revision: $revision"
    log_success "Container FQDN: $CONTAINER_FQDN"
}

purge_frontdoor_cache() {
    if [[ -z "$FRONTDOOR_PROFILE" ]] || [[ -z "$FRONTDOOR_ENDPOINT" ]]; then
        log_warning "Front Door configuration not available - skipping cache purge"
        return 0
    fi
    
    log_info "Purging Front Door cache..."
    
    # Purge all cached content
    az afd endpoint purge \
        --resource-group $RESOURCE_GROUP \
        --profile-name $FRONTDOOR_PROFILE \
        --endpoint-name $FRONTDOOR_ENDPOINT \
        --content-paths "/*"
    
    # Wait for cache purge to propagate
    log_info "Waiting for cache purge to propagate..."
    sleep 30
    
    log_success "Front Door cache purged"
}

verify_production_deployment() {
    log_info "Verifying production deployment..."
    
    local max_attempts=10
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        # Test version endpoint
        local version_response=$(curl -s "${PRODUCTION_URL}/api/version" | jq -r '.success // false' 2>/dev/null || echo "false")
        
        # Test devices endpoint
        local devices_response=$(curl -s "${PRODUCTION_URL}/api/devices" | jq -r '.success // false' 2>/dev/null || echo "false")
        
        if [ "$version_response" = "true" ] && [ "$devices_response" = "true" ]; then
            log_success "Production deployment verified successfully"
            
            # Show version info
            local version_info=$(curl -s "${PRODUCTION_URL}/api/version" | jq -r '.data.version // "unknown"' 2>/dev/null || echo "unknown")
            local build_id=$(curl -s "${PRODUCTION_URL}/api/version" | jq -r '.data.buildId // "unknown"' 2>/dev/null || echo "unknown")
            local build_time=$(curl -s "${PRODUCTION_URL}/api/version" | jq -r '.data.buildTime // "unknown"' 2>/dev/null || echo "unknown")
            
            log_success "Version: $version_info"
            log_success "Build ID: $build_id"
            log_success "Build Time: $build_time"
            return 0
        fi
        
        log_info "Production not ready yet (attempt $((attempt + 1))/$max_attempts)"
        sleep 30
        ((attempt++))
    done
    
    log_error "Production verification failed after $((max_attempts * 30)) seconds"
    return 1
}

show_logs() {
    log_info "Recent container logs:"
    az containerapp logs show \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_APP_NAME \
        --follow false \
        --tail 10
}

rollback() {
    log_warning "Rolling back to previous revision..."
    
    # Get the previous active revision
    local prev_revision=$(az containerapp revision list \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_APP_NAME \
        --query "reverse(sort_by([?active], &createdTime))[1].name" \
        --output tsv)
    
    if [ -z "$prev_revision" ]; then
        log_error "No previous revision found for rollback"
        return 1
    fi
    
    # Activate the previous revision
    az containerapp revision activate \
        --resource-group $RESOURCE_GROUP \
        --name $CONTAINER_APP_NAME \
        --revision $prev_revision
    
    log_success "Rolled back to revision: $prev_revision"
}

main() {
    log_info "Starting ReportMate container update process..."
    
    # Check prerequisites and load configuration
    check_prerequisites
    load_configuration
    
    # Show current status
    log_info "Current production status:"
    verify_container_health || log_warning "Container health check failed"
    
    # Confirm update
    confirm "Do you want to proceed with the container update?"
    
    # Generate tag
    local tag=$(generate_tag)
    log_info "Generated tag: $tag"
    
    # Build and push
    if ! build_and_push_image $tag; then
        log_error "Build and push failed"
        exit 1
    fi
    
    # Update container app
    if ! update_container_app $tag; then
        log_error "Container app update failed"
        exit 1
    fi
    
    # Verify container health
    if ! verify_container_health; then
        log_error "Container health verification failed"
        confirm "Do you want to rollback?"
        rollback
        exit 1
    fi
    
    # Purge cache
    purge_frontdoor_cache
    
    # Verify production
    if ! verify_production_deployment; then
        log_error "Production verification failed"
        confirm "Do you want to rollback?"
        rollback
        exit 1
    fi
    
    log_success "Container update completed successfully!"
    log_info "Production URL: $PRODUCTION_URL"
    
    # Show final logs
    show_logs
}

# Handle command line arguments
case "${1:-}" in
    "rollback")
        log_info "Manual rollback requested"
        check_prerequisites
        load_configuration
        rollback
        ;;
    "logs")
        log_info "Showing recent logs"
        check_prerequisites
        load_configuration
        show_logs
        ;;
    "status")
        log_info "Checking current status"
        check_prerequisites
        load_configuration
        verify_container_health
        ;;
    "purge-cache")
        log_info "Purging Front Door cache"
        check_prerequisites
        load_configuration
        purge_frontdoor_cache
        ;;
    *)
        main
        ;;
esac
