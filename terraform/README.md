# ReportMate Terraform Configuration

This directory contains the main Terraform configuration for ReportMate infrastructure deployment.

## Files

- `main.tf` - Main infrastructure configuration with all modules
- `variables.tf` - Input variables for the configuration
- `outputs.tf` - Output values from the infrastructure
- `terraform.tf` - Terraform version constraints and provider configuration
- `backend.tf` - Backend configuration for state storage
- `backend.tf.example` - Example backend configuration
- `terraform.tfvars.example` - Example variables file

## Usage

1. Copy `backend.tf.example` to `backend.tf` and configure your state storage
2. Copy `terraform.tfvars.example` to `terraform.tfvars` and set your variables
3. Run the following commands:

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

## Module Structure

The configuration uses the following modules:
- `../modules/database` - PostgreSQL database
- `../modules/storage` - Azure Storage Account
- `../modules/messaging` - Azure Web PubSub
- `../modules/monitoring` - Application Insights and Log Analytics
- `../modules/identity` - Managed Identity and RBAC
- `../modules/containers` - Container Apps for frontend
- `../modules/networking` - Azure Front Door (optional)
- `../api` - Azure Functions for API endpoints

## Scripts

Deployment scripts are located in the `../scripts/` directory.
