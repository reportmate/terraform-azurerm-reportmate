# Basic ReportMate Deployment Example

This example demonstrates a basic deployment of ReportMate with minimal configuration.

## Configuration

```hcl
module "reportmate" {
  source = "../../"
  
  # Required variables
  resource_group_name = "reportmate-basic"
  location           = "East US"
  db_password        = "MySecurePassword123!"
  
  # Optional: Use development environment
  environment = "dev"
  deploy_dev  = true
  deploy_prod = false
}
```

## Usage

1. Copy this directory to your project
2. Update the variables in `main.tf`
3. Run:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Outputs

After deployment, you can access:
- Frontend URL: `terraform output frontend_url`
- API URL: `terraform output api_url`
