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
MODEL="" # Store the final model name (potentially adjusted for DeepSeek casing)
# MAX_OUTPUT_TOKENS is now determined automatically
USE_HELM="false" # Default to false

# --- Script Configuration ---
LOCK_DIR="/tmp/workflow_runner.lock"
DOCKER_SERVICE_NAME="backend-service" # Name of the service in docker-compose.yml

# --- Helper Functions ---
usage() {
  echo "Usage: $0 --workflow <type> --task_dir <dir> --bounty_number <num> --model <model_name> [--use_helm <true|false>]"
  echo ""
  echo "Arguments:"
  echo "  --workflow          : Workflow type (e.g., patch_workflow, exploit_workflow, detect_workflow)"
  echo "  --task_dir          : Task directory relative to bountybench/ (e.g., mlflow, django)"
  echo "  --bounty_number     : Bounty number (integer)"
  echo "  --model             : Full model identifier (e.g., openai/gpt-4.1-2025-04-14, deepseek-ai/DeepSeek-R1)."
  echo "                      : (Note: Casing for deepseek-ai/deepseek-r1 will be adjusted based on --use_helm)"
  echo "  --use_helm          : Set to 'true' to enable Helm, 'false' otherwise (default: false)"
  echo ""
  echo "Example:"
  echo "  $0 --workflow patch_workflow --task_dir mlflow --bounty_number 0 --model openai/o3-2025-04-16-high-reasoning-effort --use_helm false"
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
    --model)
      if [[ -z "$2" || "$2" == --* ]]; then echo "Error: Argument for $1 is missing" >&2; usage; fi
      MODEL="$2"
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
    *)    # unknown option
      echo "Error: Unknown option: $1"
      usage
      ;;
  esac
done

# Re-enable treating unset variables as errors now that parsing is done
set -u

# --- Input Validation ---
if [ -z "$WORKFLOW" ] || [ -z "$TASK_DIR" ] || [ -z "$BOUNTY_NUM" ] || [ -z "$MODEL" ]; then
  echo "Error: Missing one or more required arguments."
  [ -z "$WORKFLOW" ] && echo "  --workflow is missing"
  [ -z "$TASK_DIR" ] && echo "  --task_dir is missing"
  [ -z "$BOUNTY_NUM" ] && echo "  --bounty_number is missing"
  [ -z "$MODEL" ] && echo "  --model is missing"
  usage # Exit using the usage function
fi

# --- Model Name Adjustment and Token Logic ---
MODEL_INPUT_LOWER=$(echo "$MODEL" | tr '[:upper:]' '[:lower:]')

# Handle DeepSeek model name casing *only* if input matches exactly (case-insensitive)
if [[ "$MODEL_INPUT_LOWER" == "deepseek-ai/deepseek-r1" ]]; then
    if [[ "$USE_HELM" == "true" ]]; then
        MODEL="deepseek-ai/deepseek-r1" # Lowercase for Helm
        echo "Info: Input matches 'deepseek-ai/deepseek-r1' and --use_helm=true. Using model name: $MODEL"
    else
        MODEL="deepseek-ai/DeepSeek-R1" # non-Helm
        echo "Info: Input matches 'deepseek-ai/deepseek-r1' and --use_helm=false. Using model name: $MODEL"
    fi
fi

case "$MODEL" in
    "anthropic/claude-3-7-sonnet-20250219" | "openai/gpt-4.1-2025-04-14")
        MAX_OUTPUT_TOKENS="8192"
        ;;
    "openai/o3-2025-04-16-high-reasoning-effort" | "google/gemini-2.5-pro-preview-03-25" | "deepseek-ai/deepseek-r1" | "deepseek-ai/DeepSeek-R1" | "openai/o4-mini-2025-04-16-high-reasoning-effort" | "anthropic/claude-3-7-sonnet-20250219-extended-thinking")
        MAX_OUTPUT_TOKENS="8192"
        ;;
    *)
        echo "Error: Unknown or unsupported model '$MODEL' provided. Cannot determine max_output_tokens."
        echo "Supported models for automatic token setting: anthropic/claude-3-7-sonnet-20250219, openai/gpt-4.1-2025-04-14, openai/o3-2025-04-16-high-reasoning-effort, google/gemini-2.5-pro-preview-03-25, deepseek-ai/DeepSeek-R1, deepseek-ai/deepseek-r1, openai/o4-mini-2025-04-16-high-reasoning-effort, anthropic/claude-3-7-sonnet-20250219-extended-thinking"
        exit 1
        ;;
esac
echo "Info: Automatically set max_output_tokens to $MAX_OUTPUT_TOKENS for model $MODEL"


# --- Specific Model/Helm Validations & Warnings ---

# Check for Anthropic + Helm incompatibility
if [[ "$MODEL" == "anthropic/"* && "$USE_HELM" == "true" ]]; then
    echo "Error: Anthropic models (like '$MODEL') cannot be run with --use_helm=true."
    exit 1
fi

# Warning for o3 + helm
if [[ "$MODEL" == "openai/o3-2025-04-16-high-reasoning-effort" && "$USE_HELM" == "true" ]]; then
    echo "Warning: Running model '$MODEL' with --use_helm=true. Reasoning token usage will not be shown."
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
echo "  Model:    $MODEL"        # Use the potentially adjusted model name
echo "  Max Out:  $MAX_OUTPUT_TOKENS" # Use the determined token count
echo "  Use Helm: $USE_HELM"

# 1. Stop existing containers
echo "Stopping Docker containers..."
docker compose down backend

# 2. Start containers in detached mode
echo "Starting Docker containers..."
# docker volume create is idempotent
docker volume create dind-data
docker compose up -d backend

# 3. Build the python command
echo "Building Python execution command..."
PYTHON_CMD_ARGS=(
    python -m workflows.runner
    --workflow-type "$WORKFLOW"
    --task_dir "bountybench/$TASK_DIR"
    --bounty_number "$BOUNTY_NUM"
    --model "$MODEL"
    --phase_iterations 100
    --max_input_tokens 8192
    --max_output_tokens "$MAX_OUTPUT_TOKENS" # Use the determined token count
    --logging_level DEBUG
)

# Conditionally add the --use_helm flag
if [[ "$USE_HELM" == "true" ]]; then
  PYTHON_CMD_ARGS+=(--use_helm)
  echo "  (Helm flag added)"
fi

# 4. Execute the command inside the container
echo "Executing command in container '$DOCKER_SERVICE_NAME'..."
docker exec -i "$DOCKER_SERVICE_NAME" /bin/bash -c "${PYTHON_CMD_ARGS[*]}"

echo "Workflow run completed successfully."

exit 0
