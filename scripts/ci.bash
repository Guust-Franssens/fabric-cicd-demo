set -e

# Load common utility functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.bash"

# Load environment variables
load_env

# Get branch name from environment (set by GitHub Actions) or git
BRANCH_NAME_RAW="${BRANCH_NAME:-$(git branch --show-current)}"

# Sanitize branch name for use in resource names
BRANCH_NAME_SAFE=$(sanitize_branch_name "${BRANCH_NAME_RAW}")

PROJECT_NAME="${PROJECT_NAME:-DEMO Fabric CICD}"
WORKSPACE_NAME=$(generate_workspace_name "${PROJECT_NAME}" "${BRANCH_NAME_SAFE}")

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

# Ensure logged in to Fabric CLI
ensure_fabric_login

# Step 1: Create the workspace
echo "Step 1: Creating workspace with name ${WORKSPACE_NAME}..."
fab mkdir ${WORKSPACE_NAME} -P capacityName=${CAPACITY_NAME}
WORKSPACE_ID=$(fab get ${WORKSPACE_NAME} -q id | tr -d '\r\n')
echo "✓ Workspace created with ID: ${WORKSPACE_ID}"

# Step 2: Grant admin security group access to the workspace
echo "Step 2 setting workspace accesses..."
fab acl set ${WORKSPACE_NAME} --identity "${SECGROUP_ADMINS_ID}" --role admin --force

# Step 3: Grant developer security group access to the workspace
if [ -n "${SECGROUP_DEVS_ID}" ]; then
  fab acl set ${WORKSPACE_NAME} --identity "${SECGROUP_DEVS_ID}" --role contributor --force
else
  echo "⊘ Skipping developer access (no dev security group configured)"
fi

# Step 4: Create keyvault managed private endpoint
if [ -n "${PE_KEYVAULT_RESOURCE_ID}" ]; then
  echo "Step 4: Creating managed private endpoint..."
  fab create ${WORKSPACE_NAME}/.managedprivateendpoints/mpe-keyvault.ManagedPrivateEndpoint \
    -P targetprivatelinkresourceid=${PE_KEYVAULT_RESOURCE_ID},targetsubresourcetype=vault,autoApproveEnabled=true
else
  echo "⊘ Skipping managed private endpoint (no resource ID configured)"
fi

# Step 5: Create link to git
echo "Step 5: Connecting workspace to Git repository..."
CONNECTION_ID=$(fab get .connections/${GIT_CONNECTION_NAME} -q id | tr -d '\r\n')
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
REMOTE_COMMIT_HASH=$(fab api workspaces/${WORKSPACE_ID}/git/status | jq -r '.text.remoteCommitHash' | tr -d '\r\n')
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

set +e
