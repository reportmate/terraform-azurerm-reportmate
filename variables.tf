### PostgreSQL
variable "db_username" {
  type    = string
  default = "reportmate"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "allowed_ips" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

### Pipeline Permissions
variable "enable_pipeline_permissions" {
  type        = bool
  description = "Enable RBAC permissions for Azure DevOps pipeline service principal"
  default     = false
}

variable "pipeline_service_principal_id" {
  type        = string
  description = "Object ID of the Azure DevOps pipeline service principal"
  default     = ""
}

### Client Authentication
variable "client_passphrases" {
  type        = string
  description = "Comma-separated list of client passphrases for restricted access. If set, only clients with valid passphrases can report data. This is the legacy global passphrase method."
  default     = ""
  sensitive   = true
}

variable "enable_machine_groups" {
  type        = bool
  description = "Enable per-machine-group passphrase authentication. When enabled, each machine group has its own unique passphrase stored in the database."
  default     = false
}

variable "enable_business_units" {
  type        = bool
  description = "Enable business units for organizational access control and machine group management."
  default     = false
}

### remote-state backend (override in CLI or tfvars)
variable "backend_rg_name" {
  type    = string
  default = "tfstate-rg"
}

variable "backend_sa_name" {
  type    = string
  default = "tfstatestorage"
}

variable "backend_container_name" {
  type    = string
  default = "tfstate"
}

### Environment Configuration
variable "environment" {
  type        = string
  description = "Deployment environment (dev, prod, or both)"
  default     = "prod"
  validation {
    condition     = contains(["dev", "prod", "both"], var.environment)
    error_message = "Environment must be 'dev', 'prod', or 'both'."
  }
}

variable "deploy_dev" {
  type        = bool
  description = "Deploy development container app"
  default     = false
}

variable "deploy_prod" {
  type        = bool
  description = "Deploy production container app"
  default     = true
}

### Custom Domain Configuration
variable "custom_domain_name" {
  type        = string
  description = "Custom domain name for the frontend (e.g., reportmate.ecuad.ca)"
  default     = ""
}

variable "enable_custom_domain" {
  type        = bool
  description = "Enable custom domain configuration"
  default     = false
}
