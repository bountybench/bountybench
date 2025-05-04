#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run_all_bounties_for_workflow.sh <workflow_type> <expected_agent_commit>

# Expect workflow type and expected agent commit
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <workflow_type> <expected_agent_commit>"
  echo "Allowed workflows: detect_workflow detect_patch_workflow exploit_workflow patch_workflow"
  exit 1
fi

WORKFLOW="$1"
EXPECTED_AGENT_COMMIT="$2"

# Validate workflow type
ALLOWED_WORKFLOWS=("detect_workflow" "detect_patch_workflow" "exploit_workflow" "patch_workflow")
VALID=false
for w in "${ALLOWED_WORKFLOWS[@]}"; do
  if [ "$w" = "$WORKFLOW" ]; then
    VALID=true
    break
  fi
done
if [ "$VALID" != "true" ]; then
  echo "Error: Invalid workflow type: $WORKFLOW"
  echo "Allowed workflows: ${ALLOWED_WORKFLOWS[*]}"
  exit 1
fi

# Check bountybench submodule commit
SUBMODULE_DIR="bountybench"
EXPECTED_COMMIT="662c9d045813bbb0f1cebad09236ca24842bfb2a"
if [ ! -d "$SUBMODULE_DIR" ]; then
  echo "Error: Submodule directory '$SUBMODULE_DIR' not found"
  exit 1
fi

pushd "$SUBMODULE_DIR" > /dev/null
CURRENT_COMMIT=$(git rev-parse HEAD)
popd > /dev/null

if [ "$CURRENT_COMMIT" != "$EXPECTED_COMMIT" ]; then
  echo "Error: bountybench submodule is at commit $CURRENT_COMMIT, expected $EXPECTED_COMMIT"
  exit 1
fi

# Check bounty agent repo commit against expected input
REPO_ROOT="$(git rev-parse --show-toplevel)"
CURRENT_AGENT_COMMIT="$(cd "$REPO_ROOT" && git rev-parse HEAD)"
if [ "$CURRENT_AGENT_COMMIT" != "$EXPECTED_AGENT_COMMIT" ]; then
  echo "Error: bounty agent repo is at commit $CURRENT_AGENT_COMMIT, expected $EXPECTED_AGENT_COMMIT"
  exit 1
fi

echo "Building Docker containers..."
docker compose up --build -d

# Directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# List of tasks to run
TASKS=(
  "InvokeAI/0"
  "LibreChat/0"
  "LibreChat/1"
  "LibreChat/3"
  "agentscope/0"
  "astropy/0"
  "bentoml/0"
  "bentoml/1"
  "composio/0"
  "fastapi/0"
  "gluon-cv/0"
  "gunicorn/0"
  "kedro/0"
  "lunary/0"
  "lunary/1"
  "lunary/2"
  "mlflow/0"
  "mlflow/1"
  "mlflow/2"
  "mlflow/3"
  "parse-url/0"
  "scikit-learn/0"
  "setuptools/0"
  "undici/0"
  "vllm/0"
  "yaml/0"
  "zipp/0"
  "gradio/0"
  "gradio/1"
  "gradio/2"
  "gpt_academic/0"
)

for task in "${TASKS[@]}"; do
  REPO="${task%%/*}"
  BOUNTY="${task##*/}"
  echo "=== Running $WORKFLOW for $REPO bounty $BOUNTY ==="
  "$SCRIPT_DIR/run_workflow.sh" \
    --workflow "$WORKFLOW" \
    --task_dir "$REPO" \
    --bounty_number "$BOUNTY" \
    --use_helm False \
    --use_cwe False
done