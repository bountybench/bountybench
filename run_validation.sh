#!/bin/bash

INPUT_FILE="bounties_list.txt"
CONTAINER_NAME="backend-service"
OUTPUT_DIR="validation_outputs"

mkdir -p "$OUTPUT_DIR"

while IFS=',' read -r TASKDIR NUM; do
    echo "Processing TASKDIR=${TASKDIR}, NUM=${NUM}"

    # 1. Start container
    echo "[INFO] Starting Docker container..."
    # (only need to create backend)
    docker compose up -d backend

    echo "[INFO] Waiting 5s for container to be ready..." 
    sleep 5

    # 2. Run command inside container
    CMD="cd bountybench && ./run_ci_local.sh ${TASKDIR}/bounties/bounty_${NUM} --patch --check-invariants"
    echo "[INFO] Running validation script in container: $CMD"

    docker exec "$CONTAINER_NAME" bash -c "$CMD" > "${OUTPUT_DIR}/bounty_${TASKDIR}_${NUM}_output.txt" 2>&1

    echo "[INFO] Output saved to ${OUTPUT_DIR}/bounty_${TASKDIR}_${NUM}_output.txt"

    # 3. Tear down container
    echo "[INFO] Stopping Docker container..."
    docker compose down -v

    echo "[INFO] Completed TASKDIR=${TASKDIR}, NUM=${NUM}"
    echo "--------------------------------------------"
    sleep 5  # Small pause between runs
done < "$INPUT_FILE"

echo "[INFO] All tasks completed!"
