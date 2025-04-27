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
MODEL=""
MAX_OUTPUT_TOKENS=""
USE_HELM="false" # Default to false

# --- Script Configuration ---
LOCK_DIR="/tmp/workflow_runner.lock"
DOCKER_SERVICE_NAME="backend-service" # Name of the service in docker-compose.yml

# --- Helper Functions ---
usage() {
  echo "Usage: $0 --workflow <type> --task_dir <dir> --bounty_number <num> --model <model_name> --max_output_tokens <tokens> [--use_helm <true|false>]"
  echo ""
  echo "Arguments:"
  echo "  --workflow          : Workflow type (e.g., patch_workflow, exploit_workflow, detect_workflow)"
  echo "  --task_dir          : Task directory relative to bountybench/ (e.g., mlflow, django)"
  echo "  --bounty_number     : Bounty number (integer)"
  echo "  --model             : Model identifier (e.g., openai/gpt-4.1-2025-04-14)"
  echo "  --max_output_tokens : Maximum output tokens (integer)"
  echo "  --use_helm          : Set to 'true' to enable Helm, 'false' otherwise (default: false)"
  echo ""
  echo "Example:"
  echo "  $0 --workflow patch_workflow --task_dir mlflow --bounty_number 0 --model openai/o3-2025-04-16-high-reasoning-effort --max_output_tokens 16384 --use_helm false"
  exit 1
}

cleanup() {
  echo "Cleaning up lock directory..."
  # Check if the directory exists before trying to remove it
  if [ -d "$LOCK_DIR" ]; then
      rmdir "$LOCK_DIR" || echo "Warning: Could not remove lock directory '$LOCK_DIR'. It might have been removed already or another process holds it."
  fi
}

# --- Argument Parsing (Revised) ---
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --workflow)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      WORKFLOW="$2"
      shift # past argument
      shift # past value
      ;;
    --task_dir)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      TASK_DIR="$2"
      shift # past argument
      shift # past value
      ;;
    --bounty_number)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      BOUNTY_NUM="$2"
      shift # past argument
      shift # past value
      ;;
    --model)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      MODEL="$2"
      shift # past argument
      shift # past value
      ;;
    --max_output_tokens)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      MAX_OUTPUT_TOKENS="$2"
      shift # past argument
      shift # past value
      ;;
    --use_helm)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      USE_HELM=$(echo "$2" | tr '[:upper:]' '[:lower:]')
      # Validate the value immediately
      if [[ "$USE_HELM" != "true" && "$USE_HELM" != "false" ]]; then
          echo "Error: --use_helm must be 'true' or 'false', received '$2'."
          usage
      fi
      shift # past argument
      shift # past value
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
# Check if required arguments were successfully parsed
if [ -z "$WORKFLOW" ] || [ -z "$TASK_DIR" ] || [ -z "$BOUNTY_NUM" ] || [ -z "$MODEL" ] || [ -z "$MAX_OUTPUT_TOKENS" ]; then
  echo "Error: Missing one or more required arguments."
  # Be more specific about which arguments are missing
  [ -z "$WORKFLOW" ] && echo "  --workflow is missing"
  [ -z "$TASK_DIR" ] && echo "  --task_dir is missing"
  [ -z "$BOUNTY_NUM" ] && echo "  --bounty_number is missing"
  [ -z "$MODEL" ] && echo "  --model is missing"
  [ -z "$MAX_OUTPUT_TOKENS" ] && echo "  --max_output_tokens is missing"
  usage # Exit using the usage function
fi

# Model/Helm specific validation (ensure USE_HELM is checked after it's potentially set)
if [[ "$USE_HELM" == "true" && "$MODEL" != "deepseek-ai/deepseek-r1" ]]; then
    echo "Error: When --use_helm is true, --model must be 'deepseek-ai/deepseek-r1'."
    exit 1
fi

if [[ "$MODEL" == "openai/o3-2025-04-16-high-reasoning-effort" && "$USE_HELM" == "true" ]]; then
    echo "Error: Model 'openai/o3-2025-04-16-high-reasoning-effort' must be run with --use_helm false."
    exit 1
fi


# --- Locking Mechanism ---
# Try to create the lock directory atomically. If it fails, another instance is running.
if ! mkdir "$LOCK_DIR"; then
  echo "Error: Another instance of the script is already running (Lock directory '$LOCK_DIR' exists)."
  # Attempt cleanup in case the lock dir was stale, but still exit
  cleanup
  exit 1
fi
# Ensure cleanup runs on script exit (normal or error)
trap cleanup EXIT SIGINT SIGTERM

# --- Main Execution ---
echo "Starting workflow run..."
echo "  Workflow: $WORKFLOW"
echo "  Task Dir: $TASK_DIR"
echo "  Bounty #: $BOUNTY_NUM"
echo "  Model:    $MODEL"
echo "  Max Out:  $MAX_OUTPUT_TOKENS"
echo "  Use Helm: $USE_HELM"

# 1. Stop existing containers
echo "Stopping Docker containers..."
docker compose down

# 2. Start containers in detached mode
echo "Starting Docker containers..."
docker compose up -d

# 3. Build the python command
echo "Building Python execution command..."
# Use an array for the command to handle spaces and quotes robustly
PYTHON_CMD_ARGS=(
    python -m workflows.runner
    --workflow-type "$WORKFLOW"
    --task_dir "bountybench/$TASK_DIR"
    --bounty_number "$BOUNTY_NUM"
    --model "$MODEL"
    --phase_iterations 100
    --max_input_tokens 8192
    --max_output_tokens "$MAX_OUTPUT_TOKENS"
    --logging_level DEBUG
)

# Conditionally add the --use_helm flag
if [[ "$USE_HELM" == "true" ]]; then
  PYTHON_CMD_ARGS+=(--use_helm) # Add flag as a separate element
  echo "  (Helm flag added)"
fi

# 4. Execute the command inside the container
echo "Executing command in container '$DOCKER_SERVICE_NAME'..."
# Use 'docker exec -i'. Pass the command arguments correctly quoted.
# Using "${PYTHON_CMD_ARGS[@]}" ensures each argument is passed as a separate word.
docker exec -i "$DOCKER_SERVICE_NAME" /bin/bash -c "${PYTHON_CMD_ARGS[*]}"


echo "Workflow run completed successfully."

# The 'trap cleanup EXIT' will automatically remove the lock directory now

exit 0
