#!/bin/bash

# Build local Docker images if necessary
# cd ../frontend
# docker build -t frontend-image:v1 -f Dockerfile.frontend .
# cd ../
# docker build -t backend-image:v1 -f Dockerfile.backend .


# Exit on any error
set -e

# Ensure Minikube is running
echo "Starting Minikube if not already running..."
minikube start --driver=docker

# Apply Kubernetes manifests
echo "Applying Kubernetes manifests..."
kubectl apply -f configmap.yaml
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

echo "Starting minikube tunnel to connect to LoadBalancer services"
echo "Access the application at http://localhost:80"

minikube tunnel