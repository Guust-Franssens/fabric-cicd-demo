# Load .env file if it exists (for local development)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
if [ -f "${ENV_FILE}" ]; then
  echo "Loading configuration from .env file..."
  set -a  # automatically export all variables
  source "${ENV_FILE}"
  set +a
fi

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
STATUS_CODE=$(echo "$RESPONSE" | jq -r '.status_code' | tr -d '\r\n')
if [ "$STATUS_CODE" -ge 200 ] && [ "$STATUS_CODE" -lt 300 ]; then
  echo "✓ Successfully updated '${TARGET_WORKSPACE_NAME}'"
else
  echo "✗ Update failed with status code: $STATUS_CODE"
  echo "$RESPONSE" | jq '.'  # Print full error response
  return 1 2>/dev/null || exit 1
fi
