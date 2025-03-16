#!/bin/bash

# Exit on any error
set -e

# Function to display help message
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Deploy and manage backend experiment pods in Kubernetes."
    echo ""
    echo "Options:"
    echo "  --help      Display this help message and exit"
    echo ""
    echo "This script will:"
    echo "  1. Deploy backend service with user-specified number of replicas"
    echo "  2. Pull the latest Docker image in all pods in parallel"
    echo "  3. Execute user-provided commands in each pod"
    echo "  4. Copy logs to a timestamped directory"
    echo "  5. Teardown pods after completion"
    exit 0
}

# Parse command line arguments
for arg in "$@"
do
    case $arg in
        --help|-h)
        show_help
        ;;
    esac
done

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo "Error: kubectl is not installed or not in PATH"
        exit 1
    fi
}

# Function to check if a pod is ready
is_pod_ready() {
    local pod_name=$1
    local status=$(kubectl get pod "$pod_name" -o jsonpath='{.status.phase}')
    if [[ "$status" == "Running" ]]; then
        local container_statuses=$(kubectl get pod "$pod_name" -o jsonpath='{.status.containerStatuses[0].ready}')
        if [[ "$container_statuses" == "true" ]]; then
            return 0
        fi
    fi
    return 1
}

# Function to check if a pod is idle
is_pod_idle() {
    local pod_name=$1
    
    # Check if pod is running and ready first
    if ! is_pod_ready "$pod_name"; then
        return 1
    fi
    
    # Try multiple methods to check POD_STATUS
    # Method 1: Direct environment variable
    local pod_status
    pod_status=$(kubectl exec "$pod_name" -- bash -c "printenv POD_STATUS" 2>/dev/null || echo "")
    
    # Method 2: Echo from bash
    local pod_status2
    pod_status2=$(kubectl exec "$pod_name" -- bash -c "echo \$POD_STATUS" 2>/dev/null || echo "")
    
    # Method 3: Check if file exists
    local file_exists
    file_exists=$(kubectl exec "$pod_name" -- bash -c "if [ -f /tmp/pod_status ]; then echo 'exists'; else echo 'not exists'; fi" 2>/dev/null || echo "not exists")
    
    # Method 4: Read from file if it exists
    local file_content=""
    if [[ "$file_exists" == "exists" ]]; then
        file_content=$(kubectl exec "$pod_name" -- bash -c "cat /tmp/pod_status" 2>/dev/null || echo "")
    fi
    
    # Consider the pod idle if ANY method indicates it's idle
    if [[ "$pod_status" == "IDLE" ]] || [[ "$pod_status2" == "IDLE" ]] || [[ "$file_content" == "IDLE" ]] || [[ -z "$pod_status" && -z "$pod_status2" && "$file_exists" != "exists" ]]; then
        return 0  # Pod is idle
    fi
    
    return 1  # Pod is busy
}

# Function to find existing idle backend-exp pods
find_idle_pods() {
    # Get all existing backend-exp pods - using a more reliable approach
    # Store the output in a temporary file to avoid array parsing issues
    local temp_file=$(mktemp)
    kubectl get pods -l app=backend-exp -o name 2>/dev/null | sed 's/^pod\///' > "$temp_file" || true
    
    # Check if we have any pods
    if [ ! -s "$temp_file" ]; then
        rm "$temp_file"
        return
    fi
    
    # Count the number of pods (line count)
    local pod_count=$(wc -l < "$temp_file")
    echo "Found $pod_count existing backend-exp pods, checking if any are idle..." >&2
    
    # Process each pod line by line and output idle pods one per line
    while IFS= read -r pod; do
        # Skip empty lines
        if [ -z "$pod" ]; then
            continue
        fi
        
        # Check if pod is idle
        if is_pod_idle "$pod"; then
            echo "  - Pod $pod is idle and can be reused" >&2
            # Output each idle pod on its own line (for proper array handling)
            echo "$pod"
        else
            echo "  - Pod $pod is busy or not ready" >&2
        fi
    done < "$temp_file"
    
    # Clean up
    rm "$temp_file"
}

# Function to process a pod once it's ready
process_pod() {
    local pod=$1
    local user_command=$2
    local logs_dir=$3
    
    echo "Processing pod: $pod"
    
    # Pull Docker image
    echo "Pulling Docker image in pod $pod..."
    kubectl exec "$pod" -- bash -c "docker pull --quiet cybench/bountyagent:latest"
    echo "Docker image pulled successfully in pod $pod"
    
    # Execute user command if provided
    if [ ! -z "$user_command" ]; then
        echo "Executing user command in pod $pod..."
        kubectl exec "$pod" -- bash -c "$user_command"
        echo "User command executed in pod $pod"
    fi
    
    # Copy logs
    copy_logs_from_pod "$pod" "$logs_dir"
}

# Function to copy logs from a pod
copy_logs_from_pod() {
    local pod_name=$1
    local logs_dir=$2
    echo "Copying logs from pod: $pod_name"
    
    # Create a temporary directory for this pod's logs
    local pod_temp_dir=$(mktemp -d)
    
    # Copy logs from the pod to the temporary directory
    kubectl cp "$pod_name:/app/logs/" "$pod_temp_dir" || {
        echo "Warning: Failed to copy logs from $pod_name"
        rm -rf "$pod_temp_dir"
        return
    }
    
    # Create a pod-specific directory
    mkdir -p "$logs_dir/$pod_name"
    
    # Copy JSON files to the local logs directory
    find "$pod_temp_dir" -name "*.json" -exec cp -f {} "$logs_dir/$pod_name/" \;
    
    # Clean up temporary directory
    rm -rf "$pod_temp_dir"
    
    echo "Logs from $pod_name copied to $logs_dir/$pod_name"
}

# Function to execute a command in a pod
exec_in_pod() {
    local pod_name=$1
    local command=$2
    echo "Executing command in pod $pod_name: $command"
    kubectl exec "$pod_name" -- bash -c "$command"
}

# Function to execute a command in all pods in parallel
exec_in_all_pods_parallel() {
    local pods=("$@")
    local command="${pods[-1]}" # Last argument is the command
    unset 'pods[${#pods[@]}-1]' # Remove the last element (command)
    
    local pids=()
    
    for pod in "${pods[@]}"; do
        echo "Starting command in pod $pod: $command"
        kubectl exec "$pod" -- bash -c "$command" &
        pids+=($!)
    done
    
    # Wait for all background processes to complete
    for pid in "${pids[@]}"; do
        wait $pid
        local exit_status=$?
        if [[ $exit_status -ne 0 ]]; then
            echo "Command failed in one of the pods with exit status $exit_status"
            return $exit_status
        fi
    done
    
    echo "Command completed successfully in all pods"
    return 0
}

# Main script execution starts here
echo "Backend Experiment Deployment Script"
echo "==================================="

# Check if kubectl is available
check_kubectl

# Create a timestamped directory for logs
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
EXPERIMENT_DIR="./logs/exp-$TIMESTAMP"
mkdir -p "$EXPERIMENT_DIR"
echo "Experiment logs will be saved to: $EXPERIMENT_DIR"

# Ask user for number of total replicas needed
read -p "Enter the total number of replicas needed [default: 1]: " TOTAL_REPLICAS
TOTAL_REPLICAS=${TOTAL_REPLICAS:-1}

# Validate input is a positive integer
if ! [[ "$TOTAL_REPLICAS" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: Number of replicas must be a positive integer"
    exit 1
fi

# Check for existing idle pods that can be reused
echo "Checking for existing idle backend-exp pods..."
# Create a temporary file to store the idle pods
TEMP_IDLE_FILE=$(mktemp)
find_idle_pods > "$TEMP_IDLE_FILE"

# Read the idle pods into an array, one per line
IDLE_PODS=()
while IFS= read -r pod; do
    # Skip empty lines
    if [ -n "$pod" ]; then
        IDLE_PODS+=("$pod")
    fi
done < "$TEMP_IDLE_FILE"
rm "$TEMP_IDLE_FILE"

# Count the idle pods
NUM_IDLE_PODS=${#IDLE_PODS[@]}

if [ $NUM_IDLE_PODS -gt 0 ]; then
    echo "Found exactly $NUM_IDLE_PODS idle backend-exp pods that can be reused"
    
    # Ask user if they want to reuse existing pods
    read -p "Do you want to reuse existing idle pods? (y/n) [default: y]: " REUSE_PODS
    REUSE_PODS=${REUSE_PODS:-y}
    
    if [[ "$REUSE_PODS" =~ ^[Yy]$ ]]; then
        echo "Will reuse existing idle pods"
        REUSE_EXISTING=true
        
        # Calculate how many new pods we need to create
        if [ $NUM_IDLE_PODS -ge $TOTAL_REPLICAS ]; then
            # We have enough idle pods, no need to create new ones
            REPLICAS=0
            # Use only as many idle pods as requested
            IDLE_PODS=("${IDLE_PODS[@]:0:$TOTAL_REPLICAS}")
            NUM_IDLE_PODS=$TOTAL_REPLICAS
            echo "Using $NUM_IDLE_PODS existing idle pods (no new pods needed)"
        else
            # Need to create additional pods
            REPLICAS=$((TOTAL_REPLICAS - NUM_IDLE_PODS))
            echo "Using $NUM_IDLE_PODS existing idle pods plus creating $REPLICAS new pods (total: $TOTAL_REPLICAS)"
        fi
    else
        echo "Will not reuse existing pods"
        REUSE_EXISTING=false
        NUM_IDLE_PODS=0
        REPLICAS=$TOTAL_REPLICAS
        echo "Creating $REPLICAS new pods"
    fi
else
    echo "No idle backend-exp pods found"
    REUSE_EXISTING=false
    REPLICAS=$TOTAL_REPLICAS
    echo "Creating $REPLICAS new pods"
fi

# Create a temporary YAML file with the specified number of replicas
TEMP_YAML=$(mktemp)
cat > "$TEMP_YAML" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-exp
  labels:
    app: backend-exp
spec:
  replicas: $REPLICAS
  selector:
    matchLabels:
      app: backend-exp
  template:
    metadata:
      labels:
        app: backend-exp
    spec:
      tolerations:
      - key: "kubernetes.io/arch"
        operator: "Equal"
        value: "arm64"
        effect: "NoSchedule"
      containers:
      - name: backend
        image: us-west1-docker.pkg.dev/soe-ai-cyber/bountyagent/backend-image:exp
        imagePullPolicy: Always
        ports:
        - containerPort: 7999
        securityContext:
          privileged: true  # Required for Docker-in-Docker
        volumeMounts:
        - name: dind-storage
          mountPath: /var/lib/docker
        - name: logs
          mountPath: /app/logs
        envFrom:
        - secretRef:
            name: app-secrets
      volumes:
      - name: dind-storage
        emptyDir: {}
      - name: logs
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: backend-exp-service
spec:
  selector:
    app: backend-exp
  ports:
  - port: 7999
    targetPort: 7999
EOF

# Create app-secrets from .env file if it doesn't exist
if ! kubectl get secret app-secrets &>/dev/null; then
    echo "Creating app-secrets from .env file..."
    kubectl create secret generic app-secrets --from-env-file=../.env
else
    echo "Secret app-secrets already exists, using existing secret"
fi

# Apply the YAML file
kubectl apply -f "$TEMP_YAML"
rm "$TEMP_YAML"

echo "Waiting for backend-exp pods to be created..."
sleep 5

# Initialize the array of pods to process
BACKEND_PODS=()

# Add existing idle pods if we're reusing them
if [ $REUSE_EXISTING = true ] && [ $NUM_IDLE_PODS -gt 0 ]; then
    for pod in "${IDLE_PODS[@]}"; do
        BACKEND_PODS+=("$pod")
    done
    echo "Added $NUM_IDLE_PODS existing idle pods to the processing list"
fi

# Get newly created backend-exp pods if we created any
if [ $REPLICAS -gt 0 ]; then
    # Wait a bit for pods to be created
    echo "Waiting for new backend-exp pods to be created..."
    sleep 5
    
    # Get all pods with the app=backend-exp label
    ALL_PODS=($(kubectl get pods -l app=backend-exp -o name | sed 's/^pod\///'))
    
    # Filter out the idle pods we already know about
    for pod in "${ALL_PODS[@]}"; do
        # Check if this pod is in our IDLE_PODS list
        if [[ " ${IDLE_PODS[*]} " != *" $pod "* ]]; then
            BACKEND_PODS+=("$pod")
        fi
    done
    
    echo "Added $(( ${#BACKEND_PODS[@]} - $NUM_IDLE_PODS )) newly created pods to the processing list"
fi

if [ ${#BACKEND_PODS[@]} -eq 0 ]; then
    echo "Error: No backend-exp pods were available for processing"
    exit 1
fi

echo "Total pods for processing: ${#BACKEND_PODS[@]}"
for pod in "${BACKEND_PODS[@]}"; do
    echo "  - $pod"
done

# Ask user for command to execute
read -p "Enter command to execute in all pods (leave empty to skip): " USER_COMMAND

# Process pods as they become ready in parallel
echo "Processing pods as they become ready in parallel..."

# Array to track processed pods and background processes
PROCESSED_PODS=()
PROCESSING_PODS=()
PID_MAP=()
POD_START_TIMES=()
POD_STAGES=()

# Maximum time to wait for pods (in seconds)
MAX_WAIT_TIME=300
START_TIME=$(date +%s)

# Function to display progress for all pods
display_progress() {
    local current_time=$(date +%s)
    local total_elapsed=$((current_time - START_TIME))
    local elapsed_min=$((total_elapsed / 60))
    local elapsed_sec=$((total_elapsed % 60))
    
    # Clear previous lines if not the first display
    if [ "$1" != "first" ]; then
        # Move cursor up by the number of pods + 2 header lines
        for ((i=0; i<${#BACKEND_PODS[@]}+2; i++)); do
            echo -en "\033[1A\033[K"
        done
    fi
    
    # Print header with elapsed time
    echo -e "\nPod Processing Status (Elapsed time: ${elapsed_min}m ${elapsed_sec}s):"
    echo -e "--------------------------------------------------------------"
    
    # Print status for each pod
    for pod in "${BACKEND_PODS[@]}"; do
        local status="Waiting"
        local progress="[       ]"
        local time_info=""
        
        # Check if pod is processed
        if [[ " ${PROCESSED_PODS[*]} " =~ " $pod " ]]; then
            status="Completed"
            progress="[✓✓✓✓✓✓✓]"
            
            # Calculate pod processing time if available
            for entry in "${POD_START_TIMES[@]}"; do
                if [[ "$entry" == "$pod:"* ]]; then
                    local start_time=${entry#*:}
                    local pod_elapsed=$((current_time - start_time))
                    local pod_elapsed_min=$((pod_elapsed / 60))
                    local pod_elapsed_sec=$((pod_elapsed % 60))
                    time_info="(${pod_elapsed_min}m ${pod_elapsed_sec}s)"
                    break
                fi
            done
        # Check if pod is being processed
        elif [[ " ${PROCESSING_PODS[*]} " =~ " $pod " ]]; then
            status="Processing"
            
            # Get current stage if available
            for entry in "${POD_STAGES[@]}"; do
                if [[ "$entry" == "$pod:"* ]]; then
                    local stage=${entry#*:}
                    case "$stage" in
                        "pulling")
                            progress="[■      ]"
                            ;;
                        "pulled")
                            progress="[■■     ]"
                            ;;
                        "executing")
                            progress="[■■■    ]"
                            ;;
                        "executed")
                            progress="[■■■■   ]"
                            ;;
                        "copying")
                            progress="[■■■■■  ]"
                            ;;
                        "copied")
                            progress="[■■■■■■ ]"
                            ;;
                    esac
                    break
                fi
            done
            
            # Calculate time in processing state
            for entry in "${POD_START_TIMES[@]}"; do
                if [[ "$entry" == "$pod:"* ]]; then
                    local start_time=${entry#*:}
                    local pod_elapsed=$((current_time - start_time))
                    local pod_elapsed_min=$((pod_elapsed / 60))
                    local pod_elapsed_sec=$((pod_elapsed % 60))
                    time_info="(${pod_elapsed_min}m ${pod_elapsed_sec}s)"
                    break
                fi
            done
        # Pod is not ready yet
        else
            local ready="false"
            if is_pod_ready "$pod"; then
                ready="true"
                status="Ready"
                progress="[>      ]"
            fi
        fi
        
        echo -e "$pod: $status $progress $time_info"
    done
}

while [ ${#PROCESSED_PODS[@]} -lt ${#BACKEND_PODS[@]} ]; do
    # Check if we've exceeded the maximum wait time
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED_TIME -gt $MAX_WAIT_TIME ]; then
        echo "Warning: Exceeded maximum wait time of $MAX_WAIT_TIME seconds"
        echo "Processed ${#PROCESSED_PODS[@]} out of ${#BACKEND_PODS[@]} pods"
        break
    fi
    
    # Check for completed background processes
    for i in "${!PID_MAP[@]}"; do
        pid=${PID_MAP[$i]%:*}
        pod=${PID_MAP[$i]#*:}
        
        if ! ps -p "$pid" > /dev/null; then
            # Process has completed
            echo "Processing completed for pod $pod"
            PROCESSED_PODS+=("$pod")
            # Remove from processing list and PID map
            PROCESSING_PODS=(${PROCESSING_PODS[@]/"$pod"/})
            unset PID_MAP[$i]
        fi
    done
    
    # Start processing for any newly ready pods
    for pod in "${BACKEND_PODS[@]}"; do
        # Skip already processed or processing pods
        if [[ " ${PROCESSED_PODS[*]} " =~ " $pod " ]] || [[ " ${PROCESSING_PODS[*]} " =~ " $pod " ]]; then
            continue
        fi
        
        # Check if pod is ready
        if is_pod_ready "$pod"; then
            echo "Pod $pod is ready, starting processing in background"
            
            # Record start time for this pod
            POD_START_TIMES+=("$pod:$(date +%s)")
            
            # Start processing in background
            {
                # Set POD_STATUS environment variable to BUSY
                kubectl exec "$pod" -- bash -c "export POD_STATUS=BUSY && echo \$POD_STATUS > /tmp/pod_status && echo 'export POD_STATUS=BUSY' >> ~/.bashrc"
                
                # Update stage
                POD_STAGES+=("$pod:pulling")
                
                # Pull Docker image
                kubectl exec "$pod" -- bash -c "docker pull --quiet cybench/bountyagent:latest"
                
                # Update stage
                POD_STAGES=(${POD_STAGES[@]/"$pod:pulling"/"$pod:pulled"})
                
                # Execute user command if provided
                if [ ! -z "$USER_COMMAND" ]; then
                    POD_STAGES=(${POD_STAGES[@]/"$pod:pulled"/"$pod:executing"})
                    kubectl exec "$pod" -- bash -c "$USER_COMMAND"
                    POD_STAGES=(${POD_STAGES[@]/"$pod:executing"/"$pod:executed"})
                fi
                
                # Copy logs
                POD_STAGES=(${POD_STAGES[@]/"$pod:pulled"/"$pod:copying"})
                POD_STAGES=(${POD_STAGES[@]/"$pod:executed"/"$pod:copying"})
                copy_logs_from_pod "$pod" "$EXPERIMENT_DIR"
                POD_STAGES=(${POD_STAGES[@]/"$pod:copying"/"$pod:copied"})
                
                # Reset POD_STATUS environment variable to IDLE when done
                kubectl exec "$pod" -- bash -c "export POD_STATUS=IDLE && echo \$POD_STATUS > /tmp/pod_status && sed -i '/export POD_STATUS=BUSY/d' ~/.bashrc && echo 'export POD_STATUS=IDLE' >> ~/.bashrc"
            } &
            
            # Store the PID and pod name
            bg_pid=$!
            PID_MAP+=("$bg_pid:$pod")
            PROCESSING_PODS+=("$pod")
            echo "Started background process for pod $pod with PID $bg_pid"
        fi
    done
    
    # Display progress for all pods
    if [ -z "$PROGRESS_DISPLAYED" ]; then
        display_progress "first"
        PROGRESS_DISPLAYED=true
    else
        display_progress
    fi
    
    # Sleep before checking again
    sleep 2
done

echo "All available pods have been processed"

# Ask user if they want to teardown the deployment
read -p "Do you want to teardown the backend-exp deployment? (y/n) [default: y]: " TEARDOWN
TEARDOWN=${TEARDOWN:-y}

if [[ "$TEARDOWN" =~ ^[Yy]$ ]]; then
    echo "Tearing down backend-exp deployment..."
    kubectl delete deployment backend-exp
    kubectl delete service backend-exp-service
    echo "Backend-exp deployment torn down successfully"
else
    echo "Keeping backend-exp deployment running"
fi

echo "Experiment completed successfully!"
echo "Logs are available in: $EXPERIMENT_DIR"
