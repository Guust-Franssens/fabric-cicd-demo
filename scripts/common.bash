#!/bin/bash
# Common utility functions for Fabric CI/CD scripts

# Get the script directory (where this common.bash file is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env file if it exists (for local development)
load_env() {
  local ENV_FILE="${SCRIPT_DIR}/../.env"
  if [ -f "${ENV_FILE}" ]; then
    echo "Loading configuration from .env file..."
    set -a  # automatically export all variables
    source "${ENV_FILE}"
    set +a
  fi
}

# Sanitize branch name for use in resource names
# - Convert to lowercase
# - Replace slashes, underscores, and spaces with hyphens
# - Remove any characters that aren't alphanumeric or hyphens
# - Remove leading/trailing hyphens
# - Truncate to max 63 characters (common limit for many systems)
sanitize_branch_name() {
  local branch_name_raw="$1"
  echo "${branch_name_raw}" | \
    tr '[:upper:]' '[:lower:]' | \
    tr '/' '-' | \
    tr '_' '-' | \
    tr ' ' '-' | \
    sed 's/[^a-z0-9-]//g' | \
    sed 's/^-*//' | \
    sed 's/-*$//' | \
    cut -c1-63
}

# Generate workspace name from project name and branch name
generate_workspace_name() {
  local project_name="$1"
  local branch_name_safe="$2"
  echo "${project_name}-${branch_name_safe}.Workspace"
}

# Check if logged in to Fabric CLI and login if needed
ensure_fabric_login() {
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
}

delete_workspace() {
  local workspace_name="$1"
  echo "Deleting workspace '${workspace_name}'..."
  MPE_LIST=$(fab ls "${workspace_name}/.managedprivateendpoints")
  if [ -n "$MPE_LIST" ]; then
      for mpe in $MPE_LIST; do
          fab rm "${workspace_name}/.managedprivateendpoints/${mpe}" --force
      done
  fi
  fab rm --force "${workspace_name}"
  echo "✓ Workspace deleted successfully"
}