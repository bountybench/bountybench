#!/bin/bash

# Exit on any error
set -e

# Apply Kubernetes manifests
kubectl apply -f configmap.yaml
kubectl apply -f dind-pvc.yaml
kubectl apply -f logs-pvc.yaml
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml
kubectl apply -f nginx.yaml
kubectl apply -f redis.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend
kubectl wait --for=condition=available --timeout=300s deployment/frontend
kubectl wait --for=condition=available --timeout=300s deployment/nginx
kubectl wait --for=condition=available --timeout=300s deployment/redis

# Get the external IP of the nginx service
echo "Getting external IP..."
EXTERNAL_IP=""
while [ -z "$EXTERNAL_IP" ]; do
  echo "Waiting for external IP..."
  EXTERNAL_IP=$(kubectl get service nginx-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
  [ -z "$EXTERNAL_IP" ] && sleep 10
done

echo "Application deployed successfully!"
echo "You can access your application at: http://$EXTERNAL_IP"
