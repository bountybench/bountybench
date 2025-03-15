#!/bin/bash

# Script to set up Docker images for BountyAgent
# This script:
# 1. Configures Docker for Google Container Registry
# 2. Tags local Docker images with GCR repository
# 3. Pushes the tagged images to GCR

echo "Starting Docker image setup for BountyAgent..."

# Step 1: Configure Docker for Google Container Registry
echo "Configuring Docker for Google Container Registry..."
gcloud auth configure-docker us-west1-docker.pkg.dev

# Step 2: Tag frontend image
echo "Tagging frontend image..."
docker tag bountyagent-frontend us-west1-docker.pkg.dev/soe-ai-cyber/bountyagent/frontend-image:v1

# Step 3: Tag backend image
echo "Tagging backend image..."
docker tag bountyagent-backend us-west1-docker.pkg.dev/soe-ai-cyber/bountyagent/backend-image:v1

# Step 4: Push frontend image
echo "Pushing frontend image to Google Container Registry..."
docker push us-west1-docker.pkg.dev/soe-ai-cyber/bountyagent/frontend-image:v1

# Step 5: Push backend image
echo "Pushing backend image to Google Container Registry..."
docker push us-west1-docker.pkg.dev/soe-ai-cyber/bountyagent/backend-image:v1

echo "Docker image setup completed successfully!"
