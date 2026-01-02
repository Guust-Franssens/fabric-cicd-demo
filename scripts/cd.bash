# Load common utility functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.bash"

# Load environment variables
load_env

# THESE SHOULD BE SET IN .env FILE (local) OR AS GITHUB SECRETS (CI/CD)
CAPACITY_NAME="${CAPACITY_NAME:-}"
export SECGROUP_ADMINS_ID="${SECGROUP_ADMINS_ID:-}"

# Validate environment
if [[ "${ENVIRONMENT}" != "prod" && "${ENVIRONMENT}" != "ppe" ]]; then
  echo "Error: Unknown environment '${ENVIRONMENT}'. Must be 'prod' or 'ppe'."
  return 1 2>/dev/null || exit 1
fi

# Set workspace ID based on environment
TARGET_WORKSPACE_NAME="${PROJECT_NAME}-${ENVIRONMENT}.workspace"

echo "Deploying to environment: ${ENVIRONMENT}"
echo "Workspace name: ${TARGET_WORKSPACE_NAME}"

# Ensure logged in to Fabric CLI
ensure_fabric_login

# Ensure workspace exists, if not create it
WORKSPACE_EXISTS=$(fab exists ${TARGET_WORKSPACE_NAME} --output_format json | jq -r '.result.message')
if [[ "${WORKSPACE_EXISTS}" == "false" ]]; then
  echo "Workspace ${TARGET_WORKSPACE_NAME} does not exist. Creating..."
  fab mkdir ${TARGET_WORKSPACE_NAME} -P capacityName=${CAPACITY_NAME}

  # The dev group are viewers in deployed to workspaces (ppe/prod)
  fab acl set ${TARGET_WORKSPACE_NAME} --identity "${SECGROUP_ADMINS_ID}" --role admin --force
  if [ -n "${SECGROUP_DEVS_ID}" ]; then
    fab acl set ${TARGET_WORKSPACE_NAME} --identity "${SECGROUP_DEVS_ID}" --role viewer --force
  fi

  if [ -n "${PE_KEYVAULT_RESOURCE_ID}" ]; then
    fab create ${TARGET_WORKSPACE_NAME}/.managedprivateendpoints/mpe-keyvault.ManagedPrivateEndpoint \
      -P targetprivatelinkresourceid=${PE_KEYVAULT_RESOURCE_ID},targetsubresourcetype=vault,autoApproveEnabled=true
  fi
fi

# Deploy items to the target workspace
python "${SCRIPT_DIR}/deploy.py" --workspace-name "${TARGET_WORKSPACE_NAME}"
