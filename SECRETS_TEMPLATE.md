# GitHub Secrets Template

Copy this template and configure these secrets in your GitHub repository:
`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

## Authentication Secrets (Required)

### FABRIC_CLIENT_ID
- **Description**: Azure service principal client (application) ID
- **Example**: `12345678-1234-1234-1234-123456789abc`
- **How to get**: Azure Portal → App registrations → Your app → Overview → Application (client) ID

### FABRIC_CLIENT_SECRET
- **Description**: Azure service principal client secret
- **Example**: `abc123~XyZ...`
- **How to get**: Azure Portal → App registrations → Your app → Certificates & secrets → New client secret

### FABRIC_TENANT_ID
- **Description**: Azure AD tenant ID
- **Example**: `87654321-4321-4321-4321-987654321cba`
- **How to get**: Azure Portal → Microsoft Entra ID → Overview → Tenant ID

## Fabric Configuration Secrets (Required)

### PROJECT_NAME
- **Description**: Your project name (used as workspace name prefix)
- **Example**: `DEMO Fabric CICD`

### CAPACITY_NAME
- **Description**: Name of your Fabric capacity
- **Example**: `X.Capacity`
- **How to get**: Fabric Portal → Settings → Capacity settings

### GIT_CONNECTION_NAME
- **Description**: Name of the Git connection in Fabric
- **Example**: `X.Connection`
- **How to get**: Fabric Portal → Settings → Git connections

## Security Group Secrets (Required)

### SECGROUP_ADMINS_ID
- **Description**: Azure AD group ID for workspace administrators
- **Example**: `11111111-2222-3333-4444-555555555555`
- **How to get**: Azure Portal → Microsoft Entra ID → Groups → Your group → Object ID

### SECGROUP_ADMINS_NAME
- **Description**: Azure AD group name for workspace administrators
- **Example**: `SecGroup Fabric Admins`

## Optional Secrets

### SECGROUP_DEVS_ID
- **Description**: Azure AD group ID for developers (optional)
- **Example**: `11111111-2222-3333-4444-555555555555`

### SECGROUP_DEVS_NAME
- **Description**: Azure AD group name for developers (optional)
- **Example**: `SecGroup Fabric Developers`

### PE_RESOURCE_ID
- **Description**: Azure resource ID for managed private endpoint (optional)
- **Example**: `/subscriptions/.../resourceGroups/.../providers/Microsoft.Storage/storageAccounts/...`
- **Note**: Leave empty if you don't need private endpoints

### PRODUCTION_WORKSPACE_ID
- **Description**: Workspace ID for production deployment (CD workflow)
- **Example**: `12345678-90ab-cdef-1234-567890abcdef`
- **How to get**: Fabric Portal → Your production workspace → Settings → Workspace ID

---

## Setting Up Service Principal Permissions

Your service principal needs the following permissions:

**Fabric Workspace Permissions**: Fabric Administrator or Capacity Administrator role

### Steps to configure:

1. Create an Azure AD App Registration
2. Create a client secret
3. Grant Fabric permissions in the Fabric Admin Portal
4. Add the service principal to your Fabric capacity

## Verification

After configuring secrets, you can verify by:
1. Creating a test branch
2. Checking GitHub Actions logs
3. Verifying workspace creation in Fabric Portal
