#!/bin/bash
# set -euo pipefail

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

echo "========================================="
echo "Starting Fabric Cleanup Pipeline"
echo "========================================="
echo "Branch (raw): ${BRANCH_NAME_RAW}"
echo "Branch (safe): ${BRANCH_NAME_SAFE}"
echo "Workspace to delete: ${WORKSPACE_NAME}"
echo "========================================="

# Ensure logged in to Fabric CLI
ensure_fabric_login

# Check if workspace exists
echo "Checking if workspace exists..."
WORKSPACE_EXISTS=$(fab ls | grep "${WORKSPACE_NAME}" || echo "")

if [ -z "${WORKSPACE_EXISTS}" ]; then
  echo "⚠ Workspace '${WORKSPACE_NAME}' not found. Nothing to delete."
  echo "This may be expected if:"
  echo "  - The workspace was already deleted"
  echo "  - The workspace was never created"
  echo "  - The branch name doesn't match a feature branch pattern"
  exit 0
fi

# Delete the workspace
delete_workspace "${WORKSPACE_NAME}"

echo "========================================="
echo "Cleanup completed successfully!"
echo "========================================="
