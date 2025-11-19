#!/bin/bash
set -euo pipefail

# Load .env file if it exists (for local development)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
if [ -f "${ENV_FILE}" ]; then
  echo "Loading configuration from .env file..."
  set -a  # automatically export all variables
  source "${ENV_FILE}"
  set +a
fi

# Get branch name from environment (set by GitHub Actions) or git
BRANCH_NAME_RAW="${BRANCH_NAME:-$(git branch --show-current)}"

# Sanitize branch name for use in resource names
# - Convert to lowercase
# - Replace slashes, underscores, and spaces with hyphens
# - Remove any characters that aren't alphanumeric or hyphens
# - Remove leading/trailing hyphens
# - Truncate to max 63 characters (common limit for many systems)
BRANCH_NAME_SAFE=$(echo "${BRANCH_NAME_RAW}" | \
  tr '[:upper:]' '[:lower:]' | \
  tr '/' '-' | \
  tr '_' '-' | \
  tr ' ' '-' | \
  sed 's/[^a-z0-9-]//g' | \
  sed 's/^-*//' | \
  sed 's/-*$//' | \
  cut -c1-63)

PROJECT_NAME="${PROJECT_NAME:-DEMO Fabric CICD}"
WORKSPACE_NAME="${PROJECT_NAME}-${BRANCH_NAME_SAFE}.Workspace"

# THESE SHOULD BE SET IN .env FILE (local) OR AS GITHUB SECRETS (CI/CD)
CAPACITY_NAME="${CAPACITY_NAME:-}"
GIT_REPO_OWNER="${GIT_REPO_OWNER:-}"
GIT_REPO_NAME="${GIT_REPO_NAME:-}"
GIT_CONNECTION_NAME="${GIT_CONNECTION_NAME:-}"
SECGROUP_ADMINS_ID="${SECGROUP_ADMINS_ID:-}"
SECGROUP_ADMINS_NAME="${SECGROUP_ADMINS_NAME:-}"

# Optional variables
PE_RESOURCE_ID="${PE_RESOURCE_ID:-}"
SECGROUP_DEVS_ID="${SECGROUP_DEVS_ID:-}"
SECGROUP_DEVS_NAME="${SECGROUP_DEVS_NAME:-}"

echo "========================================="
echo "Starting Fabric CI Pipeline"
echo "========================================="
echo "Branch (raw): ${BRANCH_NAME_RAW}"
echo "Branch (safe): ${BRANCH_NAME_SAFE}"
echo "Workspace: ${WORKSPACE_NAME}"
echo "Capacity: ${CAPACITY_NAME}"
echo "========================================="

# Check if logged in to Fabric CLI
LOGGED_IN=$(fab auth status --output_format json 2>/dev/null | jq -r '.result.data[0].logged_in // false' || echo "false")
if [ "$LOGGED_IN" != "true" ]; then
  echo "Not logged in to Fabric CLI. Attempting login..."
  if [ -n "${TENANT_ID}" ] && [ -n "${CLIENT_ID}" ] && [ -n "${CLIENT_SECRET}" ]; then
    echo "Using service principal authentication..."
    fab auth login -u "$CLIENT_ID" -p "$CLIENT_SECRET" --tenant "$TENANT_ID"
  else
    echo "Using interactive authentication..."
    fab auth login
  fi
  echo "✓ Successfully logged in to Fabric CLI"
else
  echo "✓ Already logged in to Fabric CLI"
fi

# Step 1: Create the workspace
echo "Step 1: Creating workspace..."
fab mkdir ${WORKSPACE_NAME} -P capacityName=${CAPACITY_NAME}
WORKSPACE_ID=$(fab get ${WORKSPACE_NAME} -q id)
echo "✓ Workspace created with ID: ${WORKSPACE_ID}"

# Step 2: Grant admin security group access to the workspace
echo "Step 2: Granting admin access..."
fab api -X post workspaces/${WORKSPACE_ID}/roleAssignments -i '{
  "principal": {
    "displayName": "'${SECGROUP_ADMINS_NAME}'",
    "id": "'${SECGROUP_ADMINS_ID}'",
    "type": "Group",
    "groupDetails": {
      "groupType": "SecurityGroup"
    }
  },
  "role": "Admin"
}'
echo "✓ Admin access granted"

# Step 3: Grant developer security group access to the workspace
if [ -n "${SECGROUP_DEVS_ID}" ] && [ -n "${SECGROUP_DEVS_NAME}" ]; then
  echo "Step 3: Granting developer access..."
  fab api -X post workspaces/${WORKSPACE_ID}/roleAssignments -i '{
    "principal": {
      "displayName": "'${SECGROUP_DEVS_NAME}'",
      "id": "'${SECGROUP_DEVS_ID}'",
      "type": "Group",
      "groupDetails": {
        "groupType": "SecurityGroup"
      }
    },
    "role": "Contributor"
  }'
  echo "✓ Developer access granted"
else
  echo "⊘ Skipping developer access (no dev security group configured)"
fi

# Step 4: Create managed private endpoint
if [ -n "${PE_RESOURCE_ID}" ]; then
  echo "Step 4: Creating managed private endpoint..."
  fab -c "cd ${WORKSPACE_NAME}" \
      -c "create .managedprivateendpoints/pe-belgian-journal-blob.ManagedPrivateEndpoint -P targetprivatelinkresourceid=${PE_RESOURCE_ID},targetsubresourcetype=blob"
  echo "✓ Managed private endpoint created"
else
  echo "⊘ Skipping managed private endpoint (no resource ID configured)"
fi

# Step 5: Create link to git
echo "Step 5: Connecting workspace to Git repository..."
CONNECTION_ID=$(fab get .connections/${GIT_CONNECTION_NAME} -q id)
fab api -X post workspaces/${WORKSPACE_ID}/git/connect -i '{
  "gitProviderDetails": {
    "ownerName": "'${GIT_REPO_OWNER}'",
    "repositoryName": "'${GIT_REPO_NAME}'",
    "gitProviderType": "GitHub",
    "directoryName": "src",
    "branchName": "'${BRANCH_NAME_RAW}'"
  },
  "myGitCredentials": {
    "source": "ConfiguredConnection",
    "connectionId": "'${CONNECTION_ID}'"
  }
}'
echo "✓ Git connection established"

# Step 6: Initialize the connection and populate the workspace with the git repo
echo "Step 6: Initializing Git connection and syncing items..."
fab api -X post workspaces/${WORKSPACE_ID}/git/initializeConnection -i '{
  "initializationStrategy": "PreferRemote"
}'
echo "✓ Git connection initialized"

echo "Step 7: Fetching items from Git..."
REMOTE_COMMIT_HASH=$(fab api workspaces/${WORKSPACE_ID}/git/status | jq -r '.text.remoteCommitHash')
fab api -X post workspaces/${WORKSPACE_ID}/git/updateFromGit -i '{
  "remoteCommitHash": "'${REMOTE_COMMIT_HASH}'"
}'
echo "✓ Items deployed from Git commit: ${REMOTE_COMMIT_HASH}"

echo "========================================="
echo "✓ CI Pipeline Completed Successfully!"
echo "========================================="
echo "Workspace: ${WORKSPACE_NAME}"
echo "Workspace ID: ${WORKSPACE_ID}"
echo "Branch (raw): ${BRANCH_NAME_RAW}"
echo "Branch (safe): ${BRANCH_NAME_SAFE}"
echo "Commit: ${REMOTE_COMMIT_HASH}"
echo "========================================="

