# Security Best Practices for ReportMate Infrastructure

This document outlines security best practices for deploying and maintaining ReportMate infrastructure on Azure.

## 🔒 Table of Contents

- [Secrets Management](#secrets-management)
- [Authentication & Authorization](#authentication--authorization)
- [Network Security](#network-security)
- [Database Security](#database-security)
- [Container Security](#container-security)
- [Monitoring & Auditing](#monitoring--auditing)
- [Credential Rotation](#credential-rotation)
- [Compliance](#compliance)

## 🔐 Secrets Management

### Azure Key Vault

All sensitive credentials are stored in Azure Key Vault, **never** in Terraform state or environment variables.

**Secrets stored in Key Vault:**
- Database administrator password
- Azure AD client secret
- NextAuth secret
- API passphrases

### Terraform Secret Handling

**Critical rules:**

1. **NEVER commit secrets to git:**
   ```bash
   # These files are gitignored - keep it that way!
   terraform.tfvars
   backend.tf
   *.tfvars.json
   ```

2. **Generate strong passwords:**
   ```bash
   # Use cryptographically secure random generation
   openssl rand -base64 32
   
   # Or use pwgen
   pwgen -s 32 1
   ```

3. **Use environment variables for CI/CD:**
   ```bash
   export TF_VAR_db_admin_password="$(az keyvault secret show ...)"
   ```

4. **Never use example passwords:**
   - ❌ `password123`, `MySecurePassword123!`
   - ✅ `q7LmK9pX2wN8vR3zF6H4bCmD5jT9gYhA`

### Key Vault Access Control

**Principle of least privilege:**

```hcl
# Grant minimum required permissions
resource "azurerm_key_vault_access_policy" "app" {
  secret_permissions = [
    "Get",
    "List"
  ]
  # NOT "Set", "Delete", "Purge" for applications
}
```

**Managed Identities only:**
- Use Azure Managed Identity for applications
- Never use service principal keys in production
- Container Apps automatically get managed identity

## 🔑 Authentication & Authorization

### Azure Active Directory (Entra ID)

**Application Registration:**

1. **Redirect URIs:**
   - Production: `https://yourdomain.com/api/auth/callback/azure-ad`
   - Development: `http://localhost:3000/api/auth/callback/azure-ad`
   
2. **Token Configuration:**
   - Enable ID tokens
   - Enable access tokens
   - Set token lifetime appropriately (default: 1 hour)

3. **App Roles:**
   ```json
   [
     {
       "allowedMemberTypes": ["User"],
       "description": "Administrator access",
       "displayName": "Administrator",
       "value": "Administrator"
     }
   ]
   ```

### Domain Restrictions

**Limit authentication to your organization:**

```hcl
# terraform.tfvars
allowed_auth_domains = ["yourdomain.com"]
```

This prevents external users from authenticating even if they have your Azure AD app ID.

### Multi-Factor Authentication (MFA)

**Enforce MFA at the Azure AD level:**

1. Navigate to: Azure Portal → Entra ID → Security → Authentication Methods
2. Enable MFA for all users or specific groups
3. Require MFA for the ReportMate application

**Conditional Access Policies:**
- Require MFA for all users
- Block legacy authentication
- Require compliant devices
- Restrict access by location (optional)

## 🌐 Network Security

### Virtual Network (VNet) Isolation

**Database Private Endpoint:**
```
┌─────────────────────────────────────┐
│          Internet                   │
└─────────────────┬───────────────────┘
                  │
                  │ (Blocked)
                  ▼
         ┌────────────────┐
         │   Database     │
         │ (Private Only) │
         └────────────────┘
                  ▲
                  │ (Allowed)
         ┌────────┴────────┐
         │  Container Apps │
         │    (VNet)       │
         └─────────────────┘
```

**Implementation:**
- Database accessible only via VNet
- Container Apps deployed in VNet subnet
- No public access to database

### Network Security Groups (NSGs)

**Default deny, explicit allow:**

```hcl
# Only allow HTTPS inbound
resource "azurerm_network_security_rule" "https" {
  access                     = "Allow"
  direction                  = "Inbound"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "443"
  source_address_prefix      = "*"
  destination_address_prefix = "*"
}
```

### TLS/SSL Certificates

**Always use HTTPS:**
- Azure-managed certificates for `*.azurecontainerapps.io`
- Let's Encrypt for custom domains (automated renewal)
- Minimum TLS version: 1.2

## 🗄️ Database Security

### Connection Security

**SSL enforcement:**
```hcl
resource "azurerm_postgresql_flexible_server" "main" {
  # Force SSL connections
  storage_mb = 32768
}
```

**Connection string format:**
```
postgresql://user:pass@host:5432/db?sslmode=require
```

### Firewall Rules

**Whitelist approach only:**

```hcl
# NEVER use 0.0.0.0-255.255.255.255 (allow all)
# Only allow Container App subnet
resource "azurerm_postgresql_flexible_server_firewall_rule" "container_apps" {
  start_ip_address = "10.0.1.0"
  end_ip_address   = "10.0.1.255"
}
```

### Database User Permissions

**Principle of least privilege:**

```sql
-- Application user (read/write only)
CREATE USER reportmate_app WITH PASSWORD 'generated_password';
GRANT CONNECT ON DATABASE reportmate TO reportmate_app;
GRANT USAGE ON SCHEMA public TO reportmate_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO reportmate_app;

-- Read-only user (for reporting)
CREATE USER reportmate_readonly WITH PASSWORD 'generated_password';
GRANT CONNECT ON DATABASE reportmate TO reportmate_readonly;
GRANT USAGE ON SCHEMA public TO reportmate_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reportmate_readonly;
```

### Backup & Disaster Recovery

**Automated backups:**
- Retention: 7-35 days (default: 7)
- Point-in-time restore available
- Geo-redundant backups for production

```hcl
resource "azurerm_postgresql_flexible_server" "main" {
  backup_retention_days        = 30
  geo_redundant_backup_enabled = true  # Production only
}
```

## 📦 Container Security

### Image Security

**Best practices:**

1. **Use official base images only:**
   ```dockerfile
   FROM node:20-alpine  # Alpine for smaller attack surface
   ```

2. **Scan images for vulnerabilities:**
   ```bash
   # Before pushing to registry
   docker scan reportmate:latest
   ```

3. **Keep images updated:**
   - Rebuild monthly or after security advisories
   - Use Dependabot for dependency updates

4. **Don't include secrets in images:**
   ```dockerfile
   # ❌ NEVER do this
   ENV DB_PASSWORD="secret123"
   
   # ✅ Use environment variables at runtime
   # Set via Container App configuration
   ```

### Container Registry

**Azure Container Registry security:**

```hcl
resource "azurerm_container_registry" "main" {
  # Admin user disabled - use managed identity
  admin_enabled = false
  
  # Private network access
  public_network_access_enabled = false
  
  # Enable vulnerability scanning
  quarantine_policy_enabled = true
}
```

### Runtime Security

**Container App restrictions:**

```hcl
resource "azurerm_container_app" "main" {
  template {
    container {
      # Run as non-root user
      # Set in Dockerfile: USER node
      
      # Resource limits (prevent resource exhaustion)
      cpu    = 0.5
      memory = "1Gi"
    }
  }
}
```

## 📊 Monitoring & Auditing

### Application Insights

**Log sensitive operations:**
- Authentication attempts (success/failure)
- Database connection errors
- Key Vault access
- Configuration changes

**Never log sensitive data:**
- Passwords
- Connection strings
- Personal information (PII)

### Azure Monitor Alerts

**Set up alerts for:**

1. **Failed authentication attempts:**
   ```kusto
   traces
   | where message contains "authentication failed"
   | summarize count() by bin(timestamp, 5m)
   | where count_ > 10
   ```

2. **Database connection failures:**
   ```kusto
   exceptions
   | where type == "PostgresConnectionException"
   ```

3. **High error rates:**
   ```kusto
   requests
   | where success == false
   | summarize failureRate = count() by bin(timestamp, 5m)
   | where failureRate > 10
   ```

### Audit Logs

**Enable diagnostic settings:**

```hcl
resource "azurerm_monitor_diagnostic_setting" "keyvault" {
  target_resource_id = azurerm_key_vault.main.id
  
  log {
    category = "AuditEvent"
    enabled  = true
  }
}
```

**Review logs regularly:**
- Key Vault access patterns
- Database administrator logins
- RBAC changes
- NSG rule modifications

## 🔄 Credential Rotation

### Rotation Schedule

| Credential | Rotation Period | Method |
|------------|----------------|---------|
| Database password | 90 days | Manual or automated |
| Azure AD client secret | 180 days | Azure portal + Key Vault |
| NextAuth secret | Never (unless compromised) | Manual |
| API keys | 90 days | Manual |

### Automated Rotation (Recommended)

**Azure Key Vault Rotation Policy:**

```hcl
resource "azurerm_key_vault_secret" "db_password" {
  name         = "database-password"
  value        = random_password.db.result
  
  # Expiration warning
  expiration_date = timeadd(timestamp(), "2160h")  # 90 days
}
```

**Rotation steps:**

1. Generate new secret
2. Update Key Vault
3. Update database user password
4. Restart Container Apps to pick up new secret
5. Verify connectivity
6. Delete old secret after grace period

### Manual Rotation Procedure

**Database password rotation:**

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update database
az postgres flexible-server update \
  --resource-group ReportMate \
  --name reportmate-database \
  --admin-password "$NEW_PASSWORD"

# 3. Update Key Vault
az keyvault secret set \
  --vault-name reportmate-kv \
  --name database-password \
  --value "$NEW_PASSWORD"

# 4. Restart Container Apps
az containerapp restart \
  --name reportmate-container-prod \
  --resource-group ReportMate

# 5. Verify health
curl https://reportmate-api/health
```

## 📋 Compliance

### Data Residency

**Azure region selection:**
- Choose region based on data residency requirements
- GDPR: EU regions (West Europe, North Europe)
- Canadian data sovereignty: Canada Central, Canada East

```hcl
variable "location" {
  default = "canadacentral"  # For Canadian data residency
}
```

### Encryption

**Encryption at rest:**
- Azure Storage: Enabled by default (AES-256)
- PostgreSQL: Enabled by default (TDE)
- Key Vault: Hardware Security Modules (HSM) backed

**Encryption in transit:**
- All traffic over TLS 1.2+
- Database connections require SSL
- Container Apps enforce HTTPS

### Data Retention

**GDPR compliance:**
- Event data: 30 days (configurable)
- Audit logs: 90 days minimum
- Backups: 7-35 days

```hcl
# Configure retention in terraform.tfvars
maintenance_retention_days = 30  # Events
```

**Right to be forgotten:**
- Implement user data deletion workflows
- Cascade deletes for user-related data
- Document data lineage

## 🚨 Incident Response

### Security Incident Checklist

**If credentials are compromised:**

1. **Immediately rotate all affected credentials**
2. **Review audit logs for unauthorized access**
3. **Check for data exfiltration in egress logs**
4. **Notify stakeholders per incident response plan**
5. **Update RBAC to revoke compromised accounts**
6. **Perform root cause analysis**
7. **Implement additional controls to prevent recurrence**

### Emergency Contacts

**Maintain updated contact list:**
- Azure subscription owner
- Security team lead
- Database administrator
- Application owner

### Backup Access

**Break-glass accounts:**
- Separate emergency admin account
- MFA required
- Conditional access with alerting
- Regular access review

## 📚 Additional Resources

### Microsoft Documentation

- [Azure Security Best Practices](https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns)
- [Key Vault Best Practices](https://learn.microsoft.com/azure/key-vault/general/best-practices)
- [PostgreSQL Security](https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-security)
- [Container Apps Security](https://learn.microsoft.com/azure/container-apps/security)

### Security Tools

- [Azure Defender](https://azure.microsoft.com/services/defender-for-cloud/)
- [Microsoft Sentinel](https://azure.microsoft.com/services/microsoft-sentinel/)
- [Azure Policy](https://learn.microsoft.com/azure/governance/policy/)
- [Docker Scan](https://docs.docker.com/engine/scan/)

### Compliance Frameworks

- [CIS Azure Foundations Benchmark](https://www.cisecurity.org/benchmark/azure)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [ISO 27001](https://www.iso.org/isoiec-27001-information-security.html)

---

## 🔒 Security Reporting

Found a security vulnerability? Please report it responsibly:

**DO NOT create a public GitHub issue for security vulnerabilities!**

Instead:
1. Email: security@yourdomain.com
2. Include: Detailed description, reproduction steps, impact assessment
3. Allow: 90 days for remediation before public disclosure

---

**Last Updated:** 2025-01-25
**Review Cycle:** Quarterly

