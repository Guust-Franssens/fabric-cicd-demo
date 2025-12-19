# Load common utility functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.bash"

# Load environment variables
load_env

# Set workspace ID based on environment
case "${ENVIRONMENT}" in
  prod)
    TARGET_WORKSPACE_ID="${PROD_WORKSPACE_ID}"
    TARGET_WORKSPACE_NAME="${PROJECT_NAME}-prod.workspace"
    ;;
  dev)
    TARGET_WORKSPACE_ID="${DEV_WORKSPACE_ID}"
    TARGET_WORKSPACE_NAME="${PROJECT_NAME}-dev.workspace"
    ;;
  test)
    TARGET_WORKSPACE_ID="${TEST_WORKSPACE_ID}"
    TARGET_WORKSPACE_NAME="${PROJECT_NAME}-test.workspace"
    ;;
  *)
    echo "Error: Unknown environment '${ENVIRONMENT}'. Must be 'prod', 'dev', or 'test'."
    return 1 2>/dev/null || exit 1
    ;;
esac

echo "Deploying to environment: ${ENVIRONMENT}"
echo "Target workspace ID: ${TARGET_WORKSPACE_ID}"
echo "Workspace name: ${TARGET_WORKSPACE_NAME}"

# Ensure logged in to Fabric CLI
ensure_fabric_login

RESPONSE=$(fab api workspaces/${TARGET_WORKSPACE_ID}/git/status)
REMOTE_COMMIT_HASH=$(echo "${RESPONSE}" | jq -r '.text.remoteCommitHash' | tr -d '\r\n')
WORKSPACE_HEAD=$(echo "${RESPONSE}" | jq -r '.text.workspaceHead' | tr -d '\r\n')

BODY='{
  "remoteCommitHash": "'${REMOTE_COMMIT_HASH}'",
  "workspaceHead": "'${WORKSPACE_HEAD}'",
  "allowOverrideItems": true,
  "conflictResolution": {
    "conflictResolutionType": "Workspace",
    "conflictResolutionPolicy": "PreferRemote"
  }
}'
RESPONSE=$(fab api -X post workspaces/${TARGET_WORKSPACE_ID}/git/updateFromGit -i "${BODY}")
if [ "$STATUS_CODE" -ge 200 ] && [ "$STATUS_CODE" -lt 300 ]; then
  echo "✓ Successfully updated '${TARGET_WORKSPACE_NAME}'"
else
  echo "✗ Update failed with status code: $STATUS_CODE"
  echo "$RESPONSE" | jq '.'  # Print full error response
  return 1 2>/dev/null || exit 1
fi