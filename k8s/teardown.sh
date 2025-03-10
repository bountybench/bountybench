#!/bin/bash

# Exit on any error
set -e

echo "Starting teardown of Kubernetes resources..."

# Delete deployments and services
echo "Deleting deployments and services..."
kubectl delete service nginx-service || echo "nginx-service already deleted"
kubectl delete service frontend-service || echo "frontend-service already deleted"
kubectl delete service backend-service || echo "backend-service already deleted"
kubectl delete deployment nginx || echo "nginx deployment already deleted"
kubectl delete deployment frontend || echo "frontend deployment already deleted"
kubectl delete deployment backend || echo "backend deployment already deleted"
kubectl delete deployment redis || echo "redis deployment already deleted"
kubectl delete service redis-service || echo "redis-service already deleted"

# Delete PVCs (will also delete the PVs if they're dynamically provisioned)
echo "Deleting persistent volume claims..."
kubectl delete pvc logs-data || echo "logs-data PVC already deleted"
kubectl delete pvc dind-data || echo "dind-data PVC already deleted"

# Delete ConfigMap
echo "Deleting ConfigMap..."
kubectl delete configmap nginx-config || echo "nginx-config already deleted"

# Delete Secret
echo "Deleting Secret..."
kubectl delete secret app-secrets || echo "app-secrets already deleted"

echo "Teardown completed successfully. All resources have been removed."
