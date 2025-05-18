#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
# Temporarily disable 'set -u' during argument parsing as it can cause issues
# if optional arguments are not provided. It will be re-enabled later.
set +u
# Cause pipelines to fail if any command fails, not just the last one.
set -o pipefail

# --- Default Values ---
WORKFLOW=""
TASK_DIR=""
BOUNTY_NUM=""
USE_HELM="false" # Default to false
USE_CWE="false"  # Default to false

# --- Script Configuration ---
LOCK_DIR="/tmp/workflow_runner.lock"
DOCKER_SERVICE_NAME="backend-service" # Name of the service in docker-compose.yml

# --- Helper Functions ---
usage() {
  echo "Usage: $0 --workflow <type> --task_dir <dir> --bounty_number <num> [--use_helm <true|false>] [--use_cwe <true|false>]"
  echo ""
  echo "Arguments:"
  echo "  --workflow          : Workflow type (e.g., patch_workflow, exploit_workflow, detect_workflow)"
  echo "  --task_dir          : Task directory relative to bountytasks/ (e.g., mlflow, django)"
  echo "  --bounty_number     : Bounty number (integer)"
  echo "  --use_helm          : Set to 'true' to enable Helm, 'false' otherwise (default: false)"
  echo "  --use_cwe           : Set to 'true' to pass CWE to the workflow, 'false' otherwise (default: false)"
  echo ""
  echo "Example:"
  echo "  $0 --workflow patch_workflow --task_dir mlflow --bounty_number 0 --use_helm false --use_cwe false"
  exit 1
}

cleanup() {
  echo "Cleaning up lock directory..."
  # Check if the directory exists before trying to remove it
  if [ -d "$LOCK_DIR" ]; then
      rmdir "$LOCK_DIR" || echo "Warning: Could not remove lock directory '$LOCK_DIR'. It might have been removed already or another process holds it."
  fi
  # Ensure containers are stopped on exit/error
  echo "Stopping Docker containers (cleanup)..."
  docker compose down
}

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --workflow)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      WORKFLOW="$2"
      shift 2
      ;;
    --task_dir)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      TASK_DIR="$2"
      shift 2
      ;;
    --bounty_number)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      BOUNTY_NUM="$2"
      shift 2
      ;;
    --use_helm)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      USE_HELM=$(echo "$2" | tr '[:upper:]' '[:lower:]')
      if [[ "$USE_HELM" != "true" && "$USE_HELM" != "false" ]]; then
          echo "Error: --use_helm must be 'true' or 'false', received '$2'."
          usage
      fi
      shift 2
      ;;
    --use_cwe)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      USE_CWE=$(echo "$2" | tr '[:upper:]' '[:lower:]')
      if [[ "$USE_CWE" != "true" && "$USE_CWE" != "false" ]]; then
          echo "Error: --use_cwe must be 'true' or 'false', received '$2'."
          usage
      fi
      shift 2
      ;;
    *)    # unknown option
      echo "Error: Unknown option: $1"
      usage
      ;;
  esac
done

# Re-enable treating unset variables as errors now that parsing is done
set -u

# --- Input Validation ---
if [ -z "$WORKFLOW" ] || [ -z "$TASK_DIR" ] || [ -z "$BOUNTY_NUM" ]; then
  echo "Error: Missing one or more required arguments."
  [ -z "$WORKFLOW" ] && echo "  --workflow is missing"
  [ -z "$TASK_DIR" ] && echo "  --task_dir is missing"
  [ -z "$BOUNTY_NUM" ] && echo "  --bounty_number is missing"
  usage # Exit using the usage function
fi

# --- Locking Mechanism ---
if ! mkdir "$LOCK_DIR"; then
  echo "Error: Another instance of the script is already running (Lock directory '$LOCK_DIR' exists)."
  cleanup
  exit 1
fi
trap cleanup EXIT SIGINT SIGTERM

# --- Main Execution ---
echo "Starting workflow run..."
echo "  Workflow: $WORKFLOW"
echo "  Task Dir: $TASK_DIR"
echo "  Bounty #: $BOUNTY_NUM"
echo "  Use Helm: $USE_HELM"
echo "  Use CWE: $USE_CWE"

# 1. Stop existing containers
echo "Stopping Docker containers..."
docker compose down

# 2. Start containers in detached mode
echo "Starting Docker containers..."
docker compose up -d

# 3. Build the python command
echo "Building Python execution command..."
PYTHON_CMD_ARGS=(
    python -m workflows.runner
    --workflow-type "$WORKFLOW"
    --task_dir "bountytasks/$TASK_DIR"
    --bounty_number "$BOUNTY_NUM"
    --phase_iterations 2
    --logging_level DEBUG
    --custom_agent "claude_code"
    #--include_report_title_in_cwe
)

# Conditionally add the --use_helm flag
if [[ "$USE_HELM" == "true" ]]; then
  PYTHON_CMD_ARGS+=(--use_helm)
  echo "  (Helm flag added)"
fi

if [[ "$USE_CWE" == "true" ]]; then
  PYTHON_CMD_ARGS+=(--use_cwe)
  echo "  (use_cwe flag added)"
fi

# 4. Execute the command inside the container
extra_cmd = ""
KEY = ""
API_KEY_NAME = "ANTHROPIC_API_KEY"
if KEY:
  extra_cmd = "export ${API_KEY_NAME}=${KEY} && "
echo "Executing command in container '$DOCKER_SERVICE_NAME'..."
docker exec -i "$DOCKER_SERVICE_NAME" /bin/bash -c "${extra_cmd}${PYTHON_CMD_ARGS[*]}"

echo "Workflow run completed successfully."

exit 0
