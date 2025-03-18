#!/bin/bash

# Exit on any error
set -e

# Function to display help message
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Teardown Kubernetes resources for the BountyAgent application."
    echo ""
    echo "Options:"
    echo "  --all       Delete all resources including PVCs (by default, PVCs are preserved)"
    echo "  --help      Display this help message and exit"
    echo ""
    echo "Examples:"
    echo "  $0                   # Teardown resources but preserve PVCs"
    echo "  $0 --all            # Teardown all resources including PVCs"
    exit 0
}

# Default is to preserve PVCs
DELETE_PVCS=false

# Parse command line arguments
for arg in "$@"
do
    case $arg in
        --all)
        DELETE_PVCS=true
        shift
        ;;
        --help|-h)
        show_help
        ;;
    esac
done

echo "Starting teardown of Kubernetes resources..."

# Create local logs directory
LOCAL_LOGS_DIR="./logs"
mkdir -p "$LOCAL_LOGS_DIR"

# Function to copy logs from a pod
copy_logs_from_pod() {
    POD_NAME=$1
    echo "Copying logs from pod: $POD_NAME"
    
    # Create a temporary directory for this pod's logs
    POD_TEMP_DIR=$(mktemp -d)
    
    # Copy logs from the pod to the temporary directory
    kubectl cp "$POD_NAME:/app/logs/" "$POD_TEMP_DIR" || {
        echo "Warning: Failed to copy logs from $POD_NAME"
        rm -rf "$POD_TEMP_DIR"
        return
    }
    
    # Copy JSON files to the local logs directory (overwrite if names are the same)
    find "$POD_TEMP_DIR" -name "*.json" -exec cp -f {} "$LOCAL_LOGS_DIR" \;
    
    # Clean up temporary directory
    rm -rf "$POD_TEMP_DIR"
    
    echo "Logs from $POD_NAME copied to $LOCAL_LOGS_DIR"
}

# Copy logs from all backend pods before deletion
echo "Copying logs from all backend pods..."
BACKEND_PODS=$(kubectl get pods -o name | grep "pod/backend" || echo "")

if [ -z "$BACKEND_PODS" ]; then
    echo "No backend pods found"
else
    echo "Found backend pods: $BACKEND_PODS"
    for POD in $BACKEND_PODS; do
        POD_NAME=${POD#pod/}
        copy_logs_from_pod "$POD_NAME"
    done
    echo "All logs copied successfully"
fi

# Get all backend services
echo "Finding all backend services..."
BACKEND_SERVICES=$(kubectl get services -o name | grep "service/backend" || echo "")

# Get all backend deployments
echo "Finding all backend deployments..."
BACKEND_DEPLOYMENTS=$(kubectl get deployments -o name | grep "deployment.apps/backend" || echo "")

# Delete services
echo "Deleting services..."
kubectl delete service nginx-service 2>/dev/null || echo "nginx-service already deleted"
kubectl delete service frontend-service 2>/dev/null || echo "frontend-service already deleted"
kubectl delete service redis-service 2>/dev/null || echo "redis-service already deleted"

# Delete all backend services
if [ -n "$BACKEND_SERVICES" ]; then
    for SERVICE in $BACKEND_SERVICES; do
        echo "Deleting $SERVICE..."
        kubectl delete "$SERVICE" 2>/dev/null || echo "$SERVICE already deleted"
    done
else
    echo "No backend services found"
fi

# Delete deployments
echo "Deleting deployments..."
kubectl delete deployment nginx 2>/dev/null || echo "nginx deployment already deleted"
kubectl delete deployment frontend 2>/dev/null || echo "frontend deployment already deleted"
kubectl delete deployment redis 2>/dev/null || echo "redis deployment already deleted"

# Delete all backend deployments
if [ -n "$BACKEND_DEPLOYMENTS" ]; then
    for DEPLOYMENT in $BACKEND_DEPLOYMENTS; do
        echo "Deleting $DEPLOYMENT..."
        kubectl delete "$DEPLOYMENT" 2>/dev/null || echo "$DEPLOYMENT already deleted"
    done
else
    echo "No backend deployments found"
fi

# Delete ConfigMap
echo "Deleting ConfigMap..."
kubectl delete configmap nginx-config 2>/dev/null || echo "nginx-config already deleted"

# Delete Secret
echo "Deleting Secret..."
kubectl delete secret app-secrets 2>/dev/null || echo "app-secrets already deleted"

if [ "$DELETE_PVCS" = true ]; then
    echo "Teardown completed successfully. All resources have been removed."
else
    echo "Teardown completed successfully. All resources except PVCs have been removed."
fi
echo "Logs have been saved to $LOCAL_LOGS_DIR"
