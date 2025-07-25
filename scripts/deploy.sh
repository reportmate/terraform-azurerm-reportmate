#!/bin/bash

# ReportMate REST API Unified Deployment Script
# Supports both infrastructure deployment and quick function-only deployments
# Auto-detects environment and provides intelligent deployment options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}🚀 $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

show_help() {
    echo "ReportMate REST API Deployment Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --env ENV           Environment to deploy (dev, staging, prod) [default: dev]"
    echo "  -i, --infra             Infrastructure only (Terraform deployment)"
    echo "  -f, --functions         Functions only (code deployment)"
    echo "  -t, --test             Test deployment after completion"
    echo "  -y, --yes              Auto-approve without prompts"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Full deployment with prompts"
    echo "  $0 -f                   # Functions-only deployment"
    echo "  $0 -e prod -i           # Deploy infrastructure to production"
    echo "  $0 -e staging -f -y     # Deploy functions to staging, auto-approve"
    echo ""
}

# Default values
ENVIRONMENT="dev"
DEPLOY_INFRASTRUCTURE=true
DEPLOY_FUNCTIONS=true
AUTO_APPROVE=false
RUN_TESTS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -i|--infra|--infrastructure)
            DEPLOY_INFRASTRUCTURE=true
            DEPLOY_FUNCTIONS=false
            shift
            ;;
        -f|--functions)
            DEPLOY_INFRASTRUCTURE=false
            DEPLOY_FUNCTIONS=true
            shift
            ;;
        -t|--test)
            RUN_TESTS=true
            shift
            ;;
        -y|--yes)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Configuration based on environment
RESOURCE_GROUP="ReportMate"
FUNCTION_APP_NAME="reportmate-api"

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    log_success "Azure CLI is installed"
    
    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi
    
    local account_name=$(az account show --query "user.name" -o tsv)
    local subscription_name=$(az account show --query "name" -o tsv)
    log_success "Logged in as: $account_name"
    log_success "Subscription: $subscription_name"
    
    # Check Terraform if needed
    if [ "$DEPLOY_INFRASTRUCTURE" = true ]; then
        if ! command -v terraform &> /dev/null; then
            log_error "Terraform is not installed. Please install it first."
            exit 1
        fi
        log_success "Terraform is installed"
    fi
    
    # Check Azure Functions Core Tools if needed
    if [ "$DEPLOY_FUNCTIONS" = true ]; then
        if ! command -v func &> /dev/null; then
            log_error "Azure Functions Core Tools is not installed."
            log_error "Please install from: https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local"
            exit 1
        fi
        log_success "Azure Functions Core Tools is installed"
    fi
    
    # Check required files
    if [ "$DEPLOY_INFRASTRUCTURE" = true ] && [ ! -f "main.tf" ]; then
        log_error "Terraform files not found. Must run from infrastructure root directory."
        exit 1
    fi
    
    if [ "$DEPLOY_FUNCTIONS" = true ]; then
        if [ ! -d "modules/functions/api" ] || [ ! -f "modules/functions/api/requirements.txt" ]; then
            log_error "API functions directory or requirements.txt not found in modules/functions/api."
            exit 1
        fi
        if [ ! -d "modules/functions" ]; then
            log_error "Functions module directory not found."
            exit 1
        fi
    fi
}

# Function to deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying Infrastructure with Terraform..."
    
    # Check for terraform.tfvars
    if [ ! -f "terraform.tfvars" ]; then
        log_warning "terraform.tfvars not found. Using default values."
        log_warning "Consider creating terraform.tfvars for customization."
    fi
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log_info "Planning Terraform deployment..."
    terraform plan -var="environment=${ENVIRONMENT}" -out=tfplan
    
    # Apply deployment without confirmation
    log_info "Applying Terraform deployment..."
    terraform apply tfplan
    
    # Get outputs
    FUNCTION_APP_NAME=$(terraform output -raw function_app_name 2>/dev/null || echo "$FUNCTION_APP_NAME")
    FUNCTION_APP_URL=$(terraform output -raw function_app_url 2>/dev/null || echo "")
    RESOURCE_GROUP_NAME=$(terraform output -raw resource_group_name 2>/dev/null || echo "$RESOURCE_GROUP")
    
    log_success "Infrastructure deployed successfully!"
    log_success "Function App: $FUNCTION_APP_NAME"
    log_success "Resource Group: $RESOURCE_GROUP_NAME"
    if [ -n "$FUNCTION_APP_URL" ]; then
        log_success "Function App URL: $FUNCTION_APP_URL"
    fi
}

# Function to deploy functions
deploy_functions() {
    log_info "Deploying Functions using Azure Functions Core Tools..."
    
    # Change to API directory
    cd modules/functions/api
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Build and deploy functions
    log_info "Building and deploying functions..."
    func azure functionapp publish "$FUNCTION_APP_NAME" --python
    
    log_success "Functions deployed successfully!"
    
    # Return to original directory
    cd ../../..
}

# Function to test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    # Get function app URL
    FUNCTION_URL=$(az functionapp show --name "$FUNCTION_APP_NAME" --resource-group "$RESOURCE_GROUP" --query "defaultHostName" -o tsv 2>/dev/null)
    
    if [ -z "$FUNCTION_URL" ]; then
        log_warning "Could not get function app URL. Skipping tests."
        return
    fi
    
    log_info "Function App URL: https://$FUNCTION_URL"
    
    # Test health endpoint
    HEALTH_URL="https://$FUNCTION_URL/api/health"
    log_info "Testing health endpoint: $HEALTH_URL"
    
    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    sleep 15
    
    if curl -f -s "$HEALTH_URL" > /dev/null; then
        log_success "Health check passed!"
        echo "Response:"
        curl -s "$HEALTH_URL" | python -m json.tool 2>/dev/null || echo "API is responding"
    else
        log_warning "Health check failed. The API might still be starting up."
        log_warning "Try manually: $HEALTH_URL"
    fi
    
    echo ""
    log_info "Available endpoints:"
    echo "  Health:  https://$FUNCTION_URL/api/health"
    echo "  Devices: https://$FUNCTION_URL/api/devices"
    echo "  Ingest:  https://$FUNCTION_URL/api/ingest"
}

# Main deployment function
main() {
    echo "🎯 ReportMate REST API Deployment Script"
    echo "========================================="
    echo ""
    
    # Check prerequisites
    check_prerequisites
    echo ""
    
    # Deploy infrastructure
    if [ "$DEPLOY_INFRASTRUCTURE" = true ]; then
        deploy_infrastructure
        echo ""
    fi
    
    # Deploy functions
    if [ "$DEPLOY_FUNCTIONS" = true ]; then
        deploy_functions
        echo ""
    fi
    
    # Test deployment
    if [ "$RUN_TESTS" = true ] || [ "$DEPLOY_FUNCTIONS" = true ]; then
        test_deployment
        echo ""
    fi
    
    # Final summary
    echo "🎉 DEPLOYMENT COMPLETED! 🎉"
    echo "=========================="
    echo ""
    log_success "ReportMate REST API is deployed and ready!"
    echo ""
    
    if [ "$DEPLOY_FUNCTIONS" = true ]; then
        echo "📋 Next steps:"
        echo "1. Test the API endpoints"
        echo "2. Update Windows client configuration"
        echo "3. Update web application configuration"
        echo "4. Set up monitoring and alerts"
    fi
    
    if [ "$DEPLOY_INFRASTRUCTURE" = true ]; then
        echo ""
        echo "💡 Infrastructure deployed successfully!"
        echo "   You can now use functions-only deployments with: $0 -f"
    fi
}

# Run main function
main "$@"
