# Fabric CI/CD Demo

This repository showcases how a Microsoft Fabric CI/CD flow can work using the Fabric CLI and GitHub Actions.

## Overview

This project implements a complete CI/CD pipeline for Microsoft Fabric workspaces:

- **CI (Continuous Integration)**: Automatically creates feature workspaces when new branches are created
- **CD (Continuous Deployment)**: Deploys to production workspace when changes are merged to `main`

## Architecture

### CI Flow (Feature Branches)
1. Developer creates a new feature branch (e.g., `feature/new-dashboard`)
2. GitHub Actions triggers automatically
3. A new Fabric workspace is created with the branch name
4. Workspace is connected to the Git repository
5. All Fabric items are deployed from the `src/` directory
6. Security groups are assigned appropriate permissions

### CD Flow (Production)
1. Pull request is merged to `main` branch
2. GitHub Actions triggers deployment
3. Production workspace is synced with latest Git changes
4. Items are updated in the production environment

## Setup

### Prerequisites

- Microsoft Fabric capacity
- Azure service principal with Fabric permissions
- GitHub repository with appropriate secrets configured
- Fabric CLI knowledge

### Required GitHub Secrets

Configure these secrets in your GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

#### Authentication
- `FABRIC_CLIENT_ID` - Azure service principal client ID
- `FABRIC_CLIENT_SECRET` - Azure service principal client secret
- `FABRIC_TENANT_ID` - Azure AD tenant ID

#### Fabric Configuration
- `PROJECT_NAME` - Your project name (used as workspace prefix)
- `CAPACITY_NAME` - Fabric capacity name (e.g., `fabsweden.Capacity`)
- `GIT_CONNECTION_NAME` - Name of the Git connection in Fabric

#### Security Groups
- `SECGROUP_ADMINS_ID` - Azure AD group ID for workspace admins
- `SECGROUP_ADMINS_NAME` - Azure AD group name for workspace admins
- `SECGROUP_DEVS_ID` - (Optional) Azure AD group ID for developers
- `SECGROUP_DEVS_NAME` - (Optional) Azure AD group name for developers

#### Optional Configuration
- `PE_RESOURCE_ID` - (Optional) Resource ID for managed private endpoint
- `PRODUCTION_WORKSPACE_ID` - Workspace ID for production deployment

## Usage

### Creating a Feature Workspace

```bash
# Create a new feature branch
git checkout -b feature/my-new-feature

# Push to GitHub
git push -u origin feature/my-new-feature
```

The GitHub Actions workflow will automatically:
1. Create a new Fabric workspace named `{PROJECT_NAME}.Workspace`
2. Connect it to your Git repository on the `feature/my-new-feature` branch
3. Deploy all items from the `src/` directory
4. Assign appropriate permissions

### Deploying to Production

```bash
# Merge your feature branch to main
git checkout main
git merge feature/my-new-feature
git push origin main
```

The CD workflow will update the production workspace with the latest changes.

### Manual Execution

You can also run the scripts manually:

```bash
# Run CI script locally
export PROJECT_NAME="MyProject"
export CAPACITY_NAME="fabsweden.Capacity"
# ... set other environment variables
./scripts/ci.bash

# Run CD script locally
export PRODUCTION_WORKSPACE_ID="your-workspace-id"
./scripts/cd.bash
```

## Project Structure

```
.
├── .github/
│   └── workflows/
│       ├── fabric-ci.yml    # CI workflow for feature branches
│       └── fabric-cd.yml    # CD workflow for production
├── scripts/
│   ├── ci.bash              # CI script - creates feature workspaces
│   └── cd.bash              # CD script - deploys to production
├── src/                     # Fabric items (notebooks, reports, etc.)
└── README.md
```

## Workflow Details

### CI Workflow (`fabric-ci.yml`)

**Triggers:**
- Branch creation
- Push to branches matching `feature/**` or `dev/**`

**Steps:**
1. Checkout code
2. Install Fabric CLI
3. Authenticate with service principal
4. Run `ci.bash` script
5. Generate deployment summary

### CD Workflow (`fabric-cd.yml`)

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

**Steps:**
1. Checkout code
2. Install Fabric CLI
3. Authenticate with service principal
4. Run `cd.bash` script
5. Generate deployment summary

## Fabric Items

Place your Fabric items in the `src/` directory:
- Notebooks (`.ipynb`)
- Lakehouses
- Data pipelines
- Semantic models
- Reports
- Dataflows

These will be automatically deployed to workspaces through Git integration.

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify service principal credentials
   - Ensure service principal has Fabric workspace permissions

2. **Workspace Creation Failed**
   - Check capacity name is correct
   - Verify sufficient capacity resources

3. **Git Connection Failed**
   - Ensure Git connection exists in Fabric
   - Verify repository name and owner are correct

4. **Permission Issues**
   - Verify security group IDs are correct
   - Ensure service principal has permission to assign roles

## Best Practices

1. **Branch Naming**: Use descriptive feature branch names (e.g., `feature/add-sales-report`)
2. **Security**: Never commit secrets to the repository
3. **Testing**: Test changes in feature workspaces before merging to main
4. **Cleanup**: Regularly delete unused feature workspaces to save capacity
5. **Git Structure**: Organize Fabric items logically in the `src/` directory

## Contributing

1. Create a feature branch
2. Make your changes
3. Test in the automatically created feature workspace
4. Submit a pull request
5. After approval, merge to main for production deployment

## License

This is a demo project for educational purposes.